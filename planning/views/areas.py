"""Life Areas: manage, detail, North Light, per-year assessment."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ..access import get_owned_or_404, owned
from ..forms import AssessmentForm, LifeAreaForm, NorthLightForm
from ..models import Goal, Habit, LifeArea, LifeAreaAssessment, Milestone, OPEN_STATUSES
from ..services import (
    current_year, ensure_assessments, ensure_default_life_areas, reorder_life_areas,
    restore_default_life_areas,
)


@login_required
def area_list(request):
    areas = list(owned(LifeArea, request.user))
    form = LifeAreaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        area = form.save(commit=False)
        area.user = request.user  # ownership is never taken from input
        area.sort_order = (owned(LifeArea, request.user).aggregate(m=Max("sort_order"))["m"] or 0) + 1
        area.save()
        year = current_year(request.user)
        if year:
            ensure_assessments(year)
        messages.success(request, f"Added “{area.name}”.")
        return redirect("planning:area_list")
    return render(request, "planning/area_list.html", {
        "active": [a for a in areas if a.is_active],
        "archived": [a for a in areas if not a.is_active],
        "form": form,
    })


@login_required
def area_edit(request, pk):
    area = get_owned_or_404(LifeArea, request.user, pk=pk)
    form = LifeAreaForm(request.POST or None, instance=area)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Life Area updated.")
        return redirect("planning:area_detail", pk=area.pk)
    return render(request, "planning/area_form.html", {"form": form, "area": area})


@login_required
@require_POST
def area_archive(request, pk):
    area = get_owned_or_404(LifeArea, request.user, pk=pk)
    area.is_active = False
    area.save(update_fields=["is_active"])
    messages.info(request, f"“{area.name}” archived. Its history is kept.")
    return redirect("planning:area_list")


@login_required
@require_POST
def area_restore(request, pk):
    area = get_owned_or_404(LifeArea, request.user, pk=pk)
    area.is_active = True
    area.save(update_fields=["is_active"])
    year = current_year(request.user)
    if year:
        ensure_assessments(year)
    return redirect("planning:area_list")


@login_required
@require_POST
def area_reorder(request):
    ids = [int(x) for x in request.POST.getlist("order") if x.isdigit()]
    reorder_life_areas(request.user, ids)
    return redirect("planning:area_list")


@login_required
@require_POST
def area_restore_defaults(request):
    if not owned(LifeArea, request.user).exists():
        ensure_default_life_areas(request.user)
        n = 10
    else:
        n = restore_default_life_areas(request.user)
    year = current_year(request.user)
    if year:
        ensure_assessments(year)
    messages.success(request, f"Default areas restored ({n} added or re-activated).")
    return redirect("planning:area_list")


@login_required
def area_detail(request, pk):
    area = get_owned_or_404(LifeArea, request.user, pk=pk)
    year = current_year(request.user)
    assessment = LifeAreaAssessment.objects.filter(personal_year=year, life_area=area).first() if year else None
    goals = owned(Goal, request.user).filter(life_area=area, personal_year=year) if year else Goal.objects.none()
    milestones = owned(Milestone, request.user).filter(goal__in=goals, status__in=OPEN_STATUSES).select_related("goal")
    habits = owned(Habit, request.user).filter(life_area=area, is_active=True)
    history = (LifeAreaAssessment.objects.filter(life_area=area).exclude(personal_year=year)
               .select_related("personal_year").order_by("-personal_year__start_date")) if year else \
        LifeAreaAssessment.objects.filter(life_area=area).select_related("personal_year")
    return render(request, "planning/area_detail.html", {
        "area": area, "year": year, "assessment": assessment, "goals": goals,
        "milestones": milestones, "habits": habits, "history": history,
    })


@login_required
def area_northlight(request, pk):
    area = get_owned_or_404(LifeArea, request.user, pk=pk)
    form = NorthLightForm(request.POST or None, instance=area)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "North Light saved.")
        return redirect("planning:area_detail", pk=area.pk)
    return render(request, "planning/area_northlight.html",
                  {"form": form, "area": area, "samples_open": not area.north_light})


@login_required
def area_assess(request, pk):
    """Edit this year's scores, mode and 12-month vision for one area."""
    area = get_owned_or_404(LifeArea, request.user, pk=pk)
    year = current_year(request.user)
    if year is None:
        messages.warning(request, "Create a Personal Year first.")
        return redirect("planning:year_create")
    ensure_assessments(year)
    assessment = get_owned_or_404(LifeAreaAssessment, request.user, personal_year=year, life_area=area)
    before = (assessment.satisfaction, assessment.importance, assessment.strategic_mode)
    form = AssessmentForm(request.POST or None, instance=assessment)
    if request.method == "POST" and form.is_valid():
        assessment = form.save()
        if (assessment.satisfaction, assessment.importance, assessment.strategic_mode) != before:
            assessment.snapshot(source="edit")
        messages.success(request, "Assessment saved.")
        return redirect("planning:area_detail", pk=area.pk)
    return render(request, "planning/area_assess.html", {"form": form, "area": area, "assessment": assessment, "year": year})

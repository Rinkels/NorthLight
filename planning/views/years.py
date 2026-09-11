"""Personal Years: list, create, edit, activate, complete, roll forward."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ..access import get_owned_or_404, owned, profile_for
from ..forms import PersonalYearForm, YearReflectionForm
from ..models import Goal, LifeAreaAssessment, PersonalYear, WorkStatus
from ..services import activate_year, create_next_year, default_year_bounds, ensure_assessments, start_vs_end


@login_required
def year_list(request):
    years = owned(PersonalYear, request.user)
    return render(request, "planning/year_list.html", {"years": years})


@login_required
def year_create(request):
    start, end, title = default_year_bounds(profile_for(request.user))
    form = PersonalYearForm(request.POST or None, initial={"title": title, "start_date": start, "end_date": end})
    if request.method == "POST" and form.is_valid():
        year = form.save(commit=False)
        year.user = request.user
        year.save()
        ensure_assessments(year, source="created")
        messages.success(request, f"“{year.title}” created (Planning).")
        return redirect("planning:year_detail", pk=year.pk)
    return render(request, "planning/year_form.html", {"form": form})


@login_required
def year_edit(request, pk):
    year = get_owned_or_404(PersonalYear, request.user, pk=pk)
    form = PersonalYearForm(request.POST or None, instance=year)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Personal Year updated.")
        return redirect("planning:year_detail", pk=year.pk)
    return render(request, "planning/year_form.html", {"form": form, "year": year})


@login_required
def year_detail(request, pk):
    year = get_owned_or_404(PersonalYear, request.user, pk=pk)
    assessments = LifeAreaAssessment.objects.filter(personal_year=year).select_related("life_area")
    goals = owned(Goal, request.user).filter(personal_year=year).select_related("life_area")
    reflection_form = YearReflectionForm(request.POST or None, instance=year)
    if request.method == "POST" and reflection_form.is_valid():
        reflection_form.save()
        messages.success(request, "Reflection saved.")
        return redirect("planning:year_detail", pk=year.pk)
    return render(request, "planning/year_detail.html", {
        "year": year, "assessments": assessments, "goals": goals,
        "reflection_form": reflection_form,
        "comparison": start_vs_end(year) if year.status != PersonalYear.STATUS_PLANNING else None,
    })


@login_required
@require_POST
def year_activate(request, pk):
    year = get_owned_or_404(PersonalYear, request.user, pk=pk)
    ensure_assessments(year)
    activate_year(year)
    messages.success(request, f"“{year.title}” is now your Active year.")
    return redirect("planning:dashboard")


@login_required
@require_POST
def year_complete(request, pk):
    year = get_owned_or_404(PersonalYear, request.user, pk=pk)
    year.status = PersonalYear.STATUS_COMPLETED
    year.save(update_fields=["status"])
    messages.success(request, f"“{year.title}” marked Completed. Write your annual review, then create the next year.")
    return redirect("planning:year_detail", pk=year.pk)


@login_required
@require_POST
def year_archive(request, pk):
    year = get_owned_or_404(PersonalYear, request.user, pk=pk)
    year.status = PersonalYear.STATUS_ARCHIVED
    year.save(update_fields=["status"])
    return redirect("planning:year_list")


@login_required
def year_next(request, pk):
    """Create the following year from a completed one. Goals are carried
    forward only if explicitly ticked — never automatically."""
    previous = get_owned_or_404(PersonalYear, request.user, pk=pk)
    candidates = owned(Goal, request.user).filter(personal_year=previous).exclude(status=WorkStatus.COMPLETE)
    if request.method == "POST":
        ids = [int(x) for x in request.POST.getlist("carry") if x.isdigit()]
        nxt = create_next_year(previous, carry_goal_ids=ids)
        messages.success(request, f"“{nxt.title}” created with {len(ids)} goal(s) carried forward.")
        return redirect("planning:year_detail", pk=nxt.pk)
    return render(request, "planning/year_next.html", {"previous": previous, "candidates": candidates})

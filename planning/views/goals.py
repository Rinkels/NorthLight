"""Goals, goal links, 90-day milestones, habits."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import redirect, render
from datetime import timedelta

from django.utils import timezone
from django.views.decorators.http import require_POST

from ..access import get_owned_or_404, owned
from ..forms import GoalForm, GoalLinkForm, HabitForm, MilestoneForm
from ..models import (
    GOAL_TYPE_HELP, Goal, GoalRelationship, GoalType, Habit, HabitCheckin, LifeArea,
    LifeAreaAssessment, Milestone, PersonalYear, StrategicMode, WorkStatus,
)
from ..services import STALE_GOAL_DAYS, current_year


# --------------------------------------------------------------------------- #
# Goals
# --------------------------------------------------------------------------- #

@login_required
def goal_list(request):
    user = request.user
    qs = owned(Goal, user).select_related("life_area", "personal_year")
    f = {k: request.GET.get(k, "") for k in ("year", "area", "status", "mode", "type")}
    year = current_year(user)
    if f["year"]:
        qs = qs.filter(personal_year_id=f["year"])
    elif year and not any(f.values()):
        qs = qs.filter(personal_year=year)
        f["year"] = str(year.id)
    if f["area"]:
        qs = qs.filter(life_area_id=f["area"])
    if f["status"]:
        qs = qs.filter(status=f["status"])
    if f["type"]:
        qs = qs.filter(goal_type=f["type"])
    if f["mode"]:
        pairs = LifeAreaAssessment.objects.filter(user=user, strategic_mode=f["mode"]) \
            .values_list("personal_year_id", "life_area_id")
        keep = [g.id for g in qs if (g.personal_year_id, g.life_area_id) in set(pairs)]
        qs = qs.filter(id__in=keep)
    stale_before = timezone.now() - timedelta(days=STALE_GOAL_DAYS)
    return render(request, "planning/goal_list.html", {
        "stale_before": stale_before,
        "goals": qs, "filters": f,
        "years": owned(PersonalYear, user), "areas": owned(LifeArea, user).filter(is_active=True),
        "statuses": WorkStatus.choices, "modes": StrategicMode.choices, "types": GoalType.choices,
    })


@login_required
def goal_create(request):
    year = current_year(request.user)
    initial = {"personal_year": year, "life_area": request.GET.get("area")}
    form = GoalForm(request.POST or None, initial=initial).for_user(request.user)
    if request.method == "POST" and form.is_valid():
        goal = form.save(commit=False)
        goal.user = request.user
        goal.save()
        messages.success(request, f"Goal “{goal.title}” added.")
        return redirect("planning:goal_detail", pk=goal.pk)
    return render(request, "planning/goal_form.html", {"form": form, "type_help": GOAL_TYPE_HELP})


@login_required
def goal_detail(request, pk):
    goal = get_owned_or_404(Goal, request.user, pk=pk)
    link_form = GoalLinkForm(outcome_goal=goal).for_user(request.user)
    return render(request, "planning/goal_detail.html", {
        "goal": goal,
        "milestones": goal.milestones.all(),
        "habits": goal.habits.all(),
        "supporting": [l.process_goal for l in goal.supporting_links.select_related("process_goal")],
        "supports": [l.outcome_goal for l in goal.supports_links.select_related("outcome_goal")],
        "link_form": link_form,
    })


@login_required
def goal_edit(request, pk):
    goal = get_owned_or_404(Goal, request.user, pk=pk)
    form = GoalForm(request.POST or None, instance=goal).for_user(request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Goal updated.")
        return redirect("planning:goal_detail", pk=goal.pk)
    return render(request, "planning/goal_form.html", {"form": form, "goal": goal, "type_help": GOAL_TYPE_HELP})


@login_required
@require_POST
def goal_delete(request, pk):
    goal = get_owned_or_404(Goal, request.user, pk=pk)
    goal.delete()
    messages.info(request, "Goal deleted.")
    return redirect("planning:goal_list")


@login_required
@require_POST
def goal_status(request, pk):
    """Quick status change (pause / drop / complete) — changing your mind is not failure."""
    goal = get_owned_or_404(Goal, request.user, pk=pk)
    status = request.POST.get("status")
    if status in WorkStatus.values:
        goal.status = status
        goal.save()
    nxt = request.POST.get("next")
    return redirect(nxt) if nxt else redirect("planning:goal_detail", pk=goal.pk)


@login_required
@require_POST
def goal_link(request, pk):
    goal = get_owned_or_404(Goal, request.user, pk=pk)
    form = GoalLinkForm(request.POST, outcome_goal=goal).for_user(request.user)
    if form.is_valid():
        try:
            GoalRelationship.objects.create(outcome_goal=goal, process_goal=form.cleaned_data["process_goal"])
        except IntegrityError:
            messages.info(request, "Those goals are already linked.")
    return redirect("planning:goal_detail", pk=goal.pk)


@login_required
@require_POST
def goal_unlink(request, pk, other_pk):
    goal = get_owned_or_404(Goal, request.user, pk=pk)
    owned(GoalRelationship, request.user).filter(outcome_goal=goal, process_goal_id=other_pk).delete()
    return redirect("planning:goal_detail", pk=goal.pk)


# --------------------------------------------------------------------------- #
# Milestones (90-day)
# --------------------------------------------------------------------------- #

@login_required
def milestone_create(request, goal_pk):
    goal = get_owned_or_404(Goal, request.user, pk=goal_pk)
    form = MilestoneForm(request.POST or None, initial={"goal": goal}).for_user(request.user)
    if request.method == "POST" and form.is_valid():
        m = form.save(commit=False)
        m.user = request.user
        m.save()
        messages.success(request, "Milestone added.")
        return redirect("planning:goal_detail", pk=m.goal_id)
    return render(request, "planning/milestone_form.html", {"form": form, "goal": goal})


@login_required
def milestone_edit(request, pk):
    m = get_owned_or_404(Milestone, request.user, pk=pk)
    form = MilestoneForm(request.POST or None, instance=m).for_user(request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Milestone updated.")
        return redirect("planning:goal_detail", pk=m.goal_id)
    return render(request, "planning/milestone_form.html", {"form": form, "goal": m.goal, "milestone": m})


@login_required
@require_POST
def milestone_delete(request, pk):
    m = get_owned_or_404(Milestone, request.user, pk=pk)
    goal_id = m.goal_id
    m.delete()
    return redirect("planning:goal_detail", pk=goal_id)


# --------------------------------------------------------------------------- #
# Habits (simple completion tracking)
# --------------------------------------------------------------------------- #

@login_required
def milestone_list(request):
    """All 90-day milestones, open ones first by due date, then the rest."""
    year = current_year(request.user)
    qs = owned(Milestone, request.user).select_related("goal", "goal__life_area", "goal__personal_year")
    if year and not request.GET.get("all"):
        qs = qs.filter(goal__personal_year=year)
    ms = list(qs)
    return render(request, "planning/milestone_list.html", {
        "open": sorted([m for m in ms if m.is_open], key=lambda m: (m.due_date is None, m.due_date or timezone.localdate())),
        "closed": [m for m in ms if not m.is_open],
        "year": year, "show_all": bool(request.GET.get("all")),
    })


@login_required
def habit_list(request):
    habits = owned(Habit, request.user).select_related("life_area", "goal")
    return render(request, "planning/habit_list.html", {
        "active": [h for h in habits if h.is_active],
        "inactive": [h for h in habits if not h.is_active],
        "today": timezone.localdate(),
    })


@login_required
def habit_create(request):
    form = HabitForm(request.POST or None, initial={"life_area": request.GET.get("area"), "goal": request.GET.get("goal")}) \
        .for_user(request.user)
    if request.method == "POST" and form.is_valid():
        h = form.save(commit=False)
        h.user = request.user
        h.save()
        messages.success(request, f"Habit “{h.title}” added.")
        return redirect("planning:habit_list")
    return render(request, "planning/habit_form.html", {"form": form})


@login_required
def habit_edit(request, pk):
    h = get_owned_or_404(Habit, request.user, pk=pk)
    form = HabitForm(request.POST or None, instance=h).for_user(request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Habit updated.")
        return redirect("planning:habit_list")
    return render(request, "planning/habit_form.html", {"form": form, "habit": h})


@login_required
@require_POST
def habit_delete(request, pk):
    h = get_owned_or_404(Habit, request.user, pk=pk)
    h.delete()
    return redirect("planning:habit_list")


@login_required
@require_POST
def habit_checkin(request, pk):
    """Once-per-period habits toggle today's check-in; X-times habits increment."""
    h = get_owned_or_404(Habit, request.user, pk=pk)
    today = timezone.localdate()
    existing = h.checkins.filter(date=today).first()
    if h.target_per_period == 1:
        if existing:
            existing.delete()
        else:
            HabitCheckin.objects.create(habit=h, date=today)
    else:
        if existing:
            existing.count += 1
            existing.save(update_fields=["count"])
        else:
            HabitCheckin.objects.create(habit=h, date=today)
    return redirect(request.POST.get("next") or "planning:habit_list")

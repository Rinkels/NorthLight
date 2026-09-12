"""“Design my life”: a guided walk through the user's Life Areas, one area per
page, offering starting points rather than a pre-filled life.

For every area: a sample North Light + Why to start from (editable).
For areas marked Improve: a few sample goals, with baseline and target left
blank so the user has to make them concrete. Nothing is created unless the
user ticks it; every suggestion is a click, never a default.
"""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from ..access import owned
from ..forms import NorthLightForm
from ..library import goal_samples_for
from ..models import Goal, GoalType, LifeArea, LifeAreaAssessment, StrategicMode
from ..services import ensure_planning_year


def _areas(user) -> list[LifeArea]:
    return list(owned(LifeArea, user).filter(is_active=True))


@login_required
@require_http_methods(["GET", "POST"])
def design_life(request, index: int = 1):
    areas = _areas(request.user)
    if not areas:
        messages.info(request, "Add a Life Area first, then design your life around it.")
        return redirect("planning:area_list")
    if not 1 <= index <= len(areas):
        raise Http404
    area = areas[index - 1]
    year = ensure_planning_year(request.user)
    assessment = LifeAreaAssessment.objects.filter(personal_year=year, life_area=area).first()
    suggest_goals = bool(assessment and assessment.strategic_mode == StrategicMode.IMPROVE)
    goal_samples = goal_samples_for(area.template_key) if suggest_goals else []
    existing_goals = list(owned(Goal, request.user).filter(personal_year=year, life_area=area))

    form = NorthLightForm(request.POST or None, instance=area)
    if request.method == "POST" and form.is_valid():
        form.save()
        created = 0
        chosen = {int(i) for i in request.POST.getlist("goal") if i.isdigit()}
        for i, sample in enumerate(goal_samples):
            if i in chosen:
                Goal.objects.create(
                    user=request.user, personal_year=year, life_area=area,
                    title=sample["title"], goal_type=sample["goal_type"], target_unit=sample["target_unit"],
                    description=sample["description"],
                )
                created += 1
        custom = request.POST.get("custom_goal", "").strip()
        if custom:
            Goal.objects.create(user=request.user, personal_year=year, life_area=area,
                                title=custom[:200], goal_type=GoalType.OUTCOME)
            created += 1
        if created:
            messages.success(request, f"{created} goal{'s' if created != 1 else ''} added for {area.name}. "
                                      "Open each one to set its baseline and target.")
        if index < len(areas):
            return redirect("planning:design_life_step", index=index + 1)
        return redirect("planning:design_life_done")

    return render(request, "planning/design/step.html", {
        "area": area, "index": index, "total": len(areas), "progress": int(100 * (index - 1) / len(areas)),
        "year": year, "assessment": assessment, "form": form,
        "suggest_goals": suggest_goals, "goal_samples": goal_samples, "existing_goals": existing_goals,
        "samples_open": not area.north_light,
    })


@login_required
def design_life_done(request):
    year = ensure_planning_year(request.user)
    areas = _areas(request.user)
    goals = list(owned(Goal, request.user).filter(personal_year=year).select_related("life_area"))
    return render(request, "planning/design/done.html", {
        "year": year,
        "with_light": sum(1 for a in areas if a.north_light),
        "total": len(areas),
        "goals": goals,
        "unmeasured": [g for g in goals if g.baseline is None or g.target is None],
    })

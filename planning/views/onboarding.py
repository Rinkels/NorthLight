"""Nine-step onboarding. Every step is skippable, progress is saved on each
POST, and the user can leave and come back — it must not feel like a
45-minute questionnaire.

Steps: 1 welcome · 2 areas · 3 scores · 4 gaps · 5 modes · 6 North Light + Why ·
7 Personal Year · 8 12-month visions · 9 a few goals.
"""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone

from ..access import owned, profile_for
from ..forms import LifeAreaForm, ModeFormSet, NorthLightFormSet, PersonalYearForm, QuickGoalForm, ScoreFormSet, VisionFormSet
from ..models import GOAL_TYPE_HELP, Goal, LifeArea, LifeAreaAssessment, MODE_GUIDANCE, StrategicMode
from ..services import activate_year, ensure_assessments, ensure_default_life_areas, ensure_planning_year, priority_rows, dashboard_data

TOTAL = 9
TITLES = {
    1: "Welcome", 2: "Your Life Areas", 3: "Where am I?", 4: "Priority gaps", 5: "Strategic mode",
    6: "North Light & Why", 7: "Your Personal Year", 8: "12-Month Vision", 9: "A few meaningful goals",
}


def _advance(profile, step: int) -> None:
    profile.onboarding_step = min(TOTAL, step + 1)
    profile.save(update_fields=["onboarding_step"])


def _finish(profile, user) -> None:
    profile.onboarding_complete = True
    profile.onboarding_step = TOTAL
    profile.save(update_fields=["onboarding_complete", "onboarding_step"])
    year = ensure_planning_year(user)
    if year.contains(timezone.localdate()) and not year.is_active:
        activate_year(year)


@login_required
def onboarding(request, step: int):
    if not 1 <= step <= TOTAL:
        raise Http404
    user = request.user
    profile = profile_for(user)
    ctx = {"step": step, "total": TOTAL, "title": TITLES[step], "progress": int(100 * (step - 1) / TOTAL)}

    if request.POST.get("action") == "finish":
        _finish(profile, user)
        messages.success(request, "You're set up. Come back to any of this whenever you like.")
        return redirect("planning:dashboard")

    if step == 1:
        if request.method == "POST":
            ensure_default_life_areas(user)
            ensure_planning_year(user)
            _advance(profile, step)
            return redirect("planning:onboarding", step=2)
        return render(request, "planning/onboarding/step1.html", ctx)

    if step == 2:
        ensure_default_life_areas(user)
        form = LifeAreaForm(request.POST or None) if request.POST.get("action") == "add" else LifeAreaForm()
        if request.method == "POST":
            if request.POST.get("action") == "add" and form.is_valid():
                area = form.save(commit=False)
                area.user = user
                area.sort_order = owned(LifeArea, user).count()
                area.save()
                return redirect("planning:onboarding", step=2)
            if request.POST.get("action") == "archive":
                owned(LifeArea, user).filter(pk=request.POST.get("pk")).update(is_active=False)
                return redirect("planning:onboarding", step=2)
            if request.POST.get("action") == "next":
                _advance(profile, step)
                return redirect("planning:onboarding", step=3)
        ctx.update({"areas": owned(LifeArea, user).filter(is_active=True), "form": form})
        return render(request, "planning/onboarding/step2.html", ctx)

    year = ensure_planning_year(user)
    ensure_assessments(year, source="onboarding")
    assessments = LifeAreaAssessment.objects.filter(personal_year=year).select_related("life_area")

    if step == 3:
        fs = ScoreFormSet(request.POST or None, queryset=assessments)
        if request.method == "POST" and fs.is_valid():
            for f in fs:
                if f.has_changed():
                    f.save().snapshot(source="onboarding")
            _advance(profile, step)
            return redirect("planning:onboarding", step=4)
        ctx["formset"] = fs
        return render(request, "planning/onboarding/step3.html", ctx)

    if step == 4:
        if request.method == "POST":
            _advance(profile, step)
            return redirect("planning:onboarding", step=5)
        ctx["rows"] = priority_rows(dashboard_data(user).rows)
        return render(request, "planning/onboarding/step4.html", ctx)

    if step == 5:
        fs = ModeFormSet(request.POST or None, queryset=assessments)
        if request.method == "POST" and fs.is_valid():
            fs.save()
            _advance(profile, step)
            return redirect("planning:onboarding", step=6)
        ctx.update({"formset": fs, "guidance": MODE_GUIDANCE, "modes": StrategicMode})
        return render(request, "planning/onboarding/step5.html", ctx)

    if step == 6:
        areas = owned(LifeArea, user).filter(is_active=True)
        fs = NorthLightFormSet(request.POST or None, queryset=areas)
        if request.method == "POST" and fs.is_valid():
            fs.save()
            _advance(profile, step)
            return redirect("planning:onboarding", step=7)
        ctx["formset"] = fs
        return render(request, "planning/onboarding/step6.html", ctx)

    if step == 7:
        form = PersonalYearForm(request.POST or None, instance=year)
        if request.method == "POST" and form.is_valid():
            form.save()
            _advance(profile, step)
            return redirect("planning:onboarding", step=8)
        ctx.update({"form": form, "year": year, "profile": profile})
        return render(request, "planning/onboarding/step7.html", ctx)

    if step == 8:
        fs = VisionFormSet(request.POST or None, queryset=assessments)
        if request.method == "POST" and fs.is_valid():
            fs.save()
            _advance(profile, step)
            return redirect("planning:onboarding", step=9)
        ctx["formset"] = fs
        return render(request, "planning/onboarding/step8.html", ctx)

    # step 9
    form = QuickGoalForm(request.POST or None, initial={"personal_year": year}).for_user(user)
    if request.method == "POST" and request.POST.get("action") == "add" and form.is_valid():
        goal = form.save(commit=False)
        goal.user = user
        goal.save()
        return redirect("planning:onboarding", step=9)
    ctx.update({"form": form, "goals": owned(Goal, user).filter(personal_year=year), "type_help": GOAL_TYPE_HELP})
    return render(request, "planning/onboarding/step9.html", ctx)

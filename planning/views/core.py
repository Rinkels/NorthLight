"""Accounts, profile, dashboard, history."""
from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from ..access import owned, profile_for
from ..forms import ProfileForm, ScoreFormSet, SignUpForm
from ..models import LifeArea, LifeAreaAssessment, PersonalYear
from ..services import (
    current_year, dashboard_data, next_review_due, priority_rows, save_changed_scores, score_history, stale_goals,
    stale_habits,
)


@require_http_methods(["GET", "POST"])
def signup(request):
    if request.user.is_authenticated:
        return redirect("planning:dashboard")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        profile_for(user)
        login(request, user)
        return redirect("planning:onboarding", step=1)
    return render(request, "registration/signup.html", {"form": form})


@login_required
def profile(request):
    prof = profile_for(request.user)
    form = ProfileForm(request.POST or None, instance=prof)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Settings saved.")
        return redirect("planning:profile")
    return render(request, "planning/profile.html", {"form": form, "profile": prof})


@login_required
def dashboard(request):
    prof = profile_for(request.user)
    if not prof.onboarding_complete and not owned(LifeArea, request.user).exists():
        return redirect("planning:onboarding", step=prof.onboarding_step or 1)
    data = dashboard_data(request.user)
    scores = ScoreFormSet(prefix="scores", queryset=_score_queryset(data.year)) if data.year else None
    return render(request, "planning/dashboard.html", {
        "data": data,
        "priority": priority_rows(data.rows)[:6],
        "wheel_json": json.dumps(data.wheel),
        "profile": prof,
        "scores": scores if scores is not None and scores.total_form_count() else None,
        "review_due": next_review_due(request.user, data.year),
        "stale_goals": stale_goals(request.user, data.year),
        "stale_habits": stale_habits(request.user),
    })


def _score_queryset(year):
    return (LifeAreaAssessment.objects.filter(personal_year=year, life_area__is_active=True)
            .select_related("life_area").order_by("life_area__sort_order", "life_area_id"))


@login_required
@require_http_methods(["POST"])
def dashboard_scores(request):
    """Update Satisfaction / Importance from the dashboard. Only changed rows
    are saved, and each change is snapshotted so history is never lost."""
    year = current_year(request.user)
    if year is None:
        return redirect("planning:dashboard")
    scores = ScoreFormSet(request.POST, prefix="scores", queryset=_score_queryset(year))
    if scores.is_valid():
        changed = save_changed_scores(scores, year, source="dashboard")
        messages.success(request, f"{changed} score{'s' if changed != 1 else ''} updated." if changed else "No scores changed.")
    else:
        messages.error(request, "Scores could not be saved.")
    return redirect("planning:dashboard")


@login_required
def history(request):
    hist = score_history(request.user)
    chart = {
        "years": [y.title for y in hist["years"]],
        "series": [
            {"label": row["area"].name,
             "data": [c.satisfaction if c else None for c in row["cells"]]}
            for row in hist["areas"]
        ],
    }
    return render(request, "planning/history.html", {"hist": hist, "chart_json": json.dumps(chart)})

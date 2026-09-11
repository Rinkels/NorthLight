"""Accounts, profile, dashboard, history."""
from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from ..access import owned, profile_for
from ..forms import ProfileForm, SignUpForm
from ..models import LifeArea, PersonalYear
from ..services import dashboard_data, priority_rows, score_history


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
    return render(request, "planning/dashboard.html", {
        "data": data,
        "priority": priority_rows(data.rows)[:6],
        "wheel_json": json.dumps(data.wheel),
        "profile": prof,
    })


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

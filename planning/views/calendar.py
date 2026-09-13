"""Month calendar of dated commitments, with a "this week" strip for habits
(which are cadences, not dates, and so never sit on the grid)."""
from __future__ import annotations

import calendar as cal
from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

from ..access import owned
from ..models import Habit, Milestone, OPEN_STATUSES
from ..services import add_months, calendar_items, current_year


@login_required
def calendar_view(request, year: int | None = None, month: int | None = None):
    today = timezone.localdate()
    if year is None:
        year, month = today.year, today.month
    if not (1 <= month <= 12 and 1970 <= year <= 2200):
        raise Http404
    first = date(year, month, 1)
    weeks = cal.Calendar(firstweekday=0).monthdatescalendar(year, month)
    grid_first, grid_last = weeks[0][0], weeks[-1][-1]
    items = calendar_items(request.user, grid_first, grid_last, today)
    prev_m, next_m = add_months(first, -1), add_months(first, 1)
    habits = list(owned(Habit, request.user).filter(is_active=True).select_related("life_area"))
    upcoming = list(
        owned(Milestone, request.user).filter(status__in=OPEN_STATUSES, due_date__range=(today, add_months(today, 1)))
        .select_related("goal", "goal__life_area").order_by("due_date")
    )
    return render(request, "planning/calendar.html", {
        "weeks": [[(d, d.month == month, items.get(d, [])) for d in wk] for wk in weeks],
        "first": first, "prev": prev_m, "next": next_m, "today": today,
        "year_obj": current_year(request.user),
        "habits": habits, "upcoming": upcoming,
        "weekday_names": [cal.day_abbr[i] for i in range(7)],
    })

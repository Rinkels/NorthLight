"""Data export (brief §21): everything a user has entered, in a form they can
keep, move, or read outside NorthLight.

Two shapes:
  * a single JSON document mirroring the domain hierarchy (complete, lossless);
  * flat CSVs for the two things people most often want in a spreadsheet —
    scores per area per year, and goals.

Everything here is scoped through `owned()` so the export can never contain
another user's rows.
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime
from decimal import Decimal

from django.utils import timezone

from .access import owned, profile_for
from .models import (
    Goal, GoalRelationship, Habit, LifeArea, LifeAreaAssessment, PersonalYear, Review,
)

EXPORT_FORMAT_VERSION = 1


def _plain(value):
    """JSON-friendly scalar: dates → ISO strings, Decimals → strings (exact)."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _fields(obj, names: tuple[str, ...]) -> dict:
    return {n: _plain(getattr(obj, n)) for n in names}


PROFILE_FIELDS = ("display_name", "timezone", "year_start_type", "birthday", "custom_year_start",
                  "life_review_date", "review_cadence", "created_at")
AREA_FIELDS = ("id", "name", "description", "sort_order", "is_active", "template_key", "north_light", "why",
               "created_at", "updated_at")
YEAR_FIELDS = ("id", "title", "start_date", "end_date", "status", "foundation_start_date", "notes", "reflection",
               "created_at", "updated_at")
ASSESSMENT_FIELDS = ("id", "life_area_id", "satisfaction", "importance", "priority_gap", "strategic_mode",
                     "annual_vision", "assessment_date", "updated_at")
SNAPSHOT_FIELDS = ("satisfaction", "importance", "strategic_mode", "source", "taken_at")
GOAL_FIELDS = ("id", "life_area_id", "title", "description", "goal_type", "baseline", "target", "target_unit",
               "current_value", "target_date", "status", "priority", "progress_percentage", "notes",
               "completed_date", "created_at", "updated_at")
MILESTONE_FIELDS = ("id", "title", "description", "quarter", "start_date", "due_date", "status",
                    "progress_percentage", "notes", "completed_date", "created_at", "updated_at")
HABIT_FIELDS = ("id", "life_area_id", "goal_id", "title", "frequency_type", "frequency_target", "is_active",
                "created_at")
CHECKIN_FIELDS = ("date", "count")
REVIEW_FIELDS = ("id", "review_type", "review_date", "period_label", "moved_forward", "stalled", "surprised",
                 "attention_next", "no_longer_relevant", "priorities_changed", "north_light_check", "lessons",
                 "major_events", "carry_forward", "notes", "created_at", "updated_at")


def export_user_data(user) -> dict:
    """The complete, user-scoped export as a JSON-serialisable dict."""
    profile = profile_for(user)
    areas = list(owned(LifeArea, user))
    years = list(owned(PersonalYear, user).order_by("start_date"))
    assessments = list(owned(LifeAreaAssessment, user).prefetch_related("snapshots"))
    goals = list(owned(Goal, user).prefetch_related("milestones"))
    links = list(owned(GoalRelationship, user))
    habits = list(owned(Habit, user).prefetch_related("checkins"))
    reviews = list(owned(Review, user))

    supports: dict[int, list[int]] = {}
    for link in links:
        supports.setdefault(link.outcome_goal_id, []).append(link.process_goal_id)

    def year_block(year: PersonalYear) -> dict:
        block = _fields(year, YEAR_FIELDS)
        block["assessments"] = [
            {**_fields(a, ASSESSMENT_FIELDS),
             "snapshots": [_fields(s, SNAPSHOT_FIELDS) for s in a.snapshots.all()]}
            for a in assessments if a.personal_year_id == year.id
        ]
        block["goals"] = [
            {**_fields(g, GOAL_FIELDS),
             "progress": g.progress(),
             "supported_by_goal_ids": supports.get(g.id, []),
             "milestones": [_fields(m, MILESTONE_FIELDS) for m in g.milestones.all()]}
            for g in goals if g.personal_year_id == year.id
        ]
        block["reviews"] = [_fields(r, REVIEW_FIELDS) for r in reviews if r.personal_year_id == year.id]
        return block

    return {
        "format": "northlight-export",
        "format_version": EXPORT_FORMAT_VERSION,
        "exported_at": timezone.now().isoformat(),
        "account": {"username": user.get_username(), "email": user.email},
        "profile": _fields(profile, PROFILE_FIELDS),
        "life_areas": [_fields(a, AREA_FIELDS) for a in areas],
        "personal_years": [year_block(y) for y in years],
        "habits": [
            {**_fields(h, HABIT_FIELDS),
             "checkins": [_fields(c, CHECKIN_FIELDS) for c in h.checkins.all()]}
            for h in habits
        ],
    }


SCORES_HEADER = ["personal_year", "year_start", "year_end", "life_area", "satisfaction", "importance",
                 "priority_gap", "strategic_mode", "annual_vision", "assessment_date"]
GOALS_HEADER = ["personal_year", "life_area", "title", "goal_type", "status", "priority", "baseline", "target",
                "current_value", "target_unit", "progress_pct", "target_date", "completed_date", "description"]


def scores_csv_rows(user) -> list[list]:
    qs = (owned(LifeAreaAssessment, user)
          .select_related("personal_year", "life_area")
          .order_by("personal_year__start_date", "life_area__sort_order"))
    return [SCORES_HEADER] + [
        [a.personal_year.title, a.personal_year.start_date, a.personal_year.end_date, a.life_area.name,
         a.satisfaction, a.importance, a.priority_gap, a.strategic_mode, a.annual_vision, a.assessment_date]
        for a in qs
    ]


def goals_csv_rows(user) -> list[list]:
    qs = (owned(Goal, user).select_related("personal_year", "life_area")
          .order_by("personal_year__start_date", "life_area__sort_order", "priority", "id"))
    return [GOALS_HEADER] + [
        [g.personal_year.title, g.life_area.name, g.title, g.goal_type, g.status, g.get_priority_display(),
         g.baseline, g.target, g.current_value, g.target_unit, g.progress(), g.target_date, g.completed_date,
         g.description]
        for g in qs
    ]


def to_csv(rows: list[list]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in rows:
        writer.writerow(["" if v is None else v for v in row])
    return buf.getvalue()

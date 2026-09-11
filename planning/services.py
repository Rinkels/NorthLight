"""Domain logic that spans models: defaults, Personal Year lifecycle,
dashboard aggregation, history, and the integration seam.

Views stay thin; anything with rules lives here so it can be tested directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from .access import owned, profile_for
from .models import (
    DEFAULT_LIFE_AREAS, Goal, Habit, LifeArea, LifeAreaAssessment, Milestone,
    OPEN_STATUSES, PersonalYear, StrategicMode, UserProfile, WorkStatus,
)


# --------------------------------------------------------------------------- #
# Life areas
# --------------------------------------------------------------------------- #

def ensure_default_life_areas(user) -> list[LifeArea]:
    """Create the ten default areas for a user who has none. Idempotent."""
    if owned(LifeArea, user).exists():
        return list(owned(LifeArea, user))
    return [
        LifeArea.objects.create(user=user, name=name, template_key=key, sort_order=i)
        for i, (key, name) in enumerate(DEFAULT_LIFE_AREAS)
    ]


def restore_default_life_areas(user) -> int:
    """Re-add any default area the user no longer has (matched by template_key)
    and re-activate archived defaults. Never deletes custom areas. Returns the
    number of areas added or re-activated."""
    existing = {a.template_key: a for a in owned(LifeArea, user) if a.template_key}
    changed = 0
    max_order = owned(LifeArea, user).count()
    for i, (key, name) in enumerate(DEFAULT_LIFE_AREAS):
        area = existing.get(key)
        if area is None:
            LifeArea.objects.create(user=user, name=name, template_key=key, sort_order=max_order + i)
            changed += 1
        elif not area.is_active:
            area.is_active = True
            area.save(update_fields=["is_active"])
            changed += 1
    return changed


def reorder_life_areas(user, ordered_ids: list[int]) -> None:
    """Persist a new sort order. Ids not owned by the user are ignored."""
    areas = {a.id: a for a in owned(LifeArea, user)}
    for pos, pk in enumerate(ordered_ids):
        area = areas.get(pk)
        if area is not None and area.sort_order != pos:
            area.sort_order = pos
            area.save(update_fields=["sort_order"])


# --------------------------------------------------------------------------- #
# Personal Years
# --------------------------------------------------------------------------- #

def default_year_bounds(profile: UserProfile, today: date | None = None) -> tuple[date, date, str]:
    """(start, end, title) for the Personal Year that contains `today`, per the
    profile's start-type preference. Calendar type → Jan 1 – Dec 31."""
    today = today or timezone.localdate()
    next_start = profile.next_year_start(today)
    # The current year started one "year" before the next start.
    start = _shift_year(next_start, -1)
    end = next_start - timedelta(days=1)
    title = f"{end.year} Personal Year" if profile.year_start_type == UserProfile.YEAR_CALENDAR \
        else f"{start.year}–{end.year} Personal Year"
    if start.year == end.year:
        title = f"{end.year} Personal Year"
    return start, end, title


def _shift_year(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # Feb 29
        return d.replace(year=d.year + years, day=28)


def current_year(user) -> PersonalYear | None:
    """The Active year, else the most recent Planning year, else None."""
    qs = owned(PersonalYear, user)
    return (qs.filter(status=PersonalYear.STATUS_ACTIVE).first()
            or qs.filter(status=PersonalYear.STATUS_PLANNING).order_by("-start_date").first())


def ensure_planning_year(user) -> PersonalYear:
    """Return the current year, creating a default Planning year if none exists
    (used at onboarding so assessments have a year to hang on)."""
    year = current_year(user)
    if year:
        return year
    start, end, title = default_year_bounds(profile_for(user))
    return PersonalYear.objects.create(user=user, title=title, start_date=start, end_date=end)


@transaction.atomic
def activate_year(year: PersonalYear) -> PersonalYear:
    """Make `year` the single Active year; any other Active year becomes Completed."""
    owned(PersonalYear, year.user).filter(status=PersonalYear.STATUS_ACTIVE).exclude(pk=year.pk) \
        .update(status=PersonalYear.STATUS_COMPLETED)
    year.status = PersonalYear.STATUS_ACTIVE
    year.save(update_fields=["status"])
    return year


def ensure_assessments(year: PersonalYear, source: str = "") -> list[LifeAreaAssessment]:
    """Guarantee one assessment per active area for the year. New rows start at
    5/5 (neutral) — or carry the user's most recent scores for that area — and
    get an initial snapshot. Existing rows are untouched."""
    out = []
    for area in owned(LifeArea, year.user).filter(is_active=True):
        assessment = LifeAreaAssessment.objects.filter(personal_year=year, life_area=area).first()
        if assessment is None:
            prev = (LifeAreaAssessment.objects.filter(life_area=area).exclude(personal_year=year)
                    .order_by("-personal_year__start_date").first())
            assessment = LifeAreaAssessment.objects.create(
                user=year.user, personal_year=year, life_area=area,
                satisfaction=prev.satisfaction if prev else 5,
                importance=prev.importance if prev else 5,
                strategic_mode=prev.strategic_mode if prev else StrategicMode.MAINTAIN,
            )
            assessment.snapshot(source=source or "created")
        out.append(assessment)
    return out


@transaction.atomic
def create_next_year(previous: PersonalYear, carry_goal_ids: list[int] | None = None) -> PersonalYear:
    """Create the following Personal Year from a completed one. Assessments are
    seeded from the previous year's END scores (so history is preserved as
    separate rows); goals are NOT copied automatically — only the ids the user
    explicitly chose are carried forward (as fresh, not-started goals)."""
    length = previous.length_days
    start = previous.end_date + timedelta(days=1)
    end = start + timedelta(days=length - 1)
    title = f"{end.year} Personal Year" if start.year == end.year else f"{start.year}–{end.year} Personal Year"
    nxt = PersonalYear.objects.create(user=previous.user, title=title, start_date=start, end_date=end)
    ensure_assessments(nxt, source="carried from previous year")
    for goal in owned(Goal, previous.user).filter(personal_year=previous, pk__in=carry_goal_ids or []):
        Goal.objects.create(
            user=previous.user, personal_year=nxt, life_area=goal.life_area,
            title=goal.title, description=goal.description, goal_type=goal.goal_type,
            baseline=goal.current_value if goal.current_value is not None else goal.baseline,
            target=goal.target, target_unit=goal.target_unit, priority=goal.priority,
            notes=f"Carried forward from {previous.title}.",
        )
    return nxt


# --------------------------------------------------------------------------- #
# Dashboard aggregation
# --------------------------------------------------------------------------- #

@dataclass
class AreaRow:
    area: LifeArea
    assessment: LifeAreaAssessment | None
    goals: list[Goal]

    @property
    def gap(self) -> int | None:
        return self.assessment.priority_gap if self.assessment else None

    @property
    def open_goal_count(self) -> int:
        return sum(1 for g in self.goals if g.is_open)

    @property
    def avg_progress(self) -> int | None:
        """Mean goal progress for the area, or None when it has no goals —
        an area with no goals (Protect, Maintain) is not "at 0%"."""
        if not self.goals:
            return None
        return int(round(sum(g.progress() for g in self.goals) / len(self.goals)))


@dataclass
class DashboardData:
    year: PersonalYear | None
    rows: list[AreaRow]
    goals_total: int
    goals_done: int
    milestones: list[Milestone]
    habits: list[Habit]
    improve_count: int
    protect_count: int

    @property
    def wheel(self) -> dict:
        """Chart-ready series for the Life Wheel (radar)."""
        return {
            "labels": [r.area.name for r in self.rows],
            "ids": [r.area.id for r in self.rows],
            "satisfaction": [r.assessment.satisfaction if r.assessment else 0 for r in self.rows],
            "importance": [r.assessment.importance if r.assessment else 0 for r in self.rows],
            "mode": [r.assessment.get_strategic_mode_display() if r.assessment else "" for r in self.rows],
            # Goal execution rides along for the tooltip only — never as a ring.
            "goals": [len(r.goals) for r in self.rows],
            "open": [r.open_goal_count for r in self.rows],
            "progress": [r.avg_progress for r in self.rows],
        }


def dashboard_data(user) -> DashboardData:
    year = current_year(user)
    areas = list(owned(LifeArea, user).filter(is_active=True))
    assessments = {a.life_area_id: a for a in LifeAreaAssessment.objects.filter(personal_year=year)} if year else {}
    goals = list(owned(Goal, user).filter(personal_year=year).select_related("life_area")) if year else []
    by_area: dict[int, list[Goal]] = {}
    for g in goals:
        by_area.setdefault(g.life_area_id, []).append(g)
    rows = [AreaRow(area=a, assessment=assessments.get(a.id), goals=by_area.get(a.id, [])) for a in areas]
    milestones = list(
        owned(Milestone, user).filter(goal__personal_year=year, status__in=OPEN_STATUSES)
        .select_related("goal", "goal__life_area").order_by("due_date")[:8]
    ) if year else []
    habits = list(owned(Habit, user).filter(is_active=True).select_related("life_area"))
    modes = [r.assessment.strategic_mode for r in rows if r.assessment]
    return DashboardData(
        year=year, rows=rows,
        goals_total=len(goals),
        goals_done=sum(1 for g in goals if g.status == WorkStatus.COMPLETE),
        milestones=milestones, habits=habits,
        improve_count=modes.count(StrategicMode.IMPROVE),
        protect_count=modes.count(StrategicMode.PROTECT),
    )


def priority_rows(rows: list[AreaRow]) -> list[AreaRow]:
    """Areas ordered by priority gap (descending), then importance. A signal to
    read, not an instruction to fix everything with a positive gap."""
    scored = [r for r in rows if r.assessment]
    return sorted(scored, key=lambda r: (-(r.gap or 0), -r.assessment.importance, r.area.sort_order))


# --------------------------------------------------------------------------- #
# History
# --------------------------------------------------------------------------- #

def score_history(user) -> dict:
    """{'years': [PersonalYear...], 'areas': [{'area': LifeArea, 'scores': [ (sat, imp) | None per year ]}]}
    Uses the assessment row per year — never overwritten — so trends are real."""
    years = list(owned(PersonalYear, user).order_by("start_date"))
    areas = list(owned(LifeArea, user))
    lookup = {(a.personal_year_id, a.life_area_id): a
              for a in LifeAreaAssessment.objects.filter(personal_year__in=years)}
    out_areas = []
    for area in areas:
        cells = [lookup.get((y.id, area.id)) for y in years]
        if any(cells):
            out_areas.append({"area": area, "cells": cells})
    return {"years": years, "areas": out_areas}


def start_vs_end(year: PersonalYear) -> list[dict]:
    """For an annual review: first snapshot vs current scores per area."""
    out = []
    for a in LifeAreaAssessment.objects.filter(personal_year=year).select_related("life_area"):
        first = a.snapshots.order_by("taken_at").first()
        out.append({
            "area": a.life_area,
            "start_satisfaction": first.satisfaction if first else a.satisfaction,
            "start_importance": first.importance if first else a.importance,
            "end_satisfaction": a.satisfaction,
            "end_importance": a.importance,
            "delta": a.satisfaction - (first.satisfaction if first else a.satisfaction),
        })
    return out


# --------------------------------------------------------------------------- #
# Integration seam (Phase 2: gym2x health, fracto finance — via API only)
# --------------------------------------------------------------------------- #

class ValueProvider:
    """Interface for a future external source of a goal's current value.
    V1 ships only manual entry; a HealthProvider/FinanceProvider would call an
    external API as the user, never a shared database, and return a Decimal.
    Registering one here is the only change needed — models are untouched."""

    key = "manual"

    def fetch(self, goal: Goal) -> Decimal | None:  # pragma: no cover - interface
        return None


PROVIDERS: dict[str, ValueProvider] = {}


def update_goal_value(goal: Goal, value: Decimal | None, *, provider: str = "manual") -> Goal:
    """Single choke point for changing a goal's current value, whether typed by
    the user or (later) fetched from a provider."""
    goal.current_value = value
    if goal.has_measure and value is not None and goal.progress() >= 100 and goal.is_open:
        goal.status = WorkStatus.COMPLETE
    goal.save()
    return goal

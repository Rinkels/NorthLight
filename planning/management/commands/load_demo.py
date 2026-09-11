"""Load the example profile from the product brief (§23) for development.

    python manage.py load_demo                 # creates user "demo" / password "demo-northlight"
    python manage.py load_demo --username me   # seed into an existing/new user
    python manage.py load_demo --reset         # wipe that user's planning data first

Refuses to run when DEBUG is False so it can never seed production.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from planning.access import profile_for
from planning.models import (
    Goal, GoalRelationship, GoalType, Habit, HabitCheckin, LifeArea, LifeAreaAssessment, Milestone,
    PersonalYear, Review, ReviewType, StrategicMode, WorkStatus,
)
from planning.services import ensure_assessments, ensure_default_life_areas

# template_key -> (satisfaction, importance, mode)
SCORES = {
    "health": (7, 7, StrategicMode.PROTECT),
    "relationships": (5, 6, StrategicMode.IMPROVE),
    "friends": (5, 4, StrategicMode.MAINTAIN),
    "work": (5, 7, StrategicMode.IMPROVE),
    "finance": (5, 7, StrategicMode.IMPROVE),
    "time": (7, 6, StrategicMode.PROTECT),
    "learning": (8, 5, StrategicMode.MAINTAIN),
    "creating": (9, 6, StrategicMode.PROTECT),   # "Protect / Focus"
    "fun": (4, 4, StrategicMode.EXPLORE),
    "purpose": (7, 5, StrategicMode.MAINTAIN),
}
# Previous year, so History has a trend to show.
PREVIOUS = {"health": (6, 7), "relationships": (5, 6), "friends": (5, 4), "work": (4, 7), "finance": (4, 7),
            "time": (6, 6), "learning": (7, 5), "creating": (8, 6), "fun": (4, 4), "purpose": (6, 5)}

NORTH_LIGHTS = {
    "health": ("Remain healthy, capable and energetic enough that age does not unnecessarily restrict what I can do.", "Freedom and independence."),
    "finance": ("Build enough financial independence that paid work increasingly becomes a choice rather than a requirement.", "Choice and control over my time."),
    "work": ("Do interesting, useful and intellectually challenging work with considerable autonomy.", "Autonomy and mastery."),
    "creating": ("Regularly turn ideas into real things.", "Expression, curiosity and the enjoyment of building."),
    "relationships": ("Stay genuinely close to the people who matter most.", "Connection with people who matter."),
}
VISIONS = {
    "work": "Most of my paid work is interesting, technically challenging and largely self-directed.",
    "finance": "I have increased my invested assets and proved at least one source of recurring income that does not depend directly on selling another hour of my time.",
    "relationships": "I feel noticeably closer to the people who matter most and we have deliberately created shared experiences.",
}
GOALS = [
    # (area, title, type, baseline, target, unit, current, priority)
    ("health", "Run 5K in 25:00 or less", GoalType.OUTCOME, Decimal("29"), Decimal("25"), "minutes", Decimal("27.5"), 1),
    ("health", "Complete three running/training sessions per week", GoalType.PROCESS, None, None, "", None, 2),
    ("relationships", "Complete one meaningful family trip", GoalType.EXPERIENCE, None, None, "", None, 1),
    ("relationships", "Establish one recurring family activity", GoalType.PROCESS, None, None, "", None, 2),
    ("work", "Move ≥30% of paid work toward preferred professional work", GoalType.OUTCOME, Decimal("10"), Decimal("30"), "%", Decimal("15"), 1),
    ("finance", "Reach $200,000 invested", GoalType.OUTCOME, Decimal("150000"), Decimal("200000"), "$", Decimal("168000"), 1),
    ("finance", "Build independent income ≥ $500/month for three consecutive months", GoalType.OUTCOME, Decimal("0"), Decimal("3"), "months", Decimal("0"), 1),
    ("finance", "Invest a fixed amount every month", GoalType.PROCESS, None, None, "", None, 2),
    ("time", "Protect one substantial free day or two half-days per week", GoalType.MAINTENANCE, None, None, "", None, 2),
    ("creating", "Advance one flagship personal project to a major real-world milestone", GoalType.OUTCOME, None, None, "", None, 1),
    ("fun", "Complete four memorable experiences", GoalType.EXPERIENCE, Decimal("0"), Decimal("4"), "experiences", Decimal("1"), 2),
]
LINKS = [("Run 5K in 25:00 or less", "Complete three running/training sessions per week"),
         ("Reach $200,000 invested", "Invest a fixed amount every month")]
MILESTONES = {
    "Run 5K in 25:00 or less": [("Establish baseline 5K time", WorkStatus.COMPLETE, 100), ("Follow first 12-week training cycle", WorkStatus.IN_PROGRESS, 40)],
    "Build independent income ≥ $500/month for three consecutive months": [("Select one income experiment", WorkStatus.COMPLETE, 100), ("Launch it", WorkStatus.IN_PROGRESS, 30), ("Earn the first dollar", WorkStatus.NOT_STARTED, 0)],
    "Move ≥30% of paid work toward preferred professional work": [("Identify the three kinds of work I want to be known for", WorkStatus.IN_PROGRESS, 60)],
    "Complete one meaningful family trip": [("Agree destination and date", WorkStatus.COMPLETE, 100), ("Establish approximate budget", WorkStatus.IN_PROGRESS, 50), ("Book major travel", WorkStatus.NOT_STARTED, 0)],
}
HABITS = [
    ("health", "Run 3 times per week", "times_per_week", 3, "Complete three running/training sessions per week"),
    ("finance", "Invest monthly", "monthly", 1, "Invest a fixed amount every month"),
    ("relationships", "Family outing once per month", "monthly", 1, None),
    ("finance", "Spend four hours/week building an independent income asset", "weekly", 1, None),
    ("time", "Protect Friday afternoon as unscheduled time", "weekly", 1, None),
]


class Command(BaseCommand):
    help = "Load the NorthLight demo profile (development only)."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo")
        parser.add_argument("--password", default="demo-northlight")
        parser.add_argument("--reset", action="store_true", help="Delete the user's existing planning data first.")

    @transaction.atomic
    def handle(self, *args, **opts):
        if not settings.DEBUG:
            raise CommandError("load_demo only runs with DEBUG=True (development).")
        User = get_user_model()
        user, created = User.objects.get_or_create(username=opts["username"], defaults={"email": f"{opts['username']}@example.com"})
        if created:
            user.set_password(opts["password"])
            user.save()
        if opts["reset"]:
            for model in (Review, Habit, Milestone, Goal, LifeAreaAssessment, PersonalYear, LifeArea):
                model.objects.filter(user=user).delete()
        profile = profile_for(user)
        profile.display_name = "Demo"
        profile.onboarding_complete = True
        profile.onboarding_step = 9
        profile.save()

        areas = {a.template_key: a for a in ensure_default_life_areas(user)}
        for key, (nl, why) in NORTH_LIGHTS.items():
            areas[key].north_light, areas[key].why = nl, why
            areas[key].save(update_fields=["north_light", "why"])

        today = timezone.localdate()
        this_year = PersonalYear.objects.filter(user=user, status=PersonalYear.STATUS_ACTIVE).first()
        if this_year is None:
            prev = PersonalYear.objects.create(
                user=user, title=f"{today.year - 1} Personal Year", start_date=date(today.year - 1, 1, 1),
                end_date=date(today.year - 1, 12, 31), status=PersonalYear.STATUS_COMPLETED,
                reflection="A year of laying groundwork. Health held; work and money need deliberate attention.",
            )
            for key, (s, i) in PREVIOUS.items():
                LifeAreaAssessment.objects.create(user=user, personal_year=prev, life_area=areas[key], satisfaction=s, importance=i,
                                                  strategic_mode=SCORES[key][2], assessment_date=prev.start_date).snapshot("demo")
            this_year = PersonalYear.objects.create(
                user=user, title=f"{today.year} Personal Year", start_date=date(today.year, 1, 1),
                end_date=date(today.year, 12, 31), status=PersonalYear.STATUS_ACTIVE,
                foundation_start_date=date(today.year - 1, 9, 1),
            )
        ensure_assessments(this_year, source="demo")
        for key, (s, i, mode) in SCORES.items():
            a = LifeAreaAssessment.objects.get(personal_year=this_year, life_area=areas[key])
            a.satisfaction, a.importance, a.strategic_mode = s, i, mode
            a.annual_vision = VISIONS.get(key, "")
            a.save()
            # Start-of-year snapshot at the previous year's end scores, then "now".
            a.snapshots.all().delete()
            ps, pi = PREVIOUS[key]
            snap = a.snapshot("demo start")
            snap.satisfaction, snap.importance, snap.taken_at = ps, pi, timezone.now() - timedelta(days=200)
            snap.save()
            a.snapshot("demo now")

        goals: dict[str, Goal] = {}
        for area_key, title, gtype, base, target, unit, current, prio in GOALS:
            g, _ = Goal.objects.get_or_create(user=user, personal_year=this_year, title=title, defaults={
                "life_area": areas[area_key], "goal_type": gtype, "baseline": base, "target": target,
                "target_unit": unit, "current_value": current, "priority": prio,
                "status": WorkStatus.IN_PROGRESS, "target_date": this_year.end_date,
            })
            goals[title] = g
        for outcome, process in LINKS:
            GoalRelationship.objects.get_or_create(outcome_goal=goals[outcome], process_goal=goals[process])
        q = this_year.quarter_for(today) or 1
        for goal_title, items in MILESTONES.items():
            for title, status, pct in items:
                Milestone.objects.get_or_create(user=user, goal=goals[goal_title], title=title, defaults={
                    "status": status, "progress_percentage": pct, "quarter": q,
                    "due_date": today + timedelta(days=45)})
        for area_key, title, ftype, target, goal_title in HABITS:
            h, _ = Habit.objects.get_or_create(user=user, title=title, defaults={
                "life_area": areas[area_key], "frequency_type": ftype, "frequency_target": target,
                "goal": goals.get(goal_title)})
            for d in (today - timedelta(days=1), today - timedelta(days=3)):
                HabitCheckin.objects.get_or_create(habit=h, date=d)
        Review.objects.get_or_create(user=user, personal_year=this_year, review_type=ReviewType.MONTHLY,
                                     period_label=(today.replace(day=1) - timedelta(days=1)).strftime("%B %Y"), defaults={
            "moved_forward": "Baseline 5K done (29:10). Income experiment chosen.",
            "stalled": "Family trip budget — nobody owns it yet.",
            "surprised": "How much Friday afternoons matter once protected.",
            "attention_next": "Launch the income experiment; agree the trip budget.",
        })
        self.stdout.write(self.style.SUCCESS(
            f"Demo data loaded for '{user.username}'" + (f" (password: {opts['password']})" if created else "") + "."
        ))

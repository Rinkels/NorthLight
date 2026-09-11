"""Calculations and lifecycle rules."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from planning.models import (
    Goal, GoalType, Habit, HabitCheckin, LifeArea, LifeAreaAssessment, Milestone, PersonalYear, StrategicMode,
    UserProfile, WorkStatus,
)
from planning.services import activate_year, ensure_assessments

from .utils import Setup


class PriorityGapTests(TestCase):
    def test_gap_examples_from_brief(self):
        s = Setup("gap")
        a = s.assessment
        for sat, imp, expected in ((5, 7, 2), (7, 7, 0), (9, 6, -3)):
            a.satisfaction, a.importance = sat, imp
            self.assertEqual(a.priority_gap, expected)

    def test_snapshot_preserves_history(self):
        s = Setup("snap")
        a = s.assessment
        before = a.snapshots.count()
        a.satisfaction = 8
        a.save()
        a.snapshot("review")
        self.assertEqual(a.snapshots.count(), before + 1)
        first = a.snapshots.order_by("taken_at").first()
        self.assertEqual(first.satisfaction, 5)   # original 5/5 from ensure_assessments
        self.assertEqual(a.snapshots.order_by("taken_at").last().satisfaction, 8)


class PersonalYearTests(TestCase):
    def test_dates_and_progress(self):
        s = Setup("py")
        y = PersonalYear.objects.create(user=s.user, title="T", start_date=date(2027, 1, 1), end_date=date(2027, 12, 31))
        self.assertEqual(y.length_days, 365)
        self.assertEqual(y.days_remaining(date(2027, 12, 1)), 30)
        self.assertEqual(y.days_remaining(date(2028, 6, 1)), 0)
        self.assertTrue(y.contains(date(2027, 6, 1)))
        self.assertFalse(y.contains(date(2026, 12, 31)))
        self.assertEqual(y.quarter_for(date(2027, 1, 15)), 1)
        self.assertEqual(y.quarter_for(date(2027, 12, 15)), 4)
        self.assertIsNone(y.quarter_for(date(2028, 1, 1)))
        self.assertEqual(y.progress_pct(date(2027, 1, 1)), 0)
        self.assertEqual(y.progress_pct(date(2028, 1, 1)), 100)

    def test_foundation_period(self):
        s = Setup("fp")
        y = PersonalYear.objects.create(user=s.user, title="T", start_date=date(2027, 1, 1), end_date=date(2027, 12, 31),
                                        foundation_start_date=date(2026, 9, 1))
        self.assertTrue(y.in_foundation(date(2026, 10, 1)))
        self.assertFalse(y.in_foundation(date(2027, 2, 1)))
        self.assertFalse(y.in_foundation(date(2026, 8, 1)))

    def test_end_must_be_after_start(self):
        s = Setup("bad")
        with self.assertRaises(IntegrityError), transaction.atomic():
            PersonalYear.objects.create(user=s.user, title="X", start_date=date(2027, 5, 1), end_date=date(2027, 1, 1))

    def test_only_one_active_year_per_user(self):
        s = Setup("one")  # already has an active year
        other = PersonalYear.objects.create(user=s.user, title="Next", start_date=date(2030, 1, 1), end_date=date(2030, 12, 31))
        with self.assertRaises(IntegrityError), transaction.atomic():
            other.status = PersonalYear.STATUS_ACTIVE
            other.save()
        activate_year(other)
        s.year.refresh_from_db(); other.refresh_from_db()
        self.assertEqual(other.status, PersonalYear.STATUS_ACTIVE)
        self.assertEqual(s.year.status, PersonalYear.STATUS_COMPLETED)
        # A different user can still have their own active year.
        t = Setup("two")
        self.assertEqual(t.year.status, PersonalYear.STATUS_ACTIVE)

    def test_next_year_start_by_type(self):
        s = Setup("nxt")
        p = UserProfile.objects.get(user=s.user)
        self.assertEqual(p.next_year_start(date(2026, 9, 11)), date(2027, 1, 1))
        p.year_start_type, p.birthday = UserProfile.YEAR_BIRTHDAY, date(1980, 3, 15)
        self.assertEqual(p.next_year_start(date(2026, 9, 11)), date(2027, 3, 15))
        self.assertEqual(p.next_year_start(date(2027, 3, 1)), date(2027, 3, 15))
        p.year_start_type, p.custom_year_start = UserProfile.YEAR_CUSTOM, date(2000, 2, 29)
        self.assertEqual(p.next_year_start(date(2027, 1, 1)), date(2027, 2, 28))  # non-leap fallback


class GoalTests(TestCase):
    def test_progress_interpolates_between_baseline_and_target(self):
        s = Setup("g1")
        g = s.goal  # 0 -> 10, current 4
        self.assertEqual(g.progress(), 40)
        g.current_value = Decimal("12")
        self.assertEqual(g.progress(), 100)  # clamped
        g.current_value = Decimal("-1")
        self.assertEqual(g.progress(), 0)

    def test_progress_for_decreasing_target(self):
        s = Setup("g2")
        g = Goal.objects.create(user=s.user, personal_year=s.year, life_area=s.area, title="5K",
                                baseline=Decimal("29"), target=Decimal("25"), current_value=Decimal("27"))
        self.assertEqual(g.progress(), 50)

    def test_manual_progress_when_no_measure(self):
        s = Setup("g3")
        g = Goal.objects.create(user=s.user, personal_year=s.year, life_area=s.area, title="Trip", progress_percentage=35)
        self.assertEqual(g.progress(), 35)

    def test_complete_sets_100_and_completion_date(self):
        s = Setup("g4")
        g = s.goal
        g.status = WorkStatus.COMPLETE
        g.save()
        self.assertEqual(g.progress(), 100)
        self.assertIsNotNone(g.completed_date)
        g.status = WorkStatus.IN_PROGRESS
        g.save()
        self.assertIsNone(g.completed_date)

    def test_milestone_progress_and_completion(self):
        s = Setup("g5")
        m = s.milestone
        m.progress_percentage = 60
        self.assertEqual(m.progress(), 60)
        m.status = WorkStatus.COMPLETE
        m.save()
        self.assertEqual(m.progress(), 100)
        self.assertIsNotNone(m.completed_date)


class HabitTests(TestCase):
    def test_weekly_period_and_completion(self):
        s = Setup("h1")
        h = s.habit  # weekly, target 1
        today = date(2026, 9, 9)  # a Wednesday
        start, end = h.period_bounds(today)
        self.assertEqual((start.weekday(), (end - start).days), (0, 6))
        self.assertFalse(h.period_done(today))
        HabitCheckin.objects.create(habit=h, date=today)
        self.assertTrue(h.period_done(today))

    def test_times_per_week_counts(self):
        s = Setup("h2")
        h = Habit.objects.create(user=s.user, life_area=s.area, title="Run", frequency_type="times_per_week", frequency_target=3)
        today = date(2026, 9, 9)
        HabitCheckin.objects.create(habit=h, date=today, count=2)
        self.assertEqual(h.period_count(today), 2)
        self.assertFalse(h.period_done(today))
        HabitCheckin.objects.create(habit=h, date=today - timedelta(days=1))
        self.assertTrue(h.period_done(today))

    def test_monthly_bounds(self):
        s = Setup("h3")
        h = Habit.objects.create(user=s.user, life_area=s.area, title="Invest", frequency_type="monthly")
        self.assertEqual(h.period_bounds(date(2026, 2, 10)), (date(2026, 2, 1), date(2026, 2, 28)))

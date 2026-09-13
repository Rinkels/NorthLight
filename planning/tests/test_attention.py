"""Review cadence prompts and staleness: questions, never verdicts."""
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from planning.models import Goal, HabitCheckin, Review, ReviewType, UserProfile, WorkStatus
from planning.services import add_months, next_review_due, stale_goals, stale_habits

from .utils import Setup


class ReviewDueTests(TestCase):
    def setUp(self):
        self.s = Setup("alice")
        self.year = self.s.year
        self.start = self.year.start_date
        Review.objects.filter(user=self.s.user).delete()  # Setup adds one monthly review

    def test_add_months_clamps_day(self):
        self.assertEqual(add_months(date(2026, 1, 31), 1), date(2026, 2, 28))
        self.assertEqual(add_months(date(2026, 11, 15), 3), date(2027, 2, 15))

    def test_first_monthly_review_due_one_month_after_year_start(self):
        due = next_review_due(self.s.user, self.year, today=self.start + timedelta(days=10))
        self.assertEqual(due.kind, ReviewType.MONTHLY)
        self.assertEqual(due.due_date, add_months(self.start, 1))
        self.assertFalse(due.show)  # 20 days away
        overdue = next_review_due(self.s.user, self.year, today=add_months(self.start, 1) + timedelta(days=3))
        self.assertTrue(overdue.is_overdue); self.assertEqual(overdue.days_overdue, 3)

    def test_next_due_follows_last_review(self):
        Review.objects.create(user=self.s.user, personal_year=self.year, review_type=ReviewType.MONTHLY,
                              review_date=self.start + timedelta(days=40))
        due = next_review_due(self.s.user, self.year, today=self.start + timedelta(days=50))
        self.assertEqual(due.due_date, add_months(self.start + timedelta(days=40), 1))

    def test_quarterly_cadence(self):
        UserProfile.objects.filter(user=self.s.user).update(review_cadence=UserProfile.CADENCE_QUARTERLY)
        due = next_review_due(self.s.user, self.year, today=self.start + timedelta(days=5))
        self.assertEqual(due.kind, ReviewType.QUARTERLY)
        self.assertEqual(due.due_date, add_months(self.start, 3))

    def test_annual_review_due_at_year_end_then_nothing(self):
        Review.objects.create(user=self.s.user, personal_year=self.year, review_type=ReviewType.MONTHLY,
                              review_date=self.year.end_date - timedelta(days=10))
        due = next_review_due(self.s.user, self.year, today=self.year.end_date)
        self.assertEqual(due.kind, ReviewType.ANNUAL); self.assertEqual(due.due_date, self.year.end_date)
        Review.objects.create(user=self.s.user, personal_year=self.year, review_type=ReviewType.ANNUAL,
                              review_date=self.year.end_date)
        self.assertIsNone(next_review_due(self.s.user, self.year, today=self.year.end_date))

    def test_no_year_or_before_start(self):
        self.assertIsNone(next_review_due(self.s.user, None))
        self.assertIsNone(next_review_due(self.s.user, self.year, today=self.start - timedelta(days=1)))


class StalenessTests(TestCase):
    def setUp(self):
        self.s = Setup("alice")
        self.b = Setup("bob")

    def _age(self, goal, days):
        Goal.objects.filter(pk=goal.pk).update(updated_at=timezone.now() - timedelta(days=days))

    def test_goal_becomes_stale_after_six_weeks_and_only_when_open(self):
        self.assertEqual(stale_goals(self.s.user, self.s.year), [])
        self._age(self.s.goal, 45)
        stale = stale_goals(self.s.user, self.s.year)
        self.assertEqual([x.goal for x in stale], [self.s.goal]); self.assertEqual(stale[0].days, 45)
        Goal.objects.filter(pk=self.s.goal.pk).update(status=WorkStatus.PAUSED)
        self.assertEqual(stale_goals(self.s.user, self.s.year), [])
        self._age(self.b.goal, 60)
        self.assertNotIn(self.b.goal, [x.goal for x in stale_goals(self.s.user, self.s.year)])

    def test_habit_staleness(self):
        h = self.s.habit
        self.assertEqual(stale_habits(self.s.user), [])  # created just now
        from planning.models import Habit
        Habit.objects.filter(pk=h.pk).update(created_at=timezone.now() - timedelta(days=20))
        self.assertEqual([x.habit for x in stale_habits(self.s.user)], [h])
        self.assertIsNone(stale_habits(self.s.user)[0].days)
        HabitCheckin.objects.create(habit=h, date=timezone.localdate() - timedelta(days=16))
        self.assertEqual(stale_habits(self.s.user)[0].days, 16)
        HabitCheckin.objects.create(habit=h, date=timezone.localdate())
        self.assertEqual(stale_habits(self.s.user), [])

    def test_dashboard_shows_drifting_and_status_actions_work(self):
        self.client.login(username="alice", password="pw-123456")
        self._age(self.s.goal, 50)
        resp = self.client.get(reverse("planning:dashboard"))
        self.assertContains(resp, "Drifting"); self.assertContains(resp, "not updated for 50 days")
        resp = self.client.post(reverse("planning:goal_status", args=[self.s.goal.pk]),
                                {"status": "paused", "next": reverse("planning:dashboard")})
        self.assertRedirects(resp, reverse("planning:dashboard"), fetch_redirect_response=False)
        self.s.goal.refresh_from_db(); self.assertEqual(self.s.goal.status, WorkStatus.PAUSED)
        self.assertNotContains(self.client.get(reverse("planning:dashboard")), "Drifting")

    def test_goal_list_marks_stale(self):
        self.client.login(username="alice", password="pw-123456")
        self._age(self.s.goal, 50)
        self.assertContains(self.client.get(reverse("planning:goal_list")), "not updated since")

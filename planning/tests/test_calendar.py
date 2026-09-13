"""Calendar: dated items only, own rows only."""
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from planning.models import Goal, UserProfile
from planning.services import calendar_items

from .utils import Setup


class CalendarTests(TestCase):
    def setUp(self):
        self.a = Setup("alice")
        self.b = Setup("bob")
        self.client.login(username="alice", password="pw-123456")

    def test_items_are_own_and_keyed_by_day(self):
        due = self.a.milestone.due_date
        items = calendar_items(self.a.user, due - timedelta(days=40), due + timedelta(days=40))
        labels = [i.label for day in items.values() for i in day]
        self.assertIn("alice milestone", labels)
        self.assertNotIn("bob milestone", labels)
        self.assertIn("Monthly Review", labels)  # Setup's review, dated today
        self.assertEqual(items[due][0].url, reverse("planning:goal_detail", args=[self.a.goal.pk]))

    def test_goal_target_year_bounds_and_life_review(self):
        Goal.objects.filter(pk=self.a.goal.pk).update(target_date=date(2026, 5, 20))
        UserProfile.objects.filter(user=self.a.user).update(life_review_date=date(1990, 5, 3))
        items = calendar_items(self.a.user, date(2026, 5, 1), date(2026, 5, 31), today=date(2026, 5, 10))
        self.assertEqual(items[date(2026, 5, 20)][0].kind, "goal")
        self.assertEqual(items[date(2026, 5, 3)][0].kind, "life_review")
        jan = calendar_items(self.a.user, date(self.a.year.start_date.year, 1, 1), date(self.a.year.start_date.year, 1, 31))
        self.assertTrue(any(i.kind == "year" for i in jan.get(self.a.year.start_date, [])))

    def test_page_renders_month_and_navigation(self):
        resp = self.client.get(reverse("planning:calendar_month", args=[2026, 5]))
        self.assertContains(resp, "May 2026")
        self.assertContains(resp, reverse("planning:calendar_month", args=[2026, 4]))
        self.assertContains(resp, reverse("planning:calendar_month", args=[2026, 6]))
        self.assertContains(resp, "alice habit")  # week strip
        self.assertNotContains(resp, "bob")
        self.assertEqual(self.client.get(reverse("planning:calendar_month", args=[2026, 13])).status_code, 404)

    def test_anonymous_redirected(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("planning:calendar")).status_code, 302)

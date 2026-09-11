"""User A must never see or change User B's data — GET and POST/update/delete.
Anonymous users must not reach private pages."""
from django.test import TestCase
from django.urls import reverse

from planning.models import Goal, Habit, HabitCheckin, LifeArea, Milestone, PersonalYear, Review

from .utils import Setup


class CrossUserAccessTests(TestCase):
    def setUp(self):
        self.a = Setup("alice")
        self.b = Setup("bob")
        self.client.login(username="alice", password="pw-123456")

    def _foreign_urls(self):
        b = self.b
        return {
            "area_detail": reverse("planning:area_detail", args=[b.area.pk]),
            "area_edit": reverse("planning:area_edit", args=[b.area.pk]),
            "area_northlight": reverse("planning:area_northlight", args=[b.area.pk]),
            "area_assess": reverse("planning:area_assess", args=[b.area.pk]),
            "year_detail": reverse("planning:year_detail", args=[b.year.pk]),
            "year_edit": reverse("planning:year_edit", args=[b.year.pk]),
            "goal_detail": reverse("planning:goal_detail", args=[b.goal.pk]),
            "goal_edit": reverse("planning:goal_edit", args=[b.goal.pk]),
            "milestone_edit": reverse("planning:milestone_edit", args=[b.milestone.pk]),
            "habit_edit": reverse("planning:habit_edit", args=[b.habit.pk]),
            "review_detail": reverse("planning:review_detail", args=[b.review.pk]),
            "review_edit": reverse("planning:review_edit", args=[b.review.pk]),
        }

    def test_get_foreign_objects_is_404(self):
        for name, url in self._foreign_urls().items():
            with self.subTest(name=name):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_post_update_foreign_objects_is_404_and_unchanged(self):
        b = self.b
        posts = {
            "area_edit": (reverse("planning:area_edit", args=[b.area.pk]), {"name": "HACKED"}),
            "area_northlight": (reverse("planning:area_northlight", args=[b.area.pk]), {"north_light": "HACKED", "why": "x"}),
            "area_assess": (reverse("planning:area_assess", args=[b.area.pk]),
                            {"satisfaction": 1, "importance": 1, "strategic_mode": "improve", "annual_vision": "HACKED"}),
            "year_edit": (reverse("planning:year_edit", args=[b.year.pk]),
                          {"title": "HACKED", "start_date": "2030-01-01", "end_date": "2030-12-31"}),
            "goal_edit": (reverse("planning:goal_edit", args=[b.goal.pk]), {"title": "HACKED"}),
            "goal_status": (reverse("planning:goal_status", args=[b.goal.pk]), {"status": "dropped"}),
            "milestone_edit": (reverse("planning:milestone_edit", args=[b.milestone.pk]), {"title": "HACKED"}),
            "habit_edit": (reverse("planning:habit_edit", args=[b.habit.pk]), {"title": "HACKED"}),
            "habit_checkin": (reverse("planning:habit_checkin", args=[b.habit.pk]), {}),
            "review_edit": (reverse("planning:review_edit", args=[b.review.pk]), {"notes": "HACKED"}),
            "year_activate": (reverse("planning:year_activate", args=[b.year.pk]), {}),
        }
        for name, (url, data) in posts.items():
            with self.subTest(name=name):
                self.assertEqual(self.client.post(url, data).status_code, 404)
        b.area.refresh_from_db(); b.goal.refresh_from_db(); b.year.refresh_from_db(); b.review.refresh_from_db()
        self.assertNotEqual(b.area.name, "HACKED")
        self.assertNotEqual(b.area.north_light, "HACKED")
        self.assertNotEqual(b.goal.title, "HACKED")
        self.assertNotEqual(b.goal.status, "dropped")
        self.assertNotEqual(b.year.title, "HACKED")
        self.assertNotEqual(b.review.notes, "HACKED")
        self.assertFalse(HabitCheckin.objects.filter(habit=b.habit).exists())

    def test_delete_foreign_objects_is_404_and_still_exists(self):
        b = self.b
        deletes = {
            "goal_delete": reverse("planning:goal_delete", args=[b.goal.pk]),
            "milestone_delete": reverse("planning:milestone_delete", args=[b.milestone.pk]),
            "habit_delete": reverse("planning:habit_delete", args=[b.habit.pk]),
            "review_delete": reverse("planning:review_delete", args=[b.review.pk]),
            "area_archive": reverse("planning:area_archive", args=[b.area.pk]),
        }
        for name, url in deletes.items():
            with self.subTest(name=name):
                self.assertEqual(self.client.post(url).status_code, 404)
        self.assertTrue(Goal.objects.filter(pk=b.goal.pk).exists())
        self.assertTrue(Milestone.objects.filter(pk=b.milestone.pk).exists())
        self.assertTrue(Habit.objects.filter(pk=b.habit.pk).exists())
        self.assertTrue(Review.objects.filter(pk=b.review.pk).exists())
        b.area.refresh_from_db()
        self.assertTrue(b.area.is_active)

    def test_lists_only_show_own_data(self):
        for url, foreign in (
            (reverse("planning:goal_list") + "?year=", self.b.goal.title),
            (reverse("planning:habit_list"), self.b.habit.title),
            (reverse("planning:review_list"), "bob"),
            (reverse("planning:year_list"), "bob"),
        ):
            with self.subTest(url=url):
                self.assertNotContains(self.client.get(url), foreign)

    def test_fk_tampering_on_create_is_rejected(self):
        """Posting another user's life_area / personal_year / goal id must not attach."""
        resp = self.client.post(reverse("planning:goal_create"), {
            "title": "Sneaky", "life_area": self.b.area.pk, "personal_year": self.b.year.pk,
            "goal_type": "outcome", "status": "not_started", "priority": 2, "progress_percentage": 0,
        })
        self.assertEqual(resp.status_code, 200)  # re-rendered with errors, not saved
        self.assertFalse(Goal.objects.filter(title="Sneaky").exists())
        resp = self.client.post(reverse("planning:milestone_create", args=[self.a.goal.pk]), {
            "title": "Sneaky", "goal": self.b.goal.pk, "status": "not_started", "progress_percentage": 0,
        })
        self.assertFalse(Milestone.objects.filter(title="Sneaky").exists())
        resp = self.client.post(reverse("planning:habit_create"), {
            "title": "Sneaky", "life_area": self.b.area.pk, "frequency_type": "weekly", "frequency_target": 1, "is_active": "on",
        })
        self.assertFalse(Habit.objects.filter(title="Sneaky").exists())

    def test_goal_link_cannot_reach_foreign_goal(self):
        resp = self.client.post(reverse("planning:goal_link", args=[self.a.goal.pk]), {"process_goal": self.b.goal.pk})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(self.a.goal.supporting_links.exists())


class AnonymousAccessTests(TestCase):
    def test_private_pages_redirect_to_login(self):
        s = Setup("carol")
        for name, args in (("dashboard", []), ("area_list", []), ("goal_list", []), ("habit_list", []),
                           ("review_list", []), ("history", []), ("year_list", []), ("profile", []),
                           ("onboarding", [1]), ("area_detail", [s.area.pk]), ("goal_detail", [s.goal.pk])):
            with self.subTest(name=name):
                resp = self.client.get(reverse(f"planning:{name}", args=args))
                self.assertEqual(resp.status_code, 302)
                self.assertIn("/accounts/login/", resp["Location"])

    def test_anonymous_post_cannot_mutate(self):
        s = Setup("dave")
        resp = self.client.post(reverse("planning:goal_delete", args=[s.goal.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Goal.objects.filter(pk=s.goal.pk).exists())

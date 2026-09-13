"""Dashboard extras: clickable summary cards, the score form, the milestone list."""
from django.test import TestCase
from django.urls import reverse

from planning.models import LifeAreaAssessment

from .utils import Setup


class DashboardScoreTests(TestCase):
    def setUp(self):
        self.a = Setup("alice")
        self.b = Setup("bob")
        self.client.login(username="alice", password="pw-123456")

    def _post(self, rows):
        data = {"scores-TOTAL_FORMS": len(rows), "scores-INITIAL_FORMS": len(rows),
                "scores-MIN_NUM_FORMS": 0, "scores-MAX_NUM_FORMS": 1000}
        for i, (pk, sat, imp) in enumerate(rows):
            data.update({f"scores-{i}-id": pk, f"scores-{i}-satisfaction": sat, f"scores-{i}-importance": imp})
        return self.client.post(reverse("planning:dashboard_scores"), data)

    def test_dashboard_shows_cards_as_links_and_score_form(self):
        resp = self.client.get(reverse("planning:dashboard"))
        for name in ("milestone_list", "habit_list", "goal_list", "dashboard_scores"):
            self.assertContains(resp, reverse(f"planning:{name}"))
        self.assertContains(resp, reverse("planning:year_detail", args=[self.a.year.pk]))
        self.assertContains(resp, "Update scores")

    def test_changed_scores_are_saved_and_snapshotted(self):
        a = self.a.assessment
        snaps = a.snapshots.count()
        resp = self._post([(a.pk, 8, a.importance)])
        self.assertRedirects(resp, reverse("planning:dashboard"), fetch_redirect_response=False)
        a.refresh_from_db()
        self.assertEqual(a.satisfaction, 8)
        self.assertEqual(a.snapshots.count(), snaps + 1)
        self.assertEqual(a.snapshots.latest("taken_at").source, "dashboard")

    def test_unchanged_scores_write_no_snapshot(self):
        a = self.a.assessment
        snaps = a.snapshots.count()
        self._post([(a.pk, a.satisfaction, a.importance)])
        self.assertEqual(a.snapshots.count(), snaps)

    def test_cannot_change_another_users_scores(self):
        b = self.b.assessment
        self._post([(b.pk, 1, 1)])
        b.refresh_from_db()
        self.assertEqual((b.satisfaction, b.importance), (5, 7))

    def test_review_form_rejects_forged_assessment_id_too(self):
        b = self.b.assessment
        data = {"review_date": "2026-06-01", "period_label": "June", "scores-TOTAL_FORMS": 1, "scores-INITIAL_FORMS": 1,
                "scores-MIN_NUM_FORMS": 0, "scores-MAX_NUM_FORMS": 1000,
                "scores-0-id": b.pk, "scores-0-satisfaction": 1, "scores-0-importance": 1}
        self.client.post(reverse("planning:review_create", args=["monthly"]), data)
        b.refresh_from_db()
        self.assertEqual((b.satisfaction, b.importance), (5, 7))

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(reverse("planning:dashboard_scores")).status_code, 405)


class MilestoneListTests(TestCase):
    def setUp(self):
        self.a = Setup("alice")
        self.b = Setup("bob")
        self.client.login(username="alice", password="pw-123456")

    def test_lists_only_own_milestones(self):
        resp = self.client.get(reverse("planning:milestone_list"))
        self.assertContains(resp, "alice milestone")
        self.assertNotContains(resp, "bob milestone")
        resp = self.client.get(reverse("planning:milestone_list") + "?all=1")
        self.assertContains(resp, "alice milestone")
        self.assertNotContains(resp, "bob milestone")

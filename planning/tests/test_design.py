"""Design my life: guided, per-area, creates only what the user ticks, and
suggests goals only for Improve areas."""
from django.test import TestCase
from django.urls import reverse

from planning.library import GOAL_SAMPLES
from planning.models import Goal, LifeAreaAssessment, StrategicMode

from .utils import Setup


class DesignLifeTests(TestCase):
    def setUp(self):
        self.a = Setup("alice")
        self.b = Setup("bob")
        self.client.login(username="alice", password="pw-123456")
        self.step1 = reverse("planning:design_life_step", args=[1])  # health, marked Improve in Setup

    def test_walk_shows_own_area_with_samples_and_goal_suggestions(self):
        resp = self.client.get(reverse("planning:design_life"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Health &amp; Energy")
        self.assertContains(resp, "Start from an example")
        self.assertContains(resp, GOAL_SAMPLES["health"][0]["title"])
        self.assertContains(resp, "alice goal")  # existing goal listed
        self.assertNotContains(resp, "bob")

    def test_protect_area_gets_no_goal_suggestions(self):
        second = self.a.areas[1]
        LifeAreaAssessment.objects.filter(personal_year=self.a.year, life_area=second) \
            .update(strategic_mode=StrategicMode.PROTECT)
        resp = self.client.get(reverse("planning:design_life_step", args=[2]))
        self.assertContains(resp, "no goals are suggested")
        self.assertNotContains(resp, GOAL_SAMPLES["relationships"][0]["title"])

    def test_post_saves_north_light_and_only_ticked_goals(self):
        before = Goal.objects.filter(user=self.a.user).count()
        resp = self.client.post(self.step1, {"north_light": "My light", "why": "Because", "goal": ["1"]})
        self.assertRedirects(resp, reverse("planning:design_life_step", args=[2]), fetch_redirect_response=False)
        self.a.area.refresh_from_db()
        self.assertEqual(self.a.area.north_light, "My light")
        new = Goal.objects.filter(user=self.a.user).order_by("-id").first()
        self.assertEqual(Goal.objects.filter(user=self.a.user).count(), before + 1)
        self.assertEqual(new.title, GOAL_SAMPLES["health"][1]["title"])
        self.assertEqual(new.personal_year, self.a.year)
        self.assertEqual(new.life_area, self.a.area)
        self.assertIsNone(new.baseline); self.assertIsNone(new.target)  # user must make it concrete

    def test_post_with_nothing_ticked_creates_no_goal(self):
        before = Goal.objects.filter(user=self.a.user).count()
        self.client.post(self.step1, {"north_light": "", "why": ""})
        self.assertEqual(Goal.objects.filter(user=self.a.user).count(), before)

    def test_custom_goal_and_ignored_bad_indices(self):
        before = Goal.objects.filter(user=self.a.user).count()
        self.client.post(self.step1, {"north_light": "", "why": "", "goal": ["99", "x"], "custom_goal": "Run a 10k"})
        self.assertEqual(Goal.objects.filter(user=self.a.user).count(), before + 1)
        self.assertTrue(Goal.objects.filter(user=self.a.user, title="Run a 10k").exists())

    def test_goals_are_never_created_for_other_user(self):
        bob_before = Goal.objects.filter(user=self.b.user).count()
        self.client.post(self.step1, {"north_light": "", "why": "", "goal": ["0"]})
        self.assertEqual(Goal.objects.filter(user=self.b.user).count(), bob_before)
        self.b.area.refresh_from_db()
        self.assertEqual(self.b.area.north_light, "")

    def test_last_step_redirects_to_done(self):
        last = len(self.a.areas)
        resp = self.client.post(reverse("planning:design_life_step", args=[last]), {"north_light": "", "why": "", "custom_goal": "A wish"})
        self.assertRedirects(resp, reverse("planning:design_life_done"), fetch_redirect_response=False)
        done = self.client.get(reverse("planning:design_life_done"))
        self.assertContains(done, "Make these concrete")
        self.assertContains(done, "A wish")
        self.assertEqual(self.client.get(reverse("planning:design_life_step", args=[last + 1])).status_code, 404)

    def test_anonymous_redirected(self):
        self.client.logout()
        resp = self.client.get(reverse("planning:design_life"))
        self.assertEqual(resp.status_code, 302)

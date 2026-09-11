"""Ownership on create, onboarding flow, and a render smoke test of every page."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from planning.models import Goal, Habit, LifeArea, LifeAreaAssessment, Milestone, PersonalYear, Review, UserProfile

from .utils import Setup

User = get_user_model()


class OwnershipOnCreateTests(TestCase):
    def setUp(self):
        self.s = Setup("owner")
        self.client.login(username="owner", password="pw-123456")

    def test_new_objects_belong_to_request_user(self):
        self.client.post(reverse("planning:area_list"), {"name": "Mine", "description": ""})
        self.assertEqual(LifeArea.objects.get(name="Mine").user, self.s.user)
        self.client.post(reverse("planning:goal_create"), {
            "title": "G", "life_area": self.s.area.pk, "personal_year": self.s.year.pk, "goal_type": "outcome",
            "status": "not_started", "priority": 2, "progress_percentage": 0,
        })
        self.assertEqual(Goal.objects.get(title="G").user, self.s.user)
        self.client.post(reverse("planning:milestone_create", args=[self.s.goal.pk]),
                         {"title": "M", "goal": self.s.goal.pk, "status": "not_started", "progress_percentage": 0})
        self.assertEqual(Milestone.objects.get(title="M").user, self.s.user)
        self.client.post(reverse("planning:habit_create"),
                         {"title": "H", "life_area": self.s.area.pk, "frequency_type": "daily", "frequency_target": 1, "is_active": "on"})
        self.assertEqual(Habit.objects.get(title="H").user, self.s.user)
        self.client.post(reverse("planning:year_create"),
                         {"title": "Y", "start_date": "2031-01-01", "end_date": "2031-12-31"})
        self.assertEqual(PersonalYear.objects.get(title="Y").user, self.s.user)
        self.client.post(reverse("planning:review_create", args=["monthly"]),
                         {"review_date": "2026-09-01", "period_label": "Sep", "moved_forward": "x",
                          "scores-TOTAL_FORMS": 0, "scores-INITIAL_FORMS": 0})
        self.assertEqual(Review.objects.get(period_label="Sep").user, self.s.user)

    def test_habit_checkin_toggles_and_increments(self):
        url = reverse("planning:habit_checkin", args=[self.s.habit.pk])
        self.client.post(url); self.assertEqual(self.s.habit.checkins.count(), 1)
        self.client.post(url); self.assertEqual(self.s.habit.checkins.count(), 0)   # weekly → toggle
        h = Habit.objects.create(user=self.s.user, life_area=self.s.area, title="x3", frequency_type="times_per_week", frequency_target=3)
        url = reverse("planning:habit_checkin", args=[h.pk])
        self.client.post(url); self.client.post(url)
        self.assertEqual(h.checkins.get().count, 2)

    def test_assess_records_snapshot_on_change(self):
        before = self.s.assessment.snapshots.count()
        self.client.post(reverse("planning:area_assess", args=[self.s.area.pk]),
                         {"satisfaction": 9, "importance": 6, "strategic_mode": "protect", "annual_vision": "still true"})
        self.s.assessment.refresh_from_db()
        self.assertEqual((self.s.assessment.satisfaction, self.s.assessment.priority_gap), (9, -3))
        self.assertEqual(self.s.assessment.snapshots.count(), before + 1)


class OnboardingTests(TestCase):
    def test_signup_then_walk_through(self):
        resp = self.client.post(reverse("planning:signup"), {
            "username": "newbie", "email": "n@example.com", "password1": "a-strong-passw0rd!", "password2": "a-strong-passw0rd!"})
        self.assertRedirects(resp, reverse("planning:onboarding", args=[1]))
        user = User.objects.get(username="newbie")
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        # Dashboard redirects into onboarding until areas exist
        self.assertRedirects(self.client.get(reverse("planning:dashboard")), reverse("planning:onboarding", args=[1]))
        self.assertRedirects(self.client.post(reverse("planning:onboarding", args=[1])), reverse("planning:onboarding", args=[2]))
        self.assertEqual(LifeArea.objects.filter(user=user).count(), 10)
        self.assertEqual(PersonalYear.objects.filter(user=user).count(), 1)
        # Remove one, add one
        first = LifeArea.objects.filter(user=user).first()
        self.client.post(reverse("planning:onboarding", args=[2]), {"action": "archive", "pk": first.pk})
        self.client.post(reverse("planning:onboarding", args=[2]), {"action": "add", "name": "Garden"})
        self.assertEqual(LifeArea.objects.filter(user=user, is_active=True).count(), 10)
        self.client.post(reverse("planning:onboarding", args=[2]), {"action": "next"})
        # Every step renders and progress is saved
        for step in range(3, 10):
            self.assertEqual(self.client.get(reverse("planning:onboarding", args=[step])).status_code, 200)
        year = PersonalYear.objects.get(user=user)
        self.assertEqual(LifeAreaAssessment.objects.filter(personal_year=year).count(), 10)
        # Step 9 quick goal + finish
        area = LifeArea.objects.filter(user=user, is_active=True).first()
        self.client.post(reverse("planning:onboarding", args=[9]), {
            "action": "add", "title": "One goal", "goal_type": "outcome", "life_area": area.pk, "personal_year": year.pk})
        self.assertTrue(Goal.objects.filter(user=user, title="One goal").exists())
        resp = self.client.post(reverse("planning:onboarding", args=[9]), {"action": "finish"})
        self.assertRedirects(resp, reverse("planning:dashboard"))
        user.profile.refresh_from_db()
        self.assertTrue(user.profile.onboarding_complete)
        year.refresh_from_db()
        self.assertEqual(year.status, PersonalYear.STATUS_ACTIVE)

    def test_skip_saves_progress(self):
        s = Setup("skipper")
        self.client.login(username="skipper", password="pw-123456")
        self.client.post(reverse("planning:onboarding", args=[1]))
        self.client.post(reverse("planning:onboarding", args=[2]), {"action": "next"})
        self.assertEqual(UserProfile.objects.get(user=s.user).onboarding_step, 3)


class PageSmokeTests(TestCase):
    """Every page renders for a fully set-up user — catches template errors."""

    def setUp(self):
        self.s = Setup("smoke")
        self.client.login(username="smoke", password="pw-123456")

    def test_all_pages_render(self):
        s = self.s
        pages = [
            ("dashboard", []), ("history", []), ("profile", []),
            ("area_list", []), ("area_detail", [s.area.pk]), ("area_edit", [s.area.pk]),
            ("area_northlight", [s.area.pk]), ("area_assess", [s.area.pk]),
            ("year_list", []), ("year_create", []), ("year_detail", [s.year.pk]), ("year_edit", [s.year.pk]), ("year_next", [s.year.pk]),
            ("goal_list", []), ("goal_create", []), ("goal_detail", [s.goal.pk]), ("goal_edit", [s.goal.pk]),
            ("milestone_create", [s.goal.pk]), ("milestone_edit", [s.milestone.pk]),
            ("habit_list", []), ("habit_create", []), ("habit_edit", [s.habit.pk]),
            ("review_list", []), ("review_detail", [s.review.pk]), ("review_edit", [s.review.pk]),
        ] + [("review_create", [k]) for k in ("monthly", "quarterly", "annual", "life")] \
          + [("onboarding", [i]) for i in range(1, 10)]
        for name, args in pages:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(f"planning:{name}", args=args)).status_code, 200)
        self.assertEqual(self.client.get(reverse("planning:goal_list") + "?mode=improve&status=in_progress").status_code, 200)

    def test_auth_pages_render(self):
        self.client.logout()
        for url in (reverse("login"), reverse("planning:signup"), reverse("password_reset")):
            self.assertEqual(self.client.get(url).status_code, 200)

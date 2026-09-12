"""North Light samples: every default area has starting points, custom areas
get the general set, and the forms offer them without ever writing anything."""
from django.test import TestCase
from django.urls import reverse

from planning.library import GENERAL_KEY, NORTH_LIGHT_SAMPLES, samples_for
from planning.models import DEFAULT_LIFE_AREAS, LifeArea

from .utils import Setup


class SampleLibraryTests(TestCase):
    def test_every_default_area_has_samples(self):
        for key, _name in DEFAULT_LIFE_AREAS:
            with self.subTest(key=key):
                pairs = NORTH_LIGHT_SAMPLES[key]
                self.assertGreaterEqual(len(pairs), 3)
                for nl, why in pairs:
                    self.assertTrue(nl and why)
        self.assertTrue(NORTH_LIGHT_SAMPLES[GENERAL_KEY])

    def test_custom_area_gets_general_samples(self):
        self.assertEqual(samples_for(""), NORTH_LIGHT_SAMPLES[GENERAL_KEY])
        self.assertEqual(samples_for("no-such-key"), NORTH_LIGHT_SAMPLES[GENERAL_KEY])


class SampleFormTests(TestCase):
    def setUp(self):
        self.a = Setup("alice")
        self.client.login(username="alice", password="pw-123456")

    def test_north_light_page_offers_samples_and_saves_nothing(self):
        area = self.a.area  # "health"
        resp = self.client.get(reverse("planning:area_northlight", args=[area.pk]))
        self.assertContains(resp, "Start from an example")
        self.assertContains(resp, NORTH_LIGHT_SAMPLES["health"][1][0])
        self.assertContains(resp, "<details class=\"nl-samples mb-2\" open>")  # blank field: open by default
        area.refresh_from_db()
        self.assertEqual(area.north_light, "")

    def test_samples_collapsed_once_a_north_light_exists(self):
        area = self.a.area
        area.north_light = "Mine already."; area.save()
        resp = self.client.get(reverse("planning:area_northlight", args=[area.pk]))
        self.assertContains(resp, "Start from an example")
        self.assertNotContains(resp, "<details class=\"nl-samples mb-2\" open>")

    def test_custom_area_shows_general_samples(self):
        custom = LifeArea.objects.create(user=self.a.user, name="Garden", sort_order=99)
        resp = self.client.get(reverse("planning:area_northlight", args=[custom.pk]))
        self.assertContains(resp, NORTH_LIGHT_SAMPLES[GENERAL_KEY][0][0])

    def test_onboarding_step6_offers_samples(self):
        resp = self.client.get(reverse("planning:onboarding", args=[6]))
        self.assertContains(resp, "Start from an example")
        self.assertContains(resp, NORTH_LIGHT_SAMPLES["finance"][0][0])

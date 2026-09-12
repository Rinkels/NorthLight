"""Data export: complete, user-scoped, and never leaks another user's rows."""
import csv
import io
import json

from django.test import TestCase
from django.urls import reverse

from planning.export import export_user_data
from planning.models import HabitCheckin

from .utils import Setup


class ExportTests(TestCase):
    def setUp(self):
        self.a = Setup("alice")
        self.b = Setup("bob")
        HabitCheckin.objects.create(habit=self.a.habit)
        self.client.login(username="alice", password="pw-123456")

    def test_json_export_contains_only_own_data(self):
        data = export_user_data(self.a.user)
        text = json.dumps(data)
        self.assertEqual(data["format"], "northlight-export")
        self.assertEqual(data["account"]["username"], "alice")
        self.assertIn("alice goal", text)
        self.assertIn("alice milestone", text)
        self.assertIn("alice habit", text)
        self.assertNotIn("bob", text)
        year = data["personal_years"][0]
        self.assertEqual(len(year["assessments"]), len(self.a.areas))
        self.assertTrue(year["assessments"][0]["snapshots"])  # history rides along
        self.assertEqual(year["goals"][0]["progress"], 40)
        self.assertEqual(year["reviews"][0]["moved_forward"], "things")
        self.assertEqual(data["habits"][0]["checkins"][0]["count"], 1)

    def test_json_download(self):
        resp = self.client.get(reverse("planning:export_json"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/json", resp["Content-Type"])
        self.assertIn("attachment", resp["Content-Disposition"])
        payload = json.loads(resp.content)
        self.assertEqual(payload["account"]["username"], "alice")
        self.assertNotIn("bob", resp.content.decode())

    def test_csv_downloads(self):
        for name, header_field, expected in [
            ("planning:export_scores_csv", "life_area", len(self.a.areas)),
            ("planning:export_goals_csv", "title", 1),
        ]:
            with self.subTest(name=name):
                resp = self.client.get(reverse(name))
                self.assertEqual(resp.status_code, 200)
                self.assertIn("text/csv", resp["Content-Type"])
                rows = list(csv.DictReader(io.StringIO(resp.content.decode("utf-8"))))
                self.assertEqual(len(rows), expected)
                self.assertIn(header_field, rows[0])
                self.assertFalse(any("bob" in v for r in rows for v in r.values()))

    def test_goals_csv_values(self):
        resp = self.client.get(reverse("planning:export_goals_csv"))
        row = list(csv.DictReader(io.StringIO(resp.content.decode("utf-8"))))[0]
        self.assertEqual(row["title"], "alice goal")
        self.assertEqual(row["progress_pct"], "40")
        self.assertEqual(row["target_unit"], "km")

    def test_export_page_renders_and_links(self):
        resp = self.client.get(reverse("planning:export"))
        self.assertContains(resp, reverse("planning:export_json"))
        self.assertContains(self.client.get(reverse("planning:profile")), reverse("planning:export"))

    def test_anonymous_is_redirected(self):
        self.client.logout()
        for name in ("planning:export", "planning:export_json", "planning:export_scores_csv", "planning:export_goals_csv"):
            with self.subTest(name=name):
                resp = self.client.get(reverse(name))
                self.assertEqual(resp.status_code, 302)
                self.assertIn("/accounts/login/", resp["Location"])

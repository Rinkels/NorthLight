"""Cross-model rules: defaults, assessments, rolling a year forward."""
from datetime import date
from decimal import Decimal

from django.test import TestCase

from planning.models import DEFAULT_LIFE_AREAS, Goal, LifeArea, LifeAreaAssessment, PersonalYear, StrategicMode, WorkStatus
from planning.services import (
    create_next_year, ensure_assessments, ensure_default_life_areas, restore_default_life_areas, score_history,
    start_vs_end, update_goal_value,
)

from .utils import Setup


class LifeAreaServiceTests(TestCase):
    def test_defaults_created_once(self):
        s = Setup("d1")
        self.assertEqual(LifeArea.objects.filter(user=s.user).count(), len(DEFAULT_LIFE_AREAS))
        ensure_default_life_areas(s.user)
        self.assertEqual(LifeArea.objects.filter(user=s.user).count(), len(DEFAULT_LIFE_AREAS))
        self.assertEqual([a.name for a in s.areas][:2], ["Health & Energy", "Relationships & Family"])

    def test_restore_defaults_reactivates_and_readds_without_touching_custom(self):
        s = Setup("d2")
        custom = LifeArea.objects.create(user=s.user, name="Custom", sort_order=99)
        s.areas[0].is_active = False
        s.areas[0].save()
        s.areas[1].delete()
        n = restore_default_life_areas(s.user)
        self.assertEqual(n, 2)
        self.assertTrue(LifeArea.objects.get(pk=s.areas[0].pk).is_active)
        self.assertTrue(LifeArea.objects.filter(user=s.user, template_key="relationships").exists())
        self.assertTrue(LifeArea.objects.filter(pk=custom.pk).exists())


class AssessmentServiceTests(TestCase):
    def test_ensure_assessments_is_idempotent_and_carries_previous_scores(self):
        s = Setup("a1")
        self.assertEqual(LifeAreaAssessment.objects.filter(personal_year=s.year).count(), 10)
        ensure_assessments(s.year)
        self.assertEqual(LifeAreaAssessment.objects.filter(personal_year=s.year).count(), 10)
        nxt = PersonalYear.objects.create(user=s.user, title="N", start_date=date(2030, 1, 1), end_date=date(2030, 12, 31))
        ensure_assessments(nxt)
        carried = LifeAreaAssessment.objects.get(personal_year=nxt, life_area=s.area)
        self.assertEqual((carried.satisfaction, carried.importance, carried.strategic_mode), (5, 7, StrategicMode.IMPROVE))
        # and the original is a separate, untouched row
        s.assessment.refresh_from_db()
        self.assertEqual(s.assessment.personal_year, s.year)

    def test_start_vs_end(self):
        s = Setup("a2")
        s.assessment.satisfaction = 8
        s.assessment.save()
        row = next(r for r in start_vs_end(s.year) if r["area"] == s.area)
        self.assertEqual((row["start_satisfaction"], row["end_satisfaction"], row["delta"]), (5, 8, 3))


class NextYearTests(TestCase):
    def test_goals_not_copied_unless_chosen_and_history_kept(self):
        s = Setup("n1")
        other = Goal.objects.create(user=s.user, personal_year=s.year, life_area=s.area, title="Leave behind")
        s.year.status = PersonalYear.STATUS_COMPLETED
        s.year.save()
        nxt = create_next_year(s.year, carry_goal_ids=[s.goal.pk])
        self.assertEqual(nxt.start_date, date(s.year.end_date.year + 1, 1, 1))
        titles = set(Goal.objects.filter(personal_year=nxt).values_list("title", flat=True))
        self.assertEqual(titles, {s.goal.title})
        carried = Goal.objects.get(personal_year=nxt)
        self.assertEqual(carried.status, WorkStatus.NOT_STARTED)
        self.assertEqual(carried.baseline, Decimal("4"))     # last current value becomes the new baseline
        self.assertTrue(Goal.objects.filter(pk=other.pk, personal_year=s.year).exists())
        # Previous year's assessments are untouched; new year has its own rows
        self.assertEqual(LifeAreaAssessment.objects.filter(personal_year=s.year).count(), 10)
        self.assertEqual(LifeAreaAssessment.objects.filter(personal_year=nxt).count(), 10)
        hist = score_history(s.user)
        self.assertEqual([y.pk for y in hist["years"]], [s.year.pk, nxt.pk])

    def test_carrying_foreign_goal_id_is_ignored(self):
        s = Setup("n2")
        t = Setup("n3")
        s.year.status = PersonalYear.STATUS_COMPLETED
        s.year.save()
        nxt = create_next_year(s.year, carry_goal_ids=[t.goal.pk])
        self.assertEqual(Goal.objects.filter(personal_year=nxt).count(), 0)


class DashboardRowTests(TestCase):
    def test_area_progress_and_wheel_payload(self):
        from planning.services import dashboard_data
        s = Setup("dash")  # one goal at 40% in s.area; other areas have none
        data = dashboard_data(s.user)
        row = next(r for r in data.rows if r.area == s.area)
        self.assertEqual((row.avg_progress, row.open_goal_count), (40, 1))
        empty = next(r for r in data.rows if r.area != s.area)
        self.assertIsNone(empty.avg_progress)          # no goals ≠ 0%
        wheel = data.wheel
        idx = wheel["ids"].index(s.area.id)
        self.assertEqual((wheel["goals"][idx], wheel["open"][idx], wheel["progress"][idx]), (1, 1, 40))
        self.assertEqual(wheel["mode"][idx], "Improve")
        self.assertIsNone(wheel["progress"][wheel["ids"].index(empty.area.id)])


class ProviderSeamTests(TestCase):
    def test_update_goal_value_completes_when_target_reached(self):
        s = Setup("p1")
        update_goal_value(s.goal, Decimal("10"))
        s.goal.refresh_from_db()
        self.assertEqual(s.goal.status, WorkStatus.COMPLETE)

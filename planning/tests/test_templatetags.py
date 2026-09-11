from decimal import Decimal

from django.test import TestCase

from planning.models import Goal
from planning.templatetags.planning_extras import measure, num

from .utils import Setup


class NumberFormattingTests(TestCase):
    def test_num(self):
        self.assertEqual(num(Decimal("165000.00")), "165,000")
        self.assertEqual(num(Decimal("27.50")), "27.5")
        self.assertEqual(num(Decimal("0.25")), "0.25")
        self.assertEqual(num(None), "—")
        self.assertEqual(num("abc"), "abc")

    def test_measure_unit_placement(self):
        self.assertEqual(measure(Decimal("165000"), "$"), "$165,000")
        self.assertEqual(measure(Decimal("165000"), "CAD"), "CAD 165,000")
        self.assertEqual(measure(Decimal("27.5"), "minutes"), "27.5 minutes")
        self.assertEqual(measure(Decimal("3"), ""), "3")
        self.assertEqual(measure(None, "$"), "—")


class PctOfTargetTests(TestCase):
    def test_money_goal_reads_both_ways(self):
        s = Setup("pct")
        g = Goal.objects.create(user=s.user, personal_year=s.year, life_area=s.area, title="200K",
                                baseline=Decimal("165000"), target=Decimal("200000"), current_value=Decimal("165000"))
        self.assertEqual(g.progress(), 0)          # no movement from baseline yet
        self.assertEqual(g.pct_of_target(), 82)    # but 82% of the way to the number
        g.current_value = Decimal("182500")
        self.assertEqual((g.progress(), g.pct_of_target()), (50, 91))

    def test_not_shown_when_meaningless(self):
        s = Setup("pct2")
        decreasing = Goal.objects.create(user=s.user, personal_year=s.year, life_area=s.area, title="5K",
                                         baseline=Decimal("26"), target=Decimal("25"), current_value=Decimal("25.5"))
        self.assertIsNone(decreasing.pct_of_target())
        self.assertEqual(decreasing.progress(), 50)
        from_zero = s.goal  # baseline 0 → identical to progress, so omitted
        self.assertIsNone(from_zero.pct_of_target())

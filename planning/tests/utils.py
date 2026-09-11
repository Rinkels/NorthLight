"""Shared fixtures: a fully set-up user (areas, active year, assessments,
goal, milestone, habit, review) so tests can hit real pages."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from planning.models import (
    Goal, GoalType, Habit, LifeAreaAssessment, Milestone, PersonalYear, Review, ReviewType, StrategicMode,
    WorkStatus,
)
from planning.services import ensure_assessments, ensure_default_life_areas

User = get_user_model()


class Setup:
    def __init__(self, username: str, *, active=True):
        self.user = User.objects.create_user(username=username, password="pw-123456")
        self.areas = ensure_default_life_areas(self.user)
        today = timezone.localdate()
        self.year = PersonalYear.objects.create(
            user=self.user, title=f"{today.year} Personal Year",
            start_date=date(today.year, 1, 1), end_date=date(today.year, 12, 31),
            status=PersonalYear.STATUS_ACTIVE if active else PersonalYear.STATUS_PLANNING,
        )
        ensure_assessments(self.year, source="test")
        self.area = self.areas[0]
        self.assessment = LifeAreaAssessment.objects.get(personal_year=self.year, life_area=self.area)
        self.assessment.satisfaction, self.assessment.importance, self.assessment.strategic_mode = 5, 7, StrategicMode.IMPROVE
        self.assessment.save()
        self.goal = Goal.objects.create(
            user=self.user, personal_year=self.year, life_area=self.area, title=f"{username} goal",
            goal_type=GoalType.OUTCOME, baseline=Decimal("0"), target=Decimal("10"), target_unit="km",
            current_value=Decimal("4"), status=WorkStatus.IN_PROGRESS,
        )
        self.milestone = Milestone.objects.create(user=self.user, goal=self.goal, title=f"{username} milestone",
                                                  due_date=today + timedelta(days=30))
        self.habit = Habit.objects.create(user=self.user, life_area=self.area, goal=self.goal, title=f"{username} habit")
        self.review = Review.objects.create(user=self.user, personal_year=self.year, review_type=ReviewType.MONTHLY,
                                            period_label="Test", moved_forward="things")

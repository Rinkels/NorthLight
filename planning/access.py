"""Server-side ownership enforcement.

CRITICAL: a logged-in user must never be able to read or change another
user's data. Every view resolves objects through these helpers — which scope
the query to `request.user` — so a foreign primary key is simply a 404. Hiding
links is never relied upon.

Child objects without their own `user` column (HabitCheckin, GoalRelationship,
AssessmentSnapshot) are scoped through their parent's owner.
"""
from __future__ import annotations

from django.shortcuts import get_object_or_404

from .models import (
    AssessmentSnapshot, Goal, GoalRelationship, Habit, HabitCheckin, LifeArea,
    LifeAreaAssessment, Milestone, PersonalYear, Review, UserProfile,
)

# Model -> lookup that reaches the owning user.
OWNER_LOOKUP = {
    UserProfile: "user",
    LifeArea: "user",
    PersonalYear: "user",
    LifeAreaAssessment: "user",
    Goal: "user",
    Milestone: "user",
    Habit: "user",
    Review: "user",
    HabitCheckin: "habit__user",
    GoalRelationship: "outcome_goal__user",
    AssessmentSnapshot: "assessment__user",
}


def owned(model, user):
    """QuerySet of `model` rows belonging to `user`. Raises if the model has
    no registered owner path — so a new model can't silently leak."""
    lookup = OWNER_LOOKUP[model]
    return model.objects.filter(**{lookup: user})


def get_owned_or_404(model, user, **kwargs):
    """get_object_or_404, always scoped to the owner. Use this for every
    pk-based lookup in views (GET and POST/update/delete paths alike)."""
    return get_object_or_404(owned(model, user), **kwargs)


def profile_for(user) -> UserProfile:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile

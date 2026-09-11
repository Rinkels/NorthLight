"""Forms. Ownership is never taken from form input: views set `user` and
scope every FK queryset (life areas, years, goals) to the request user via
`for_user()`, so a tampered POST cannot attach data to someone else's objects.
"""
from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .access import owned
from .models import (
    Goal, GoalRelationship, Habit, HabitCheckin, LifeArea, LifeAreaAssessment,
    Milestone, PersonalYear, Review, ReviewType, UserProfile,
)

User = get_user_model()


class BootstrapMixin:
    """Apply Bootstrap classes without repeating widget attrs everywhere."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            w = field.widget
            if isinstance(w, (forms.CheckboxInput,)):
                w.attrs.setdefault("class", "form-check-input")
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                w.attrs.setdefault("class", "form-select")
            else:
                w.attrs.setdefault("class", "form-control")
            if isinstance(w, forms.Textarea):
                w.attrs.setdefault("rows", 3)


# --------------------------------------------------------------------------- #
# Accounts
# --------------------------------------------------------------------------- #

class SignUpForm(BootstrapMixin, UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class ProfileForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("display_name", "timezone", "year_start_type", "birthday", "custom_year_start",
                  "life_review_date", "review_cadence", "reminders_enabled")
        widgets = {
            "birthday": forms.DateInput(attrs={"type": "date"}),
            "custom_year_start": forms.DateInput(attrs={"type": "date"}),
            "life_review_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        data = super().clean()
        kind = data.get("year_start_type")
        if kind == UserProfile.YEAR_BIRTHDAY and not data.get("birthday"):
            self.add_error("birthday", "Enter your birthday to use birthday-to-birthday years.")
        if kind == UserProfile.YEAR_CUSTOM and not data.get("custom_year_start"):
            self.add_error("custom_year_start", "Enter the annual start date.")
        return data


# --------------------------------------------------------------------------- #
# Life areas
# --------------------------------------------------------------------------- #

class LifeAreaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = LifeArea
        fields = ("name", "description")


class NorthLightForm(BootstrapMixin, forms.ModelForm):
    """North Light + Why — directional, not a SMART goal."""

    class Meta:
        model = LifeArea
        fields = ("north_light", "why")
        widgets = {"north_light": forms.Textarea(attrs={"rows": 3}), "why": forms.Textarea(attrs={"rows": 2})}


# --------------------------------------------------------------------------- #
# Assessments
# --------------------------------------------------------------------------- #

class ScoreForm(BootstrapMixin, forms.ModelForm):
    """Satisfaction + Importance (1–10)."""

    class Meta:
        model = LifeAreaAssessment
        fields = ("satisfaction", "importance")
        widgets = {
            "satisfaction": forms.NumberInput(attrs={"min": 1, "max": 10, "type": "range", "class": "form-range"}),
            "importance": forms.NumberInput(attrs={"min": 1, "max": 10, "type": "range", "class": "form-range"}),
        }


class ModeForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = LifeAreaAssessment
        fields = ("strategic_mode",)


class VisionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = LifeAreaAssessment
        fields = ("annual_vision",)
        widgets = {"annual_vision": forms.Textarea(attrs={"rows": 3})}


class AssessmentForm(BootstrapMixin, forms.ModelForm):
    """Full per-area strategy edit from the Life Area detail page."""

    class Meta:
        model = LifeAreaAssessment
        fields = ("satisfaction", "importance", "strategic_mode", "annual_vision")
        widgets = {
            "satisfaction": forms.NumberInput(attrs={"min": 1, "max": 10}),
            "importance": forms.NumberInput(attrs={"min": 1, "max": 10}),
            "annual_vision": forms.Textarea(attrs={"rows": 3}),
        }


ScoreFormSet = forms.modelformset_factory(LifeAreaAssessment, form=ScoreForm, extra=0)
ModeFormSet = forms.modelformset_factory(LifeAreaAssessment, form=ModeForm, extra=0)
VisionFormSet = forms.modelformset_factory(LifeAreaAssessment, form=VisionForm, extra=0)
NorthLightFormSet = forms.modelformset_factory(LifeArea, form=NorthLightForm, extra=0)


# --------------------------------------------------------------------------- #
# Personal years
# --------------------------------------------------------------------------- #

class PersonalYearForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = PersonalYear
        fields = ("title", "start_date", "end_date", "foundation_start_date", "notes")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "foundation_start_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        data = super().clean()
        start, end, foundation = data.get("start_date"), data.get("end_date"), data.get("foundation_start_date")
        if start and end and end <= start:
            self.add_error("end_date", "The year must end after it starts.")
        if start and foundation and foundation >= start:
            self.add_error("foundation_start_date", "The Foundation Period must begin before the year starts.")
        return data


class YearReflectionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = PersonalYear
        fields = ("reflection",)
        widgets = {"reflection": forms.Textarea(attrs={"rows": 5})}


# --------------------------------------------------------------------------- #
# Goals / milestones / habits
# --------------------------------------------------------------------------- #

class OwnedFKMixin:
    """Scope FK choices to the owner. Call `for_user(user)` after init."""

    def for_user(self, user):
        if "life_area" in self.fields:
            self.fields["life_area"].queryset = owned(LifeArea, user).filter(is_active=True)
        if "personal_year" in self.fields:
            self.fields["personal_year"].queryset = owned(PersonalYear, user).exclude(
                status=PersonalYear.STATUS_ARCHIVED)
        if "goal" in self.fields:
            self.fields["goal"].queryset = owned(Goal, user)
        for name in ("outcome_goal", "process_goal"):
            if name in self.fields:
                self.fields[name].queryset = owned(Goal, user)
        return self


class GoalForm(BootstrapMixin, OwnedFKMixin, forms.ModelForm):
    class Meta:
        model = Goal
        fields = ("title", "life_area", "personal_year", "goal_type", "description",
                  "baseline", "target", "target_unit", "current_value", "target_date",
                  "status", "priority", "progress_percentage", "notes")
        widgets = {
            "target_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class QuickGoalForm(BootstrapMixin, OwnedFKMixin, forms.ModelForm):
    """Onboarding: just enough to capture a meaningful goal. Everything else
    keeps its model default and can be refined later from the goal page."""

    class Meta:
        model = Goal
        fields = ("title", "goal_type", "life_area", "personal_year", "target_date", "baseline", "target", "target_unit")
        widgets = {"target_date": forms.DateInput(attrs={"type": "date"}), "personal_year": forms.HiddenInput()}


class GoalValueForm(BootstrapMixin, forms.ModelForm):
    """Quick update of a goal's current value / status from list pages."""

    class Meta:
        model = Goal
        fields = ("current_value", "progress_percentage", "status")


class GoalLinkForm(BootstrapMixin, OwnedFKMixin, forms.ModelForm):
    class Meta:
        model = GoalRelationship
        fields = ("process_goal",)

    def __init__(self, *args, outcome_goal: Goal, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcome_goal = outcome_goal

    def for_user(self, user):
        super().for_user(user)
        self.fields["process_goal"].queryset = (
            self.fields["process_goal"].queryset.exclude(pk=self.outcome_goal.pk)
            .filter(personal_year=self.outcome_goal.personal_year)
        )
        self.fields["process_goal"].label = "Supporting (process) goal"
        return self


class MilestoneForm(BootstrapMixin, OwnedFKMixin, forms.ModelForm):
    class Meta:
        model = Milestone
        fields = ("title", "goal", "description", "quarter", "start_date", "due_date",
                  "status", "progress_percentage", "notes")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class HabitForm(BootstrapMixin, OwnedFKMixin, forms.ModelForm):
    class Meta:
        model = Habit
        fields = ("title", "life_area", "goal", "frequency_type", "frequency_target", "is_active")


class HabitCheckinForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = HabitCheckin
        fields = ("date", "count")
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


# --------------------------------------------------------------------------- #
# Reviews
# --------------------------------------------------------------------------- #

REVIEW_FIELDS = {
    ReviewType.MONTHLY: ("moved_forward", "stalled", "surprised", "attention_next", "no_longer_relevant", "notes"),
    ReviewType.QUARTERLY: ("moved_forward", "stalled", "priorities_changed", "north_light_check", "attention_next", "notes"),
    ReviewType.ANNUAL: ("moved_forward", "stalled", "lessons", "major_events", "carry_forward", "notes"),
    ReviewType.LIFE: ("north_light_check", "priorities_changed", "notes"),
}


class ReviewForm(BootstrapMixin, forms.ModelForm):
    """Shows only the reflection prompts relevant to the review type."""

    class Meta:
        model = Review
        fields = ("review_date", "period_label", "moved_forward", "stalled", "surprised", "attention_next",
                  "no_longer_relevant", "priorities_changed", "north_light_check", "lessons", "major_events",
                  "carry_forward", "notes")
        widgets = {"review_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, review_type: str, **kwargs):
        super().__init__(*args, **kwargs)
        keep = {"review_date", "period_label", *REVIEW_FIELDS[ReviewType(review_type)]}
        for name in list(self.fields):
            if name not in keep:
                self.fields.pop(name)

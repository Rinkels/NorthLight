"""NorthLight domain model.

Ownership rule: every top-level object carries an explicit `user` FK, and
child objects (HabitCheckin, GoalRelationship, AssessmentSnapshot) derive
ownership through their parent. Views MUST filter on the request user — see
planning.access. Never rely on hiding links.

Conceptual hierarchy (the product's core sequence):
  LifeArea (North Light, Why — timeless, directional)
    → LifeAreaAssessment per PersonalYear (Satisfaction, Importance, Gap,
      strategic mode, 12-Month Vision)
      → Goal → Milestone (90-day) / Habit → HabitCheckin
  PersonalYear → Review (monthly / quarterly / annual / life)
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

SCORE_VALIDATORS = [MinValueValidator(1), MaxValueValidator(10)]
PCT_VALIDATORS = [MinValueValidator(0), MaxValueValidator(100)]


# --------------------------------------------------------------------------- #
# Profile
# --------------------------------------------------------------------------- #

class UserProfile(models.Model):
    YEAR_CALENDAR = "calendar"
    YEAR_BIRTHDAY = "birthday"
    YEAR_CUSTOM = "custom"
    YEAR_START_CHOICES = [
        (YEAR_CALENDAR, "Calendar year (January 1)"),
        (YEAR_BIRTHDAY, "Birthday to birthday"),
        (YEAR_CUSTOM, "Custom annual start date"),
    ]
    CADENCE_MONTHLY = "monthly"
    CADENCE_QUARTERLY = "quarterly"
    CADENCE_CHOICES = [(CADENCE_MONTHLY, "Monthly"), (CADENCE_QUARTERLY, "Quarterly")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=120, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    year_start_type = models.CharField(max_length=16, choices=YEAR_START_CHOICES, default=YEAR_CALENDAR)
    birthday = models.DateField(null=True, blank=True, help_text="Only needed for birthday-based years or a birthday Life Review.")
    custom_year_start = models.DateField(null=True, blank=True, help_text="Month and day are used; the year is ignored.")
    life_review_date = models.DateField(
        null=True, blank=True,
        help_text="Optional annual deep Life Review date (e.g. your birthday), separate from Personal Year planning.",
    )
    review_cadence = models.CharField(max_length=16, choices=CADENCE_CHOICES, default=CADENCE_MONTHLY)
    reminders_enabled = models.BooleanField(default=False, help_text="Architecture placeholder — no reminders are sent in V1.")
    onboarding_step = models.PositiveSmallIntegerField(default=1)
    onboarding_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.display_name or self.user.get_username()

    @property
    def name(self) -> str:
        return self.display_name or self.user.get_username()

    def next_year_start(self, today: date | None = None) -> date:
        """The next Personal Year start after `today`, per the chosen start type."""
        today = today or timezone.localdate()
        if self.year_start_type == self.YEAR_BIRTHDAY and self.birthday:
            anchor = self.birthday
        elif self.year_start_type == self.YEAR_CUSTOM and self.custom_year_start:
            anchor = self.custom_year_start
        else:
            return date(today.year + 1, 1, 1)
        candidate = _safe_date(today.year, anchor.month, anchor.day)
        if candidate <= today:
            candidate = _safe_date(today.year + 1, anchor.month, anchor.day)
        return candidate


def _safe_date(year: int, month: int, day: int) -> date:
    """date(), but tolerate Feb 29 anchors in non-leap years."""
    try:
        return date(year, month, day)
    except ValueError:
        return date(year, month, 28)


# --------------------------------------------------------------------------- #
# Life Areas
# --------------------------------------------------------------------------- #

DEFAULT_LIFE_AREAS = [
    ("health", "Health & Energy"),
    ("relationships", "Relationships & Family"),
    ("friends", "Friends & Community"),
    ("work", "Work & Career"),
    ("finance", "Financial Freedom"),
    ("time", "Time Freedom"),
    ("learning", "Learning & Growth"),
    ("creating", "Creating & Building"),
    ("fun", "Fun & Adventure"),
    ("purpose", "Purpose & Contribution"),
]

NORTH_LIGHT_EXAMPLES = {
    "health": ("Remain healthy, capable and energetic enough that age does not unnecessarily restrict what I can do.",
               "Freedom and independence."),
    "finance": ("Build enough financial independence that paid work increasingly becomes a choice rather than a requirement.",
                "Choice and control over my time."),
    "work": ("Do interesting, useful and intellectually challenging work with considerable autonomy.",
             "Autonomy and mastery."),
    "creating": ("Regularly turn ideas into real things.",
                 "Expression, curiosity and the enjoyment of building."),
    "relationships": ("Stay genuinely close to the people who matter most.",
                      "Connection with people who matter."),
}


class LifeArea(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="life_areas")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, help_text="Inactive areas are archived, not deleted — history is kept.")
    template_key = models.CharField(max_length=32, blank=True, help_text="Which default area this came from, if any.")
    # Directional and relatively timeless — deliberately NOT a SMART goal.
    north_light = models.TextField(blank=True, help_text="What does “good” ultimately look like in this part of your life?")
    why = models.TextField(blank=True, help_text="Why does this matter?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [models.Index(fields=["user", "is_active", "sort_order"])]

    def __str__(self) -> str:
        return self.name

    @property
    def examples(self) -> tuple[str, str] | None:
        return NORTH_LIGHT_EXAMPLES.get(self.template_key)


# --------------------------------------------------------------------------- #
# Personal Years
# --------------------------------------------------------------------------- #

class PersonalYear(models.Model):
    STATUS_PLANNING = "planning"
    STATUS_ACTIVE = "active"
    STATUS_COMPLETED = "completed"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_PLANNING, "Planning"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="personal_years")
    title = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PLANNING, db_index=True)
    foundation_start_date = models.DateField(
        null=True, blank=True,
        help_text="Optional runway before the year starts: baselines, measurements, habit tests, choosing focus.",
    )
    notes = models.TextField(blank=True)
    reflection = models.TextField(blank=True, help_text="Summary written at the end of the year.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gt=models.F("start_date")), name="personal_year_end_after_start"),
            # One Active year per user at a time — the dashboard hinges on it.
            models.UniqueConstraint(fields=["user"], condition=Q(status="active"), name="one_active_personal_year_per_user"),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def is_active(self) -> bool:
        return self.status == self.STATUS_ACTIVE

    @property
    def length_days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    def days_remaining(self, today: date | None = None) -> int:
        today = today or timezone.localdate()
        return max(0, (self.end_date - today).days)

    def days_elapsed(self, today: date | None = None) -> int:
        today = today or timezone.localdate()
        return min(self.length_days, max(0, (today - self.start_date).days))

    def progress_pct(self, today: date | None = None) -> int:
        return int(round(100 * self.days_elapsed(today) / self.length_days)) if self.length_days else 0

    def contains(self, day: date) -> bool:
        return self.start_date <= day <= self.end_date

    def in_foundation(self, today: date | None = None) -> bool:
        today = today or timezone.localdate()
        return bool(self.foundation_start_date) and self.foundation_start_date <= today < self.start_date

    def quarter_for(self, day: date) -> int | None:
        """1–4 for a day inside the year; quarters are equal slices of the year."""
        if not self.contains(day):
            return None
        q_len = self.length_days / 4
        return min(4, int((day - self.start_date).days // q_len) + 1)


# --------------------------------------------------------------------------- #
# Assessments (per year, per area) + score history
# --------------------------------------------------------------------------- #

class StrategicMode(models.TextChoices):
    IMPROVE = "improve", "Improve"
    PROTECT = "protect", "Protect"
    MAINTAIN = "maintain", "Maintain"
    EXPLORE = "explore", "Explore"
    DEEMPHASIZE = "deemphasize", "De-emphasize"


MODE_GUIDANCE = {
    StrategicMode.IMPROVE: "This area deserves deliberate attention and movement this year.",
    StrategicMode.PROTECT: "This is working. The job is to keep it working — not to turn a 9 into a 10.",
    StrategicMode.MAINTAIN: "Good enough for now. Keep it ticking over without major investment.",
    StrategicMode.EXPLORE: "Unclear what you want here yet. Try things; decide later.",
    StrategicMode.DEEMPHASIZE: "Consciously giving this less attention for now. That is a legitimate choice.",
}


class LifeAreaAssessment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assessments")
    personal_year = models.ForeignKey(PersonalYear, on_delete=models.CASCADE, related_name="assessments")
    life_area = models.ForeignKey(LifeArea, on_delete=models.CASCADE, related_name="assessments")
    satisfaction = models.PositiveSmallIntegerField(validators=SCORE_VALIDATORS, help_text="How satisfied am I with this area today? (1–10)")
    importance = models.PositiveSmallIntegerField(validators=SCORE_VALIDATORS, help_text="How important is this area to me? (1–10)")
    strategic_mode = models.CharField(max_length=16, choices=StrategicMode.choices, default=StrategicMode.MAINTAIN)
    annual_vision = models.TextField(
        blank=True,
        help_text="If this area had genuinely improved by the end of this Personal Year, what would be true?",
    )
    assessment_date = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["life_area__sort_order", "life_area_id"]
        constraints = [
            models.UniqueConstraint(fields=["personal_year", "life_area"], name="one_assessment_per_area_per_year"),
        ]

    def __str__(self) -> str:
        return f"{self.life_area} — {self.personal_year} (S{self.satisfaction}/I{self.importance})"

    @property
    def priority_gap(self) -> int:
        """importance − satisfaction. A signal, not a verdict: positive suggests
        the area may deserve attention; it is never an absolute ranking."""
        return self.importance - self.satisfaction

    @property
    def mode_guidance(self) -> str:
        return MODE_GUIDANCE.get(self.strategic_mode, "")

    def snapshot(self, source: str = "") -> "AssessmentSnapshot":
        """Record the current scores so start-vs-end and trend views survive edits."""
        return AssessmentSnapshot.objects.create(
            assessment=self, satisfaction=self.satisfaction, importance=self.importance,
            strategic_mode=self.strategic_mode, source=source,
        )


class AssessmentSnapshot(models.Model):
    """Point-in-time copy of an assessment's scores. Written on creation and
    whenever a review updates scores, so history is never overwritten."""
    assessment = models.ForeignKey(LifeAreaAssessment, on_delete=models.CASCADE, related_name="snapshots")
    satisfaction = models.PositiveSmallIntegerField(validators=SCORE_VALIDATORS)
    importance = models.PositiveSmallIntegerField(validators=SCORE_VALIDATORS)
    strategic_mode = models.CharField(max_length=16, choices=StrategicMode.choices)
    source = models.CharField(max_length=40, blank=True, help_text="e.g. onboarding, monthly review, annual review")
    taken_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["taken_at"]

    @property
    def priority_gap(self) -> int:
        return self.importance - self.satisfaction


# --------------------------------------------------------------------------- #
# Goals, relationships, 90-day milestones
# --------------------------------------------------------------------------- #

class WorkStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Not Started"
    IN_PROGRESS = "in_progress", "In Progress"
    AT_RISK = "at_risk", "At Risk"
    COMPLETE = "complete", "Complete"
    PAUSED = "paused", "Paused"
    DROPPED = "dropped", "Dropped"


OPEN_STATUSES = (WorkStatus.NOT_STARTED, WorkStatus.IN_PROGRESS, WorkStatus.AT_RISK)


class GoalType(models.TextChoices):
    OUTCOME = "outcome", "Outcome Goal"
    PROCESS = "process", "Process Goal"
    MILESTONE = "milestone", "Milestone"
    EXPERIENCE = "experience", "Experience"
    MAINTENANCE = "maintenance", "Maintenance / Protection"


GOAL_TYPE_HELP = {
    GoalType.OUTCOME: "A result you want to be true, e.g. “Investment portfolio reaches $200,000.” Often affected by factors outside your control.",
    GoalType.PROCESS: "A behaviour you control, e.g. “Invest $X every month.” Process goals usually support an outcome goal.",
    GoalType.MILESTONE: "A discrete event, e.g. “Book the family trip.”",
    GoalType.EXPERIENCE: "Something to live through, e.g. “Four genuinely memorable experiences this year.”",
    GoalType.MAINTENANCE: "Keep something that already works, e.g. “Protect Friday afternoons.” Protecting is legitimate.",
}


class Goal(models.Model):
    PRIORITY_CHOICES = [(1, "High"), (2, "Medium"), (3, "Low")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="goals")
    personal_year = models.ForeignKey(PersonalYear, on_delete=models.CASCADE, related_name="goals")
    life_area = models.ForeignKey(LifeArea, on_delete=models.CASCADE, related_name="goals")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    goal_type = models.CharField(max_length=16, choices=GoalType.choices, default=GoalType.OUTCOME)
    baseline = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    target = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    target_unit = models.CharField(max_length=40, blank=True, help_text="e.g. $, km, minutes, sessions")
    current_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    target_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=WorkStatus.choices, default=WorkStatus.NOT_STARTED, db_index=True)
    priority = models.PositiveSmallIntegerField(choices=PRIORITY_CHOICES, default=2)
    progress_percentage = models.PositiveSmallIntegerField(
        default=0, validators=PCT_VALIDATORS,
        help_text="Manual progress, used when there is no numeric baseline/target.",
    )
    notes = models.TextField(blank=True)
    completed_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["priority", "target_date", "id"]
        indexes = [models.Index(fields=["user", "personal_year", "status"])]

    def __str__(self) -> str:
        return self.title

    @property
    def is_open(self) -> bool:
        return self.status in OPEN_STATUSES

    @property
    def has_measure(self) -> bool:
        return self.baseline is not None and self.target is not None and self.target != self.baseline

    def progress(self) -> int:
        """0–100. Complete → 100; numeric goals interpolate current between
        baseline and target (works for decreasing targets too); otherwise the
        manual percentage."""
        if self.status == WorkStatus.COMPLETE:
            return 100
        if self.has_measure and self.current_value is not None:
            span = self.target - self.baseline
            done = (self.current_value - self.baseline) / span
            return int(max(Decimal(0), min(Decimal(1), done)) * 100)
        return int(self.progress_percentage)

    def save(self, *args, **kwargs):
        if self.status == WorkStatus.COMPLETE and not self.completed_date:
            self.completed_date = timezone.localdate()
        if self.status != WorkStatus.COMPLETE:
            self.completed_date = None
        super().save(*args, **kwargs)


class GoalRelationship(models.Model):
    """Outcome goal ← supported by → process goal. Optional, never mandatory."""
    outcome_goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name="supporting_links")
    process_goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name="supports_links")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["outcome_goal", "process_goal"], name="unique_goal_link"),
            models.CheckConstraint(condition=~Q(outcome_goal=models.F("process_goal")), name="goal_cannot_support_itself"),
        ]

    def __str__(self) -> str:
        return f"{self.process_goal} → {self.outcome_goal}"


class Milestone(models.Model):
    """A 90-day milestone / project that makes an annual goal actionable."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="milestones")
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    quarter = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(4)],
                                               help_text="Quarter of the Personal Year, if you think in quarters.")
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=WorkStatus.choices, default=WorkStatus.NOT_STARTED, db_index=True)
    progress_percentage = models.PositiveSmallIntegerField(default=0, validators=PCT_VALIDATORS)
    notes = models.TextField(blank=True)
    completed_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "id"]

    def __str__(self) -> str:
        return self.title

    @property
    def is_open(self) -> bool:
        return self.status in OPEN_STATUSES

    def progress(self) -> int:
        return 100 if self.status == WorkStatus.COMPLETE else int(self.progress_percentage)

    def save(self, *args, **kwargs):
        if self.status == WorkStatus.COMPLETE and not self.completed_date:
            self.completed_date = timezone.localdate()
        if self.status != WorkStatus.COMPLETE:
            self.completed_date = None
        super().save(*args, **kwargs)


# --------------------------------------------------------------------------- #
# Habits (simple completion tracking — deliberately not a habit platform)
# --------------------------------------------------------------------------- #

class FrequencyType(models.TextChoices):
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    TIMES_PER_WEEK = "times_per_week", "X times per week"
    MONTHLY = "monthly", "Monthly"
    TIMES_PER_MONTH = "times_per_month", "X times per month"


class Habit(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="habits")
    life_area = models.ForeignKey(LifeArea, on_delete=models.CASCADE, related_name="habits")
    goal = models.ForeignKey(Goal, null=True, blank=True, on_delete=models.SET_NULL, related_name="habits")
    title = models.CharField(max_length=200)
    frequency_type = models.CharField(max_length=20, choices=FrequencyType.choices, default=FrequencyType.WEEKLY)
    frequency_target = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["life_area__sort_order", "title"]

    def __str__(self) -> str:
        return self.title

    @property
    def target_per_period(self) -> int:
        if self.frequency_type in (FrequencyType.DAILY, FrequencyType.WEEKLY, FrequencyType.MONTHLY):
            return 1
        return self.frequency_target

    @property
    def period_label(self) -> str:
        return {
            FrequencyType.DAILY: "today",
            FrequencyType.WEEKLY: "this week",
            FrequencyType.TIMES_PER_WEEK: "this week",
            FrequencyType.MONTHLY: "this month",
            FrequencyType.TIMES_PER_MONTH: "this month",
        }[self.frequency_type]

    def period_bounds(self, today: date | None = None) -> tuple[date, date]:
        today = today or timezone.localdate()
        if self.frequency_type == FrequencyType.DAILY:
            return today, today
        if self.frequency_type in (FrequencyType.WEEKLY, FrequencyType.TIMES_PER_WEEK):
            start = today - timedelta(days=today.weekday())
            return start, start + timedelta(days=6)
        start = today.replace(day=1)
        nxt = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        return start, nxt - timedelta(days=1)

    def period_count(self, today: date | None = None) -> int:
        start, end = self.period_bounds(today)
        agg = self.checkins.filter(date__range=(start, end)).aggregate(total=models.Sum("count"))
        return int(agg["total"] or 0)

    def period_done(self, today: date | None = None) -> bool:
        return self.period_count(today) >= self.target_per_period


class HabitCheckin(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="checkins")
    date = models.DateField(default=timezone.localdate)
    count = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["-date"]
        constraints = [models.UniqueConstraint(fields=["habit", "date"], name="one_checkin_per_habit_per_day")]

    def __str__(self) -> str:
        return f"{self.habit} on {self.date} ×{self.count}"


# --------------------------------------------------------------------------- #
# Reviews
# --------------------------------------------------------------------------- #

class ReviewType(models.TextChoices):
    MONTHLY = "monthly", "Monthly Review"
    QUARTERLY = "quarterly", "Quarterly Review"
    ANNUAL = "annual", "Annual Review"
    LIFE = "life", "Life Review"


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    personal_year = models.ForeignKey(PersonalYear, on_delete=models.CASCADE, related_name="reviews")
    review_type = models.CharField(max_length=12, choices=ReviewType.choices, db_index=True)
    review_date = models.DateField(default=timezone.localdate)
    period_label = models.CharField(max_length=40, blank=True, help_text="e.g. “September 2027”, “Q3”")

    # Monthly
    moved_forward = models.TextField(blank=True, verbose_name="What moved forward?")
    stalled = models.TextField(blank=True, verbose_name="What stalled?")
    surprised = models.TextField(blank=True, verbose_name="What surprised me?")
    attention_next = models.TextField(blank=True, verbose_name="What deserves attention next?")
    no_longer_relevant = models.TextField(blank=True, verbose_name="Are any goals no longer relevant?")
    # Quarterly / Life
    priorities_changed = models.TextField(blank=True, verbose_name="Have my priorities changed?")
    north_light_check = models.TextField(blank=True, verbose_name="Does the North Light still feel correct? Is this still what I want?")
    # Annual
    lessons = models.TextField(blank=True, verbose_name="Lessons")
    major_events = models.TextField(blank=True, verbose_name="Major events")
    carry_forward = models.TextField(blank=True, verbose_name="What carries forward?")

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-review_date", "-id"]

    def __str__(self) -> str:
        return f"{self.get_review_type_display()} — {self.period_label or self.review_date}"

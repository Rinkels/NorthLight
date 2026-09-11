"""Admin for support/development inspection. Normal users never need this.
Free-text reflections are shown but never logged; no secrets are exposed."""
from django.contrib import admin

from .models import (
    AssessmentSnapshot, Goal, GoalRelationship, Habit, HabitCheckin, LifeArea,
    LifeAreaAssessment, Milestone, PersonalYear, Review, UserProfile,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "year_start_type", "review_cadence", "onboarding_complete", "updated_at")
    list_filter = ("year_start_type", "review_cadence", "onboarding_complete")
    search_fields = ("user__username", "user__email", "display_name")
    ordering = ("user__username",)


@admin.register(LifeArea)
class LifeAreaAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "sort_order", "is_active", "template_key", "updated_at")
    list_filter = ("is_active", "template_key")
    search_fields = ("name", "user__username")
    ordering = ("user", "sort_order")


@admin.register(PersonalYear)
class PersonalYearAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "start_date", "end_date", "status", "foundation_start_date")
    list_filter = ("status",)
    search_fields = ("title", "user__username")
    ordering = ("user", "-start_date")
    date_hierarchy = "start_date"


class SnapshotInline(admin.TabularInline):
    model = AssessmentSnapshot
    extra = 0
    readonly_fields = ("satisfaction", "importance", "strategic_mode", "source", "taken_at")
    can_delete = False


@admin.register(LifeAreaAssessment)
class LifeAreaAssessmentAdmin(admin.ModelAdmin):
    list_display = ("life_area", "personal_year", "user", "satisfaction", "importance", "gap", "strategic_mode", "assessment_date")
    list_filter = ("strategic_mode", "personal_year__status")
    search_fields = ("life_area__name", "user__username", "personal_year__title")
    ordering = ("user", "personal_year", "life_area__sort_order")
    inlines = [SnapshotInline]

    @admin.display(description="Gap")
    def gap(self, obj):
        return obj.priority_gap


class MilestoneInline(admin.TabularInline):
    model = Milestone
    extra = 0
    fields = ("title", "quarter", "due_date", "status", "progress_percentage")


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "personal_year", "life_area", "goal_type", "status", "priority", "target_date", "progress_display")
    list_filter = ("status", "goal_type", "priority", "personal_year__status")
    search_fields = ("title", "user__username", "life_area__name")
    ordering = ("user", "personal_year", "priority")
    inlines = [MilestoneInline]

    @admin.display(description="Progress")
    def progress_display(self, obj):
        return f"{obj.progress()}%"


@admin.register(GoalRelationship)
class GoalRelationshipAdmin(admin.ModelAdmin):
    list_display = ("outcome_goal", "process_goal", "created_at")
    search_fields = ("outcome_goal__title", "process_goal__title")


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "goal", "quarter", "due_date", "status", "progress_percentage")
    list_filter = ("status", "quarter")
    search_fields = ("title", "goal__title", "user__username")
    ordering = ("user", "due_date")


class CheckinInline(admin.TabularInline):
    model = HabitCheckin
    extra = 0


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "life_area", "goal", "frequency_type", "frequency_target", "is_active")
    list_filter = ("frequency_type", "is_active")
    search_fields = ("title", "user__username")
    inlines = [CheckinInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("review_type", "period_label", "review_date", "user", "personal_year")
    list_filter = ("review_type",)
    search_fields = ("user__username", "personal_year__title", "period_label")
    ordering = ("-review_date",)
    date_hierarchy = "review_date"

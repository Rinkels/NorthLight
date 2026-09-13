from django.urls import path

from .views import areas, calendar, core, design, export, goals, onboarding, reviews, years

app_name = "planning"

urlpatterns = [
    path("", core.dashboard, name="dashboard"),
    path("signup/", core.signup, name="signup"),
    path("settings/", core.profile, name="profile"),
    path("scores/", core.dashboard_scores, name="dashboard_scores"),
    path("history/", core.history, name="history"),
    path("calendar/", calendar.calendar_view, name="calendar"),
    path("calendar/<int:year>/<int:month>/", calendar.calendar_view, name="calendar_month"),
    path("design/", design.design_life, name="design_life"),
    path("design/<int:index>/", design.design_life, name="design_life_step"),
    path("design/done/", design.design_life_done, name="design_life_done"),
    path("export/", export.export_page, name="export"),
    path("export/json/", export.export_json, name="export_json"),
    path("export/scores.csv", export.export_scores_csv, name="export_scores_csv"),
    path("export/goals.csv", export.export_goals_csv, name="export_goals_csv"),
    path("onboarding/<int:step>/", onboarding.onboarding, name="onboarding"),

    # Life areas
    path("areas/", areas.area_list, name="area_list"),
    path("areas/reorder/", areas.area_reorder, name="area_reorder"),
    path("areas/restore-defaults/", areas.area_restore_defaults, name="area_restore_defaults"),
    path("areas/<int:pk>/", areas.area_detail, name="area_detail"),
    path("areas/<int:pk>/edit/", areas.area_edit, name="area_edit"),
    path("areas/<int:pk>/archive/", areas.area_archive, name="area_archive"),
    path("areas/<int:pk>/restore/", areas.area_restore, name="area_restore"),
    path("areas/<int:pk>/north-light/", areas.area_northlight, name="area_northlight"),
    path("areas/<int:pk>/assess/", areas.area_assess, name="area_assess"),

    # Personal years
    path("years/", years.year_list, name="year_list"),
    path("years/new/", years.year_create, name="year_create"),
    path("years/<int:pk>/", years.year_detail, name="year_detail"),
    path("years/<int:pk>/edit/", years.year_edit, name="year_edit"),
    path("years/<int:pk>/activate/", years.year_activate, name="year_activate"),
    path("years/<int:pk>/complete/", years.year_complete, name="year_complete"),
    path("years/<int:pk>/archive/", years.year_archive, name="year_archive"),
    path("years/<int:pk>/next/", years.year_next, name="year_next"),

    # Goals
    path("goals/", goals.goal_list, name="goal_list"),
    path("goals/new/", goals.goal_create, name="goal_create"),
    path("goals/<int:pk>/", goals.goal_detail, name="goal_detail"),
    path("goals/<int:pk>/edit/", goals.goal_edit, name="goal_edit"),
    path("goals/<int:pk>/delete/", goals.goal_delete, name="goal_delete"),
    path("goals/<int:pk>/status/", goals.goal_status, name="goal_status"),
    path("goals/<int:pk>/link/", goals.goal_link, name="goal_link"),
    path("goals/<int:pk>/unlink/<int:other_pk>/", goals.goal_unlink, name="goal_unlink"),
    path("goals/<int:goal_pk>/milestones/new/", goals.milestone_create, name="milestone_create"),
    path("milestones/", goals.milestone_list, name="milestone_list"),
    path("milestones/<int:pk>/edit/", goals.milestone_edit, name="milestone_edit"),
    path("milestones/<int:pk>/delete/", goals.milestone_delete, name="milestone_delete"),

    # Habits
    path("habits/", goals.habit_list, name="habit_list"),
    path("habits/new/", goals.habit_create, name="habit_create"),
    path("habits/<int:pk>/edit/", goals.habit_edit, name="habit_edit"),
    path("habits/<int:pk>/delete/", goals.habit_delete, name="habit_delete"),
    path("habits/<int:pk>/checkin/", goals.habit_checkin, name="habit_checkin"),

    # Reviews
    path("reviews/", reviews.review_list, name="review_list"),
    path("reviews/new/<str:kind>/", reviews.review_create, name="review_create"),
    path("reviews/<int:pk>/", reviews.review_detail, name="review_detail"),
    path("reviews/<int:pk>/edit/", reviews.review_edit, name="review_edit"),
    path("reviews/<int:pk>/delete/", reviews.review_delete, name="review_delete"),
]

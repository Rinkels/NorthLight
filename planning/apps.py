from django.apps import AppConfig


class PlanningConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "planning"
    verbose_name = "Planning"

    def ready(self):
        from . import signals  # noqa: F401 — connects the profile auto-create signal

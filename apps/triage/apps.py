"""
apps/triage/apps.py

Registers the pre_save signal for coordinate enrichment when the app loads.
"""

from django.apps import AppConfig


class TriageConfig(AppConfig):
    name = "apps.triage"
    verbose_name = "Triage"

    def ready(self):
        import apps.triage.signals  # noqa: F401  — registers pre_save handler
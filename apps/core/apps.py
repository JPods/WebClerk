from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"
    label = "core"

    def ready(self):
        # Initialize WCAPI registry
        try:
            from .wcapi import registry
            registry.refresh_from_settings()
        except Exception:
            pass

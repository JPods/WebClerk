from django.apps import AppConfig


class SupportConfig(AppConfig):
    name = "apps.support"
    verbose_name = "Support"

    def ready(self):
        try:
            from .signals import register_action_signals
            register_action_signals()
        except Exception:
            # Avoid startup errors if Action model not ready
            pass

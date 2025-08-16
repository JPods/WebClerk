# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/apps.py
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        import core.signals.pending_trigger  # Ensures signals are registered

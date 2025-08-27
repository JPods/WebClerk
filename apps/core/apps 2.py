# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/apps.py
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
<<<<<<< HEAD:core/apps.py
    name = 'core'

    def ready(self):
        import core.signals.pending_trigger  # Ensures signals are registered
=======
    name = 'apps.core'
>>>>>>> 01558f6ebce5d18d828e022158343627fc8162d8:apps/core/apps.py

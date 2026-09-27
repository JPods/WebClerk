from django.apps import AppConfig


class SyncConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sync'

    def ready(self):
        # Import on one route: preview, approve, import as commands on a bundle (plan §17.13).
        from .services import bundle_import
        bundle_import.register()

from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"
    label = "core"

    def ready(self):
        # Initialize WCAPI registry
        try:
            from apps.core.utils import registry
            registry.refresh_from_settings()
        except Exception:
            pass

        # Load all settings into Redis cache asynchronously at app startup
        try:
            from .tasks.cache_tasks import update_all_settings_cache
            update_all_settings_cache.delay()
        except Exception:
            pass  # Graceful degradation if settings cache fails


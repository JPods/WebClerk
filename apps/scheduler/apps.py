from django.apps import AppConfig


class SchedulerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.scheduler'
    verbose_name = 'Scheduler'

    def ready(self):
        # Import tasks to register with Celery
        from . import tasks  # noqa: F401

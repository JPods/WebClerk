__all__ = []  # intentionally empty to avoid early model imports during Django app loading
"""Common app init: ensure signals registered."""

from django.apps import AppConfig


class CommonConfig(AppConfig):
	name = 'common'
	verbose_name = 'Common'

	def ready(self):  # pragma: no cover
		# Import signals to connect receivers
		from . import signals  # noqa: F401
		# Register system checks (copilot instruction sync, etc.)
		from . import checks  # noqa: F401
		# Register periodic tasks (Celery Beat) lazily after app ready
		try:
			from django_celery_beat.models import PeriodicTask, IntervalSchedule
			# Ensure interval (every 10 minutes) exists
			schedule, _ = IntervalSchedule.objects.get_or_create(every=10, period=IntervalSchedule.MINUTES)
			PeriodicTask.objects.get_or_create(
				name='refresh_keywords_periodic',
				defaults={
					'interval': schedule,
					'task': 'common.tasks.refresh_keywords_task',
				}
			)
		except Exception:
			# Silent fail during migrate / first setup
			pass

# Backward compatibility (Django <3.2 style) if INSTALLED_APPS uses 'common'
default_app_config = 'common.CommonConfig'

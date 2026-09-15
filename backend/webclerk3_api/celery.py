"""
Celery application for webclerk3.

Creates the Celery app instance and configures it from Django settings.
Auto-discovers tasks in all INSTALLED_APPS.
"""
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')

app = Celery('webclerk3_api')

# Read config from Django settings; all celery-related keys must use CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks.py in all installed apps
app.autodiscover_tasks()

# Explicitly register task modules not under direct INSTALLED_APPS
app.autodiscover_tasks(['apps.support.scheduler'])


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Verify Celery is working: celery -A webclerk3_api call webclerk3_api.celery.debug_task"""
    print(f'Request: {self.request!r}')

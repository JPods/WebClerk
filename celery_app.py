# Each Celery worker process will execute the code 
# in celery_app.py when it starts, 
# so the single import and call is sufficient for every worker.
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webClerk3.settings')

app = Celery('webClerk3')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Ensure access rules are loaded for Celery workers
from core.services import view_edit_access
view_edit_access.reload_access_data()



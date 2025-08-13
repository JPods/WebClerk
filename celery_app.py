import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webClerk3.settings')

app = Celery('webClerk3')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Ensure access rules are loaded for Celery workers
from core.services import access_fields
access_fields.reload_access_data()

# Ensure access rules are loaded for Celery workers
from core.services import access_fields
access_fields.reload_access_data()


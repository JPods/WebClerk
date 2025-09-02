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
from apps.core.services import view_edit_access
# Replace 'reload_access_data' with the correct function or attribute from view_edit_access
# For example, if the correct function is 'load_access_data', use:
# view_edit_access.load_access_data()
# If no such function exists, remove or update this line accordingly.



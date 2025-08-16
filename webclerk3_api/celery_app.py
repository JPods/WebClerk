# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/webclerk3_api/celery_app.py
import os
from celery import Celery

# 3 terminals named celery, redis, python
# % redis-server
# % celery -A webclerk3_api worker -l info

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')

app = Celery('webclerk3_api')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
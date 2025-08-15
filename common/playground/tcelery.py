import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')  # Adjust to your settings module

import django

django.setup()

from celery import Celery


#Step	Command/Action
#Start Redis	redis-server
#Start Celery worker in webclerk3	celery -A common.tcelery worker -l info
# Start Celery worker in common celery -A common.tcelery worker -l info
#Python shell	python
#Test task	from common.tcelery import reverse; reverse.delay("abc")




app = Celery('common', broker='redis://localhost:6379/0')

@app.task
def reverse(text):
    print(f"Reversing: {text}")
    return text[::-1]

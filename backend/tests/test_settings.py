import os
import django
from django.conf import settings

os.environ['DJANGO_SETTINGS_MODULE'] = 'project_name.settings'
django.setup()

INSTALLED_APPS = [
    # Add your apps here
]
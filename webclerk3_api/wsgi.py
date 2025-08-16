# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/webclerk3_api/wsgi.py
"""
WSGI config for webclerk3_api project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')

application = get_wsgi_application()

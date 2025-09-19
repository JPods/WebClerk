"""
ASGI config for webclerk3_api project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')

from django.core.asgi import get_asgi_application

application = get_asgi_application()

#Tip: You can call load_keyword_requirements() in your 
# AppConfig’s ready() method and cache the result.

from apps.core.models.setting import Setting
from django.core.cache import cache
from django.db import connection

def load_keyword_requirements():
    # Load all active keyword requirements once at startup
    requirements = {}
    for setting in Setting.objects.filter(purpose="keywords_from", is_active=True):
        requirements[setting.table_name] = setting.data
    return requirements

def get_keyword_requirements():
    try:
        requirements = cache.get('keyword_requirements')
        if requirements is None:
            requirements = load_keyword_requirements()
            cache.set('keyword_requirements', requirements, timeout=3600)
        return requirements
    except Exception as e:
        # If the settings or django_content_type table does not exist, return empty dict
        error_str = str(e)
        if (
            hasattr(e, 'pgcode') or
            'relation "settings" does not exist' in error_str or
            'relation "django_content_type" does not exist' in error_str
        ):
            return {}
        raise
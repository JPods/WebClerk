#Tip: You can call load_keyword_requirements() in your 
# AppConfig’s ready() method and cache the result.

from apps.core.models.setting import Setting
from apps.core.services.cache_service import cache_service

def load_keyword_requirements():
    # Load all active keyword requirements once at startup
    # Select only columns we need to avoid referencing columns that may not exist in early migrations
    requirements = {}
    qs = Setting.objects.filter(purpose="refs_setup", is_active=True).only("model_name", "data")
    for setting in qs:
        key = getattr(setting, 'model_name', None)
        if key:
            requirements[key] = setting.data
    return requirements

def get_keyword_requirements():
    try:
        cache_key = cache_service.make_key('keywords', 'requirements')
        requirements = cache_service.get(cache_key)
        if requirements is None:
            requirements = load_keyword_requirements()
            cache_service.set(cache_key, requirements, ttl=3600)
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
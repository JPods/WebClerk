#Tip: You can call load_keyword_requirements() in your 
# AppConfig’s ready() method and cache the result.
import logging

logger = logging.getLogger(__name__)

from apps.core.models.setting import Setting
from apps.core.services.cache_service import cache_service

def load_keyword_requirements():
    """Load keyword requirements from wc:model config.search sections."""
    try:
        import time
        start_time = time.time()
        timeout = 10  # 10 second timeout

        requirements = {}
        # Read search config from wc:model records
        qs = Setting.objects.filter(purpose="wc:model", is_active=True)

        for setting in qs:
            if time.time() - start_time > timeout:
                logger.warning("Timeout reached loading keyword requirements")
                break

            key = getattr(setting, 'parent_model', None)
            if key:
                search = (setting.config or {}).get('search')
                if search:
                    requirements[key] = search

        # Legacy fallback — check for any remaining wc:keywords records
        if not requirements:
            for setting in Setting.objects.filter(purpose="wc:keywords", is_active=True):
                key = getattr(setting, 'parent_model', None)
                if key:
                    requirements[key] = setting.config

        logger.info("Loaded keyword requirements for %d models in %.2fs", len(requirements), time.time() - start_time)
        return requirements
    except Exception as e:
        logger.error("Error loading keyword requirements: %s", e)
        return {}

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
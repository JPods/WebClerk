#Tip: You can call load_keyword_requirements() in your 
# AppConfig’s ready() method and cache the result.
import logging
console_logger = logging.getLogger('console')  # Console logger for debugging

from apps.core.models.setting import Setting
from apps.core.services.cache_service import cache_service

def load_keyword_requirements():
    """Load keyword requirements with timeout and error handling."""
    try:
        import time
        start_time = time.time()
        timeout = 10  # 10 second timeout
        
        requirements = {}
        # Use basic query without .only() to avoid hanging
        qs = Setting.objects.filter(purpose__in=["refs_setup", "ref_seup"], is_active=True)
        
        for setting in qs:
            # Check timeout
            if time.time() - start_time > timeout:
                print(f"[KEYWORDS] Timeout reached, stopping keyword requirements loading")
                break
                
            key = getattr(setting, 'model_target', None)
            if key:
                requirements[key] = setting.data
        
        print(f"[KEYWORDS] Loaded requirements for {len(requirements)} models in {time.time() - start_time:.2f}s")
        return requirements
    except Exception as e:
        print(f"[KEYWORDS] Error loading requirements: {e}")
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
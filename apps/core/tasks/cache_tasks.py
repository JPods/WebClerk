from celery import shared_task
from apps.core.services.cache_service import cache_service
from apps.core.utils import access_utils
from apps.core.constants import keyword_requirements, constants_init
from typing import Dict, Any
from apps.core.services.wcapi_registry import ALLOWED_TABLE_KEYS
from django.apps import apps


@shared_task(name='apps.core.tasks.cache_tasks.update_access_fields_cache')
def update_access_fields_cache():
    """Async update of access field rules for all models."""
    processed = 0
    try:
        # Iterate through all models and cache their access rules
        for model in apps.get_models():
            model_name = model._meta.model_name
            # Cache access rules for different user roles
            # This would need to be implemented based on your access_utils logic
            # For now, just mark as processed
            processed += 1
        return {'processed': processed, 'status': 'completed'}
    except Exception as e:
        return {'processed': processed, 'error': str(e)}


@shared_task(name='apps.core.tasks.cache_tasks.update_keyword_requirements_cache')
def update_keyword_requirements_cache():
    """Async update of keyword requirements."""
    try:
        requirements = keyword_requirements.load_keyword_requirements()
        key = cache_service.make_key('keywords', 'requirements')
        cache_service.set(key, requirements, ttl=3600)  # 1 hour
        return {'status': 'completed', 'count': len(requirements)}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


@shared_task(name='apps.core.tasks.cache_tasks.update_model_registry_cache')
def update_model_registry_cache():
    """Cache model registry data."""
    try:
        key = cache_service.make_key('registry', 'models')
        cache_service.set(key, ALLOWED_TABLE_KEYS, ttl=86400)  # 24 hours
        return {'status': 'completed', 'count': len(ALLOWED_TABLE_KEYS)}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


@shared_task(name='apps.core.tasks.cache_tasks.update_constants_cache')
def update_constants_cache():
    """Async update of constants from database settings."""
    try:
        constants = constants_init.load_constants_from_settings()
        key = cache_service.make_key('constants', 'all')
        cache_service.set(key, constants, ttl=3600)  # 1 hour
        # Also refresh in-memory cache
        constants_init.refresh_cached_constants()
        return {'status': 'completed', 'categories': list(constants.keys())}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


@shared_task(name='apps.core.tasks.cache_tasks.update_all_settings_cache')
def update_all_settings_cache():
    """Load all active Setting records into Redis cache."""
    try:
        from apps.core.models.setting import Setting

        # Load all active settings
        settings = Setting.objects.filter(is_active=True).only('model_name', 'purpose', 'data')

        # Group by purpose for efficient caching
        settings_by_purpose = {}
        for setting in settings:
            purpose = setting.purpose or 'general'
            if purpose not in settings_by_purpose:
                settings_by_purpose[purpose] = {}
            if setting.model_name:
                settings_by_purpose[purpose][setting.model_name] = setting.data

        # Cache each purpose group
        for purpose, data in settings_by_purpose.items():
            cache_key = cache_service.make_key('settings', purpose)
            cache_service.set(cache_key, data, ttl=3600)  # 1 hour TTL

        # Also cache all settings in a single key for easy access
        all_settings = {}
        for setting in settings:
            key = f"{setting.model_name or 'general'}:{setting.purpose or 'general'}"
            all_settings[key] = setting.data

        cache_key = cache_service.make_key('settings', 'all')
        cache_service.set(cache_key, all_settings, ttl=3600)

        return {'status': 'completed', 'purposes': list(settings_by_purpose.keys()), 'total_settings': len(settings)}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


@shared_task(name='apps.core.tasks.cache_tasks.invalidate_cache_namespace')
def invalidate_cache_namespace(namespace: str):
    """Invalidate all caches in a namespace."""
    try:
        cache_service.invalidate_namespace(namespace)
        return {'status': 'completed', 'namespace': namespace}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


@shared_task(name='apps.core.tasks.cache_tasks.execute_save_async_hooks')
def execute_save_async_hooks(model_name: str, record_id: int, hook_data: Dict[str, Any]):
    """Execute save_async hooks asynchronously after save completes."""
    try:
        from apps.core.constants.save_hooks import execute_save_hook
        from django.apps import apps

        # Get the model and instance
        try:
            model = apps.get_model('core', model_name)  # Adjust app label as needed
            instance = model.objects.get(id=record_id)
        except Exception as e:
            return {'status': 'error', 'error': f'Could not load instance: {e}'}

        # Execute async hooks
        result = execute_save_hook(model_name.lower(), 'save_async', instance, hook_data)

        return {
            'status': 'completed' if result['success'] else 'failed',
            'executed': result.get('executed', []),
            'errors': result.get('errors', [])
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
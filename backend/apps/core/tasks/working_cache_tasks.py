"""
Working cache population function that avoids the problematic .only() query.
"""
import time
import logging

logger = logging.getLogger(__name__)


    # Purposes needed at startup for request handling.
    # Everything else is lazy-loaded when first accessed.
STARTUP_PURPOSES = {
    'wc:model',  # combined model definition (replaces schema_map, field_access, etc.)
    'wc:field_access', 'wc:schema_map',  # legacy — remove after migration complete
    'wc:workbench_fields', 'wc:db_defaults',
    'wc:keywords', 'wc:search', 'wc:detail_layout', 'wc:selectlist',
    'wc:model_related', 'wc:list_column_config', 'wc:feature',
    'wc:company_profile', 'wc:react_settings',
}


def update_all_settings_cache_working():
    """Load essential Setting records into cache at startup."""
    start_time = time.time()

    try:
        logger.info("Starting working cache population...")

        from apps.core.models.setting import Setting

        logger.info("Querying active settings (startup purposes only)...")
        active_settings = Setting.objects.filter(
            is_active=True, purpose__in=STARTUP_PURPOSES
        )
        
        # Convert to list to force immediate evaluation
        settings_list = list(active_settings)
        logger.info(f"Found {len(settings_list)} active settings")
        
        if not settings_list:
            logger.info("No active settings found, completing successfully")
            return {'status': 'completed', 'message': 'No active settings found', 'total_settings': 0}
        
        # Process settings
        settings_by_purpose = {}
        all_settings = {}
        
        for setting in settings_list:
            purpose = setting.purpose or 'general'
            model_key = setting.parent_model or 'general'
            data = setting.config or {}
            
            # Group by purpose
            if purpose not in settings_by_purpose:
                settings_by_purpose[purpose] = {}
            if model_key:
                settings_by_purpose[purpose][model_key] = data
            
            # Add to all settings
            key = f"{model_key}:{purpose}"
            all_settings[key] = data
        
        # Cache results
        from apps.core.services.cache_service import cache_service
        
        # Cache each purpose group
        cached_purposes = []
        for purpose, data in settings_by_purpose.items():
            try:
                cache_key = cache_service.make_key('settings', purpose)
                cache_service.set(cache_key, data, ttl=3600)
                cached_purposes.append(purpose)
            except Exception as e:
                logger.error(f"Failed to cache purpose {purpose}: {e}")
        
        # Cache all settings
        try:
            cache_key = cache_service.make_key('settings', 'all')
            cache_service.set(cache_key, all_settings, ttl=3600)
        except Exception as e:
            logger.error(f"Failed to cache all settings: {e}")
        
        elapsed = time.time() - start_time
        logger.info(f"Cache population completed in {elapsed:.2f} seconds")
        
        return {
            'status': 'completed', 
            'purposes': cached_purposes, 
            'total_settings': len(settings_list),
            'elapsed': round(elapsed, 2)
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error in cache population after {elapsed:.2f} seconds: {e}")
        import traceback
        traceback.print_exc()
        return {'status': 'error', 'error': str(e), 'elapsed': round(elapsed, 2)}
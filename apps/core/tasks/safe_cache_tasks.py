"""
Safe cache population function with timeout handling.
"""
import time
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def update_all_settings_cache_safe():
    """Load all active Setting records into Redis cache with timeout handling."""
    start_time = time.time()
    timeout = 30  # 30 second timeout
    
    try:
        logger.info("Starting safe cache population...")
        
        # Check timeout
        if time.time() - start_time > timeout:
            return {'status': 'timeout', 'error': 'Operation timed out'}
        
        from apps.core.models.setting import Setting
        logger.info("Setting model imported successfully")
        
        # Check timeout
        if time.time() - start_time > timeout:
            return {'status': 'timeout', 'error': 'Operation timed out during import'}
        
        # Load all active settings with basic query
        logger.info("Querying active settings...")
        settings_query = Setting.objects.filter(is_active=True).only('model_name', 'purpose', 'data')
        
        # Convert to list to avoid lazy evaluation issues
        settings_list = list(settings_query)
        logger.info(f"Found {len(settings_list)} active settings")
        
        # Check timeout
        if time.time() - start_time > timeout:
            return {'status': 'timeout', 'error': 'Operation timed out during query'}
        
        # Process settings
        settings_by_purpose = {}
        all_settings = {}
        
        for setting in settings_list:
            # Check timeout
            if time.time() - start_time > timeout:
                return {'status': 'timeout', 'error': 'Operation timed out during processing'}
                
            purpose = setting.purpose or 'general'
            model_name = setting.model_name or 'general'
            data = setting.data or {}
            
            # Group by purpose
            if purpose not in settings_by_purpose:
                settings_by_purpose[purpose] = {}
            if model_name:
                settings_by_purpose[purpose][model_name] = data
            
            # Add to all settings
            key = f"{model_name}:{purpose}"
            all_settings[key] = data
        
        # Check timeout
        if time.time() - start_time > timeout:
            return {'status': 'timeout', 'error': 'Operation timed out before caching'}
        
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
            'elapsed': elapsed
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error in cache population after {elapsed:.2f} seconds: {e}")
        import traceback
        traceback.print_exc()
        return {'status': 'error', 'error': str(e), 'elapsed': elapsed}
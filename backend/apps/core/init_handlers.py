"""
App initialization handler to populate cache after Django is ready.

Uses post_migrate signal but only runs ONCE (for the core app).
Only caches purposes that are needed at request time — not alice_*
or other operational data.
"""
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from apps.core.tasks.working_cache_tasks import update_all_settings_cache_working
import logging

logger = logging.getLogger(__name__)


@receiver(post_migrate)
def populate_cache_after_migration(sender, **kwargs):
    """Populate cache once — only when the core app's migrations finish."""
    if sender.label != 'core':
        return
    try:
        logger.info("Populating settings cache (core only)...")
        result = update_all_settings_cache_working()
        if result['status'] == 'completed':
            logger.info(f"Cache populated: {result.get('total_settings', 0)} settings loaded")
        else:
            logger.warning(f"Cache population failed: {result.get('error', 'Unknown error')}")
    except Exception as e:
        logger.error(f"Error populating cache: {e}")


def populate_cache_lazily():
    """
    Lazy cache population function.
    Call this when you actually need the cache data.
    """
    try:
        # Check if cache key exists
        from apps.core.services.cache import cache_service
        cache_key = cache_service.make_key('settings', 'all')
        
        if not cache_service.exists(cache_key):
            # Populate cache if not exists
            logger.info("Cache missing, populating...")
            result = update_all_settings_cache_working()
            return result['status'] == 'completed'
        return True
    except Exception as e:
        logger.error(f"Error in lazy cache population: {e}")
        return False
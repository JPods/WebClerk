from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.core.models.setting import Setting
from apps.core.services.cache_service import cache_service

def _dispatch_task(task_name, *args, **kwargs):
    """Safely import apps.core.tasks and call the named task.
    If the attribute is a Celery task use .delay(), otherwise call directly.
    Returns True if a callable was found and invoked, False otherwise.
    """
    try:
        from apps.core import tasks as cache_tasks  # tasks should live at apps/core/tasks.py
    except ImportError:
        return False

    func = getattr(cache_tasks, task_name, None)
    if not callable(func):
        return False

    # If this is a Celery task, prefer .delay(); otherwise call synchronously.
    if hasattr(func, "delay") and callable(getattr(func, "delay")):
        try:
            func.delay(*args, **kwargs)
            return True
        except Exception:
            # If delay fails for any reason, fall back to direct call
            try:
                func(*args, **kwargs)
                return True
            except Exception:
                return False
    else:
        try:
            func(*args, **kwargs)
            return True
        except Exception:
            return False


@receiver([post_save, post_delete], sender=Setting)
def invalidate_setting_caches(sender, instance, **kwargs):
    """Invalidate caches when Setting records change."""
    if instance.purpose == 'view_edit':
        # Invalidate permission caches
        cache_service.invalidate_namespace('permissions')
        # Trigger async update of access rules (or sync fallback)
        if not _dispatch_task('update_access_fields_cache'):
            # Graceful degradation: nothing to do, task module missing or task failed
            pass

    elif instance.purpose == 'refs_setup':
        # Invalidate keyword caches
        cache_service.invalidate_namespace('keywords')
        # Trigger async update of keyword requirements (or sync fallback)
        if not _dispatch_task('update_keyword_requirements_cache'):
            pass  # Graceful degradation

    elif instance.purpose == 'constant_init':
        # Invalidate constants cache
        cache_service.invalidate_namespace('constants')
        # Refresh cached constants
        try:
            from apps.core.constants.constants_init import refresh_cached_constants
            refresh_cached_constants()
        except ImportError:
            pass  # Graceful degradation

    elif instance.purpose == 'save_pre_post':
        # Invalidate save hooks cache for the affected model
        try:
            from apps.core.constants.save_hooks import invalidate_save_hooks_cache
            invalidate_save_hooks_cache(instance.model_name)
        except ImportError:
            pass  # Graceful degradation


@receiver(post_save)
def invalidate_model_caches(sender, instance, **kwargs):
    """Invalidate caches when model instances change that affect cached data."""
    # Add specific invalidation logic for models that affect caches
    # For example, if User model changes, might need to invalidate user-related caches
    pass


# Function to manually invalidate caches (can be called from management commands)
def invalidate_all_caches():
    """Invalidate all application caches."""
    namespaces = ['permissions', 'keywords', 'registry', 'global', 'constants']
    for namespace in namespaces:
        # Try to dispatch a Celery task; if not available, fall back to direct invalidation
        if not _dispatch_task('invalidate_cache_namespace', namespace):
            cache_service.invalidate_namespace(namespace)
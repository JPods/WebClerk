from celery import shared_task
from apps.core.services import view_edit_access
import logging

logger = logging.getLogger(__name__)

@shared_task
def celery_startup_task():
    view_edit_access.reload_access_data()
    print("Access rules loaded in Celery worker.")

@shared_task
def save_pre(model_key, data):
    # Dynamically call a model-specific pre-save task if it exists
    func_name = f"{model_key.rstrip('s')}_save_pre"
    if func_name in globals():
        return globals()[func_name](data)
    # Default: do nothing
    return {'success': True}

@shared_task
def save_post(model_key, data):
    # Dynamically call a model-specific post-save task if it exists
    print("Post-save for:", model_key)
    func_name = f"{model_key.rstrip('s')}_save_post"
    if func_name in globals():
        return globals()[func_name](data)
    # Default: do nothing
    return {'success': True}

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=3)
def save_post_async(self, model_key, record_id, version):  # type: ignore[override]
    """Generic async fan-out hook after a record is saved.

    Retries up to 3 times with exponential backoff (unless disabled by setting SAVE_POST_ASYNC_RETRY_ENABLED=False).
    Downstream consumers can extend this task or listen on the broker queue.
    Emits lightweight metadata only (table, id, version). Extend as needed.
    """
    from django.conf import settings  # local import
    retry_enabled = getattr(settings, 'SAVE_POST_ASYNC_RETRY_ENABLED', True)
    if not retry_enabled and self.request.retries > 0:
        # If retries disabled mid-flight, stop further attempts.
        return {'dispatched': False, 'attempt': self.request.retries, 'retry_disabled': True}
    logger.info(
    "save_post_async dispatch table=%s id=%s version=%s attempt=%s retry_enabled=%s",
    model_key,
        record_id,
        version,
        self.request.retries,
        retry_enabled,
    )
    return {'dispatched': True, 'attempt': self.request.retries, 'retry_enabled': retry_enabled}

# Example table-specific pre/post tasks
def contact_save_pre(data):
    # Custom logic for contacts before save
    print("Pre-save for contact:", data)
    return {'success': True}

def contact_save_post(data):
    # Custom logic for contacts after save
    print("Post-save for contact:", data)
    return {'success': True}
from celery import shared_task
from apps.core.services import view_edit_access
from apps.core.services.wcapi_registry import get_model, normalize_table_key
from django.db import IntegrityError
from django.forms.models import model_to_dict
import json
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

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=3)
def perform_save_operation(self, model_key, data, record_id=None, expected_version=None, user_id=None):
    """Celery task to perform the save operation asynchronously."""
    try:
        # Normalize and resolve model
        norm_key = normalize_table_key(model_key)
        if not norm_key:
            raise ValueError(f'Unknown model: {model_key}')
        model = get_model(norm_key)
        if not model:
            raise ValueError(f'Unknown model: {model_key}')

        # Create or update
        is_update = bool(record_id)
        if is_update:
            obj = model.objects.get(id=record_id)
            if expected_version is not None:
                current_version = getattr(obj, 'version', None)
                if current_version != expected_version:
                    raise ValueError(f'Version conflict: expected {expected_version} got {current_version}')
        else:
            obj = model()

        # Assign fields (similar to SaveWcapiView logic)
        nested_fields = ['refs', 'prefs', 'metadata', 'actions']
        json_field_names = {
            f.name for f in obj._meta.get_fields()
            if hasattr(f, 'attname') and isinstance(f, model._meta.pk.__class__.__bases__[0].__subclasshook__(type('JSONField', (), {})))  # rough check
        }

        raw_password = None
        for field, value in data.items():
            if field == 'password':
                raw_password = value
                continue
            if field in ('model_name', 'id', 'version', 'expected_version'):
                continue
            if hasattr(obj, field):
                current = getattr(obj, field)
                is_json_field = field in json_field_names or isinstance(current, dict)
                if isinstance(value, dict) and is_json_field:
                    if isinstance(current, str):
                        try:
                            current = json.loads(current)
                        except json.JSONDecodeError:
                            current = {}
                    if not isinstance(current, dict):
                        current = {}
                    # Deep merge
                    def deep_merge(a, b):
                        for k, v in (b or {}).items():
                            if isinstance(v, dict) and isinstance(a.get(k), dict):
                                deep_merge(a[k], v)
                            else:
                                a[k] = v
                        return a
                    merged = deep_merge(current, value)
                    setattr(obj, field, merged)
                else:
                    setattr(obj, field, value)

        if raw_password is not None and hasattr(obj, 'set_password'):
            obj.set_password(raw_password)

        # Save
        obj.save()

        # Post-save async task
        try:
            task_async = getattr(self, 'save_post_async', None)
            if task_async is not None:
                task_async.delay(model_key, obj.id, getattr(obj, 'version', None))
        except Exception:
            pass

        return {'success': True, 'id': obj.id, 'version': getattr(obj, 'version', None)}

    except IntegrityError as e:
        raise ValueError(f'Integrity error: {str(e)}')
    except Exception as e:
        raise ValueError(f'Failed to save: {str(e)}')

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=3)
def update_keywords_task(self, model_key, record_id):
    """Celery task to update keywords for a record."""
    try:
        norm_key = normalize_table_key(model_key)
        if not norm_key:
            raise ValueError(f'Unknown model: {model_key}')
        model = get_model(norm_key)
        if not model:
            raise ValueError(f'Unknown model: {model_key}')

        obj = model.objects.get(id=record_id)
        if hasattr(obj, 'update_keywords'):
            obj.update_keywords()
            obj.save(update_fields=['refs', 'metadata'])
        return {'success': True}
    except Exception as e:
        raise ValueError(f'Failed to update keywords: {str(e)}')
from celery import shared_task
from django.apps import apps
from django.utils import timezone

from .models import BaseModel

@shared_task(name='common.tasks.refresh_keywords_task')
def refresh_keywords_task(limit: int = 500, batch_size: int = 200):
    """Periodic task to refresh pending keywords across BaseModel subclasses.

    Processes up to 'limit' objects per invocation to avoid long-running tasks.
    """
    processed = 0
    started = timezone.now()
    for model in apps.get_models():
        if not issubclass(model, BaseModel) or model is BaseModel:
            continue
        qs = getattr(model.objects, 'keyword_pending', lambda: None)()
        if qs is None:
            continue
        qs = qs.only('id', 'metadata', 'refs')
        for obj in qs.iterator(chunk_size=batch_size):
            obj.update_keywords()
            model.objects.filter(pk=obj.pk).update(refs=obj.refs, metadata=obj.metadata)
            processed += 1
            if processed >= limit:
                duration = (timezone.now() - started).total_seconds()
                return {'processed': processed, 'duration': duration}
    duration = (timezone.now() - started).total_seconds()
    return {'processed': processed, 'duration': duration}

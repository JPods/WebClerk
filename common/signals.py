from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps

from .models import BaseModel

@receiver(post_save)
def basemodel_change_logger(sender, instance, created, **kwargs):
    # Only handle subclasses of BaseModel; skip BaseModel itself (abstract) and proxy models
    if not isinstance(instance, BaseModel):
        return
    # Determine changed fields: Django doesn't directly give, so keep minimal placeholder
    # Future: integrate dirty-fields tracking.
    changed_fields = []  # placeholder
    emit_change_log = getattr(instance, "emit_change_log", None)
    if callable(emit_change_log):
        payload = emit_change_log(changed_fields)
        # Placeholder: print or route to a queue/log. Replace with Celery task send.
        # For now avoid noisy output in tests; could use logging.
        # import logging; logging.getLogger(__name__).info("CHANGE_LOG %s", payload)
        _ = payload

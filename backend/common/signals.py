from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps
import logging

from .models import BaseModel

logger = logging.getLogger(__name__)

# Models that should NOT enqueue denormalization on save.
_DENORM_SKIP_MODELS = {'pending', 'log', 'refsmismatchlog'}


@receiver(post_save)
def basemodel_change_logger(sender, instance, created, **kwargs):
    # Only handle subclasses of BaseModel; skip BaseModel itself (abstract) and proxy models
    if not isinstance(instance, BaseModel):
        return

    # Mark keywords as pending so the refresh task picks it up
    if hasattr(instance, 'metadata') and isinstance(instance.metadata, dict):
        flags = instance.metadata.setdefault('flags', {})
        if not flags.get('keywords_pending'):
            flags['keywords_pending'] = True
            type(instance).objects.filter(pk=instance.pk).update(metadata=instance.metadata)

    # Push to Alice's permanent denormalize stack
    model_name = instance._meta.model_name
    if model_name in _DENORM_SKIP_MODELS:
        return

    try:
        from apps.core.services.alice_denormalize import push_to_stack
        push_to_stack(model_name, instance.pk)
    except Exception:
        # Never let queue failures break a save
        logger.debug('Failed to push to alice denorm stack for %s:%s', model_name, instance.pk, exc_info=True)

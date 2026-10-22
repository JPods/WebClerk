from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps
import logging

from .models import BaseModel

logger = logging.getLogger(__name__)


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

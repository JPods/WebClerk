from __future__ import annotations

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction

from apps.products.models.inventory_layer import InventoryStack
from apps.products.services.inventory_adjustment_processor import process_pending_for_stack


@receiver(pre_save, sender=InventoryStack)
def _invstack_capture_prev(sender, instance: InventoryStack, **kwargs):  # pragma: no cover - simple state capture
    if instance.pk:
        try:
            prev = sender.objects.only('is_locked').get(pk=instance.pk)
            instance._prev_is_locked = prev.is_locked  # type: ignore[attr-defined]
        except sender.DoesNotExist:  # pragma: no cover
            instance._prev_is_locked = None  # type: ignore[attr-defined]
    else:
        instance._prev_is_locked = None  # type: ignore[attr-defined]


@receiver(post_save, sender=InventoryStack)
def _invstack_process_on_unlock(sender, instance: InventoryStack, created: bool, **kwargs):  # pragma: no cover - integration behavior
    prev_locked = getattr(instance, '_prev_is_locked', None)
    if prev_locked and not instance.is_locked:
        # Defer processing until after transaction commit to see final state.
        def _do():
            try:
                process_pending_for_stack(instance.pk)
            except Exception:  # swallow (optional logging)
                pass
        transaction.on_commit(_do)

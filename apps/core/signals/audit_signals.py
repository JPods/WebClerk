"""Auto-wire AuditLog to capture field-level changes on save.

Registers post_save signals for key models. On every update, diffs old vs new
field values and writes to AuditLog.changes as {field: {old, new}}.

Excludes: computed/cached fields, JSON blobs (too noisy), timestamps.
Skips creates (no old values to diff) — only logs updates.
"""
from __future__ import annotations

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# Fields to exclude from diff — computed, cached, or too noisy
AUDIT_EXCLUDE_FIELDS = {
    'dt_created', 'dt_modified', 'version', 'row_version',
    'metadata', 'refs', 'prefs', 'actions', 'comments', 'stats',
    'health_rating', 'keywords',
}

# Models to auto-audit (app_label.ModelName)
AUDITED_MODELS = {
    'transactions.Invoice',
    'transactions.Order',
    'transactions.Proposal',
    'transactions.Purchase',
    'transactions.WorkOrder',
    'transactions.Payment',
    'transactions.Receipt',
    'core.Contact',
    'core.Action',
    'products.Item',
    'products.Serial',
}


def _get_model_key(instance) -> str:
    return f"{instance._meta.app_label}.{instance.__class__.__name__}"


def _diff_fields(old_values: dict, instance) -> dict:
    """Compare old field values to current instance, return {field: {old, new}} for changed fields."""
    changes = {}
    for field_name, old_val in old_values.items():
        if field_name in AUDIT_EXCLUDE_FIELDS:
            continue
        new_val = getattr(instance, field_name, None)
        # Normalize for comparison
        if old_val != new_val:
            changes[field_name] = {
                'old': _serialize(old_val),
                'new': _serialize(new_val),
            }
    return changes


def _serialize(val):
    """Convert a value to JSON-serializable form."""
    if val is None:
        return None
    if isinstance(val, (int, float, str, bool)):
        return val
    return str(val)


def audit_post_save(sender, instance, created, **kwargs):
    """Post-save handler that logs field changes to AuditLog."""
    if created:
        return  # Skip creates — no old values to diff

    model_key = _get_model_key(instance)
    if model_key not in AUDITED_MODELS:
        return

    # Check if we captured old values in pre_save
    old_values = getattr(instance, '_audit_old_values', None)
    if not old_values:
        return

    changes = _diff_fields(old_values, instance)
    if not changes:
        return  # Nothing actually changed

    try:
        from apps.core.models.audit import AuditLog
        AuditLog.log_action(
            model_name=instance.__class__.__name__.lower(),
            record_id=instance.pk,
            action='updated',
            changes=changes,
        )
    except Exception:
        logger.debug("AuditLog write failed", exc_info=True)

    # Clean up
    instance._audit_old_values = None


def audit_pre_save(sender, instance, **kwargs):
    """Pre-save handler that captures current field values before the save."""
    if not instance.pk:
        return  # New record — nothing to diff against

    model_key = _get_model_key(instance)
    if model_key not in AUDITED_MODELS:
        return

    try:
        old = type(instance).objects.filter(pk=instance.pk).values().first()
        if old:
            instance._audit_old_values = old
    except Exception:
        pass


def register_audit_signals():
    """Connect audit signals for all audited models. Call from AppConfig.ready()."""
    from django.db.models.signals import pre_save, post_save
    from django.apps import apps

    for model_path in AUDITED_MODELS:
        try:
            app_label, model_name = model_path.split('.')
            model_cls = apps.get_model(app_label, model_name)
            pre_save.connect(audit_pre_save, sender=model_cls, dispatch_uid=f'audit_pre_{model_path}')
            post_save.connect(audit_post_save, sender=model_cls, dispatch_uid=f'audit_post_{model_path}')
        except Exception:
            logger.debug(f"Could not register audit signal for {model_path}", exc_info=True)

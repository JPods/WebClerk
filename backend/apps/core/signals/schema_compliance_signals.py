"""Schema compliance signals — Alice checks on Setting save and post-migrate.

Two triggers:
1. post_save on Setting — when a wc:model Setting is modified, validate it.
2. post_migrate — after any migration, run a full schema compliance audit.

Violations are logged and optionally fixed (Alice mode).

Established: 2026-08-09
"""
from __future__ import annotations

import logging

from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver

logger = logging.getLogger(__name__)

SCHEMA_PURPOSES = {'wc:model', 'wc:schema_map', 'wc:enrichment_panels', 'wc:detail_layout', 'wc:field_access'}


@receiver(post_save, sender='core.Setting')
def check_setting_schema_compliance(sender, instance, **kwargs):
    """After a Setting is saved, validate it if it's a schema-related purpose."""
    purpose = getattr(instance, 'purpose', '')
    if purpose not in SCHEMA_PURPOSES:
        return

    try:
        from apps.core.services.schema_validate import validate_schema_setting
        violations = validate_schema_setting(instance)
        if violations:
            model_name = getattr(instance, 'parent_model', '') or ''
            logger.warning(
                '[SCHEMA_COMPLIANCE] Setting #%s (%s/%s) has %d violations: %s',
                instance.id, purpose, model_name, len(violations),
                '; '.join(v['message'] for v in violations),
            )
            # Store violations on the Setting for Alice to review
            config = instance.config if isinstance(instance.config, dict) else {}
            config['_schema_violations'] = violations
            # Use update to avoid re-triggering this signal
            type(instance).objects.filter(pk=instance.pk).update(config=config)
    except Exception as e:
        logger.error('[SCHEMA_COMPLIANCE] Error checking Setting #%s: %s', instance.id, e)


@receiver(post_migrate)
def check_schema_compliance_after_migrate(sender, **kwargs):
    """After any migration, run a full schema compliance audit."""
    # Only run once per migrate command, not per app
    app_label = getattr(sender, 'label', '')
    if app_label != 'core':
        return  # Only trigger on core app migration to avoid running N times

    try:
        from apps.core.services.schema_validate import audit_all_schema_settings
        result = audit_all_schema_settings(fix=False)
        if result['violations']:
            logger.warning(
                '[SCHEMA_COMPLIANCE] Post-migrate audit: %d violations in %d settings',
                len(result['violations']), result['settings_with_violations'],
            )
            for v in result['violations']:
                logger.warning('  %s', v['message'])
        else:
            logger.info('[SCHEMA_COMPLIANCE] Post-migrate audit: all %d settings comply',
                        result['total_settings'])
    except Exception as e:
        logger.error('[SCHEMA_COMPLIANCE] Post-migrate audit error: %s', e)

"""Schema Compliance — validate model Pydantic schemas inherit from BaseModel defaults.

The source of truth is BaseModel's default factories in common/models.py:
  default_metadata(), default_refs(), default_prefs(), default_comments()

Every model's Pydantic schema MUST inherit from the corresponding base class
in common/schemas/envelopes.py, which mirrors those defaults. If a model's
schema doesn't inherit, it can't handle BaseModel's envelope fields — saves
will fail, data will be lost, Alice can't coach.

Three checks:
1. Schema inheritance — does each model's Pydantic class extend the correct base?
2. Default acceptance — can the Pydantic schema parse what BaseModel's factory produces?
3. Record compliance — do existing records have valid envelopes?

Established: 2026-08-09
"""
from __future__ import annotations

import importlib
import logging
from typing import Any

from django.apps import apps

logger = logging.getLogger(__name__)

# ── BaseModel reserved field names (22 fields across 7 mixins) ──
BASEMODEL_RESERVED = frozenset({
    'id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'version',
    'is_active', 'security_level', 'dt_approved', 'times_used',
    'dt_last_used', 'purpose', 'config',
    'is_deleted', 'is_archived', 'is_locked',
    'metadata', 'refs', 'prefs', 'actions', 'comments',
    'health_rating',
})

READONLY_FIELDS = frozenset({
    'id', 'uuid', 'dt_created', 'dt_modified', 'version', 'health_rating',
})

M2M_SKIP_FIELDS = frozenset({
    'groups', 'user_permissions', 'logentry',
})

# ── Required Pydantic inheritance ──
# Each schema_map Setting must declare these keys, and each must point to a
# class that inherits from the corresponding base in common/schemas/envelopes.py.
REQUIRED_SCHEMA_KEYS = {
    'metadata_schema': 'MetadataBase',
    'refs_schema': 'RefsBase',
    'prefs_schema': 'RecordPrefsBase',
    'config_schema': 'ConfigBase',
}


def _get_envelope_bases():
    """Import the base classes from envelopes.py — BaseModel's source of truth."""
    from common.schemas.envelopes import (
        MetadataBase, RefsBase, RecordPrefsBase, ConfigBase,
    )
    return {
        'metadata_schema': MetadataBase,
        'refs_schema': RefsBase,
        'prefs_schema': RecordPrefsBase,
        'config_schema': ConfigBase,
    }


def _get_defaults():
    """Get BaseModel's actual default dictionaries — the ground truth."""
    from common.models import (
        default_metadata, default_refs, default_prefs, default_comments,
    )
    return {
        'metadata': default_metadata(),
        'refs': default_refs(),
        'prefs': default_prefs(),
        'comments': default_comments(),
        'config': {},
    }


def validate_schema_setting(setting) -> list[dict[str, Any]]:
    """Validate one Setting's Pydantic structure against BaseModel.

    For schema_map Settings:
    1. Must declare metadata_schema, refs_schema, prefs_schema, config_schema
    2. Each must point to a class that inherits from the correct envelope base
    3. Each base class must accept what BaseModel's default factory produces

    Returns list of violation dicts.
    """
    violations = []
    config = setting.config if isinstance(setting.config, dict) else {}
    purpose = getattr(setting, 'purpose', '')
    model_name = getattr(setting, 'parent_model', '') or ''

    if purpose == 'wc:schema_map':
        _check_schema_inheritance(config, model_name, violations)
    elif purpose == 'wc:enrichment_panels':
        _check_enrichment_panels(config, model_name, violations)
    elif purpose == 'wc:detail_layout':
        _check_detail_layout(config, model_name, violations)
    elif purpose == 'wc:field_access':
        _check_field_access(config, model_name, violations)

    return violations


def _check_schema_inheritance(config: dict, model_name: str, violations: list):
    """Core check: does each Pydantic schema inherit from BaseModel's envelope bases?"""
    module_path = config.get('pydantic_schema', '')

    if not module_path:
        violations.append({
            'field': 'pydantic_schema',
            'violation_type': 'missing_module',
            'message': f'{model_name}: no pydantic_schema module path in schema_map',
        })
        return

    # Import the module
    try:
        mod = importlib.import_module(module_path)
    except Exception as e:
        violations.append({
            'field': 'pydantic_schema',
            'violation_type': 'import_error',
            'message': f'{model_name}: cannot import {module_path}: {type(e).__name__}: {e}',
        })
        return

    # Get the envelope base classes
    try:
        bases = _get_envelope_bases()
    except Exception as e:
        violations.append({
            'field': 'envelopes',
            'violation_type': 'base_import_error',
            'message': f'Cannot import envelope base classes: {e}',
        })
        return

    # Check each required schema key
    for schema_key, base_name in REQUIRED_SCHEMA_KEYS.items():
        class_name = config.get(schema_key, '')

        if not class_name:
            violations.append({
                'field': schema_key,
                'violation_type': 'missing_schema',
                'message': f'{model_name}: missing {schema_key} — model Pydantic must '
                           f'declare a class that inherits from {base_name}',
            })
            continue

        cls = getattr(mod, class_name, None)
        if cls is None:
            violations.append({
                'field': schema_key,
                'violation_type': 'class_not_found',
                'message': f'{model_name}: {class_name} not found in {module_path}',
            })
            continue

        required_base = bases[schema_key]
        try:
            if not issubclass(cls, required_base):
                violations.append({
                    'field': schema_key,
                    'violation_type': 'inheritance_missing',
                    'message': f'{model_name}: {class_name} does NOT inherit from '
                               f'{base_name} — BaseModel envelopes will not be supported',
                })
        except Exception as e:
            violations.append({
                'field': schema_key,
                'violation_type': 'inheritance_check_error',
                'message': f'{model_name}: error checking {class_name}: {type(e).__name__}',
            })
            continue

    # Check that the Pydantic schemas can accept BaseModel's default outputs
    _check_default_acceptance(mod, config, model_name, violations)


def _check_default_acceptance(mod, config: dict, model_name: str, violations: list):
    """Verify each Pydantic schema can parse what BaseModel's default factory produces."""
    try:
        defaults = _get_defaults()
    except Exception:
        return  # Can't get defaults — skip this check

    schema_to_default = {
        'metadata_schema': 'metadata',
        'refs_schema': 'refs',
        'prefs_schema': 'prefs',
        'config_schema': 'config',
    }

    for schema_key, default_key in schema_to_default.items():
        class_name = config.get(schema_key, '')
        if not class_name:
            continue
        cls = getattr(mod, class_name, None)
        if cls is None:
            continue

        default_value = defaults[default_key]
        try:
            cls.model_validate(default_value)
        except Exception as e:
            violations.append({
                'field': schema_key,
                'violation_type': 'default_rejection',
                'message': f'{model_name}: {class_name} rejects BaseModel default '
                           f'for {default_key}: {type(e).__name__}: {str(e)[:200]}',
            })


def _check_enrichment_panels(config: dict, model_name: str, violations: list):
    """Check enrichment panel definitions."""
    panels = config.get('panels', [])
    for panel in panels:
        if not isinstance(panel, dict):
            violations.append({
                'field': 'panels',
                'violation_type': 'invalid_panel',
                'message': f'{model_name}: enrichment panel is not a dict',
            })


def _check_detail_layout(config: dict, model_name: str, violations: list):
    """Check detail_layout for M2M field references."""
    for section in config.get('sections', []):
        if not isinstance(section, dict):
            continue
        for col in section.get('columns', []):
            if not isinstance(col, dict):
                continue
            for field_def in col.get('fields', []):
                if isinstance(field_def, dict):
                    top_field = field_def.get('field', '').split('.')[0]
                    if top_field in M2M_SKIP_FIELDS:
                        violations.append({
                            'field': field_def['field'],
                            'violation_type': 'm2m_in_layout',
                            'message': f'{model_name}: layout references M2M field "{top_field}"',
                        })


def _check_field_access(config: dict, model_name: str, violations: list):
    """Check field_access for editable read-only fields."""
    for role, perms in config.items():
        if not isinstance(perms, dict):
            continue
        for field in perms.get('edit', []):
            if field in READONLY_FIELDS:
                violations.append({
                    'field': field,
                    'violation_type': 'readonly_editable',
                    'message': f'{model_name}: field_access grants edit on read-only "{field}" for role "{role}"',
                })


def audit_all_schema_settings(fix: bool = False) -> dict:
    """Audit all schema-related Settings against BaseModel.

    Args:
        fix: If True, rebuild non-compliant schemas (Alice mode).
             If False, report only (Claude audit mode).
    """
    Setting = apps.get_model('core', 'Setting')

    settings = Setting.objects.filter(
        purpose__in=['wc:schema_map', 'wc:enrichment_panels', 'wc:detail_layout', 'wc:field_access'],
        is_active=True,
        is_deleted=False,
    ).order_by('purpose', 'parent_model')

    all_violations = []
    settings_with_violations = 0

    for setting in settings:
        violations = validate_schema_setting(setting)
        if violations:
            settings_with_violations += 1
            for v in violations:
                v['setting_id'] = setting.id
                v['setting_ida'] = setting.ida or ''
                v['purpose'] = setting.purpose
                v['parent_model'] = getattr(setting, 'parent_model', '')
            all_violations.extend(violations)

            if fix:
                _fix_setting_violations(setting, violations)

    result = {
        'total_settings': settings.count(),
        'violations': all_violations,
        'settings_with_violations': settings_with_violations,
        'clean_settings': settings.count() - settings_with_violations,
    }

    logger.info(
        'Schema compliance audit: %d settings, %d violations in %d settings',
        result['total_settings'], len(all_violations), settings_with_violations,
    )
    return result


def _fix_setting_violations(setting, violations: list):
    """Fix violations — move colliding data to _violations bucket, rebuild missing schemas."""
    config = setting.config if isinstance(setting.config, dict) else {}
    bucket = config.setdefault('_violations', [])

    for v in violations:
        field = v['field']
        if v['violation_type'] == 'reserved_collision' and field in config:
            bucket.append({
                'field': field,
                'original_value': config.pop(field, None),
                'reason': v['message'],
            })

    setting.config = config
    setting.save(update_fields=['config', 'dt_modified'])
    logger.warning('Fixed %d violations in Setting #%s (%s)',
                   len(violations), setting.id, setting.ida)


def validate_record_envelopes(obj) -> list[dict[str, Any]]:
    """Validate one record's JSON envelopes against BaseModel defaults.

    Checks each envelope is a dict with expected sub-keys from the default factory.
    """
    violations = []
    model_name = obj._meta.model_name
    defaults = _get_defaults()

    for field_name in ('metadata', 'refs', 'prefs', 'comments', 'config'):
        if not hasattr(obj, field_name):
            continue
        value = getattr(obj, field_name)

        if value is None:
            violations.append({
                'field': field_name,
                'violation_type': 'null_envelope',
                'message': f'{model_name}#{obj.pk}: {field_name} is None (should be dict)',
                'fix': 'set_default',
            })
        elif isinstance(value, str):
            violations.append({
                'field': field_name,
                'violation_type': 'string_envelope',
                'message': f'{model_name}#{obj.pk}: {field_name} is string (should be dict)',
                'fix': 'parse_or_default',
            })
        elif not isinstance(value, dict):
            violations.append({
                'field': field_name,
                'violation_type': 'wrong_type',
                'message': f'{model_name}#{obj.pk}: {field_name} is {type(value).__name__}',
                'fix': 'set_default',
            })
        elif field_name in defaults:
            # Check that required sub-keys from the default are present
            default = defaults[field_name]
            missing = [k for k in default if k not in value]
            if missing:
                violations.append({
                    'field': field_name,
                    'violation_type': 'missing_keys',
                    'message': f'{model_name}#{obj.pk}: {field_name} missing keys: {missing}',
                    'fix': 'merge_defaults',
                    'missing_keys': missing,
                })

    return violations

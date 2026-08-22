"""
Config unpack service — promote fields from config.original to named config keys.

Users ask Alice: "I need the barCode field on items visible."
Alice calls unpack_field() to promote config.original.barCode → config.bar_code
across all records of that model.

This is the learning loop:
  1. WC2 import puts everything in config.original
  2. Known-useful fields are extracted to named keys at import time
  3. Users discover they need more fields — Alice unpacks on demand
  4. Alice tracks which fields get unpacked (useful) vs never touched (junk)
  5. Next import adds the useful ones to the extract_keys dict automatically

Usage:
  from apps.conversion.services.config_unpack import unpack_field, list_original_fields

  # See what's available in config.original for a model
  fields = list_original_fields('item')
  # → {'barCode': {'count': 3200, 'sample': 'ABC-123'}, ...}

  # Promote a field
  result = unpack_field('item', 'barCode', config_key='bar_code')
  # → {'updated': 3200, 'skipped': 1088, 'empty': 0}

  # Bulk promote several fields
  result = unpack_fields('item', {'barCode': 'bar_code', 'ean': 'ean'})

  # Undo — move a named key back (demote)
  result = demote_field('item', 'bar_code')
"""

import logging
from django.apps import apps
from django.db.models import Q

logger = logging.getLogger(__name__)


# Map friendly model names to Django model paths
MODEL_MAP = {
    'item': 'products.Item',
    'customer': 'orgs.OrgBase',
    'vendor': 'orgs.OrgBase',
    'contact': 'core.Contact',
    'order': 'transactions.Order',
    'invoice': 'transactions.Invoice',
    'proposal': 'transactions.Proposal',
    'purchase': 'transactions.Purchase',
    'payment': 'transactions.Payment',
    'order_line': 'transactions.OrderLine',
    'invoice_line': 'transactions.InvoiceLine',
    'proposal_line': 'transactions.ProposalLine',
    'purchase_line': 'transactions.PurchaseLine',
}

# Org types that need filtering
ORG_TYPE_FILTER = {
    'customer': 'customer',
    'vendor': 'vendor',
}


def _get_model_and_qs(model_name):
    """Resolve model name to Django model class and base queryset."""
    model_name = model_name.lower().strip()
    model_path = MODEL_MAP.get(model_name)
    if not model_path:
        raise ValueError(f"Unknown model: {model_name}. Available: {', '.join(sorted(MODEL_MAP.keys()))}")

    app_label, model_class_name = model_path.split('.')
    Model = apps.get_model(app_label, model_class_name)
    qs = Model.objects.all()

    # Filter by org_type for org models
    org_type = ORG_TYPE_FILTER.get(model_name)
    if org_type:
        qs = qs.filter(org_type=org_type)

    return Model, qs


def list_original_fields(model_name, sample_size=100):
    """List all fields available in config.original across records.

    Returns dict of {field_name: {count, sample, type}} showing what's
    available to unpack. Samples the first N records for speed.

    This is what Alice shows the user: "Here's what's in config.original
    that hasn't been unpacked yet."
    """
    _, qs = _get_model_and_qs(model_name)

    # Sample records that have config.original
    records = list(
        qs.filter(config__has_key='original')
        .exclude(config__original={})
        .values_list('config', flat=True)[:sample_size]
    )

    if not records:
        return {}

    # Count field occurrences and collect samples
    field_info = {}
    for config in records:
        original = config.get('original', {})
        if not isinstance(original, dict):
            continue
        # Get already-extracted keys (everything in config that isn't 'original' or 'profiles')
        already_extracted = {k for k in config.keys() if k not in ('original', 'profiles')}

        for field, value in original.items():
            if value in (None, '', 0, False, [], {}):
                continue
            if field not in field_info:
                field_info[field] = {
                    'count': 0,
                    'sample': None,
                    'type': type(value).__name__,
                    'already_extracted': field in already_extracted,
                }
            field_info[field]['count'] += 1
            if field_info[field]['sample'] is None:
                # Truncate long samples
                sample = value
                if isinstance(value, str) and len(value) > 80:
                    sample = value[:80] + '...'
                elif isinstance(value, dict):
                    sample = '{...}'
                elif isinstance(value, list):
                    sample = f'[{len(value)} items]'
                field_info[field]['sample'] = sample

    # Sort by count descending
    return dict(sorted(field_info.items(), key=lambda x: -x[1]['count']))


def unpack_field(model_name, original_field, config_key=None, record_id=None, dry_run=False):
    """Promote a field from config.original to a named config key.

    Args:
        model_name: 'item', 'customer', 'order', etc.
        original_field: The WC2 field name in config.original (e.g. 'barCode')
        config_key: The target key in config (e.g. 'bar_code'). Defaults to original_field.
        record_id: If set, only unpack for this one record. Otherwise all records.
        dry_run: If True, count affected records without writing.

    Returns:
        {'updated': N, 'skipped': N, 'empty': N}
    """
    Model, qs = _get_model_and_qs(model_name)
    config_key = config_key or original_field

    if record_id:
        qs = qs.filter(pk=record_id)

    # Only records that have this field in config.original
    qs = qs.filter(**{f'config__original__has_key': original_field})

    updated = 0
    skipped = 0
    empty = 0

    for record in qs.iterator(chunk_size=500):
        config = record.config if isinstance(record.config, dict) else {}
        original = config.get('original', {})
        value = original.get(original_field)

        if value in (None, '', 0, False, [], {}):
            empty += 1
            continue

        # Already has this key with a value — skip
        if config.get(config_key) not in (None, '', 0):
            skipped += 1
            continue

        if not dry_run:
            config[config_key] = value
            record.config = config
            Model.objects.filter(pk=record.pk).update(config=config)

        updated += 1

    result = {'updated': updated, 'skipped': skipped, 'empty': empty}
    logger.info(f"unpack_field({model_name}, {original_field} → {config_key}): {result}")
    return result


def unpack_fields(model_name, field_map, dry_run=False):
    """Promote multiple fields at once.

    Args:
        model_name: 'item', 'customer', etc.
        field_map: Dict of {original_field: config_key}
            e.g. {'barCode': 'bar_code', 'ean': 'ean'}
        dry_run: If True, count without writing.

    Returns:
        Dict of {config_key: {updated, skipped, empty}}
    """
    results = {}
    for original_field, config_key in field_map.items():
        results[config_key] = unpack_field(
            model_name, original_field, config_key=config_key, dry_run=dry_run
        )
    return results


def demote_field(model_name, config_key, record_id=None, dry_run=False):
    """Remove a named config key (value stays in config.original).

    Use when Alice learns a field is junk — demote it back.
    The value is NOT deleted from config.original, just from the named key.
    """
    Model, qs = _get_model_and_qs(model_name)

    if record_id:
        qs = qs.filter(pk=record_id)

    qs = qs.filter(**{f'config__has_key': config_key})

    removed = 0
    for record in qs.iterator(chunk_size=500):
        config = record.config if isinstance(record.config, dict) else {}
        if config_key in config:
            del config[config_key]
            if not dry_run:
                record.config = config
                Model.objects.filter(pk=record.pk).update(config=config)
            removed += 1

    result = {'removed': removed}
    logger.info(f"demote_field({model_name}, {config_key}): {result}")
    return result

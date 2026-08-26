"""
core.services.dedup — Server-side duplicate detection and merge for any model.

Usage via wcapi/manage/:
    POST /wcapi/manage/
    { "action": "find_duplicates", "model": "contact", "match_fields": ["name_first+name_last"] }
    { "action": "merge_records", "model": "contact", "winner_id": 123, "loser_ids": [456, 789] }

Match field syntax:
    "email"              — exact match on single field
    "name_first+name_last" — composite key (both must match)
    "phone:normalized"   — match with normalization (strips non-digits)

Alice uses this for every model. The pattern is universal:
    contacts: name, email, phone
    items: sku, description, vendor+sku
    actions: task title similarity
"""
import os
import re
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from django.apps import apps
from django.db.models import Count

log = logging.getLogger(__name__)

DEDUP_JOURNAL_DIR = Path('/Users/williamjames/Documents/CommerceExpert/webclerk3_data/dedup_journal')


def _journal_record(model_name: str, record, action: str, context: str = ''):
    """Write a full record snapshot to the dedup journal before merge/delete."""
    try:
        DEDUP_JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        path = DEDUP_JOURNAL_DIR / f'{today}_{model_name}.jsonl'

        # Serialize the record
        if hasattr(record, '__dict__'):
            # Django model instance — serialize all fields
            data = {}
            for field in record._meta.get_fields():
                fname = getattr(field, 'attname', getattr(field, 'name', None))
                if not fname or not hasattr(record, fname):
                    continue
                val = getattr(record, fname, None)
                try:
                    json.dumps(val)  # test serializable
                    data[fname] = val
                except (TypeError, ValueError):
                    data[fname] = str(val)
        else:
            data = dict(record)

        entry = {
            'action': action,
            'model': model_name,
            'id': data.get('id'),
            'ida': data.get('ida', ''),
            'dt': datetime.now(timezone.utc).isoformat(),
            'context': context,
            'record': data,
        }

        with open(path, 'a') as f:
            f.write(json.dumps(entry, default=str) + '\n')

    except Exception as e:
        log.warning(f'Dedup journal write failed: {e}')


def normalize_phone(val):
    """Normalize phone for dedup matching using the canonical normalizer.

    Returns digits-only with country code (e.g. "14055551234").
    Single-arg wrapper so it fits in the NORMALIZERS dict.
    """
    from apps.core.services.phone_normalizer import normalize_phone as _canonical
    return _canonical(str(val or ''), default_country="US")


def normalize_email(val):
    return (val or '').strip().lower()


NORMALIZERS = {
    'phone': normalize_phone,
    'email': normalize_email,
    'normalized': lambda v: re.sub(r'\s+', ' ', str(v or '')).strip().lower(),
}


def find_duplicates(model_name, match_fields, limit=500, exclude_deleted=True):
    """
    Find duplicate groups in a model by match_fields.

    Args:
        model_name: Django model name (e.g., 'contact', 'item')
        match_fields: List of field specs:
            "email" — single field exact match
            "name_first+name_last" — composite match
            "phone:normalized" — match with normalizer
        limit: max groups to return
        exclude_deleted: skip is_deleted=True records

    Returns:
        {
            "groups": [
                {
                    "match_key": "john|smith",
                    "match_fields": ["name_first", "name_last"],
                    "records": [
                        {"id": 1, "ida": "...", "fields": {...}, "score": 5},
                        {"id": 2, "ida": "...", "fields": {...}, "score": 3},
                    ],
                    "recommended_winner": 1,
                },
                ...
            ],
            "total_groups": N,
            "total_duplicates": N,
        }
    """
    try:
        Model = apps.get_model('core', model_name)
    except LookupError:
        # Try other apps
        for app in ['products', 'transactions', 'orgs', 'accounts', 'communications']:
            try:
                Model = apps.get_model(app, model_name)
                break
            except LookupError:
                continue
        else:
            return {"error": f"Model '{model_name}' not found"}

    qs = Model.objects.all()
    if exclude_deleted and hasattr(Model, 'is_deleted'):
        qs = qs.filter(is_deleted=False)
    if hasattr(Model, 'is_active'):
        qs = qs.filter(is_active=True)

    # Parse match fields
    parsed_fields = []
    for spec in match_fields:
        if ':' in spec:
            field_part, normalizer_name = spec.rsplit(':', 1)
            normalizer = NORMALIZERS.get(normalizer_name, lambda v: str(v or '').strip().lower())
        else:
            field_part = spec
            normalizer = lambda v: str(v or '').strip().lower()

        if '+' in field_part:
            fields = field_part.split('+')
        else:
            fields = [field_part]

        parsed_fields.append((fields, normalizer))

    # Build groups by composite key
    groups_map = defaultdict(list)

    # Determine which fields to fetch for display
    display_fields = set()
    for fields, _ in parsed_fields:
        display_fields.update(fields)
    # Always include useful display fields
    model_field_names = {fld.name for fld in Model._meta.get_fields() if hasattr(fld, 'column')}
    for f in ['ida', 'email', 'phone', 'attention', 'name_first', 'name_last',
              'company', 'title', 'source_name', 'health_rating', 'address_full',
              'department', 'description', 'name', 'display_name']:
        if f in model_field_names:
            display_fields.add(f)

    # Fetch records
    try:
        records = list(qs.values(*[f for f in display_fields if f != 'id'], 'id')[:10000])
    except Exception:
        # Some fields might not exist on this model — fetch just id + match fields
        fetch_fields = set(['id'])
        for fields, _ in parsed_fields:
            fetch_fields.update(fields)
        records = list(qs.values(*fetch_fields)[:10000])

    for rec in records:
        # Build composite key
        key_parts = []
        skip = False
        for fields, normalizer in parsed_fields:
            vals = []
            for f in fields:
                v = normalizer(rec.get(f, ''))
                if not v:
                    skip = True
                    break
                vals.append(v)
            if skip:
                break
            key_parts.extend(vals)

        if skip or not key_parts:
            continue

        key = '|'.join(key_parts)
        groups_map[key].append(rec)

    # Filter to groups with duplicates
    dupe_groups = {k: v for k, v in groups_map.items() if len(v) > 1}

    # Score each record in each group (higher = better candidate to keep)
    def score_record(rec):
        s = 0
        email = str(rec.get('email', ''))
        if email and 'placeholder' not in email:
            s += 3
        if rec.get('phone'):
            s += 2
        if rec.get('company'):
            s += 1
        if rec.get('address_full'):
            s += 1
        if rec.get('title'):
            s += 1
        if rec.get('source_name') == 'meshmobility.com':
            s += 2  # real user signup
        if str(rec.get('ida', '')).startswith('wc2'):
            s -= 1  # legacy import
        # Lower ID = older = often the original
        s += 1  # base score for existing
        return s

    result_groups = []
    total_dupes = 0

    for key, recs in sorted(dupe_groups.items(), key=lambda x: -len(x[1]))[:limit]:
        scored = []
        for rec in recs:
            scored.append({
                'id': rec['id'],
                'ida': rec.get('ida', ''),
                'fields': {k: v for k, v in rec.items() if v and v != '' and k != 'id'},
                'score': score_record(rec),
            })
        scored.sort(key=lambda x: -x['score'])
        winner = scored[0]['id']

        field_names = []
        for fields, _ in parsed_fields:
            field_names.extend(fields)

        result_groups.append({
            'match_key': key,
            'match_fields': field_names,
            'records': scored,
            'recommended_winner': winner,
        })
        total_dupes += len(recs) - 1

    return {
        'groups': result_groups,
        'total_groups': len(result_groups),
        'total_duplicates': total_dupes,
    }


def journal_delete(model_name, record_ids):
    """Journal records before they are deleted via the dedup UI."""
    try:
        Model = apps.get_model('core', model_name)
    except LookupError:
        for app in ['products', 'transactions', 'orgs', 'accounts', 'communications']:
            try:
                Model = apps.get_model(app, model_name)
                break
            except LookupError:
                continue
        else:
            return {"error": f"Model '{model_name}' not found"}

    records = list(Model.objects.filter(id__in=record_ids))
    for rec in records:
        _journal_record(model_name, rec, 'dedup_delete', f'deleted during dedup review')
    return {"journaled": len(records)}


def merge_records(model_name, winner_id, loser_ids, merge_strategy='fill_empty'):
    """
    Merge loser records into the winner. Soft-delete losers.

    merge_strategy:
        'fill_empty' — only fill fields on winner that are empty/null
        'overwrite' — loser values overwrite winner (use with caution)
        'collect' — collect all unique values into config.merged_values

    Returns:
        {"merged": N, "winner_id": winner_id, "fields_updated": [...]}
    """
    try:
        Model = apps.get_model('core', model_name)
    except LookupError:
        for app in ['products', 'transactions', 'orgs', 'accounts', 'communications']:
            try:
                Model = apps.get_model(app, model_name)
                break
            except LookupError:
                continue
        else:
            return {"error": f"Model '{model_name}' not found"}

    try:
        winner = Model.objects.get(id=winner_id)
    except Model.DoesNotExist:
        return {"error": f"Winner record {winner_id} not found"}

    losers = list(Model.objects.filter(id__in=loser_ids))
    if not losers:
        return {"error": "No loser records found"}

    # Journal: snapshot winner before update and all losers before delete
    _journal_record(model_name, winner, 'merge_winner_before', f'merging {len(losers)} losers into #{winner_id}')
    for loser in losers:
        _journal_record(model_name, loser, 'merge_loser_deleted', f'merged into winner #{winner_id}')

    fields_updated = []
    merged_data = []

    # Skip these fields during merge
    skip_fields = {
        'id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'dt_joined',
        'version', 'is_active', 'is_deleted', 'is_archived', 'is_locked',
        'password', 'is_superuser', 'is_staff', 'last_login',
        'metadata', 'refs', 'prefs', 'actions', 'comments', 'config',
    }

    for loser in losers:
        loser_snapshot = {}
        for field in Model._meta.get_fields():
            fname = getattr(field, 'attname', getattr(field, 'name', None))
            if not fname or fname in skip_fields:
                continue
            if not hasattr(loser, fname):
                continue

            loser_val = getattr(loser, fname, None)
            winner_val = getattr(winner, fname, None)

            if loser_val and str(loser_val).strip():
                loser_snapshot[fname] = str(loser_val)

                if merge_strategy == 'fill_empty':
                    if not winner_val or str(winner_val).strip() == '':
                        setattr(winner, fname, loser_val)
                        fields_updated.append(fname)

        # Store loser data in winner's config.merged_records
        merged_data.append({
            'id': loser.id,
            'ida': getattr(loser, 'ida', ''),
            'source_name': getattr(loser, 'source_name', ''),
            'data': loser_snapshot,
        })

        # Soft-delete the loser
        loser.is_deleted = True
        loser.is_active = False
        loser.save()

    # Update winner's config with merge history
    config = winner.config if isinstance(winner.config, dict) else {}
    existing_merged = config.get('merged_records', [])
    config['merged_records'] = existing_merged + merged_data
    winner.config = config
    winner.save()

    return {
        'merged': len(losers),
        'winner_id': winner_id,
        'fields_updated': list(set(fields_updated)),
    }

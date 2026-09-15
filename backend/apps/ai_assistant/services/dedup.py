"""
Duplicate Detection & Extraction Service — Alice skill.

Alice scans records for potential duplicates across any model. When duplicates
are found, the duplicate records are:
  1. Serialized to JSON files under sync/dedup/pending/
  2. Referenced by a Bundle record pointing to the retained (surviving) record
  3. Deactivated in the database (is_active=False, is_deleted=True)
  4. Available for operator review: compare pending files against retained record

After review, files move to sync/dedup/processed/.

Alice can escalate complex merge decisions to Claude Code via the existing
escalation connection (conn-alice-claude, id=32).

Usage:
    from apps.ai_assistant.services.dedup import DedupService

    svc = DedupService()
    candidates = svc.scan_model('orgbase', limit=500)    # find duplicates
    result = svc.extract_duplicates(candidates[0])        # extract to pending
    svc.mark_reviewed(bundle_id, action='keep_retained')  # operator decision
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone as tz
from pathlib import Path
from typing import Any, Optional

from django.apps import apps
from django.db import transaction
from django.db.models import Q

logger = logging.getLogger(__name__)

# Filesystem paths relative to project root
DEDUP_BASE = Path(__file__).resolve().parents[3] / 'sync' / 'dedup'
DEDUP_PENDING = DEDUP_BASE / 'pending'
DEDUP_PROCESSED = DEDUP_BASE / 'processed'

# Internal connection for dedup bundles — created on first use
DEDUP_CONNECTION_IDA = 'conn-alice-dedup'
ESCALATION_CONNECTION_ID = 32  # Alice → Claude Code

# Matching strategies per model — (field_group_name, field_list, threshold_description)
MATCH_STRATEGIES: dict[str, list[tuple[str, list[str], str]]] = {
    'orgbase': [
        ('name_zip', ['display_name__8', 'address__zip__5'], 'First 8 chars of name + first 5 chars of zip'),
        ('email', ['email__exact'], 'Exact email match'),
        ('phone', ['phone__digits_last_7'], 'Last 7 digits of phone'),
    ],
    'contact': [
        ('name_email', ['name__lower', 'email__exact'], 'Same name (case-insensitive) + same email'),
        ('email', ['email__exact'], 'Exact email match'),
        ('phone', ['phone__digits_last_7'], 'Last 7 digits of phone'),
    ],
    'item': [
        ('sku', ['sku__exact'], 'Exact SKU match'),
        ('name_vendor', ['name__lower', 'vendor_id__exact'], 'Same name + same vendor'),
        ('upc', ['upc__exact'], 'Exact UPC match'),
    ],
}


def _now_ms() -> int:
    return int(time.time() * 1000)


def _ensure_dirs():
    """Create dedup directories if they don't exist."""
    DEDUP_PENDING.mkdir(parents=True, exist_ok=True)
    DEDUP_PROCESSED.mkdir(parents=True, exist_ok=True)


def _get_or_create_dedup_connection():
    """Get or create the internal connection for dedup bundles."""
    Connection = apps.get_model('sync', 'Connection')
    conn = Connection.objects.filter(ida=DEDUP_CONNECTION_IDA, is_active=True).first()
    if conn:
        return conn
    conn = Connection.objects.create(
        ida=DEDUP_CONNECTION_IDA,
        name='Alice Dedup',
        type='internal',
        status='active',
        purpose='ingest',
        comment='Internal connection for duplicate detection and extraction. '
                'Bundles reference retained records; payloads stored as files '
                'in sync/dedup/pending/ and sync/dedup/processed/.',
        config={
            'from_agent': 'alice',
            'dedup_paths': {
                'pending': 'sync/dedup/pending/',
                'processed': 'sync/dedup/processed/',
            },
        },
        rules={
            'auto_deactivate': True,
            'require_operator_review': True,
            'escalate_when': [
                'More than 5 duplicates in one group',
                'Retained record has lower health_rating than a duplicate',
                'Duplicates have different linked transactions',
            ],
        },
    )
    logger.info('Created dedup connection: id=%d ida=%s', conn.pk, conn.ida)
    return conn


def _serialize_record(obj) -> dict:
    """Serialize a Django model instance to a JSON-safe dict."""
    data = {}
    for field in obj._meta.fields:
        val = getattr(obj, field.name, None)
        if val is None:
            data[field.name] = None
        elif isinstance(val, (int, float, bool, str)):
            data[field.name] = val
        elif isinstance(val, (dict, list)):
            data[field.name] = val
        else:
            data[field.name] = str(val)
    return data


def _normalize_for_match(value: str, rule: str) -> str:
    """Apply a matching rule to normalize a value for comparison."""
    if not value:
        return ''
    if rule.endswith('__lower'):
        return value.strip().lower()
    if '__' in rule:
        parts = rule.split('__')
        if len(parts) >= 2:
            if parts[-1].isdigit():
                # Prefix match: field__8 means first 8 chars
                n = int(parts[-1])
                return value.strip().lower()[:n]
            if parts[-1] == 'exact':
                return value.strip().lower()
            if parts[-1] == 'digits_last_7':
                digits = ''.join(c for c in value if c.isdigit())
                return digits[-7:] if len(digits) >= 7 else digits
    return value.strip().lower()


def _extract_field_value(obj, field_spec: str) -> str:
    """Extract a field value from an object, supporting dotted paths into JSON fields."""
    # field_spec format: "field__rule" or "field__subfield__rule"
    parts = field_spec.split('__')
    field_name = parts[0]

    val = getattr(obj, field_name, None)
    if val is None:
        return ''

    # Walk into JSON/dict fields
    if isinstance(val, dict) and len(parts) >= 3:
        # e.g., address__zip__5 → obj.address['zip'], then first 5 chars
        subfield = parts[1]
        val = val.get(subfield, '')

    if not isinstance(val, str):
        val = str(val) if val else ''

    return val


class DedupService:
    """Alice's duplicate detection and extraction service."""

    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm

    def scan_model(
        self,
        model_name: str,
        limit: int = 500,
        strategy_name: Optional[str] = None,
    ) -> list[dict]:
        """Scan a model for duplicate candidates.

        Returns a list of duplicate groups:
        [
            {
                'strategy': 'name_zip',
                'match_key': 'acme wi_531',
                'retained_id': 123,       # highest health_rating
                'duplicate_ids': [456, 789],
                'record_count': 3,
                'confidence': 'high',
            },
            ...
        ]
        """
        strategies = MATCH_STRATEGIES.get(model_name.lower(), [])
        if not strategies:
            logger.warning('No match strategies defined for model: %s', model_name)
            return []

        if strategy_name:
            strategies = [s for s in strategies if s[0] == strategy_name]

        # Resolve model
        model_map = {
            'orgbase': ('orgs', 'OrgBase'),
            'contact': ('orgs', 'Contact'),
            'item': ('products', 'Item'),
        }
        app_model = model_map.get(model_name.lower())
        if not app_model:
            logger.warning('Unknown model for dedup: %s', model_name)
            return []

        Model = apps.get_model(*app_model)
        qs = Model.objects.filter(is_active=True, is_deleted=False).order_by('pk')[:limit]
        records = list(qs)

        all_groups = []
        seen_ids = set()

        for strat_name, field_specs, description in strategies:
            # Build match keys
            buckets: dict[str, list] = {}
            for obj in records:
                if obj.pk in seen_ids:
                    continue
                key_parts = []
                skip = False
                for spec in field_specs:
                    raw_val = _extract_field_value(obj, spec)
                    normalized = _normalize_for_match(raw_val, spec)
                    if not normalized:
                        skip = True
                        break
                    key_parts.append(normalized)
                if skip:
                    continue
                match_key = '|'.join(key_parts)
                buckets.setdefault(match_key, []).append(obj)

            # Groups with 2+ records are duplicates
            for match_key, group in buckets.items():
                if len(group) < 2:
                    continue

                # Retained = highest health_rating, then lowest pk (oldest)
                group.sort(key=lambda o: (-getattr(o, 'health_rating', 0), o.pk))
                retained = group[0]
                duplicates = group[1:]

                # Mark these IDs as seen so other strategies don't re-match
                for obj in group:
                    seen_ids.add(obj.pk)

                should_escalate = (
                    len(duplicates) > 5
                    or any(
                        getattr(d, 'health_rating', 0) > getattr(retained, 'health_rating', 0)
                        for d in duplicates
                    )
                )

                all_groups.append({
                    'strategy': strat_name,
                    'strategy_description': description,
                    'model': model_name,
                    'match_key': match_key,
                    'retained_id': retained.pk,
                    'retained_name': getattr(retained, 'display_name', '') or getattr(retained, 'name', ''),
                    'duplicate_ids': [d.pk for d in duplicates],
                    'record_count': len(group),
                    'confidence': 'high' if strat_name in ('email', 'sku', 'upc') else 'medium',
                    'escalate': should_escalate,
                })

        logger.info(
            'Dedup scan: model=%s records=%d groups=%d',
            model_name, len(records), len(all_groups),
        )
        return all_groups

    def extract_duplicates(self, group: dict) -> dict:
        """Extract duplicate records from the database into pending files.

        Args:
            group: A duplicate group dict from scan_model()

        Returns:
            {bundle_id, file_path, retained_id, extracted_count, escalated}
        """
        _ensure_dirs()

        model_name = group['model']
        retained_id = group['retained_id']
        duplicate_ids = group['duplicate_ids']

        # Resolve model
        model_map = {
            'orgbase': ('orgs', 'OrgBase'),
            'contact': ('orgs', 'Contact'),
            'item': ('products', 'Item'),
        }
        app_model = model_map.get(model_name.lower())
        if not app_model:
            return {'error': f'Unknown model: {model_name}'}

        Model = apps.get_model(*app_model)
        Bundle = apps.get_model('sync', 'Bundle')

        # Load records
        try:
            retained = Model.objects.get(pk=retained_id)
        except Model.DoesNotExist:
            return {'error': f'Retained record {retained_id} not found'}

        duplicates = list(Model.objects.filter(pk__in=duplicate_ids))
        if not duplicates:
            return {'error': 'No duplicate records found'}

        # Serialize all records
        retained_data = _serialize_record(retained)
        duplicate_data = [_serialize_record(d) for d in duplicates]

        # Build the extraction payload
        ts = datetime.now(tz.utc).strftime('%Y%m%dT%H%M%S')
        filename = f'{model_name}_{retained_id}_{ts}.json'
        payload = {
            'model': model_name,
            'strategy': group['strategy'],
            'match_key': group['match_key'],
            'confidence': group['confidence'],
            'dt_extracted': datetime.now(tz.utc).isoformat(),
            'retained': {
                'id': retained_id,
                'data': retained_data,
            },
            'duplicates': [
                {'id': d.pk, 'data': dd}
                for d, dd in zip(duplicates, duplicate_data)
            ],
        }

        # Write to pending
        file_path = DEDUP_PENDING / filename
        file_path.write_text(json.dumps(payload, indent=2, default=str))

        # Create Bundle record
        conn = _get_or_create_dedup_connection()
        bundle = Bundle.objects.create(
            connection=conn,
            direction='sync',
            status='queued',
            alert='info' if not group.get('escalate') else 'warning',
            payload={'file': str(file_path.relative_to(DEDUP_BASE.parent.parent))},
            config={
                'type': 'dedup_extraction',
                'model': model_name,
                'strategy': group['strategy'],
                'match_key': group['match_key'],
                'retained_id': retained_id,
                'duplicate_ids': duplicate_ids,
                'file_path': str(file_path),
                'confidence': group['confidence'],
                'escalated': group.get('escalate', False),
            },
            size=file_path.stat().st_size,
        )

        # Hard delete duplicates from DB — the bundle file is the archive.
        # Junk does not grow better with age.
        with transaction.atomic():
            Model.objects.filter(pk__in=duplicate_ids).delete()

        extracted_count = len(duplicates)
        logger.info(
            'Dedup extracted: model=%s retained=%d duplicates=%d bundle=%d file=%s',
            model_name, retained_id, extracted_count, bundle.pk, filename,
        )

        # Escalate to Claude if needed
        escalated = False
        if group.get('escalate'):
            escalated = self._escalate_to_claude(bundle, group, retained, duplicates)

        return {
            'bundle_id': bundle.pk,
            'file_path': str(file_path),
            'retained_id': retained_id,
            'extracted_count': extracted_count,
            'escalated': escalated,
        }

    def copy_field(
        self,
        bundle_id: int,
        duplicate_id: int,
        field_name: str,
    ) -> dict:
        """Copy one field from a duplicate (in the bundle file) to the retained record.

        User clicks a field on an indented duplicate row — that value
        overwrites the same field on the retained record. One field at a time.

        Args:
            bundle_id: Bundle PK
            duplicate_id: PK of the duplicate record (in bundle payload)
            field_name: field to copy

        Returns:
            {retained_id, field, old_value, new_value}
        """
        bundle, config, Model = self._resolve_bundle(bundle_id)
        if isinstance(bundle, dict):
            return bundle  # error

        retained_id = config['retained_id']
        file_path = Path(config.get('file_path', ''))

        if not file_path.exists():
            return {'error': 'Bundle file not found'}

        payload = json.loads(file_path.read_text())
        dup_data_map = {d['id']: d['data'] for d in payload.get('duplicates', [])}
        dup_record = dup_data_map.get(duplicate_id)
        if not dup_record:
            return {'error': f'Duplicate {duplicate_id} not in bundle'}

        if field_name not in dup_record:
            return {'error': f'Field {field_name} not in duplicate data'}

        try:
            retained = Model.objects.get(pk=retained_id)
        except Model.DoesNotExist:
            return {'error': f'Retained record {retained_id} not found'}

        old_value = getattr(retained, field_name, None)
        new_value = dup_record[field_name]
        setattr(retained, field_name, new_value)
        retained.save()

        # Log the copy in bundle response
        response = bundle.response or {}
        copies = response.get('field_copies', [])
        copies.append({
            'field': field_name,
            'from_duplicate': duplicate_id,
            'old_value': str(old_value)[:200] if old_value else None,
            'new_value': str(new_value)[:200] if new_value else None,
            'dt': _now_ms(),
        })
        response['field_copies'] = copies
        bundle.response = response
        bundle.save(update_fields=['response'])

        logger.info(
            'Dedup copy_field: bundle=%d field=%s from dup=%d to retained=%d',
            bundle_id, field_name, duplicate_id, retained_id,
        )

        return {
            'retained_id': retained_id,
            'field': field_name,
            'old_value': old_value,
            'new_value': new_value,
        }

    def remove_from_bundle(
        self,
        bundle_id: int,
        duplicate_id: int,
    ) -> dict:
        """Hard delete a duplicate from the DB and delete it from the bundle.

        Gone from the DB, gone from the bundle. Users work through the
        bundle until it's empty. No archiving junk — back up the bundle
        first if you want to keep it.

        Args:
            bundle_id: Bundle PK
            duplicate_id: PK of the record to remove

        Returns:
            {deleted_id, remaining_duplicates}
        """
        bundle, config, Model = self._resolve_bundle(bundle_id)
        if isinstance(bundle, dict):
            return bundle  # error

        # Hard delete from DB (may already be deleted from extract)
        Model.objects.filter(pk=duplicate_id).delete()

        # Remove from bundle config
        dup_ids = config.get('duplicate_ids', [])
        if duplicate_id in dup_ids:
            dup_ids.remove(duplicate_id)
            config['duplicate_ids'] = dup_ids
            bundle.config = config

        # Remove from bundle file
        file_path = Path(config.get('file_path', ''))
        if file_path.exists():
            payload = json.loads(file_path.read_text())
            payload['duplicates'] = [
                d for d in payload.get('duplicates', [])
                if d.get('id') != duplicate_id
            ]
            file_path.write_text(json.dumps(payload, indent=2, default=str))

        bundle.save(update_fields=['config'])

        # If no duplicates left, bundle is done — delete the file
        if not dup_ids:
            bundle.status = 'success'
            bundle.dt_processed = _now_ms()
            bundle.save(update_fields=['status', 'dt_processed'])
            if file_path.exists():
                file_path.unlink()

        logger.info(
            'Dedup remove: bundle=%d deleted=%d remaining=%d',
            bundle_id, duplicate_id, len(dup_ids),
        )

        return {
            'deleted_id': duplicate_id,
            'remaining_duplicates': len(dup_ids),
        }

    def mark_done(self, bundle_id: int, reviewer: str = '') -> dict:
        """User is done reviewing this bundle. Delete the file.

        The user has worked through every duplicate — copied what they
        wanted, removed the rest. Nothing left to keep.

        Args:
            bundle_id: Bundle PK
            reviewer: who reviewed

        Returns:
            {status, file_deleted}
        """
        bundle, config, _ = self._resolve_bundle(bundle_id)
        if isinstance(bundle, dict):
            return bundle  # error

        bundle.status = 'success'
        bundle.dt_processed = _now_ms()
        bundle.response = {
            **(bundle.response or {}),
            'action': 'done',
            'reviewer': reviewer,
            'dt_reviewed': _now_ms(),
        }
        bundle.save()

        # Delete the file — user is done, nothing to archive
        file_path = Path(config.get('file_path', ''))
        file_deleted = False
        if file_path.exists():
            file_path.unlink()
            file_deleted = True

        return {'status': 'success', 'file_deleted': file_deleted}

    def _resolve_bundle(self, bundle_id: int):
        """Resolve bundle, config, and Model. Returns (bundle, config, Model) or error dict."""
        Bundle = apps.get_model('sync', 'Bundle')
        try:
            bundle = Bundle.objects.get(pk=bundle_id)
        except Bundle.DoesNotExist:
            return {'error': f'Bundle {bundle_id} not found'}, None, None

        config = bundle.config or {}
        if config.get('type') != 'dedup_extraction':
            return {'error': 'Not a dedup bundle'}, None, None

        model_map = {
            'orgbase': ('orgs', 'OrgBase'),
            'contact': ('orgs', 'Contact'),
            'item': ('products', 'Item'),
        }
        app_model = model_map.get(config.get('model', '').lower())
        if not app_model:
            return {'error': f"Unknown model: {config.get('model')}"}, None, None

        Model = apps.get_model(*app_model)
        return bundle, config, Model


    def list_pending(self) -> list[dict]:
        """List all pending dedup bundles awaiting operator review."""
        Bundle = apps.get_model('sync', 'Bundle')
        conn = _get_or_create_dedup_connection()

        bundles = Bundle.objects.filter(
            connection=conn,
            dt_processed=0,
        ).order_by('-dt_created')

        results = []
        for b in bundles:
            config = b.config or {}
            results.append({
                'bundle_id': b.pk,
                'model': config.get('model'),
                'retained_id': config.get('retained_id'),
                'duplicate_count': len(config.get('duplicate_ids', [])),
                'strategy': config.get('strategy'),
                'confidence': config.get('confidence'),
                'escalated': config.get('escalated', False),
                'file_path': config.get('file_path'),
                'dt_created': b.dt_created,
            })
        return results

    def load_pending_file(self, bundle_id: int) -> Optional[dict]:
        """Load the pending file for operator comparison."""
        Bundle = apps.get_model('sync', 'Bundle')
        try:
            bundle = Bundle.objects.get(pk=bundle_id)
        except Bundle.DoesNotExist:
            return None

        config = bundle.config or {}
        file_path = Path(config.get('file_path', ''))
        if not file_path.exists():
            return None

        return json.loads(file_path.read_text())

    def _escalate_to_claude(self, bundle, group, retained, duplicates) -> bool:
        """Create an Action record for Claude Code to review a complex dedup case."""
        try:
            Action = apps.get_model('core', 'Action')
        except LookupError:
            logger.warning('Action model not found — cannot escalate dedup')
            return False

        reason_parts = []
        if len(duplicates) > 5:
            reason_parts.append(f'{len(duplicates)} duplicates (complex group)')
        for d in duplicates:
            if getattr(d, 'health_rating', 0) > getattr(retained, 'health_rating', 0):
                reason_parts.append(
                    f'Duplicate #{d.pk} has higher health ({d.health_rating}) '
                    f'than retained #{retained.pk} ({retained.health_rating})'
                )
                break

        Action.objects.create(
            ida=f'ALICE-DEDUP-{bundle.pk}',
            name=f'Dedup review: {group["model"]} — {group["match_key"]}',
            status='pending',
            config={
                'escalation': {
                    'to': 'claude_code',
                    'reason': '; '.join(reason_parts) or 'Complex dedup case',
                    'user_request': 'Review duplicate group and recommend merge strategy',
                    'context': {
                        'bundle_id': bundle.pk,
                        'model': group['model'],
                        'strategy': group['strategy'],
                        'match_key': group['match_key'],
                        'retained_id': group['retained_id'],
                        'duplicate_ids': group['duplicate_ids'],
                        'confidence': group['confidence'],
                    },
                },
            },
        )
        logger.info('Escalated dedup bundle %d to Claude Code', bundle.pk)
        return True

    def scan_all(self, limit_per_model: int = 500) -> dict:
        """Scan all configured models for duplicates. Nightly task entry point."""
        results = {}
        for model_name in MATCH_STRATEGIES:
            groups = self.scan_model(model_name, limit=limit_per_model)
            results[model_name] = {
                'groups_found': len(groups),
                'total_duplicates': sum(len(g['duplicate_ids']) for g in groups),
                'escalations': sum(1 for g in groups if g.get('escalate')),
            }
        return results

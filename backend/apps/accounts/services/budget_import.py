"""
Budget Import Processor
========================

Accepts Excel (.xlsx), CSV, or JSON. Parses into Budget records.
Creates a Bundle for audit trail. Validates account codes against GlAccount.
Locked periods (dt_journaled > 0) are not modified.

Supported formats:
  - CSV: header row + data rows (see samples/budget_monthly_example.csv)
  - Excel: first sheet, header row + data rows (same columns as CSV)
  - JSON: list of objects with same keys as CSV columns

Required columns: period, dt_period_start, dt_period_end, account, debit, credit
Optional columns: description

Usage via manage action:
    POST /wcapi/manage/
    { "action": "import_budget", "params": {
        "connection_id": 42,       # Connection record (schedule-payroll, etc.)
        "file_path": "/tmp/budget.csv",  # or .xlsx or .json
        "data": "..."              # alternative: raw content (CSV/JSON string)
    }}
"""
from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

from django.apps import apps as dj_apps
from django.db import transaction

logger = logging.getLogger(__name__)


REQUIRED_COLUMNS = {'period', 'dt_period_start', 'dt_period_end', 'account', 'debit', 'credit'}
OPTIONAL_COLUMNS = {'description', 'purchase_id'}


def _parse_csv(content: str) -> list[dict]:
    """Parse CSV string into list of row dicts."""
    reader = csv.DictReader(io.StringIO(content))
    return [dict(row) for row in reader]


def _parse_json(content: str) -> list[dict]:
    """Parse JSON string (list of objects) into list of row dicts."""
    data = json.loads(content)
    if isinstance(data, dict) and 'entries' in data:
        data = data['entries']
    if not isinstance(data, list):
        raise ValueError("JSON must be a list of objects or {entries: [...]}")
    return data


def _parse_excel(file_path: str) -> list[dict]:
    """Parse Excel file (first sheet) into list of row dicts."""
    import openpyxl
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not rows:
        return []

    headers = [str(h).strip().lower() for h in rows[0]]
    result = []
    for row in rows[1:]:
        if all(v is None for v in row):
            continue
        result.append(dict(zip(headers, row)))
    return result


def _detect_format(file_path: Optional[str], data: Optional[str]) -> str:
    """Detect format from file extension or content."""
    if file_path:
        ext = Path(file_path).suffix.lower()
        if ext in ('.xlsx', '.xls'):
            return 'excel'
        if ext == '.json':
            return 'json'
        return 'csv'
    if data:
        stripped = data.strip()
        if stripped.startswith('[') or stripped.startswith('{'):
            return 'json'
        return 'csv'
    raise ValueError("Either file_path or data must be provided")


def _validate_row(row: dict, row_num: int, valid_accounts: set) -> tuple[dict, list[str]]:
    """Validate and normalize a single row. Returns (normalized_row, errors)."""
    errors = []

    # Check required fields
    for col in REQUIRED_COLUMNS:
        if col not in row or row[col] is None or str(row[col]).strip() == '':
            errors.append(f"Row {row_num}: missing required column '{col}'")

    if errors:
        return row, errors

    # Normalize values
    try:
        period = str(row['period']).strip()
        dt_start = int(row['dt_period_start'])
        dt_end = int(row['dt_period_end'])
        account = str(row['account']).strip()
        debit = Decimal(str(row['debit']).strip())
        credit = Decimal(str(row['credit']).strip())
    except (ValueError, InvalidOperation, TypeError) as e:
        errors.append(f"Row {row_num}: invalid value — {e}")
        return row, errors

    # Validate account exists in chart of accounts
    if valid_accounts and account not in valid_accounts:
        errors.append(f"Row {row_num}: account '{account}' not found in chart of accounts")

    # Validate period boundaries
    if dt_start >= dt_end:
        errors.append(f"Row {row_num}: dt_period_start must be before dt_period_end")

    if debit < 0 or credit < 0:
        errors.append(f"Row {row_num}: debit and credit must be non-negative")

    normalized = {
        'period': period,
        'dt_period_start': dt_start,
        'dt_period_end': dt_end,
        'account': account,
        'debit': debit,
        'credit': credit,
        'description': str(row.get('description', '')).strip(),
        'purchase_id': int(row['purchase_id']) if row.get('purchase_id') else None,
    }

    return normalized, errors


def import_budget(
    connection_id: Optional[int] = None,
    file_path: Optional[str] = None,
    data: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    """Import budget entries from file or data string.

    Args:
        connection_id: Connection record for audit trail (optional)
        file_path: Path to .csv, .xlsx, or .json file
        data: Raw CSV or JSON string (alternative to file_path)
        dry_run: If True, validate only — don't create records

    Returns:
        {
            'status': 'success' | 'error' | 'dry_run',
            'created': 12,
            'updated': 3,
            'skipped_locked': 2,
            'errors': [...],
            'bundle_id': 42,
        }
    """
    Budget = dj_apps.get_model('accounts', 'Budget')
    GlAccount = dj_apps.get_model('accounts', 'GlAccount')
    Connection = dj_apps.get_model('sync', 'Connection')
    Bundle = dj_apps.get_model('sync', 'Bundle')

    # Load valid account codes
    valid_accounts = set(
        GlAccount.objects.values_list('ida', flat=True).exclude(ida='')
    )

    # Parse input
    fmt = _detect_format(file_path, data)

    if fmt == 'excel':
        if not file_path:
            raise ValueError("Excel format requires file_path")
        rows = _parse_excel(file_path)
    elif fmt == 'json':
        content = data or Path(file_path).read_text()
        rows = _parse_json(content)
    else:
        content = data or Path(file_path).read_text()
        rows = _parse_csv(content)

    if not rows:
        return {'status': 'error', 'errors': ['No data rows found'], 'created': 0, 'updated': 0, 'skipped_locked': 0}

    # Validate all rows
    all_errors = []
    validated = []
    for i, row in enumerate(rows, start=2):  # row 2 = first data row (row 1 = header)
        normalized, row_errors = _validate_row(row, i, valid_accounts)
        all_errors.extend(row_errors)
        if not row_errors:
            validated.append(normalized)

    if all_errors and not validated:
        return {'status': 'error', 'errors': all_errors, 'created': 0, 'updated': 0, 'skipped_locked': 0}

    if dry_run:
        return {
            'status': 'dry_run',
            'valid_rows': len(validated),
            'errors': all_errors,
            'created': 0,
            'updated': 0,
            'skipped_locked': 0,
        }

    # Create Bundle for audit trail
    bundle = None
    if connection_id:
        try:
            conn = Connection.objects.get(pk=connection_id)
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            bundle = Bundle.objects.create(
                connection=conn,
                direction='pull',
                model_name='budget',
                status='running',
                dt_processed=now_ms,
                config={'format': fmt, 'file': file_path or 'inline_data'},
            )
        except Connection.DoesNotExist:
            pass

    # Create/update Budget records
    created = 0
    updated = 0
    skipped_locked = 0

    with transaction.atomic():
        for row in validated:
            # Check if locked period
            existing = Budget.objects.filter(
                period=row['period'],
                account=row['account'],
            ).first()

            if existing:
                if existing.dt_journaled > 0:
                    skipped_locked += 1
                    continue
                # Update existing
                existing.dt_period_start = row['dt_period_start']
                existing.dt_period_end = row['dt_period_end']
                existing.debit = row['debit']
                existing.credit = row['credit']
                existing.description = row['description']
                if row['purchase_id']:
                    existing.purchase_id = row['purchase_id']
                if bundle:
                    existing.bundle = bundle
                existing.save()
                updated += 1
            else:
                Budget.objects.create(
                    period=row['period'],
                    dt_period_start=row['dt_period_start'],
                    dt_period_end=row['dt_period_end'],
                    account=row['account'],
                    debit=row['debit'],
                    credit=row['credit'],
                    description=row['description'],
                    purchase_id=row['purchase_id'],
                    bundle=bundle,
                )
                created += 1

    # Update bundle status
    if bundle:
        bundle.status = 'success' if not all_errors else 'warning'
        bundle.response = {
            'created': created,
            'updated': updated,
            'skipped_locked': skipped_locked,
            'errors': all_errors[:20],  # cap stored errors
        }
        bundle.save(update_fields=['status', 'response', 'dt_modified', 'version'])

    return {
        'status': 'success' if not all_errors else 'warning',
        'created': created,
        'updated': updated,
        'skipped_locked': skipped_locked,
        'errors': all_errors,
        'bundle_id': bundle.pk if bundle else None,
    }

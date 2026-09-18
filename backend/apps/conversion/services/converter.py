"""
Alice's data conversion pipeline.

Takes a messy file from a user, uses Claude to understand its structure,
maps it to WC3 schema, documents every oddity, and produces a clean
bundle ready for /sync/receive/.

Multiple passes — each pass refines the mapping and resolves oddities.
"""

import csv
import hashlib
import io
import json
import logging
import time
from datetime import timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.utils import timezone as dj_timezone

from apps.conversion.models import (
    ConversionProject,
    SourceFile,
    ColumnMap,
    Oddity,
    StagingRow,
    PassLog,
)

logger = logging.getLogger(__name__)


# ── WC3 Item schema for Claude's reference ──────────────────────────

WC3_ITEM_SCHEMA = {
    "scalar_fields": {
        "sku": "string, max 80, case-insensitive unique identifier",
        "name": "string, max 160, display name",
        "kind": "physical | service | bundle",
        "uom": "string, max 20, unit of measure (EA, HR, KG, LB, FT, etc.)",
        "base_uom": "string, max 20, canonical base unit for conversions",
        "description": "text, full description",
    },
    "json_fields": {
        "price": {
            "base": "float, primary sell price",
            "msrp": "float, manufacturer suggested retail",
            "retail": "float, 100% of base",
            "wholesale": "float, 90% of base",
            "distributor": "float, 75% of base",
            "currency": "string, ISO currency code, default USD",
        },
        "cost": {
            "standard": "float, standard cost",
            "avg": "float, average cost",
            "last": "float, last receipt cost",
            "landed": "float, landed cost (incl. freight/duty)",
        },
        "quantity": {
            "on_hand": "float, physical count",
            "allocated": "float, reserved for orders",
            "available": "float, on_hand minus allocated",
            "on_order": "float, on purchase orders",
        },
        "gls": {
            "inventory": "string, GL account for inventory asset",
            "cost": "string, GL account for cost",
            "cogs": "string, GL account for cost of goods sold",
            "revenue": "string, GL account for revenue",
        },
        "flags": {
            "back_order_allowed": "bool",
            "discountable": "bool",
            "serialized": "bool",
            "not_tracked": "bool",
        },
        "tax_code": {
            "code": "string, tax code identifier",
            "category": "string, tangible | service | exempt",
        },
    },
}


def _get_claude_client():
    """Load Anthropic client using Alice's API key.

    Key lookup order:
    1. allie_api_keys.json -> keys.anthropic (dedicated Anthropic key)
    2. ANTHROPIC_API_KEY environment variable
    """
    import anthropic
    key_file = Path.home() / 'Allie' / 'config' / 'allie_api_keys.json'
    if key_file.exists():
        data = json.loads(key_file.read_text())
        keys = data.get('keys', data)
        api_key = keys.get('anthropic', '')
        if api_key:
            return anthropic.Anthropic(api_key=api_key)
    # Fall back to environment variable
    return anthropic.Anthropic()


# ── File Reading ─────────────────────────────────────────────────────

def read_source_file(path: Path) -> dict:
    """Read a source file and return metadata + sample rows."""
    suffix = path.suffix.lower()
    file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    file_size = path.stat().st_size

    if suffix in ('.csv', '.tsv', '.txt'):
        return _read_delimited(path, file_hash, file_size, suffix)
    if suffix in ('.xlsx', '.xls'):
        return _read_excel(path, file_hash, file_size)
    if suffix == '.json':
        return _read_json(path, file_hash, file_size)

    raise ValueError(f"Unsupported file type: {suffix}")


def _detect_delimiter(path: Path, suffix: str) -> str:
    sample = path.read_text(encoding='utf-8', errors='replace')[:4096]
    if suffix == '.tsv':
        return '\t'
    tab_count = sample.count('\t')
    comma_count = sample.count(',')
    pipe_count = sample.count('|')
    if tab_count > comma_count and tab_count > pipe_count:
        return '\t'
    if pipe_count > comma_count:
        return '|'
    return ','


def _read_delimited(path: Path, file_hash: str, file_size: int, suffix: str) -> dict:
    delimiter = _detect_delimiter(path, suffix)
    encoding = 'utf-8'
    try:
        text = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        encoding = 'latin-1'
        text = path.read_text(encoding='latin-1')

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    headers = list(reader.fieldnames or [])
    rows = []
    total = 0
    for row in reader:
        total += 1
        if len(rows) < 20:
            rows.append(dict(row))

    file_type = 'tsv' if delimiter == '\t' else 'csv'
    return {
        'file_type': file_type,
        'file_hash': file_hash,
        'file_size': file_size,
        'raw_headers': headers,
        'sample_rows': rows,
        'row_count': total,
        'encoding': encoding,
        'delimiter': delimiter,
    }


def _read_excel(path: Path, file_hash: str, file_size: int) -> dict:
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(h or '') for h in next(rows_iter, [])]
    rows = []
    total = 0
    for row_vals in rows_iter:
        total += 1
        if len(rows) < 20:
            rows.append({h: str(v) if v is not None else '' for h, v in zip(headers, row_vals)})
    wb.close()
    return {
        'file_type': 'xlsx',
        'file_hash': file_hash,
        'file_size': file_size,
        'raw_headers': headers,
        'sample_rows': rows,
        'row_count': total,
        'encoding': 'utf-8',
        'delimiter': '',
    }


def _read_json(path: Path, file_hash: str, file_size: int) -> dict:
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if isinstance(data, list):
        rows = data[:20]
        headers = list(rows[0].keys()) if rows else []
        total = len(data)
    elif isinstance(data, dict):
        # Look for a list value
        for key, val in data.items():
            if isinstance(val, list) and val and isinstance(val[0], dict):
                rows = val[:20]
                headers = list(rows[0].keys())
                total = len(val)
                break
        else:
            rows = [data]
            headers = list(data.keys())
            total = 1
    else:
        raise ValueError("JSON must be a list of objects or an object containing a list")
    return {
        'file_type': 'json',
        'file_hash': file_hash,
        'file_size': file_size,
        'raw_headers': headers,
        'sample_rows': rows,
        'row_count': total,
        'encoding': 'utf-8',
        'delimiter': '',
    }


# ── Pass 1: Column Mapping via Claude ────────────────────────────────

def run_column_mapping(source_file: SourceFile, pass_log: PassLog) -> list[ColumnMap]:
    """Ask Claude to map source columns to WC3 schema."""
    client = _get_claude_client()

    prompt = f"""You are Alice, a data conversion specialist for WebClerk (WC3).

A user has uploaded a data file. Map each source column to the correct WC3 field.

SOURCE COLUMNS: {json.dumps(source_file.raw_headers)}

SAMPLE DATA (first rows):
{json.dumps(source_file.sample_rows[:5], indent=2)}

WC3 ITEM SCHEMA:
{json.dumps(WC3_ITEM_SCHEMA, indent=2)}

For each source column, respond with a JSON array of objects:
{{
  "source_column": "the original column name",
  "target_model": "Item" or "BillOfMaterial" or "OrgBase" or "",
  "target_field": "the WC3 field name or JSON path like price.base",
  "confidence": 0.0 to 1.0,
  "transform": "normalize_uom" or "parse_decimal" or "parse_bool" or "map_gl" or "as_is" or "",
  "reasoning": "why this mapping"
}}

If a column doesn't map to any WC3 field, set target_model and target_field to empty
strings and explain in reasoning. Respond with ONLY the JSON array, no other text."""

    t0 = time.time()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
        metadata={"user_id": "alice"},
    )
    elapsed = time.time() - t0

    pass_log.llm_calls += 1
    pass_log.llm_input_tokens += response.usage.input_tokens
    pass_log.llm_output_tokens += response.usage.output_tokens
    pass_log.duration_seconds += elapsed
    pass_log.llm_model = "claude-haiku-4-5-20251001"

    # Parse Claude's response
    text = response.content[0].text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0]
    mappings = json.loads(text)

    column_maps = []
    for m in mappings:
        # Collect sample values for this column
        samples = []
        for row in source_file.sample_rows[:10]:
            val = row.get(m['source_column'], '')
            if val and val not in samples:
                samples.append(val)
                if len(samples) >= 5:
                    break

        cm = ColumnMap.objects.create(
            source_file=source_file,
            source_column=m['source_column'],
            target_model=m.get('target_model', ''),
            target_field=m.get('target_field', ''),
            confidence=m.get('confidence', 0.0),
            transform=m.get('transform', ''),
            status='proposed' if m.get('target_field') else 'unmapped',
            reasoning=m.get('reasoning', ''),
            sample_values=samples,
            pass_number=pass_log.pass_number,
        )
        column_maps.append(cm)

    return column_maps


# ── Value Transforms ─────────────────────────────────────────────────

def _parse_decimal(value: str) -> float | None:
    if not value or not value.strip():
        return None
    cleaned = value.strip().replace(',', '').replace('$', '').replace('%', '').replace('+', '')
    try:
        return float(Decimal(cleaned))
    except (InvalidOperation, ValueError):
        return None


def _parse_bool(value: str) -> bool | None:
    if not value:
        return None
    v = value.strip().lower()
    if v in ('1', 'true', 't', 'yes', 'y'):
        return True
    if v in ('0', 'false', 'f', 'no', 'n'):
        return False
    return None


def _normalize_uom(value: str) -> str:
    from apps.products.uom import normalize_uom
    return normalize_uom(value.strip()) if value else ''


TRANSFORMS = {
    'parse_decimal': _parse_decimal,
    'parse_bool': _parse_bool,
    'normalize_uom': _normalize_uom,
    'as_is': lambda v: v.strip() if v else '',
    'map_gl': lambda v: v.strip() if v else '',
}


# ── Pass 2+: Convert Rows ───────────────────────────────────────────

def convert_rows(source_file: SourceFile, pass_log: PassLog) -> dict:
    """Apply confirmed column maps to all rows, creating StagingRows and Oddities."""
    maps = ColumnMap.objects.filter(
        source_file=source_file,
        status='confirmed',
    ).exclude(target_field='')

    if not maps.exists():
        logger.warning("No confirmed column maps for %s", source_file.filename)
        return {'staged': 0, 'rejected': 0, 'oddities': 0}

    # Group maps by target_model
    model_maps = {}
    for cm in maps:
        model_maps.setdefault(cm.target_model, []).append(cm)

    # Read full file
    path = Path(source_file.filename)
    file_meta = read_source_file(path)
    all_rows = _read_all_rows(path, file_meta)

    stats = {'staged': 0, 'rejected': 0, 'oddities': 0}

    for row_num, row in enumerate(all_rows, start=1):
        for target_model, field_maps in model_maps.items():
            data = {}
            row_oddities = []

            for cm in field_maps:
                raw_value = row.get(cm.source_column, '')
                transform_fn = TRANSFORMS.get(cm.transform, TRANSFORMS['as_is'])

                try:
                    converted = transform_fn(raw_value)
                except Exception as e:
                    row_oddities.append(Oddity(
                        project=source_file.project,
                        source_file=source_file,
                        severity='warning',
                        category='transform_error',
                        description=f"Transform '{cm.transform}' failed on '{raw_value}': {e}",
                        source_column=cm.source_column,
                        source_row=row_num,
                        source_value=str(raw_value)[:500],
                        pass_number=pass_log.pass_number,
                    ))
                    converted = None

                if converted is None and raw_value:
                    row_oddities.append(Oddity(
                        project=source_file.project,
                        source_file=source_file,
                        severity='info',
                        category='null_after_transform',
                        description=f"Value '{raw_value}' converted to null for {cm.target_field}",
                        source_column=cm.source_column,
                        source_row=row_num,
                        source_value=str(raw_value)[:500],
                        pass_number=pass_log.pass_number,
                    ))

                # Set nested JSON fields (e.g., price.base)
                _set_nested(data, cm.target_field, converted)

            # Save oddities
            if row_oddities:
                Oddity.objects.bulk_create(row_oddities)
                stats['oddities'] += len(row_oddities)

            # Determine status
            error_oddities = [o for o in row_oddities if o.severity == 'error']
            row_status = 'needs_review' if error_oddities else 'staged'
            oddity_ids = []  # Will be populated after bulk_create gives IDs

            StagingRow.objects.create(
                source_file=source_file,
                source_row_number=row_num,
                target_model=target_model,
                data=data,
                status=row_status,
                pass_number=pass_log.pass_number,
            )

            if row_status == 'staged':
                stats['staged'] += 1
            else:
                stats['rejected'] += 1

        pass_log.rows_processed += 1

    pass_log.rows_staged = stats['staged']
    pass_log.rows_rejected = stats['rejected']
    pass_log.oddities_found = stats['oddities']
    return stats


def _read_all_rows(path: Path, file_meta: dict) -> list[dict]:
    """Read all rows from a source file."""
    file_type = file_meta.get('file_type', '')
    encoding = file_meta.get('encoding', 'utf-8')

    if file_type == 'json':
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        if isinstance(data, list):
            return data
        for val in data.values():
            if isinstance(val, list) and val and isinstance(val[0], dict):
                return val
        return [data]

    delimiter = file_meta.get('delimiter', ',')
    text = path.read_text(encoding=encoding, errors='replace')
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    return list(reader)


def _set_nested(data: dict, field_path: str, value):
    """Set a value in a nested dict using dot notation: price.base -> data['price']['base']."""
    parts = field_path.split('.')
    target = data
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = value


# ── Bundle Assembly ──────────────────────────────────────────────────

def assemble_bundle(project: ConversionProject) -> dict:
    """Read all staged rows and produce a bundle payload matching WC3 schema."""
    staged = StagingRow.objects.filter(
        source_file__project=project,
        status='staged',
    ).order_by('target_model', 'source_row_number')

    payload = {}
    for row in staged:
        model_key = _model_to_bundle_key(row.target_model)
        payload.setdefault(model_key, []).append(row.data)

    return payload


def _model_to_bundle_key(model_name: str) -> str:
    """Convert model name to bundle payload key."""
    mapping = {
        'Item': 'items',
        'BillOfMaterial': 'bill_of_materials',
        'OrgBase': 'organizations',
        'GlAccount': 'gl_accounts',
    }
    return mapping.get(model_name, model_name.lower() + 's')


# ── Full Pipeline ────────────────────────────────────────────────────

def start_conversion(project_name: str, file_path: str, supplier_name: str = '') -> ConversionProject:
    """Start a new conversion project from a file."""
    path = Path(file_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    project = ConversionProject.objects.create(
        name=project_name,
        supplier_name=supplier_name,
    )

    file_meta = read_source_file(path)
    source_file = SourceFile.objects.create(
        project=project,
        filename=str(path),
        file_type=file_meta['file_type'],
        file_size=file_meta['file_size'],
        file_hash=file_meta['file_hash'],
        raw_headers=file_meta['raw_headers'],
        row_count=file_meta['row_count'],
        sample_rows=file_meta['sample_rows'],
        encoding=file_meta['encoding'],
        delimiter=file_meta['delimiter'],
    )

    # Pass 1: Column mapping
    pass_log = PassLog.objects.create(
        project=project,
        pass_number=1,
        focus='initial_column_mapping',
    )

    column_maps = run_column_mapping(source_file, pass_log)

    pass_log.status = 'awaiting_review'
    pass_log.dt_completed = dj_timezone.now()
    pass_log.save()

    project.pass_count = 1
    project.stats = {
        'columns_total': len(column_maps),
        'columns_mapped': sum(1 for cm in column_maps if cm.target_field),
        'columns_unmapped': sum(1 for cm in column_maps if not cm.target_field),
        'high_confidence': sum(1 for cm in column_maps if cm.confidence >= 0.8),
        'low_confidence': sum(1 for cm in column_maps if 0 < cm.confidence < 0.5),
    }
    project.save()

    return project


def run_conversion_pass(project: ConversionProject) -> PassLog:
    """Run the next conversion pass — apply confirmed maps and convert rows."""
    project.pass_count += 1
    pass_number = project.pass_count

    pass_log = PassLog.objects.create(
        project=project,
        pass_number=pass_number,
        focus='row_conversion',
    )

    for source_file in project.source_files.all():
        stats = convert_rows(source_file, pass_log)

    pass_log.status = 'complete'
    pass_log.dt_completed = dj_timezone.now()
    pass_log.save()

    project.stats['last_pass'] = {
        'pass_number': pass_number,
        'staged': pass_log.rows_staged,
        'rejected': pass_log.rows_rejected,
        'oddities': pass_log.oddities_found,
    }
    project.save()

    return pass_log

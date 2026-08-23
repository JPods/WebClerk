#!/usr/bin/env python3
"""
StatementHarvester — Drop bank statements into a folder. We eat them.

Outputs JSON files, not database records. The JSON file is the user's
working space. Only business lines that survive classification get
promoted to psql Payment records. Personal data never enters the database.

Each line gets a UUID at harvest time — idempotent promotion (no duplicates).

Supported formats:
  - Wells Fargo CC (2025+): Month, Post Date, Description, Amount, Category
  - Wells Fargo (legacy): Date, Amount, *, empty, Description (no header)
  - USAA (checking + CC): Date, Description, Original Description, Category, Amount, Status
  - Wise: ID, Status, Direction, Created on, ..., Source amount, ..., Target name
  - Domain registrar (GoDaddy): Receipt number, ..., Order date, Product, Name, ..., Total
  - Generic CSV with date + amount + description columns

Usage:
    # Harvest a folder → creates JSON files in the output directory
    python3 tools/statement_harvester.py ~/Taxes/2025/ --out ~/Allie/statements/

    # Harvest to default location (~/Allie/statements/)
    python3 tools/statement_harvester.py ~/Taxes/2025/

    # Preview as JSON to stdout
    python3 tools/statement_harvester.py ~/Taxes/2025/ --preview

    # Check for missing expected statements
    python3 tools/statement_harvester.py ~/Taxes/2025/ --check
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Optional


# ─── Bank detection from file content ────────────────────────────────

BANK_SIGNATURES = [
    (lambda h, r: 'month' in h and 'post date' in h,
     'wellsfargo_cc', 'Wells Fargo Credit Card'),
    (lambda h, r: 'original description' in h or ('description' in h and 'status' in h and 'category' in h),
     'usaa', 'USAA'),
    (lambda h, r: 'direction' in h and 'source fee amount' in h,
     'wise', 'Wise'),
    (lambda h, r: 'receipt number' in h and 'order total' in h,
     'registrar', 'Domain Registrar'),
    (lambda h, r: len(r) >= 4 and _is_date(r[0]) and _is_number(r[1]) and r[2].strip() == '*',
     'wellsfargo_checking', 'Wells Fargo Checking'),
    (lambda h, r: 'date' in h and 'amount' in h,
     'generic', 'Generic Bank'),
]


def _is_date(s: str) -> bool:
    try:
        _parse_date(s)
        return True
    except ValueError:
        return False


def _is_number(s: str) -> bool:
    try:
        float(s.strip().strip('"').replace(',', '').replace('$', ''))
        return True
    except ValueError:
        return False


def detect_bank(headers: list[str], first_row: list[str]) -> tuple[str, str, str]:
    h = [c.strip().lower() for c in headers]
    for test_fn, source, name in BANK_SIGNATURES:
        try:
            if test_fn(h, first_row):
                return source, source, name
        except (IndexError, ValueError):
            continue
    return 'unknown', 'unknown', 'Unknown Bank'


# ─── Date and amount parsing ────────────────────────────────────────

def _parse_date(s: str) -> date:
    s = s.strip().strip('"')
    for fmt in ('%m/%d/%Y', '%Y-%m-%d', '%m/%d/%y'):
        try:
            d = datetime.strptime(s, fmt)
            if d.year < 100:
                d = d.replace(year=d.year + 2000)
            return d.date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {s}")


def _parse_amount(s: str) -> float:
    s = s.strip().strip('"').replace('$', '').replace(',', '')
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
    return float(s)


def _month_date(month_str: str, day_str: str) -> date:
    parts = month_str.strip().split()
    if len(parts) == 2:
        month_name, year = parts[0], int(parts[1])
    else:
        month_name, year = month_str.strip(), datetime.now().year
    day_str = day_str.strip()
    m, d = day_str.split('/')
    return date(year, int(m), int(d))


# ─── Format-specific parsers ────────────────────────────────────────

def parse_usaa(rows, source):
    lines = []
    for row in rows:
        if len(row) < 5:
            continue
        try:
            dt = _parse_date(row[0])
            amount = _parse_amount(row[4])
        except (ValueError, IndexError):
            continue
        lines.append(_make_line(
            dt=dt, description=row[1].strip().strip('"'), amount=amount, source=source,
            raw_text=','.join(row),
            bank_category=row[3].strip().strip('"') if len(row) > 3 else '',
            extra={'original_description': row[2].strip().strip('"') if len(row) > 2 else '',
                   'status': row[5].strip() if len(row) > 5 else ''},
        ))
    return lines


def parse_wf_cc_2025(rows, source):
    lines = []
    for row in rows:
        if len(row) < 4:
            continue
        try:
            dt = _month_date(row[0], row[1])
            amount = _parse_amount(row[3])
        except (ValueError, IndexError):
            continue
        lines.append(_make_line(
            dt=dt, description=row[2].strip(), amount=amount, source=source,
            raw_text=','.join(row),
            bank_category=row[4].strip() if len(row) > 4 else '',
        ))
    return lines


def parse_wf_legacy(rows, source):
    lines = []
    for row in rows:
        if len(row) < 5:
            continue
        try:
            dt = _parse_date(row[0])
            amount = _parse_amount(row[1])
        except (ValueError, IndexError):
            continue
        lines.append(_make_line(
            dt=dt, description=row[4].strip().strip('"') if len(row) > 4 else row[3].strip().strip('"'),
            amount=amount, source=source, raw_text=','.join(row),
        ))
    return lines


def parse_wise(rows, source):
    lines = []
    for row in rows:
        if len(row) < 11:
            continue
        try:
            dt = datetime.strptime(row[3].strip().strip('"'), '%Y-%m-%d %H:%M:%S').date()
        except (ValueError, IndexError):
            continue
        direction = row[2].strip().strip('"').upper()
        try:
            source_amount = _parse_amount(row[10])
        except (ValueError, IndexError):
            continue
        if direction == 'OUT':
            source_amount = -abs(source_amount)
        target_name = row[12].strip().strip('"') if len(row) > 12 else ''
        reference = row[16].strip().strip('"') if len(row) > 16 else ''
        lines.append(_make_line(
            dt=dt, description=f"Wise → {target_name}" if target_name else "Wise transfer",
            amount=source_amount, source=source, raw_text=','.join(row),
            extra={'wise_id': row[0].strip(), 'direction': direction,
                   'target_name': target_name, 'reference': reference, 'status': row[1].strip()},
        ))
    return lines


def parse_registrar(rows, source):
    lines = []
    for row in rows:
        if len(row) < 10:
            continue
        try:
            dt_str = row[2].strip().strip('"')
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00')).date()
        except (ValueError, IndexError):
            continue
        try:
            total = -abs(_parse_amount(row[9]))
        except (ValueError, IndexError):
            continue
        product = row[3].strip().strip('"')
        name = row[4].strip().strip('"')
        desc = f"{product}: {name[:80]}" if name else product
        lines.append(_make_line(
            dt=dt, description=desc, amount=total, source=source,
            raw_text=','.join(c[:50] for c in row),
            extra={'receipt_number': row[0].strip(), 'product': product,
                   'currency': row[10].strip() if len(row) > 10 else 'USD',
                   'payment_method': f"{row[21].strip()} {row[22].strip()}" if len(row) > 22 else ''},
        ))
    return lines


def parse_generic(rows, headers, source):
    h = [c.strip().lower() for c in headers]
    date_idx = next((i for i, c in enumerate(h) if c in ('date', 'post_date', 'post date', 'transaction_date', 'transaction date')), 0)
    amt_idx = next((i for i, c in enumerate(h) if c == 'amount'), 1)
    desc_idx = next((i for i, c in enumerate(h) if c in ('description', 'memo', 'payee', 'name')), 2)
    cat_idx = next((i for i, c in enumerate(h) if c in ('category', 'type')), None)

    lines = []
    for row in rows:
        if len(row) <= max(date_idx, amt_idx, desc_idx):
            continue
        try:
            dt = _parse_date(row[date_idx])
            amount = _parse_amount(row[amt_idx])
        except (ValueError, IndexError):
            continue
        bank_cat = row[cat_idx].strip() if cat_idx is not None and cat_idx < len(row) else ''
        lines.append(_make_line(
            dt=dt, description=row[desc_idx].strip().strip('"'),
            amount=amount, source=source, raw_text=','.join(row),
            bank_category=bank_cat,
        ))
    return lines


# ─── Line builder with UUID ─────────────────────────────────────────

def _make_line(*, dt: date, description: str, amount: float, source: str,
               raw_text: str, bank_category: str = '', extra: dict = None) -> dict:
    """Build one statement line with a UUID for idempotent promotion."""
    return {
        'uuid': str(uuid.uuid4()),
        'dt_transaction': f"{dt}T00:00:00Z",
        'description': description,
        'amount': amount,
        'source': source,
        'raw_text': raw_text,
        'classification': 'unknown',
        'category': '',
        'ledger': 'post',
        'promoted': False,
        'payment_id': None,
        'merchant': '',
        'bank_category': bank_category,
        'metadata': extra or {},
    }


# ─── File harvesting ────────────────────────────────────────────────

def harvest_file(filepath: str, source_override: str = '') -> tuple[list[dict], str, str]:
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        all_rows = list(reader)

    if not all_rows:
        return [], 'empty', 'Empty File'

    first_row = all_rows[0]
    second_row = all_rows[1] if len(all_rows) > 1 else []
    fmt_key, auto_source, bank_name = detect_bank(first_row, second_row)
    source = source_override or auto_source

    if fmt_key == 'wellsfargo_checking':
        return parse_wf_legacy(all_rows, source), source, bank_name
    elif fmt_key == 'wellsfargo_cc':
        return parse_wf_cc_2025(all_rows[1:], source), source, bank_name
    elif fmt_key == 'usaa':
        return parse_usaa(all_rows[1:], source), source, bank_name
    elif fmt_key == 'wise':
        return parse_wise(all_rows[1:], source), source, bank_name
    elif fmt_key == 'registrar':
        return parse_registrar(all_rows[1:], source), source, bank_name
    elif fmt_key in ('generic', 'unknown'):
        return parse_generic(all_rows[1:], first_row, source), source, bank_name
    return [], source, bank_name


def harvest_folder(folder: str, source_override: str = '') -> tuple[list[dict], dict[str, int]]:
    p = Path(folder)
    all_lines = []
    banks_found: dict[str, int] = {}

    for f in sorted(p.rglob('*.csv')):
        lines, source, bank_name = harvest_file(str(f), source_override)
        if lines:
            all_lines.extend(lines)
            banks_found[bank_name] = banks_found.get(bank_name, 0) + len(lines)
            print(f"  {f.name}: {len(lines)} lines ({bank_name})", file=sys.stderr)
        else:
            print(f"  {f.name}: no lines parsed", file=sys.stderr)

    return all_lines, banks_found


# ─── JSON file I/O ──────────────────────────────────────────────────

def get_output_dir() -> Path:
    """Default output directory for statement JSON files."""
    d = Path.home() / 'Allie' / 'statements'
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_json(lines: list[dict], source: str, output_dir: Path = None) -> Path:
    """Save harvested lines to a JSON file. Returns the file path."""
    if output_dir is None:
        output_dir = get_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime('%Y%m%d')
    filename = f"{source}-{ts}.json"
    filepath = output_dir / filename

    # If file exists, merge — don't duplicate UUIDs
    existing = []
    if filepath.exists():
        try:
            existing = json.loads(filepath.read_text())
        except (json.JSONDecodeError, ValueError):
            existing = []

    # Dedup by raw_text hash — UUIDs are unique per harvest, raw_text identifies the same transaction
    existing_hashes = {hashlib.md5(l.get('raw_text', '').encode()).hexdigest()[:16]
                       for l in existing if isinstance(l, dict)}
    new_lines = []
    for l in lines:
        h = hashlib.md5(l.get('raw_text', '').encode()).hexdigest()[:16]
        if h not in existing_hashes:
            new_lines.append(l)
            existing_hashes.add(h)
    merged = existing + new_lines

    filepath.write_text(json.dumps(merged, indent=2))
    return filepath, len(new_lines), len(lines) - len(new_lines)


def load_json(filepath: str) -> list[dict]:
    """Load statement lines from a JSON file."""
    p = Path(filepath)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, ValueError):
        return []


def save_json_changes(filepath: str, lines: list[dict]):
    """Write updated lines back to the JSON file."""
    Path(filepath).write_text(json.dumps(lines, indent=2))


def list_json_files(output_dir: Path = None) -> list[dict]:
    """List all statement JSON files with summary info."""
    if output_dir is None:
        output_dir = get_output_dir()
    files = []
    for f in sorted(output_dir.glob('*.json')):
        try:
            data = json.loads(f.read_text())
            total = len(data)
            classified = sum(1 for l in data if l.get('classification') != 'unknown')
            promoted = sum(1 for l in data if l.get('promoted'))
            business = sum(1 for l in data if l.get('classification') == 'business')
            personal = sum(1 for l in data if l.get('classification') == 'personal')
            files.append({
                'filename': f.name,
                'path': str(f),
                'total': total,
                'classified': classified,
                'promoted': promoted,
                'business': business,
                'personal': personal,
                'unknown': total - classified,
            })
        except Exception:
            files.append({'filename': f.name, 'path': str(f), 'total': 0, 'error': True})
    return files


# ─── Expected accounts ──────────────────────────────────────────────

def _expected_accounts_file() -> Path:
    return get_output_dir() / '_expected_accounts.json'


def get_expected_accounts() -> dict:
    f = _expected_accounts_file()
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}


def save_expected_accounts(accounts: dict):
    _expected_accounts_file().write_text(json.dumps(accounts, indent=2))


def check_missing(banks_found: dict[str, int]):
    expected = get_expected_accounts()
    if not expected:
        return []
    missing = []
    for source_label, display_name in expected.items():
        if display_name not in banks_found and source_label not in banks_found:
            missing.append(display_name)
            print(f"  ⚠ MISSING: {display_name} ({source_label})", file=sys.stderr)
    return missing


def learn_accounts(banks_found: dict[str, int]):
    expected = get_expected_accounts()
    changed = False
    for bank_name in banks_found:
        source_key = bank_name.lower().replace(' ', '_')
        if source_key not in expected:
            expected[source_key] = bank_name
            changed = True
            print(f"  📝 Alice learned new account: {bank_name}", file=sys.stderr)
    if changed:
        save_expected_accounts(expected)


# ─── Promote business lines to Payment records ──────────────────────

def promote_to_payments(json_filepath: str) -> dict:
    """Promote business+post lines from JSON to psql Payment records.

    Only lines where classification=business, ledger=post, promoted=False
    get created as Payment records. UUID prevents duplicates.
    """
    wc3_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(wc3_root))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')

    import django
    django.setup()

    from decimal import Decimal
    from apps.transactions.models.payment import Payment

    lines = load_json(json_filepath)
    created = 0
    skipped = 0
    already = 0

    for line in lines:
        if line.get('classification') != 'business':
            continue
        if line.get('ledger') != 'post':
            continue
        if line.get('promoted'):
            skipped += 1
            continue

        line_uuid = line.get('uuid', '')
        if not line_uuid:
            continue

        # Check if already promoted (idempotent)
        if Payment.objects.filter(refs__source__statement_uuid=line_uuid).exists():
            line['promoted'] = True
            already += 1
            continue

        amount = Decimal(str(line.get('amount', 0)))
        payment = Payment.objects.create(
            type='expense' if amount < 0 else 'received',
            amount=amount,
            category=line.get('category', ''),
            method=line.get('source', ''),
            notes=line.get('description', ''),
            status='completed',
            refs={
                'source': {
                    'type': 'statement',
                    'statement_uuid': line_uuid,
                    'file': Path(json_filepath).name,
                },
            },
        )
        line['promoted'] = True
        line['payment_id'] = payment.id
        created += 1

    # Write changes back to JSON
    save_json_changes(json_filepath, lines)

    return {'created': created, 'skipped': skipped, 'already_promoted': already}


# ─── Main ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='StatementHarvester — drop statements into a folder, we eat them → JSON',
    )
    parser.add_argument('path', help='CSV file or folder of CSVs')
    parser.add_argument('--source', default='', help='Override source label (auto-detected if omitted)')
    parser.add_argument('--out', default='', help='Output directory for JSON files (default: ~/Allie/statements/)')
    parser.add_argument('--preview', action='store_true', help='Print parsed JSON to stdout instead of saving')
    parser.add_argument('--check', action='store_true', help='Check for missing expected statements')
    parser.add_argument('--promote', action='store_true', help='Promote business lines from JSON to Payment records')
    args = parser.parse_args()

    # Promote mode — process a JSON file
    if args.promote:
        json_path = args.path
        if not Path(json_path).exists():
            print(f"File not found: {json_path}", file=sys.stderr)
            sys.exit(1)
        result = promote_to_payments(json_path)
        print(f"Promoted {result['created']} lines to Payment records "
              f"(skipped {result['skipped']}, already promoted {result['already_promoted']})")
        return

    p = Path(args.path)
    output_dir = Path(args.out) if args.out else get_output_dir()

    if p.is_dir():
        print(f"Harvesting folder: {p}", file=sys.stderr)
        lines, banks_found = harvest_folder(str(p), args.source)
        missing = check_missing(banks_found)
        learn_accounts(banks_found)

        if args.check:
            if not banks_found:
                print("No statements found in folder.", file=sys.stderr)
            else:
                print(f"\nFound {len(lines)} lines from {len(banks_found)} accounts:", file=sys.stderr)
                for bank, count in sorted(banks_found.items()):
                    print(f"  {bank}: {count} lines", file=sys.stderr)
            return

        if args.preview:
            print(json.dumps(lines, indent=2))
            print(f"\n# {len(lines)} lines from {len(banks_found)} accounts", file=sys.stderr)
            return

        # Save to JSON files — one per source
        by_source: dict[str, list] = {}
        for line in lines:
            by_source.setdefault(line['source'], []).append(line)

        total_new = 0
        total_dup = 0
        for source, source_lines in sorted(by_source.items()):
            filepath, new, dup = save_json(source_lines, source, output_dir)
            total_new += new
            total_dup += dup
            print(f"  {filepath.name}: {new} new, {dup} duplicates", file=sys.stderr)

        print(f"\nSaved {total_new} new lines ({total_dup} duplicates) to {output_dir}", file=sys.stderr)
        if missing:
            print(f"⚠ Missing accounts: {', '.join(missing)}", file=sys.stderr)

    elif p.is_file():
        lines, source, bank_name = harvest_file(str(p), args.source)
        if not lines:
            print("No lines parsed.", file=sys.stderr)
            sys.exit(1)

        if args.preview:
            print(json.dumps(lines, indent=2))
            return

        filepath, new, dup = save_json(lines, source, output_dir)
        print(f"Saved {new} new lines ({dup} duplicates) to {filepath}", file=sys.stderr)

    else:
        print(f"Error: {args.path} not found", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

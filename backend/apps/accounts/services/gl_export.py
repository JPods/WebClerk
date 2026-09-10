"""
GL Export — accounting program format adapters.

Each adapter takes the canonical bundle.json (from build_gl_journal_bundle)
and converts it to a format importable by a specific accounting program.

Report records on gl_journal reference these by name:
    "GL Export — Generic CSV"      → generic_csv
    "GL Export — Generic JSON"     → generic_json
    "GL Export — QuickBooks IIF"   → quickbooks_iif
    "GL Export — Xero CSV"         → xero_csv
    "GL Export — Sage CSV"         → sage_csv

Usage:
    from apps.accounts.services.gl_export import gl_export
    content, filename, content_type = gl_export('2026-08', 'generic_csv')
"""
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Map report names to adapter keys
REPORT_NAME_MAP = {
    'GL Export — Generic CSV': 'generic_csv',
    'GL Export — Generic JSON': 'generic_json',
    'GL Export — QuickBooks IIF': 'quickbooks_iif',
    'GL Export — Xero CSV': 'xero_csv',
    'GL Export — Sage CSV': 'sage_csv',
}


def gl_export(period: str, adapter: str, division: str = '') -> tuple:
    """Export GL journals for a period in the specified format.

    Args:
        period: 'YYYY-MM' (e.g. '2026-08')
        adapter: one of generic_csv, generic_json, quickbooks_iif, xero_csv, sage_csv
        division: optional division filter

    Returns:
        (content: str, filename: str, content_type: str)
    """
    from apps.sync.services.gl_journal_bundle import build_gl_journal_bundle

    bundle = build_gl_journal_bundle(period)

    if division:
        bundle['entries'] = [e for e in bundle['entries'] if e.get('division') == division]
        _recalc_totals(bundle)

    adapters = {
        'generic_csv': _generic_csv,
        'generic_json': _generic_json,
        'quickbooks_iif': _quickbooks_iif,
        'xero_csv': _xero_csv,
        'sage_csv': _sage_csv,
    }

    fn = adapters.get(adapter)
    if not fn:
        raise ValueError(f"Unknown GL export adapter: {adapter}")

    return fn(bundle, period)


def _recalc_totals(bundle: dict):
    """Recalculate totals after filtering entries."""
    total_debits = sum(e.get('debit', 0) for e in bundle['entries'])
    total_credits = sum(e.get('credit', 0) for e in bundle['entries'])
    bundle['totals'] = {
        'entry_count': len(bundle['entries']),
        'total_debits': round(total_debits, 2),
        'total_credits': round(total_credits, 2),
        'balanced': abs(total_debits - total_credits) < 0.01,
    }


def _epoch_to_date(epoch_ms) -> str:
    """Convert epoch ms to YYYY-MM-DD."""
    if not epoch_ms:
        return ''
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d')
    except (ValueError, OSError):
        return ''


def _epoch_to_mmddyyyy(epoch_ms) -> str:
    """Convert epoch ms to MM/DD/YYYY (QuickBooks format)."""
    if not epoch_ms:
        return ''
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime('%m/%d/%Y')
    except (ValueError, OSError):
        return ''


# ---------------------------------------------------------------------------
# Generic CSV — importable by most programs
# ---------------------------------------------------------------------------

def _generic_csv(bundle: dict, period: str) -> tuple:
    """Standard CSV with all fields. Most accounting programs can import this.

    Columns: Date,Account,Debit,Credit,Description,Reference,Division,Source
    """
    company = bundle.get('source', {}).get('name', 'WebClerk')
    lines = ['Date,Account,Debit,Credit,Description,Reference,Division,Source']

    for e in bundle['entries']:
        date = _epoch_to_date(e.get('dt_created'))
        account = e.get('account', '')
        debit = f"{e.get('debit', 0):.2f}" if e.get('debit') else ''
        credit = f"{e.get('credit', 0):.2f}" if e.get('credit') else ''
        note = str(e.get('note', '')).replace(',', ';').replace('"', "'")
        ref = e.get('batch_id', '')
        division = e.get('division', '')
        source = f"{e.get('source_model', '')}:{e.get('source_id', '')}"
        lines.append(f'{date},{account},{debit},{credit},"{note}",{ref},{division},{source}')

    # Append control totals as comment
    t = bundle['totals']
    lines.append('')
    lines.append(f'# Control Totals — {company} — Period {period}')
    lines.append(f'# Entries: {t["entry_count"]}')
    lines.append(f'# Total Debits: {t["total_debits"]:.2f}')
    lines.append(f'# Total Credits: {t["total_credits"]:.2f}')
    lines.append(f'# Balanced: {t["balanced"]}')

    content = '\n'.join(lines)
    filename = f'{period}_gl_journal.csv'
    return content, filename, 'text/csv'


# ---------------------------------------------------------------------------
# Generic JSON — canonical bundle format
# ---------------------------------------------------------------------------

def _generic_json(bundle: dict, period: str) -> tuple:
    """Canonical JSON bundle with control totals. This is the master format."""
    content = json.dumps(bundle, indent=2, default=str)
    filename = f'{period}_gl_journal.json'
    return content, filename, 'application/json'


# ---------------------------------------------------------------------------
# QuickBooks Desktop IIF
# ---------------------------------------------------------------------------

def _quickbooks_iif(bundle: dict, period: str) -> tuple:
    """QuickBooks Desktop IIF (Intuit Interchange Format).

    IIF groups entries into TRNS/SPL/ENDTRNS blocks. Each block must
    balance internally. We group by batch_id (one batch = one balanced
    transaction).
    """
    lines = [
        '!TRNS\tTRNSTYPE\tDATE\tACCNT\tAMOUNT\tMEMO\tNAME',
        '!SPL\tTRNSTYPE\tDATE\tACCNT\tAMOUNT\tMEMO\tNAME',
        '!ENDTRNS',
    ]

    # Group entries by batch_id
    batches = {}
    for e in bundle['entries']:
        batch = e.get('batch_id', 'UNBATCHED')
        batches.setdefault(batch, []).append(e)

    for batch_id, entries in batches.items():
        if not entries:
            continue
        first = True
        for e in entries:
            date = _epoch_to_mmddyyyy(e.get('dt_created'))
            account = e.get('account', '')
            amt = (e.get('debit', 0) or 0) - (e.get('credit', 0) or 0)
            note = str(e.get('note', '')).replace('\t', ' ')
            tag = 'TRNS' if first else 'SPL'
            lines.append(f'{tag}\tGENERAL JOURNAL\t{date}\t{account}\t{amt:.2f}\t{note}\t')
            first = False
        lines.append('ENDTRNS')

    content = '\n'.join(lines)
    filename = f'{period}_gl_journal.iif'
    return content, filename, 'text/plain'


# ---------------------------------------------------------------------------
# Xero CSV — Manual Journal Import
# ---------------------------------------------------------------------------

def _xero_csv(bundle: dict, period: str) -> tuple:
    """Xero manual journal import CSV format.

    Xero requires: *JournalNumber,*Date,*AccountCode,*Description,
    *TaxRate,Debit,Credit,TrackingName1,TrackingOption1

    Journals with the same JournalNumber are grouped as one entry.
    """
    lines = ['*JournalNumber,*Date,*AccountCode,*Description,*TaxRate,Debit,Credit,TrackingName1,TrackingOption1']

    # Group by batch_id → one Xero journal per batch
    batches = {}
    for e in bundle['entries']:
        batch = e.get('batch_id', 'UNBATCHED')
        batches.setdefault(batch, []).append(e)

    journal_num = 0
    for batch_id, entries in batches.items():
        journal_num += 1
        for e in entries:
            date = _epoch_to_date(e.get('dt_created'))
            account = e.get('account', '')
            note = str(e.get('note', '')).replace(',', ';').replace('"', "'")
            debit = f"{e.get('debit', 0):.2f}" if e.get('debit') else ''
            credit = f"{e.get('credit', 0):.2f}" if e.get('credit') else ''
            division = e.get('division', '')
            tracking_name = 'Division' if division else ''
            lines.append(f'{journal_num},{date},{account},"{note}",No Tax,{debit},{credit},{tracking_name},{division}')

    content = '\n'.join(lines)
    filename = f'{period}_gl_journal_xero.csv'
    return content, filename, 'text/csv'


# ---------------------------------------------------------------------------
# Sage 50 CSV — General Journal Import
# ---------------------------------------------------------------------------

def _sage_csv(bundle: dict, period: str) -> tuple:
    """Sage 50 (Peachtree) general journal CSV import format.

    Sage requires: Date,Reference,GL Account,Description,Debit,Credit
    """
    lines = ['Date,Reference,GL Account,Description,Debit,Credit']

    for e in bundle['entries']:
        date = _epoch_to_mmddyyyy(e.get('dt_created'))
        ref = e.get('batch_id', '')
        account = e.get('account', '')
        note = str(e.get('note', '')).replace(',', ';').replace('"', "'")
        debit = f"{e.get('debit', 0):.2f}" if e.get('debit') else ''
        credit = f"{e.get('credit', 0):.2f}" if e.get('credit') else ''
        lines.append(f'{date},{ref},{account},"{note}",{debit},{credit}')

    content = '\n'.join(lines)
    filename = f'{period}_gl_journal_sage.csv'
    return content, filename, 'text/csv'

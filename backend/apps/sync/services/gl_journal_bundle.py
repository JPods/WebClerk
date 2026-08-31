"""
GL Journal Bundle — canonical format for all accounting handoffs.

WC3 produces the canonical bundle.json. Two destinations:
    1. Local file — downloaded by user, fed to the Journal Formatter tool
    2. Upstream HQ — Bundle record for multi-location consolidation

The Journal Formatter is a separate external-facing tool (like Statement
Sorter) that consumes bundle.json and produces output formatted for the
target accounting program (QuickBooks, Xero, Sage, etc.). WC3 does not
carry accounting program format specs — that's the formatter's job.

    Statement Sorter:   Bank CSV    → WC3 JSON     (inbound)
    Journal Formatter:  WC3 JSON    → Accounting    (outbound)

From the accountant's point of view, a standalone business and a
multi-location company produce identical bundle.json. Every entry
carries a source UUID from Setting(purpose='wc:company_profile').

Flow:
    GL Journals → build_gl_journal_bundle() → bundle.json
                                                  │
                                   ┌──────────────┼──────────────┐
                                   ↓                              ↓
                         Journal Formatter            send_upstream()
                         (external tool —             (Bundle record
                          QB / Xero / Sage)            at HQ)

Usage:
    from apps.sync.services.gl_journal_bundle import (
        build_gl_journal_bundle,
        send_gl_journal_bundle,
    )

    bundle = build_gl_journal_bundle(period='2026-08')
    # Save as bundle.json for Journal Formatter or user download
    # OR send upstream for multi-location consolidation:
    send_gl_journal_bundle(connection, bundle)
"""
import logging
import time

logger = logging.getLogger(__name__)


def _get_company_source() -> dict:
    """Get the company source identifier from Setting(purpose='wc:company_profile').

    Returns {"uuid": str, "name": str, "ida": str} — the identity stamp
    on every journal entry. The accountant uses this to know which company
    produced the entry, whether standalone or multi-location.
    """
    try:
        from apps.core.models import Setting
        company = Setting.objects.filter(
            purpose='wc:company_profile', is_active=True,
        ).first()
        if company:
            config = company.config if isinstance(company.config, dict) else {}
            return {
                'uuid': str(company.uuid),
                'name': config.get('company', {}).get('name', ''),
                'ida': company.ida or '',
            }
    except Exception:
        pass
    return {'uuid': '', 'name': '', 'ida': ''}


def build_gl_journal_bundle(period: str) -> dict:
    """Build a GL journal bundle from this installation's posted journals.

    The bundle is the canonical format — same structure whether it's
    downloaded for the Journal Formatter or sent upstream to HQ.
    Every entry carries the company source UUID.

    Args:
        period: Accounting period, e.g. '2026-08'

    Returns a dict — save as bundle.json or pass to send_gl_journal_bundle().
    """
    import datetime
    from django.apps import apps as dj_apps

    GlJournal = dj_apps.get_model('accounts', 'GlJournal')
    source = _get_company_source()

    year, month = [int(x) for x in period.split('-')]
    start = datetime.datetime(year, month, 1, tzinfo=datetime.timezone.utc)
    if month == 12:
        end = datetime.datetime(year + 1, 1, 1, tzinfo=datetime.timezone.utc)
    else:
        end = datetime.datetime(year, month + 1, 1, tzinfo=datetime.timezone.utc)

    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)

    journals = GlJournal.objects.filter(
        dt_created__gte=start_ms,
        dt_created__lt=end_ms,
        is_active=True,
    ).order_by('dt_created').values(
        'id', 'ida', 'account', 'debit', 'credit', 'type',
        'source_model', 'source_id', 'division', 'batch_id',
        'note', 'dt_created',
    )

    entries = []
    total_debits = 0.0
    total_credits = 0.0

    for j in journals:
        debit = float(j['debit'] or 0)
        credit = float(j['credit'] or 0)
        total_debits += debit
        total_credits += credit

        entries.append({
            'id': j['id'],
            'ida': j['ida'] or '',
            'account': j['account'] or '',
            'debit': debit,
            'credit': credit,
            'type': j['type'] or '',
            'source_model': j['source_model'] or '',
            'source_id': j['source_id'],
            'division': j['division'] or '',
            'batch_id': j['batch_id'],
            'note': j['note'] or '',
            'dt_created': j['dt_created'],
        })

    return {
        'type': 'gl_journal',
        'version': '1.0',
        'source': source,
        'period': period,
        'dt_built': int(time.time() * 1000),
        'entries': entries,
        'totals': {
            'entry_count': len(entries),
            'total_debits': round(total_debits, 2),
            'total_credits': round(total_credits, 2),
            'balanced': abs(total_debits - total_credits) < 0.01,
        },
    }


def send_gl_journal_bundle(connection, bundle_data: dict) -> dict:
    """Send a GL journal bundle to an upstream WC3 instance.

    The upstream does NOT load journals into its GL — it stores them
    as a Bundle for the Journal Formatter to consume. The accountant
    at HQ sees entries from each location tagged by company UUID.

    Args:
        connection: The Connection record for the upstream WC3
        bundle_data: The canonical bundle from build_gl_journal_bundle()

    Returns the upstream server's response.
    """
    import httpx
    import uuid

    config = connection.config if isinstance(connection.config, dict) else {}
    endpoint = config.get('endpoint', '')
    key = config.get('key', '')

    if not endpoint or not key:
        raise ValueError(
            f"Connection {connection.ida} missing endpoint or key in config"
        )

    url = endpoint.rstrip('/') + '/wcapi/sync/receive/'

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                url,
                headers={'X-Sync-Key': key},
                json={
                    'idempotency_key': str(uuid.uuid4()),
                    'sequence': int(time.time()),
                    'payload': bundle_data,
                },
            )
            resp.raise_for_status()
            return resp.json()

    except httpx.ConnectError:
        raise ConnectionError(f"Cannot reach upstream at {endpoint}")
    except Exception as e:
        logger.exception("GL journal bundle send failed")
        raise ConnectionError(f"Bundle send error: {e}")

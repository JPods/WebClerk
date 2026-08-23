"""
pack_demo_bundle — Export Settings + demo data as a single baseline bundle.

Usage:
    python manage.py pack_demo_bundle                        # write demo-bundle.json
    python manage.py pack_demo_bundle --output /tmp/db.json  # custom path
    python manage.py pack_demo_bundle --dry-run              # show counts only

Creates a portable JSON file containing:
  1. All active Setting records (system foundation)
  2. Demo contacts, orgs, items, BOM, transactions, payments, GL entries

The bundle is designed for:
  - demo.webclerk.com (public read-only training)
  - Local download (user loads demo data, trains, then removes it)
  - New installation bootstrap (Settings + sample data)

All non-Setting records are tagged refs.source="demo-baseline" on load,
enabling clean removal via remove_demo_data.
"""
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.core.models.setting import Setting


# Models to export — order matters for import (dependencies first)
DEMO_MODELS = [
    ('contact', 'apps.core.models.contact', 'Contact'),
    ('org', 'apps.orgs.models', 'OrgBase'),
    ('item', 'apps.products.models', 'Item'),
    ('bill_of_material', 'apps.products.models.bill_of_material', 'BillOfMaterial'),
    ('proposal', 'apps.transactions.models', 'Proposal'),
    ('proposal_line', 'apps.transactions.models', 'ProposalLine'),
    ('order', 'apps.transactions.models', 'Order'),
    ('order_line', 'apps.transactions.models', 'OrderLine'),
    ('invoice', 'apps.transactions.models', 'Invoice'),
    ('invoice_line', 'apps.transactions.models', 'InvoiceLine'),
    ('payment', 'apps.transactions.models', 'Payment'),
    ('gl_journal', 'apps.accounts.models', 'GlJournal'),
]

# Fields to skip during serialization (not portable).
# Note: id IS included — load_demo_data needs the old PK to remap FK references.
SKIP_FIELDS = {'_state', '_pydantic_cache'}

# JSON-serializable field types that need special handling
JSON_FIELDS = {'config', 'metadata', 'refs', 'prefs', 'comments', 'price', 'cost',
               'gls', 'totals', 'item', 'quantity', 'sell', 'source', 'terms_json',
               'op_data', 'health_rating', 'paths', 'cost_snapshot', 'actions'}


def _serialize_value(val):
    """Convert a value to JSON-safe form."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, bytes):
        return None  # skip binary
    return val


def _serialize_record(obj):
    """Serialize a Django model instance to a dict, keyed by field name."""
    data = {}
    for field in obj._meta.get_fields():
        if not hasattr(field, 'attname'):
            continue
        name = field.attname
        if name in SKIP_FIELDS:
            continue
        val = getattr(obj, name, None)
        data[name] = _serialize_value(val)
    return data


class Command(BaseCommand):
    help = 'Export Settings + demo data as a portable baseline bundle'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output', type=str, default='demo-bundle.json',
            help='Output file path (default: demo-bundle.json)',
        )
        parser.add_argument('--dry-run', action='store_true',
                            help='Show counts without writing')
        parser.add_argument('--demo-source', type=str, default='demo-baseline',
                            help='Value of refs.source to filter demo records (default: demo-baseline)')

    def handle(self, *args, **options):
        demo_source = options['demo_source']
        bundle = {
            'version': '1.0',
            'source': 'pack_demo_bundle',
            'dt_exported': datetime.now(timezone.utc).isoformat(),
            'demo_source_tag': demo_source,
            'settings': [],
            'data': {},
        }

        # ── Settings ───────────────────────────────────────────────────
        for s in Setting.objects.filter(is_active=True).order_by('purpose', 'parent_model'):
            if not s.uuid:
                continue
            bundle['settings'].append({
                'uuid': str(s.uuid),
                'ida': s.ida or '',
                'name': s.name or '',
                'scope': s.scope or 'system',
                'purpose': s.purpose or '',
                'parent_model': s.parent_model or '',
                'explanation': getattr(s, 'explanation', '') or '',
                'paths': getattr(s, 'paths', {}) or {},
                'config': s.config or {},
                'metadata': s.metadata or {},
                'prefs': s.prefs or {},
                'refs': s.refs or {},
            })

        self.stdout.write(f"Settings: {len(bundle['settings'])} records")

        # ── Demo data ──────────────────────────────────────────────────
        from importlib import import_module

        total_data = 0
        for key, module_path, class_name in DEMO_MODELS:
            mod = import_module(module_path)
            Model = getattr(mod, class_name)

            # Find demo records by refs.source tag
            qs = Model.objects.filter(refs__source=demo_source)
            records = [_serialize_record(obj) for obj in qs]
            bundle['data'][key] = records
            total_data += len(records)
            self.stdout.write(f"  {key}: {len(records)} records")

        self.stdout.write(f"\nTotal: {len(bundle['settings'])} settings + {total_data} data records")

        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS('\n(dry run — nothing written)'))
            return

        output_path = Path(options['output'])
        with open(output_path, 'w') as f:
            json.dump(bundle, f, indent=2, ensure_ascii=False, default=str)

        size_kb = output_path.stat().st_size / 1024
        self.stdout.write(self.style.SUCCESS(
            f"\nWritten to {output_path} ({size_kb:.0f} KB)"
        ))

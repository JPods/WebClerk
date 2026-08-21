"""
Generate alice_guess2 layouts for all workbench_fields Settings.

Applies learned principles from Bill's contact layout:
1. Assembled fields > parts (attention > name parts, address_full > street/city)
2. Who/how/where first, identity second, system last
3. Narrow widths — more columns visible at a glance
4. Context fields (purpose, status, title) early
5. Admin flags (is_superuser, security_level) are noise in lists
6. JSON blobs (metadata, refs, prefs) go to bottom of detail

Usage:
  ./manage.py seed_alice_guess2          # dry run
  ./manage.py seed_alice_guess2 --apply  # write to database
"""
from django.core.management.base import BaseCommand
from apps.core.models import Setting
import copy


# Smart width by field name — same logic as React getDefaultFieldSpec
def width_for(field):
    fl = field.lower()
    if fl in ('display_name', 'company', 'name'): return 150
    if fl in ('ida', 'sku'): return 90
    if fl == 'id': return 50
    if 'phone' in fl: return 120
    if 'email' in fl: return 180
    if fl in ('address_full',): return 160
    if fl in ('description', 'title'): return 160
    if fl in ('notes', 'comments', 'comment'): return 160
    if fl in ('terms', 'price_level'): return 70
    if fl in ('total', 'balance', 'amount', 'debit', 'credit', 'price', 'cost', 'value_original', 'value_available'): return 90
    if fl in ('status', 'type', 'category', 'kind', 'org_type', 'kanban_column'): return 80
    if fl in ('qty', 'quantity', 'line_number', 'sequence', 'priority', 'difficulty'): return 50
    if fl.startswith('dt_') or 'date' in fl: return 90
    if fl.startswith('is_'): return 45
    if fl in ('uuid',): return 90
    if fl in ('metadata', 'refs', 'prefs', 'actions', 'config'): return 50
    if fl in ('attention',): return 120
    if fl in ('assigned_to', 'project_name'): return 120
    if fl in ('purpose', 'role', 'source', 'model_name', 'parent_model'): return 90
    if fl in ('percent_complete', 'burndown', 'health_rating'): return 60
    if fl in ('name',): return 140
    if fl in ('action',): return 160
    return 100


def align_for(field):
    fl = field.lower()
    if fl in ('total', 'balance', 'amount', 'debit', 'credit', 'price', 'cost', 'id',
              'qty', 'quantity', 'line_number', 'sequence', 'priority', 'difficulty',
              'version', 'security_level', 'health_rating', 'percent_complete', 'burndown',
              'value_original', 'value_available', 'discount_potential'):
        return 'right'
    if fl.startswith('dt_') or fl.startswith('is_') or 'date' in fl:
        return 'center'
    return 'left'


def format_for(field):
    fl = field.lower()
    if 'phone' in fl: return 'phone'
    if fl in ('total', 'balance', 'amount', 'debit', 'credit', 'price', 'cost',
              'value_original', 'value_available', 'discount_potential'):
        return 'currency'
    if fl.startswith('dt_') or 'date' in fl: return 'date'
    if fl in ('metadata', 'refs', 'prefs', 'actions', 'config'): return 'json'
    return None


def make_spec(field, visible=True):
    spec = {'field': field, 'width': width_for(field), 'align': align_for(field), 'visible': visible}
    fmt = format_for(field)
    if fmt:
        spec['format'] = fmt
    return spec


# System fields — always at bottom of detail, never in list
SYSTEM_FIELDS = {
    'uuid', 'version', 'security_level', 'is_deleted', 'is_archived', 'is_locked',
    'health_rating', 'metadata', 'refs', 'prefs', 'actions', 'config', 'comments',
    'search_vector', 'password', 'user_permissions', 'groups',
}

# Fields to exclude from lists
LIST_EXCLUDE = SYSTEM_FIELDS | {
    'search_vector', 'password', 'user_permissions', 'groups',
    'is_superuser', 'is_staff', 'name_prefix', 'name_suffix', 'name_middle',
    'is_deleted', 'is_archived', 'is_locked',
}

# Per-model list field priorities (ordered)
LIST_PRIORITIES = {
    # Transactions
    'order':    ['ida', 'status', 'attention', 'total', 'email', 'phone', 'terms', 'address_full', 'priority', 'dt_created'],
    'invoice':  ['ida', 'status', 'attention', 'total', 'balance', 'email', 'phone', 'terms', 'address_full', 'dt_created'],
    'purchase': ['ida', 'status', 'attention', 'total', 'email', 'terms', 'address_full', 'dt_created'],
    'proposal': ['ida', 'status', 'attention', 'total', 'email', 'phone', 'terms', 'address_full', 'dt_created'],
    'work_order': ['ida', 'status', 'total', 'priority', 'dt_created', 'dt_modified'],
    'receipt':  ['ida', 'status', 'dt_created', 'dt_modified'],
    'requisition': ['ida', 'status', 'dt_created', 'dt_modified'],

    # Transaction lines
    'order_line':    ['ida', 'description', 'qty', 'price', 'total', 'status'],
    'invoice_line':  ['ida', 'description', 'qty', 'price', 'total', 'status'],
    'purchase_line': ['ida', 'description', 'qty', 'price', 'total'],
    'proposal_line': ['ida', 'description', 'qty', 'price', 'total'],
    'work_order_line': ['ida', 'description', 'qty', 'price', 'total'],
    'receipt_line':  ['ida', 'description', 'qty', 'dt_created'],
    'requisition_line': ['ida', 'description', 'qty', 'dt_created'],

    # Orgs
    'customer':     ['ida', 'display_name', 'status', 'email', 'phone', 'address_full', 'price_level', 'terms'],
    'vendor':       ['ida', 'display_name', 'status', 'email', 'phone', 'address_full', 'price_level', 'terms'],
    'manufacturer': ['ida', 'display_name', 'status', 'email', 'phone', 'address_full'],
    'employee':     ['ida', 'display_name', 'status', 'email', 'phone', 'address_full'],
    'rep':          ['ida', 'display_name', 'status', 'email', 'phone', 'address_full'],

    # Products
    'item':         ['ida', 'name', 'sku', 'kind', 'price', 'cost', 'uom', 'is_active'],
    'bill_of_material': ['ida', 'name', 'description', 'qty', 'uom', 'is_active'],
    'variant':      ['ida', 'name', 'sku', 'price'],
    'serial':       ['ida', 'item', 'status', 'dt_created'],
    'catalog':      ['ida', 'name', 'status', 'dt_created'],
    'org_item':     ['ida', 'item', 'org', 'price', 'is_active'],

    # Accounting
    'gl_account':   ['ida', 'name', 'type', 'category', 'is_active'],
    'gl_journal':   ['ida', 'source', 'debit', 'credit', 'model_name', 'dt_journaled', 'is_active'],
    'ledger':       ['ida', 'value_original', 'value_available', 'source', 'model_name', 'dt_due', 'dt_applied'],
    'payment':      ['ida', 'type', 'total', 'status', 'contact', 'dt_created'],
    'payment_application': ['ida', 'amount', 'invoice', 'payment', 'dt_created'],
    'payment_method': ['ida', 'name', 'type', 'is_active'],
    'payment_term': ['ida', 'name', 'description', 'is_active'],

    # Communications
    'email':    ['ida', 'attention', 'email', 'type', 'is_active'],
    'phone':    ['ida', 'attention', 'phone', 'type', 'is_active'],
    'address':  ['ida', 'attention', 'address_full', 'type', 'is_active'],
    'domain':   ['ida', 'name', 'type', 'status', 'is_active'],

    # System / admin
    'action':   ['ida', 'action', 'status', 'kanban_column', 'assigned_to', 'priority', 'project_name', 'dt_deadline', 'percent_complete'],
    'document': ['ida', 'name', 'category', 'model_name', 'dt_created'],
    'project':  ['ida', 'name', 'status', 'priority', 'dt_created'],
    'report':   ['ida', 'name', 'category', 'output_type', 'model_name', 'purpose'],
    'setting':  ['ida', 'name', 'purpose', 'parent_model', 'is_active'],
    'question_answer': ['ida', 'question', 'category', 'model_name', 'is_active'],
    'tag':      ['ida', 'name', 'type', 'model_name', 'is_active'],
    'notification': ['ida', 'title', 'status', 'type', 'dt_created'],
    'audit':    ['ida', 'model_name', 'action', 'contact', 'dt_created'],

    # Sync / integration
    'connection':   ['ida', 'name', 'type', 'status', 'is_active'],
    'sync_bundle':  ['ida', 'name', 'status', 'model_name', 'dt_created'],

    # Inventory
    'inventory_check': ['ida', 'status', 'dt_created'],
    'inventory_check_line': ['ida', 'item', 'qty', 'dt_created'],
    'inventory_reservation': ['ida', 'item', 'qty', 'status'],
    'inventory_adjustment_run': ['ida', 'status', 'dt_created'],
    'inventory_metrics_snapshot': ['ida', 'item', 'dt_created'],
    'pending_inventory_adjustment': ['ida', 'item', 'qty', 'status'],
    'pending_payment_application': ['ida', 'amount', 'status', 'dt_created'],

    # Delivery
    'delivery_visit': ['ida', 'status', 'dt_created'],
    'delivery_line': ['ida', 'item', 'qty', 'status'],

    # Other
    'currency':  ['ida', 'name', 'code', 'is_active'],
    'service':   ['ida', 'name', 'type', 'status', 'is_active'],
    'tax_jurisdiction': ['ida', 'name', 'type', 'rate', 'is_active'],
    'term':      ['ida', 'name', 'type', 'is_active'],
    'warehouse': ['ida', 'name', 'status', 'address_full', 'is_active'],
    'item_xref': ['ida', 'item', 'source', 'dt_created'],
    'item_usage': ['ida', 'item', 'qty', 'dt_created'],
    'serial_log': ['ida', 'serial', 'action', 'dt_created'],
    'statement_line': ['ida', 'description', 'amount', 'dt_created'],
}

# Related panels per model
RELATED_PANELS = {
    'contact':  ['email', 'phone', 'address', 'domain'],
    'customer': ['order', 'invoice', 'contact'],
    'vendor':   ['purchase', 'contact'],
    'order':    ['order_line'],
    'invoice':  ['invoice_line', 'payment'],
    'purchase': ['purchase_line'],
    'proposal': ['proposal_line'],
    'item':     ['serial', 'item_xref', 'org_item', 'bill_of_material'],
    'project':  ['action'],
    'action':   ['document', 'question_answer'],
}


class Command(BaseCommand):
    help = 'Generate alice_guess2 layouts for all workbench_fields Settings'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        apply = options['apply']
        qs = Setting.objects.filter(purpose='wc:workbench_fields')
        total = qs.count()
        updated = 0
        skipped = 0

        for s in qs:
            cfg = copy.deepcopy(s.config or {})
            db = cfg.get('db', {})
            model = s.parent_model

            # Skip contact (already done by Bill)
            if model == 'contact':
                skipped += 1
                continue

            # Get available fields from current detail
            available = set()
            for f in db.get('detail', []):
                name = f['field'] if isinstance(f, dict) else f
                available.add(name)
            # Also add from list
            for f in db.get('list', []):
                name = f['field'] if isinstance(f, dict) else f
                available.add(name)

            if not available:
                skipped += 1
                continue

            # Build list: use priority order, filter to available fields
            priority = LIST_PRIORITIES.get(model, [])
            list_fields = [f for f in priority if f in available]
            # If no priority defined, use first 6 non-system fields from detail
            if not list_fields:
                list_fields = [f for f in [ff['field'] if isinstance(ff, dict) else ff for ff in db.get('detail', [])]
                               if f not in LIST_EXCLUDE][:6]

            guess2_list = [make_spec(f) for f in list_fields]

            # Build detail: operational first, then remaining, system last
            operational = [f for f in list_fields if f in available]
            system_at_bottom = [f for f in available if f in SYSTEM_FIELDS]
            middle = [f for f in available if f not in set(operational) and f not in SYSTEM_FIELDS]
            # Sort middle alphabetically for consistency
            middle.sort()
            detail_order = []
            seen = set()
            for f in operational + middle + system_at_bottom:
                if f not in seen:
                    detail_order.append(f)
                    seen.add(f)

            guess2_detail = [make_spec(f) for f in detail_order]

            # Build related
            related = RELATED_PANELS.get(model, [])

            # Build view
            view = {
                'name': 'alice_guess2',
                'list': guess2_list,
                'detail': guess2_detail,
                'panel': [],
                'card': [],
            }

            # Add/replace in views
            views = [v for v in db.get('views', []) if v.get('name') != 'alice_guess2']
            views.append(view)
            db['views'] = views

            # Set related if defined
            if related and not db.get('related'):
                db['related'] = related

            self.stdout.write(f'  {model:30s} list={len(guess2_list):>2} detail={len(guess2_detail):>2} related={related or "[]"}')

            if apply:
                cfg['db'] = db
                s.config = cfg
                s.save(update_fields=['config'])
                updated += 1
            else:
                updated += 1

        mode = 'APPLIED' if apply else 'DRY RUN'
        self.stdout.write(self.style.SUCCESS(
            f'\n{mode}: {total} total, {updated} updated, {skipped} skipped'
        ))

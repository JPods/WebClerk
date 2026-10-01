"""Bring a database's existing GL onto the GL-by-layer rules, once (Bill, 2026-09-30; plan
~/Allie/readmes/assessments/2026-09-30-gl-by-layer.md, step 7). Every change is a command or a
stamped reversal, never a raw edit of a posted row:

1. Openings: the layers no line made (opening balances) get one opening count workorder
   (config.opening) as their parent, and journalizing it posts Dr inventory / Cr opening equity.
2. Purchases: a PO posts nothing, so each journalized purchase is unjournalized, with the reason.
3. Invoices: each journalized invoice's item-cost COGS and inventory rows are reversed (those rows
   only; revenue, AR and tax stand) and its layer COGS is posted: what its movements took at each
   layer's fixed cost, plus what it took short at the deficit's cost.

    manage.py restate_gl_by_layer            # dry run: what it would do
    manage.py restate_gl_by_layer --apply

Take a backup first; the command does not.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

REASON = 'GL by layer (Bill, 2026-09-30): a PO posts nothing; COGS comes from the layers'


class Command(BaseCommand):
    help = 'Restate the existing GL onto the GL-by-layer rules (openings, purchases, invoice COGS).'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Write; without it, a dry run.')

    def handle(self, *args, **options):
        apply = options['apply']
        with transaction.atomic():
            report = {'openings': self._openings(apply), 'purchases': self._purchases(apply),
                      'orphans': self._orphan_purchase_rows(apply),
                      'invoices': self._invoices(apply), 'adjustments': self._adjustments(apply),
                      'missing movements': self._missing_movements(apply),
                      'workorders': self._workorders(apply)}
            if not apply:
                transaction.set_rollback(True)
        for part, lines in report.items():
            self.stdout.write(self.style.SUCCESS(f'{part}:'))
            for line in lines:
                self.stdout.write(f'  {line}')
        if not apply:
            self.stdout.write(self.style.WARNING('DRY RUN: nothing was written (rerun with --apply).'))

    # ── 1. Openings ────────────────────────────────────────────────────────────────────
    def _openings(self, apply):
        from apps.accounts.services.journalize import journalize_workorder
        from apps.products.models.inventory_layer import InventoryLayer, InventoryMovement
        from apps.transactions.models import WorkOrder
        layers = InventoryLayer.objects.filter(parent_model='')
        if not layers.exists():
            return ['no layer without a parent']
        value = sum((Decimal(str((l.quantity or {}).get('received') or 0)) *
                     Decimal(str((l.cost or {}).get('landed') or 0)) for l in layers), Decimal('0'))
        count = layers.count()
        from apps.core.services.comment_stamp import append_comment
        wo = WorkOrder.objects.create(kind='count', status='complete', config={'opening': True})
        append_comment(wo, 'process', f'Opening balances: {count} layers ({REASON})', source='restate')
        wo.save(update_fields=['comments'])
        ids = list(layers.values_list('pk', flat=True))
        InventoryLayer.objects.filter(pk__in=ids).update(parent_model='workorder', parent_id=wo.pk)
        InventoryMovement.objects.filter(inventory_layer_id__in=ids, parent_model='',
                                         movement_type=InventoryMovement.MOVEMENT_RECEIPT
                                         ).update(parent_model='workorder', parent_id=wo.pk)
        out = journalize_workorder(wo.pk)
        return [f'opening count workorder {wo.pk}: {count} layers, received value {value:.2f}',
                f'journalized: {out}']

    # ── 2. Purchases ───────────────────────────────────────────────────────────────────
    def _purchases(self, apply):
        """Every purchase with GL rows still standing is reversed: by unjournalize when it is marked
        journalized, else by reversal alone (posted rows without the mark), stamped either way."""
        from apps.accounts.models import GlJournal
        from apps.accounts.services.ledger_balance import reverse_gl_entries
        from apps.core.services.comment_stamp import append_comment
        from apps.core.services.door import Actor
        from apps.core.services.verbs import run_command
        from apps.transactions.models import Purchase
        done = []
        ids = set(GlJournal.objects.filter(source_model='purchase').values_list('source_id', flat=True))
        for po in Purchase.objects.filter(pk__in=ids).order_by('pk'):
            if po.dt_journaled:
                out = run_command(Actor.system(), 'unjournalize', 'purchase', po.pk, {'reason': REASON})
                count = out['reversed']
            else:
                count = reverse_gl_entries(po, reason=REASON)
                if count:
                    append_comment(po, 'process', f'GL reversed: {REASON}', source='restate')
                    po.save(update_fields=['comments'])
            done.append(f'purchase {po.ida or po.pk}: {count} rows reversed')
        return done or ['no posted purchase']

    def _orphan_purchase_rows(self, apply):
        """GL rows of a purchase that no longer exists: reversed row by row (a PO posts nothing)."""
        from apps.accounts.models import GlJournal
        from apps.transactions.models import Purchase
        rows = GlJournal.objects.filter(source_model='purchase').exclude(
            source_id__in=Purchase.objects.values('pk'))
        reversed_ids = set(GlJournal.objects.filter(reversal_of__in=rows.values('id'))
                           .values_list('reversal_of', flat=True))
        done = []
        for row in rows.order_by('id'):
            if row.pk in reversed_ids:
                continue
            GlJournal.objects.create(ida=row.ida, account=row.account, debit=row.credit, credit=row.debit,
                                     source='automation', type=row.type, source_id=row.source_id,
                                     source_model='purchase_reversal', event_id=row.event_id,
                                     reversal_of=row.pk, note=f'Orphan (purchase deleted): {REASON}'[:255])
            done.append(f'row {row.pk} of deleted purchase {row.source_id} on {row.account} reversed')
        return done or ['no orphan purchase rows']

    def _missing_movements(self, apply):
        """A layer whose movements do not add up to what it holds lost an issue movement (a part used
        from the layer its own build made wrote none, fixed 2026-09-30). The line whose event
        recorded the take gets its movement back, so the GL can post it."""
        from django.db.models import Sum
        from apps.products.models.inventory_layer import InventoryLayer, InventoryMovement
        from apps.transactions.models import WorkOrderLine
        done = []
        for layer in InventoryLayer.objects.select_related('warehouse').all():
            q = layer.quantity or {}
            holds = (Decimal(str(q.get('received') or 0)) - Decimal(str(q.get('issued') or 0))
                     - Decimal(str(q.get('scrapped') or 0)))
            moved = InventoryMovement.objects.filter(inventory_layer=layer).aggregate(t=Sum('quantity'))['t'] or 0
            missing = Decimal(str(moved)) - holds
            if missing <= 0:
                continue
            for line in WorkOrderLine.objects.filter(events__contains=[{'consumed': {'layers': [{'layer_id': layer.pk}]}}]):
                for event in line.events or []:
                    for take in ((event or {}).get('consumed') or {}).get('layers') or []:
                        if take.get('layer_id') != layer.pk or take.get('build') or take.get('found') \
                                or take.get('return') or float(take.get('qty') or 0) <= 0 or missing <= 0:
                            continue
                        qty = min(Decimal(str(take['qty'])), missing)
                        InventoryMovement.objects.create(
                            item_id=layer.item_id, warehouse=layer.warehouse, inventory_layer=layer,
                            site_code=layer.warehouse.site_code, movement_type=InventoryMovement.MOVEMENT_ISSUE,
                            quantity=-qty, reason='restated: an issue that wrote no movement',
                            parent_model='workorderline', parent_id=line.pk)
                        missing -= qty
                        done.append(f'layer {layer.pk}: issue of {qty} by workorder line {line.pk} restored')
            if missing > 0:
                done.append(f'layer {layer.pk}: {missing} still unaccounted (no event names the take)')
        return done or ['every layer matches its movements']

    # ── 2b. Legacy adjustments and workorders ─────────────────────────────────────────
    def _adjustments(self, apply):
        """A legacy item adjustment's inventory credit was stock the books opened with: to opening
        equity, as a pre-layer sale's is."""
        from apps.accounts.models import GlAccount, GlJournal
        from apps.accounts.services.journalize import _role
        inventory_accounts = set(GlAccount.objects.filter(used_for='inventory').values_list('ida', flat=True))
        opening = _role('opening_balance_equity', used_by='restate_gl_by_layer')
        rows = GlJournal.objects.filter(source_model='adjustment', account__in=inventory_accounts)
        reversed_ids = set(GlJournal.objects.filter(reversal_of__in=rows.values('id'))
                           .values_list('reversal_of', flat=True))
        net: dict = {}
        for row in rows:
            if row.pk not in reversed_ids:
                key = (row.source_id, row.account, row.ida)
                net[key] = net.get(key, Decimal('0')) + Decimal(str(row.debit or 0)) - Decimal(str(row.credit or 0))
        done = []
        for (source_id, account, ida), amount in net.items():
            amount = amount.quantize(Decimal('0.01'))
            if amount >= 0:
                continue
            for acct, debit, credit in ((account, -amount, None), (opening, None, -amount)):
                GlJournal.objects.create(ida=ida, account=acct, debit=float(debit) if debit else None,
                                         credit=float(credit) if credit else None, source='automation',
                                         type='inventory', source_id=source_id, source_model='adjustment',
                                         event_id='opening-reclass',
                                         note='Adjusted stock the books opened with: to opening equity')
            done.append(f'adjustment {ida}: {-amount:.2f} inventory credit moved to opening equity')
        return done or ['no legacy adjustment']

    def _workorders(self, apply):
        """Every workorder with movements not yet posted is journalized, so the GL holds every layer
        change (the opening count, built above, is journalized already)."""
        from apps.accounts.services.journalize import journalize_workorder
        from apps.products.models.inventory_layer import InventoryMovement
        from apps.transactions.models import WorkOrder, WorkOrderLine
        line_ids = InventoryMovement.objects.filter(parent_model='workorderline', dt_journaled=0) \
            .values_list('parent_id', flat=True)
        wo_ids = set(WorkOrderLine.objects.filter(pk__in=line_ids).values_list('workorder_id', flat=True))
        done = []
        for wo in WorkOrder.objects.filter(pk__in=wo_ids).order_by('pk'):
            out = journalize_workorder(wo.pk)
            done.append(f'workorder {wo.ida or wo.pk} ({wo.kind}): {out}')
        return done or ['no workorder with unposted movements']

    # ── 3. Invoices ────────────────────────────────────────────────────────────────────
    def _invoices(self, apply):
        """An invoice whose lines consumed layers: its item-cost COGS rows are reversed and its layer
        COGS posted. An invoice from before layers followed sales (no movements, no deficits): its
        COGS stands, and the inventory it credited moves to opening equity, since the goods it
        sold were stock the books opened with (Bill, 2026-09-30)."""
        from apps.accounts.models import GlAccount, GlJournal
        from apps.accounts.services.journalize import (_get_item_gls, _invoice_cost_of_goods, _now_ms, _role,
                                                       journal_ida)
        from apps.accounts.services.ledger_balance import reverse_gl_entries
        from apps.products.models.inventory_layer import InventoryMovement
        from apps.transactions.models import Invoice
        cost_accounts = set(GlAccount.objects.filter(used_for__in=('cogs', 'inventory'))
                            .values_list('ida', flat=True))
        inventory_accounts = set(GlAccount.objects.filter(used_for='inventory').values_list('ida', flat=True))
        opening = _role('opening_balance_equity', used_by='restate_gl_by_layer')

        def _post(invoice, account, debit, credit, event_id, note):
            GlJournal.objects.create(
                ida=journal_ida('', 'SJ', invoice.ida), account=account,
                debit=float(debit) if debit else None, credit=float(credit) if credit else None,
                source='automation', type='sales', source_id=invoice.pk, source_model='invoice',
                event_id=event_id, note=note)

        done = []
        for invoice in Invoice.objects.filter(dt_journaled__gt=0).order_by('pk'):
            movements, cost_by_item = _invoice_cost_of_goods(list(invoice.lines.all()))
            if movements or cost_by_item:
                reversed_rows = reverse_gl_entries(invoice, reason=REASON, accounts=cost_accounts)
                posted = Decimal('0')
                for item_id, cost in cost_by_item.items():
                    if not cost:
                        continue
                    gls = _get_item_gls(item_id) if item_id else {}
                    _post(invoice, gls.get('cogs') or _role('cost_of_goods_sold'), cost, None,
                          'cogs-by-layer', 'COGS restated from the layers')
                    _post(invoice, gls.get('inventory') or _role('inventory'), None, cost,
                          'cogs-by-layer', 'COGS restated from the layers')
                    posted += cost
                InventoryMovement.objects.filter(pk__in=[m.pk for m in movements]).update(dt_journaled=_now_ms())
                done.append(f'invoice {invoice.ida}: {reversed_rows} cost rows reversed; layer COGS {posted:.2f}')
                continue
            rows = GlJournal.objects.filter(source_id=invoice.pk, source_model='invoice',
                                            account__in=inventory_accounts)
            reversed_ids = set(GlJournal.objects.filter(reversal_of__in=rows.values('id'))
                               .values_list('reversal_of', flat=True))
            net: dict = {}
            for row in rows:
                if row.pk not in reversed_ids:
                    net[row.account] = net.get(row.account, Decimal('0')) + \
                        Decimal(str(row.debit or 0)) - Decimal(str(row.credit or 0))
            moved = Decimal('0')
            for account, amount in net.items():
                amount = amount.quantize(Decimal('0.01'))
                if amount < 0:                     # inventory credited for goods never posted in
                    _post(invoice, account, -amount, None, 'opening-reclass',
                          'Sold from stock the books opened with: to opening equity')
                    _post(invoice, opening, None, -amount, 'opening-reclass',
                          'Sold from stock the books opened with: to opening equity')
                    moved += -amount
            done.append(f'invoice {invoice.ida}: before layers; COGS stands, {moved:.2f} inventory credit '
                        'moved to opening equity')
        return done or ['no journalized invoice']

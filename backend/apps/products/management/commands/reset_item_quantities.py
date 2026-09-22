"""Reset items to a balanced opening position: the training data set's repair.

Bill, 2026-09-21: *"we need a balanced data set for training. So when we find defects, we
can force the data to be what we had intended."* Balanced means:

1. every change to on_hand has a Pending,
2. on_hand equals Σ(received − issued − scrapped) over the item's layers,
3. the layers carry FIFO/LIFO, and cost.avg is a moving average,
4. on_qt / on_so / on_po / on_wo equal the open documents (rebuild_commitment_buckets),
5. allocated equals the allocations that were made, each a Pending.

This command used to set on_hand to 100 directly, with no Pending and no layer. That is
how wc_demo came to hold 5004 units against 13 in layers. Bill: "We have done it
regularly. From now on even in demo data we should make inventory changes that comply."

For each item (not deleted; qq/zz scratch items included — the assessors read them):

- its item Pendings become history: processed ones are marked
  ``config.epoch = 'before-reset-<date>'``; unprocessed ones are voided
  (``changes.state = 'void'``). Unprocessed Pendings with no record_id (the item-id
  resolver bug) are voided too: they could never apply.
- its layers and movements are deleted, and its buckets and allocated are zeroed once,
  directly: the one write this rule allows, because it closes the history the Pendings
  above no longer sum to.
- then everything it holds comes back through Pendings, each applied by the one applier:
  every live receipt line is replayed (on_hand, on_rc and a new layer the line points
  at); a physical item's remaining stock opens in one ``opening_balance`` layer at
  cost.avg; its allocation is re-made; its commitments are rebuilt from the documents.
  A service holds no stock.

DEMO DATA ONLY. Bill: *"The key in demo data is establishing a balance. That is not true of
real data where defects must be accounted for."* Real data keeps its defects on the record
and is corrected by accounted entries, never by a reset. The command refuses any database
whose name does not say demo (or a pytest test_ database), and write-through mode.

    manage.py reset_item_quantities                       # dry run
    manage.py reset_item_quantities --apply
    manage.py reset_item_quantities --apply --on-hand 50  # open physical items at 50
    manage.py reset_item_quantities --apply --item-id 612
"""
from collections import defaultdict
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

BUCKETS = ('on_hand', 'on_so', 'on_po', 'on_wo', 'on_qt', 'on_in', 'on_rc', 'in_process', 'allocated',
           'available')


def _d(value) -> Decimal:
    return Decimal(str(value or 0))


class Command(BaseCommand):
    help = "Reset items to a balanced opening position (Pendings, layers, commitments agree)"

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='write the reset')
        parser.add_argument('--on-hand', type=int, default=None,
                            help='open every physical item at this quantity (default: what it holds now)')
        parser.add_argument('--item-id', type=int, default=None, help='one item only')
        parser.add_argument('--warehouse-id', type=int, default=1,
                            help='warehouse opening layers land in (default: 1)')

    def handle(self, *args, **options):
        from django.conf import settings
        from apps.core.models import Pending
        from apps.products.models import Item, Warehouse
        from apps.products.models.inventory_layer import InventoryLayer, InventoryMovement
        from apps.transactions.models import ReceiptLine
        from apps.transactions.services.line_manage import _line_item_id
        from apps.products.management.commands.rebuild_commitment_buckets import (
            BUCKETS as COMMITMENTS, post_repair, wanted_by_item)

        db_name = str(settings.DATABASES['default'].get('NAME') or '')
        if getattr(settings, 'WRITE_THROUGH_ENABLED', False) or not (
                'demo' in db_name.lower() or db_name.startswith('test_')):
            raise CommandError(f"refusing to reset '{db_name}': demo data only — real data "
                               "keeps its defects on the record (Bill, 2026-09-21)")

        items = Item.objects.filter(is_deleted=False)
        if options['item_id']:
            items = items.filter(pk=options['item_id'])
        items = {i.pk: i for i in items}
        if not items:
            raise CommandError('no items in scope')
        ids = list(items)
        warehouse = Warehouse.objects.get(pk=options['warehouse_id'])

        # What each item's receipts put on the shelf — replayed, not re-opened.
        receipts = defaultdict(list)
        for rl in (ReceiptLine.objects.filter(is_deleted=False, receipt__is_deleted=False)
                   .select_related('receipt')):
            item_id = _line_item_id(rl)
            qty = _d((rl.quantity or {}).get('active'))
            if item_id and int(item_id) in items and qty > 0:
                receipts[int(item_id)].append((rl, qty))

        def plan_for(item):
            if item.is_not_tracked:           # no stock: no layers, buckets stay zero
                return {'receipts': [], 'opening': Decimal('0'), 'allocated': Decimal('0')}
            received = sum((q for _rl, q in receipts[item.pk]), Decimal('0'))
            if options['on_hand'] is not None:
                target = Decimal(options['on_hand'])
            else:
                target = max(_d((item.quantity or {}).get('on_hand')), Decimal('0'))
            return {'receipts': receipts[item.pk], 'opening': max(target - received, Decimal('0')),
                    'allocated': max(_d((item.quantity or {}).get('allocated')), Decimal('0'))}

        plan = {pk: plan_for(item) for pk, item in items.items()}
        str_ids = [str(i) for i in ids]
        history = Pending.objects.filter(model_name='item', record_id__in=str_ids)
        orphans = Pending.objects.filter(model_name='item', dt_processed=0).filter(
            Q(record_id='') | Q(record_id__isnull=True))
        layers = InventoryLayer.objects.filter(item_id__in=ids)
        epoch = f"before-reset-{timezone.now():%Y-%m-%d}"

        self.stdout.write(
            f"{len(ids)} items; {history.filter(dt_processed__gt=0).count()} pendings become "
            f"'{epoch}'; {history.filter(dt_processed=0).count() + orphans.count()} voided; "
            f"{layers.count()} layers deleted; replay {sum(len(p['receipts']) for p in plan.values())} "
            f"receipt lines; {sum(1 for p in plan.values() if p['opening'])} opening balances "
            f"({sum(p['opening'] for p in plan.values())} units, warehouse {warehouse.code}); "
            f"{sum(1 for p in plan.values() if p['allocated'])} allocations re-made")
        if not options['apply']:
            self.stdout.write(self.style.WARNING('Dry run — pass --apply to write.'))
            return

        now_ms = int(timezone.now().timestamp() * 1000)
        with transaction.atomic():
            for p in history.filter(dt_processed__gt=0):
                p.config = {**(p.config if isinstance(p.config, dict) else {}), 'epoch': epoch}
                p.save(update_fields=['config', 'dt_modified', 'version'])
            for p in list(history.filter(dt_processed=0)) + list(orphans):
                changes = p.changes if isinstance(p.changes, dict) else {}
                p.changes = {**changes, 'state': 'void',
                             'void_reason': f'{epoch}: history closed by reset_item_quantities'}
                p.dt_processed = now_ms
                p.save(update_fields=['changes', 'dt_processed', 'dt_modified', 'version'])

            InventoryMovement.objects.filter(item_id__in=ids).delete()
            layers.delete()                      # receipt lines' FK is SET_NULL
            for item in items.values():
                q = dict(item.quantity or {})
                q.update({b: 0 for b in BUCKETS})
                Item.objects.filter(pk=item.pk).update(quantity=q)

            for pk, item in items.items():
                p = plan[pk]
                for rl, qty in p['receipts']:
                    cost = rl.cost if isinstance(rl.cost, dict) else {}
                    Pending.objects.create(
                        model_name='item', record_id=str(pk), purpose='inventory_line_add',
                        name=f"reset replay: receipt {rl.receipt.ida} line {rl.pk}"[:120],
                        changes={
                            'type_id': 'RC', 'item_id': pk, 'line_id': rl.pk,
                            'on_hand': float(qty), 'on_rc': float(qty),
                            'reason': f'{epoch}: receipt replayed',
                            'layer': {'line_id': rl.pk, 'create': {
                                'warehouse_id': rl.warehouse_id or warehouse.pk,
                                'lot': rl.lot or '', 'serial_batch': rl.serial_batch or '',
                                'unit_cost': float(cost.get('unit') or 0),
                                'source_doc_type': rl.receipt.source_type or 'purchase_receipt',
                                'source_doc_id': rl.receipt_id,
                            }},
                        },
                    )
                if p['opening']:
                    cost = item.cost if isinstance(item.cost, dict) else {}
                    Pending.objects.create(
                        model_name='item', record_id=str(pk), purpose='opening_balance',
                        name=f"opening balance: {item.ida or item.name}"[:120],
                        changes={
                            'type_id': 'OB', 'item_id': pk, 'on_hand': float(p['opening']),
                            'reason': f'{epoch}: opening balance',
                            'layer': {'create': {
                                'warehouse_id': warehouse.pk,
                                'unit_cost': float(cost.get('avg') or cost.get('last') or 0),
                                'source_doc_type': 'opening_balance', 'source_doc_id': None,
                                'lot': 'OPENING',
                            }},
                        },
                    )
                if p['allocated']:
                    Pending.objects.create(
                        model_name='item', record_id=str(pk), purpose='allocation',
                        name=f"reset replay: allocate {p['allocated']} of item {pk}",
                        changes={'allocated': float(p['allocated'])},
                        config={'item_id': pk, 'source_type': 'allocation', 'by': 'reset',
                                'reason': f'{epoch}: allocation re-made', 'verb': 'allocate'},
                    )

            want = wanted_by_item()
            for pk, item in items.items():
                target = want.get(pk) or {}
                deltas = {b: (0.0, round(target.get(b, 0.0), 4)) for b in COMMITMENTS
                          if round(target.get(b, 0.0), 4)}
                if deltas:
                    post_repair(item, deltas)

            stuck = Pending.objects.filter(model_name='item', record_id__in=str_ids, dt_processed=0)
            if stuck.exists():
                raise CommandError(f'{stuck.count()} reset pendings did not apply (locked?) — '
                                   'rolled back, nothing changed')

        self.stdout.write(self.style.SUCCESS(f"Reset {len(ids)} items to a balanced opening position."))

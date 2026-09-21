"""Does inventory and cash balance? One read-only answer, for Alice and for people.

Bill, 2026-09-21: *"A dedicated function for Alice of balance_checker would be very
helpful"* and *"pending records should be powerful for this."*

Every check here is an **invariant or an independent axis**, never a recomputation done
the way the writer does it. A checker that derives a figure with the writer's formula
shares the writer's bug and reports clean: that is how the AP sign error survived
``in_step`` (recheck 3, 2026-09-20). So:

- **Inventory — the Pending journal.** ``Item.quantity`` is a running total the applier
  moves one delta at a time. The applied Pendings are the journal behind it. Every bucket
  must equal Σ its applied Pendings since the item's last epoch (a reset marks earlier
  Pendings ``config.epoch``). A writer that moves a bucket without a Pending, or a Pending
  that applied twice, shows here and nowhere else.
- **Inventory — the layers.** on_hand must equal Σ (received − issued − scrapped) over the
  item's layers, and each layer must lie in its own range.
- **Inventory — commitments.** on_qt / on_so / on_po / on_wo against the open documents
  (``commitment_gaps``: the same function the repair uses).
- **Cash — invariants and echoes, not a Pending sum.** ``refresh_cash_available`` already
  derives available as amount − Σ applied Pendings, so summing those Pendings again would be
  the writer's formula twice. Cash uses the range invariant and the ledger echoes in
  ``compute_org_summary`` / ``compute_vendor_summary``.
- **Pendings that should have applied and did not.** A Pending with a handler that is still
  unprocessed after ``stuck_minutes`` is money or stock that the record says moved and the
  books say did not.

Nothing here writes. A finding is data; a person (or a reset on demo data) repairs.
"""
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from django.apps import apps as dj_apps
from django.db.models import Q

BUCKETS = ('on_hand', 'allocated', 'on_so', 'on_po', 'on_wo', 'on_qt', 'on_in', 'on_rc')
CASH_PURPOSES = ('cash_application', 'cash_application_receipt')
TOLERANCE = Decimal('0.0001')
STUCK_MINUTES = 10


def _d(value) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal('0')


def _finding(check, model, record_id, message, *, ida=None, field=None, have=None, expect=None):
    out = {'check': check, 'model': model, 'record_id': record_id, 'ida': ida, 'message': message}
    if field is not None:
        out['field'] = field
    if have is not None:
        out.update(have=float(have), expect=float(expect), gap=float(_d(have) - _d(expect)))
    return out


def _pending_data(pending) -> dict:
    """What the applier applies: ``changes`` when it is a dict, else ``config``.

    The same selection ``Pending._apply_inventory`` makes — a selection, not a formula.
    """
    if isinstance(pending.changes, dict) and pending.changes:
        return pending.changes
    return pending.config if isinstance(pending.config, dict) else {}


def check_inventory(item_id=None) -> tuple[list, dict]:
    Item = dj_apps.get_model('products', 'Item')
    Pending = dj_apps.get_model('core', 'Pending')
    InventoryLayer = dj_apps.get_model('products', 'InventoryLayer')
    from apps.core.models.pending import INVENTORY_PURPOSES
    from apps.products.management.commands.rebuild_commitment_buckets import commitment_gaps

    items = Item.objects.filter(is_deleted=False)
    if item_id:
        items = items.filter(pk=item_id)
    items = {i.pk: i for i in items}
    findings = []

    # The journal: Σ applied Pendings per item per bucket, since the last epoch.
    journal = defaultdict(lambda: dict.fromkeys(BUCKETS, Decimal('0')))
    pendings = (Pending.objects.filter(model_name='item', purpose__in=INVENTORY_PURPOSES,
                                       dt_processed__gt=0)
                .exclude(config__has_key='epoch'))
    if item_id:
        pendings = pendings.filter(record_id=str(item_id))
    for p in pendings.iterator():
        try:
            pk = int(p.record_id)
        except (TypeError, ValueError):
            continue
        data = _pending_data(p)
        for bucket in BUCKETS:
            journal[pk][bucket] += _d(data.get(bucket))

    # The shelf: Σ remaining over each item's layers, and each layer in its own range.
    shelf = defaultdict(Decimal)
    layers = InventoryLayer.objects.all()
    if item_id:
        layers = layers.filter(item_id=item_id)
    for layer in layers.iterator():
        q = layer.quantity or {}
        received, issued, scrapped = _d(q.get('received')), _d(q.get('issued')), _d(q.get('scrapped'))
        shelf[layer.item_id] += received - issued - scrapped
        if received < 0 or issued < 0 or scrapped < 0 or issued + scrapped > received + TOLERANCE:
            findings.append(_finding(
                'inventory.layer_range', 'inventorylayer', layer.pk,
                f"layer {layer.pk} (item {layer.item_id}): received {received}, issued {issued}, "
                f"scrapped {scrapped} — out more than came in"))

    for pk, item in items.items():
        quantity = item.quantity or {}
        label = item.ida or item.name
        for bucket in BUCKETS:
            have, expect = _d(quantity.get(bucket)), journal[pk][bucket]
            if abs(have - expect) > TOLERANCE:
                findings.append(_finding(
                    'inventory.pending_journal', 'item', pk,
                    f"item {label}: {bucket} {have} but its applied Pendings sum to {expect} "
                    f"— a change with no Pending, or a Pending applied twice",
                    ida=label, field=bucket, have=have, expect=expect))
        on_hand, allocated = _d(quantity.get('on_hand')), _d(quantity.get('allocated'))
        available = _d(quantity.get('available'))
        if abs(available - (on_hand - allocated)) > TOLERANCE:
            findings.append(_finding(
                'inventory.available', 'item', pk,
                f"item {label}: available {available} ≠ on_hand {on_hand} − allocated {allocated}",
                ida=label, field='available', have=available, expect=on_hand - allocated))
        if abs(on_hand - shelf[pk]) > TOLERANCE:
            findings.append(_finding(
                'inventory.layers', 'item', pk,
                f"item {label}: on_hand {on_hand} but its layers hold {shelf[pk]}",
                ida=label, field='on_hand', have=on_hand, expect=shelf[pk]))

    for gap in commitment_gaps(item_id):
        findings.append(_finding(
            'inventory.commitments', 'item', gap['item_id'],
            f"item {gap['ida']}: {gap['bucket']} {gap['have']} but open documents commit {gap['expect']}",
            ida=gap['ida'], field=gap['bucket'], have=gap['have'], expect=gap['expect']))

    # A receipt line that put stock on the shelf must point at the layer it made.
    ReceiptLine = dj_apps.get_model('transactions', 'ReceiptLine')
    orphans = ReceiptLine.objects.filter(is_deleted=False, receipt__is_deleted=False,
                                         inventory_layer__isnull=True)
    if item_id:
        orphans = orphans.filter(Q(item_fk_id=item_id) | Q(item__item_id=item_id) | Q(item__id_num=item_id))
    for line in orphans:
        if _d((line.quantity or {}).get('active')) > 0:
            findings.append(_finding(
                'inventory.receipt_without_layer', 'receiptline', line.pk,
                f"receipt line {line.pk} (receipt {line.receipt_id}) received stock but has no layer"))

    return findings, {'items': len(items), 'layers': len(shelf)}


def check_pendings(stuck_minutes=STUCK_MINUTES, item_id=None) -> tuple[list, dict]:
    """Pendings a handler should have applied and has not; plus the backlog with no handler."""
    Pending = dj_apps.get_model('core', 'Pending')
    from apps.core.models.pending import INVENTORY_PURPOSES

    cutoff = int(datetime.now(timezone.utc).timestamp() * 1000) - stuck_minutes * 60_000
    handled = Q(model_name='item', purpose__in=INVENTORY_PURPOSES) | Q(purpose__in=CASH_PURPOSES)
    stuck = Pending.objects.filter(handled, dt_processed=0, dt_created__lt=cutoff)
    if item_id:
        stuck = stuck.filter(model_name='item', record_id=str(item_id))
    findings = []
    for p in stuck:
        state = (p.changes or {}).get('state') if isinstance(p.changes, dict) else None
        if state in ('void', 'canceled'):
            continue
        findings.append(_finding(
            'pending.stuck', 'pending', p.pk,
            f"pending {p.pk} ({p.purpose}, {p.model_name} {p.record_id}) unapplied after "
            f"{p.attempts} attempts — the record says it moved, the books say it did not"))

    backlog = defaultdict(int)
    for purpose in (Pending.objects.filter(dt_processed=0).exclude(handled)
                    .values_list('purpose', flat=True)):
        backlog[purpose or '(none)'] += 1
    return findings, {'unhandled_backlog': dict(backlog)}


def check_cash(org_id=None) -> tuple[list, dict]:
    """Every customer and vendor with documents or cash: the in_step invariants."""
    from apps.accounts.services.ledger_balance import compute_org_summary, compute_vendor_summary
    Invoice = dj_apps.get_model('transactions', 'Invoice')
    Receipt = dj_apps.get_model('transactions', 'Receipt')
    Cash = dj_apps.get_model('transactions', 'Cash')

    def ids(qs, field):
        qs = qs.filter(is_deleted=False).exclude(**{f'{field}__isnull': True})
        if org_id:
            qs = qs.filter(**{field: org_id})
        return set(qs.values_list(field, flat=True).distinct())

    customers = ids(Invoice.objects, 'customer_id') | ids(Cash.objects, 'customer_id')
    vendors = ids(Receipt.objects, 'vendor_id') | ids(Cash.objects, 'vendor_id')
    findings = []
    for side, org_ids, summarize in (('customer', customers, compute_org_summary),
                                     ('vendor', vendors, compute_vendor_summary)):
        for oid in sorted(org_ids):
            summary = summarize(oid)
            for mismatch in summary.mismatches or []:
                findings.append(_finding(f'cash.{side}', 'org', oid, f"{side} {oid}: {mismatch}"))
    return findings, {'customers': len(customers), 'vendors': len(vendors)}


def check_balances(scope=('inventory', 'cash', 'pending'), item_id=None, org_id=None,
                   stuck_minutes=STUCK_MINUTES) -> dict:
    """The one entry point. Returns ``{balanced, findings, counts, checked, dt_checked}``.

    ``balanced`` is True only when no check found anything. ``counts`` groups findings by
    check, so a reader sees at a glance which axis drifted.
    """
    from django.conf import settings
    findings, checked = [], {}
    if 'inventory' in scope:
        f, c = check_inventory(item_id)
        findings += f
        checked['inventory'] = c
    if 'pending' in scope:
        f, c = check_pendings(stuck_minutes, item_id)
        findings += f
        checked['pending'] = c
    if 'cash' in scope and not item_id:
        f, c = check_cash(org_id)
        findings += f
        checked['cash'] = c

    counts = defaultdict(int)
    for f in findings:
        counts[f['check']] += 1
    return {
        'balanced': not findings,
        'database': str(settings.DATABASES['default'].get('NAME') or ''),
        'dt_checked': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'scope': list(scope),
        'checked': checked,
        'counts': dict(counts),
        'findings': findings,
    }


def _event_scope(pending) -> tuple[str, dict]:
    """What one Pending touched: an item, or the customer/vendor whose cash moved."""
    if pending.model_name == 'item':
        return 'inventory', {'item_id': int(pending.record_id)} if str(pending.record_id or '').isdigit() else {}
    changes = pending.changes if isinstance(pending.changes, dict) else {}
    Cash = dj_apps.get_model('transactions', 'Cash')
    cash = Cash.objects.filter(pk=changes.get('cash_id')).first()
    if cash is None:
        return 'cash', {}
    side = 'vendor' if pending.purpose == 'cash_application_receipt' else 'customer'
    org_id = getattr(cash, f'{side}_id', None)
    return 'cash', {'org_id': org_id} if org_id else {}


def _write_event(pending, applied: bool, event: str) -> None:
    import json
    from django.conf import settings
    record = {
        'dt': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        'event': event,
        'pending_id': pending.pk,
        'purpose': pending.purpose,
        'model': pending.model_name,
        'record_id': pending.record_id,
        'name': pending.name,
        'changes': pending.changes if isinstance(pending.changes, dict) else _pending_data(pending),
        'applied': applied,
    }
    if applied:
        area, target = _event_scope(pending)
        if area == 'inventory' and target:
            findings, _ = check_inventory(target['item_id'])
        elif area == 'cash' and target:
            findings, _ = check_cash(target['org_id'])
        else:
            findings = [_finding('event.unscoped', pending.model_name, pending.record_id,
                                 f"pending {pending.pk}: cannot tell which item or party it moved")]
        record.update(scope={area: target}, balanced=not findings, findings=findings[:10])
    path = settings.BALANCE_EVENT_LOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a') as fh:
        fh.write(json.dumps(record, default=str) + '\n')


def log_balance_event(pending, applied: bool, event: str = 'apply') -> None:
    """One line per cash or inventory event: what moved, and whether it still balances.

    Bill, 2026-09-21: *"Especially while we are testing, should we have a running log of
    every cash and inventory event and if it is properly balanced?"* The check runs
    after the commit, so it sees what the next reader sees; it is scoped to the item or
    party the event touched, so the first unbalanced line names the event that broke it.
    A Pending that did not apply is logged too (``applied: false``) — it is the start of a
    stuck one. Never raises: a log must not stop a sale.
    """
    from django.conf import settings
    from django.db import transaction
    if not getattr(settings, 'BALANCE_EVENT_LOG', False):
        return

    def write():
        try:
            _write_event(pending, applied, event)
        except Exception:
            import logging
            logging.getLogger(__name__).warning('balance event log failed for pending %s',
                                                pending.pk, exc_info=True)

    transaction.on_commit(write)

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
- **Inventory — the layers.** on_hand + Σ open deficit must equal Σ (received − issued −
  scrapped) over the item's layers, and each layer must lie in its own range. A deficit
  still open once on_hand is back to ≥ 0 is a fault (the receipt did not fill it).
- **Inventory — in process.** quantity.in_process must equal Σ metadata.on_assembly, the
  pointers to the workorder lines holding the parts.
- **Inventory — not tracked.** An item with flags.not_tracked (labor, freight estimates)
  holds no layer and no bucket (Bill, 2026-09-22).
- **Inventory — commitments.** on_qt / on_so / on_po / on_wo against the open documents
  (``commitment_gaps``: the same function the repair uses).
- **Cash — every Cash's stored available against its Pendings** (Bill, 2026-09-25): available
  = amount − Σ applied AR + Σ applied AP − refunds, the same rule inventory buckets follow.
  Summing is not "the writer's formula twice": it compares the *stored* number to the
  journal, and a stored number can drift while the formula is fine (wc_demo cash 58–60 sat
  at 0.00 for weeks; their Pendings said 1,663.00). Every Cash is checked, with or without
  a customer or vendor. Then the org invariants and ledger echoes in
  ``compute_org_summary`` / ``compute_vendor_summary``.
- **Cash Pendings that say processed but not applied** (state still ``pending`` with
  ``dt_processed`` set): money the record promises and the books never count.
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

BUCKETS = ('on_hand', 'allocated', 'on_so', 'on_po', 'on_wo', 'on_qt', 'on_in', 'on_rc', 'in_process')
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
    from apps.core.models.pending import DEFICIT_PURPOSE, INVENTORY_PURPOSES
    from apps.products.management.commands.rebuild_commitment_buckets import commitment_gaps

    items = Item.objects.all()
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

    # Open shortages: an issue that took on_hand below 0 left a deficit Pending open until
    # receipts fill it. The shelf is short by exactly that much (Bill, 2026-09-21).
    deficit = defaultdict(Decimal)
    deficits = Pending.objects.filter(purpose=DEFICIT_PURPOSE, dt_processed=0)
    if item_id:
        deficits = deficits.filter(record_id=str(item_id))
    for p in deficits.iterator():
        try:
            deficit[int(p.record_id)] += p.incremental_remaining('deficit_qty')
        except (TypeError, ValueError):
            continue

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
        if abs(on_hand + deficit[pk] - shelf[pk]) > TOLERANCE:
            findings.append(_finding(
                'inventory.layers', 'item', pk,
                f"item {label}: on_hand {on_hand} + open deficit {deficit[pk]} but its layers "
                f"hold {shelf[pk]}",
                ida=label, field='on_hand', have=on_hand + deficit[pk], expect=shelf[pk]))
        if deficit[pk] > TOLERANCE and on_hand >= 0:
            findings.append(_finding(
                'inventory.deficit_stale', 'item', pk,
                f"item {label}: on_hand {on_hand} is back, but {deficit[pk]} of deficit is still "
                f"open — the receipt that restored it did not fill the deficit",
                ida=label, field='on_hand', have=deficit[pk], expect=0))
        on_assembly = sum((_d(e.get('quantity')) for e in ((item.metadata or {}).get('on_assembly')
                           or []) if isinstance(e, dict)), Decimal('0'))
        in_process = _d(quantity.get('in_process'))
        if abs(in_process - on_assembly) > TOLERANCE:
            findings.append(_finding(
                'inventory.in_process', 'item', pk,
                f"item {label}: in_process {in_process} but metadata.on_assembly points at "
                f"{on_assembly}", ida=label, field='in_process', have=in_process, expect=on_assembly))
        if item.is_not_tracked:
            held = {b: float(_d(quantity.get(b))) for b in BUCKETS
                    if abs(_d(quantity.get(b))) > TOLERANCE}
            if held or abs(shelf[pk]) > TOLERANCE:
                findings.append(_finding(
                    'inventory.not_tracked_stock', 'item', pk,
                    f"item {label} is not tracked (flags.not_tracked) but holds buckets {held} "
                    f"and layers {shelf[pk]}", ida=label))

    for gap in commitment_gaps(item_id):
        findings.append(_finding(
            'inventory.commitments', 'item', gap['item_id'],
            f"item {gap['ida']}: {gap['bucket']} {gap['have']} but open documents commit {gap['expect']}",
            ida=gap['ida'], field=gap['bucket'], have=gap['have'], expect=gap['expect']))

    # A receipt line that put stock on the shelf must point at the layer it made.
    ReceiptLine = dj_apps.get_model('transactions', 'ReceiptLine')
    orphans = ReceiptLine.objects.filter(inventory_layer__isnull=True)
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

    # Processed but never applied: the applier marks 'applied' and dt_processed together,
    # close_queued marks 'canceled' and dt_processed together. 'pending' with dt_processed
    # set is neither — it counts nowhere (wc_demo #850, 2026-09-25).
    limbo = Pending.objects.filter(purpose__in=CASH_PURPOSES, changes__state='pending'
                                   ).exclude(dt_processed=0)
    for p in ([] if item_id else limbo):
        c = p.changes if isinstance(p.changes, dict) else {}
        findings.append(_finding(
            'pending.limbo', 'pending', p.pk,
            f"pending {p.pk} ({p.purpose}: {c.get('amount')} from cash {c.get('cash_id')} to "
            f"{'receipt ' + str(c.get('receipt_id')) if c.get('receipt_id') else 'invoice ' + str(c.get('invoice_id'))}) "
            f"is marked processed but was never applied — it counts on neither side"))

    backlog = defaultdict(int)
    for purpose in (Pending.objects.filter(dt_processed=0).exclude(handled)
                    .values_list('purpose', flat=True)):
        backlog[purpose or '(none)'] += 1
    return findings, {'unhandled_backlog': dict(backlog)}


def check_cash_available(org_id=None, cash_id=None) -> list:
    """Every Cash: stored ``available`` == amount − Σ applied AR + Σ applied AP − refunds,
    and the Pendings never take it past zero (``cash.overspent``). The creation check under
    the cash row lock refuses an overspend; this warns when any path wrote one anyway —
    Rule 10: an applier never refuses, so the warning is the fail-safe (Bill, 2026-09-25)."""
    from apps.transactions.services.cash.cash_pending import _applied, refunded
    from apps.transactions.services.cash.cash_pending_receipt import _applied as _applied_ap
    Cash = dj_apps.get_model('transactions', 'Cash')
    qs = Cash.objects.all()
    if org_id:
        qs = qs.filter(Q(customer_id=org_id) | Q(vendor_id=org_id))
    if cash_id:
        qs = qs.filter(pk=cash_id)
    findings = []
    for cash in qs.order_by('pk'):
        expect = ((_d(cash.amount) - _applied(cash_id=cash.pk) + _applied_ap(cash_id=cash.pk)
                   - refunded(cash)) if cash.holds_money else Decimal('0'))
        have = _d(cash.available)
        amount = _d(cash.amount)
        if expect and amount and (expect > 0) != (amount > 0):
            findings.append(_finding(
                'cash.overspent', 'cash', cash.pk,
                f"cash {cash.pk} ({cash.ida}) of {abs(amount)} has {abs(amount - expect)} "
                f"applied: {abs(expect)} more than it received",
                ida=cash.ida, field='available', have=expect, expect=Decimal('0')))
        if abs(have - expect) > TOLERANCE:
            findings.append(_finding(
                'cash.available', 'cash', cash.pk,
                f"cash {cash.pk} ({cash.ida}) shows {have} available; its Pendings say {expect}",
                ida=cash.ida, field='available', have=have, expect=expect))
    return findings


def _applied_by(purpose: str, key: str, adjustment_kinds=()) -> tuple[dict, dict]:
    """Σ applied amounts per document id for one application purpose, in one query:
    ({doc_id: money}, {doc_id: adjustments})."""
    Pending = dj_apps.get_model('core', 'Pending')
    money, adjusted = defaultdict(Decimal), defaultdict(Decimal)
    for changes in (Pending.objects.filter(purpose=purpose, changes__state='applied')
                    .values_list('changes', flat=True)):
        doc_id = (changes or {}).get(key)
        if doc_id is None:
            continue
        amount = _d(changes.get('amount'))
        if changes.get('kind') in adjustment_kinds:
            adjusted[int(doc_id)] += amount
        else:
            money[int(doc_id)] += amount
    return money, adjusted


def check_document_settlement(org_id=None) -> list:
    """Every invoice and receipt: the stored settlement against its applications.

    The mirror of ``check_cash_available`` (fix #2, Fable L2 H-1): ``totals.received`` /
    ``adjusted`` (AR) and ``totals.paid`` (AP) must equal Σ their applied Pendings, and
    ``balance`` must equal total − settled − adjusted. Stored numbers are compared with the
    journal; nothing is recomputed the writer's way. wc_demo invoices 75, 96–101 read
    received 0.00 over 734.00 applied, and ``in_step`` agreed because the ledger echo was
    written from the same wrong number.
    """
    from apps.transactions.services.cash.cash_pending import ADJUSTMENT_METHODS
    Invoice = dj_apps.get_model('transactions', 'Invoice')
    Receipt = dj_apps.get_model('transactions', 'Receipt')
    findings = []
    sides = (
        (Invoice, 'invoice', 'customer_id', 'cash_application', 'invoice_id', 'received', ADJUSTMENT_METHODS),
        (Receipt, 'receipt', 'vendor_id', 'cash_application_receipt', 'receipt_id', 'paid', ()),
    )
    for Model, label, org_field, purpose, key, settle_key, adj_kinds in sides:
        money, adjusted = _applied_by(purpose, key, adj_kinds)
        qs = Model.objects.all()
        if org_id:
            qs = qs.filter(**{org_field: org_id})
        for doc in qs.only('id', 'ida', 'totals').order_by('pk'):
            t = doc.totals if isinstance(doc.totals, dict) else {}
            expect_settled = money.get(doc.pk, Decimal(0))
            have_settled = _d(t.get(settle_key))
            if abs(have_settled - expect_settled) > TOLERANCE:
                findings.append(_finding(
                    f'{label}.{settle_key}', label, doc.pk,
                    f"{label} {doc.pk} ({doc.ida}) shows {settle_key} {have_settled}; its applications say "
                    f"{expect_settled}", ida=doc.ida, field=f'totals.{settle_key}',
                    have=have_settled, expect=expect_settled))
            stored_adj = _d(t.get('adjusted'))
            if label == 'invoice':
                expect_adj = adjusted.get(doc.pk, Decimal(0))
                if abs(stored_adj - expect_adj) > TOLERANCE:
                    findings.append(_finding(
                        'invoice.adjusted', label, doc.pk,
                        f"invoice {doc.pk} ({doc.ida}) shows adjusted {stored_adj}; its applications say {expect_adj}",
                        ida=doc.ida, field='totals.adjusted', have=stored_adj, expect=expect_adj))
            expect_balance = _d(t.get('total')) - have_settled - stored_adj
            if abs(_d(t.get('balance')) - expect_balance) > TOLERANCE:
                findings.append(_finding(
                    f'{label}.balance', label, doc.pk,
                    f"{label} {doc.pk} ({doc.ida}) balance {_d(t.get('balance'))} ≠ total − {settle_key} − "
                    f"adjusted = {expect_balance}", ida=doc.ida, field='totals.balance',
                    have=_d(t.get('balance')), expect=expect_balance))
    return findings


def check_ledger_rows(org_id=None) -> list:
    """Every invoice and receipt: its ledger rows against its terms.

    Bill, 2026-09-26: rows per document = the instalments its terms call for, open or paid
    (``ledger.rows``), and Σ value_available of those rows = the document's balance
    (``ledger.sum``). The count is structural: a missing or doubled row shows here even
    when the money happens to add up.
    """
    from apps.accounts.services.terms_ledger import expected_ledger_rows
    Ledger = dj_apps.get_model('accounts', 'Ledger')
    Invoice = dj_apps.get_model('transactions', 'Invoice')
    Receipt = dj_apps.get_model('transactions', 'Receipt')
    findings = []
    sides = ((Invoice, 'invoice', 'customer_id', 'invoice_id'),
             (Receipt, 'receipt', 'vendor_id', 'parent_id'))
    for Model, label, org_field, key in sides:
        rows = defaultdict(list)
        for doc_id, value in (Ledger.objects.filter(model_name=label)
                              .values_list(key, 'value_available')):
            rows[doc_id].append(_d(value))
        qs = Model.objects.all()
        if org_id:
            qs = qs.filter(**{org_field: org_id})
        for doc in qs.order_by('pk'):
            try:
                expect = expected_ledger_rows(doc, label)
            except ValueError as e:                  # no resolvable terms: say so
                findings.append(_finding('ledger.terms', label, doc.pk, f"{label} {doc.pk} ({doc.ida}): {e}",
                                         ida=doc.ida))
                continue
            have = rows.get(doc.pk, [])
            if len(have) != expect:
                findings.append(_finding(
                    'ledger.rows', label, doc.pk,
                    f"{label} {doc.pk} ({doc.ida}) has {len(have)} ledger rows; its terms call for {expect}",
                    ida=doc.ida, field='ledger', have=len(have), expect=expect))
            if have:
                balance = _d((doc.totals or {}).get('balance'))
                if abs(sum(have, Decimal(0)) - balance) > TOLERANCE:
                    findings.append(_finding(
                        'ledger.sum', label, doc.pk,
                        f"{label} {doc.pk} ({doc.ida}) ledger rows hold {sum(have, Decimal(0))}; "
                        f"its balance is {balance}", ida=doc.ida, field='ledger.value_available',
                        have=sum(have, Decimal(0)), expect=balance))
    return findings


def check_orphan_applications() -> list:
    """An applied application whose cash or document no longer exists: money the journal
    says moved, pointing nowhere (wc_demo: six Pendings, 699.90, after the 09-23 purge)."""
    Pending = dj_apps.get_model('core', 'Pending')
    Cash = dj_apps.get_model('transactions', 'Cash')
    Invoice = dj_apps.get_model('transactions', 'Invoice')
    Receipt = dj_apps.get_model('transactions', 'Receipt')
    cash_ids = set(Cash.objects.values_list('pk', flat=True))
    docs = {'invoice_id': set(Invoice.objects.values_list('pk', flat=True)),
            'receipt_id': set(Receipt.objects.values_list('pk', flat=True))}
    findings = []
    for p in (Pending.objects.filter(purpose__in=CASH_PURPOSES, changes__state='applied')
              .only('id', 'changes').order_by('pk')):
        c = p.changes or {}
        gone = []
        if c.get('cash_id') is not None and int(c['cash_id']) not in cash_ids:
            gone.append(f"cash {c['cash_id']}")
        for key, ids in docs.items():
            if c.get(key) is not None and int(c[key]) not in ids:
                gone.append(f"{key.removesuffix('_id')} {c[key]}")
        if gone:
            findings.append(_finding(
                'pending.orphan', 'pending', p.pk,
                f"pending {p.pk} applied {_d(c.get('amount'))} to {', '.join(gone)}, which no longer exist",
                have=_d(c.get('amount')), expect=Decimal(0)))
    return findings


def check_cash(org_id=None) -> tuple[list, dict]:
    """Every customer and vendor with documents or cash: the in_step invariants."""
    from apps.accounts.services.ledger_balance import compute_org_summary, compute_vendor_summary
    Invoice = dj_apps.get_model('transactions', 'Invoice')
    Receipt = dj_apps.get_model('transactions', 'Receipt')
    Cash = dj_apps.get_model('transactions', 'Cash')

    def ids(qs, field):
        qs = qs.exclude(**{f'{field}__isnull': True})
        if org_id:
            qs = qs.filter(**{field: org_id})
        return set(qs.values_list(field, flat=True).distinct())

    findings = (check_cash_available(org_id) + check_document_settlement(org_id)
                + check_ledger_rows(org_id))
    if not org_id:
        findings += check_orphan_applications()
    customers = ids(Invoice.objects, 'customer_id') | ids(Cash.objects, 'customer_id')
    vendors = ids(Receipt.objects, 'vendor_id') | ids(Cash.objects, 'vendor_id')
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
        elif area == 'cash':
            cash_id = (pending.changes or {}).get('cash_id') if isinstance(pending.changes, dict) else None
            # The org check already includes the org's cash; a cash with no party is
            # checked on its own (wc_demo 58–60 had none, so nothing ever looked).
            Cash = dj_apps.get_model('transactions', 'Cash')
            if target:
                findings = check_cash(target['org_id'])[0]
            elif cash_id and Cash.objects.filter(pk=cash_id).exists():
                findings = check_cash_available(cash_id=cash_id)
            else:                                     # the cash is gone: say so, never "balanced"
                findings = [_finding('event.unscoped', pending.model_name, pending.record_id,
                                     f"pending {pending.pk}: cash {cash_id} not found")]
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

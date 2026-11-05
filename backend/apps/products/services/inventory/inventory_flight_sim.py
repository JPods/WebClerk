"""
Flight Simulator: Inventory — Interactive training for inventory flows.

Shows how quantities, pending records, and GL entries change at each
stage of a transaction lifecycle. The user walks through:

  1. Starting inventory (item with on_hand=100)
  2. Add Quote for 15 units → on_qt changes, NO GL
  3. Convert 9 to Order → on_qt decreases, on_so increases, pending created, NO GL
  4. Create Invoice for 4 → on_so decreases, on_hand decreases, GL: AR/Revenue/COGS/Inventory + Tax + Commission
  5. Create Purchase for 14 → on_po increases, NO GL
  6. Receive 11 from Purchase → on_po decreases, on_hand increases, GL: Inventory/AP
  7. Partial payment on invoice → GL: Cash/AR (partial amount)
  8. Discount on remaining → GL: Discount/AR
  9. Write-off small balance → GL: Bad Debt/AR

Tax and shipping come from operational records, never from constants here
(Bill, 2026-09-19): the tax jurisdiction SIM_TAX_JURISDICTION (test_8%) and the
carrier SIM_SHIP_VIA (test_4%, 4% of goods). 8% is 2 × 4%, so a doubling error
shows at a glance. Commission: 5% of revenue (scenario assumption).
"""
from __future__ import annotations

import logging
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.apps import apps as dj_apps

logger = logging.getLogger(__name__)


def _now_ms():
    return int(time.time() * 1000)


# GL accounts for the simulator's postings, by the keys its scenarios use.
# Resolved from the company GL role map, so the simulator teaches the same
# accounts the real journals post to.
_SIM_GL_ROLES = {
    'ar': 'accounts_receivable',
    'cash': 'undeposited_funds',
    'revenue': 'sales_revenue',
    'cogs': 'cost_of_goods_sold',
    'inventory': 'inventory',
    'ap': 'accounts_payable',
    'tax_payable': 'sales_tax_payable',
    'commission_exp': 'commission_expense',
    'commission_pay': 'commission_payable',
    'discount': 'discount_given',
    'shipping': 'shipping_revenue',
    'bad_debt': 'bad_debt_writeoff',
    'scrap': 'scrap',
}


def _gl_defaults() -> Dict[str, str]:
    from apps.accounts.services.chart import role_account
    return {key: role_account(role, used_by='flight simulator') for key, role in _SIM_GL_ROLES.items()}


SIM_TAX_JURISDICTION = 'test_8%'     # TaxJurisdiction.tax_jurisdiction (seed_tax_jurisdictions)
SIM_SHIP_VIA = 'test_4%'             # wc:shipping_service entry (seed_shipping_service)
COMMISSION_RATE = Decimal('0.05')    # 5% — scenario assumption until the demo rep carries it

CENT = Decimal('0.01')


def _r2(x: Decimal) -> Decimal:
    return x.quantize(CENT)


def sim_rates() -> Dict[str, Any]:
    """The simulator's tax and shipping, read from the records a user would apply."""
    from apps.transactions.services.fulfillment.fulfillment_freight import shipping_service_for
    TaxJurisdiction = dj_apps.get_model('accounts', 'TaxJurisdiction')
    tj = TaxJurisdiction.objects.filter(tax_jurisdiction=SIM_TAX_JURISDICTION).first()
    svc = shipping_service_for(SIM_SHIP_VIA) or {}
    if tj is None or svc.get('rate_method') != 'percent_of_goods':
        raise ValueError(
            f"Flight simulator needs tax jurisdiction {SIM_TAX_JURISDICTION} and carrier {SIM_SHIP_VIA}: "
            "run seed_tax_jurisdictions and seed_shipping_service.")
    return {
        'tax_jurisdiction': SIM_TAX_JURISDICTION,
        'tax_name': tj.tax_name,
        'tax_rate': Decimal(str(tj.tax_rate_sales or 0)),
        'ship_via': SIM_SHIP_VIA,
        'shipping_rate': Decimal(str(svc.get('rate_percent') or 0)) / 100,
    }


def _money_breakdown(qty: int, unit_price: Decimal, rates: Dict[str, Any]) -> Dict[str, Decimal]:
    goods = _r2(unit_price * qty)
    shipping = _r2(goods * rates['shipping_rate'])
    tax = _r2(goods * rates['tax_rate'])            # shipping not taxed (company tax_policy default)
    return {'goods': goods, 'shipping': shipping, 'tax': tax, 'total': goods + shipping + tax}


def _pct(rate: Decimal) -> str:
    return f"{(rate * 100).normalize():f}%"

# Training items carry this ida prefix. reset_flight_simulator deletes
# transaction lines and headers, so it will only touch items named this way.
TRAINING_IDA_PREFIX = 'qq'


def reset_flight_simulator(item_ida: str) -> Dict[str, Any]:
    """Reset an item and all its training data to clean state.

    Called when the user clicks a simulation card (fresh start).
    Deletes all training transactions, lines, and pending records
    for this item, then resets quantity to on_hand=100, everything else 0.

    Refuses any item whose ida does not carry the training prefix. This is
    destructive on real records — it deletes every line referencing the item
    and any header those lines leave empty — so the prefix is the only thing
    standing between a mis-typed ida and live data.
    """
    if not str(item_ida or '').lower().startswith(TRAINING_IDA_PREFIX):
        return {
            'error': (
                f"refusing to reset '{item_ida}': the flight simulator only resets "
                f"training items, whose ida starts with '{TRAINING_IDA_PREFIX}'. "
                f"Resetting a real item would delete its transaction lines and any "
                f"header left empty. Run the simulation in watch-only mode instead."
            ),
            'refused': True,
            'item_ida': item_ida,
        }

    Item = dj_apps.get_model('products', 'Item')
    Pending = dj_apps.get_model('core', 'Pending')
    Quote = dj_apps.get_model('transactions', 'Quote')
    Order = dj_apps.get_model('transactions', 'Order')
    Invoice = dj_apps.get_model('transactions', 'Invoice')

    try:
        item = Item.objects.get(ida=item_ida)
    except Item.DoesNotExist:
        return {'error': f'Item with ida={item_ida} not found'}

    item_id = item.pk

    # Delete all pending records for this item
    p_del = Pending.objects.filter(record_id=str(item_id)).delete()

    # Collect parent header IDs from lines, then delete lines and orphaned headers
    line_configs = [
        ('transactions', 'QuoteLine', 'quote_id', 'transactions', 'Quote'),
        ('transactions', 'OrderLine', 'order_id', 'transactions', 'Order'),
        ('transactions', 'InvoiceLine', 'invoice_id', 'transactions', 'Invoice'),
        ('transactions', 'PurchaseLine', 'purchase_id', 'transactions', 'Purchase'),
        ('transactions', 'WorkOrderLine', 'workorder_id', 'transactions', 'WorkOrder'),
    ]
    lines_deleted = 0
    headers_deleted = 0
    for line_app, line_model, fk_field, header_app, header_model in line_configs:
        try:
            LineModel = dj_apps.get_model(line_app, line_model)
            lines_qs = LineModel.objects.filter(item_fk_id=item_id)
            # Collect parent IDs before deleting
            parent_ids = set(lines_qs.values_list(fk_field, flat=True))
            count, _ = lines_qs.delete()
            lines_deleted += count
            # Delete parent headers that now have zero lines
            if parent_ids:
                HeaderModel = dj_apps.get_model(header_app, header_model)
                for pid in parent_ids:
                    remaining = LineModel.objects.filter(**{fk_field: pid}).count()
                    if remaining == 0:
                        HeaderModel.objects.filter(pk=pid).delete()
                        headers_deleted += 1
        except LookupError:
            pass

    # Reset item quantity
    item.quantity = {
        'on_qt': 0, 'on_po': 0, 'on_so': 0, 'on_wo': 0,
        'on_hand': 100, 'allocated': 0, 'available': 100,
    }
    item.save(update_fields=['quantity'])

    return {
        'success': True,
        'item_id': item_id,
        'item_ida': item_ida,
        'quantity': item.quantity,
        'pending_deleted': p_del[1].get('core.Pending', 0) if isinstance(p_del[1], dict) else 0,
        'lines_deleted': lines_deleted,
        'headers_deleted': headers_deleted,
    }


def _recompute_available(state: Dict[str, Any]) -> None:
    """Set state['available'] using the production formula, in place.

    The simulator must not carry its own inventory arithmetic. It previously
    used `available = on_hand`, which ignores allocation and so taught a rule
    the system does not follow. available_from_quantity() is the same function
    Item._normalize_quantity uses to write the stored value.
    """
    from apps.products.services.inventory.inventory_available import (
        available_from_quantity,
    )

    computed = available_from_quantity(state)
    if computed is not None:
        state['available'] = computed


def get_flight_transactions(item_id: int, since: Optional[int] = None) -> Dict[str, Any]:
    """Build the transaction display — three rows per event.

    since: epoch ms (UTC). When set, only lines and pending records created at
    or after it are shown, and the first row is the item's state at that
    moment. A fresh simulation passes its start time so the panels begin
    empty instead of replaying the item's whole history.

    Row pattern:
      1. item          — starting state (or state after previous event)
      2. transaction   — the line that was saved (cause)
      3. pending       — the pending record created by the line (mechanism)
      4. item          — item.quantity after pending applied (effect)

    The first row is always the initial item state (before any events).
    Running totals are reconstructed by walking pending deltas forward.
    """
    # Displayed columns. 'allocated' is carried in the running state (no pending
    # delta touches it) because the production availability formula needs it —
    # it is not displayed.
    COLUMNS = ['on_hand', 'on_so', 'on_po', 'on_qt', 'on_wo', 'available']
    STATE_COLUMNS = COLUMNS + ['allocated']

    Item = dj_apps.get_model('products', 'Item')
    Pending = dj_apps.get_model('core', 'Pending')

    try:
        item = Item.objects.get(pk=item_id)
    except Item.DoesNotExist:
        return {'error': f'Item {item_id} not found'}

    quantity = item.quantity if isinstance(item.quantity, dict) else {}
    current_state = {col: _dec(quantity.get(col, 0)) for col in STATE_COLUMNS}
    item_dict = {
        'id': item.pk,
        'ida': item.ida,
        'name': str(item),
        'quantity': current_state,
    }

    # ── Gather transaction lines ─────────────────────────────────────
    tx_lines = []
    line_models = [
        ('transactions', 'QuoteLine', 'quote'),
        ('transactions', 'OrderLine', 'order'),
        ('transactions', 'InvoiceLine', 'invoice'),
        ('transactions', 'PurchaseLine', 'purchase'),
        ('transactions', 'WorkOrderLine', 'workorder'),
        # A receipt is where purchased goods land and the payable is born (2026-10-27: the
        # console journalizes the invoice, its cash and the receipt).
        ('transactions', 'ReceiptLine', 'receipt'),
    ]
    for app, model_name, parent_model in line_models:
        try:
            LineModel = dj_apps.get_model(app, model_name)
        except LookupError:
            continue
        line_qs = LineModel.objects.filter(
            item_fk_id=item_id, is_active=True
        )
        if since is not None:
            line_qs = line_qs.filter(dt_created__gte=since)
        for line in line_qs.select_related(parent_model).order_by('dt_created'):
            qty = _line_active_qty(line)
            parent_obj = getattr(line, parent_model, None)
            parent_ida = getattr(parent_obj, 'ida', '') if parent_obj else ''
            parent_id = getattr(line, f'{parent_model}_id', None)
            # One row per transaction + line: the document and the line on it
            # are one event. The inventory change is the pending record's row.
            tx_lines.append({
                'type': f'{parent_model}_line',
                # The ida carries the document type (1023-inv), so it is the whole label.
                'label': f'{parent_ida} × {_fmt_qty(qty)}',
                'hint': f'{parent_model} line {line.pk}: {_fmt_qty(qty)} × {item.ida}',
                'model': parent_model,
                'record_id': parent_id,
                'ida': parent_ida,
                'line_id': line.pk,
                'qty': qty,
                'dt': getattr(line, 'dt_created', 0) or 0,
            })

    # ── Gather pending records ───────────────────────────────────────
    pending_list = []
    pending_qs = Pending.objects.filter(model_name='item', record_id=str(item_id))
    if since is not None:
        pending_qs = pending_qs.filter(dt_created__gte=since)
    for p in pending_qs.order_by('dt_created'):
        data = p.changes if isinstance(p.changes, dict) else {}
        deltas = {}
        for col in COLUMNS:
            v = float(data.get(col, 0) or 0)
            if v != 0:
                deltas[col] = v
        pending_list.append({
            'type': 'pending',
            'id': p.pk,
            'ida': p.ida or str(p.pk),
            'reason': data.get('reason') or '',
            'doc_id': data.get('doc_id') or '',
            'purpose': p.purpose or '',
            'name': p.name or '',
            'deltas': deltas,
            'processed': p.is_processed(),
            'line_id': data.get('line_id'),
            'dt': getattr(p, 'dt_created', 0) or 0,
        })

    # ── Pair lines with their pending records ────────────────────────
    # Sort both by dt_created, then interleave: line → pending → state
    tx_lines.sort(key=lambda x: x['dt'])
    pending_list.sort(key=lambda x: x['dt'])

    # ── Compute initial state by reverse-walking ─────────────────────
    # Start from current item.quantity, subtract all pending deltas
    # to get back to the state before any transactions.
    initial = dict(current_state)
    for p in pending_list:
        if p['processed']:
            for col, delta in p['deltas'].items():
                initial[col] = initial.get(col, 0) - delta
    # Availability comes from the production formula, never a local one.
    _recompute_available(initial)

    # ── Build rows ───────────────────────────────────────────────────
    rows: List[Dict[str, Any]] = []
    running = dict(initial)

    # Row 1: initial item state
    rows.append({
        'type': 'item',
        'label': f'{item_dict["ida"]}',
        'values': {col: int(running[col]) for col in COLUMNS},
    })

    # Merge lines and pending by timestamp
    all_events = []
    for tx in tx_lines:
        all_events.append(('line', tx))
    for p in pending_list:
        all_events.append(('pending', p))
    all_events.sort(key=lambda x: (x[1]['dt'], 0 if x[0] == 'line' else 1))

    for kind, event in all_events:
        if kind == 'line':
            # Transaction line row (cause)
            rows.append({
                'type': event['type'],
                'label': event['label'],
                'model': event['model'],
                'record_id': event.get('record_id'),
                'ida': event.get('ida', ''),
                'hint': event['hint'],
                'values': {'qty': event['qty']},
            })
        elif kind == 'pending':
            # Pending row (mechanism) — show deltas
            display_deltas = {}
            for col, v in event['deltas'].items():
                display_deltas[col] = f'+{int(v)}' if v > 0 else f'{int(v)}'
            # Pending row (mechanism) — a separate record from the line. It
            # carries the inventory change; the line only carries the quantity.
            reason = event['reason'] or event['name'] or event['purpose']
            source = f' ← {event["doc_id"]}' if event['doc_id'] else ''
            rows.append({
                'type': 'pending',
                'label': f'Pending {event["ida"]}',
                'hint': f'{reason}{source}',
                'model': 'pending',
                'record_id': event['id'],
                'values': display_deltas,
                'processed': event['processed'],
            })
            # Item state row (effect) — running totals after this pending
            if event['processed']:
                for col, delta in event['deltas'].items():
                    running[col] = running.get(col, 0) + delta
                _recompute_available(running)
            rows.append({
                'type': 'item',
                'label': item_dict['ida'],
                'values': {col: int(running[col]) for col in COLUMNS},
            })

    # ── Cash and GL rows ───────────────────────────────────────────
    # These are separate sections of the display. A failure in either must not
    # take the quantity rows with it: this function previously raised whenever
    # the cash model could not be resolved, so the Counts panel rendered
    # empty and the reason never reached the screen. Failures are reported in
    # 'warnings' rather than swallowed.
    warnings: List[str] = []

    try:
        cash_rows = _get_cash_rows(tx_lines)
    except Exception as exc:
        logger.exception('flight sim: cash rows failed')
        cash_rows = []
        warnings.append(f'Money rows unavailable: {exc}')

    return {
        'columns': COLUMNS,
        'rows': rows,
        'cash_rows': cash_rows,
        'item': item_dict,
        'row_count': len(rows),
        'warnings': warnings,
    }


def get_flight_by_invoice(invoice_ida: str) -> Dict[str, Any]:
    """Audit mode — enter an invoice number, see inventory, cash, and GL.

    Finds the invoice, gets its line items, finds the item(s),
    then returns the same 3-section data as get_flight_transactions.
    """
    Invoice = dj_apps.get_model('transactions', 'Invoice')
    InvoiceLine = dj_apps.get_model('transactions', 'InvoiceLine')

    # Find invoice by ida, partial ida, or numeric id
    invoice = None
    # Exact ida match
    invoice = Invoice.objects.filter(ida=invoice_ida).first()
    if not invoice:
        # The number people type: "1023" matches "1023-inv" (and "1023-inv-qq")
        invoice = Invoice.objects.filter(ida__istartswith=f'{invoice_ida}-').order_by('ida').first()
    if not invoice:
        # Record id as a last resort
        try:
            invoice = Invoice.objects.filter(pk=int(invoice_ida)).first()
        except (ValueError, TypeError):
            pass
    if not invoice:
        # Try ida containing the input
        invoice = Invoice.objects.filter(ida__icontains=invoice_ida).first()
    if not invoice:
        return {'error': f'Invoice "{invoice_ida}" not found'}

    # Get item IDs from invoice lines — check FK first, then JSON envelope
    lines = InvoiceLine.objects.filter(invoice=invoice, is_active=True)
    item_ids = set()
    for line in lines:
        if line.item_fk_id:
            item_ids.add(line.item_fk_id)
        else:
            # Fallback: item_id in JSON item field
            item_data = getattr(line, 'item', None)
            if isinstance(item_data, dict) and item_data.get('item_id'):
                item_ids.add(int(item_data['item_id']))
    item_ids = list(item_ids)

    if not item_ids:
        return {'error': f'Invoice {invoice.ida} has no line items with identifiable products'}

    # Use first item for the inventory display (most common case: single-item invoice)
    # For multi-item invoices, we still show all cash and GL for the whole invoice
    primary_item_id = item_ids[0]

    # Get the standard flight transactions for the item
    result = get_flight_transactions(primary_item_id)
    if result.get('error'):
        return result

    # Add invoice-specific context
    result['audit_mode'] = True
    result['invoice'] = {
        'id': invoice.pk,
        'ida': invoice.ida,
        'status': getattr(invoice, 'status', ''),
        'total': float(getattr(invoice, 'total', 0) or 0),
    }
    result['item_count'] = len(item_ids)

    return result


def _applied_to(changes: Dict[str, Any]) -> str:
    """The document a cash application names, by its ida: 'invoice 1054-inv', 'receipt 19'."""
    for model in ('invoice', 'receipt'):
        doc_id = changes.get(f'{model}_id')
        if doc_id:
            doc = dj_apps.get_model('transactions', model.title()).objects.filter(pk=doc_id).first()
            return f'{model} {(doc.ida if doc else "") or f"#{doc_id}"}'
    return 'unapplied'


def _get_cash_rows(tx_lines: list) -> List[Dict[str, Any]]:
    """Build cash display rows from transaction lines.

    Finds all invoices/orders linked to the item's transaction lines,
    then finds cash and cash application pending records.
    """
    Cash = dj_apps.get_model('transactions', 'Cash')
    Pending = dj_apps.get_model('core', 'Pending')

    # Collect parent invoice and order IDs from transaction lines
    invoice_ids = set()
    order_ids = set()
    receipt_ids = set()
    for tx in tx_lines:
        if tx['type'] == 'invoice_line' and tx.get('record_id'):
            invoice_ids.add(tx['record_id'])
        elif tx['type'] == 'order_line' and tx.get('record_id'):
            order_ids.add(tx['record_id'])
        elif tx['type'] == 'receipt_line' and tx.get('record_id'):
            receipt_ids.add(tx['record_id'])

    if not invoice_ids and not order_ids and not receipt_ids:
        return []

    # Find cash linked to these invoices or orders
    from django.db.models import Q
    q = Q()
    if invoice_ids:
        q |= Q(invoice_id__in=invoice_ids)
        q |= Q(parent_model='invoice', parent_id__in=invoice_ids)
    if order_ids:
        q |= Q(parent_model='order', parent_id__in=order_ids)
    if receipt_ids:
        q |= Q(receipt_id__in=receipt_ids)          # paying the vendor for what was received

    cash_entries = Cash.objects.filter(q, is_active=True).order_by('dt_created')

    rows = []
    for pay in cash_entries:
        amount = float(pay.amount or 0)
        available = float(pay.available or 0)
        applied = amount - available
        method = getattr(pay, 'method', '') or ''
        status = getattr(pay, 'status', '') or ''

        rows.append({
            'type': 'cash',
            'label': f'Cash {pay.ida or f"#{pay.pk}"}',
            'model': 'cash',
            'record_id': pay.pk,
            'values': {
                'amount': f'${amount:.2f}',
                'applied': f'${applied:.2f}' if applied else '',
                'available': f'${available:.2f}',
                'method': method,
                'status': status,
            },
        })

        # This cash's applications: the Pendings that name it.
        pay_pending = Pending.objects.filter(
            purpose='cash_application', changes__cash_id=pay.pk).order_by('dt_created')

        for pp in pay_pending:
            changes = pp.changes if isinstance(pp.changes, dict) else {}
            app_amount = float(changes.get('amount', 0) or 0)
            state = changes.get('state', 'pending')
            rows.append({
                'type': 'cash_application',
                # Named by the document number people know (1054-inv), not its record id: an
                # invoice showing $0 open seemed to have no payments, because they read
                # "→ Invoice #160" (Bill, 2026-10-27).
                'label': f'  Apply ${app_amount:.2f} → {_applied_to(changes)}',
                'values': {
                    'amount': f'-${app_amount:.2f}',
                    'applied': f'${app_amount:.2f}',
                    'available': '',
                    'method': '',
                    'status': state,
                },
                'processed': state == 'applied',
            })

    return rows


def get_item_by_ida(ida: str) -> Dict[str, Any]:
    """Look up an item by ida and return its flight state."""
    Item = dj_apps.get_model('products', 'Item')
    try:
        item = Item.objects.get(ida=ida)
    except Item.DoesNotExist:
        return {'error': f'Item with ida={ida} not found'}
    return get_item_flight_state(item.pk)


def get_item_flight_state(item_id: int) -> Dict[str, Any]:
    """Return the complete flight state for an item — all lines, pending, GL impact.

    This is the real-time view. The flight simulator UI calls this after
    each user action to show what changed.
    """
    G = _gl_defaults()
    Item = dj_apps.get_model('products', 'Item')
    Pending = dj_apps.get_model('core', 'Pending')

    try:
        item = Item.objects.get(pk=item_id)
    except Item.DoesNotExist:
        return {'error': f'Item {item_id} not found'}

    quantity = item.quantity if isinstance(item.quantity, dict) else {}
    cost_data = item.cost if isinstance(item.cost, dict) else {}
    gls = item.gls if isinstance(getattr(item, 'gls', None), dict) else {}
    price_data = item.price if isinstance(item.price, dict) else {}

    item_dict = {
        'id': item.pk,
        'ida': item.ida,
        'name': str(item),
        'quantity': {
            'on_hand': _dec(quantity.get('on_hand', 0)),
            'on_so': _dec(quantity.get('on_so', 0)),
            'on_po': _dec(quantity.get('on_po', 0)),
            'on_qt': _dec(quantity.get('on_qt', 0)),
            'on_wo': _dec(quantity.get('on_wo', 0)),
            'allocated': _dec(quantity.get('allocated', 0)),
            'available': _dec(quantity.get('available', 0)),
            'on_rc': _dec(quantity.get('on_rc', 0)),
            'on_in': _dec(quantity.get('on_in', 0)),
        },
        'cost': {
            'standard': _dec(cost_data.get('standard', 0)),
            'last': _dec(cost_data.get('last', 0)),
            'avg': _dec(cost_data.get('average', cost_data.get('avg', 0))),
        },
        'price': {
            'base': _dec(price_data.get('base', 0)),
        },
        'gls': {
            'revenue': gls.get('revenue') or G['revenue'],
            'cogs': gls.get('cogs') or G['cogs'],
            'inventory': gls.get('inventory') or G['inventory'],
            'purchase': gls.get('purchase') or G['ap'],
        },
    }

    # Gather all transaction lines for this item
    lines = []
    lines.extend(_get_quote_lines(item_id, item_dict))
    lines.extend(_get_order_lines(item_id, item_dict))
    lines.extend(_get_invoice_lines(item_id, item_dict))
    lines.extend(_get_purchase_lines(item_id, item_dict))
    lines.extend(_get_workorder_lines(item_id, item_dict))

    # Sort by dt_created
    lines.sort(key=lambda x: x.get('dt_created') or 0)

    # Gather pending records
    pending = _get_pending_records(item_id)

    return {
        'item': item_dict,
        'lines': lines,
        'pending': pending,
        'sim_rates': {k: (float(v) if isinstance(v, Decimal) else v) for k, v in sim_rates().items()},
        'commission_rate': float(COMMISSION_RATE),
        'gl_accounts': G,
        'dt_generated': _now_ms(),
    }


def sim_header_defaults() -> Dict[str, Any]:
    """What the simulator puts on every document it creates (Bill, 2026-09-19): the test
    tax jurisdiction and carrier override the customer's normal defaults, so every run
    gives the same numbers. A user may change them back; the outcome then changes."""
    R = sim_rates()
    return {
        'ship_via': R['ship_via'],
        'finance': {'sales_tax_rate': float(R['tax_rate']), 'sales_tax_name': R['tax_name'],
                    'tax_jurisdiction': R['tax_jurisdiction']},
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _dec(val) -> float:
    """Safely convert a value to float."""
    try:
        return float(val or 0)
    except (TypeError, ValueError):
        return 0.0


def _get_quote_lines(item_id: int, item_dict: dict) -> list:
    """Get all quote lines for this item."""
    try:
        QuoteLine = dj_apps.get_model('transactions', 'QuoteLine')
    except LookupError:
        return []

    lines = []
    for pl in QuoteLine.objects.filter(item_fk_id=item_id, is_active=True):
        qty = _line_qty(pl)
        price = _line_price(pl)
        lines.append({
            'type': 'quote_line',
            'id': pl.pk,
            'parent_id': pl.quote_id,
            'parent_ida': getattr(pl.quote, 'ida', '') if hasattr(pl, 'quote') else '',
            'parent_model': 'quote',
            'quantity': qty,
            'price': price,
            'status': getattr(pl, 'status', ''),
            'dt_created': getattr(pl, 'dt_created', None),
            'gl_impact': {
                'has_impact': False,
                'reason': 'Quote — no GL impact (quote only)',
                'entries': [],
            },
        })
    return lines


def _get_order_lines(item_id: int, item_dict: dict) -> list:
    try:
        OrderLine = dj_apps.get_model('transactions', 'OrderLine')
    except LookupError:
        return []

    lines = []
    for ol in OrderLine.objects.filter(item_fk_id=item_id, is_active=True):
        qty = _line_qty(ol)
        price = _line_price(ol)
        lines.append({
            'type': 'order_line',
            'id': ol.pk,
            'parent_id': ol.order_id,
            'parent_ida': getattr(ol.order, 'ida', '') if hasattr(ol, 'order') else '',
            'parent_model': 'order',
            'quantity': qty,
            'price': price,
            'status': getattr(ol, 'status', ''),
            'dt_created': getattr(ol, 'dt_created', None),
            'gl_impact': {
                'has_impact': False,
                'reason': 'Order — no GL impact (commitment only)',
                'entries': [],
            },
        })
    return lines


def _get_invoice_lines(item_id: int, item_dict: dict) -> list:
    G = _gl_defaults()
    try:
        InvoiceLine = dj_apps.get_model('transactions', 'InvoiceLine')
    except LookupError:
        return []

    unit_cost = Decimal(str(item_dict['cost']['standard'] or item_dict['cost']['avg'] or 0))
    gl = item_dict['gls']

    lines = []
    for il in InvoiceLine.objects.filter(item_fk_id=item_id, is_active=True):
        qty = _line_qty(il)
        price = _line_price(il)
        active_qty = Decimal(str(qty.get('active', qty.get('staged', 0)) or 0))
        extended = Decimal(str((il.totals or {}).get('amount', 0) or 0))

        if extended == 0 and active_qty > 0:
            unit_price = Decimal(str(price.get('unit', price.get('base', 0)) or 0))
            extended = unit_price * active_qty

        line_totals = il.totals or {}
        tax_amount = Decimal(str(line_totals.get('tax', 0) or 0))          # the line's own tax
        shipping_amount = Decimal(str(line_totals.get('shipping', 0) or 0))
        ar_total = Decimal(str(line_totals.get('total', 0) or 0)) or (extended + tax_amount + shipping_amount)
        rate_pct = _pct(Decimal(str(line_totals.get('tax_rate', 0) or 0)))
        cogs_amount = unit_cost * active_qty
        commission_amount = (extended * COMMISSION_RATE).quantize(Decimal('0.01'))

        entries = []
        if extended > 0:
            entries = [
                {'account': G['ar'], 'side': 'debit',
                 'amount': float(ar_total), 'purpose': f'AR ({active_qty} × price + shipping + {rate_pct} tax)'},
                {'account': gl['revenue'], 'side': 'credit',
                 'amount': float(extended), 'purpose': f'Revenue ({active_qty} × unit price)'},
                {'account': G['tax_payable'], 'side': 'credit',
                 'amount': float(tax_amount), 'purpose': f'Sales Tax ({rate_pct} × ${float(extended)})'},
            ]
            if shipping_amount > 0:
                entries.append({'account': G['shipping'], 'side': 'credit',
                                'amount': float(shipping_amount), 'purpose': 'Shipping revenue'})
            if cogs_amount > 0:
                entries.extend([
                    {'account': gl['cogs'], 'side': 'debit',
                     'amount': float(cogs_amount), 'purpose': f'COGS ({active_qty} × ${float(unit_cost)})'},
                    {'account': gl['inventory'], 'side': 'credit',
                     'amount': float(cogs_amount), 'purpose': 'Inventory reduction'},
                ])
            if commission_amount > 0:
                entries.extend([
                    {'account': G['commission_exp'], 'side': 'debit',
                     'amount': float(commission_amount), 'purpose': f'Commission ({float(COMMISSION_RATE)*100}% × ${float(extended)})'},
                    {'account': G['commission_pay'], 'side': 'credit',
                     'amount': float(commission_amount), 'purpose': 'Commission payable to rep'},
                ])

        lines.append({
            'type': 'invoice_line',
            'id': il.pk,
            'parent_id': il.invoice_id,
            'parent_ida': getattr(il.invoice, 'ida', '') if hasattr(il, 'invoice') else '',
            'parent_model': 'invoice',
            'quantity': qty,
            'price': price,
            'status': getattr(il, 'status', ''),
            'dt_created': getattr(il, 'dt_created', None),
            'gl_impact': {
                'has_impact': extended > 0,
                'reason': 'Invoice — AR/Revenue/Tax/COGS/Inventory/Commission' if extended > 0 else 'Invoice — $0 line, no GL',
                'entries': entries,
            },
        })
    return lines


def _get_purchase_lines(item_id: int, item_dict: dict) -> list:
    G = _gl_defaults()
    try:
        PurchaseLine = dj_apps.get_model('transactions', 'PurchaseLine')
    except LookupError:
        return []

    gl = item_dict['gls']
    lines = []
    for pl in PurchaseLine.objects.filter(item_fk_id=item_id, is_active=True):
        qty = _line_qty(pl)
        cost = getattr(pl, 'cost', None) or getattr(pl, 'price', None) or {}
        if isinstance(cost, dict):
            cost_dict = cost
        else:
            cost_dict = {}
        extended = Decimal(str((pl.totals or {}).get('amount', 0) or 0))

        # PO line has no GL until received
        lines.append({
            'type': 'purchase_line',
            'id': pl.pk,
            'parent_id': pl.purchase_id,
            'parent_ida': getattr(pl.purchase, 'ida', '') if hasattr(pl, 'purchase') else '',
            'parent_model': 'purchase',
            'quantity': qty,
            'price': cost_dict,
            'status': getattr(pl, 'status', ''),
            'dt_created': getattr(pl, 'dt_created', None),
            'gl_impact': {
                'has_impact': False,
                'reason': 'Purchase Order — no GL impact until goods are received',
                'entries': [],
                'on_rc': [
                    {'account': gl['inventory'], 'side': 'debit',
                     'amount': float(extended), 'purpose': 'Inventory increase (when received)'},
                    {'account': G['ap'], 'side': 'credit',
                     'amount': float(extended), 'purpose': 'AP (owed to vendor, when received)'},
                ] if extended > 0 else [],
            },
        })
    return lines


def _get_workorder_lines(item_id: int, item_dict: dict) -> list:
    try:
        WorkOrderLine = dj_apps.get_model('transactions', 'WorkOrderLine')
    except LookupError:
        return []

    lines = []
    for wl in WorkOrderLine.objects.filter(item_fk_id=item_id, is_active=True):
        qty = _line_qty(wl)
        lines.append({
            'type': 'workorder_line',
            'id': wl.pk,
            'parent_id': wl.workorder_id if hasattr(wl, 'workorder_id') else None,
            'parent_ida': '',
            'parent_model': 'workorder',
            'quantity': qty,
            'price': {},
            'status': getattr(wl, 'status', ''),
            'dt_created': getattr(wl, 'dt_created', None),
            'gl_impact': {
                'has_impact': False,
                'reason': 'Work Order — GL impact on completion (BOM build)',
                'entries': [],
            },
        })
    return lines


def _get_pending_records(item_id: int) -> list:
    Pending = dj_apps.get_model('core', 'Pending')
    records = []
    for p in Pending.objects.filter(
        record_id=str(item_id),
    ).order_by('-dt_created')[:50]:
        records.append({
            'id': p.pk,
            'model_name': p.model_name or '',
            'purpose': p.purpose if hasattr(p, 'purpose') else (p.name or ''),
            'changes': p.changes if isinstance(p.changes, list) else [],
            'is_processed': p.is_processed(),
            'dt_created': getattr(p, 'dt_created', None),
            'dt_processed': p.dt_processed,
        })
    return records


def _line_active_qty(line) -> float:
    """Extract the active quantity from a line as a float."""
    qty = getattr(line, 'quantity', None)
    if isinstance(qty, dict):
        return float(qty.get('active', qty.get('staged', 0)) or 0)
    if isinstance(qty, (int, float)):
        return float(qty)
    return 0.0


def _fmt_qty(qty: float) -> str:
    """7.0 → '7', 2.5 → '2.5' — whole units read as whole numbers."""
    return str(int(qty)) if float(qty).is_integer() else str(qty)


def _line_qty(line) -> dict:
    """Extract quantity dict from a line, handling both dict and scalar."""
    qty = getattr(line, 'quantity', None)
    if isinstance(qty, dict):
        return qty
    if isinstance(qty, (int, float)):
        return {'active': float(qty), 'staged': float(qty)}
    return {}


def _line_price(line) -> dict:
    """Extract price dict from a line."""
    price = getattr(line, 'price', None)
    if isinstance(price, dict):
        return price
    return {}

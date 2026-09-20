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
    ]
    for app, model_name, parent_model in line_models:
        try:
            LineModel = dj_apps.get_model(app, model_name)
        except LookupError:
            continue
        line_qs = LineModel.objects.filter(
            item_fk_id=item_id, is_active=True, is_deleted=False
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

    try:
        gl_rows = _get_gl_rows(tx_lines)
    except Exception as exc:
        logger.exception('flight sim: GL rows failed')
        gl_rows = []
        warnings.append(f'GL rows unavailable: {exc}')

    return {
        'columns': COLUMNS,
        'rows': rows,
        'cash_rows': cash_rows,
        'gl_rows': gl_rows,
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
    lines = InvoiceLine.objects.filter(invoice=invoice, is_active=True, is_deleted=False)
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
    for tx in tx_lines:
        if tx['type'] == 'invoice_line' and tx.get('record_id'):
            invoice_ids.add(tx['record_id'])
        elif tx['type'] == 'order_line' and tx.get('record_id'):
            order_ids.add(tx['record_id'])

    if not invoice_ids and not order_ids:
        return []

    # Find cash linked to these invoices or orders
    from django.db.models import Q
    q = Q()
    if invoice_ids:
        q |= Q(invoice_id__in=invoice_ids)
        q |= Q(parent_model='invoice', parent_id__in=invoice_ids)
    if order_ids:
        q |= Q(parent_model='order', parent_id__in=order_ids)

    cash_entries = Cash.objects.filter(q, is_active=True, is_deleted=False).order_by('dt_created')

    rows = []
    for pay in cash_entries:
        amount = float(pay.amount or 0)
        available = float(pay.available or 0)
        applied = amount - available
        method = getattr(pay, 'method', '') or ''
        status = getattr(pay, 'status', '') or ''

        rows.append({
            'type': 'cash',
            'label': f'Cash #{pay.ida or pay.pk}',
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

        # Find cash application pending records
        pay_pending = Pending.objects.filter(
            purpose='cash_application',
            name__icontains=str(pay.pk),
        ).order_by('dt_created')

        # Also check by changes content
        if not pay_pending.exists():
            pay_pending = Pending.objects.filter(
                purpose='cash_application',
            ).order_by('dt_created')

        for pp in pay_pending:
            changes = pp.changes if isinstance(pp.changes, dict) else {}
            if changes.get('cash_id') != pay.pk:
                continue
            app_amount = float(changes.get('amount', 0) or 0)
            inv_id = changes.get('invoice_id')
            state = changes.get('state', 'pending')
            rows.append({
                'type': 'cash_application',
                'label': f'  Apply ${app_amount:.2f} → Invoice #{inv_id}',
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


def _get_gl_rows(tx_lines: list) -> List[Dict[str, Any]]:
    """Build GL journal display rows from transaction lines.

    Finds GlJournal entries linked to the item's invoices, cash, purchases.
    """
    try:
        GlJournal = dj_apps.get_model('accounts', 'GlJournal')
    except LookupError:
        return []

    # Collect source documents from transaction lines
    from django.db.models import Q
    q = Q()
    source_docs = set()
    for tx in tx_lines:
        if tx.get('record_id') and tx['type'] in ('invoice_line', 'order_line', 'purchase_line'):
            model = tx['type'].replace('_line', '')
            source_docs.add((model, tx['record_id']))
            q |= Q(source_model=model, source_id=tx['record_id'])

    # Also find GL entries for cash_entries linked to these invoices
    invoice_ids = {doc_id for model, doc_id in source_docs if model == 'invoice'}
    if invoice_ids:
        Cash = dj_apps.get_model('transactions', 'Cash')
        pay_ids = list(Cash.objects.filter(
            invoice_id__in=invoice_ids, is_active=True, is_deleted=False
        ).values_list('pk', flat=True))
        for pid in pay_ids:
            q |= Q(source_model='cash', source_id=pid)

    if not q:
        return []

    journals = GlJournal.objects.filter(q).order_by('dt_created')

    rows = []
    # Group by batch_id for cleaner display
    current_batch = None
    for gl in journals:
        batch = gl.batch_id or ''
        if batch != current_batch:
            current_batch = batch
            source_label = f'{gl.source_model or ""} #{gl.source_id or ""}'
            rows.append({
                'type': 'gl_header',
                'label': f'Journal: {batch or source_label}',
                'values': {},
            })

        debit = float(gl.debit or 0)
        credit = float(gl.credit or 0)
        rows.append({
            'type': 'gl_entry',
            'label': f'  {gl.account}',
            'values': {
                'debit': f'${debit:.2f}' if debit else '',
                'credit': f'${credit:.2f}' if credit else '',
                'source': f'{gl.source_model}',
            },
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


def get_flight_scenario() -> Dict[str, Any]:
    """Return the scripted training scenario with expected values at each step.

    This is the "lesson plan" — what the user should do and what they
    should see at each step. The UI walks through these steps.
    """
    G = _gl_defaults()
    unit_price = Decimal('10.00')
    unit_cost = Decimal('6.00')
    R = sim_rates()
    tax_pct, ship_pct = _pct(R['tax_rate']), _pct(R['shipping_rate'])
    b = _money_breakdown(4, unit_price, R)                  # the invoice for 4 units
    cogs = _r2(unit_cost * 4)
    commission = _r2(b['goods'] * COMMISSION_RATE)
    paid = Decimal('30.00')
    discount = Decimal('10.00')
    after_pay = b['total'] - paid
    write_off = after_pay - discount
    ret_goods = _r2(unit_price)
    ret_tax = _r2(ret_goods * R['tax_rate'])
    ret_credit = ret_goods + ret_tax                        # shipping on the order is not refunded
    m = lambda x: f"${x:,.2f}"

    steps = [
        {
            'step': 1,
            'title': 'Starting Inventory',
            'instruction': 'Select an item with on_hand = 100, price = $10.00, cost = $6.00',
            'action': None,
            'expected_quantity': {
                'on_hand': 100, 'on_so': 0, 'on_po': 0, 'on_qt': 0,
                'allocated': 0, 'available': 100,
            },
            'expected_gl': [],
            'explanation': 'No transactions yet. All 100 units are available.',
        },
        {
            'step': 2,
            'title': 'Create Quote for 15 units',
            'instruction': 'Create a Quote with 1 line: 15 units of this item at $10.00',
            'action': 'create_quote_line',
            'qty': 15,
            'expected_quantity': {
                'on_hand': 100, 'on_so': 0, 'on_po': 0, 'on_qt': 15,
                'allocated': 0, 'available': 100,
            },
            'expected_gl': [],
            'explanation': 'Quote reserves 15 units (on_qt=15). No GL impact — a quote is just a quote. Available stays 100 because quotes don\'t allocate.',
        },
        {
            'step': 3,
            'title': 'Convert 9 units to Order',
            'instruction': 'Create an Order from the Quote for 9 of the 15 units',
            'action': 'create_order_from_quote',
            'qty': 9,
            'expected_quantity': {
                'on_hand': 100, 'on_so': 9, 'on_po': 0, 'on_qt': 6,
                'allocated': 0, 'available': 100,
            },
            'expected_pending': [
                {'purpose': 'on_so', 'delta': '+9'},
                {'purpose': 'on_qt', 'delta': '-9'},
            ],
            'expected_gl': [],
            'explanation': (
                'Order commits 9 units (on_so=9). Quote drops to 6 remaining. Pending records track '
                'the movement. Still NO GL impact — an order is a commitment, not a financial event.\n\n'
                'Available stays 100. An order does NOT allocate: allocation is a salesperson\'s '
                'deliberate act, made by reading on_hand, available and on_so and deciding which '
                'goods are set aside for whom. available = on_hand − allocated, and nothing but a '
                'person moves allocated.'
            ),
        },
        {
            'step': 4,
            'title': 'Create Invoice for 4 units',
            'instruction': (f'Create an Invoice from the Order for 4 of the 9 units, with tax jurisdiction '
                            f'{R["tax_jurisdiction"]} ({tax_pct}) and ship via {R["ship_via"]} ({ship_pct} of goods)'),
            'action': 'create_invoice_from_order',
            'qty': 4,
            'expected_quantity': {
                'on_hand': 96, 'on_so': 5, 'on_po': 0, 'on_qt': 6,
                'allocated': 0, 'available': 96,
            },
            'expected_pending': [
                {'purpose': 'on_hand', 'delta': '-4'},
                {'purpose': 'on_so', 'delta': '-4'},
            ],
            'expected_gl': [
                {'account': G['ar'], 'side': 'debit', 'amount': float(b['total']),
                 'purpose': f"Accounts Receivable (goods {m(b['goods'])} + shipping {m(b['shipping'])} + tax {m(b['tax'])} = {m(b['total'])})"},
                {'account': G['revenue'], 'side': 'credit', 'amount': float(b['goods']),
                 'purpose': f"Revenue (4 × {m(unit_price)})"},
                {'account': G['shipping'], 'side': 'credit', 'amount': float(b['shipping']),
                 'purpose': f"Shipping revenue ({ship_pct} × {m(b['goods'])}, {R['ship_via']})"},
                {'account': G['tax_payable'], 'side': 'credit', 'amount': float(b['tax']),
                 'purpose': f"Sales Tax Payable ({tax_pct} × {m(b['goods'])}, {R['tax_jurisdiction']})"},
                {'account': G['cogs'], 'side': 'debit', 'amount': float(cogs),
                 'purpose': f"Cost of Goods Sold (4 × {m(unit_cost)})"},
                {'account': G['inventory'], 'side': 'credit', 'amount': float(cogs),
                 'purpose': 'Inventory reduction (4 units leave the shelf)'},
                {'account': G['commission_exp'], 'side': 'debit', 'amount': float(commission),
                 'purpose': f"Commission Expense ({_pct(COMMISSION_RATE)} × {m(b['goods'])} revenue)"},
                {'account': G['commission_pay'], 'side': 'credit', 'amount': float(commission),
                 'purpose': 'Commission Payable (owed to rep)'},
            ],
            'explanation': (
                'THIS is the financial event. Inventory leaves the shelf (on_hand 100→96). '
                'Order backlog drops (on_so 9→5). GL records the sale:\n'
                f"• AR debit {m(b['total'])} (what the customer owes: goods + shipping + tax)\n"
                f"• Revenue credit {m(b['goods'])} (what we earned on the goods)\n"
                f"• Shipping revenue credit {m(b['shipping'])} ({ship_pct} of goods, carrier {R['ship_via']})\n"
                f"• Tax payable credit {m(b['tax'])} ({tax_pct}, owed to the jurisdiction — 2 × shipping)\n"
                f"• COGS debit {m(cogs)} (cost of what we sold)\n"
                f"• Inventory credit {m(cogs)} (asset leaves the books)\n"
                f"• Commission expense {m(commission)} / payable {m(commission)} (owed to rep)"
            ),
        },
        {
            'step': 5,
            'title': 'Create Purchase for 14 units',
            'instruction': 'Create a Purchase Order for 14 units at $6.00 cost',
            'action': 'create_purchase',
            'qty': 14,
            'expected_quantity': {
                'on_hand': 96, 'on_so': 5, 'on_po': 14, 'on_qt': 6,
                'allocated': 0, 'available': 96,
            },
            'expected_pending': [
                {'purpose': 'on_po', 'delta': '+14'},
            ],
            'expected_gl': [],
            'explanation': 'PO commits to buy 14 units (on_po=14). No GL impact — a PO is a commitment to a vendor, not a financial event. The money hasn\'t moved yet.',
        },
        {
            'step': 6,
            'title': 'Receive 11 of 14 from Purchase',
            'instruction': 'Receive 11 units against the PO (partial receipt)',
            'action': 'receive_purchase',
            'qty': 11,
            'expected_quantity': {
                'on_hand': 107, 'on_so': 5, 'on_po': 3, 'on_qt': 6,
                'allocated': 0, 'available': 107,
            },
            'expected_pending': [
                {'purpose': 'on_hand', 'delta': '+11'},
                {'purpose': 'on_po', 'delta': '-11'},
            ],
            'expected_gl': [
                {'account': G['inventory'], 'side': 'debit', 'amount': 66.00,
                 'purpose': 'Inventory increase (11 × $6.00 — goods on the shelf)'},
                {'account': G['ap'], 'side': 'credit', 'amount': 66.00,
                 'purpose': 'Accounts Payable (we owe the vendor)'},
            ],
            'explanation': (
                'Goods arrive. Inventory increases (on_hand 96→107). PO backlog drops (on_po 14→3). '
                'GL records the receipt:\n'
                '• Inventory debit $66.00 (asset on the shelf)\n'
                '• AP credit $66.00 (we owe the vendor)\n'
                'Note: 3 units still on order (on_po=3).'
            ),
        },
        {
            'step': 7,
            'title': f"Partial Payment — {m(paid)} of {m(b['total'])} invoice",
            'instruction': f"Record a {m(paid)} cash against the {m(b['total'])} invoice",
            'action': 'partial_payment',
            'amount': float(paid),
            'expected_gl': [
                {'account': G['cash'], 'side': 'debit', 'amount': float(paid),
                 'purpose': 'Cash received'},
                {'account': G['ar'], 'side': 'credit', 'amount': float(paid),
                 'purpose': f"AR reduced (customer owes {m(after_pay)} remaining)"},
            ],
            'explanation': (
                f"Customer pays {m(paid)} of the {m(b['total'])} owed. No inventory change — this is purely financial.\n"
                f"• Cash debit {m(paid)} (money in the bank)\n"
                f"• AR credit {m(paid)} (reduce what they owe)\n"
                f"Remaining balance: {m(b['total'])} - {m(paid)} = {m(after_pay)}"
            ),
        },
        {
            'step': 8,
            'title': f"Discount — {m(discount)} off remaining balance",
            'instruction': f"Apply a {m(discount)} discount to the remaining {m(after_pay)} balance (a user's decision, recorded as theirs)",
            'action': 'discount',
            'amount': float(discount),
            'expected_gl': [
                {'account': G['discount'], 'side': 'debit', 'amount': float(discount),
                 'purpose': 'Discount given (expense — reduces margin)'},
                {'account': G['ar'], 'side': 'credit', 'amount': float(discount),
                 'purpose': f"AR reduced (customer now owes {m(write_off)})"},
            ],
            'explanation': (
                f"We give the customer a {m(discount)} discount. No inventory change.\n"
                f"• Discount expense debit {m(discount)} (cost of the discount)\n"
                f"• AR credit {m(discount)} (reduce what they owe)\n"
                f"Remaining balance: {m(after_pay)} - {m(discount)} = {m(write_off)}\n"
                'Note: This hits the Discount Expense account, NOT Revenue. '
                f"Revenue stays at {m(b['goods'])} — the discount is tracked separately so you can see margin erosion."
            ),
        },
        {
            'step': 9,
            'title': f"Write-off — dismiss {m(write_off)} remaining balance",
            'instruction': f"Write off the remaining {m(write_off)} as uncollectable (a user's decision, recorded as theirs)",
            'action': 'write_off',
            'amount': float(write_off),
            'exit_point': {
                'name': 'Invoice Settled',
                'summary': f"The invoice is fully settled: {m(paid)} cash + {m(discount)} discount + {m(write_off)} write-off = {m(b['total'])}. You can stop here or continue to see returns, aging, and orphan cleanup.",
            },
            'expected_gl': [
                {'account': G['bad_debt'], 'side': 'debit', 'amount': float(write_off),
                 'purpose': 'Bad Debt expense (cost of uncollectable)'},
                {'account': G['ar'], 'side': 'credit', 'amount': float(write_off),
                 'purpose': 'AR zeroed out (invoice fully settled)'},
            ],
            'explanation': (
                f"The {m(write_off)} remaining isn't worth chasing. Write it off.\n"
                f"• Bad Debt debit {m(write_off)} (expense — money we'll never collect)\n"
                f"• AR credit {m(write_off)} (balance now $0)\n"
                f"The invoice is now fully settled: {m(paid)} cash + {m(discount)} discount + {m(write_off)} write-off = {m(b['total'])}."
            ),
        },
        # ── Reverse Flow ─────────────────────────────────────────────
        {
            'step': 10,
            'title': 'Return 1 unit',
            'instruction': 'Customer returns 1 of the 4 invoiced units. Create a Credit Memo.',
            'action': 'create_return',
            'qty': 1,
            'section': 'Reverse Flow',
            'expected_quantity': {
                'on_hand': 108, 'on_so': 5, 'on_po': 3, 'on_qt': 6,
                'allocated': 0, 'available': 108,
            },
            'expected_pending': [
                {'purpose': 'on_hand', 'delta': '+1'},
            ],
            'expected_gl': [
                {'account': G['revenue'], 'side': 'debit', 'amount': float(ret_goods),
                 'purpose': f"Revenue reversal (1 × {m(unit_price)})"},
                {'account': G['tax_payable'], 'side': 'debit', 'amount': float(ret_tax),
                 'purpose': f"Sales tax reversal ({tax_pct} × {m(ret_goods)})"},
                {'account': G['ar'], 'side': 'credit', 'amount': float(ret_credit),
                 'purpose': f"Credit memo — customer is owed {m(ret_credit)} (shipping is not refunded)"},
                {'account': G['inventory'], 'side': 'debit', 'amount': 6.00,
                 'purpose': 'Inventory restored (1 × $6.00 — item back on shelf)'},
                {'account': G['cogs'], 'side': 'credit', 'amount': 6.00,
                 'purpose': 'COGS reversal (cost of returned unit)'},
            ],
            'explanation': (
                'Customer sends 1 unit back. The goods and their tax reverse; shipping already done does not:\n'
                f"• Revenue debit {m(ret_goods)} (we un-earn the sale)\n"
                f"• Tax debit {m(ret_tax)} (we un-collect the tax)\n"
                f"• AR credit {m(ret_credit)} (we now owe the customer a credit)\n"
                '• Inventory debit $6.00 (unit back on the shelf)\n'
                '• COGS credit $6.00 (cost reversal)\n'
                'On_hand goes from 107→108. The unit is physically back.'
            ),
        },
        {
            'step': 11,
            'title': 'Scrap returned item',
            'instruction': 'The returned unit is damaged. Create an inventory adjustment to scrap it.',
            'action': 'scrap_adjustment',
            'qty': 1,
            'section': 'Reverse Flow',
            'expected_quantity': {
                'on_hand': 107, 'on_so': 5, 'on_po': 3, 'on_qt': 6,
                'allocated': 0, 'available': 107,
            },
            'expected_pending': [
                {'purpose': 'on_hand', 'delta': '-1'},
            ],
            'expected_gl': [
                {'account': G['scrap'], 'side': 'debit', 'amount': 6.00,
                 'purpose': 'Scrap/loss expense (damaged goods — cost of 1 unit)'},
                {'account': G['inventory'], 'side': 'credit', 'amount': 6.00,
                 'purpose': 'Inventory reduction (scrapped unit leaves the books)'},
            ],
            'explanation': (
                'The returned item is damaged beyond resale. Scrap it.\n'
                '• Scrap expense debit $6.00 (loss on the damaged unit)\n'
                '• Inventory credit $6.00 (remove from asset)\n'
                'On_hand goes from 108→107. The unit is gone.\n'
                'This is a real cost — we got the item back but can\'t sell it. '
                'Alice tracks scrap rates by vendor and category.'
            ),
        },
        {
            'step': 12,
            'title': 'Refund customer',
            'instruction': f"Issue a refund cash of {m(ret_credit)} against the credit memo.",
            'action': 'refund_cash',
            'amount': float(ret_credit),
            'section': 'Reverse Flow',
            'exit_point': {
                'name': 'Returns Complete',
                'summary': 'Return processed, item scrapped, customer refunded. You can stop here or continue to see aging and orphan cleanup.',
            },
            'expected_gl': [
                {'account': G['ar'], 'side': 'debit', 'amount': float(ret_credit),
                 'purpose': 'Clear credit memo balance'},
                {'account': G['cash'], 'side': 'credit', 'amount': float(ret_credit),
                 'purpose': 'Cash outflow — refund to customer'},
            ],
            'explanation': (
                'Pay the customer what we owe from the credit memo.\n'
                f"• AR debit {m(ret_credit)} (clear the credit balance)\n"
                f"• Cash credit {m(ret_credit)} (money leaves the bank)\n"
                'The return cycle is now complete: item returned, scrapped, customer refunded.'
            ),
        },
        # ── Aging ─────────────────────────────────────────────────────
        {
            'step': 13,
            'title': 'Pay vendor — $66.00 AP',
            'instruction': 'Pay the $66.00 owed to the vendor for the 11 received units.',
            'action': 'vendor_cash',
            'amount': 66.00,
            'section': 'Settlement',
            'expected_gl': [
                {'account': G['ap'], 'side': 'debit', 'amount': 66.00,
                 'purpose': 'AP cleared — vendor paid'},
                {'account': G['cash'], 'side': 'credit', 'amount': 66.00,
                 'purpose': 'Cash outflow to vendor'},
            ],
            'explanation': (
                'We owe the vendor $66 from step 6 (11 units × $6.00). Pay it.\n'
                '• AP debit $66.00 (we no longer owe the vendor)\n'
                '• Cash credit $66.00 (money leaves the bank)\n'
                'AP is now zero. All vendor obligations settled.'
            ),
        },
        # ── Cleanup ───────────────────────────────────────────────────
        {
            'step': 14,
            'title': 'Cancel remaining quote (6 units)',
            'instruction': 'Cancel the 6 units still sitting on the original quote.',
            'action': 'cancel_quote_remainder',
            'qty': 6,
            'section': 'Cleanup',
            'expected_quantity': {
                'on_hand': 107, 'on_so': 5, 'on_po': 3, 'on_qt': 0,
                'allocated': 0, 'available': 107,
            },
            'expected_pending': [
                {'purpose': 'on_qt', 'delta': '-6'},
            ],
            'expected_gl': [],
            'explanation': (
                'The remaining 6 quote units are stale — cancel them.\n'
                'On_p drops from 6→0. No GL impact (quotes never had financial weight).\n'
                'This is housekeeping — orphan quotes clutter reports and confuse users.'
            ),
        },
        {
            'step': 15,
            'title': 'Close remaining SO (5) and PO (3)',
            'instruction': 'Close the 5 remaining order units and 3 remaining PO units.',
            'action': 'close_orphans',
            'section': 'Cleanup',
            'exit_point': {
                'name': 'Clean Books',
                'summary': 'All orphans cleared through close_transaction. Books are clean: '
                           'on_hand=107, available=107, no open commitments.',
            },
            'expected_quantity': {
                'on_hand': 107, 'on_so': 0, 'on_po': 0, 'on_qt': 0,
                'allocated': 0, 'available': 107,
            },
            'expected_pending': [
                {'purpose': 'on_so', 'delta': '-5'},
                {'purpose': 'on_po', 'delta': '-3'},
            ],
            'expected_gl': [],
            'explanation': (
                'Close the remaining open commitments:\n'
                '• SO: 5 units cancelled (on_so 5→0)\n'
                '• PO: 3 units cancelled (on_po 3→0)\n'
                'No GL — these were commitments, not financial events.\n'
                'Available stays 107 — commitments never touched it. Allocation is the only\n'
                'thing that reduces available, and only a person allocates.\n\n'
                'The books are clean. Every transaction from quote to cleanup '
                'is accounted for. No orphans, no dangling commitments.'
            ),
        },
    ]

    # Summary: what happened across the full lifecycle — every number computed
    revenue = b['goods'] - ret_goods
    net_cogs = cogs - _r2(unit_cost)
    gross_margin = revenue - net_cogs
    scrap = _r2(unit_cost)
    net_margin = gross_margin + b['shipping'] - commission - discount - write_off - scrap
    cash_out = _r2(unit_cost * 11) + ret_credit
    invoice_summary = {
        'invoice_total': float(b['total']),
        'breakdown': [
            {'source': 'Revenue', 'amount': float(b['goods'])},
            {'source': 'Shipping', 'amount': float(b['shipping'])},
            {'source': 'Sales Tax', 'amount': float(b['tax'])},
        ],
        'settlement': [
            {'method': 'Cash received', 'amount': float(paid)},
            {'method': 'Discount given', 'amount': float(discount)},
            {'method': 'Written off', 'amount': float(write_off)},
        ],
        'settlement_total': float(paid + discount + write_off),
        'margin_analysis': {
            'revenue': float(revenue),
            'cogs': float(net_cogs),
            'gross_margin': float(gross_margin),
            'shipping_revenue': float(b['shipping']),
            'commission': float(commission),
            'discount': float(discount),
            'bad_debt': float(write_off),
            'scrap': float(scrap),
            'refund_cash': float(ret_credit),
            'net_margin': float(net_margin),
            'margin_pct': float((net_margin / revenue * 100).quantize(Decimal('0.1'))) if revenue else 0.0,
            'note': (
                f"Net margin = gross margin {m(gross_margin)} + shipping {m(b['shipping'])} − commission {m(commission)} "
                f"− discount {m(discount)} − write-off {m(write_off)} − scrap {m(scrap)} = {m(net_margin)}. "
                'The return + scrap turned a thin profit into a loss. This is why Alice tracks erosion at every stage.'
            ),
        },
        'cash_position': {
            'cash_in': float(paid),
            'cash_out': float(cash_out),
            'net_cash': float(paid - cash_out),
            'note': f"We collected {m(paid)} and paid out {m(cash_out)} (vendor {m(_r2(unit_cost * 11))} + refund {m(ret_credit)}).",
        },
    }

    return {
        'steps': steps,
        'invoice_summary': invoice_summary,
        'config': {
            'unit_price': 10.00,
            'unit_cost': 6.00,
            'tax_jurisdiction': R['tax_jurisdiction'],
            'tax_rate': float(R['tax_rate']),
            'ship_via': R['ship_via'],
            'shipping_rate': float(R['shipping_rate']),
            'commission_rate': float(COMMISSION_RATE),
            'starting_on_hand': 100,
        },
        'gl_accounts': G,
    }


def get_cash_flight_scenario() -> Dict[str, Any]:
    """Cash Lifecycle flight scenario.

    Walks through the full cash flow that WC2 handled via Make_Payment,
    CashCreate, ApplyCash, and Ledger_PaySave:

      1. Create Order for 10 units at $10 = $100
      2. Invoice 6 of the 10 (tax jurisdiction test_8%, ship via test_4%)
      3. Accept cash of $80 (tendered $100 cash, change $20)
      4. Apply $50 of the $80 to the invoice
      5. Journal the cash (post GL entries)
      6. Check ledger — cash available $30, invoice balance = total − $50
      7. Apply the rest to close the invoice
      8. What remains of the $80 is unapplied, on account
    Every invoice amount is computed from the jurisdiction and carrier records.

    Key fields demonstrated: amount, available, tendered, change.
    Key behaviors: available decrements on apply, ledger tracks available not amount.
    """
    G = _gl_defaults()
    unit_price = Decimal('10.00')
    unit_cost = Decimal('6.00')
    R = sim_rates()
    tax_pct, ship_pct = _pct(R['tax_rate']), _pct(R['shipping_rate'])
    b = _money_breakdown(6, unit_price, R)
    cogs = _r2(unit_cost * 6)
    cash_amt, first = Decimal('80.00'), Decimal('50.00')
    balance = b['total'] - first
    left_after_first = cash_amt - first
    left_after_close = left_after_first - balance
    m = lambda x: f"${x:,.2f}"

    steps = [
        {
            'step': 1,
            'title': 'Create Order — 10 units × $10.00',
            'instruction': 'Create an Order with 10 units of the training item at $10.00 each. Total = $100.00.',
            'action': 'create_order',
            'qty': 10,
            'expected_cash': None,
            'expected_gl': [],
            'explanation': (
                'No financial event yet. The order is a commitment — 10 units reserved (on_so=10). '
                'No cash fields involved. No GL impact.'
            ),
        },
        {
            'step': 2,
            'title': 'Invoice 6 of 10 — partial shipment',
            'instruction': (f"Create an Invoice from the Order for 6 of the 10 units, tax jurisdiction {R['tax_jurisdiction']}, "
                            f"ship via {R['ship_via']}. Invoice total = {m(b['total'])} "
                            f"({m(b['goods'])} goods + {m(b['shipping'])} shipping ({ship_pct}) + {m(b['tax'])} tax ({tax_pct}))."),
            'action': 'create_invoice_from_order',
            'qty': 6,
            'expected_invoice': {
                'amount': float(b['goods']),
                'shipping': float(b['shipping']),
                'tax': float(b['tax']),
                'total': float(b['total']),
                'balance_due': float(b['total']),
            },
            'expected_gl': [
                {'account': G['ar'], 'side': 'debit', 'amount': float(b['total']),
                 'purpose': f"AR — customer owes {m(b['total'])}"},
                {'account': G['revenue'], 'side': 'credit', 'amount': float(b['goods']),
                 'purpose': f"Revenue — 6 × {m(unit_price)}"},
                {'account': G['shipping'], 'side': 'credit', 'amount': float(b['shipping']),
                 'purpose': f"Shipping — {ship_pct} × {m(b['goods'])}"},
                {'account': G['tax_payable'], 'side': 'credit', 'amount': float(b['tax']),
                 'purpose': f"Sales Tax — {tax_pct} × {m(b['goods'])}"},
                {'account': G['cogs'], 'side': 'debit', 'amount': float(cogs),
                 'purpose': f"COGS — 6 × {m(unit_cost)}"},
                {'account': G['inventory'], 'side': 'credit', 'amount': float(cogs),
                 'purpose': 'Inventory reduction'},
            ],
            'explanation': (
                f"THIS is the financial event. 6 units ship. Invoice created for {m(b['total'])}.\n"
                f"GL records the sale. AR = {m(b['total'])}. Revenue = {m(b['goods'])}. "
                f"Shipping = {m(b['shipping'])}. Tax = {m(b['tax'])} (2 × shipping).\n"
                'The remaining 4 units stay on the order (on_so=4).'
            ),
        },
        {
            'step': 3,
            'title': 'Accept Cash — $80 (tendered $100 cash)',
            'instruction': (
                'Create a Cash record:\n'
                '• amount = $80.00 (what they\'re paying)\n'
                '• tendered = $100.00 (what they handed over)\n'
                '• change = $20.00 (auto-computed)\n'
                '• available = $80.00 (auto-set = amount on creation)\n\n'
                'Do NOT apply it to the invoice yet. This is just accepting the money.'
            ),
            'action': 'create_cash',
            'amount': 80.00,
            'tendered': 100.00,
            'expected_cash': {
                'amount': 80.00,
                'available': 80.00,
                'tendered': 100.00,
                'change': 20.00,
                'status': 'completed',
            },
            'expected_gl': [
                {'account': G['cash'], 'side': 'debit', 'amount': 80.00,
                 'purpose': 'Cash received (amount, not tendered)'},
                {'account': G['ar'], 'side': 'credit', 'amount': 80.00,
                 'purpose': 'AR reduced by cash amount'},
            ],
            'explanation': (
                'Customer hands over $100 cash for an $80 cash. Change = $20.\n\n'
                'Key fields on Cash record:\n'
                '• amount = $80 — the real cash amount\n'
                '• tendered = $100 — what the customer physically gave\n'
                '• change = $20 — computed: tendered - amount\n'
                '• available = $80 — starts equal to amount, decrements as applied\n\n'
                'WC2 equivalent: [Cash]amount, [Cash]amountAvailable, '
                '[Cash]tendered, [Cash]change\n\n'
                'The cash exists but is NOT yet applied to the invoice. '
                'The customer has $80 on account.'
            ),
        },
        {
            'step': 4,
            'title': 'Apply $50 to Invoice',
            'instruction': (
                f"Apply $50 of the $80 cash to the {m(b['total'])} invoice.\n\n"
                'After this step:\n'
                '• Cash.available drops from $80 → $30\n'
                f"• Invoice balance drops from {m(b['total'])} → {m(balance)}\n"
                '• Ledger value_available updates to -$30 (tracks unapplied)\n'
                '• Pending application record created (purpose cash_application)'
            ),
            'action': 'apply_cash_to_invoice',
            'amount': 50.00,
            'expected_cash': {
                'amount': 80.00,
                'available': 30.00,
                'tendered': 100.00,
                'change': 20.00,
            },
            'expected_invoice': {
                'total': float(b['total']),
                'received': float(first),
                'balance_due': float(balance),
                'status': 'partially_paid',
            },
            'expected_gl': [],
            'explanation': (
                f"Partial application. We take $50 of the $80 and apply it to the {m(b['total'])} invoice.\n\n"
                'What changes:\n'
                '• Cash.available: $80 → $30 (decremented by apply amount)\n'
                '• Invoice.totals.received: $0 → $50\n'
                f"• Invoice.totals.balance: {m(b['total'])} → {m(balance)}\n"
                '• Invoice status: "sent" → "partially_paid"\n'
                '• Ledger value_available: -$80 → -$30 (on next cash save)\n\n'
                'What does NOT change:\n'
                '• Cash.amount stays $80 (immutable — the original cash)\n'
                '• Cash.tendered stays $100\n'
                '• Cash.change stays $20\n\n'
                'WC2: This is the ApplyCash dialog. The user picks invoices '
                'and allocates cash dollars across them. amountAvailable tracked '
                'how much was left to allocate.'
            ),
        },
        {
            'step': 5,
            'title': 'Journal the Cash',
            'instruction': (
                'Post the cash to the GL (user-initiated action).\n\n'
                'This creates GlJournal records from the staged metadata.gl_accounts.\n'
                'The cash is now locked — can only be reversed, not edited.'
            ),
            'action': 'post_gl',
            'expected_gl': [
                {'account': G['cash'], 'side': 'debit', 'amount': 80.00,
                 'purpose': 'Cash receipt — full cash amount'},
                {'account': G['ar'], 'side': 'credit', 'amount': 80.00,
                 'purpose': 'AR reduction — full cash amount'},
            ],
            'explanation': (
                'GL journals are created. The cash is now part of the permanent record.\n\n'
                'Note: GL posts the FULL cash amount ($80), not the applied amount ($50). '
                'The journal captures the cash event. The application captures the allocation. '
                'These are two different things:\n'
                '• Cash event: "Customer gave us $80" → GL\n'
                '• Allocation: "We applied $50 to Invoice #X" → Pending application record\n\n'
                'The ledger tracks available ($30) for aging and credit calculations. '
                'The GL tracks the full amount for financial statements.'
            ),
        },
        {
            'step': 6,
            'title': 'Check the Ledger',
            'instruction': (
                'Verify the ledger state for this customer. Ledger rows echo their primary records:\n\n'
                f"• Invoice ledger: value_original = +{m(b['total'])}, value_available = +{m(balance)} (echoes the invoice)\n"
                '• Cash ledger: value_original = -$80, value_available = -$30 (echoes the cash)\n\n'
                'Org financial.summary should show:\n'
                f"• receivable = {m(balance)} (open invoice balances) = receivable_ledger\n"
                '• unapplied_cash = $30 = unapplied_cash_ledger\n'
                f"• net = {m(balance)} − $30 = {m(balance - left_after_first)}; in_step = true\n"
                f"• customer balances.due = {m(balance)} (invoices only; unapplied cash is shown apart)"
            ),
            'action': 'check_ledger',
            'expected_ledger': {
                'invoice_value_original': float(b['total']),
                'invoice_value_available': float(balance),
                'cash_value_original': -80.00,
                'cash_value_available': -30.00,
                'net': float(balance - left_after_first),
            },
            'explanation': (
                'The ledger is the single source of truth for AR aging.\n\n'
                'WC2 equivalent: Ledger_TallyBal computed:\n'
                '• balanceDue from SUM(unAppliedValue) across all ledger records\n'
                '• balanceAvailableCashEntries from SUM(amountAvailable) on Cash\n'
                '• totalExposure = balanceDue + openOrders\n\n'
                'WC3 does the same in update_org_balances():\n'
                '• Reads all Ledger records for org → aging buckets\n'
                '• Reads Cash.available WHERE > 0 → available_cash_entries\n'
                '• total_exposure = balance_due + open_orders - available_cash_entries'
            ),
        },
        {
            'step': 7,
            'title': f"Apply remaining {m(balance)} — close the invoice",
            'instruction': (
                f"Apply {m(balance)} more of the cash to the invoice.\n\n"
                'After this step:\n'
                f"• Cash.available: $30 → {m(left_after_close)}\n"
                f"• Invoice balance: {m(balance)} → $0\n"
                '• Invoice status: "partially_paid" → "paid"\n'
                f"• {m(left_after_close)} remains unapplied on account"
            ),
            'action': 'apply_cash_to_invoice',
            'amount': float(balance),
            'expected_cash': {
                'amount': 80.00,
                'available': float(left_after_close),
            },
            'expected_invoice': {
                'total': float(b['total']),
                'received': float(b['total']),
                'balance_due': 0.00,
                'status': 'paid',
            },
            'explanation': (
                f"Invoice is fully paid. The {m(left_after_close)} remaining on the cash is unapplied.\n\n"
                'This is common in commerce: customer overpays, or pays a round number. '
                'The excess stays on account as available_cash_entries. It can be:\n'
                '• Applied to the next invoice\n'
                '• Refunded\n'
                '• Left on account as a credit\n\n'
                'WC2 tracked this with balanceAvailableCashEntries on Customer. '
                'WC3 tracks it with Cash.available and org.financial.available_cash_entries.'
            ),
        },
        {
            'step': 8,
            'title': 'Summary — the cash lifecycle',
            'instruction': 'Review what happened across all 7 steps.',
            'action': None,
            'exit_point': {
                'name': 'Cash Lifecycle Complete',
                'summary': (
                    f"Order $100 → Invoice {m(b['total'])} (partial) → Cash $80 (tendered $100, change $20) "
                    f"→ Apply $50 → Journal → Apply {m(balance)} → Invoice paid, {m(left_after_close)} on account."
                ),
            },
            'explanation': (
                'The four cash fields and their roles:\n\n'
                '| Field     | Created | After apply $50 | After apply $13 |\n'
                '|-----------|---------|-----------------|------------------|\n'
                '| amount    | $80     | $80             | $80              |\n'
                f"| available | $80     | $30             | {m(left_after_close):<16} |\n"
                '| tendered  | $100    | $100            | $100             |\n'
                '| change    | $20     | $20             | $20              |\n\n'
                'amount and tendered are immutable (what happened). '
                'available is the working field (what\'s left to allocate). '
                'change is computed (tendered - amount).\n\n'
                'The ledger tracks available, not amount. This is how WC2 worked '
                '(aLdgValue = -amountAvailable) and now WC3 matches.'
            ),
        },
    ]

    return {
        'steps': steps,
        'config': {
            'unit_price': 10.00,
            'unit_cost': 6.00,
            'tax_jurisdiction': R['tax_jurisdiction'],
            'tax_rate': float(R['tax_rate']),
            'ship_via': R['ship_via'],
            'shipping_rate': float(R['shipping_rate']),
            'starting_on_hand': 100,
        },
        'gl_accounts': G,
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
    for pl in QuoteLine.objects.filter(item_fk_id=item_id, is_active=True, is_deleted=False):
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
    for ol in OrderLine.objects.filter(item_fk_id=item_id, is_active=True, is_deleted=False):
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
    for il in InvoiceLine.objects.filter(item_fk_id=item_id, is_active=True, is_deleted=False):
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
    for pl in PurchaseLine.objects.filter(item_fk_id=item_id, is_active=True, is_deleted=False):
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
    for wl in WorkOrderLine.objects.filter(item_fk_id=item_id, is_active=True, is_deleted=False):
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

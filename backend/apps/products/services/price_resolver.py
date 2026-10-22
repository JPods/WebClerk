"""Pricing and costing — one behavior per side (Bill, 2026-10-22).

    resolve_price(item, customer_id, qty, level)  →  PriceResolution   (sell side)
    resolve_cost(item, basis)                     →  CostResolution    (buy side)

Each names the other's figure so users can see control: a price carries the cost it is
measured against and its margin; a cost carries the list price it feeds and the margin
left at list. Nothing else picks a price level or a cost basis — the browser asks the
server (manage action ``price_lines``), and every server path calls these two.

Sell cascade (first match wins; quantity breaks and a universal % ride on the level price):
  1. price_locked     — a manual price on the line; nothing else runs
  2. catalog line     — a catalog assigned to this customer with a line for this item
                        (by item, category, vendor or all_items; min/max qty)
  3. price level      — explicit (line/header) else the customer's price_level:
                        retail, wholesale, distributor or sample
       + qty break    — item.price.qty_breaks at the quantity
       + universal %  — a universal-% catalog assigned to this customer
  4. list price       — item.price.retail, else item.price.base
Then the margin floor: the catalog's margin_floor, else the company profile's
config.pricing.minimum_margin (15 when unset; 0 still flags a sale below cost).
Below the floor is flagged, never blocked — committing callers call flag_below_margin().

Cost basis: item.config.costing_method does not choose it (that values COGS); the
company profile inventory.unit_cost_default does — last, standard, avg or landed. An
item with nothing at that basis falls to standard, then to whatever cost it has (avg,
last, landed — a built item's BOM rollup lands in avg). A not-tracked item (labor,
freight) is always its standard rate.

Readme: apps/products/readmes/pricing_operations.md (flowchart + Alice coaching).
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)

CENT = Decimal('0.01')

#: The price levels — the only ones (Bill, 2026-10-22); each is an Item.price key.
PRICE_LEVELS = ('retail', 'wholesale', 'distributor', 'sample')

#: Which item cost a new line starts from (company profile inventory.unit_cost_default).
COST_BASES = ('last', 'standard', 'avg', 'landed')
DEFAULT_COST_BASIS = 'last'

DEFAULT_MINIMUM_MARGIN_PCT = Decimal('15')


# ---------------------------------------------------------------------------
# Price levels
# ---------------------------------------------------------------------------

def named_price_level(value) -> str:
    """A price level as stored: one of the four words (in any case, stored lowercase);
    blank stays blank. Anything else is refused, naming the four."""
    text = str(value or '').strip()
    if not text:
        return ''
    if text.lower() in PRICE_LEVELS:
        return text.lower()
    raise ValueError(f"Price level '{text}' is not a price level. "
                     f"Use one of: {', '.join(PRICE_LEVELS)} — or leave it blank for "
                     f"the customer's level.")


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

@dataclass
class PriceResolution:
    """A sell price and how it was reached — with the cost it is measured against."""
    price: Decimal                      # final unit price
    list_price: Decimal                 # item's list price (retail, else base)
    resolved_by: str                    # price_locked | catalog_line | price_level | list_price
    price_level: str = ''               # level word used ('' when none)
    qty_break: Optional[dict] = None    # the break applied, if any
    catalog_id: Optional[int] = None
    catalog_name: str = ''
    catalog_line_id: Optional[int] = None
    discount_pct: Decimal = Decimal('0')
    discount_amount: Decimal = Decimal('0')   # list_price - price, never negative
    unit_cost: Decimal = Decimal('0')   # the buy side's figure (resolve_cost)
    cost_basis: str = ''
    margin_pct: Optional[Decimal] = None      # (price - cost) / price
    margin_floor: Decimal = Decimal('0')
    below_margin_floor: bool = False
    price_locked: bool = False

    def as_dict(self) -> dict:
        return _plain(asdict(self))


@dataclass
class CostResolution:
    """A buy-side unit cost and its basis — with the list price it feeds."""
    unit: Decimal                       # unit cost a new line starts from
    basis: str                          # last | standard | avg | landed | none
    list_price: Decimal                 # the sell side's figure
    margin_pct: Optional[Decimal] = None      # margin left at list price

    def as_dict(self) -> dict:
        return _plain(asdict(self))


def _plain(d: dict) -> dict:
    return {k: (float(v) if isinstance(v, Decimal) else v) for k, v in d.items()}


def _dec(value) -> Optional[Decimal]:
    if value is None or value == '':
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _margin(price: Decimal, cost: Decimal) -> Optional[Decimal]:
    if price <= 0 or cost <= 0:
        return None
    return ((price - cost) / price * Decimal('100')).quantize(CENT, rounding=ROUND_HALF_UP)


def _item(item):
    if hasattr(item, 'price'):
        return item
    from apps.products.models.item import Item
    try:
        return Item.objects.get(pk=item)
    except Item.DoesNotExist:
        raise ValueError(f'Item #{item} not found')


def list_price(item) -> Decimal:
    """The item's list price — retail (level A), else base."""
    price = item.price if isinstance(item.price, dict) else {}
    for key in ('retail', 'base'):
        value = _dec(price.get(key))
        if value is not None and value > 0:
            return value
    return Decimal('0')


# ---------------------------------------------------------------------------
# Buy side
# ---------------------------------------------------------------------------

def _company_config(section: str) -> dict:
    from apps.core.models import Setting
    company = Setting.objects.filter(purpose='wc:company_profile', is_active=True).first()
    out = company.config.get(section, {}) if company and isinstance(company.config, dict) else {}
    return out if isinstance(out, dict) else {}


def cost_basis_default() -> str:
    """The company's unit_cost_default; a missing or unknown value is 'last' — what the
    company actually paid most recently."""
    try:
        basis = _company_config('inventory').get('unit_cost_default')
    except Exception:
        logger.exception('unit_cost_default: company profile unreadable')
        return DEFAULT_COST_BASIS
    return basis if basis in COST_BASES else DEFAULT_COST_BASIS


def resolve_cost(item, *, basis: Optional[str] = None) -> CostResolution:
    """The unit cost a line starts from, and the list price it feeds.

    A not-tracked item is its standard rate. Otherwise the basis (company default when
    None); an item with nothing at that basis falls to standard — a new item has a
    standard cost before it has ever been bought — then to any cost it has, so a figure
    on the item is never priced as zero.
    """
    item = _item(item)
    cost = item.cost if isinstance(item.cost, dict) else {}
    first = basis or cost_basis_default()
    keys = ('standard',) if item.is_not_tracked else (
        first, 'standard', *[k for k in ('avg', 'last', 'landed') if k != first])
    unit, used = Decimal('0'), 'none'
    for key in keys:
        value = _dec(cost.get(key))
        if value is not None and value > 0:
            unit, used = value, key
            break
    sell = list_price(item)
    return CostResolution(unit=unit, basis=used, list_price=sell, margin_pct=_margin(sell, unit))


# ---------------------------------------------------------------------------
# Sell side
# ---------------------------------------------------------------------------

def _customer(customer_id):
    if not customer_id:
        return None
    from apps.orgs.models.customer import Customer
    return Customer.objects.filter(pk=customer_id).only('id', 'price_level').first()


def _assigned_catalogs(customer, level: str, now_ms: int):
    """Active catalogs, in their window, assigned to this customer — highest priority first.

    Assigned means: the catalog's customer is this customer, or applies_to names it
    (``all``, ``customers`` [org ids], ``price_levels`` [level words]). A catalog with
    no assignment applies to no one — a vendor's catalog is not a customer's price list.
    """
    if customer is None:
        return []
    from apps.products.models.catalog import Catalog
    catalogs = Catalog.objects.filter(is_active=True, dt_effective_start__lte=now_ms).filter(
        Q(dt_effective_end__isnull=True) | Q(dt_effective_end__gte=now_ms)).order_by('-priority', 'id')
    out = []
    for catalog in catalogs:
        applies = catalog.applies_to if isinstance(catalog.applies_to, dict) else {}
        if (catalog.customer_orgbase_id == customer.pk
                or applies.get('all')
                or customer.pk in (applies.get('customers') or [])
                or (level and level in (applies.get('price_levels') or []))):
            out.append(catalog)
    return out


def _catalog_line(catalog, item, qty: Decimal):
    """The catalog's line for this item at this quantity: a direct item line first, then
    a scope line (all_items, categories, vendors)."""
    from apps.products.models.catalog import CatalogLine

    def fits(line):
        return ((line.min_qty is None or qty >= line.min_qty)
                and (line.max_qty is None or qty <= line.max_qty))

    for line in CatalogLine.objects.filter(catalog=catalog, item=item).order_by('id'):
        if fits(line):
            return line
    item_cats = (item.catalog or {}).get('categories', []) if isinstance(item.catalog, dict) else []
    for line in CatalogLine.objects.filter(catalog=catalog, item__isnull=True).order_by('id'):
        scope = line.scope if isinstance(line.scope, dict) else {}
        if not fits(line):
            continue
        if (scope.get('all_items')
                or any(c in (scope.get('categories') or []) for c in item_cats)
                or (item.vendor_id and item.vendor_id in (scope.get('vendors') or []))):
            return line
    return None


def _catalog_line_price(line, level_price: Decimal, qty: Decimal) -> tuple[Decimal, Decimal, Optional[dict]]:
    """(price, discount_pct, qty_break) from a catalog line. Tiers in items.pricing win;
    otherwise the adjustment, taken off the line's price_unit or the level price."""
    pricing = (line.items or {}).get('pricing', {}) if isinstance(line.items, dict) else {}
    tier = None
    for t in sorted(pricing.get('tiers') or [], key=lambda t: t.get('min_qty', 0) or 0):
        if qty >= Decimal(str(t.get('min_qty', 0) or 0)) and _dec(t.get('price')) is not None:
            tier = t
    if tier is not None:
        return _dec(tier['price']), Decimal('0'), {'min_qty': tier.get('min_qty', 0), 'catalog_tier': True}

    adj_type = line.adjustment_type or 'percent_off'
    adj_value = _dec(line.adjustment_value) or Decimal('0')
    start = _dec(line.price_unit) or level_price
    if adj_type == 'fixed_price':
        return (_dec(line.price_unit) or adj_value), Decimal('0'), None
    if adj_type == 'amount_off':
        amount = _dec(line.discount_amount) or adj_value
        return max(Decimal('0'), start - amount), Decimal('0'), None
    if adj_type == 'percent_off':
        pct = _dec(line.discount_percent) or adj_value
        return start * (Decimal('100') - pct) / Decimal('100'), pct, None
    return start, Decimal('0'), None


def _level_price(item, level: str, qty: Decimal) -> tuple[Decimal, str, Optional[dict]]:
    """(price, resolved_by, qty_break) at a level: the item's price for the level, else
    list price; then the highest quantity break the quantity reaches, when it is lower.

    A break is {min_qty, unit_price} or {min_qty, variant_item_id} (whose list price
    applies) — Item.save keeps only those keys, so a break is one price for every level,
    and it never raises a customer's price above their level's."""
    price = item.price if isinstance(item.price, dict) else {}
    at_level = _dec(price.get(level)) if level else None
    unit, by = (at_level, 'price_level') if at_level is not None and at_level > 0 else (list_price(item), 'list_price')
    best, applied = unit, None
    for brk in sorted([b for b in price.get('qty_breaks') or [] if isinstance(b, dict)],
                      key=lambda b: b.get('min_qty', 0) or 0):
        if qty < Decimal(str(brk.get('min_qty', 0) or 0)):
            break
        value = _dec(brk.get('unit_price'))
        if value is None and brk.get('variant_item_id'):
            from apps.products.models.item import Item
            variant = Item.objects.filter(pk=brk['variant_item_id']).first()
            value = list_price(variant) if variant else None
        if value is not None:
            best = value
            applied = {k: brk[k] for k in brk}
    if applied is not None and best < unit:
        return best, by, applied
    return unit, by, None


def _minimum_margin_pct() -> Decimal:
    """The company floor: company profile config.pricing.minimum_margin (15 when unset)."""
    value = _dec(_company_config('pricing').get('minimum_margin'))
    return DEFAULT_MINIMUM_MARGIN_PCT if value is None else value


def resolve_price(
    item,
    *,
    customer_id: Optional[int] = None,
    qty=1,
    level: Optional[str] = None,
    as_of_ms: Optional[int] = None,
    price_locked_value=None,
) -> PriceResolution:
    """The unit price for an item, to a customer, at a quantity — and the cost under it.

    ``level`` is an explicit level (the line's, else the header's); when blank the
    customer's price_level applies. Never writes: below-floor results are flagged by
    the caller that commits the price (flag_below_margin).
    """
    item = _item(item)
    qty = Decimal(str(qty or 1))
    now_ms = as_of_ms or int(timezone.now().timestamp() * 1000)
    cost = resolve_cost(item)
    listed = list_price(item)
    customer = _customer(customer_id)
    company_floor = _minimum_margin_pct()
    level = named_price_level(level) or named_price_level(getattr(customer, 'price_level', '') or '')

    def done(price, resolved_by, *, floor=None, **kw) -> PriceResolution:
        price = Decimal(str(price)).quantize(CENT, rounding=ROUND_HALF_UP)
        margin = _margin(price, cost.unit)
        floor = floor if floor else company_floor
        return PriceResolution(
            price=price, list_price=listed, resolved_by=resolved_by, price_level=level,
            discount_amount=max(Decimal('0'), listed - price) if listed > 0 else Decimal('0'),
            unit_cost=cost.unit, cost_basis=cost.basis, margin_pct=margin, margin_floor=floor,
            below_margin_floor=margin is not None and margin < floor, **kw)

    if price_locked_value is not None:
        return done(price_locked_value, 'price_locked', price_locked=True)

    catalogs = _assigned_catalogs(customer, level, now_ms)
    level_unit, by, qty_break = _level_price(item, level, qty)

    for catalog in catalogs:
        if catalog.is_universal_pct:
            continue
        line = _catalog_line(catalog, item, qty)
        if line is not None:
            price, pct, tier = _catalog_line_price(line, level_unit, qty)
            return done(price, 'catalog_line', floor=_dec(catalog.margin_floor),
                        catalog_id=catalog.pk, catalog_name=catalog.name,
                        catalog_line_id=line.pk, discount_pct=pct, qty_break=tier)

    universal = next((c for c in catalogs if c.is_universal_pct and (c.universal_pct or 0) > 0), None)
    if universal is not None:
        pct = Decimal(str(universal.universal_pct))
        return done(level_unit * (Decimal('100') - pct) / Decimal('100'), by,
                    floor=_dec(universal.margin_floor), qty_break=qty_break, discount_pct=pct,
                    catalog_id=universal.pk, catalog_name=universal.name)
    return done(level_unit, by, qty_break=qty_break)


def flag_below_margin(item, result: PriceResolution, customer_id: Optional[int] = None) -> None:
    """An informational Action when a committed price is below its margin floor.

    Never blocks the price or the shipment — flag and ship, review in the sales dashboard.
    """
    if not result.below_margin_floor:
        return
    item = _item(item)
    try:
        from apps.core.models.action import Action
        source = f'Catalog: {result.catalog_name} (#{result.catalog_id}). ' if result.catalog_id else ''
        Action.objects.create(
            action={'en': f'Below-margin price: {item.ida or item.name}'},
            description={'en': (
                f'{item.ida} priced at ${result.price} ({result.resolved_by}) against cost '
                f'${result.unit_cost} ({result.cost_basis}) is {result.margin_pct}% margin, '
                f'below the {result.margin_floor}% floor. {source}'
                f'Customer: #{customer_id}. Review in sales dashboard.'
            )},
            status='Backlog',
            priority=1,            # low
        )
    except Exception:
        # Never blocks the price; said out loud (Axiom 6).
        logger.error('below-margin alert Action not created', exc_info=True)


# ---------------------------------------------------------------------------
# Callers' doors
# ---------------------------------------------------------------------------

def price_lines(items: list, *, customer_id: Optional[int] = None, level: Optional[str] = None) -> dict:
    """Both figures for a set of items — what the browser shows before a line is saved.

    items: [{item_id, qty}]. Returns {level, lines: [{item_id, qty, price, cost}]}.
    """
    lines = []
    resolved_level = ''
    for entry in items or []:
        item = _item(int(entry['item_id']))
        price = resolve_price(item, customer_id=customer_id, qty=entry.get('qty') or 1, level=level)
        resolved_level = resolved_level or price.price_level
        lines.append({'item_id': item.pk, 'qty': float(entry.get('qty') or 1),
                      'price': price.as_dict(), 'cost': resolve_cost(item).as_dict()})
    return {'level': resolved_level, 'lines': lines}


def get_price_matrix(item_id: int) -> dict:
    """Every level's price, the qty breaks, and the cost envelope — the item's pricing grid."""
    item = _item(item_id)
    price = item.price if isinstance(item.price, dict) else {}
    cost = item.cost if isinstance(item.cost, dict) else {}
    resolved = resolve_cost(item)
    return {
        'item_id': item.pk,
        'item_name': str(item),
        'currency': price.get('currency', 'USD'),
        'levels': [{'level': w,
                    'price': float(p) if (p := _dec(price.get(w))) is not None else None,
                    'margin_pct': float(m) if (m := _margin(p or Decimal('0'), resolved.unit)) is not None else None}
                   for w in PRICE_LEVELS],
        'list_price': float(resolved.list_price),
        'qty_breaks': price.get('qty_breaks') or [],
        'cost': {k: float(v) if (v := _dec(cost.get(k))) is not None else None for k in COST_BASES},
        'unit_cost': resolved.as_dict(),
    }


def apply_line_pricing(line_model_name: str, line_id: int, customer_id: Optional[int] = None,
                       qty=None) -> dict:
    """Reprice a saved sell line: resolve, write price.unit, flag below margin.

    Item from item_fk, quantity from quantity.active, customer from the parent document,
    level from the line else the header. The totals engine writes line.totals on save.
    """
    from apps.core.constants.model_registry import get_model_meta

    meta = get_model_meta(line_model_name)
    if not meta:
        raise ValueError(f'Unknown line model: {line_model_name}')
    LineModel = meta.import_model()
    line = LineModel.objects.filter(pk=line_id).first()
    if line is None:
        raise ValueError(f'{line_model_name} #{line_id} not found')

    item_id = getattr(line, 'item_fk_id', None) or (getattr(line, 'item', None) or {}).get('item_id')
    if not item_id:
        raise ValueError(f'Line #{line_id} has no item reference')
    qty = qty or (getattr(line, 'quantity', None) or {}).get('active') or 1
    parent = getattr(line, 'parent', None)
    if customer_id is None and parent is not None:
        customer_id = getattr(parent, 'customer_id', None)
    level = getattr(line, 'price_level', None) or getattr(parent, 'price_level', None)

    result = resolve_price(item_id, customer_id=customer_id, qty=qty, level=level)
    flag_below_margin(item_id, result, customer_id)
    if not isinstance(line.price, dict):
        line.price = {}
    line.price['unit'] = float(result.price)
    line.save(update_fields=['price'])

    out = result.as_dict()
    out.update(line_id=line_id, quantity=float(qty), amount=(line.totals or {}).get('amount', 0))
    return out


__all__ = [
    'PRICE_LEVELS', 'COST_BASES', 'named_price_level',
    'PriceResolution', 'CostResolution', 'list_price',
    'resolve_price', 'resolve_cost', 'cost_basis_default', 'flag_below_margin',
    'price_lines', 'get_price_matrix', 'apply_line_pricing',
]

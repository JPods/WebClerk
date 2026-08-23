from __future__ import annotations

from django.db import models
from common.models import BaseModel
from .item_base_model import ItemLinkedBase


def default_catalog_metrics():
    """Default metrics structure for a Catalog.

    Keys:
        item_count: Total items linked (lines)
        active_item_count: Subset currently active/eligible
        dt_last_priced: Epoch ms of last pricing change event
        dt_last_sync: Epoch ms of last external sync (if connected)
        plan_value_total: Planned extended value for next delivery window
        actual_value_total: Actual delivered/confirmed value
        variance_value_total: actual - plan value
        fill_rate_pct: Delivered lines / planned lines * 100
        avg_margin_pct: Average margin across active lines (if pricing present)
        usage_rolling_30d: Aggregate usage (units) in trailing 30 days for analytics
        update_accuracy_pct: % of attempted updates accepted by downstream systems
    """
    return {
        "item_count": 0,
        "active_item_count": 0,
        "dt_last_priced": None,
        "dt_last_sync": None,
        "plan_value_total": None,
        "actual_value_total": None,
        "variance_value_total": None,
        "fill_rate_pct": None,
        "avg_margin_pct": None,
        "usage_rolling_30d": None,
        "update_accuracy_pct": None,
    }

CATALOG_METRICS_KEY_INFO = {
    "item_count": "Total catalog lines (denormalized count)",
    "active_item_count": "Count of lines currently valid/active",
    "dt_last_priced": "Last epoch ms a price was changed",
    "dt_last_sync": "Epoch ms of last integration sync",
    "plan_value_total": "Planned extended delivery value for upcoming window",
    "actual_value_total": "Actual delivered extended value",
    "variance_value_total": "Actual - planned value variance",
    "fill_rate_pct": "% of planned lines successfully fulfilled",
    "avg_margin_pct": "Average margin percent across active lines",
    "usage_rolling_30d": "Rolling 30 day usage units (aggregated)",
    "update_accuracy_pct": "Percent of attempted external updates accepted",
}


class Catalog(BaseModel):
    @property
    def ida(self):
        return str(self.pk)

    @property
    def description(self):
        return self.name

    """Collection of items with pricing overrides and discounts."""

    name = models.CharField(max_length=160)
    code = models.CharField(max_length=60, db_index=True, help_text="Catalog code (unique per vendor_org; may repeat across vendors)")
    currency = models.CharField(max_length=8, default="USD")
    dt_effective_start = models.BigIntegerField()
    dt_effective_end = models.BigIntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    orgbase = models.ForeignKey('orgs.OrgBase', on_delete=models.SET_NULL, null=True, blank=True, related_name='vendor_catalogs', db_column='orgbase_id', help_text='Owning / publishing vendor organization (optional)')
    customer_orgbase = models.ForeignKey('orgs.OrgBase', on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_catalogs', db_column='customer_orgbase_id', help_text='Target customer organization scope (optional)')
    manufacturer_orgbase = models.ForeignKey('orgs.OrgBase', on_delete=models.SET_NULL, null=True, blank=True, related_name='manufacturer_catalogs', db_column='manufacturer_orgbase_id', help_text='Manufacturer associated with this catalog (optional)')
    rep_orgbase = models.ForeignKey('orgs.OrgBase', on_delete=models.SET_NULL, null=True, blank=True, related_name='rep_catalogs', db_column='rep_orgbase_id', help_text='Representative / agent organization (optional)')
    employee_orgbase = models.ForeignKey('orgs.OrgBase', on_delete=models.SET_NULL, null=True, blank=True, related_name='employee_catalogs', db_column='employee_orgbase_id', help_text='Internal employee / corporate organizational context (optional)')
    connection = models.ForeignKey(
        'sync.Connection',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='catalogs',
        db_column='connection_id',
        help_text='Sync connection managing external catalog integration (optional)'
    )
    metrics = models.JSONField(default=default_catalog_metrics, blank=True, null=True, help_text="Operational & performance metrics (plan vs actual, sync stats, counts)")

    # Pricing control fields (added from WC2 SpecialDiscount mining)
    priority = models.IntegerField(default=0, db_index=True,
        help_text="Higher priority wins when multiple catalogs match. 0=default.")
    applies_to = models.JSONField(default=dict, blank=True,
        help_text="Targeting scope: {contacts: [id], contact_types: ['wholesale'], categories: [], all: false}")
    is_universal_pct = models.BooleanField(default=False,
        help_text="True = blanket % applied to all items; False = per-line rules in CatalogLine")
    universal_pct = models.DecimalField(max_digits=6, decimal_places=3, default=0, blank=True,
        help_text="Universal discount % (used only when is_universal_pct=True)")
    margin_floor = models.DecimalField(max_digits=6, decimal_places=2, default=0, blank=True,
        help_text="Minimum margin % allowed — below triggers approval Action")

    def __str__(self):
        return self.name or self.code or f"Catalog {self.id}"

    class Meta:
        indexes = [
            models.Index(fields=("is_active", "dt_effective_start"), name="catalog_active_idx"),
            models.Index(fields=("orgbase",), name="catalog_vendor_idx"),
            models.Index(fields=("customer_orgbase",), name="catalog_customer_idx"),
            models.Index(fields=("manufacturer_orgbase",), name="catalog_manufacturer_idx"),
            models.Index(fields=("rep_orgbase",), name="catalog_rep_idx"),
            models.Index(fields=("employee_orgbase",), name="catalog_employee_idx"),
            models.Index(fields=("connection",), name="catalog_connection_idx"),
        ]
        constraints = [
            # Allow same code across different vendors, but enforce uniqueness per vendor.
            models.UniqueConstraint(fields=("code", "orgbase"), name="uniq_catalog_code_vendor"),
            # Enforce temporal validity (end >= start when end present)
            models.CheckConstraint(
                check=(models.Q(dt_effective_end__isnull=True) | models.Q(dt_effective_end__gte=models.F("dt_effective_start"))),
                name="ck_catalog_effective_range",
            ),
        ]

    # Backwards compatibility aliases
    @property
    def effective_dt_start(self):  # pragma: no cover
        return self.dt_effective_start

    @effective_dt_start.setter
    def effective_dt_start(self, v):  # pragma: no cover
        self.dt_effective_start = v

    @property
    def effective_dt_end(self):  # pragma: no cover
        return self.dt_effective_end

    @effective_dt_end.setter
    def effective_dt_end(self, v):  # pragma: no cover
        self.dt_effective_end = v

    # ---------------- Pricing policy (JSON conventions to avoid migrations) -----------------
    # Conventions stored in metadata / prefs:
    # - metadata.pricing = {"tax_included": bool, "currency": "USD", "rounding": {"precision": 2}}
    # - prefs.price_lists = {"default": {...}, "customer_group": {"groupA": {...}}}
    #   where each price list dict may include: {"discounts": [{"type": "percent|amount", "value": 5, "from": ms, "to": ms}],
    #                                             "tiers": [{"min_qty": 10, "price": 9.99}]}

    def set_pricing_policy(self, tax_included: bool | None = None, currency: str | None = None, precision: int | None = None):
        if not isinstance(self.metadata, dict):
            self.metadata = {}
        pricing = self.metadata.get('pricing') or {}
        if tax_included is not None:
            pricing['tax_included'] = bool(tax_included)
        if currency is not None:
            pricing['currency'] = currency
        if precision is not None:
            pricing['rounding'] = {'precision': int(precision)}
        self.metadata['pricing'] = pricing

    def get_pricing_policy(self) -> dict:
        policy = (self.metadata or {}).get('pricing') or {}
        if 'currency' not in policy and self.currency:
            policy['currency'] = self.currency
        return policy


class CatalogLine(ItemLinkedBase):
    @property
    def ida(self):
        return str(self.pk)

    @property
    def description(self):
        return str(self.catalog) if hasattr(self, 'catalog') else ""

    """Item entry in a catalog with specific pricing overrides."""

    catalog = models.ForeignKey(Catalog, on_delete=models.CASCADE, related_name="lines", db_column='catalog_id')
    price_unit = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    discount_percent = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)

    # Rule-based scope (what items does this line apply to)
    ADJUSTMENT_TYPES = [
        ('percent_off', 'Percent Off'),
        ('fixed_price', 'Fixed Price'),
        ('amount_off', 'Amount Off'),
        ('price_level', 'Price Level'),
    ]
    scope = models.JSONField(default=dict, blank=True,
        help_text="What this line covers: {items: [id], categories: [], vendors: [], all_items: false}")
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPES, default='percent_off', blank=True)
    adjustment_value = models.DecimalField(max_digits=14, decimal_places=4, default=0, blank=True,
        help_text="Value depends on type: 15.0 = 15% off, or $15 fixed, or price level code")
    min_qty = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True,
        help_text="Minimum qty for this price break (null = any)")
    max_qty = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True,
        help_text="Maximum qty for this price break (null = unlimited)")

    items = models.JSONField(default=dict, blank=True, null=True)
        # list ids prices, attributes, etc. for denormalized lookup
        # if it exceeds a size, put it in an external doc store
    metrics = models.JSONField(default=default_catalog_metrics, blank=True, help_text="Line-level metrics snapshot (plan/actual/value deltas)")

    def __str__(self):
        return f"CatalogLine {self.id} on {self.catalog_id}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["catalog", "item"], name="uniq_catalog_item"),
        ]

    # Lightweight metric helpers
    def touch_pricing(self, epoch_ms: int | None = None):  # pragma: no cover simple helper
        if not isinstance(self.metrics, dict):
            self.metrics = default_catalog_metrics()
        if epoch_ms is None:
            import time
            epoch_ms = int(time.time() * 1000)
        self.metrics["dt_last_priced"] = epoch_ms  # type: ignore[index]
        return self.metrics

    def record_sync(self, epoch_ms: int | None = None):  # pragma: no cover simple helper
        if not isinstance(self.metrics, dict):
            self.metrics = default_catalog_metrics()
        if epoch_ms is None:
            import time
            epoch_ms = int(time.time() * 1000)
        self.metrics["dt_last_sync"] = epoch_ms  # type: ignore[index]
        return self.metrics

    def update_plan_actual_value(self, plan: float | None, actual: float | None):  # pragma: no cover
        if not isinstance(self.metrics, dict):
            self.metrics = default_catalog_metrics()
        if plan is not None:
            self.metrics["plan_value_total"] = float(plan)  # type: ignore[index]
        if actual is not None:
            self.metrics["actual_value_total"] = float(actual)  # type: ignore[index]
        if plan is not None and actual is not None:
            self.metrics["variance_value_total"] = float(actual - plan)  # type: ignore[index]
            if plan > 0:
                # fill_rate_pct remains separate; plan vs actual value could inform margin accuracy
                pass
        return self.metrics
        indexes = [
            models.Index(fields=("catalog_id",), name="catalogline_catalog_idx"),
        ]

    # ---------------- Pricing helpers (tiered, group-specific, discounts) -------------------
    # Conventions (JSON):
    # - items.pricing = { "tiers": [{"min_qty": 1, "price": 10.00}],
    #                     "discounts": [{"type": "percent|amount", "value": 5, "from": ms, "to": ms}],
    #                     "customer_groups": {"retail": { ... same shape ... }, "wholesale": {...}},
    #                     "tax_included": bool }

    def _ensure_items_pricing(self):
        if not isinstance(self.items, dict):
            self.items = {}
        self.items.setdefault('pricing', {})
        return self.items['pricing']

    def set_tiered_prices(self, tiers: list[dict]):
        p = self._ensure_items_pricing()
        p['tiers'] = tiers

    def add_tier(self, min_qty: int, price: float):
        p = self._ensure_items_pricing()
        tiers = p.get('tiers') or []
        tiers.append({'min_qty': int(min_qty), 'price': float(price)})
        tiers.sort(key=lambda t: t.get('min_qty') or 0)
        p['tiers'] = tiers

    def set_discounts(self, discounts: list[dict]):
        p = self._ensure_items_pricing()
        p['discounts'] = discounts

    def add_discount(self, kind: str, value: float, dt_from_ms: int | None = None, dt_to_ms: int | None = None):
        p = self._ensure_items_pricing()
        disc = p.get('discounts') or []
        disc.append({'type': kind, 'value': float(value), 'from': dt_from_ms, 'to': dt_to_ms})
        p['discounts'] = disc

    def set_group_pricing(self, group: str, tiers: list[dict] | None = None, discounts: list[dict] | None = None):
        p = self._ensure_items_pricing()
        groups = p.get('customer_groups') or {}
        entry = groups.get(group) or {}
        if tiers is not None:
            entry['tiers'] = tiers
        if discounts is not None:
            entry['discounts'] = discounts
        groups[group] = entry
        p['customer_groups'] = groups

    def get_effective_price(self, qty: float = 1.0, group: str | None = None, when_ms: int | None = None) -> dict:
        """Compute an indicative effective unit price based on tiers and discounts in JSON.

        This is a helper for UI/estimation; authoritative pricing may still run in services.
        Returns: {"base": number|None, "tier": number|None, "discount": number|None, "final": number|None}
        """
        from django.utils import timezone
        if when_ms is None:
            when_ms = int(timezone.now().timestamp() * 1000)
        base = float(self.price_unit) if self.price_unit is not None else None
        p = (self.items or {}).get('pricing') or {}
        # pick tiers
        active_tiers = []
        if group and isinstance(p.get('customer_groups'), dict):
            active_tiers = (p['customer_groups'].get(group) or {}).get('tiers') or []
        if not active_tiers:
            active_tiers = p.get('tiers') or []
        tier_price = None
        if active_tiers:
            # choose the highest tier with min_qty <= qty
            active_tiers = sorted(active_tiers, key=lambda t: (t.get('min_qty') or 0))
            for t in active_tiers:
                if (t.get('min_qty') or 0) <= qty:
                    tier_price = float(t.get('price')) if t.get('price') is not None else None
        # discounts
        disc_list = []
        if group and isinstance(p.get('customer_groups'), dict):
            disc_list = (p['customer_groups'].get(group) or {}).get('discounts') or []
        if not disc_list:
            disc_list = p.get('discounts') or []
        discount_value = 0.0
        for d in disc_list:
            f = d.get('from'); to = d.get('to')
            if (f is None or when_ms >= f) and (to is None or when_ms <= to):
                kind = (d.get('type') or '').lower()
                val = float(d.get('value') or 0)
                if kind == 'percent':
                    # percent applied on candidate price (tier if present else base)
                    base_ref = tier_price if tier_price is not None else base
                    if base_ref is not None:
                        discount_value += base_ref * (val / 100.0)
                elif kind == 'amount':
                    discount_value += val
        # combine
        candidate = tier_price if tier_price is not None else base
        final = None if candidate is None else max(0.0, candidate - discount_value)
        return {'base': base, 'tier': tier_price, 'discount': discount_value if discount_value else None, 'final': final}

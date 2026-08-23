from __future__ import annotations

from django.db import models
from typing import Optional, Dict, Any
from apps.products.choices import ITEM_XREF_SOURCE_CHOICES
from .item_base_model import ItemLinkedBase


class ItemXRef(ItemLinkedBase):
    """External cross reference mapping for supplier/manufacturer identifiers."""

    @property
    def ida(self):
        return str(self.pk)

    @property
    def description(self):
        return self.source_name

    SOURCE_MANUFACTURER = "manufacturer"
    SOURCE_WHOLESALER = "wholesaler"
    SOURCE_OTHER = "other"
    SOURCE_CHOICES = ITEM_XREF_SOURCE_CHOICES

    # Source system classification (manufacturer, wholesaler, other)
    source = models.CharField(max_length=40, choices=SOURCE_CHOICES, db_index=True)
    # Optional pointer details for external system record (if needed)
    source_id = models.BigIntegerField(blank=True, null=True)
    # Legacy field renamed to source_model_name (historical migration retains old name)
    source_model_name = models.CharField(max_length=40, blank=True)
    source_name = models.CharField(max_length=120, blank=True)
    external_sku = models.CharField(max_length=120, db_index=True)
    external_uuid = models.UUIDField(blank=True, null=True)
    # Structured cost object (e.g. {"value": 12.34, "currency": "USD", "breaks": []})
    cost = models.JSONField(default=dict, blank=True, null=True, help_text="Structured cost data (value, currency, tiers, etc.)")
    is_preferred = models.BooleanField(default=False, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["item_id", "source", "external_sku"], name="uniq_item_source_sku"),
        ]
        indexes = [
            models.Index(fields=("source", "external_sku"), name="xref_source_sku_idx"),
        ]

    def __str__(self):  # pragma: no cover
        return f"{getattr(self.item, 'pk', '?')}:{self.source}:{self.external_sku}"

    # ---------------- Convenience JSON-backed attributes (no schema changes) -----------------
    # We standardize on using metadata and refs (from BaseModel) to store auxiliary alias data
    # without introducing migrations. Conventions:
    # - metadata.effectivity = {"start": epoch_ms|None, "end": epoch_ms|None}
    # - refs.partner = {"org_id": int|None, "role": "supplier|customer|manufacturer|distributor|other"}
    # - refs.codes = {"gtin": str|None, "upc": str|None, "ean": str|None, "mpn": str|None, "barcode_type": str|None}

    # Effectivity helpers --------------------------------------------------------------------
    @property
    def dt_effective_start(self) -> Optional[int]:
        meta = self.metadata if isinstance(self.metadata, dict) else {}
        eff = meta.get('effectivity') or {}
        return eff.get('start')

    @property
    def dt_effective_end(self) -> Optional[int]:
        meta = self.metadata if isinstance(self.metadata, dict) else {}
        eff = meta.get('effectivity') or {}
        return eff.get('end')

    def set_effectivity(self, start_ms: Optional[int], end_ms: Optional[int]) -> None:
        if not isinstance(self.metadata, dict):
            self.metadata = {}
        eff = self.metadata.get('effectivity') or {}
        eff['start'] = int(start_ms) if isinstance(start_ms, (int, float)) else None
        eff['end'] = int(end_ms) if isinstance(end_ms, (int, float)) else None
        self.metadata['effectivity'] = eff

    def is_effective(self, when_ms: Optional[int] = None) -> bool:
        """Return True when within [start,end] window (inclusive). None is treated as open-bound."""
        if when_ms is None:
            from django.utils import timezone
            when_ms = int(timezone.now().timestamp() * 1000)
        s = self.dt_effective_start
        e = self.dt_effective_end
        if s is not None and when_ms < s:
            return False
        if e is not None and when_ms > e:
            return False
        return True

    # Partner helpers ------------------------------------------------------------------------
    def set_partner(self, org_id: Optional[int], role: str) -> None:
        if not isinstance(self.refs, dict):
            self.refs = {}
        partner = self.refs.get('partner') or {}
        partner['org_id'] = int(org_id) if isinstance(org_id, int) else None
        partner['role'] = role
        self.refs['partner'] = partner

    def get_partner(self) -> Dict[str, Any]:
        return (self.refs or {}).get('partner') or {}

    # Codes helpers ---------------------------------------------------------------------------
    def set_codes(self, gtin: Optional[str] = None, upc: Optional[str] = None, ean: Optional[str] = None,
                  mpn: Optional[str] = None, barcode_type: Optional[str] = None) -> None:
        if not isinstance(self.refs, dict):
            self.refs = {}
        codes = self.refs.get('codes') or {}
        if gtin is not None:
            codes['gtin'] = str(gtin)
        if upc is not None:
            codes['upc'] = str(upc)
        if ean is not None:
            codes['ean'] = str(ean)
        if mpn is not None:
            codes['mpn'] = str(mpn)
        if barcode_type is not None:
            codes['barcode_type'] = str(barcode_type)
        self.refs['codes'] = codes

    def get_codes(self) -> Dict[str, Any]:
        return (self.refs or {}).get('codes') or {}

    # Cost helpers ----------------------------------------------------------------------------
    def set_cost(self, value: Optional[float] = None, currency: Optional[str] = None,
                 tiers: Optional[list] = None, extra: Optional[Dict[str, Any]] = None) -> None:
        payload: Dict[str, Any] = self.cost if isinstance(self.cost, dict) else {}
        if value is not None:
            payload['value'] = float(value)
        if currency is not None:
            payload['currency'] = currency
        if tiers is not None:
            payload['breaks'] = tiers
        if extra:
            payload.update(extra)
        self.cost = payload

"""
Pydantic schemas for Item JSON envelopes.

Inherits standard bases. Item has the richest prefs (import, display, shipping, variants).
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# ── .quantity (Item-specific, not an envelope — lives on Item.quantity JSONB) ──

class ItemQuantity(BaseModel):
    """Schema for Item.quantity JSONB — inventory bucket states + control points.

    Bucket fields are updated by inventory services (pending drain, reservations,
    transaction lifecycle). Control fields (inventory_min/max) are set by the
    recommend_inventory_bounds() service or manually.
    """
    on_hand: Optional[float] = None
    allocated: Optional[float] = None
    available: Optional[float] = None
    on_so: Optional[float] = None       # on sales order
    on_po: Optional[float] = None       # on purchase order
    on_p: Optional[float] = None        # on proposal (probability-weighted)
    on_reciept: Optional[float] = None  # in receiving (spelling preserved for compat)
    on_in: Optional[float] = None       # on invoice (shipped, pending GL)
    on_wo: Optional[float] = None       # on work order
    inventory_min: Optional[float] = None  # reorder point — trigger replenishment below this
    inventory_max: Optional[float] = None  # max stock level — order up to this

    class Config:
        extra = "forbid"


# ── .config ────────────────────────────────────────────────────────

class ItemConfig(ConfigBase):
    pass


# ── .metadata (inherits MetadataBase) ─────────────────────────────

class ItemMetadata(MetadataBase):
    """Item-specific metadata. Standard fields inherited."""
    variants: Optional[dict] = None    # system-managed variant matrix


# ── .prefs ─────────────────────────────────────────────────────────

class ItemPrefs(RecordPrefsBase):
    """Item prefs — import rules, display, shipping, variants, restrictions."""
    import_prefs: Optional[dict] = Field(None, alias="import")
    import_details: dict = Field(default_factory=dict)
    display: Optional[dict] = None
    shipping: Optional[dict] = None
    variants: Optional[dict] = None
    restrictions: Optional[dict] = None


# ── .refs ──────────────────────────────────────────────────────────

class ItemRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    variants: list = Field(default_factory=list)
    depends_on: dict = Field(default_factory=dict)
    related_ids: list[int] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# ── Setting defaults ──────────────────────────────────────────────

class ItemSettingDefaults(BaseModel):
    status: str = "active"
    is_active: bool = True
    type: str = ""
    category: str = ""

    class Config:
        extra = "forbid"

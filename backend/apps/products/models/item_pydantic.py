"""
Pydantic schemas for Item JSON envelopes.

Inherits standard bases. Item has the richest prefs (import, display, shipping, variants).
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef
from common.schemas.images import ItemImages


# ── .quantity (Item-specific, not an envelope — lives on Item.quantity JSONB) ──

class ItemRateProfile(BaseModel):
    """How an item's demand is shaped, as multipliers on units_per_day.

    Some items are not flat (Bill, 2026-09-17): a pattern by day of week, by month,
    around named dates — whatever the item actually does. A multiplier of 1.0 is an
    ordinary day, 0 is a day with no demand (closed Sundays), 2.4 is the Friday rush.

    Kept as multipliers rather than absolute rates so the baseline stays one number:
    change the baseline and the whole shape moves with it.

    dow      {"mon".."sun": factor}
    month    {"1".."12": factor}
    dates    [{"name": "July 4", "dt": epoch_ms | "mm-dd", "factor": 2.1, "span_days": 3}]
    samples  per-bucket counts — a factor fitted to three Tuesdays is noise, and the
             writer must say how thin it is rather than let it pass for a pattern.
    """
    dow: Optional[dict] = None
    month: Optional[dict] = None
    dates: Optional[list] = None
    samples: Optional[dict] = None
    basis: Optional[str] = None   # history | manual | vendor | calendar

    class Config:
        extra = "forbid"


class ItemRate(BaseModel):
    """A consumption rate on Item.quantity — units per day, with what it rests on.

    Two rates, and the difference between them is the signal (Bill, 2026-09-17):
      rate_expected — what we plan for. Set: by a person, or by Alice from history.
      rate_actual   — what is happening. Computed from Pending dt_created (the arrival
                      times of demand), by one writer, never typed by hand.

    rate_actual is a stored measurement, not a stored opinion: it carries the window it
    was measured over and when it was computed, so a stale rate is visible as stale
    instead of passing for current. Blank beats a guess.
    """
    units_per_day: Optional[float] = None  # the baseline; a profile bends it
    window_days: Optional[int] = None    # measured over / planned over
    samples: Optional[int] = None        # demand records behind rate_actual
    dt_computed: Optional[int] = None    # epoch ms — rate_actual, by its one writer
    dt_set: Optional[int] = None         # epoch ms — rate_expected, by whoever set it
    basis: Optional[str] = None          # manual | history | seasonal | vendor
    history: Optional[list] = None       # [{dt, units_per_day}] — the item's own curve
    profile: Optional[ItemRateProfile] = None  # pattern: some items are not flat

    class Config:
        extra = "forbid"


class ItemQuantity(BaseModel):
    """Schema for Item.quantity JSONB — inventory bucket states + control points.

    Bucket fields are updated by inventory services (pending drain, reservations,
    transaction lifecycle). Control fields (min/max) are set by the
    recommend_inventory_bounds() service or manually.

    Rates say what min and max cannot: min is a level, a rate is a speed. What decides
    whether a line joins the next delivery is whether stock survives until the truck
    after it — a level cannot answer that alone.
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
    min: Optional[float] = None  # reorder point — trigger replenishment below this
    max: Optional[float] = None  # max stock level — order up to this
    rate_expected: Optional[ItemRate] = None  # planned consumption — set
    rate_actual: Optional[ItemRate] = None    # observed consumption — computed

    class Config:
        extra = "forbid"


# ── .config ────────────────────────────────────────────────────────

class ItemConfig(ConfigBase):
    pass


# ── .metadata (inherits MetadataBase) ─────────────────────────────

class ItemMetadata(MetadataBase):
    """Item-specific metadata. Standard fields inherited."""
    variants: Optional[dict] = None    # system-managed variant matrix
    images: Optional[ItemImages] = None


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

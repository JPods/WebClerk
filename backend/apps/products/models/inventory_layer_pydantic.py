"""
Pydantic schemas for Inventory Layer JSON envelopes.

Inherits standard bases. Add model-specific fields only.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from common.schemas.envelopes import ConfigBase, MetadataBase, RecordPrefsBase, RefsBase, SourceRef


# -- .config ----------------------------------------------------------------

class InventoryLayerConfig(ConfigBase):
    pass


# -- .metadata (inherits MetadataBase) --------------------------------------

class InventoryLayerMetadata(MetadataBase):
    pass


# -- .prefs (inherits RecordPrefsBase) --------------------------------------

class InventoryLayerPrefs(RecordPrefsBase):
    pass


# -- .refs (inherits RefsBase) ----------------------------------------------

class InventoryLayerRefs(RefsBase):
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source: Optional[SourceRef] = None


# -- .quantity and .cost ------------------------------------------------------
# What a layer holds and what each unit is carried at. Read-only on the form: a layer's quantity
# and cost change only through its receipt line, a count, or the Pending applier, never through
# a save (products/behaviours.InventoryLayerBehaviour). Until 2026-11-26 the layer's cost was
# mapped to the transaction cost schema and its quantity to none, so the door let out only
# cost.freight and cost.handling and the form could not show a layer's quantity, unit cost,
# duty, vat or landed cost at all (Bill: "very hard to see or find values").

def _qty(title: str, description: str):
    return Field(0.0, title=title, description=description,
                 json_schema_extra={'widget': 'number', 'precision': 4, 'readonly': True})


def _unit(title: str, description: str):
    return Field(0.0, title=title, description=description,
                 json_schema_extra={'widget': 'currency', 'precision': 4, 'readonly': True})


class InventoryLayerQuantity(BaseModel):
    """Units in and out of the layer. What is left = received − issued − scrapped."""
    received: float = _qty("Received", "Units the layer was born with, as corrected on its receipt line")
    issued: float = _qty("Issued", "Units sold, used or moved out of the layer")
    scrapped: float = _qty("Scrapped", "Units written off from the layer")

    class Config:
        extra = "allow"


class InventoryLayerCost(BaseModel):
    """Per-unit cost of the layer (products/models/inventory_layer.default_cost)."""
    unit_po: float = _unit("Unit PO", "The unit cost on the receipt line, after its discount")
    freight: float = _unit("Freight", "Freight per unit: the line's share ÷ quantity received")
    duty: float = _unit("Duty", "Duty per unit: the line's share ÷ quantity received")
    handling: float = _unit("Handling", "Handling per unit: the line's share ÷ quantity received")
    vat: float = _unit("VAT", "VAT per unit: the line's share ÷ quantity received")
    landed: float = _unit("Landed", "What one unit is carried at: unit_po + freight + duty + handling + vat")
    moving_avg: float = _unit("Moving Avg", "The item's average cost after this receipt")
    trend_pct: float = Field(0.0, title="Trend %", description="Change against the average before this receipt",
                             json_schema_extra={'widget': 'number', 'precision': 2, 'readonly': True})
    scrap_cost: float = _unit("Scrap Cost", "Per-unit write-off attributed to scrap for this layer")
    fifo_snapshot: float = _unit("FIFO Snapshot", "FIFO pick cost when the layer was made")
    lifo_snapshot: float = _unit("LIFO Snapshot", "LIFO pick cost when the layer was made")
    currency: str = Field("USD", title="Currency", json_schema_extra={'widget': 'text', 'readonly': True})
    exchange_rate: float = Field(1.0, title="Exchange Rate",
                                 json_schema_extra={'widget': 'number', 'precision': 6, 'readonly': True})

    class Config:
        extra = "allow"

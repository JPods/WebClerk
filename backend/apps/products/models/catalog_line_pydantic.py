"""
Pydantic schemas for CatalogLine's JSON fields — what price_resolver reads from a line.

``scope`` is what a line without an item covers (price_resolver._catalog_line);
``items.pricing.tiers`` are its quantity prices (price_resolver._catalog_line_price).
Envelopes (config, metadata, prefs, refs) use the standard bases.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class CatalogLineScope(BaseModel):
    """The items a line without an item covers. One of the three must name something."""
    all_items: bool = Field(False, title="All Items",
                            description="Every item the catalog's customers buy")
    categories: list[str] = Field(default_factory=list, title="Categories",
                                  description="Items whose catalog.categories include one of these")
    vendors: list[int] = Field(default_factory=list, title="Vendors",
                               description="Items whose vendor is one of these vendor ids")

    class Config:
        extra = "forbid"

    def names_something(self) -> bool:
        return bool(self.all_items or self.categories or self.vendors)


class CatalogLineTier(BaseModel):
    min_qty: float = Field(0, title="Min Qty")
    price: Optional[float] = Field(None, title="Price")

    class Config:
        extra = "forbid"


class CatalogLinePricing(BaseModel):
    tiers: list[CatalogLineTier] = Field(default_factory=list, title="Tiers",
                                         description="The highest tier the quantity reaches is the price")

    class Config:
        extra = "forbid"


class CatalogLineItems(BaseModel):
    pricing: CatalogLinePricing = Field(default_factory=CatalogLinePricing, title="Pricing")

    class Config:
        extra = "forbid"

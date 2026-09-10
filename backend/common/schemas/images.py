"""
Image schemas — standard image metadata for contacts, orgs, and items.

All images stored as paths in metadata.images. Actual files in /media/.
Resizing happens at upload time via Pillow. Schemas validate the structure.
Standard format: .jpg (except SVG placeholders and logos needing transparency).

Sizes:
  tn    — 90px max  thumbnail (lists, badges, cart lines)
  md    — 256px     catalog grid, cards, profile
  hires — original  detail page, zoom, print
"""
from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field


class ImageSet(BaseModel):
    """Standard 3-size image set — .jpg, stored as relative paths."""
    tn: Optional[str] = None        # 90px max — thumbnail
    md: Optional[str] = None        # 256px — catalog/cards
    hires: Optional[str] = None     # original resolution
    alt: Optional[str] = None       # alt text for accessibility

    class Config:
        extra = "forbid"


class ContactImages(BaseModel):
    """Contact photo + optional additional images."""
    photo: Optional[ImageSet] = None

    class Config:
        extra = "forbid"


class OrgImages(BaseModel):
    """Organization logo + optional banner and additional images."""
    logo: Optional[ImageSet] = None
    banner: Optional[ImageSet] = None
    icon: Optional[ImageSet] = None   # favicon-sized, for nav/tabs

    class Config:
        extra = "forbid"


class ItemImages(BaseModel):
    """Product/item images — primary + gallery."""
    primary: Optional[ImageSet] = None
    gallery: Optional[List[ImageSet]] = Field(default_factory=list)

    class Config:
        extra = "forbid"

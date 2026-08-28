"""
Image schemas — standard image metadata for contacts, orgs, and items.

All images stored as paths in metadata.images. Actual files in /media/.
Resizing happens at upload time via Pillow. Schemas validate the structure.

Sizes:
  tn       — 64px  thumbnail (lists, badges, gantt assignee)
  sm       — 128px small (contact card, chat avatar)
  md       — 256px medium (profile page, directory)
  lg       — 512px large (detail page hero)
  original — full  (user download, print)
"""
from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field


class ImageSet(BaseModel):
    """Standard image size set — used for any entity's primary image."""
    tn: Optional[str] = None        # 64px  — thumbnail
    sm: Optional[str] = None        # 128px — small
    md: Optional[str] = None        # 256px — medium
    lg: Optional[str] = None        # 512px — large
    original: Optional[str] = None  # full resolution
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

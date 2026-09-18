"""
Image schemas — standard image metadata for contacts, orgs, and items.

metadata.images holds flags, not paths. Actual files in /media/.
Resizing happens at upload time via Pillow. Schemas validate the structure.
Standard format: .jpg (except SVG placeholders and logos needing transparency).

Sizes:
  tn — 90px max  thumbnail (lists, badges, cart lines)
  md — 256px     catalog grid, cards, profile
  hr — original  detail page, zoom, print
"""
from __future__ import annotations

from pydantic import BaseModel


class ImageFlags(BaseModel):
    """metadata.images on every record. Files live at media/images/<model>/<ida>/{tn,md,hr}.jpg;
    the flags say which sizes exist. source = "local" | "remote:<Supplier>" | "placeholder"
    | a supplier part key such as "adafruit:<pid>". Read by resolve_image."""
    source: str = ""
    tn: bool = False
    md: bool = False
    hr: bool = False

    class Config:
        extra = "forbid"

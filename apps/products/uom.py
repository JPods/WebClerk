from __future__ import annotations

"""Lightweight Units of Measure utilities (no DB schema required).

Design:
- Canonical categories: count, weight, length, volume, time.
- Each UoM maps to a category and a factor to a chosen base unit for that category.
- Conversions are pure functions; packaging/multipacks are handled per-Item via JSON prefs.

Notes:
- Count base is EA (each). Common alternates like DZ (dozen) are provided.
- Weight base is g. Length base is m. Volume base is ml. Time base is s.
"""
from typing import Dict, Tuple

# Map UOM -> (category, factor_to_base)
UOM_FACTORS: Dict[str, Tuple[str, float]] = {
    # count
    'EA': ('count', 1.0),
    'EACH': ('count', 1.0),
    'DZ': ('count', 12.0),
    'DOZEN': ('count', 12.0),
    'HUN': ('count', 100.0),
    'CS12': ('count', 12.0),  # shorthand: 12-pack case (optional convenience)
    # weight
    'G': ('weight', 1.0),
    'KG': ('weight', 1000.0),
    'MG': ('weight', 0.001),
    'LB': ('weight', 453.59237),
    'OZ': ('weight', 28.349523125),
    # length
    'M': ('length', 1.0),
    'CM': ('length', 0.01),
    'MM': ('length', 0.001),
    'IN': ('length', 0.0254),
    'FT': ('length', 0.3048),
    # volume
    'ML': ('volume', 1.0),
    'L': ('volume', 1000.0),
    'FLOZ': ('volume', 29.5735295625),
    'GAL': ('volume', 3785.411784),
    # time
    'S': ('time', 1.0),
    'MIN': ('time', 60.0),
    'H': ('time', 3600.0),
}

# Normalize aliases to canonical codes used above
ALIASES: Dict[str, str] = {
    'EACH': 'EA',
    'EAC': 'EA',
    'EA': 'EA',
    'DOZ': 'DZ',
    'DOZEN': 'DZ',
    'OUNCE': 'OZ',
    'OUNCES': 'OZ',
    'POUND': 'LB',
    'POUNDS': 'LB',
    'LITER': 'L',
    'LITRE': 'L',
    'LITERS': 'L',
    'LITRES': 'L',
    'MILLILITER': 'ML',
    'MILLILITRE': 'ML',
    'MILLILITERS': 'ML',
    'MILLILITRES': 'ML',
    'SECOND': 'S',
    'SECONDS': 'S',
    'HOUR': 'H',
    'HOURS': 'H',
}


def normalize_uom(code: str) -> str:
    c = (code or '').strip().upper()
    return ALIASES.get(c, c)


def get_category(uom: str) -> str | None:
    u = normalize_uom(uom)
    info = UOM_FACTORS.get(u)
    return info[0] if info else None


def to_base_factor(uom: str) -> float | None:
    u = normalize_uom(uom)
    info = UOM_FACTORS.get(u)
    return info[1] if info else None


def can_convert(uom_from: str, uom_to: str) -> bool:
    c1 = get_category(uom_from)
    c2 = get_category(uom_to)
    return c1 is not None and c1 == c2


def convert(quantity: float, uom_from: str, uom_to: str) -> float:
    """Convert quantity between same-category UOMs using factor-to-base.

    Raises ValueError if categories do not match or factors missing.
    """
    u_from = normalize_uom(uom_from)
    u_to = normalize_uom(uom_to)
    info_from = UOM_FACTORS.get(u_from)
    info_to = UOM_FACTORS.get(u_to)
    if not info_from or not info_to or info_from[0] != info_to[0]:
        raise ValueError(f"Cannot convert {u_from} -> {u_to} (category mismatch or unknown)")
    base_qty = float(quantity) * info_from[1]
    return base_qty / info_to[1]

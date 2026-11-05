"""The company profile — the one ``wc:company_profile`` Setting — read a section at a time.

Cached, because operational saves read it (Item.save reads the cost basis; an order's birth
reads ``default``), and an operational save must not pay a query for admin configuration.
The cache is cleared when the profile is saved (signals/access_signals.py).

Sections a save reads: ``inventory`` (cost basis), ``pricing`` (minimum margin), ``default``
(Bill, 2026-11-05: ``default.terms`` is the company's terms when a customer has none;
``default.order_new.days`` and ``.priority`` are what a new order is born with).
"""
from __future__ import annotations

COMPANY_CACHE = 'company_profile'


def company_config(section: str) -> dict:
    """One section of the company profile's ``config``; ``{}`` when the profile or the
    section is missing or is not an object."""
    from apps.core.models import Setting
    from apps.core.services.cache import cache_service
    key = cache_service.make_key(COMPANY_CACHE, section)
    cached = cache_service.get(key)
    if cached is not None:
        return cached
    company = Setting.objects.filter(purpose='wc:company_profile', is_active=True).first()
    out = company.config.get(section, {}) if company and isinstance(company.config, dict) else {}
    out = out if isinstance(out, dict) else {}
    cache_service.set(key, out, ttl=0)
    return out

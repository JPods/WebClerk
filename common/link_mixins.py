"""Standard relationship/link JSON helpers & mixins.

Goal: Provide a reusable, opinionated structure for refs.links so 80% of
models can rely on a consistent lightweight relationship vocabulary
without bespoke per‑model initialization logic.

Usage:
    from common.link_mixins import StandardLinksMixin
    class MyModel(StandardLinksMixin, RefsMixin, BaseModel):
        ...

The mixin ensures (on save) that refs.links contains the canonical keys
USING singular model_name (canonical) forms:
    contact, email, phone, location, domain,
    customer, vendor, manufacturer, rep,
    order, project, document

It DOES NOT overwrite existing arrays; it only initializes missing ones.
This keeps it safe / idempotent for existing records.

We also expose helpers:
    ensure_standard_links(refs) -> dict
    default_extended_refs() -> dict  (drop-in alternative to default_refs)

Future Expansion:
- Add additional link buckets (e.g., invoices, purchases) as tables land.
- Optional validation / normalization hooks (e.g., dedupe, int coercion).
"""
from __future__ import annotations

from typing import Iterable, Dict, Any
from django.db import models
# TODO: potential enhancement: refine link resolution by canonical model key
# Canonical singular model_name keys
STANDARD_LINK_KEYS: tuple[str, ...] = (
    "contact",
    "email",
    "phone",
    "location",
    "domain",
    # Organization type buckets (singular)
    "customer",
    "vendor",
    "manufacturer",
    "rep",
    # Generic cross-type (singular)
    "order",
    "project",
    "document",
)



def ensure_standard_links(refs: dict | None) -> dict:
    """Ensure refs.links exists with STANDARD_LINK_KEYS lists.

    Returns the mutated (or newly created) refs dict. Does not clear existing
    contents; only creates missing containers.
    """
    if refs is None:
        refs = {}
    if not isinstance(refs, dict):  # defensive
        return {}
    links = refs.setdefault("links", {})
    if not isinstance(links, dict):  # reset corrupt shape
        links = {}
        refs["links"] = links
    for key in STANDARD_LINK_KEYS:
        links.setdefault(key, [])
    # keep other top-level keys if present; no destructive changes
    refs.setdefault("keywords", [])
    refs.setdefault("tags", [])
    refs.setdefault("related_ids", [])
    refs.setdefault("categories", [])
    return refs


def default_extended_refs() -> dict:
    """Return a superset default refs structure including all standard link buckets.

    Safe to use as a model field default callable.
    """
    return {
        "keywords": [],
        "tags": [],
        "categories": [],
        "related_ids": [],
    "links": {k: [] for k in STANDARD_LINK_KEYS},
    }


class StandardLinksMixin(models.Model):
    """Abstract mixin adding ensure_standard_links pre-save behavior.

    Assumes the concrete model already has a JSONField named `refs` (e.g. via
    RefsMixin). If not present, this mixin is a no-op.
    """
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):  # type: ignore[override]
        if hasattr(self, "refs"):
            try:
                current = getattr(self, "refs", {})
                ensured = ensure_standard_links(current if isinstance(current, dict) else {})
                setattr(self, "refs", ensured)
            except Exception:  # pragma: no cover - defensive
                pass
        return super().save(*args, **kwargs)


__all__ = [
    "STANDARD_LINK_KEYS",
    "ensure_standard_links",
    "default_extended_refs",
    "StandardLinksMixin",
]

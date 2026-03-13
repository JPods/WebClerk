"""Shared fragment-based search utilities.

Extracted from PrefixAndSearchView.build_query() and enhanced with
the ``@`` contains modifier for wc2-parity fragment search.

Usage from views::

    from common.search_utils import parse_fragments, build_fragment_query

    qs = build_fragment_query(qs, raw_search, search_fields, ModelCls)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

from django.db import models

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Fragment:
    """A single parsed search fragment."""
    value: str                          # lowercased, trimmed
    mode: str                           # "startswith" | "contains"


def parse_fragments(raw: str) -> list[Fragment]:
    """Parse a comma-separated search string into typed fragments.

    - Split on comma (with optional surrounding whitespace)
    - ``@`` prefix → contains mode (``@`` stripped from value)
    - No prefix   → startswith mode
    - Empty / whitespace-only fragments are dropped
    - Values are lowercased for case-insensitive matching
    """
    if not raw or not raw.strip():
        return []

    fragments: list[Fragment] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if part.startswith("@") and len(part) > 1:
            fragments.append(Fragment(value=part[1:].lower(), mode="contains"))
        else:
            fragments.append(Fragment(value=part.lower(), mode="startswith"))
    return fragments


def build_fragment_query(
    qs,
    raw_search: str,
    search_fields: Sequence[str],
    model_cls: type[models.Model] | None = None,
    *,
    include_refs_keywords: bool = True,
) -> models.QuerySet:
    """Apply fragment-based search to a queryset.

    Args:
        qs: The base queryset to filter.
        raw_search: Raw comma-separated search string from the user.
        search_fields: Field names to search (OR within each fragment).
        model_cls: The Django model class (used to detect ``refs`` field).
        include_refs_keywords: Whether to also search ``refs.keywords``.

    Returns:
        Filtered queryset. All fragments are ANDed; fields within each
        fragment are ORed.

    Fragment modes:
        - ``startswith`` (default) → ``field__istartswith``
        - ``contains`` (``@`` prefix) → ``field__icontains``
        - Keywords always use ``icontains`` regardless of mode.
    """
    fragments = parse_fragments(raw_search)
    if not fragments:
        return qs

    # Detect refs JSON field
    has_refs = False
    if include_refs_keywords and model_cls is not None:
        try:
            field_names = {f.name for f in model_cls._meta.get_fields()}
            has_refs = "refs" in field_names
        except Exception:
            pass

    for frag in fragments:
        or_q = models.Q()

        # Scalar field matching
        for field in search_fields:
            if frag.mode == "startswith":
                or_q |= models.Q(**{f"{field}__istartswith": frag.value})
            else:
                or_q |= models.Q(**{f"{field}__icontains": frag.value})

        # Keyword matching (always icontains — keywords are individual tokens)
        if has_refs:
            or_q |= models.Q(**{"refs__keywords__icontains": frag.value})

        qs = qs.filter(or_q)

    return qs

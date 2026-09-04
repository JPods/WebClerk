"""Shared fragment-based search utilities with PostgreSQL Full-Text Search.

Extracted from PrefixAndSearchView.build_query() and enhanced with:
- ``@`` contains modifier for wc2-parity fragment search
- PostgreSQL FTS via SearchVector/SearchQuery for ranked results
- Trigram similarity for typo tolerance (requires pg_trgm extension)

Usage from views::

    from common.search_utils import parse_fragments, build_fragment_query

    qs = build_fragment_query(qs, raw_search, search_fields, ModelCls)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

from django.db import models

from apps.core.services.record_keywords import strip_alphanum

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Fragment:
    """A single parsed search fragment."""
    value: str                          # lowercased, trimmed
    value_alphanum: str                 # non-alphanumeric stripped for keyword matching
    mode: str                           # "startswith" | "contains"


def parse_fragments(raw: str) -> list[Fragment]:
    """Parse a comma-separated search string into typed fragments.

    - Split on comma (with optional surrounding whitespace)
    - ``@`` prefix → contains mode (``@`` stripped from value)
    - No prefix   → startswith mode
    - Empty / whitespace-only fragments are dropped
    - Values are lowercased for case-insensitive matching
    - Alphanum-stripped version stored for keyword matching
    """
    if not raw or not raw.strip():
        return []

    fragments: list[Fragment] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if part.startswith("@") and len(part) > 1:
            val = part[1:].lower()
            fragments.append(Fragment(value=val, value_alphanum=strip_alphanum(val), mode="contains"))
        else:
            val = part.lower()
            fragments.append(Fragment(value=val, value_alphanum=strip_alphanum(val), mode="startswith"))
    return fragments


def _has_fts_support() -> bool:
    """Check if PostgreSQL FTS imports are available."""
    try:
        from django.contrib.postgres.search import SearchVector, SearchQuery  # noqa: F401
        return True
    except ImportError:
        return False


def trigram_search(
    qs,
    search_term: str,
    field_name: str,
    threshold: float = 0.3,
) -> models.QuerySet:
    """Fuzzy search using PostgreSQL trigram similarity.

    Useful for typo-tolerant name lookups. Requires pg_trgm extension.
    Returns queryset annotated with similarity score, ordered by relevance.

    Usage:
        qs = trigram_search(Contact.objects.active(), "smth", "name_last")
    """
    try:
        from django.contrib.postgres.search import TrigramSimilarity
    except ImportError:
        # Fallback to icontains
        return qs.filter(**{f"{field_name}__icontains": search_term})

    return (
        qs.annotate(similarity=TrigramSimilarity(field_name, search_term))
        .filter(similarity__gte=threshold)
        .order_by('-similarity')
    )


def _build_fts_query(
    qs,
    fragments: list[Fragment],
    search_fields: Sequence[str],
    model_cls: type[models.Model],
    has_refs: bool,
) -> models.QuerySet:
    """Build a PostgreSQL FTS query with ranking.

    Uses SearchVector across text fields + SearchQuery for each fragment.
    Falls back to icontains for JSON refs.keywords (FTS doesn't index JSON).
    """
    from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

    # Identify text fields that FTS can index (CharField, TextField, etc.)
    text_types = {'CharField', 'TextField', 'EmailField', 'URLField', 'SlugField'}
    fts_fields = []
    for field_name in search_fields:
        try:
            field_obj = model_cls._meta.get_field(field_name)
            if hasattr(field_obj, 'get_internal_type') and field_obj.get_internal_type() in text_types:
                fts_fields.append(field_name)
        except Exception:
            continue

    if not fts_fields:
        # No FTS-eligible fields — fall back to simple matching
        return _build_simple_query(qs, fragments, search_fields, has_refs)

    # Build SearchVector from all eligible text fields
    vector = SearchVector(fts_fields[0], config='english')
    for field_name in fts_fields[1:]:
        vector = vector + SearchVector(field_name, config='english')

    # Build combined query from all fragments
    combined_sq = None
    for frag in fragments:
        # Use plainto_tsquery for natural language matching (handles stemming)
        sq = SearchQuery(frag.value, config='english', search_type='plain')
        if combined_sq is None:
            combined_sq = sq
        else:
            combined_sq = combined_sq & sq  # AND between fragments

    if combined_sq is None:
        return qs

    # Apply FTS filter + ranking
    qs = qs.annotate(
        search_vector=vector,
        search_rank=SearchRank(vector, combined_sq),
    ).filter(search_vector=combined_sq)

    # Also include refs.keywords matches (icontains — FTS can't index JSON)
    # Use alphanum-stripped value so "555-1234" matches stored "5551234"
    if has_refs:
        refs_q = models.Q()
        for frag in fragments:
            kw = frag.value_alphanum or frag.value
            refs_q &= models.Q(refs__keywords__icontains=kw)
        # Union: FTS results OR keyword matches
        qs = qs | qs.model.objects.filter(refs_q)

    # Order by rank (best matches first), then by dt_created
    qs = qs.order_by('-search_rank')

    return qs


def _build_simple_query(
    qs,
    fragments: list[Fragment],
    search_fields: Sequence[str],
    has_refs: bool,
) -> models.QuerySet:
    """Fallback: simple icontains/istartswith matching (original behavior)."""
    combined = _build_and_chain(fragments, search_fields, has_refs)
    if combined:
        qs = qs.filter(combined)
    return qs


def _build_and_chain(
    fragments: list[Fragment],
    search_fields: Sequence[str],
    has_refs: bool,
) -> models.Q:
    """Build an AND chain of fragment queries. Each fragment ORs across fields."""
    combined = models.Q()
    for frag in fragments:
        or_q = models.Q()
        for field in search_fields:
            if frag.mode == "startswith":
                or_q |= models.Q(**{f"{field}__istartswith": frag.value})
            else:
                or_q |= models.Q(**{f"{field}__icontains": frag.value})
        # Keywords: icontains on JSON array — PostgreSQL searches serialized text.
        # Use alphanum-stripped value so "555-1234" matches stored "5551234"
        if has_refs:
            kw = frag.value_alphanum or frag.value
            or_q |= models.Q(**{"refs__keywords__icontains": kw})
        combined &= or_q
    return combined


def build_fragment_query(
    qs,
    raw_search: str,
    search_fields: Sequence[str],
    model_cls: type[models.Model] | None = None,
    *,
    include_refs_keywords: bool = True,
    use_fts: bool = True,
) -> models.QuerySet:
    """Apply fragment-based search to a queryset.

    Args:
        qs: The base queryset to filter.
        raw_search: Raw search string from the user.
        search_fields: Field names to search (OR within each fragment).
        model_cls: The Django model class (used to detect ``refs`` field).
        include_refs_keywords: Whether to also search ``refs.keywords``.
        use_fts: Use PostgreSQL Full-Text Search when available (default True).

    Returns:
        Filtered queryset (ranked by relevance when FTS is active).

    Syntax:
        - Comma = AND: ``bil,jame`` → starts with "bil" AND starts with "jame"
        - Pipe = OR:   ``612,bil|405,bil`` → (612 AND bil) OR (405 AND bil)
        - ``@`` prefix = contains: ``@smith`` → field contains "smith"
        - Keywords use ``icontains`` (JSON array elements are individual tokens).
    """
    if not raw_search or not raw_search.strip():
        return qs

    # Detect refs JSON field
    has_refs = False
    if include_refs_keywords and model_cls is not None:
        try:
            field_names = {f.name for f in model_cls._meta.get_fields()}
            has_refs = "refs" in field_names
        except Exception:
            pass

    # Split on pipe for OR groups, each group is comma-separated AND
    or_groups = raw_search.split("|")

    # For single group without pipe, try FTS for better ranking
    if len(or_groups) == 1 and use_fts and _has_fts_support() and model_cls is not None:
        fragments = parse_fragments(or_groups[0])
        if fragments:
            # Only use FTS when all fragments are startswith mode
            # (contains mode with @ prefix uses icontains directly)
            all_startswith = all(f.mode == "startswith" for f in fragments)
            if all_startswith:
                try:
                    return _build_fts_query(qs, fragments, search_fields, model_cls, has_refs)
                except Exception:
                    logger.debug('FTS query failed, falling back to simple search', exc_info=True)

    # Fallback: original pipe-separated OR logic with simple matching
    combined_or = models.Q()
    for group in or_groups:
        fragments = parse_fragments(group)
        if not fragments:
            continue
        combined_or |= _build_and_chain(fragments, search_fields, has_refs)

    if combined_or:
        qs = qs.filter(combined_or)

    return qs

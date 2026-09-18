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
    contact, email, phone, address, domain,
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
# Enhanced canonical model key mapping for refined link resolution
# Maps various model name formats to their canonical singular forms
CANONICAL_MODEL_KEYS = {
    # Contact-related models
    'contacts': 'contact',
    'contact': 'contact',
    'person': 'contact',
    'people': 'contact',
    
    # Email models
    'emails': 'email',
    'email': 'email',
    'email_address': 'email',
    'email_addresses': 'email',
    
    # Phone models
    'phones': 'phone',
    'phone': 'phone',
    'phone_number': 'phone',
    'phone_numbers': 'phone',
    'telephone': 'phone',
    
    # Address models
    'address': 'address',
    'addresses': 'address',
    
    # Domain models
    'domains': 'domain',
    'domain': 'domain',
    'website': 'domain',
    'websites': 'domain',
    
    # Organization type models
    'customers': 'customer',
    'customer': 'customer',
    'client': 'customer',
    'clients': 'customer',
    
    'vendors': 'vendor',
    'vendor': 'vendor',
    'supplier': 'vendor',
    'suppliers': 'vendor',
    
    'manufacturers': 'manufacturer',
    'manufacturer': 'manufacturer',
    'maker': 'manufacturer',
    'makers': 'manufacturer',
    
    'reps': 'rep',
    'rep': 'rep',
    'representative': 'rep',
    'representatives': 'rep',
    'sales_rep': 'rep',
    'sales_reps': 'rep',
    
    # Generic cross-type models
    'orders': 'order',
    'order': 'order',
    
    'projects': 'project',
    'project': 'project',
    'job': 'project',
    'jobs': 'project',
    
    'documents': 'document',
    'document': 'document',
    'doc': 'document',
    'docs': 'document',
    'file': 'document',
    'files': 'document',
}

def resolve_canonical_model_key(model_key: str) -> str:
    """Resolve a model key to its canonical form.
    
    Args:
        model_key: Input model key (can be plural, singular, or alternative name)
        
    Returns:
        Canonical model key in singular form
    """
    if not model_key:
        return ''
        
    # Convert to lowercase and strip whitespace
    key_lower = model_key.lower().strip()
    
    # Direct lookup in canonical mapping
    if key_lower in CANONICAL_MODEL_KEYS:
        return CANONICAL_MODEL_KEYS[key_lower]
    
    # Try to singularize common plural forms
    if key_lower.endswith('ies'):
        # companies -> company
        singular = key_lower[:-3] + 'y'
    elif key_lower.endswith('s') and not key_lower.endswith('ss'):
        # contacts -> contact
        singular = key_lower[:-1]
    else:
        singular = key_lower
        
    # Check if the singular form exists in our mapping
    if singular in CANONICAL_MODEL_KEYS:
        return CANONICAL_MODEL_KEYS[singular]
        
    # Return the original key if no canonical form found
    return model_key

def validate_model_key(model_key: str) -> bool:
    """Validate if a model key is recognized in the canonical mapping.
    
    Args:
        model_key: Model key to validate
        
    Returns:
        True if the key is recognized, False otherwise
    """
    canonical_key = resolve_canonical_model_key(model_key)
    return canonical_key in STANDARD_LINK_KEYS

# Canonical singular model_name keys
STANDARD_LINK_KEYS: tuple[str, ...] = (
    "contact",
    "email",
    "phone",
    "address",
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


def ensure_canonical_links(refs: dict | None, model_key: str | None = None) -> dict:
    """Ensure refs.links exists with canonical model key resolution.
    
    This function enhances ensure_standard_links by validating and resolving
    model keys to their canonical forms before creating link buckets.
    
    Args:
        refs: refs dict to enhance
        model_key: Optional model key for validation and canonical resolution
        
    Returns:
        The enhanced refs dict with canonical link structure
    """
    if model_key:
        # Validate and resolve the model key to canonical form
        canonical_key = resolve_canonical_model_key(model_key)
        if not validate_model_key(canonical_key):
            # If model key is not recognized, still create standard structure
            # but log a warning for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Unrecognized model key: {model_key} -> {canonical_key}")
    
    # Use the standard links structure but ensure canonical validation
    return ensure_standard_links(refs)


def get_canonical_link_keys(model_key: str) -> list[str]:
    """Get the canonical link keys for a given model key.
    
    Args:
        model_key: Input model key to resolve
        
    Returns:
        List of canonical link keys that should be present for this model
    """
    canonical_key = resolve_canonical_model_key(model_key)
    
    # Base link keys that all models should have
    base_keys = ['contact', 'email', 'phone', 'address', 'domain']
    
    # Model-specific additional keys
    model_specific_keys = {
        'customer': ['vendor', 'manufacturer', 'rep'],
        'vendor': ['customer', 'manufacturer', 'rep'],
        'order': ['project', 'document'],
        'project': ['order', 'document'],
        'document': ['order', 'project'],
    }
    
    # Get specific keys for this model, or empty list if not found
    specific_keys = model_specific_keys.get(canonical_key, [])
    
    return base_keys + specific_keys


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
    "CANONICAL_MODEL_KEYS",
    "resolve_canonical_model_key",
    "validate_model_key",
    "ensure_standard_links",
    "ensure_canonical_links",
    "get_canonical_link_keys",
    "default_extended_refs",
    "StandardLinksMixin",
]

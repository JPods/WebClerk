"""
Model Link Denormalization Templates.

Defines how models are represented when linked via refs.links and which
fields contribute to refs.keywords for searchability.

When a record is linked to another (e.g., customer to order), these templates
define:
1. keyword_fields: Fields to extract for search (lowercased, added to refs.keywords)
2. link_template: Structure of the refs.links.<model>[{...}] entry

Link template values are field paths on the source model:
- "id" → source.id
- "display_name" → source.display_name
- "org.display_name" → source.org.display_name (resolved via dotted path)
- null → Set at link time by the linking code

See readmes/topics/architecture/role-based-access-plan.md for full documentation.
"""
from typing import Any, Optional


# =============================================================================
# Link Templates by Model
# =============================================================================

MODEL_LINK_TEMPLATES: dict[str, dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # Organization Models
    # -------------------------------------------------------------------------
    
    "customer": {
        "keyword_fields": ["company", "display_name", "ida", "email", "phone"],
        "link_template": {
            "id": "id",
            "company": "display_name",
            "ida": "ida",
            "email": "email",
            "phone": "phone",
            "attention": "attention",
            "address_full": "address_full",
        },
    },
    
    "vendor": {
        "keyword_fields": ["company", "display_name", "ida", "email"],
        "link_template": {
            "id": "id",
            "company": "display_name",
            "ida": "ida",
            "email": "email",
            "phone": "phone",
            "attention": "attention",
            "address_full": "address_full",
        },
    },
    
    "manufacturer": {
        "keyword_fields": ["company", "display_name", "ida"],
        "link_template": {
            "id": "id",
            "company": "display_name",
            "ida": "ida",
            "commission_based": None,  # Set at link time: True for commission orders
        },
    },
    
    "employee": {
        "keyword_fields": ["display_name", "ida", "email"],
        "link_template": {
            "id": "id",
            "attention": "display_name",
            "ida": "ida",
            "email": "email",
            "role": None,  # Set at link time: "salesperson", "production", "admin"
        },
    },
    
    # -------------------------------------------------------------------------
    # Contact / Person Models
    # -------------------------------------------------------------------------
    
    "contact": {
        "keyword_fields": ["display_name", "email", "phone", "attention"],
        "link_template": {
            "id": "id",
            "attention": "display_name",
            "email": "email",
            "phone": "phone",
            "role": None,  # Set at link time: "buyer", "ap", "shipping"
        },
    },
    
    "rep": {
        "keyword_fields": ["display_name", "ida", "company", "email"],
        "link_template": {
            "id": "id",
            "attention": "display_name",
            "company": "org.display_name",  # Dotted path to rep's org
            "ida": "ida",
            "email": "email",
            "role": None,  # "salesperson", "support"
            "commission_pc": None,  # e.g., 60.0
        },
    },
    
    # -------------------------------------------------------------------------
    # Product Models
    # -------------------------------------------------------------------------
    
    "item": {
        "keyword_fields": ["ida", "name", "sku", "upc", "manufacturer_part_number"],
        "link_template": {
            "id": "id",
            "ida": "ida",
            "name": "name",
            "sku": "sku",
            "description": "description",
        },
    },
    
    "category": {
        "keyword_fields": ["name", "code"],
        "link_template": {
            "id": "id",
            "name": "name",
            "code": "code",
        },
    },
    
    # -------------------------------------------------------------------------
    # Transaction Models
    # -------------------------------------------------------------------------
    
    "order": {
        "keyword_fields": ["ida", "name"],
        "link_template": {
            "id": "id",
            "ida": "ida",
            "name": "name",
            "status": "status",
            "total": "totals.total",
        },
    },
    
    "invoice": {
        "keyword_fields": ["ida", "name"],
        "link_template": {
            "id": "id",
            "ida": "ida",
            "name": "name",
            "status": "status",
            "total": "totals.total",
            "balance": "totals.balance",
        },
    },
    
    "proposal": {
        "keyword_fields": ["ida", "name"],
        "link_template": {
            "id": "id",
            "ida": "ida",
            "name": "name",
            "status": "status",
            "total": "totals.total",
        },
    },
    
    "purchase": {
        "keyword_fields": ["ida", "name"],
        "link_template": {
            "id": "id",
            "ida": "ida",
            "name": "name",
            "status": "status",
            "total": "totals.total",
        },
    },
    
    # -------------------------------------------------------------------------
    # Supporting Models
    # -------------------------------------------------------------------------
    
    "document": {
        "keyword_fields": ["name", "filename"],
        "link_template": {
            "id": "id",
            "name": "name",
            "filename": "filename",
            "file_type": "file_type",
        },
    },
    
    "project": {
        "keyword_fields": ["name", "ida", "code"],
        "link_template": {
            "id": "id",
            "name": "name",
            "ida": "ida",
            "code": "code",
            "status": "status",
        },
    },
    
    "action": {
        "keyword_fields": ["name", "description"],
        "link_template": {
            "id": "id",
            "name": "name",
            "status": "status",
            "action_type": "action_type",
        },
    },
    
    "warehouse": {
        "keyword_fields": ["name", "code"],
        "link_template": {
            "id": "id",
            "name": "name",
            "code": "code",
        },
    },
    
    "glaccount": {
        "keyword_fields": ["name", "account_number", "ida"],
        "link_template": {
            "id": "id",
            "name": "name",
            "account_number": "account_number",
            "ida": "ida",
        },
    },
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_link_template(model_name: str) -> dict[str, Any]:
    """
    Get the link template for a model.
    
    Returns empty dict if no template defined.
    """
    config = MODEL_LINK_TEMPLATES.get(model_name, {})
    return config.get("link_template", {})


def get_keyword_fields(model_name: str) -> list[str]:
    """
    Get the keyword fields for a model.
    
    Returns empty list if no fields defined.
    """
    config = MODEL_LINK_TEMPLATES.get(model_name, {})
    return config.get("keyword_fields", [])


def resolve_dotted_path(obj: Any, path: str) -> Any:
    """
    Resolve a dotted path on an object.
    
    Example:
        resolve_dotted_path(order, "totals.total") → order.totals["total"]
        resolve_dotted_path(rep, "org.display_name") → rep.org.display_name
    
    Args:
        obj: The source object
        path: Dotted path like "org.display_name" or "totals.total"
    
    Returns:
        Resolved value or None if path doesn't exist
    """
    if not path or obj is None:
        return None
    
    parts = path.split(".")
    current = obj
    
    for part in parts:
        if current is None:
            return None
        
        # Try attribute access first
        if hasattr(current, part):
            current = getattr(current, part)
        # Then dict access for JSONFields
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    
    return current


def build_link_entry(
    source_obj: Any,
    model_name: str,
    overrides: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """
    Build a refs.links entry for a model instance.
    
    Uses the link_template to extract fields from source_obj,
    then applies any overrides for fields that are set at link time.
    
    Args:
        source_obj: The model instance being linked
        model_name: Model name to get template for
        overrides: Values for null template fields (role, commission_pc, etc.)
    
    Returns:
        Dict suitable for refs.links.<model>[]
    
    Example:
        build_link_entry(employee, "employee", {"role": "salesperson"})
        → {"id": 42, "attention": "John Doe", "ida": "EMP-001", "role": "salesperson"}
    """
    template = get_link_template(model_name)
    if not template:
        # Minimal fallback
        return {"id": getattr(source_obj, "id", None)}
    
    entry = {}
    for dest_field, source_path in template.items():
        if source_path is None:
            # Field to be set at link time
            if overrides and dest_field in overrides:
                entry[dest_field] = overrides[dest_field]
        else:
            # Resolve from source object
            value = resolve_dotted_path(source_obj, source_path)
            if value is not None:
                entry[dest_field] = value
    
    return entry


def extract_keywords(source_obj: Any, model_name: str) -> list[str]:
    """
    Extract keyword values from a model instance.
    
    Returns lowercased, non-empty string values from keyword_fields.
    
    Args:
        source_obj: The model instance
        model_name: Model name to get keyword_fields for
    
    Returns:
        List of keyword strings for refs.keywords
    
    Example:
        extract_keywords(customer, "customer")
        → ["acme corp", "ACM-001", "orders@acme.com"]
    """
    fields = get_keyword_fields(model_name)
    if not fields:
        return []
    
    keywords = []
    for field in fields:
        value = resolve_dotted_path(source_obj, field)
        if value and isinstance(value, str):
            keyword = value.strip().lower()
            if keyword:
                keywords.append(keyword)
    
    return keywords

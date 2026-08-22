"""
Role-Based Access Control Defaults.

Code-based default configurations for roles. These serve as the base layer
that can be overridden by ModelRoleConfig database records and then by
company-specific Settings.

Override priority:
    1. Code defaults (this file)
    2. ModelRoleConfig database records
    3. Company-specific Settings records
    4. User-specific overrides (future)

See readmes/topics/architecture/role-based-access-plan.md for full documentation.
"""
from typing import Any

# =============================================================================
# Role Definitions
# =============================================================================

ROLE_DEFAULTS: dict[str, dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # Portal Roles (External Users)
    # -------------------------------------------------------------------------
    
    "user_customer": {
        "is_portal": True,
        "description": "Customer portal user - view own orders/invoices",
        # Portal users: no cost visibility, no price_level changes, no negative qty
        "restricted_fields": {
            "edit_deny": ["price_level"],
            "negative_quantity": False,
            "view_deny": ["cost", "cost.standard", "cost.last", "cost.avg", "cost.landed"],
        },
        "models": {
            "order": {
                "query_filters": {
                    "OR": [
                        {"customer_id__in": "$user.org_ids.customer"},
                        {"refs__links__customer__contains": [{"id": "$user.org_ids.customer"}]},
                    ]
                },
                "view_fields": [
                    "id", "ida", "status", "totals.total", "totals.balance",
                    "dt_created", "dt_modified", "lines", "refs.links.contact",
                    "customer_id", "address_full", "attention", "notes",
                ],
                "edit_fields": [],
                "allow_create": False,
                "allow_delete": False,
            },
            "invoice": {
                "query_filters": {
                    "OR": [
                        {"customer_id__in": "$user.org_ids.customer"},
                        {"refs__links__customer__contains": [{"id": "$user.org_ids.customer"}]},
                    ]
                },
                "view_fields": [
                    "id", "ida", "status", "totals.total", "totals.balance",
                    "dt_created", "lines", "customer_id",
                ],
                "edit_fields": [],
                "allow_create": False,
                "allow_delete": False,
            },
            "proposal": {
                "query_filters": {
                    "OR": [
                        {"customer_id__in": "$user.org_ids.customer"},
                        {"refs__links__customer__contains": [{"id": "$user.org_ids.customer"}]},
                    ]
                },
                "view_fields": [
                    "id", "ida", "status", "totals.total", "dt_created", "lines",
                ],
                "edit_fields": [],
                "allow_create": False,
                "allow_delete": False,
            },
            "action": {
                "query_filters": {
                    "refs__links__customer__contains": [{"id": "$user.org_ids.customer"}]
                },
                "view_fields": "*",
                "edit_fields": ["notes", "refs.tags"],
                "allow_create": True,  # Can create new action requests
                "allow_delete": False,
            },
        },
    },
    
    "user_vendor": {
        "is_portal": True,
        "description": "Vendor portal user - view purchases and supplied inventory",
        "models": {
            "purchase": {
                "query_filters": {
                    "OR": [
                        {"vendor_id__in": "$user.org_ids.vendor"},
                        {"refs__links__vendor__contains": [{"id": "$user.org_ids.vendor"}]},
                    ]
                },
                "view_fields": [
                    "id", "ida", "status", "totals.total", "dt_created", "lines",
                    "vendor_id", "address_full", "attention",
                ],
                "edit_fields": [],
                "allow_create": False,
                "allow_delete": False,
            },
            "item": {
                "query_filters": {
                    "refs__links__vendor__contains": [{"id": "$user.org_ids.vendor"}],
                    "metadata__flags__published": True,
                },
                "view_fields": [
                    "id", "ida", "name", "description", "sku",
                    "quantity.on_hand", "quantity.available", "quantity.on_po",
                    "quantity.inventory_min", "quantity.inventory_max",
                    "quantity.vendor_min", "quantity.vendor_max",
                ],
                "edit_fields": [
                    "quantity.vendor_min", "quantity.vendor_max",
                ],
                "allow_create": False,
                "allow_delete": False,
            },
            "action": {
                "query_filters": {
                    "refs__links__vendor__contains": [{"id": "$user.org_ids.vendor"}]
                },
                "view_fields": "*",
                "edit_fields": ["notes"],
                "allow_create": True,
                "allow_delete": False,
            },
        },
    },
    
    "user_manufacturer": {
        "is_portal": True,
        "description": "Manufacturer portal - purchases, inventory, commission orders",
        "models": {
            "purchase": {
                "query_filters": {
                    "OR": [
                        {"manufacturer_id__in": "$user.org_ids.manufacturer"},
                        {"refs__links__manufacturer__contains": [{"id": "$user.org_ids.manufacturer"}]},
                    ]
                },
                "view_fields": [
                    "id", "ida", "status", "totals.total", "dt_created", "lines",
                ],
                "edit_fields": [],
                "allow_create": False,
                "allow_delete": False,
            },
            "order": {
                # Commission-based orders where manufacturer ships
                "query_filters": {
                    "is_commission": True,
                    "refs__links__manufacturer__contains": [
                        {"id": "$user.org_ids.manufacturer", "commission_based": True}
                    ]
                },
                "view_fields": [
                    "id", "ida", "status", "totals.total", "dt_created",
                    "lines", "customer_id", "refs.links.customer",
                    "address_full", "attention", "notes",
                ],
                "edit_fields": ["status"],  # Limited: can mark shipped
                "allow_create": False,
                "allow_delete": False,
            },
            "item": {
                "query_filters": {
                    "manufacturer_id__in": "$user.org_ids.manufacturer",
                    "metadata__flags__published": True,
                },
                "view_fields": [
                    "id", "ida", "name", "description",
                    "inventory.on_hand", "inventory.available",
                ],
                "edit_fields": [],
                "allow_create": False,
                "allow_delete": False,
            },
            "action": {
                "query_filters": {
                    "refs__links__manufacturer__contains": [{"id": "$user.org_ids.manufacturer"}]
                },
                "view_fields": "*",
                "edit_fields": ["notes", "status"],
                "allow_create": True,
                "allow_delete": False,
            },
        },
    },
    
    "user_rep": {
        "is_portal": True,
        "description": "Sales rep - orders for assigned customers",
        "models": {
            "order": {
                "query_filters": {
                    "refs__links__rep__contains": [{"id": "$user.contact_id"}]
                },
                "view_fields": "*",
                "edit_fields": ["lines", "notes", "status", "refs.tags", "attention"],
                "allow_create": True,
                "allow_delete": False,
            },
            "proposal": {
                "query_filters": {
                    "refs__links__rep__contains": [{"id": "$user.contact_id"}]
                },
                "view_fields": "*",
                "edit_fields": ["lines", "notes", "status", "refs.tags"],
                "allow_create": True,
                "allow_delete": False,
            },
            "invoice": {
                "query_filters": {
                    "refs__links__rep__contains": [{"id": "$user.contact_id"}]
                },
                "view_fields": "*",
                "edit_fields": [],  # Read-only
                "allow_create": False,
                "allow_delete": False,
            },
            "customer": {
                "query_filters": {
                    "refs__links__rep__contains": [{"id": "$user.contact_id"}]
                },
                "view_fields": [
                    "id", "company", "ida", "email", "phone", "address_full",
                    "refs.links.contact", "refs.links.rep",
                ],
                "edit_fields": [],
                "allow_create": False,
                "allow_delete": False,
            },
            "contact": {
                "query_filters": {
                    "OR": [
                        {"refs__links__rep__contains": [{"id": "$user.contact_id"}]},
                        {"customer__refs__links__rep__contains": [{"id": "$user.contact_id"}]},
                    ]
                },
                "view_fields": [
                    "id", "display_name", "email", "phone", "refs.links.customer",
                ],
                "edit_fields": [],
                "allow_create": False,
                "allow_delete": False,
            },
            "item": {
                "query_filters": {"metadata__flags__published": True},
                "view_fields": [
                    "id", "ida", "name", "description", "sku",
                    "sell.price", "inventory.available",
                ],
                "edit_fields": [],
                "allow_create": False,
                "allow_delete": False,
            },
            "action": {
                "query_filters": {
                    "refs__links__rep__contains": [{"id": "$user.contact_id"}]
                },
                "view_fields": "*",
                "edit_fields": ["notes", "status", "refs.tags"],
                "allow_create": True,
                "allow_delete": False,
            },
        },
    },
    
    # -------------------------------------------------------------------------
    # Internal Roles (Employees)
    # -------------------------------------------------------------------------
    
    "user_sales": {
        "is_portal": False,
        "description": "Internal sales - all customer transactions",
        # Staff authority restrictions (2026-06-27):
        #   - price_level: NOT editable (staff/admin only)
        #   - negative quantity: NOT allowed (staff/admin only for returns)
        #   - cost fields: NOT visible (staff/admin only)
        "restricted_fields": {
            "edit_deny": ["price_level"],           # on order/invoice lines — staff only
            "negative_quantity": False,              # returns require staff authority
            "view_deny": ["cost", "cost.standard", "cost.last", "cost.avg", "cost.landed"],
        },
        "models": {
            "order": {
                "query_filters": {},  # All orders
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": False,
            },
            "proposal": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": False,
            },
            "invoice": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": ["status", "notes", "refs.tags"],  # Limited edit
                "allow_create": True,
                "allow_delete": False,
            },
            "customer": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": False,
            },
            "contact": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": False,
            },
            "item": {
                "query_filters": {},
                "view_fields": "*",
                "view_deny": ["cost"],  # Cost hidden from sales — staff only
                "edit_fields": [],  # Read-only
                "allow_create": False,
                "allow_delete": False,
            },
            "action": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": False,
            },
        },
    },
    
    "user_production": {
        "is_portal": False,
        "description": "Production - product/inventory management",
        "models": {
            "item": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": False,
            },
            "bom": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": False,
            },
            "bomline": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": False,
            },
            "workorder": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": False,
            },
            "order": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": ["status", "lines.status"],  # Production status only
                "allow_create": False,
                "allow_delete": False,
            },
            "purchase": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": [],  # Read-only
                "allow_create": False,
                "allow_delete": False,
            },
            "action": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": False,
            },
        },
    },
    
    "user_accounting": {
        "is_portal": False,
        "description": "Accounting - financial transactions",
        "models": {
            "invoice": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": False,
            },
            "payment": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": False,
            },
            "ledger": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": False,
            },
            "glaccount": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": False,
            },
            "order": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": [],  # Read-only
                "allow_create": False,
                "allow_delete": False,
            },
            "customer": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": ["financial", "terms", "credit_limit"],  # Financial fields only
                "allow_create": False,
                "allow_delete": False,
            },
            "vendor": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": ["financial", "terms"],
                "allow_create": False,
                "allow_delete": False,
            },
            "action": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": False,
            },
        },
    },
    
    "user_warehouse": {
        "is_portal": False,
        "description": "Warehouse - inventory operations",
        "models": {
            "inventory": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": False,
            },
            "receipt": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": False,
            },
            "transfer": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": False,
            },
            "warehouse": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": False,
            },
            "item": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": ["inventory", "location", "bin"],  # Inventory fields only
                "allow_create": False,
                "allow_delete": False,
            },
            "purchase": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": ["status", "lines.received_qty"],  # Receiving only
                "allow_create": False,
                "allow_delete": False,
            },
            "order": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": ["status", "lines.picked_qty", "lines.shipped_qty"],  # Shipping only
                "allow_create": False,
                "allow_delete": False,
            },
            "action": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": False,
            },
        },
    },
    
    # -------------------------------------------------------------------------
    # Administrative Roles
    # -------------------------------------------------------------------------
    
    "admin": {
        "is_portal": False,
        "description": "Administrator - full application access",
        "models": {
            "*": {  # Wildcard matches all models
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": True,
            },
        },
    },
    
    "superuser": {
        "is_portal": False,
        "description": "Superuser - system owner with database access",
        "parent_role": "admin",
        "models": {
            "*": {
                "query_filters": {},
                "view_fields": "*",
                "edit_fields": "*",
                "allow_create": True,
                "allow_delete": True,
            },
        },
    },
}


# =============================================================================
# Role Hierarchy
# =============================================================================

ROLE_HIERARCHY = {
    "superuser": ["admin"],
    "admin": ["user_accounting", "user_warehouse", "user_production", "user_sales"],
    "user_sales": ["user_rep"],  # user_rep is a subset of user_sales
}


def get_role_ancestors(role: str) -> list[str]:
    """
    Get all ancestor roles for a given role.
    
    If user_rep inherits from user_sales which inherits from admin,
    this returns ["user_sales", "admin", "superuser"].
    """
    ancestors = []
    for parent, children in ROLE_HIERARCHY.items():
        if role in children:
            ancestors.append(parent)
            ancestors.extend(get_role_ancestors(parent))
    return ancestors


def get_effective_config(role: str, model_name: str) -> dict[str, Any]:
    """
    Get effective configuration for a role and model.
    
    Checks the role's config first, then parent role, then wildcard.
    """
    role_config = ROLE_DEFAULTS.get(role, {})
    models_config = role_config.get("models", {})
    
    # Direct match
    if model_name in models_config:
        return models_config[model_name]
    
    # Wildcard match
    if "*" in models_config:
        return models_config["*"]
    
    # Check parent role
    parent = role_config.get("parent_role")
    if parent:
        return get_effective_config(parent, model_name)
    
    # No config found
    return {}

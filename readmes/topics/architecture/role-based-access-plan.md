# Role-Based Access Control (RBAC) Plan

**Status:** ✅ Implemented  
**Date:** March 5, 2026  
**Last Updated:** March 5, 2026

---

## Overview

Implement a flexible role-based access control system that:
1. Filters queries based on user role and ownership
2. Controls field-level view/edit permissions
3. Provides denormalization templates for refs.links
4. Allows company-specific customization via Settings

---

## Roles

| Role | Type | Query Scope | Write Scope |
|------|------|-------------|-------------|
| `user_customer` | Portal | Own orders/invoices via FK or refs.links.customer | New action requests only |
| `user_vendor` | Portal | Own purchases + published inventory they supply | New action requests only |
| `user_manufacturer` | Portal | Own purchases + published inventory + commission orders | Action requests + limited fields |
| `user_rep` | Portal | Records where refs.links.rep contains their ID | Create orders for assigned customers |
| `user_sales` | Internal | All customer-facing transactions | Create/edit orders, proposals |
| `user_production` | Internal | All transactions | Edit product.* models |
| `user_accounting` | Internal | Payments, ledgers, GL, invoices | Apply payments, adjust ledgers |
| `user_warehouse` | Internal | Inventory, receipts, transfers | Inventory adjustments, receiving |
| `admin` | Internal | All models | All models |
| `superuser` | System | All models + Postgres | All models + Postgres |

### Role Hierarchy

```
superuser
  └── admin
        ├── user_accounting
        ├── user_warehouse
        ├── user_production
        └── user_sales
              └── user_rep (subset)

Portal roles (separate branch):
├── user_customer
├── user_vendor
└── user_manufacturer
```

---

## User ↔ Role ↔ Org Mapping

### User Profile

```python
# On User model or related profile
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    contact = models.ForeignKey('core.Contact', on_delete=models.SET_NULL, null=True)
    
    # Roles stored in refs for flexibility
    # refs.roles = ["user_sales", "user_production"]
```

### Contact ↔ Org Links

Contacts have FKs to their primary org:
```python
# Contact model
customer = models.ForeignKey('orgs.OrgBase', related_name='contacts_as_customer', ...)
vendor = models.ForeignKey('orgs.OrgBase', related_name='contacts_as_vendor', ...)
manufacturer = models.ForeignKey('orgs.OrgBase', related_name='contacts_as_manufacturer', ...)
employee = models.ForeignKey('orgs.OrgBase', related_name='contacts_as_employee', ...)  # Internal company
```

Plus denormalized refs.links for additional associations:
```python
contact.refs.links = {
    "customer": [{"id": 42, "company": "Acme Corp", ...}],
    "vendor": [{"id": 99, "company": "Supplier Inc", ...}],
}
```

### Org ↔ Contact Links (Bidirectional)

```python
customer.refs.links = {
    "contact": [
        {"id": 1, "attention": "John Doe", "email": "john@acme.com", "role": "buyer"},
        {"id": 2, "attention": "Jane Smith", "email": "jane@acme.com", "role": "ap"},
    ]
}
```

### User Role Resolution

```python
def get_user_roles(user) -> list[str]:
    """Get all roles for a user."""
    if user.is_superuser:
        return ["superuser"]
    
    profile = getattr(user, 'profile', None)
    if not profile or not profile.contact:
        return []
    
    contact = profile.contact
    refs = contact.refs or {}
    return refs.get("roles", [])

def get_user_org_ids(user, org_type: str) -> list[int]:
    """Get org IDs user is associated with for a given type."""
    profile = getattr(user, 'profile', None)
    if not profile or not profile.contact:
        return []
    
    contact = profile.contact
    ids = []
    
    # Primary FK
    fk_id = getattr(contact, f"{org_type}_id", None)
    if fk_id:
        ids.append(fk_id)
    
    # Additional from refs.links
    links = (contact.refs or {}).get("links", {}).get(org_type, [])
    ids.extend(link.get("id") for link in links if link.get("id"))
    
    return list(set(ids))
```

---

## Configuration Models

### RoleConfig

```python
class RoleConfig(BaseModel):
    """Role definition and global permissions."""
    
    role = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True)
    is_portal = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    parent_role = models.CharField(max_length=50, blank=True, null=True)  # Inheritance
    
    # Global permissions
    permissions = models.JSONField(default=dict)
    # {
    #   "can_create_orders": true,
    #   "can_delete": false,
    #   "can_export": true,
    # }
    
    class Meta:
        db_table = 'core_roleconfig'
```

### ModelRoleConfig

```python
class ModelRoleConfig(BaseModel):
    """Per-model, per-role configuration."""
    
    model_name = models.CharField(max_length=100, db_index=True)
    role = models.CharField(max_length=50, db_index=True)
    
    # Query filtering
    query_filters = models.JSONField(default=dict)
    # {
    #   "customer_id": "$user.org_ids.customer",
    #   "OR": [
    #     {"customer_id": "$user.org_ids.customer"},
    #     {"refs__links__customer__contains": [{"id": "$user.org_ids.customer"}]}
    #   ]
    # }
    
    # Field access - separate view and edit
    view_fields = models.JSONField(default=list)
    # ["id", "ida", "status", "totals.total", "refs.tags"]
    # Use "*" for all fields
    
    edit_fields = models.JSONField(default=list)
    # ["status", "notes", "refs.tags", "lines"]
    # Supports dotted paths: "refs.tags", "totals.discount"
    
    # Permissions
    allow_create = models.BooleanField(default=False)
    allow_delete = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'core_modelroleconfig'
        unique_together = [('model_name', 'role')]
```

### ModelLinkConfig

```python
class ModelLinkConfig(BaseModel):
    """Denormalization templates for refs.links."""
    
    model_name = models.CharField(max_length=100, unique=True, db_index=True)
    
    # Fields to extract for refs.keywords when this model is linked
    keyword_fields = models.JSONField(default=list)
    # ["company", "ida", "email", "attention"]
    
    # Template for refs.links.<model>[{...}]
    link_template = models.JSONField(default=dict)
    # {
    #   "id": "id",
    #   "company": "display_name", 
    #   "ida": "ida",
    #   "email": "email",
    #   "attention": "attention",
    #   "role": null,  # Set at link time
    #   "commission_based": null,  # For manufacturers
    #   "commission_pc": null,  # For reps
    # }
    
    class Meta:
        db_table = 'core_modellinkconfig'
```

---

## Default Configurations (Code)

### Role Defaults

```python
# apps/core/role_defaults.py

ROLE_DEFAULTS = {
    "user_customer": {
        "is_portal": True,
        "description": "Customer portal user - view own orders/invoices",
        "models": {
            "order": {
                "query_filters": {
                    "OR": [
                        {"customer_id__in": "$user.org_ids.customer"},
                        {"refs__links__customer__contains": [{"id": "$user.org_ids.customer"}]},
                    ]
                },
                "view_fields": ["id", "ida", "status", "totals.total", "totals.balance", 
                               "dt_created", "dt_modified", "lines", "refs.links.contact"],
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
                "view_fields": ["id", "ida", "status", "totals.total", "totals.balance",
                               "dt_created", "lines"],
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
                "view_fields": ["id", "ida", "status", "totals.total", "dt_created", "lines"],
                "edit_fields": [],
                "allow_create": False,
                "allow_delete": False,
            },
            "item": {
                "query_filters": {
                    "refs__links__vendor__contains": [{"id": "$user.org_ids.vendor"}],
                    "metadata__flags__published": True,
                },
                "view_fields": ["id", "ida", "name", "description", "inventory.on_hand"],
                "edit_fields": [],
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
                "view_fields": ["id", "ida", "status", "totals.total", "dt_created", "lines"],
                "edit_fields": [],
                "allow_create": False,
                "allow_delete": False,
            },
            "order": {
                # Commission-based orders where manufacturer ships
                "query_filters": {
                    "refs__links__manufacturer__contains": [
                        {"id": "$user.org_ids.manufacturer", "commission_based": True}
                    ]
                },
                "view_fields": ["id", "ida", "status", "totals.total", "dt_created", 
                               "lines", "customer", "refs.links.customer"],
                "edit_fields": ["status"],  # Limited: can mark shipped
                "allow_create": False,
                "allow_delete": False,
            },
            "item": {
                "query_filters": {
                    "manufacturer_id__in": "$user.org_ids.manufacturer",
                    "metadata__flags__published": True,
                },
                "view_fields": ["id", "ida", "name", "description", "inventory.on_hand"],
                "edit_fields": [],
                "allow_create": False,
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
                "edit_fields": ["lines", "notes", "status", "refs.tags"],
                "allow_create": True,
                "allow_delete": False,
            },
            "proposal": {
                "query_filters": {
                    "refs__links__rep__contains": [{"id": "$user.contact_id"}]
                },
                "view_fields": "*",
                "edit_fields": ["lines", "notes", "status"],
                "allow_create": True,
                "allow_delete": False,
            },
            "customer": {
                "query_filters": {
                    "refs__links__rep__contains": [{"id": "$user.contact_id"}]
                },
                "view_fields": ["id", "company", "ida", "email", "phone", "address_full",
                               "refs.links.contact"],
                "edit_fields": [],
                "allow_create": False,
                "allow_delete": False,
            },
            "item": {
                "query_filters": {"metadata__flags__published": True},
                "view_fields": ["id", "ida", "name", "description", "sell.price", 
                               "inventory.available"],
                "edit_fields": [],
                "allow_create": False,
                "allow_delete": False,
            },
        },
    },
    
    "user_sales": {
        "is_portal": False,
        "description": "Internal sales - all customer transactions",
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
                "edit_fields": ["status", "notes"],  # Limited edit
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
                "edit_fields": [],  # Read-only
                "allow_create": False,
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
        },
    },
    
    "admin": {
        "is_portal": False,
        "description": "Administrator - full application access",
        "models": {
            "*": {  # All models
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
        "description": "Superuser - system owner with Postgres access",
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
```

### Link Template Defaults

```python
# apps/core/link_defaults.py

MODEL_LINK_TEMPLATES = {
    "customer": {
        "keyword_fields": ["company", "ida", "email", "phone"],
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
        "keyword_fields": ["company", "ida", "email"],
        "link_template": {
            "id": "id",
            "company": "display_name",
            "ida": "ida",
            "email": "email",
            "phone": "phone",
            "attention": "attention",
        },
    },
    
    "manufacturer": {
        "keyword_fields": ["company", "ida"],
        "link_template": {
            "id": "id",
            "company": "display_name",
            "ida": "ida",
            "commission_based": None,  # Set at link time: True for commission orders
        },
    },
    
    "employee": {
        "keyword_fields": ["display_name", "ida"],
        "link_template": {
            "id": "id",
            "attention": "display_name",
            "ida": "ida",
            "email": "email",
            "role": None,  # Set at link time: "salesperson", "production", "admin"
        },
    },
    
    "rep": {
        "keyword_fields": ["display_name", "ida", "company"],
        "link_template": {
            "id": "id",
            "attention": "display_name",
            "company": "org.display_name",  # Dotted path resolution
            "ida": "ida",
            "role": None,  # "salesperson", "support"
            "commission_pc": None,  # e.g., 60.0
        },
    },
    
    "contact": {
        "keyword_fields": ["display_name", "email", "phone"],
        "link_template": {
            "id": "id",
            "attention": "display_name",
            "email": "email",
            "phone": "phone",
            "role": None,  # "buyer", "ap", "shipping"
        },
    },
    
    "item": {
        "keyword_fields": ["ida", "name", "sku"],
        "link_template": {
            "id": "id",
            "ida": "ida",
            "name": "name",
            "sku": "sku",
        },
    },
}
```

---

## Commission Order Support

### Transaction Model Field

```python
# In TransactionBaseModel
is_commission = models.BooleanField(default=False, db_index=True)
# True when WC3 user sells on behalf of manufacturer who ships
# WC3 invoices manufacturer for commission
```

### refs.links.manufacturer Entry

```json
{
  "refs": {
    "links": {
      "manufacturer": [{
        "id": 123,
        "company": "MFG Corp",
        "ida": "MFG-001",
        "commission_based": true
      }]
    }
  }
}
```

### Query Filter for Manufacturer Portal

```python
# Commission orders visible to manufacturer
{
    "refs__links__manufacturer__contains": [
        {"id": "$user.org_ids.manufacturer", "commission_based": True}
    ]
}
```

---

## Dotted Path Field Access

### Examples

| Path | Meaning |
|------|---------|
| `"*"` | All fields |
| `"id"` | Top-level field |
| `"totals.total"` | Nested JSON field |
| `"refs.tags"` | Refs tags array |
| `"refs.links.contact"` | Contact links array |
| `"lines"` | Related lines (entire array) |
| `"lines.status"` | Only status field on lines |
| `"lines.picked_qty"` | Only picked_qty on lines |

### Resolution Logic

```python
def is_field_allowed(field_path: str, allowed_fields: list) -> bool:
    """Check if a field path is allowed by the field list."""
    if "*" in allowed_fields:
        return True
    
    # Exact match
    if field_path in allowed_fields:
        return True
    
    # Parent path allows children
    parts = field_path.split(".")
    for i in range(len(parts)):
        parent = ".".join(parts[:i+1])
        if parent in allowed_fields:
            return True
    
    return False

def filter_data_by_fields(data: dict, allowed_fields: list, mode: str = "view") -> dict:
    """Filter record data to only allowed fields."""
    if "*" in allowed_fields:
        return data
    
    result = {}
    for field in allowed_fields:
        parts = field.split(".")
        # Navigate and copy allowed paths
        # ... implementation
    return result
```

---

## Settings Override Priority

```
1. Code Defaults (ROLE_DEFAULTS, MODEL_LINK_TEMPLATES)
   ↓
2. ModelRoleConfig / RoleConfig database records
   ↓  
3. Company-specific Settings records
   ↓
4. User-specific overrides (future)
```

### Resolution

```python
def get_model_role_config(model_name: str, role: str) -> dict:
    """Get effective configuration with override chain."""
    
    # 1. Start with code defaults
    config = copy.deepcopy(
        ROLE_DEFAULTS.get(role, {}).get("models", {}).get(model_name, {})
    )
    
    # Inherit from parent role if not defined
    if not config:
        parent = ROLE_DEFAULTS.get(role, {}).get("parent_role")
        if parent:
            config = copy.deepcopy(
                ROLE_DEFAULTS.get(parent, {}).get("models", {}).get(model_name, {})
            )
    
    # Check wildcard
    if not config:
        config = copy.deepcopy(
            ROLE_DEFAULTS.get(role, {}).get("models", {}).get("*", {})
        )
    
    # 2. Override with database ModelRoleConfig
    try:
        db_config = ModelRoleConfig.objects.get(model_name=model_name, role=role)
        if db_config.query_filters:
            config["query_filters"] = db_config.query_filters
        if db_config.view_fields:
            config["view_fields"] = db_config.view_fields
        if db_config.edit_fields:
            config["edit_fields"] = db_config.edit_fields
        config["allow_create"] = db_config.allow_create
        config["allow_delete"] = db_config.allow_delete
    except ModelRoleConfig.DoesNotExist:
        pass
    
    # 3. Override with company Settings (future)
    # company_settings = get_company_setting(f"rbac.{role}.{model_name}")
    # if company_settings:
    #     config.update(company_settings)
    
    return config
```

---

## Implementation Phases

### Phase 1: Models & Defaults ✅
- [x] Create `RoleConfig`, `ModelRoleConfig`, `ModelLinkConfig` models → [apps/core/models/rbac.py](../../../apps/core/models/rbac.py)
- [x] Create `role_defaults.py` with ROLE_DEFAULTS → [apps/core/services/role_defaults.py](../../../apps/core/services/role_defaults.py)
- [x] Create `link_defaults.py` with MODEL_LINK_TEMPLATES → [apps/core/services/link_defaults.py](../../../apps/core/services/link_defaults.py)
- [x] Add `is_commission` field to TransactionBaseModel
- [x] Migration for new models and field

### Phase 2: User Profile ✅
- [x] Create/update UserProfile model with contact FK → [apps/core/models/rbac.py](../../../apps/core/models/rbac.py#L199)
- [x] Add `refs.roles[]` support on Contact model (via BaseModel.refs JSONField)
- [x] Implement `get_user_roles()`, `get_user_org_ids()` → [apps/core/services/role_filter.py](../../../apps/core/services/role_filter.py)

### Phase 3: Query Filtering ✅
- [x] Implement `inject_role_filters()` service → [apps/core/services/role_filter.py](../../../apps/core/services/role_filter.py)
- [x] Integrate into `WCAPIGetView.post()`
- [x] Handle OR conditions and variable resolution

### Phase 4: Field Projection ✅
- [x] Implement `filter_data_by_fields()` for view → [apps/core/services/field_projection.py](../../../apps/core/services/field_projection.py)
- [x] Implement `validate_edit_fields()` for save
- [x] Integrate into response serialization → [apps/core/views/wcapi.py](../../../apps/core/views/wcapi.py)
- [x] Integrate into save validation → [apps/transactions/views/wcapi.py](../../../apps/transactions/views/wcapi.py)

### Phase 5: Link Denormalization ✅
- [x] Update `denormalize_org_links()` to use templates → [apps/transactions/services/denormalize_org_links.py](../../../apps/transactions/services/denormalize_org_links.py)
- [x] Update keyword refresh to use `keyword_fields`
- [x] Add `commission_based` support

### Phase 6: Frontend Integration ✅
- [x] API endpoint for user's effective permissions → [apps/core/views/permissions.py](../../../apps/core/views/permissions.py)
- [x] React context for role-based UI rendering → `React2025/src/context/PermissionsContext.tsx`
- [x] Field-level visibility/editability in forms → `React2025/src/components/PermissionGuards.tsx`

### Phase 7: Admin UI + Role Seeding ✅
- [x] CRUD for RoleConfig → [apps/core/admin.py](../../../apps/core/admin.py#L306)
- [x] CRUD for ModelRoleConfig → [apps/core/admin.py](../../../apps/core/admin.py#L320)
- [x] CRUD for ModelLinkConfig → [apps/core/admin.py](../../../apps/core/admin.py#L336)
- [x] Seed management command → [apps/core/management/commands/seed_rbac_roles.py](../../../apps/core/management/commands/seed_rbac_roles.py)
- [x] Seeded 10 roles, 48 model role configurations

---

## API Endpoints

### Get User Permissions

```
GET /wcapi/permissions/
Response: {
    "roles": ["user_sales", "user_production"],
    "org_ids": {
        "customer": [],
        "vendor": [],
        "manufacturer": [],
        "employee": [1]
    },
    "contact_id": 42,
    "models": {
        "order": {
            "view": true,
            "view_fields": "*",
            "edit": true,
            "edit_fields": "*",
            "create": true,
            "delete": false
        },
        "item": {
            "view": true,
            "view_fields": "*",
            "edit": true,
            "edit_fields": "*",
            "create": true,
            "delete": false
        }
    }
}
```

---

## See Also

- [refs-pattern.md](refs-pattern.md) — Refs.links denormalization pattern
- [05-model-registry.md](../../05-model-registry.md) — Model registration

---

## Implementation Files

### Backend (webClerk3)

| File | Purpose |
|------|---------|
| `apps/core/models/rbac.py` | `RoleConfig`, `ModelRoleConfig`, `ModelLinkConfig`, `UserProfile` models |
| `apps/core/services/role_defaults.py` | Code defaults for all 10 roles |
| `apps/core/services/link_defaults.py` | Link template defaults for org types |
| `apps/core/services/role_filter.py` | Query filtering injection and variable resolution |
| `apps/core/services/field_projection.py` | Field-level view/edit filtering |
| `apps/core/views/permissions.py` | `/wcapi/permissions/` API endpoints |
| `apps/core/admin.py` | Django admin for RBAC models |
| `apps/core/management/commands/seed_rbac_roles.py` | Management command to seed roles |

### Frontend (React2025)

| File | Purpose |
|------|---------|
| `src/type/permissions.ts` | TypeScript types for permissions API |
| `src/context/PermissionsContext.tsx` | React context for role-based access |
| `src/components/PermissionGuards.tsx` | `PermissionGate`, `FieldGuard`, `ModelGuard` components |

### Database

Seeded via `python manage.py seed_rbac_roles`:
- **10 roles**: `user_customer`, `user_vendor`, `user_manufacturer`, `user_rep`, `user_sales`, `user_production`, `user_accounting`, `user_warehouse`, `admin`, `superuser`
- **48 model role configurations**: Per-model access rules for each role
- [06-api-conventions.md](../../06-api-conventions.md) — API envelope format

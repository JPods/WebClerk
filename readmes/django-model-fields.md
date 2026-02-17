# Django Model Field Definitions — webClerk3

Extracted from `/Users/williamjames/Documents/CommerceExpert/webClerk3` on 2026-02-13.

---

## Table of Contents
1. [CoreModel (abstract)](#1-coremodel-abstract)
2. [BaseModel (abstract, full composition)](#2-basemodel-abstract-full-composition)
3. [TransactionBaseModel (abstract)](#3-transactionbasemodel-abstract)
4. [BaseLineCore / BaseSellLineModel / BaseExecLineModel (abstract)](#4-baselinecore--baseselllinemodel--baseexeclinemodel-abstract)
5. [OrgBase (unified organization)](#5-orgbase-unified-organization)
6. [Customer / Vendor / Rep / Employee / Manufacturer (proxy models)](#6-proxy-models-customer-vendor-rep-employee-manufacturer)
7. [Contact](#7-contact)
8. [Item (catalog product)](#8-item-catalog-product)
9. [Order](#9-order)
10. [OrderLine](#10-orderline)
11. [Invoice](#11-invoice)
12. [InvoiceLine](#12-invoiceline)
13. [Payment](#13-payment)
14. [PaymentMethod](#14-paymentmethod)
15. [PaymentTerm](#15-paymentterm)
16. [PaymentApplication](#16-paymentapplication)
17. [Choices / Enums Reference](#17-choices--enums-reference)

---

## 1. CoreModel (abstract)

**File:** `common/models.py`  
**Purpose:** Identity + timestamps + optimistic version. Minimal required baseline.

| Field | Django Type | Details |
|-------|-----------|---------|
| `id` | `BigAutoField` | `primary_key=True` |
| `uuid` | `UUIDField` | `editable=False, unique=True, null=True, blank=True` |
| `ida` | `CharField(40)` | `blank=True, db_index=True` — soft id from external system |
| `dt_created` | `BigIntegerField` | `default=0, db_index=True` — millisecond epoch |
| `dt_modified` | `BigIntegerField` | `default=0, db_index=True` — millisecond epoch |
| `version` | `PositiveIntegerField` | `default=1` — optimistic concurrency |
| `is_active` | `BooleanField` | `default=True, db_index=True` |
| `security_level` | `IntegerField` | `default=0, blank=True, db_index=True` |

---

## 2. BaseModel (abstract, full composition)

**File:** `common/models.py`  
**Inherits:** `ActionsMixin`, `CoreModel`, `MetadataMixin`, `RefsMixin`, `KeywordsMixin`, `PrefsMixin`, `CommentsMixin`, `HealthMixin`, `LifecycleMixin`, `UniversalDictMixin`, `AtomicJSONMixin`

BaseModel composes all mixins. Every concrete model that extends BaseModel gets ALL of these fields:

### CoreModel fields (above)
(id, uuid, ida, dt_created, dt_modified, version, is_active, security_level)

### LifecycleMixin fields
| Field | Django Type | Details |
|-------|-----------|---------|
| `is_deleted` | `BooleanField` | `default=False, db_index=True` |
| `is_archived` | `BooleanField` | `default=False, db_index=True` |

### MetadataMixin fields
| Field | Django Type | Details |
|-------|-----------|---------|
| `metadata` | `JSONField` | `default=default_metadata` |

**`metadata` default structure:**
```json
{
  "security": "",
  "publish": "",
  "priority": "",
  "version": "1.0",
  "access": {"view": [], "edit": []},
  "resources": {"required": {}, "allocated": {}},
  "flow": {},
  "source": {},
  "images": {
    "primary": "",
    "gallery": [],
    "thumbnail": ""
  },
  "history": {
    "created":  {"dt": <ms_epoch>, "contact_id": 0},
    "modified": {"dt": <ms_epoch>, "contact_id": 0},
    "accessed": {"dt": <ms_epoch>, "contact_id": 0},
    "verified": {"dt": 0, "contact_id": 0},
    "synced":   {"dt": 0, "contact_id": 0}
  },
  "health": {
    "rating": 0,
    "completeness": 0,
    "accuracy": 0,
    "freshness": 0,
    "consistency": 0
  },
  "undefined": {}
}
```

### RefsMixin fields
| Field | Django Type | Details |
|-------|-----------|---------|
| `refs` | `JSONField` | `default=default_refs` |

**`refs` default structure:**
```json
{
  "keywords": [],
  "tags": [],
  "links": {"contact": [], "item": []},
  "parents": [],
  "depends_on": {},
  "categories": [],
  "related_ids": []
}
```

### PrefsMixin fields
| Field | Django Type | Details |
|-------|-----------|---------|
| `prefs` | `JSONField` | `default=default_prefs` |

**`prefs` default structure:**
```json
{"userdefined": {}}
```

### CommentsMixin fields
| Field | Django Type | Details |
|-------|-----------|---------|
| `comments` | `JSONField` | `default=default_comments` |

**`comments` default structure:**
```json
{
  "public": "",
  "process": "",
  "partner": "",
  "notes": []
}
```

### ActionsMixin fields
| Field | Django Type | Details |
|-------|-----------|---------|
| `actions` | `JSONField` | `default=dict, blank=True` |

**`actions` suggested structure:**
```json
{
  "required": true,
  "status": "pending|done|blocked",
  "who": 123,
  "when": 1737052800000,
  "what": "call vendor",
  "kind": "followup|review|ship|approve",
  "extra": {}
}
```

### HealthMixin fields
| Field | Django Type | Details |
|-------|-----------|---------|
| `health_rating` | `IntegerField` | `default=0` — Data quality rating 0-100 |

### GIN Indexes on BaseModel
- `refs` (GIN)
- `prefs` (GIN)
- `actions` (GIN)
- `actions->'status'` (btree via KeyTextTransform)
- `actions->'required'`
- `actions->'who'`
- `actions->'when'`

---

## 3. TransactionBaseModel (abstract)

**File:** `apps/transactions/models/base_transaction_model.py`  
**Inherits:** `BaseModel` (so includes ALL BaseModel fields above)

| Field | Django Type | Details |
|-------|-----------|---------|
| `total` | `DecimalField(18,6)` | `blank=True, null=True, db_index=True` — denormalized from totals.total |
| `balance` | `DecimalField(18,6)` | `blank=True, null=True, db_index=True` — denormalized from totals.balance |
| `status` | `CharField(32)` | `choices=TRANSACTION_STATUS_CHOICES, default="planned", db_index=True` |
| `priority` | `CharField(32)` | `blank=True, null=True` |
| `price_level` | `CharField(50)` | `blank=True, null=True` |
| `customer_id` | `BigIntegerField` | `default=0, db_index=True` |
| `manufacturer_id` | `BigIntegerField` | `default=0, db_index=True` |
| `vendor_id` | `BigIntegerField` | `default=0, db_index=True` |
| `parent_id` | `BigIntegerField` | `blank=True, null=True, db_index=True` — ID of parent transaction |
| `parent_model` | `CharField(20)` | `choices=TRANSACTION_PARENT_MODEL_CHOICES, blank=True, null=True, db_index=True` |
| `cost` | `JSONField` | `default=dict, blank=True, null=True` |
| `sell` | `JSONField` | `default=dict, blank=True, null=True` |
| `totals` | `JSONField` | `default=default_totals, blank=True, null=True` |
| `finance` | `JSONField` | `default=dict, blank=True, null=True` |
| `flow` | `JSONField` | `default=dict, blank=True, null=True` |
| `source` | `JSONField` | `default=dict, blank=True, null=True` |
| `actions` | `JSONField` | `default=dict, blank=True, null=True` |

**`totals` default structure:**
```json
{
  "subtotal": 0,
  "discount": 0,
  "taxable": 0,
  "tax": 0,
  "shipping": 0,
  "other": 0,
  "total": 0,
  "cost": 0,
  "margin": 0,
  "margin_pc": 0,
  "received": 0,
  "balance": 0
}
```

**`cost` (header) default structure:**
```json
{
  "line_sum_goods": null,
  "line_sum_tax": null,
  "line_sum_shipping": null,
  "line_sum_handling": null,
  "handling": null,
  "freight": null,
  "tax_rate": null,
  "tax": null,
  "commissions": null,
  "total": null
}
```

**`finance` default structure:**
```json
{
  "sales_tax_id": 0,
  "sales_tax_name": "",
  "sales_tax_rate": null,
  "sales_tax": null,
  "cost_tax_id": 0,
  "cost_tax_name": "",
  "cost_tax_rate": null,
  "cost_tax": null,
  "tax_subtotal": null,
  "tax_pc": null,
  "collection_expense": null,
  "exchange_expense": null
}
```

**Constants on class:**
- `STATUS_PLANNED = "planned"`
- `STATUS_RELEASED = "released"`
- `STATUS_IN_PROGRESS = "in_progress"`
- `STATUS_HOLD = "hold"`
- `STATUS_COMPLETE = "complete"`
- `STATUS_CANCELED = "canceled"`

---

## 4. BaseLineCore / BaseSellLineModel / BaseExecLineModel (abstract)

**File:** `apps/transactions/models/base_line_model.py`  
**BaseLineCore inherits:** `BaseModel`  
**BaseSellLineModel inherits:** `BaseLineCore`  
**BaseExecLineModel inherits:** `BaseLineCore`

### BaseLineCore fields (all line types)

| Field | Django Type | Details |
|-------|-----------|---------|
| `price_level` | `CharField(50)` | `blank=True, null=True` |
| `status` | `CharField(50)` | `blank=True, null=True` |
| `item` | `JSONField` | `default=dict, blank=True, null=True` |
| `quantity` | `JSONField` | `default=dict, blank=True, null=True` |
| `cost` | `JSONField` | `default=dict, blank=True, null=True` |
| `tax` | `JSONField` | `default=dict, blank=True, null=True` |
| `physical` | `JSONField` | `default=dict, blank=True, null=True` |

Plus ALL BaseModel inherited fields (id, uuid, ida, metadata, refs, prefs, comments, actions, health_rating, is_active, is_deleted, is_archived, etc.)

### BaseSellLineModel additional fields (proposals, orders, invoices)

| Field | Django Type | Details |
|-------|-----------|---------|
| `price` | `JSONField` | `default=dict, blank=True, null=True` |

**`item` default structure:**
```json
{
  "item_id": null,
  "ida_item": "",
  "uuid_item": "",
  "description": "",
  "description_text": "",
  "time_lead": null,
  "addresses": [],
  "unit_measure": "",
  "sequence": 0,
  "line_number": 0,
  "is_deleted": false,
  "is_active": true,
  "is_archived": false
}
```

**`quantity` default structure (order type):**
```json
{
  "placed": 0,
  "actioned": 0,
  "remaining": 0,
  "is_fixed": false,
  "precision": 2,
  "is_blanket": false,
  "increment": 0
}
```

**`price` (line) default structure:**
```json
{
  "unit": 0.0,
  "unit_base": 0.0,
  "discount_percent": 0.0,
  "discount_amount": 0.0,
  "extended": 0.0,
  "is_fixed": false,
  "precision": 2
}
```

**`cost` (line) default structure:**
```json
{
  "unit": 0.0,
  "unit_base": 0.0,
  "discount_percent": 0.0,
  "discount_amount": 0.0,
  "extended": 0.0,
  "shipping": 0.0,
  "handling": 0.0,
  "freight": 0.0,
  "commissions": 0.0,
  "tax_rate": 0.0,
  "tax": 0.0,
  "is_fixed": false,
  "precision": 2,
  "tax_code": "",
  "tax_code_id": 0,
  "tax_lookup_id": 0
}
```

**`tax` (line) default structure:**
```json
{
  "sales_rate": null,
  "sales": null,
  "cost_rate": null,
  "cost": null,
  "shipping": null,
  "tax_service_id": 0
}
```

**`physical` default structure:**
```json
{
  "weight": {"value": 0.0, "unit": ""},
  "dimensions": {"length": 0.0, "width": 0.0, "height": 0.0, "unit": ""},
  "volume": {"value": 0.0, "unit": ""},
  "package_count": 0,
  "is_hazmat": false
}
```

---

## 5. OrgBase (unified organization)

**File:** `apps/orgs/models/base.py`  
**Inherits:** `StandardLinksMixin`, `RelationshipStatsMixin`, `StatsMixin`, `BaseModel`  
**DB table:** default (orgs_orgbase)

### Own columns

| Field | Django Type | Details |
|-------|-----------|---------|
| `org_type` | `CharField(20)` | `choices=OrgType.choices, db_index=True, blank=True, null=True` |
| `display_name` | `CharField(255)` | `db_index=True` (aliased as `company` property) |
| `contact_id` | `IntegerField` | `blank=True, null=True` — optional primary contact |
| `attention` | `CharField(255)` | `blank=True, null=True` |
| `email` | `EmailField` | `blank=True, null=True` |
| `phone` | `CharField(50)` | `blank=True, null=True` |
| `price_level` | `CharField(30)` | `blank=True, null=True` |
| `status` | `CharField(30)` | `blank=True, choices=ORG_STATUS_CHOICES, db_index=True` |

### Aspect JSONB fields (org-specific)

| Field | Django Type | Default Factory |
|-------|-----------|----------------|
| `contacts` | `JSONField` | `default_contacts` → `[]` — list of `{id, name, role, phones, emails}` |
| `addresses` | `JSONField` | `default_addresses` → `[]` — list of `{id, type, address, geo}` |
| `domains` | `JSONField` | `default_domains` → `[]` — list of `{domain, verified, dt_verified}` |
| `phones` | `JSONField` | `default_phones` → `[]` — list of `{id, type, number, ext, primary}` |
| `emails` | `JSONField` | `default_emails` → `[]` — list of `{id, type, email, primary, bounce_count}` |
| `docs` | `JSONField` | `default_docs` → `[]` — list of `{id, kind, name, size, sha256}` |
| `connections` | `JSONField` | `default_connections` → `{}` — pointers like `{"email_svc": "vault:cred:123"}` |
| `relations` | `JSONField` | `default_relations` → `{"parents":[], "children":[], "linked_ids":[]}` |
| `financial` | `JSONField` | `default_financial` (see below) |
| `data` | `JSONField` | `default_data` → `{}` |
| `metrics` | `JSONField` | `default_metrics` → `{"counts":{}, "periods":{}}` |
| `gl_accounts` | `JSONField` | `default_gl_accounts` → `{}` |

### From StatsMixin

| Field | Django Type | Details |
|-------|-----------|---------|
| `stats` | `JSONField` | `default=default_stats` → `{"counts":{}, "values":{}, "series":{}, "last":{}}` |

### From RelationshipStatsMixin

| Field | Django Type | Details |
|-------|-----------|---------|
| `relationship_stats` | `JSONField` | `default=default_relationship_stats` → `{"counts":{}, "dt_last":{}}` |

### Plus ALL BaseModel fields
(id, uuid, ida, dt_created, dt_modified, version, is_active, is_deleted, is_archived, security_level, metadata, refs, prefs, comments, actions, health_rating)

### `financial` default structure (very large — type-keyed):
```json
{
  "common": {
    "currency": "USD",
    "account": {"dt_opened": null, "dt_last_activity": null, "hold": false, "cod_only": false, "inactive": false},
    "rating": {"internal": null, "comments": "", "credit_score": null},
    "settings": {"discount_pct": 0, "tax_exempt": false, "tax_exempt_id": "", "terms_id": null, "notes": ""}
  },
  "customer": {
    "credit": {"limit": 0, "high": 0, "available": 0},
    "balances": {"due": 0, "current": 0, "open_orders": 0, "total_exposure": 0},
    "aging": {"future": 0, "period_1": 0, "period_2": 0, "period_3": 0},
    "payment": {"days_avg_paid": 0, "days_pay": 0, "dt_last_payment": null, "last_payment_amount": 0},
    "sales": {"mtd": 0, "ytd": 0, "lifetime": 0, "dt_last_sale": null, "last_sale_amount": 0},
    "margin": {"mtd": 0, "ytd": 0, "pct": 0},
    "returns": {"mtd": 0, "ytd": 0, "count": 0},
    "deposits": {"unapplied": 0},
    "collection": {"cost_mtd": 0, "cost_ytd": 0, "cost_alltime": 0},
    "minimums": {"order": 0},
    "stats": {
      "proposals": {"issued": {"count":0,"value":0}, "canceled": {"count":0,"value":0}, "executed": {"count":0,"value":0}},
      "orders": {"issued": {"count":0,"value":0}, "canceled": {"count":0,"value":0}, "executed": {"count":0,"value":0}},
      "invoices": {"issued": {"count":0,"value":0}, "canceled": {"count":0,"value":0}, "executed": {"count":0,"value":0}},
      "payments": {"issued": {"count":0,"value":0}, "canceled": {"count":0,"value":0}, "executed": {"count":0,"value":0}}
    },
    "complaints": {"our_fault":0, "their_fault":0, "unresolved":0, "costs":{"us":0,"partner":0,"rep":0}},
    "small_stings": {
      "received": {"count":0,"value":0,"paid":0,"pending":0},
      "issued": {"count":0,"value":0,"collected":0,"pending":0},
      "by_category": {"shipping":{"count":0,"value":0},"billing":{"count":0,"value":0},"quality":{"count":0,"value":0},"service":{"count":0,"value":0},"other":{"count":0,"value":0}}
    }
  },
  "vendor": {
    "credit": {"limit": 0, "terms_days": 0},
    "balances": {"due": 0, "current": 0, "open_pos": 0},
    "aging": {"future": 0, "period_1": 0, "period_2": 0, "period_3": 0},
    "purchases": {"mtd": 0, "ytd": 0, "lifetime": 0, "dt_last_purchase": null, "last_purchase_amount": 0},
    "costs": {"mtd": 0, "ytd": 0},
    "payments_made": {"mtd": 0, "ytd": 0, "dt_last_payment": null},
    "minimums": {"order": 0, "purchase": 0},
    "stats": {"purchases": {"issued":{"count":0,"value":0},"canceled":{"count":0,"value":0},"executed":{"count":0,"value":0}}},
    "complaints": {"our_fault":0,"their_fault":0,"unresolved":0,"costs":{"us":0,"partner":0,"rep":0}},
    "small_stings": { ... }
  },
  "rep": {
    "commissions": {"mtd":0,"ytd":0,"lifetime":0,"pending":0,"paid":0,"rate_pct":0},
    "sales_credited": {"mtd":0,"ytd":0,"lifetime":0},
    "customers_count": 0,
    "stats": { ... }
  },
  "employee": {
    "payroll": {"salary":0,"rate_hourly":0,"rate_type":"salary"},
    "expenses": {"mtd":0,"ytd":0,"pending":0},
    "commissions": {"mtd":0,"ytd":0},
    "time": {"hours_mtd":0,"hours_ytd":0}
  },
  "manufacturer": {
    "purchases": {"mtd":0,"ytd":0,"lifetime":0},
    "rebates": {"earned_ytd":0,"received_ytd":0,"pending":0},
    "pricing_tier": null,
    "lead_time_days": 0,
    "freight_terms": "",
    "min_order": 0,
    "stats": { ... }
  },
  "fx": {
    "gain_loss_mtd": 0,
    "gain_loss_ytd": 0,
    "gain_loss_alltime": 0
  }
}
```

### GIN Indexes
- `contacts` (GIN)
- `relations` (GIN)
- `financial` (GIN)
- `domains` (GIN)

### Constraints
- `display_name` cannot be empty string

---

## 6. Proxy Models: Customer, Vendor, Rep, Employee, Manufacturer

**File:** `apps/orgs/models/proxies.py`  
**All inherit:** `OrgBase` (proxy=True, no new table)

Each uses a `_TypeFilteredManager` that auto-filters/auto-sets `org_type`:

| Proxy Model | `org_type` value |
|------------|-----------------|
| `Customer` | `"customer"` |
| `Vendor` | `"vendor"` |
| `Rep` | `"rep"` |
| `Employee` | `"employee"` |
| `Manufacturer` | `"manufacturer"` |

**All fields are identical to OrgBase.** The proxy just scopes queries and auto-sets `org_type` on create/save.

---

## 7. Contact

**File:** `apps/core/models/contact.py`  
**Inherits:** `StandardLinksMixin`, `BaseModel`, `AbstractBaseUser`, `PermissionsMixin`  
**DB table:** `contacts`

### Own columns

| Field | Django Type | Details |
|-------|-----------|---------|
| `email` | `EmailField` | `unique=True` — login username |
| `name_first` | `CharField(100)` | `blank=True` |
| `name_last` | `CharField(100)` | `blank=True` |
| `name_middle` | `CharField(100)` | `blank=True` |
| `name_prefix` | `CharField(20)` | `blank=True` (Mr., Ms., Dr.) |
| `name_suffix` | `CharField(20)` | `blank=True` (Jr., Sr., III) |
| `attention` | `CharField(201)` | `blank=True` — auto-filled from first+last |
| `employee_id` | `BigIntegerField` | `null=True, blank=True` |
| `customer_id` | `BigIntegerField` | `null=True, blank=True` |
| `vendor_id` | `BigIntegerField` | `null=True, blank=True` |
| `manufacturer_id` | `BigIntegerField` | `null=True, blank=True` |
| `rep_id` | `BigIntegerField` | `null=True, blank=True` |
| `other_id` | `BigIntegerField` | `null=True, blank=True` |
| `company` | `CharField(200)` | `blank=True` |
| `title` | `CharField(100)` | `blank=True` — job title |
| `department` | `CharField(100)` | `blank=True` |
| `comment` | `TextField` | `blank=True, default=""` |
| `role` | `CharField(50)` | `choices=CONTACT_ROLE_CHOICES, default='user'` |
| `is_active` | `BooleanField` | `default=True` |
| `is_staff` | `BooleanField` | `default=False` |
| `dt_joined` | `DateTimeField` | `default=timezone.now` |
| `password` | _(from AbstractBaseUser)_ | hashed password |
| `last_login` | _(from AbstractBaseUser)_ | `DateTimeField, null=True` |

### From PermissionsMixin (Django)
| Field | Django Type |
|-------|-----------|
| `is_superuser` | `BooleanField` |
| `groups` | `ManyToManyField` |
| `user_permissions` | `ManyToManyField` |

### Plus ALL BaseModel fields
(id, uuid, ida, dt_created, dt_modified, version, is_active, is_deleted, is_archived, security_level, metadata, refs, prefs, comments, actions, health_rating)

**USERNAME_FIELD:** `email`  
**REQUIRED_FIELDS:** `['name_first', 'name_last']`

---

## 8. Item (catalog product)

**File:** `apps/products/models/item.py`  
**Inherits:** `StatsMixin`, `BaseModel`  
**DB table:** default (products_item)

### Own columns

| Field | Django Type | Details |
|-------|-----------|---------|
| `name` | `CharField(160)` | `db_index=True` |
| `sku` | `CharField(80)` | `blank=True, null=True` — soft unique (case-insensitive at app layer) |
| `qr_code` | `CharField(255)` | `blank=True, null=True` |
| `kind` | `CharField(20)` | `choices=ITEM_KIND_CHOICES, default="physical", db_index=True` |
| `uom` | `CharField(20)` | `blank=True` — unit of measure (EA, HR, KG) |
| `base_uom` | `CharField(20)` | `blank=True` — canonical base unit for conversions |
| `description` | `TextField` | `blank=True` |
| `specification_id` | `BigIntegerField` | `null=True, blank=True` |
| `row_version` | `IntegerField` | `default=0, db_index=True` — additional optimistic concurrency |

### JSONB fields

| Field | Django Type | Default Factory |
|-------|-----------|----------------|
| `gls` | `JSONField` | `default=dict` — GL account mappings `{inventory, cogs, revenue, variance}` |
| `flags` | `JSONField` | `default=default_flags` (see below) |
| `price` | `JSONField` | `default=default_price` (see below) |
| `cost` | `JSONField` | `default=default_cost` (see below) |
| `tax_code` | `JSONField` | `default=default_tax` (see below) |
| `catalog` | `JSONField` | `default=default_catalog` (see below) |
| `quantity` | `JSONField` | `default=dict` — inventory quantities |

### From StatsMixin
| Field | Django Type | Details |
|-------|-----------|---------|
| `stats` | `JSONField` | `default=default_stats` → `{"counts":{}, "values":{}, "series":{}, "last":{}}` |

### Plus ALL BaseModel fields
(id, uuid, ida, dt_created, dt_modified, version, is_active, is_deleted, is_archived, security_level, metadata, refs, prefs, comments, actions, health_rating)

**`flags` default:**
```json
{
  "back_order_allowed": false,
  "discountable": false,
  "linked": false,
  "not_tracked": false,
  "pacing": false,
  "print_suppressed": false,
  "serialized": false,
  "tally_by_type": false
}
```

**`price` default:**
```json
{
  "base": null,
  "msrp": null,
  "tiers": [],
  "qty_breaks": [],
  "currency": "USD",
  "history": []
}
```

**`cost` default:**
```json
{
  "standard": null,
  "last": null,
  "avg": null,
  "landed": null,
  "currency": "USD",
  "components": {},
  "qty_breaks": [],
  "history": []
}
```

**`tax_code` default:**
```json
{
  "code": "",
  "jurisdiction": "",
  "category": "",
  "rate": null,
  "exemptions": [],
  "jurisdiction_params": []
}
```

**`catalog` default:**
```json
{
  "categories": [],
  "attributes": {},
  "web": {},
  "flags": {}
}
```

**`quantity` canonical keys:** `on_hand`, `allocated`, `available`, `on_so`, `on_po`, `on_p`, `on_reciept`, `on_in`, `on_wo`

### Indexes
- `(kind, is_active)` composite
- `(is_active, kind)` composite
- `Lower(sku)` functional index

---

## 9. Order

**File:** `apps/transactions/models/order.py`  
**Inherits:** `TransactionBaseModel`  
**DB table:** `orders`

**No additional columns beyond TransactionBaseModel.** All fields come from TransactionBaseModel + BaseModel.

Complete field set = **CoreModel** + **BaseModel mixins** + **TransactionBaseModel** fields:
- id, uuid, ida, dt_created, dt_modified, version, is_active, security_level
- is_deleted, is_archived
- metadata (JSON), refs (JSON), prefs (JSON), comments (JSON), actions (JSON), health_rating
- total, balance, status, priority, price_level
- customer_id, manufacturer_id, vendor_id
- parent_id, parent_model
- cost (JSON), sell (JSON), totals (JSON), finance (JSON), flow (JSON), source (JSON)

---

## 10. OrderLine

**File:** `apps/transactions/models/order_line.py`  
**Inherits:** `BaseSellLineModel`  
**DB table:** `order_lines`

| Field | Django Type | Details |
|-------|-----------|---------|
| `order` | `ForeignKey('transactions.Order')` | `related_name="lines", on_delete=CASCADE` |

Plus ALL BaseSellLineModel fields:
- BaseModel: id, uuid, ida, dt_created, dt_modified, version, is_active, security_level, is_deleted, is_archived, metadata, refs, prefs, comments, actions, health_rating
- BaseLineCore: price_level, status, item (JSON), quantity (JSON), cost (JSON), tax (JSON), physical (JSON)
- BaseSellLineModel: price (JSON)

---

## 11. Invoice

**File:** `apps/transactions/models/invoice.py`  
**Inherits:** `TransactionBaseModel`  
**DB table:** `invoices`

| Field | Django Type | Details |
|-------|-----------|---------|
| `refs` | `JSONField` | `default=dict, blank=True, null=True` — overrides BaseModel refs |
| `metadata` | `JSONField` | `default=dict, blank=True, null=True` — overrides BaseModel metadata |

Plus ALL TransactionBaseModel + BaseModel fields.

---

## 12. InvoiceLine

**File:** `apps/transactions/models/invoice_line.py`  
**Inherits:** `BaseSellLineModel`  
**DB table:** `invoice_lines`

| Field | Django Type | Details |
|-------|-----------|---------|
| `invoice` | `ForeignKey('transactions.Invoice')` | `related_name="lines", on_delete=CASCADE, db_column="invoice_id", null=True, blank=True` |

Plus ALL BaseSellLineModel fields (same as OrderLine).

---

## 13. Payment

**File:** `apps/transactions/models/payment.py`  
**Inherits:** `BaseModel`  
**DB table:** `payments`

### Own columns

| Field | Django Type | Details |
|-------|-----------|---------|
| `invoice_id` | `ForeignKey('transactions.Invoice')` | `on_delete=CASCADE, null=True, blank=True, related_name='payments'` |
| `contact_id` | `ForeignKey('core.Contact')` | `on_delete=CASCADE, related_name='payments'` |
| `amount` | `DecimalField(15,2)` | Payment amount |
| `dt_payment` | `DateTimeField` | Date payment was made |
| `paymentmethod_id` | `ForeignKey(PaymentMethod)` | `on_delete=SET_NULL, null=True, blank=True` |
| `paymentterm_id` | `ForeignKey(PaymentTerm)` | `on_delete=SET_NULL, null=True, blank=True` |
| `reference_number` | `CharField(100)` | `blank=True` — check number, tx ID, etc |
| `notes` | `TextField` | `blank=True` |
| `gateway` | `CharField(20)` | `choices=PAYMENT_GATEWAY_CHOICES, default='manual'` |
| `id_gateway_transaction` | `CharField(255)` | `blank=True` |
| `id_gateway_payment_intent` | `CharField(255)` | `blank=True` |
| `status` | `CharField(20)` | `choices=PAYMENT_STATUS_CHOICES, default='pending'` |
| `gateway_response` | `JSONField` | `null=True, blank=True` — raw gateway response |
| `dt_processed` | `DateTimeField` | `null=True, blank=True` |
| `reconciled` | `BooleanField` | `default=False` |
| `dt_reconciliation` | `DateTimeField` | `null=True, blank=True` |
| `fee_amount` | `DecimalField(10,2)` | `default=0` |

### JSONB fields (override BaseModel defaults)

| Field | Django Type | Default |
|-------|-----------|---------|
| `refs` | `JSONField` | `{"invoice_ids":[], "order_ids":[], "source":{"type":"","id":0}}` |
| `metadata` | `JSONField` | `{"reconciliation":{"batch_id":null,"statement_date":null,"notes":""},"gateway_metadata":{},"processing_fees":[],"audit_trail":[]}` |

Plus remaining BaseModel fields.

---

## 14. PaymentMethod

**File:** `apps/transactions/models/payment.py`  
**Inherits:** `BaseModel`  
**DB table:** `payment_methods`

| Field | Django Type | Details |
|-------|-----------|---------|
| `name` | `CharField(100)` | `unique=True` |
| `description` | `TextField` | `blank=True` |
| `is_active` | `BooleanField` | `default=True` |

Plus ALL BaseModel fields.

---

## 15. PaymentTerm

**File:** `apps/transactions/models/payment.py`  
**Inherits:** `BaseModel`  
**DB table:** `payment_terms`

| Field | Django Type | Details |
|-------|-----------|---------|
| `name` | `CharField(100)` | `unique=True` |
| `description` | `TextField` | `blank=True` |
| `days` | `IntegerField` | `default=0` |
| `is_active` | `BooleanField` | `default=True` |

Plus ALL BaseModel fields.

---

## 16. PaymentApplication

**File:** `apps/transactions/models/payment_application.py`  
**Inherits:** `BaseModel`  
**DB table:** `payment_applications`

| Field | Django Type | Details |
|-------|-----------|---------|
| `payment_id` | `ForeignKey('transactions.Payment')` | `on_delete=CASCADE, related_name='applications'` |
| `invoice_id` | `ForeignKey('transactions.Invoice')` | `on_delete=CASCADE, related_name='payment_applications'` |
| `amount` | `DecimalField(15,2)` | Amount applied |
| `applied_at` | `DateTimeField` | `auto_now_add=True` |
| `notes` | `TextField` | `blank=True` |

**Constraint:** `unique_together = ['payment_id', 'invoice_id']`

Plus ALL BaseModel fields.

---

## 17. Choices / Enums Reference

### OrgType (TextChoices) — `apps/orgs/models/constants.py`
| Value | Label |
|-------|-------|
| `"customer"` | Customer |
| `"vendor"` | Vendor |
| `"rep"` | Rep |
| `"employee"` | Employee |
| `"manufacturer"` | Manufacturer |
| `"other"` | Other |

### ORG_STATUS_CHOICES — `apps/orgs/choices.py`
`""` (Unspecified), `"active"`, `"prospect"`, `"suspended"`, `"inactive"`, `"retired"`

### TRANSACTION_STATUS_CHOICES — `apps/transactions/choices.py`
`""`, `"planned"`, `"released"`, `"in_progress"`, `"hold"`, `"complete"`, `"canceled"`

### TRANSACTION_PARENT_MODEL_CHOICES
`"proposal"`, `"order"`, `"invoice"`, `"purchase"`, `"workorder"`, `"requisition"`

### PAYMENT_GATEWAY_CHOICES
`""`, `"manual"`, `"stripe"`, `"paypal"`

### PAYMENT_STATUS_CHOICES
`""`, `"pending"`, `"processing"`, `"completed"`, `"failed"`, `"cancelled"`, `"refunded"`, `"partially_refunded"`

### CONTACT_ROLE_CHOICES — `apps/core/choices.py`
`""`, `"user"`, `"employee"`, `"admin"`

### ITEM_KIND_CHOICES — `apps/products/choices.py`
`"physical"`, `"service"`, `"bundle"`

---

## Summary: Complete Field Inventory per Model

### Inherited field count from BaseModel (present on EVERY model):
| Inherited Field | Source Mixin |
|----------------|-------------|
| `id` | CoreModel |
| `uuid` | CoreModel |
| `ida` | CoreModel |
| `dt_created` | CoreModel |
| `dt_modified` | CoreModel |
| `version` | CoreModel |
| `is_active` | CoreModel |
| `security_level` | CoreModel |
| `is_deleted` | LifecycleMixin |
| `is_archived` | LifecycleMixin |
| `metadata` (JSONB) | MetadataMixin |
| `refs` (JSONB) | RefsMixin |
| `prefs` (JSONB) | PrefsMixin |
| `comments` (JSONB) | CommentsMixin |
| `actions` (JSONB) | ActionsMixin |
| `health_rating` | HealthMixin |

**Total BaseModel inherited fields: 16** (8 scalar + 5 JSONB + 3 boolean)

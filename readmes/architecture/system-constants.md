# System Constants Reference

**Purpose:** Every constant listed here is a value that breaks silently if
guessed wrong. This is the contract between backend and frontend. Alice
validates against these. Developers read this before adding new values.

---

## How to Use This Document

1. **Before adding a new status, type, or category** — check here first.
   The value may already exist under a different name.
2. **Before hardcoding a string** — use the constant, not the string.
3. **Alice validates** — she flags values not in these lists.

---

## Setting Purposes

**File:** `apps/core/choices.py` — `SETTING_PURPOSE_CHOICES`
**Used by:** Setting.purpose field. Controls what the Setting configures.

| Purpose | What it controls |
|---------|-----------------|
| `workbench_fields` | DataBrowser layouts (config.db.list/detail/panel/card) |
| `detail_layout` | JSON detail form layout |
| `field_access` | Field-level RBAC + field_behaviors + field_groups |
| `schema_map` | Maps model names to Pydantic schemas |
| `print_layout` | Print template configuration |
| `db_defaults` | Model default values |
| `ui_webclerk` | Global UI configuration |
| `payment_gateway` | Payment processor config |
| `search_presets` | Saved search configurations |
| `alice_coaching` | Alice training data |
| `qa_questions` | Quiz/QA question bank |
| `device_status` | Device health monitoring |

Wrong purpose = Setting is invisible to the feature that needs it.

---

## Organization Types

**File:** `apps/orgs/models/constants.py` — `OrgType`
**React:** `apps/orgs/orgConfig.ts`

| Value | Color | Financial metrics |
|-------|-------|------------------|
| `customer` | blue #0d6efd | sales, AR, credit limit |
| `vendor` | purple #6f42c1 | purchases, AP, terms |
| `manufacturer` | green #198754 | costs, lead times |
| `employee` | orange #fd7e14 | payroll, commission |
| `rep` | red #dc3545 | commission, territory |
| `other` | — | minimal |

Wrong org_type = wrong financial dashboard, wrong metrics, wrong field layout.

---

## Organization Statuses

**File:** `apps/orgs/choices.py`

| Value | Meaning |
|-------|---------|
| `active` | Normal operating state |
| `default_company` | The primary organization |
| `prospect` | Not yet a customer |
| `suspended` | Temporarily frozen |
| `inactive` | No longer active |
| `retired` | Permanently closed |

---

## Transaction Statuses

**File:** `apps/transactions/choices.py` — `TRANSACTION_STATUS_CHOICES`
**React:** `useOrderStatus.ts`

| Value | Meaning | Color |
|-------|---------|-------|
| `planned` | Created, not released | gray |
| `released` | Approved for processing | blue |
| `in_progress` | Being worked | yellow |
| `hold` | Paused | orange |
| `complete` | Done | green |
| `canceled` | Voided | red |

**Legacy values** (backward compat): `draft`, `confirmed`, `shipped`, `delivered`, `cancelled` (note extra 'l').

---

## Project Statuses

**File:** `apps/transactions/choices.py` — `PROJECT_STATUS_CHOICES`

| Value | Meaning |
|-------|---------|
| `draft` | Not started |
| `active` | In progress |
| `onhold` | Paused |
| `blocked` | Waiting on dependency |
| `done` | Complete |
| `canceled` | Abandoned |

Note: Projects use `done`, transactions use `complete`. Don't mix them.

---

## Project Attention Levels

| Value | Meaning |
|-------|---------|
| `low` | Background |
| `normal` | Standard |
| `high` | Needs attention |
| `critical` | Immediate action required |

---

## Action (Kanban) Columns

**File:** `apps/core/choices.py`

| Value | Display |
|-------|---------|
| `Backlog` | Not started |
| `Planning` | Being planned |
| `InProcess` | Active work |
| `Review` | Needs review |
| `Complete` | Done |

---

## Action Difficulty (Fibonacci)

| Value | Label |
|-------|-------|
| `1` | Easy |
| `4` | Average |
| `8` | Hard |
| `13` | Complex |
| `21` | Expert |

---

## Payment

**File:** `apps/transactions/choices.py`

### Gateway
| Value | Meaning |
|-------|---------|
| `manual` | Manual entry |
| `spreedly` | Spreedly payment processor |

### Status
| Value | Meaning |
|-------|---------|
| `pending` | Awaiting processing |
| `processing` | In flight |
| `completed` | Settled |
| `failed` | Rejected |
| `cancelled` | Voided |
| `refunded` | Fully refunded |
| `partially_refunded` | Partial refund |

---

## Item Types

**File:** `apps/products/choices.py`

| Value | Meaning |
|-------|---------|
| `physical` | Tangible goods with inventory |
| `service` | Labor / time-based |
| `bundle` | Kit of other items |

---

## Price Levels

**React:** `config/selectLists.ts`

| Value | Meaning |
|-------|---------|
| `retail` | Standard consumer price |
| `wholesale` | Bulk/reseller price |
| `distributor` | Distribution channel price |
| `employee` | Internal/staff price |
| `sample` | Demo/sample — may be zero |

Affects tax calculations and margin reporting.

---

## GL Account Types

**File:** `apps/accounts/choices.py`

### Type
| Value |
|-------|
| `asset` |
| `liability` |
| `equity` |
| `revenue` |
| `expense` |
| `contra` |

### Category
`cash`, `receivables`, `payables`, `inventory`, `sales`, `cogs`, `expense`, `other`

### Usage
`posting`, `reporting`, `tax`, `consolidation`, `other`

---

## Ledger

### Source
`invoice`, `payment`, `journal`, `adjustment`, `import`, `other`

### Model (discriminator)
`invoice`, `credit_memo`, `debit_memo`, `purchase`, `payment`, `other`

---

## Report

**File:** `apps/core/choices.py`

### output_type
`print`, `email`, `api`, `json`, `export`, `label`, `merge`, `screen`

### category
`report`, `statement`, `list`, `summary`, `letter`, `label`, `export`, `utility`

### purpose (REPORT_PURPOSE_CHOICES)
`form-detail`, `form-list`, `print`, `export`, `label`, `letter`, `query`, `sort`, `dashboard`, `script`, `onboarding`

---

## Communication Types

### Email Type
`work`, `personal`, `support`, `billing`, `other`

### Domain Type
`website`, `linkedin`, `facebook`, `twitter`, `github`, `other`

### Address Type
`billing`, `shipping`, `headquarters`, `branch`, `other`

---

## Widget Types (React)

**File:** `React2025/src/constants/widgetTypes.ts`

17 types that control how fields render in forms and lists:

| Type | Default Width | Sizing |
|------|--------------|--------|
| `text` | 200 | grow |
| `number` | 100 | fixed |
| `currency` | 120 | fixed |
| `email` | 250 | grow |
| `phone` | 150 | fixed |
| `zip` | 100 | fixed |
| `url` | 250 | grow |
| `address` | 300 | grow |
| `geo` | 120 | fixed |
| `lookup` | 200 | grow |
| `select` | 150 | fixed |
| `boolean` | 80 | fixed |
| `date` | 130 | fixed |
| `timestamp` | 170 | fixed |
| `json` | 300 | grow |
| `json-tree` | 300 | grow |
| `textarea` | 300 | grow |
| `readonly` | 200 | grow |
| `masked` | 150 | fixed |

Wrong widget type = field silently falls back to `text`.

---

## Filter Operators (React)

**File:** `React2025/src/constants/filterOperators.ts`

| Field Type | Operators |
|-----------|-----------|
| Text | `contains`, `startswith`, `endswith`, `eq`, `neq`, `not_contains`, `empty`, `notempty` |
| Number | `eq`, `neq`, `gt`, `lt`, `gte`, `lte`, `empty`, `notempty` |
| Date | `eq`, `lt`, `gt`, `lte`, `gte`, `range`, `empty` |
| Boolean | `eq`, `neq` |
| Lookup | `eq`, `neq`, `empty`, `notempty` |

Maps to Django lookups: `icontains`, `startswith`, `exact`, `isnull`, `range`, etc.

---

## Setting Scope Hierarchy

| Value | Meaning |
|-------|---------|
| `system` | Applies to all users |
| `org` | Per-organization override |
| `role` | Per-role override |
| `user` | Per-user override |

Lookup order: user > role > org > system (most specific wins).

---

## Inventory

### Reservation State
`pending`, `committed`, `canceled`, `expired`

### Movement Type
`receipt`, `issue`, `adjust`

### Pending Inventory State
`pending`, `applied`, `canceled`

### Check Status
`planned`, `in_progress`, `completed`, `canceled`

---

## Delivery

### Visit Status
`planned`, `en_route`, `arrived`, `closed`, `canceled`

### Line Status
`planned`, `loaded`, `delivered`, `skipped`, `partial`

---

## Erosion Categories

Tracks where margin leaks:

`margin`, `discount`, `fx_loss`, `late_payment`, `return_credit`, `rework`,
`shipping`, `bad_debt`, `price_override`, `other`

Source models: `proposal`, `order`, `invoice`, `purchase`, `payment`,
`credit_memo`, `action`, `question_answer`

---

## Rules

1. **Never invent a new value** without adding it to the choices file AND this document.
2. **Never hardcode a string** — import the constant.
3. **Case matters** — `canceled` not `Canceled`, `customer` not `Customer`.
4. **Alice validates** — she flags values not in these lists.
5. **Frontend and backend must agree** — if you add a backend choice, add it to the React selectLists or constants file too.

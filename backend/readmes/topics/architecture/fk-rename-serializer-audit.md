# FK Rename Serializer Audit Report

**Date:** 2026-02-15  
**Scope:** All Django serializers in `apps/` after the 48-field FK rename (drop `_id` suffix)

## Key Concepts

After the rename, a FK field named `customer` has:
- **Field name:** `customer` (the FK descriptor — returns the related object)
- **Attname:** `customer_id` (the raw integer column accessor — returns the PK integer)

In DRF serializer `fields` lists:
- `'customer'` → uses the FK field; serializes as the related object's PK value
- `'customer_id'` → uses the attname; serializes as the raw integer

Both are technically valid, but using the FK field name (`'customer'`) is the canonical DRF pattern and enables nested serializers, validators, and `PrimaryKeyRelatedField` behavior.

## Severity Legend

- ❌ **BUG** — Will cause runtime errors or incorrect behavior
- ⚠️ **ATTNAME** — Uses `_id` attname instead of FK field name; functional but non-canonical
- ℹ️ **INFO** — Attname access in Python code (`.customer_id`); valid and often preferred for performance

---

## 1. `apps/transactions/serializers/payment_serializers.py`

### ❌ BUG — `create()` and `update()` assign FK objects to attname keys

After popping the integer ID and resolving the object, the code assigns the object instance back using the `_id` suffixed key name. When passed to `super().create(validated_data)` → `Model.objects.create(**validated_data)`, Django expects the attname key to receive an integer PK, not an object instance.

| Line | Code | Issue | Fix |
|------|------|-------|-----|
| L51 | `validated_data["invoice_id"] = invoice` | Assigns Invoice object to `invoice_id` key | Change to `validated_data["invoice"] = invoice` |
| L55 | `validated_data["invoice_id"] = None` | OK (None is acceptable) | Change to `validated_data["invoice"] = None` for consistency |
| L62 | `validated_data["contact_id"] = contact` | Assigns Contact object to `contact_id` key | Change to `validated_data["contact"] = contact` |
| L68 | `validated_data["payment_method_id"] = payment_method` | Assigns PaymentMethod object to `payment_method_id` key | Change to `validated_data["payment_method"] = payment_method` |
| L74 | `validated_data["payment_term_id"] = payment_term` | Assigns PaymentTerm object to `payment_term_id` key | Change to `validated_data["payment_term"] = payment_term` |
| L84 | `validated_data["invoice_id"] = invoice` | Same bug in `update()` | Change to `validated_data["invoice"] = invoice` |
| L91 | `validated_data["contact_id"] = contact` | Same bug in `update()` | Change to `validated_data["contact"] = contact` |
| L99 | `validated_data["payment_method_id"] = payment_method` | Same bug in `update()` | Change to `validated_data["payment_method"] = payment_method` |
| L106 | `validated_data["payment_term_id"] = payment_term` | Same bug in `update()` | Change to `validated_data["payment_term"] = payment_term` |

### ⚠️ ATTNAME — Explicit field declarations use `_id` suffix

| Line | Code | Issue | Recommended |
|------|------|-------|-------------|
| L7 | `invoice_id = serializers.IntegerField(...)` | Declares `invoice_id` as IntegerField bypassing FK validation | Use `invoice = serializers.PrimaryKeyRelatedField(queryset=Invoice.objects.all(), ...)` |
| L8 | `contact_id = serializers.IntegerField(...)` | Same | Use `contact = serializers.PrimaryKeyRelatedField(queryset=Contact.objects.all(), ...)` |
| L9 | `payment_method_id = serializers.IntegerField(...)` | Same | Use `payment_method = serializers.PrimaryKeyRelatedField(...)` |
| L10 | `payment_term_id = serializers.IntegerField(...)` | Same | Use `payment_term = serializers.PrimaryKeyRelatedField(...)` |

### ⚠️ ATTNAME — `fields` list uses `_id` suffix

| Line | Fields | Issue |
|------|--------|-------|
| L16-20 | `"invoice_id"`, `"contact_id"`, `"payment_method_id"`, `"payment_term_id"` | Attname pattern; functional but non-canonical |

---

## 2. `apps/transactions/serializers/transaction_serializers.py`

### ⚠️ ATTNAME — `fields` lists use `_id` suffix for FK fields

**ProposalSerializer (L56):**

| Line | Field | Model FK | Attname used |
|------|-------|----------|-------------|
| L56 | `'customer_id'` | `customer` (FK to OrgBase) | `customer_id` |
| L56 | `'vendor_id'` | `vendor` (FK to OrgBase) | `vendor_id` |

**OrderSerializer (L178):**

| Line | Field | Model FK | Attname used |
|------|-------|----------|-------------|
| L178 | `'customer_id'` | `customer` | `customer_id` |
| L178 | `'manufacturer_id'` | `manufacturer` | `manufacturer_id` |
| L178 | `'vendor_id'` | `vendor` | `vendor_id` |

**PurchaseSerializer (L272):**

| Line | Field | Model FK | Attname used |
|------|-------|----------|-------------|
| L272 | `'customer_id'` | `customer` | `customer_id` |
| L272 | `'manufacturer_id'` | `manufacturer` | `manufacturer_id` |
| L272 | `'vendor_id'` | `vendor` | `vendor_id` |

**InvoiceSerializer (L321):**

| Line | Field | Model FK | Attname used |
|------|-------|----------|-------------|
| L321 | `'customer_id'` | `customer` | `customer_id` |
| L321 | `'vendor_id'` | `vendor` | `vendor_id` |

**PaymentSerializer (L333):**

| Line | Field | Model FK | Attname used |
|------|-------|----------|-------------|
| L333 | `'payment_method_id'` | `payment_method` | `payment_method_id` |
| L333 | `'payment_term_id'` | `payment_term` (via `terms_fk`) | `payment_term_id` — **Note:** Model FK is `payment_term` with `db_column='paymentterm_id'`, attname is `payment_term_id` |
| L333 | `'contact_id'` | `contact` | `contact_id` |
| L333 | `'invoice_id'` | `invoice` | `invoice_id` |

### ℹ️ INFO — SerializerMethodField attname access (valid)

| Line | Code | Notes |
|------|------|-------|
| L62 | `obj.customer_id` in `get_customer_name` | Accesses attname for integer PK lookup — valid & efficient |
| L71 | `obj.vendor_id` in `get_vendor_name` | Same |
| L191 | `obj.customer_id` in OrderSerializer.`get_customer_name` | Same |
| L201 | `obj.vendor_id` in OrderSerializer.`get_vendor_name` | Same |
| L292 | `obj.customer_id` in PurchaseSerializer.`get_customer_name` | Same but queries Contact instead of OrgBase — possible logic bug (customer FK points to OrgBase) |
| L302 | `obj.vendor_id` in PurchaseSerializer.`get_vendor_name` | Same — queries Contact for vendor FK which points to OrgBase |

### ⚠️ ATTNAME — `validate_*` methods match attname field names

| Line | Method | Notes |
|------|--------|-------|
| L118 | `validate_customer_id` | Matches field name `customer_id` in fields list — if renamed to `customer`, method must become `validate_customer` |
| L126 | `validate_vendor_id` | Same |
| L240 | `validate_customer_id` (OrderSerializer) | Same |
| L249 | `validate_vendor_id` (OrderSerializer) | Same |

---

## 3. `apps/transactions/serializers/line_serializers.py`

### ⚠️ ATTNAME — `ProjectSerializer` field mismatch

| Line | Field | Model field | Issue |
|------|-------|-------------|-------|
| L170 | `'contact_id'` in fields | `id_contact` (BigIntegerField) | **Not a renamed FK** — the model uses `id_contact`, not `contact_id`. This will cause `ImproperlyConfigured` error unless there's a `contact_id` property on the model. Likely pre-existing issue, not from FK rename. |

### ℹ️ NO ISSUES — Line serializers FK usage

The line serializers correctly use `source='proposal'`, `source='order'`, `source='invoice'`, `source='purchase'`, `source='workorder'` in their `PrimaryKeyRelatedField` declarations, matching the post-rename FK field names.

---

## 4. `apps/transactions/serializers/invoice_serializers.py`

### ⚠️ ATTNAME — `InvoiceSerializer.fields` uses `_id` suffix

| Line | Field | Model FK | Attname used |
|------|-------|----------|-------------|
| L8 | `'customer_id'` | `customer` | `customer_id` |
| L8 | `'vendor_id'` | `vendor` | `vendor_id` |

---

## 5. `apps/products/serializers.py`

### ⚠️ ATTNAME — Multiple serializers use `_id` attname for FK fields

**ServiceSerializer (L56):**

| Line | Field | Model FK | Notes |
|------|-------|----------|-------|
| L59 | `'item_id'` | `item` (FK from ItemLinkedBase) | Attname; should be `'item'` |

**ItemXrefSerializer (L67):**

| Line | Field | Model FK | Notes |
|------|-------|----------|-------|
| L72 | `'item_id'` | `item` (FK from ItemLinkedBase) | Attname; should be `'item'`. Note: `'source_id'` is NOT a FK — it's a plain field |

**SerialSerializer (L79):**

| Line | Field | Model FK | Notes |
|------|-------|----------|-------|
| L85 | `'item_id'` | `item` (FK from ItemLinkedBase) | Attname |
| L86 | `'inventory_layer_id'` | `inventory_layer` (FK, db_column='inventorylayer_id') | Attname |

**BillOfMaterialSerializer (L96, the one in serializers.py, NOT bom_serializers.py):**

| Line | Field | Model FK | Notes |
|------|-------|----------|-------|
| L106 | `'parent_id'` | `parent_item` (FK, db_column='parent_id') | Attname is `parent_item_id`, NOT `parent_id`. `parent_id` matches the **db_column** name, but DRF resolves via Python attname. **This will fail** unless there's a `parent_id` property. ❌ Likely BUG |
| L106 | `'child_id'` | `child_item` (FK, db_column='child_id') | Same — attname is `child_item_id`, not `child_id`. ❌ Likely BUG |

**CatalogSerializer (L115):**

| Line | Field | Model FK | Notes |
|------|-------|----------|-------|
| L124 | `'orgbase_id'` | `orgbase` | Attname |
| L124 | `'customer_orgbase_id'` | `customer_orgbase` | Attname |
| L124 | `'manufacturer_orgbase_id'` | `manufacturer_orgbase` | Attname |
| L124 | `'rep_orgbase_id'` | `rep_orgbase` | Attname |
| L124 | `'employee_orgbase_id'` | `employee_orgbase` | Attname |
| L125 | `'connection_id'` | `connection` | Attname |

**OrgItemSerializer (L131):**

| Line | Field | Model FK | Notes |
|------|-------|----------|-------|
| L139 | `'item_id'` | `item` (FK from ItemLinkedBase) | Attname |
| L139 | `'orgbase_id'` | `orgbase` | Attname |
| L139 | `'catalog_id'` | `catalog` | Attname |

**ItemUsageSerializer (L158):**

| Line | Field | Model FK | Notes |
|------|-------|----------|-------|
| L165 | `'item_id'` | `item` (FK from ItemLinkedBase) | Attname |

**InventoryReservationSerializer (L175, the one in serializers.py):**

| Line | Field | Model FK | Notes |
|------|-------|----------|-------|
| L180 | `'item_id'` | `item` | Attname |
| L180 | `'warehouse_id'` | `warehouse` | Attname |
| L181 | `'inventory_layer_id'` | `inventory_layer` (db_column='inventorylayer_id') | Attname |

---

## 6. `apps/products/serializers/bom_serializers.py`

### ✅ CORRECT — FK field names and `source=` arguments

All `source=` arguments use the correct post-rename FK field names:
- `source='child_item'` ✅
- `source='parent_item'` ✅

### ℹ️ INFO — Attname access in SerializerMethodField (valid)

| Line | Code | Notes |
|------|------|-------|
| L77 | `obj.child_item_id` | Attname access in `get_component_child_count` — valid, efficient for integer comparison |
| L78 | `parent_item_id=obj.child_item_id` | ORM filter using attname — valid, canonical Django pattern |
| L84-86 | `obj.child_item_id`, `parent_item_id=obj.child_item_id` | Same pattern in `get_refs` |

---

## 7. `apps/products/serializers/reservation_serializers.py`

### ✅ CORRECT — Uses FK field names

`InventoryReservationSerializer.fields` uses: `'item'`, `'warehouse'`, `'stack'` — correct FK field names.

### ⚠️ STRUCTURAL — `read_only_fields` defined outside Meta

| Line | Issue |
|------|-------|
| L16 | `read_only_fields = [...]` is at class level, not inside `class Meta:`. DRF ignores class-level `read_only_fields`; it must be inside `Meta`. |

---

## 8. `apps/orgs/serializers/orgbase_serializer.py`

### ⚠️ ATTNAME — `contact_id` in fields list

| Line | Field | Model FK | Notes |
|------|-------|----------|-------|
| L31 | `'contact_id'` | `contact` (FK to Contact) | Attname; could be `'contact'` |

### ✅ CORRECT — `source="terms_fk_id"`

| Line | Code | Notes |
|------|------|-------|
| L12 | `terms_id = serializers.IntegerField(source="terms_fk_id", ...)` | Correctly accesses the attname of `terms_fk` FK. Intentional aliasing for API backwards compatibility. |

---

## 9. `apps/docs/serializers/question_answer.py`

### ⚠️ ATTNAME — `setting_id` in fields list

| Line | Field | Model FK | Notes |
|------|-------|----------|-------|
| L18 | `'setting_id'` | `setting` (FK to Setting) | Attname; could be `'setting'` |

**Note:** `question_id` and `answer_id` (also in fields) are plain `IntegerField`s on the model, NOT FKs. They are unaffected by the rename.

### ✅ CORRECT — `source='setting.name'`

| Line | Code | Notes |
|------|------|-------|
| L11 | `source='setting.name'` | Correctly traverses the FK field `setting` to access `.name` |

---

## 10. `apps/core/views/action_views.py`

### ✅ CORRECT — `parent_action` in fields

| Line | Field | Model FK | Notes |
|------|-------|----------|-------|
| L28 | `'parent_action'` | `parent_action` (FK to self) | Correct post-rename FK field name |

### ℹ️ NOT FKs — `contact_id`, `project_id`, `project_name`, `project_ida`, `project_metadata`

These are all plain model fields (`BigIntegerField`, `CharField`, `JSONField`), NOT renamed FKs. No action needed.

---

## 11. `apps/sync/serializers/connection.py`

### ✅ NO ISSUES

No FK fields referenced in the fields list. All fields are direct model attributes.

---

## 12. `apps/transactions/serializers/transfer_serializers.py`

### ✅ NO ISSUES

All serializers are plain `serializers.Serializer` (not ModelSerializer). Field names like `payment_id`, `invoice_id`, `source_id`, `order_id` are API contract fields, not model field references.

---

## Summary

### Bugs (❌) — Require immediate fix

| # | File | Issue |
|---|------|-------|
| 1 | `transactions/serializers/payment_serializers.py` L51,62,68,74,84,91,99,106 | `create()`/`update()` assign FK object instances to `_id`-suffixed keys in `validated_data`. Will pass object where integer is expected. |
| 2 | `products/serializers.py` L106 | `'parent_id'` in BillOfMaterialSerializer fields — attname is `parent_item_id`, not `parent_id`. DRF field resolution will fail. |
| 3 | `products/serializers.py` L106 | `'child_id'` in BillOfMaterialSerializer fields — attname is `child_item_id`, not `child_id`. Same issue. |

### Attname pattern (⚠️) — Functional but non-canonical

| # | File | Count | Fields using attname |
|---|------|-------|---------------------|
| 1 | `transactions/serializers/transaction_serializers.py` | 12 | `customer_id`, `vendor_id`, `manufacturer_id`, `contact_id`, `invoice_id`, `payment_method_id`, `payment_term_id` across 5 serializers |
| 2 | `transactions/serializers/payment_serializers.py` | 4 | `invoice_id`, `contact_id`, `payment_method_id`, `payment_term_id` (as explicit IntegerFields) |
| 3 | `transactions/serializers/invoice_serializers.py` | 2 | `customer_id`, `vendor_id` |
| 4 | `products/serializers.py` | 18 | `item_id` (×5), `orgbase_id` (×2), `catalog_id` (×2), `warehouse_id` (×2), `inventory_layer_id` (×2), `connection_id`, `customer_orgbase_id`, `manufacturer_orgbase_id`, `rep_orgbase_id`, `employee_orgbase_id` |
| 5 | `orgs/serializers/orgbase_serializer.py` | 1 | `contact_id` |
| 6 | `docs/serializers/question_answer.py` | 1 | `setting_id` |
| 7 | `transactions/serializers/line_serializers.py` | 1 | `contact_id` in ProjectSerializer (but model field is `id_contact`, separate issue) |

**Total: ~39 attname-pattern field references across serializers**

### Correct (✅) — No action needed

| File | Notes |
|------|-------|
| `products/serializers/bom_serializers.py` | All `source=` args use correct FK names |
| `products/serializers/reservation_serializers.py` | Uses FK field names in fields list |
| `transactions/serializers/line_serializers.py` | Line serializers use correct `source=` for parent FK |
| `transactions/serializers/transaction_serializers.py` PaymentApplicationSerializer | Uses `'payment'`, `'invoice'` FK field names |
| `core/views/action_views.py` | Uses `'parent_action'` correctly |
| `sync/serializers/connection.py` | No FK field references |
| `docs/serializers/question_answer.py` | `source='setting.name'` traverses FK correctly |
| `orgs/serializers/orgbase_serializer.py` | `source="terms_fk_id"` is intentional aliasing |

### Recommendations

1. **Fix bugs first** — The `payment_serializers.py` create/update methods and the BOM serializer `parent_id`/`child_id` field names are the highest priority.

2. **Decide on convention** — The attname pattern (`customer_id` in fields list) is widespread and functional. If the API contract expects integer IDs in JSON keys like `"customer_id": 42`, keeping attnames is pragmatic. If you want full FK semantics (nested writes, `PrimaryKeyRelatedField` validation), switch to FK field names.

3. **If migrating to FK field names:**
   - Rename fields in `fields` lists
   - Rename any corresponding `validate_<field>` methods
   - Update any explicit `serializers.IntegerField(...)` declarations to `serializers.PrimaryKeyRelatedField(...)`
   - Update frontend code that sends/receives these field names in JSON payloads
   - This is an **API-breaking change** for consumers expecting `customer_id` in responses

4. **For `products/serializers.py` specifically** — This file has a separate, simpler BillOfMaterialSerializer that conflicts with the one in `bom_serializers.py`. Consider removing the duplicate.

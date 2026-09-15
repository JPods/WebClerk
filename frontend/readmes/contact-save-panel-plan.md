# Contact Save — Panel Layout Plan

> Target: `ContactDetail3.tsx` (r25) → `POST /wcapi/save/` (wc3)

---

## 1. Problem Statement

A Contact record is a hub that links to:
- **4 communication models** — Email, Phone, Address, Domain
- **5 org associations** — Customer, Vendor, Rep, Employee, Manufacturer (+ Other)

Today, the save payload from `ContactDetail` only submits scalar contact fields.
Communications and orgs are managed through separate pickers, dialogs, and tab
panels — each making its own `saveRecord()` calls. This scatters the workflow
and makes it hard for users to:

1. See all linked records at a glance while editing
2. Check for existing communications or orgs before creating duplicates
3. Understand which linked record is the "primary" one

---

## 2. Design Goals

| # | Goal |
|---|------|
| G1 | Each related model gets its own **panel** in the Basic Information area |
| G2 | The **denormalized scalar field** on the Contact record is shown at the top of each panel |
| G3 | The linked record whose ID matches the Contact's `*_id` field gets a **★ star badge** |
| G4 | Users can **search existing records** from within each panel before creating new ones |
| G5 | The final save payload is a **single composite body** submitted to `wcapi/save` |
| G6 | Keep full backward compatibility — `ContactDetail` and `ContactDetail2` are untouched |

---

## 3. Data Model Recap

### 3a. Communications — Scalar ↔ FK Pairs

| Scalar Field (on Contact) | FK Field (on Contact) | Target Model | Target Table | Key Display Field |
|---------------------------|-----------------------|--------------|-------------|-------------------|
| `email`                   | `email_id`            | Email        | `emails`    | `email`           |
| `phone`                   | `phone_id`            | Phone        | `phones`    | `number`          |
| `address_full`            | `address_id`          | Address      | `locations` | `full`            |
| `domain`                  | `domain_id`           | Domain       | `domains`   | `path`            |

- Scalar fields are **denormalized copies** for quick display/search.
- `*_id` fields are **raw BigIntegerFields** (not Django FKs) — soft pointers.
- Each comm model has a proper Django FK back to Contact (`contact_id`, CASCADE).

### 3b. Org Associations — Real ForeignKeys

| FK Field (on Contact) | Django Field | Points To          | OrgBase.org_type |
|-----------------------|-------------|---------------------|------------------|
| `customer_id`         | `customer`  | `orgs.OrgBase`      | `customer`       |
| `vendor_id`           | `vendor`    | `orgs.OrgBase`      | `vendor`         |
| `rep_id`              | `rep`       | `orgs.OrgBase`      | `rep`            |
| `employee_id`         | `employee`  | `orgs.OrgBase`      | `employee`       |
| `manufacturer_id`     | `manufacturer` | `orgs.OrgBase`   | `manufacturer`   |
| `other_id`            | (BigIntegerField) | any          | —                |

- All except `other_id` are proper Django FKs with `SET_NULL`.
- OrgBase is a **single table** with a `org_type` discriminator + proxy models.

---

## 4. Panel Layout — Visual Spec

### 4a. Overall Structure (ContactDetail3 — Edit Mode)

```
┌──────────────────────────────────────────────────────┐
│  Header   (name, #id, status badges)                 │
├──────────────────────────────────────────────────────┤
│  Toolbar  (Save / Cancel)                            │
├──────────────────────────────────────────────────────┤
│  Name Fields       (name_first, name_last, etc.)     │ ← existing form fields
├──────────────────────────────────────────────────────┤
│  ┌─ Email Panel ─────────────────────────────────┐   │
│  │  email: user@example.com   (scalar, editable) │   │
│  │  ┌──────────────────────────────────────────┐ │   │
│  │  │ ★ #42  user@example.com   Work           │ │   │  ← primary (matches email_id)
│  │  │   #87  alt@example.com    Personal        │ │   │
│  │  │   + Add   🔍 Search existing              │ │   │
│  │  └──────────────────────────────────────────┘ │   │
│  └───────────────────────────────────────────────┘   │
│  ┌─ Phone Panel ─────────────────────────────────┐   │
│  │  phone: (555) 123-4567     (scalar, editable) │   │
│  │  ┌──────────────────────────────────────────┐ │   │
│  │  │ ★ #15  (555) 123-4567   Mobile           │ │   │
│  │  │   #16  (555) 987-6543   Office            │ │   │
│  │  │   + Add   🔍 Search existing              │ │   │
│  │  └──────────────────────────────────────────┘ │   │
│  └───────────────────────────────────────────────┘   │
│  ┌─ Address Panel ───────────────────────────────┐   │
│  │  address_full: 123 Main St, City, ST 12345    │   │
│  │  ┌──────────────────────────────────────────┐ │   │
│  │  │ ★ #9  123 Main St …     Billing          │ │   │
│  │  │   #10 456 Oak Ave …     Shipping          │ │   │
│  │  │   + Add   🔍 Search existing              │ │   │
│  │  └──────────────────────────────────────────┘ │   │
│  └───────────────────────────────────────────────┘   │
│  ┌─ Domain Panel ────────────────────────────────┐   │
│  │  domain: example.com       (scalar, editable) │   │
│  │  ┌──────────────────────────────────────────┐ │   │
│  │  │ ★ #3  example.com       Website           │ │   │
│  │  │   + Add   🔍 Search existing              │ │   │
│  │  └──────────────────────────────────────────┘ │   │
│  └───────────────────────────────────────────────┘   │
├──────────────────────────────────────────────────────┤
│  ┌─ Organization Panels ─────────────────────────┐   │
│  │  customer_id: 42 — Acme Corp         ★        │   │
│  │  vendor_id:   — (none)                         │   │
│  │  rep_id:      17 — Jane Smith         ★        │   │
│  │  employee_id: — (none)                         │   │
│  │  manufacturer_id: — (none)                     │   │
│  │  other_id:    — (none)                         │   │
│  │  🔍 Assign Org                                 │   │
│  └───────────────────────────────────────────────┘   │
├──────────────────────────────────────────────────────┤
│  Company Fields    (company, title, department, etc.)│
│  Auth Fields       (is_active, is_staff, passwords)  │
├──────────────────────────────────────────────────────┤
│  Tab Navigation                                      │
│  Tab Content                                         │
└──────────────────────────────────────────────────────┘
```

### 4b. View Mode

In view mode the panels are read-only. Same layout but:
- Scalar field displayed as label/value (not editable input)
- Linked records listed with ★ badge on the primary
- No "+ Add" or "Search existing" buttons

---

## 5. Communication Panel Component

### 5a. New Component: `CommLinkPanel`

```
src/apps/common/components/panels/CommLinkPanel.tsx
```

#### Props

```typescript
interface CommLinkPanelProps {
  /** "email" | "phone" | "address" | "domain" */
  type: CommType;
  /** Panel title (defaults to capitalized type) */
  title?: string;
  /** The denormalized scalar value from the contact record */
  scalarValue: string | null | undefined;
  /** The *_id field value — which linked record is primary */
  primaryId: number | null | undefined;
  /** All linked records for this type (from communications state) */
  items: any[];
  /** Whether the form is in edit/add mode */
  isEditing: boolean;
  /** Called when user updates the scalar field */
  onScalarChange?: (value: string) => void;
  /** Called when user selects an existing record as primary */
  onSetPrimary?: (id: number, displayValue: string) => void;
  /** Called when user clicks "Search existing" */
  onSearchExisting?: () => void;
  /** Called when user clicks "+ Add" */
  onAddNew?: () => void;
  /** Called when user clicks a record row to view/edit it */
  onItemClick?: (item: any) => void;
}
```

#### Behavior

| Action | Effect |
|--------|--------|
| Click ★ on a non-primary record | Calls `onSetPrimary(id, displayValue)` → updates contact `*_id` + scalar |
| Edit scalar input | Calls `onScalarChange(value)` → updates react-hook-form field value |
| Click "Search existing" | Opens search dialog (reuse existing `CommSelectDialog` pattern) |
| Click "+ Add" | Opens `CommunicationAddEditModal` for this type |
| Click a record row | Opens inline edit or navigates to detail page |

#### Record Row Anatomy

```
┌──────────────────────────────────────────────────────┐
│ ★  #42   user@example.com           Work    ✎  ✕    │
│ ↑   ↑          ↑                     ↑      ↑  ↑    │
│ star id    display value            type   edit del  │
└──────────────────────────────────────────────────────┘
```

- **★** = filled gold star if `item.id === primaryId`, outline otherwise
- **#id** = mono font, subtle color
- **display value** = `email` / `number` / `full` / `path` depending on type
- **type/name** = secondary text
- **✎ / ✕** = edit / unlink actions (edit mode only)

### 5b. Display Value Resolution

| Type    | Display Field Priority                        |
|---------|-----------------------------------------------|
| email   | `item.email` → `item.address` → `item.value`  |
| phone   | `item.number` → `item.value` → `item.format`  |
| address | `item.full` → build from `address1, city, state, zip` |
| domain  | `item.path` → `item.domain` → `item.value`    |

---

## 6. Org Association Panel Component

### 6a. New Component: `OrgLinkPanel`

```
src/apps/common/components/panels/OrgLinkPanel.tsx
```

#### Props

```typescript
interface OrgLinkPanelProps {
  /** All org FK fields and their current values */
  orgFields: {
    field: string;              // "customer_id", "vendor_id", etc.
    label: string;              // "Customer", "Vendor", etc.
    value: number | null;       // Current FK value
    displayName?: string;       // Resolved name from OrgBase
    orgType: SearchableOrgType; // For search dialog filtering
  }[];
  /** "other_id" value (BigIntegerField, not typed) */
  otherId?: number | null;
  /** Whether the form is in edit/add mode */
  isEditing: boolean;
  /** Called when user selects an org from search */
  onOrgSelect?: (field: string, org: OrgSearchResult) => void;
  /** Called when user clears an org association */
  onOrgClear?: (field: string) => void;
}
```

#### Behavior

| Action | Effect |
|--------|--------|
| Click 🔍 on a field row | Opens `OrgSearchDialog` filtered to that org_type |
| Click ✕ on a populated field | Calls `onOrgClear(field)` → sets FK to null |
| Select from search dialog | Calls `onOrgSelect(field, org)` → sets FK + display name |

#### Row Anatomy

```
┌──────────────────────────────────────────────────────┐
│  customer_id:   42  ★ Acme Corp               🔍 ✕  │
│  vendor_id:     —   (none)                     🔍    │
│  rep_id:        17  ★ Jane Smith               🔍 ✕  │
│  employee_id:   —   (none)                     🔍    │
│  manufacturer:  —   (none)                     🔍    │
│  other_id:      —   (none)                     🔍    │
└──────────────────────────────────────────────────────┘
```

- **★** = gold star appears when field has a value (i.e., org is linked)
- **🔍** = search button (edit mode only)
- **✕** = clear button, only when a value is set (edit mode only)

---

## 7. Search-Existing Flow

### 7a. Communication Search

When user clicks "Search existing" in a `CommLinkPanel`:

```
1. Open modal/dropdown with search input
2. User types → debounced call to getRecords(type, { search: query, limit: 50 })
3. Results rendered as selectable rows
4. Show ALL results (not just this contact's records)
5. Results already linked to this contact get a "linked" badge
6. User clicks a result →
   a. If already linked to this contact → just set as primary
   b. If linked to another contact → create new copy for this contact, then set as primary
   c. If unlinked → link to this contact, then set as primary
```

### 7b. Org Search

Reuses the existing `OrgSearchDialog` component. No changes needed — it already
filters by `org_type` and returns `OrgSearchResult` with `id`, `display_name`,
`ida`, `email`, `phone`.

---

## 8. Save Payload — Composite Body

### 8a. Current Approach (ContactDetail / ContactDetail2)

```typescript
// r25 → POST /wcapi/save/
{
  model_name: "contact",
  // Scalar fields only
  email: "user@example.com",
  name_first: "John",
  name_last: "Doe",
  customer_id: 42,
  // ... etc
}
```

Communications are saved by **separate** `saveRecord("email", {...})` calls from the
`CommunicationsPanel` and picker dialogs. This works but is fragmented.

### 8b. New Approach (ContactDetail3)

Two strategies — choose one:

#### Option A: Keep Separate Calls (Recommended for Phase 1)

Keep the existing pattern of separate `saveRecord` calls for each comm/org,
but **orchestrate them from the panel components** instead of scattering across
dialogs and tabs. The contact save payload stays scalar-only.

**Pros**: No wc3 backend changes needed. Proven pattern.
**Cons**: Multiple round trips. No atomicity.

#### Option B: Composite Payload (Future — requires wc3 changes)

Submit everything in one body:

```typescript
{
  model_name: "contact",
  // Contact scalars
  email: "user@example.com",
  name_first: "John",
  // Communications — upsert
  _communications: {
    emails: [
      { id: 42, email: "user@example.com", is_primary: true },
      { email: "alt@example.com", name: "Personal" },  // new, no id
    ],
    phones: [
      { id: 15, number: "5551234567", is_primary: true },
    ],
    addresses: [...],
    domains: [...],
  },
  // Org associations
  customer_id: 42,
  vendor_id: null,
  rep_id: 17,
  // ...
}
```

**wc3 changes required**: Add a hook in `SaveWcapiView` (or a dedicated
`ContactSaveService`) that intercepts the `_communications` key, processes
each child list (create/update/link), sets the `*_id` primary pointers,
and denormalizes scalar values — all within a single `transaction.atomic()`.

**Pros**: Single round trip. Atomic. Cleaner.
**Cons**: Backend work. More complex error handling.

---

## 9. Implementation Plan

### Phase 1 — Panel UX (r25 only, no wc3 changes)

| Step | Task | File(s) |
|------|------|---------|
| 1.1 | Create `CommLinkPanel` component | `src/apps/common/components/panels/CommLinkPanel.tsx` |
| 1.2 | Create `OrgLinkPanel` component | `src/apps/common/components/panels/OrgLinkPanel.tsx` |
| 1.3 | Update `ContactDetail3.tsx` edit mode — replace inline comm pickers with `CommLinkPanel` × 4 | `ContactDetail3.tsx` |
| 1.4 | Update `ContactDetail3.tsx` edit mode — replace org ID inputs with `OrgLinkPanel` | `ContactDetail3.tsx` |
| 1.5 | Update `ContactDetail3.tsx` view mode — render `CommLinkPanel` (read-only) + `OrgLinkPanel` (read-only) in the cards area | `ContactDetail3.tsx` |
| 1.6 | Wire search/add callbacks to existing dialog components | `ContactDetail3.tsx` |
| 1.7 | Test: verify save produces same backend result as `ContactDetail` | Manual QA |

### Phase 2 — Composite Save (r25 + wc3)

| Step | Task | File(s) |
|------|------|---------|
| 2.1 | Create `ContactSaveService` in wc3 | `apps/core/services/contact_save.py` |
| 2.2 | Register hook in `SaveWcapiView` for `model_name="contact"` | `apps/core/views/save_view.py` |
| 2.3 | Implement `_communications` processing — upsert, link, set primary | `contact_save.py` |
| 2.4 | Update `contactApi.ts` to build composite payload | `contactApi.ts` |
| 2.5 | Update `ContactDetail3.tsx` to submit single payload | `ContactDetail3.tsx` |
| 2.6 | Add tests for composite save | `tests/test_contact_save.py` |

### Phase 3 — Polish

| Step | Task |
|------|------|
| 3.1 | Inline editing of comm record fields within the panel row |
| 3.2 | Drag-to-reorder records within a panel |
| 3.3 | Optimistic UI updates |
| 3.4 | Keyboard shortcuts (↑↓ to navigate, ★ to set primary) |

---

## 10. File Inventory

### New Files

| File | Purpose |
|------|---------|
| `src/apps/common/components/panels/CommLinkPanel.tsx` | Communication link panel (email/phone/address/domain) |
| `src/apps/common/components/panels/OrgLinkPanel.tsx` | Org association panel (customer/vendor/rep/employee/manufacturer) |
| `apps/core/services/contact_save.py` (Phase 2) | Composite save service in wc3 |

### Modified Files

| File | Change |
|------|--------|
| `ContactDetail3.tsx` | Replace comm pickers + org inputs with panel components |
| `save_view.py` (Phase 2) | Hook for contact composite save |
| `contactApi.ts` (Phase 2) | Build composite payload |

### Untouched

| File | Reason |
|------|--------|
| `ContactDetail.tsx` | Original — no changes |
| `ContactDetail2.tsx` | ScalarCard variant — no changes |
| `CommunicationsPanel.tsx` | Tab panel — still used in the Comms tab |

---

## 11. Open Questions

| # | Question | Default |
|---|----------|---------|
| Q1 | Should comm panels be collapsible like ScalarCards? | Yes — collapsed by default in view mode, expanded in edit mode |
| Q2 | Should "Search existing" search globally or only this contact's records? | Global search, with "already linked" badges |
| Q3 | Should changing the ★ primary auto-update the scalar field? | Yes — mirror the display value into the scalar |
| Q4 | Should we allow unlinking a comm record (remove from contact) vs just un-starring? | Yes — ✕ unlinks, ★ toggle changes primary |
| Q5 | Phase 2 composite save — wrap in `transaction.atomic()`? | Yes — all or nothing |
| Q6 | Should OrgLinkPanel show org display_name inline or require click to see? | Show inline: `42 ★ Acme Corp` |

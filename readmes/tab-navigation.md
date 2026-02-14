# Tab Navigation Reference

How tab navigation works across Detail and Display pages.

---

## Architecture

`DetailTabs` is the single source of truth for tab navigation. It lives at
`src/components/common/DetailTabs.tsx` and handles:

1. **Tab bar rendering** — tab buttons with icons, badges, role-based visibility
2. **Standard panel rendering** — when `recordData` is provided, DetailTabs auto-renders
   the correct panel (ActionsPanel, CommentsPanel, DocumentsPanel, FinancialsPanel,
   or JsonFieldEditor) for the active standard tab
3. **Custom tab content** — model-specific tabs inject their own `content: ReactNode`
   via `additionalTabs`

### Standard Tabs

These tab IDs are built-in with pre-configured icons and behavior (alphabetical):

| Tab ID | Icon | Auto-renders | Admin-only |
|--------|------|:------------:|:----------:|
| `actions` | FaTasks | ActionsPanel | — |
| `comments` | FaComments | CommentsPanel | — |
| `contacts` | FaUsers | — | — |
| `documents` | FaFile | DocumentsPanel | — |
| `financials` | FaDollarSign | FinancialsPanel | — |
| `overview` | FaInfoCircle | — | — |
| `raw` | FaCode | JsonFieldEditor | ✓ |

> `overview` is not in `DEFAULT_STANDARD_TABS` — the overview section is rendered
> persistently above the tab bar. Pass it explicitly in `standardTabs` only if needed.
>
> `contacts` provides a tab button only — its content varies per page and should be
> rendered via `additionalTabs[].content`.

### Removed Tabs

The following tabs were removed from the standard set. Their data is accessible
through the **Raw** tab, which has an admin-only edit button:

- ~~history~~ — viewable in Raw
- ~~metadata~~ — viewable in Raw
- ~~prefs~~ — viewable in Raw
- ~~refs~~ — viewable in Raw

---

## Usage Patterns

### Pattern 1 — Standard Tabs (recommended)

The simplest approach. Pass standard tab IDs and record data — DetailTabs
handles everything:

```tsx
import { DetailTabs, useDetailTabs } from "@/components/common/DetailTabs";

// In component:
const { activeTab, setActiveTab } = useDetailTabs("campaign_detail", "actions", [
  "actions", "comments", "documents", "raw",
]);

<DetailTabs
  entityType="campaign_detail"
  activeTab={activeTab}
  onTabChange={setActiveTab}
  standardTabs={["actions", "comments", "documents", "raw"]}
  badges={{
    comments: recordData?.comments?.length,
    documents: recordData?.refs?.links?.document?.length,
  }}
  panelEntityType="campaign"
  entityId={recordData.id}
  recordData={recordData}
  isEditing={currentMode !== "view"}
  onRecordChange={setRecordData}
/>
```

No panel imports needed. No render blocks. DetailTabs renders the active panel
automatically.

### Pattern 2 — Standard + Custom Tabs

When a page needs model-specific tabs alongside standard ones:

```tsx
<DetailTabs
  entityType="customer"
  activeTab={activeTab}
  onTabChange={setActiveTab}
  standardTabs={["actions", "comments", "documents", "raw"]}
  additionalTabs={[
    {
      id: "contacts",
      label: "Contacts",
      icon: <FaUsers size={14} />,
      content: <ContactsPanel parentModel="customer" parentId={data.id} />,
    },
    {
      id: "financial",
      label: "Financial",
      icon: <FaDollarSign size={14} />,
      content: <FinancialsPanel totals={data?.financial?.totals} />,
    },
  ]}
  panelEntityType="customer"
  entityId={data.id}
  recordData={data}
  isEditing={mode !== "view"}
  onRecordChange={setData}
/>
```

### Pattern 3 — Tab Bar Only (legacy)

If `recordData` is not provided, DetailTabs renders only the tab bar.
The page handles panel rendering manually. This is the legacy pattern —
migrate to Pattern 1 or 2 when possible.

```tsx
<DetailTabs
  entityType="currency"
  activeTab={activeTab}
  onTabChange={setActiveTab}
  standardTabs={["comments", "actions", "raw"]}
/>
{/* Manual panel rendering below */}
{activeTab === "comments" && <CommentsPanel ... />}
```

---

## Props Reference

### DetailTabsProps

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `activeTab` | `string` | — | Currently active tab ID |
| `additionalTabs` | `TabConfig[]` | `[]` | Custom tabs with optional `content` |
| `badges` | `Record<string, number \| string>` | `{}` | Badge counts for tabs |
| `className` | `string` | `''` | CSS class for the tab bar |
| `columnCount` | `2 \| 3` | `3` | Current column count |
| `entityId` | `string \| number` | — | Entity ID for panel components |
| `entityType` | `string` | — | localStorage key prefix for tab persistence |
| `isEditing` | `boolean` | `false` | Whether panels are in edit mode |
| `onColumnCountChange` | `(count: 2 \| 3) => void` | — | Column change callback |
| `onRecordChange` | `(data: any) => void` | — | Callback when panels update record data |
| `onTabChange` | `(tabId: string) => void` | — | Tab change callback |
| `panelEntityType` | `string` | `entityType` | Entity type for panels (e.g., "campaign") |
| `recordData` | `any` | — | Full record data (triggers auto panel rendering) |
| `showColumnSelector` | `boolean` | `false` | Show 2/3 column layout selector |
| `standardTabs` | `StandardTabId[]` | `['actions','comments','documents','raw']` | Which built-in tabs to show |

### TabConfig

| Field | Type | Description |
|-------|------|-------------|
| `adminOnly` | `boolean` | Only visible to admin users |
| `badge` | `number \| string` | Optional badge count |
| `content` | `ReactNode` | Panel content rendered when tab is active |
| `hidden` | `boolean` | Hide this tab |
| `icon` | `ReactNode` | Optional icon element |
| `id` | `string` | Unique tab identifier |
| `label` | `string` | Display label |
| `roles` | `string[]` | Only visible to these roles |

---

## Tab Tiers

### Tier 1 — Base (every model)

Every detail page receives these four tabs by default via `DEFAULT_STANDARD_TABS`:

| Tab | Panel | Notes |
|-----|-------|-------|
| `actions` | ActionsPanel | auto-rendered |
| `comments` | CommentsPanel | auto-rendered |
| `documents` | DocumentsPanel | auto-rendered |
| `raw` | JsonFieldEditor | auto-rendered, admin-only |

Pages that need nothing beyond these four pass no `additionalTabs` at all.

**Models using base only:**
Accounts (Audit, Currency, Exchange Rate, Exchange Transaction, GL Account, GL Journal),
Products (Bill of Material, Catalog, Flow, Item, ItemXref, Matrics, OrgItem, Serial,
Service, Spec, Usage, Variant, Warehouse),
Core/Docs (Bundle, Campaign, Connection, Document, Report, Setting, Template).

### Tier 2 — Org Tabs (Customer & Vendor)

Orgs extend the base with five `additionalTabs`:

| Tab | Panel | Notes |
|-----|-------|-------|
| `contacts` | ContactPanel | linked contacts |
| `financials` | FinancialsPanel | totals, cost, sell, currency |
| `items` | *ItemsPanel* | lines from transactions + serials (see below) |
| `qa` | QAPanel | question groups |
| `transactions` | *TransactionsPanel* | sub-tables per org type (see below) |

#### `transactions` tab — contents by org type

| Org type | Sub-tables |
|----------|------------|
| Customer | proposals, orders, invoices, ledgers, payments |
| Vendor | purchases, receipts |

The TransactionsPanel renders a filterable list grouped by sub-table type.
Each row links to its transaction detail page.

#### `items` tab

Shows line items sourced from the org's transactions plus any linked serials.
Provides a consolidated view of every product the org has interacted with.

### Tier 3 — Transaction Tabs (via TransactionDetailBase)

Transactions use their own tab system within `TransactionDetailBase`:

| Tabs | Details |
|------|---------|
| Built-in | actions, comments, contacts, documents, financials, qa, raw |
| Custom per type | receiving (Purchase), shipping (Order/Invoice), tax (Invoice) |

### Tier 4 — Communications

| Page | standardTabs | additionalTabs |
|------|-------------|----------------|
| Address | actions, comments, documents, raw | contacts, financials |
| Domain, Email, Phone | actions, comments, documents, raw | contacts |

### Admin-Only

| Page | Mechanism |
|------|-----------|
| OrgDetail (Employee wrapper) | Custom tab bar, 17 defaultTabs — not using DetailTabs |

---

## Tab Tier Summary

```
┌─────────────────────────────────────────────────────┐
│  Tier 1 — Base (all models)                         │
│  actions · comments · documents · raw               │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │  Tier 2 — Orgs (Customer / Vendor)            │  │
│  │  + contacts · financials · items · qa         │  │
│  │  + transactions                               │  │
│  │    Customer: proposals, orders, invoices,     │  │
│  │              ledgers, payments                │  │
│  │    Vendor:   purchases, receipts              │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │  Tier 3 — Transactions (own tab system)       │  │
│  │  + contacts · financials · qa                 │  │
│  │  + type-specific: receiving, shipping, tax    │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │  Tier 4 — Communications                     │  │
│  │  + contacts (all) · financials (Address only) │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## Migration Status

Pages migrated to auto-rendering (Pattern 1):

| Status | Pages |
|--------|-------|
| ✅ Migrated | AuditDetail, BundleDetail, CampaignDetail, ConnectionDetail, ReportDetail, SettingDetail |
| ⬜ Pending | Accounts, Communications, Core/Docs, Customer, Item, Products (Detail + Display), Vendor |
| N/A | TransactionDetailBase (own tab system), OrgDetail (own tab system), Line editors (no tabs) |

---

## Hooks

### `useDetailTabs(entityType, defaultTab, validTabs?)`

Manages active tab state with localStorage persistence.

```tsx
const { activeTab, setActiveTab } = useDetailTabs("campaign_detail", "actions", [
  "actions", "comments", "documents", "raw",
]);
```

### `useColumnCount(entityType, defaultCount?)`

Manages 2/3 column layout state with localStorage persistence.

```tsx
const { columnCount, setColumnCount } = useColumnCount("campaignDetail_columnCount", 3);
```

---

## File Locations

| Component | Path | Status |
|-----------|------|--------|
| ActionsPanel | `src/apps/common/components/panels/ActionsPanel.tsx` | ✅ |
| BasicInformationPanel | `src/apps/common/components/panels/BasicInformationPanel.tsx` | ✅ |
| CommentsPanel | `src/apps/common/components/panels/CommentsPanel.tsx` | ✅ |
| CommunicationsPanel | `src/apps/common/components/panels/CommunicationsPanel.tsx` | ✅ |
| ContactPanel | `src/apps/common/components/panels/ContactPanel.tsx` | ✅ |
| DetailTabs | `src/components/common/DetailTabs.tsx` | ✅ |
| DocumentsPanel | `src/apps/common/components/panels/DocumentsPanel.tsx` | ✅ |
| FinancialsPanel | `src/apps/common/components/panels/FinancialsPanel.tsx` | ✅ |
| ItemsPanel | `src/apps/common/components/panels/ItemsPanel.tsx` | ✅ |
| JsonFieldEditor | `src/apps/common/components/JsonFieldEditor.tsx` | ✅ |
| LinkagesPanel | `src/apps/common/components/panels/LinkagesPanel.tsx` | ✅ |
| MetadataPanel | `src/apps/common/components/panels/MetadataPanel.tsx` | ✅ |
| ModelDataPanel | `src/apps/common/components/panels/ModelDataPanel.tsx` | ✅ |
| PrefsPanel | `src/apps/common/components/panels/PrefsPanel.tsx` | ✅ |
| QAPanel | `src/apps/common/components/panels/QAPanel.tsx` | ✅ |
| RawDataPanel | `src/apps/common/components/panels/RawDataPanel.tsx` | ✅ |
| RefsPanel | `src/apps/common/components/panels/RefsPanel.tsx` | ✅ |
| SerialPanel | `src/apps/common/components/panels/SerialPanel.tsx` | ✅ |
| ShippingPanel | `src/apps/common/components/panels/ShippingPanel.tsx` | ✅ |
| TemplateQAPanel | `src/apps/common/components/panels/TemplateQAPanel.tsx` | ✅ |
| TransactionsPanel | `src/apps/common/components/panels/TransactionsPanel.tsx` | ✅ |
| Panel barrel export | `src/apps/common/components/panels/index.ts` | ✅ |
| Panel types | `src/apps/common/components/panels/types.ts` | ✅ |
| Document upload utils | `src/apps/common/components/panels/documentUpload.ts` | ✅ |
| QA utilities | `src/apps/common/components/panels/qaUtils.ts` | ✅ |
| Permissions hook | `src/apps/common/components/panels/usePermissions.ts` | ✅ |

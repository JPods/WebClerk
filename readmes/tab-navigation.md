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

These tab IDs are built-in with pre-configured icons and behavior:

| Tab ID | Icon | Auto-renders | Admin-only |
|--------|------|:------------:|:----------:|
| `overview` | FaInfoCircle | — | — |
| `contacts` | FaUsers | — | — |
| `comments` | FaComments | CommentsPanel | — |
| `actions` | FaTasks | ActionsPanel | — |
| `documents` | FaFile | DocumentsPanel | — |
| `financials` | FaDollarSign | FinancialsPanel | — |
| `raw` | FaCode | JsonFieldEditor | ✓ |

> `overview` and `contacts` provide tab buttons only — their content varies per page
> and should be rendered via `additionalTabs[].content` when needed.

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
| `entityType` | `string` | — | localStorage key prefix for tab persistence |
| `activeTab` | `string` | — | Currently active tab ID |
| `onTabChange` | `(tabId: string) => void` | — | Tab change callback |
| `standardTabs` | `StandardTabId[]` | `['overview','comments','actions','documents','raw']` | Which built-in tabs to show |
| `additionalTabs` | `TabConfig[]` | `[]` | Custom tabs with optional `content` |
| `badges` | `Record<string, number \| string>` | `{}` | Badge counts for tabs |
| `entityId` | `string \| number` | — | Entity ID for panel components |
| `recordData` | `any` | — | Full record data (triggers auto panel rendering) |
| `panelEntityType` | `string` | `entityType` | Entity type for panels (e.g., "campaign") |
| `isEditing` | `boolean` | `false` | Whether panels are in edit mode |
| `onRecordChange` | `(data: any) => void` | — | Callback when panels update record data |
| `showColumnSelector` | `boolean` | `false` | Show 2/3 column layout selector |
| `columnCount` | `2 \| 3` | `3` | Current column count |
| `onColumnCountChange` | `(count: 2 \| 3) => void` | — | Column change callback |
| `className` | `string` | `''` | CSS class for the tab bar |

### TabConfig

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Unique tab identifier |
| `label` | `string` | Display label |
| `icon` | `ReactNode` | Optional icon element |
| `badge` | `number \| string` | Optional badge count |
| `adminOnly` | `boolean` | Only visible to admin users |
| `roles` | `string[]` | Only visible to these roles |
| `hidden` | `boolean` | Hide this tab |
| `content` | `ReactNode` | Panel content rendered when tab is active |

---

## Tab Layouts by Page Group

### Customer & Vendor

| Page | standardTabs | additionalTabs |
|------|-------------|----------------|
| Customer | actions, comments, documents, raw | contacts, financial, qa |
| Vendor | actions, comments, documents, overview, raw | contacts, financial, qa |

### Transactions (via TransactionDetailBase)

| Tabs | Details |
|------|---------|
| Built-in | actions, comments, contacts, documents, financials, qa, raw |
| Custom per type | shipping (Order/Invoice), tax (Invoice), receiving (Purchase) |

### Products (Detail + Display pages)

| Page | standardTabs |
|------|-------------|
| Catalog, Flow, Matrics, Serial, Service, Spec, Variant, Warehouse, Usage, ItemXref, OrgItem | actions, comments, documents, raw |
| Item | actions, comments, documents, raw (two render paths: view + edit) |
| Bill of Material | actions, comments, documents, raw |

### Accounts

| Page | standardTabs |
|------|-------------|
| Currency, GL Account, Exchange Rate, Exchange Transaction, GL Journal | comments, actions, raw |
| Audit | actions, comments, documents, raw |

### Communications

| Page | standardTabs |
|------|-------------|
| Address | contacts, comments, actions, documents, financials, raw |
| Phone, Email, Domain | contacts, comments, actions, documents, raw |

### Core / Docs

| Page | Tabs |
|------|------|
| Setting, Report, Campaign, Bundle, Connection | actions, comments, documents, raw (migrated to auto-rendering) |
| Template | actions, comments, documents, raw |
| Action | comments, documents, qa, contacts |
| Contact | actions, comments, communications, documents, raw |
| Document | actions, comments, documents, raw |

### Admin-Only

| Page | Mechanism |
|------|-----------|
| OrgDetail (Employee wrapper) | Custom tab bar, 17 defaultTabs — not using DetailTabs |

---

## Migration Status

Pages migrated to auto-rendering (Pattern 1):

| Status | Pages |
|--------|-------|
| ✅ Migrated | CampaignDetail, BundleDetail, ConnectionDetail, AuditDetail, ReportDetail, SettingDetail |
| ⬜ Pending | Products (Detail + Display), Accounts, Communications, Core/Docs, Customer, Vendor, Item |
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

| Component | Path |
|-----------|------|
| DetailTabs | `src/components/common/DetailTabs.tsx` |
| ActionsPanel | `src/apps/common/components/panels/ActionsPanel.tsx` |
| CommentsPanel | `src/apps/common/components/panels/CommentsPanel.tsx` |
| DocumentsPanel | `src/apps/common/components/panels/DocumentsPanel.tsx` |
| FinancialsPanel | `src/apps/common/components/panels/FinancialsPanel.tsx` |
| RawDataPanel | `src/apps/common/components/panels/RawDataPanel.tsx` |
| JsonFieldEditor | `src/apps/common/components/JsonFieldEditor.tsx` |
| Panel types | `src/apps/common/components/panels/types.ts` |

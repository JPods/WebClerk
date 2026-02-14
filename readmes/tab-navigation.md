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
| `actions` | FaTasks | ActionsPanel | — |
| `comments` | FaComments | CommentsPanel | — |
| `contacts` | FaUsers | — | — |
| `documents` | FaFile | DocumentsPanel | — |
| `financials` | FaDollarSign | FinancialsPanel | — |
| `overview` | FaInfoCircle | — | — |
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
| `standardTabs` | `StandardTabId[]` | `['actions','comments','documents','overview','raw']` | Which built-in tabs to show |

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

## Tab Layouts by Page Group

### Customer & Vendor

| Page | standardTabs | additionalTabs |
|------|-------------|----------------|
| Customer | actions, comments, documents, raw | contacts, financial, qa |
| Vendor | actions, comments, documents, overview, raw | contacts, financial, qa |

> Tab IDs within each cell are listed alphabetically.

### Transactions (via TransactionDetailBase)

| Tabs | Details |
|------|---------|
| Built-in | actions, comments, contacts, documents, financials, qa, raw |
| Custom per type | receiving (Purchase), shipping (Order/Invoice), tax (Invoice) |

### Products (Detail + Display pages)

| Page | standardTabs |
|------|-------------|
| Bill of Material | actions, comments, documents, raw |
| Catalog, Flow, ItemXref, Matrics, OrgItem, Serial, Service, Spec, Usage, Variant, Warehouse | actions, comments, documents, raw |
| Item | actions, comments, documents, raw (two render paths: view + edit) |

### Accounts

| Page | standardTabs |
|------|-------------|
| Audit | actions, comments, documents, raw |
| Currency, Exchange Rate, Exchange Transaction, GL Account, GL Journal | actions, comments, raw |

### Communications

| Page | standardTabs |
|------|-------------|
| Address | actions, comments, contacts, documents, financials, raw |
| Domain, Email, Phone | actions, comments, contacts, documents, raw |

### Core / Docs

| Page | Tabs |
|------|------|
| Action | comments, contacts, documents, qa |
| Bundle, Campaign, Connection, Report, Setting | actions, comments, documents, raw (migrated to auto-rendering) |
| Contact | actions, comments, communications, documents, raw |
| Document | actions, comments, documents, raw |
| Template | actions, comments, documents, raw |

### Admin-Only

| Page | Mechanism |
|------|-----------|
| OrgDetail (Employee wrapper) | Custom tab bar, 17 defaultTabs — not using DetailTabs |

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

| Component | Path |
|-----------|------|
| ActionsPanel | `src/apps/common/components/panels/ActionsPanel.tsx` |
| CommentsPanel | `src/apps/common/components/panels/CommentsPanel.tsx` |
| DetailTabs | `src/components/common/DetailTabs.tsx` |
| DocumentsPanel | `src/apps/common/components/panels/DocumentsPanel.tsx` |
| FinancialsPanel | `src/apps/common/components/panels/FinancialsPanel.tsx` |
| JsonFieldEditor | `src/apps/common/components/JsonFieldEditor.tsx` |
| Panel types | `src/apps/common/components/panels/types.ts` |
| RawDataPanel | `src/apps/common/components/panels/RawDataPanel.tsx` |

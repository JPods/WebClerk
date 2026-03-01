# `refs.links` — Frontend Consumption Guide

Every record in the system carries a `refs` JSONB column with a `links`
sub-object that holds **denormalized snapshots** of related entities.
This is the **single source of truth** for which related records belong to
a given parent — the frontend reads from `refs.links` and never queries
related models independently to build tab/panel data.

See also: `webClerk3/readmes/denorm-fields.md` for the backend denormalization
mechanics and field lists.

---

## 1. Structure

```jsonc
{
  "refs": {
    "links": {
      // Org roles — single dict (not array) for 1:1
      "customer": { "id": 42, "company": "Acme Corp", "email": "..." },
      "vendor":   { "id": 88, "company": "WidgetCo", "email": "..." },

      // Related records — arrays of snapshot dicts
      "contact":  [{ "id": 6, "display_name": "Jane", "purpose": "billto" }, ...],
      "action":   [{ "id": 101, "ida": "101", "name": "Follow up" }, ...],
      "document": [{ "id": 55, "ida": "55", "name": "PO.pdf", "type": "pdf" }, ...],
      "email":    [{ "id": 12, "email": "billing@acme.com", "name": "billing" }, ...],
      "phone":    [{ "id": 14, "number": "555-1234", "name": "office" }, ...],
      "address":  [{ "id": 223, "address1": "123 Main", "city": "Springfield", ... }],
      "item":     [{ "id": 300, "sku": "WDG-100", "name": "Widget" }],
      "project":  [{ "id": 7, "name": "2025 Refresh", "status": "active" }]
    },
    "keywords": ["acme", "widget", "rush"],
    "categories": []
  }
}
```

Each snapshot dict always includes `id` (numeric PK). Additional fields come
from `common/denorm_registry.py` on the backend — the frontend **never
hard-codes** which fields exist; it reads whatever the snapshot provides.

---

## 2. Golden Rule: Read from `refs.links`, Not from Separate Queries

| Correct | Wrong |
|---------|-------|
| `data.refs?.links?.contact` | `getRecords("contact", { parent_id })` |
| `data.refs?.links?.action`  | `getRecords("action", { parent_model, parent_id })` |
| `data.refs?.links?.email`   | `getRecords("email", { contact_id })` |

Separate queries return **all** records matching the FK — not just those
linked to this specific parent. `refs.links` is curated and scoped.

### When to Query the Full Record

Only when the user wants to **edit** a related record do we fetch it by ID:

```ts
// Display: use snapshot from refs.links
const actions = data.refs?.links?.action ?? [];

// Edit: fetch full record for the modal
const fullAction = await getRecord("action", actionId);
```

---

## 3. Tab Data Binding Pattern

Every detail page tab that shows related records follows the same pattern:

```tsx
// In renderCustomTab or renderTabContent
case "actions": {
  // 1. Extract IDs from refs.links (source of truth)
  const actionIds = (data.refs?.links?.action ?? [])
    .map((a: any) => typeof a === "number" ? a : a?.id)
    .filter((id: any): id is number => typeof id === "number");

  // 2. Fetch full records only for those IDs
  //    (useTransactionTasks hook with useActionIds: true)

  // 3. Render the table with fetched data
  return <ActionsTable actions={fetchedActions} actionIds={actionIds} />;
}

case "contacts":
  return (
    <ContactPanel
      contacts={normalizeRefsLinksContact(data.refs?.links?.contact ?? [])}
    />
  );

case "documents":
  return (
    <DocumentsPanel
      documents={data.refs?.links?.document ?? []}
    />
  );
```

### Pattern for Hooks

When a hook fetches related records, pass the IDs from `refs.links`:

```ts
const actionIds = useMemo(() => {
  const refsActions = data?.refs?.links?.action;
  if (!Array.isArray(refsActions)) return [];
  return refsActions
    .map((a: any) => typeof a === "number" ? a : a?.id)
    .filter((id: any): id is number => typeof id === "number");
}, [data?.refs?.links?.action]);

const { tasks } = useTransactionTasks({
  parent_model: "order",
  parentId: data?.id,
  actionIds,
  useActionIds: actionIds.length > 0,  // ← prevents fallback to parent_id query
  autoFetch: true,
});
```

---

## 4. Writing Back to `refs.links`

When adding a new related record (e.g., creating an action from an order),
update **both** the backend link and the local state:

```ts
// After creating a new action, update refs.links.action on the parent
const handleAutoSaveOrderActions = async (ids: number[]) => {
  await saveRecord("order", {
    id: orderId,
    refs: {
      mode: "merge",
      value: {
        links: {
          action: ids.map((id) => {
            // Preserve existing snapshot if available
            const existing = data.refs?.links?.action?.find(
              (a: any) => (typeof a === "number" ? a : a?.id) === id,
            );
            return existing ?? { id };
          }),
        },
      },
    },
  });
};
```

Key points:
- Use `mode: "merge"` on the `refs` field — never overwrite the whole object
- Preserve existing snapshot dicts; only add `{ id }` stubs for new entries
- The backend will hydrate stubs to full snapshots on next save via
  `RefsMixin.denormalize_links()`

---

## 5. Snapshot Shapes by Model

Snapshot fields are defined in `common/denorm_registry.py`. Key shapes:

| Model | Key Fields |
|-------|-----------|
| `customer` / `vendor` / `manufacturer` | `id, ida, display_name, email, phone, address_full, attention, status` |
| `contact` | `id, ida, display_name, company, title, role, email, phone, attention` |
| `action` | `id, ida, name` |
| `document` | `id, ida, name, type` |
| `project` | `id, ida, name, status` |
| `email` | `id, ida, email, name, type, is_primary` |
| `phone` | `id, ida, number, format, name` |
| `address` | `id, ida, address1, city, state, zip, country, full` |
| `item` | `id, ida, name, sku, description, kind, uom` |

> Contact snapshots on transactions may also carry `purpose` (e.g. `"billto"`,
> `"shipto"`) which is added by the linking logic, not the denorm registry.

---

## 6. Communication Records (Contact & Org Pages)

On Contact and Org detail pages, communication records (email, phone, address,
domain) are **always** displayed from `refs.links` — never queried separately.

```tsx
// Correct — from the parent record's refs.links
const emails = contact.refs?.links?.email ?? [];
const phones = contact.refs?.links?.phone ?? [];
const addresses = contact.refs?.links?.address ?? [];

// Wrong — separate query
const emails = await getRecords("email", { contact_id: contact.id }); // ❌
```

The CommLinkPanel and OrgLinkPanel components follow this pattern. Only when
the user clicks Edit on a specific comm record do we fetch the full record.

---

## 7. Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Tab shows **all** records instead of just related ones | Read IDs from `refs.links`, not from a blanket FK query |
| New record not appearing after create | Add the new ID to `refs.links` and save the parent |
| Snapshot data is stale after external edit | Run backend backfill or re-fetch the parent record |
| Overwriting entire `refs` object on save | Use `mode: "merge"` to patch only `refs.links` |
| Querying comm records separately on contact pages | Read from `refs.links.email`, `.phone`, `.address` |

---

## 8. Related Files

| File | Purpose |
|------|---------|
| `webClerk3/common/denorm_registry.py` | Field lists for each snapshot type |
| `webClerk3/common/models.py` → `RefsMixin` | Generic denormalization on save |
| `webClerk3/readmes/denorm-fields.md` | Backend denorm documentation |
| `src/apps/transactions/types/transactionTypes.ts` | TS types for denorm shapes |
| `src/apps/common/components/panels/` | CommLinkPanel, ContactPanel, etc. |
| `src/apps/transactions/components/TransactionDetailBase.tsx` | Base tab rendering |

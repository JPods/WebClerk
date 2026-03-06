# Display Related — Opening Related Records in Windows

## Overview

When a user clicks a link to open a related record (e.g. "View Item" from a transaction line, or "Open Contact" from an order panel), the record opens as a floating window inside the app shell — **not** in a new browser tab or popup.

This pattern is called **display_related** and is used consistently across panels, detail pages, and line modals throughout R25.

---

## Architecture

### Component Stack

```
User clicks "Open Item #42"
        │
        ▼
getModelDetailPath("item", 42)
        │  → "/products/item/detail/42"
        ▼
getModelWindowTitle("item", 42, "ABC-123")
        │  → "Item ABC-123"
        ▼
windowManager.ensureWindow(path, title, { maximized: false })
        │
        ▼
WindowManagerContext adds/activates window
        │
        ▼
PrivateRoute.AppLayout renders windows
        │
        ▼
resolveWindowElement(path) → <ItemDetail />
        │  (looks up protectedRoutesConfig)
        ▼
MacWindowChrome wraps the component
```

### Key Files

| File | Purpose |
|------|---------|
| [src/apps/common/components/panels/getModelDetailPath.ts](../src/apps/common/components/panels/getModelDetailPath.ts) | Maps `(model, id)` → route path, builds window titles |
| [src/context/WindowManagerContext.tsx](../src/context/WindowManagerContext.tsx) | Manages floating window state, provides `ensureWindow()` |
| [src/routes/protectedRoutesConfig.tsx](../src/routes/protectedRoutesConfig.tsx) | Route → element registry; `resolveWindowElement()` resolver |
| [src/routes/Routes.ts](../src/routes/Routes.ts) | `PageRoutes` class with all route path constants |
| [src/routes/Router.tsx](../src/routes/Router.tsx) | React Router `<Route>` declarations |
| [src/routes/PrivateRoute.tsx](../src/routes/PrivateRoute.tsx) | `AppLayout` renders windows via `MacWindowChrome` |

---

## How It Works

### 1. Path Resolution (`getModelDetailPath`)

`MODEL_DETAIL_BASES` maps model names to their route base paths:

```ts
const MODEL_DETAIL_BASES: Record<string, string> = {
  customer: "/org/customer/detail",
  order:    "/transactions/order/detail",
  item:     "/products/item/detail",
  contact:  "/core/contact/detail",
  // ... etc
};

getModelDetailPath("item", 42)  → "/products/item/detail/42"
```

### 2. Window Title (`getModelWindowTitle`)

Builds a human-readable title from the model name, ID, and optional display identifier:

```ts
getModelWindowTitle("item", 42, "ABC-123")  → "Item ABC-123"
getModelWindowTitle("order", 100)           → "Order #100"
```

### 3. WindowManager (`ensureWindow`)

`ensureWindow(path, title, options)` either:
- **Activates** an existing window if one already matches the path
- **Creates** a new floating window if none exists

```ts
const windowManager = useWindowManager();
windowManager.ensureWindow(path, title, { maximized: false });
```

### 4. Route Resolution (`resolveWindowElement`)

When `AppLayout` renders a window, it calls `resolveWindowElement(path)` which matches the path against the `protectedRoutesConfig` array and returns the corresponding React element. If no match is found, it renders `<NotFoundPage />`.

---

## Implementation Pattern

### Minimal Example — Panel Row Click

```tsx
import { getModelDetailPath, getModelWindowTitle } from '@/apps/common/components/panels/getModelDetailPath';
import { useWindowManager } from '@/context/WindowManagerContext';

const MyPanel = () => {
  const windowManager = useWindowManager();

  const handleOpenItem = (itemId: number, ida?: string) => {
    const path = getModelDetailPath("item", itemId);
    const title = getModelWindowTitle("item", itemId, ida);
    windowManager.ensureWindow(path, title, { maximized: false });
  };

  return (
    <button onClick={() => handleOpenItem(42, "WIDGET-A")}>
      Open Item
    </button>
  );
};
```

### Full Example — Transaction Line "View Item" Button

From `LinesCard.tsx`, where each table row has an "Open item" icon:

```tsx
const handleOpenItem = (itemId: number, ida?: string) => {
  const path = getModelDetailPath("item", itemId);
  const title = getModelWindowTitle("item", itemId, ida);
  windowManager.ensureWindow(path, title, { maximized: false });
};

// In the table row:
<button onClick={() => handleOpenItem(openId, itemCode)}>
  <FaExternalLinkAlt size={12} />
</button>
```

### Passing Through Drawers/Modals

When a modal (like `LineDetailsModal`) needs to open a related record, it receives an `onOpenItem` callback from its parent. The parent (e.g. `LinesCard`) provides the callback that calls `ensureWindow`:

```tsx
// Parent (LinesCard):
<LineDetailsModal
  onOpenItem={(id) => handleOpenItem(id as number)}
/>

// Child (LineDetailsModal):
<button onClick={() => onOpenItem(itemId)}>
  Open Item
</button>
```

---

## Existing Implementations

Components that already use this pattern:

| Component | Opens | File |
|-----------|-------|------|
| `ItemsPanel` | Item, Serial | `src/apps/common/components/panels/ItemsPanel.tsx` |
| `SerialPanel` | Serial | `src/apps/common/components/panels/SerialPanel.tsx` |
| `TransactionsPanel` | Order, Invoice, etc. | `src/apps/common/components/panels/TransactionsPanel.tsx` |
| `ContactPanel` | Contact | `src/apps/common/components/panels/ContactPanel.tsx` |
| `LinesCard` | Item | `src/apps/transactions/components/LinesCard.tsx` |
| `CustomerSalesPanel` | Transactions | `src/apps/transactions/components/CustomerSalesPanel.tsx` |
| `VendorDetail` | Contact, Vendor | `src/apps/orgs/models/vendor/pages/VendorDetail.tsx` |
| `CustomerDetail` | Contact, Customer | `src/apps/orgs/models/customer/pages/CustomerDetail.tsx` |
| `TransactionDetailBase` | Transfer targets | `src/apps/transactions/components/TransactionDetailBase.tsx` |

---

## Adding a New Model to display_related

### Checklist

1. **`Routes.ts`** — Add the route constant:
   ```ts
   static readonly productsItemDetail: string = "/products/item/detail/:id";
   ```

2. **`Router.tsx`** — Add the `<Route>`:
   ```tsx
   <Route path={PageRoutes.productsItemDetail} element={<ItemDetail />} />
   ```

3. **`protectedRoutesConfig.tsx`** — Add to the config array (required for WindowManager):
   ```tsx
   { path: PageRoutes.productsItemDetail, element: <ItemDetail /> },
   ```

4. **`getModelDetailPath.ts`** — Add to `MODEL_DETAIL_BASES`:
   ```ts
   item: "/products/item/detail",
   ```

5. **Component** — Use `useWindowManager()` + `ensureWindow()`.

### Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Using `window.open(path)` | Opens new browser window with full app shell + sidebar | Use `windowManager.ensureWindow()` |
| Missing from `protectedRoutesConfig` | Window opens but shows 404 page | Add entry to `protectedRoutesConfig` |
| `getModelDetailPath` uses stale route | Path doesn't match any route | Sync with `Routes.ts` |
| Passing item code instead of ID | Route param can't be parsed as number | Always pass numeric `item_id` |

---

## WcapiRouteHandler (Alternate Entry Point)

The route `/wcapi/get/?model_name=item&id=42` is handled by `WcapiRouteHandler.tsx`, which reads query params and renders the appropriate detail component. This serves as a universal URL scheme for opening any model:

```ts
// WcapiRouteHandler MODEL_DETAIL_MAP
const MODEL_DETAIL_MAP = {
  purchase: PurchaseDetail,
  order: OrderDetail,
  invoice: InvoiceDetail,
  proposal: ProposalDetail,
  item: ItemDetail,
  customer: CustomerDetailPage,
  vendor: VendorDetail,
  contact: ContactDetail,
};
```

This is mainly used for deep-linking and programmatic navigation. The WindowManager approach via `getModelDetailPath` is preferred for UI interactions.

---

## Window Sizing

### Presets

`getModelDetailPath.ts` exports a `WINDOW_PRESETS` constant with four named presets:

| Preset | Dimensions | Use Case |
|--------|-----------|----------|
| `DETAIL` | 980 × 640, floating | Single record view/edit (item, order, customer, contact) |
| `LIST` | 1200 × 720, floating | Collection / table view (wider for columns) |
| `COMPACT` | 720 × 500, floating | Small reference lookups (serial, phone, email, address) |
| `FULL` | maximized | Dashboard-style views |

```ts
import { WINDOW_PRESETS } from '@/apps/common/components/panels/getModelDetailPath';

windowManager.ensureWindow(path, title, WINDOW_PRESETS.DETAIL);
windowManager.ensureWindow(path, title, WINDOW_PRESETS.COMPACT);
```

### Per-Model Defaults

`MODEL_WINDOW_PRESET` maps each model to its default preset. Use `getModelWindowPreset(model)` to retrieve it:

```ts
import { getModelWindowPreset } from '@/apps/common/components/panels/getModelDetailPath';

const opts = getModelWindowPreset("item");   // → DETAIL (980 × 640)
const opts2 = getModelWindowPreset("phone"); // → COMPACT (720 × 500)

windowManager.ensureWindow(path, title, opts);
```

### All-in-One Helper

`getModelWindowArgs(model, id, ida?, name?, overrides?)` returns `{ path, title, options }` ready for `ensureWindow()`:

```ts
import { getModelWindowArgs } from '@/apps/common/components/panels/getModelDetailPath';

const win = getModelWindowArgs("item", 42, "ABC-123");
windowManager.ensureWindow(win.path, win.title, win.options);
```

### Overriding at the Callsite

Pass `optionOverrides` to `getModelWindowArgs`, or spread presets with custom values:

```ts
// Via getModelWindowArgs
const win = getModelWindowArgs("order", 100, "ORD-100", null, { width: 1100 });

// Via direct spread
windowManager.ensureWindow(path, title, { ...WINDOW_PRESETS.DETAIL, width: 1100 });
```

### Constraints

| Property | Value | Source |
|----------|-------|--------|
| Min width | 520px | `MacWindowChrome.tsx` |
| Min height | 360px | `MacWindowChrome.tsx` |
| Default new window | maximized | `WindowManagerContext.tsx` |
| Stagger offset | 28px × windowCount | `WindowManagerContext.tsx` |

Windows are user-resizable via drag handles in `MacWindowChrome`.

### Adding a New Preset

1. Add the preset to `WINDOW_PRESETS` in `getModelDetailPath.ts`
2. Assign it to models in `MODEL_WINDOW_PRESET`
3. Document the preset in this readme and copilot instructions §17

---

## Multi-Window & Multi-Monitor Support

**Multiple windows is central to the enterprise UX.** Power users with multiple monitors routinely open several records side-by-side — e.g. comparing an order and its invoice, or viewing an item while editing a purchase order.

### How It Works

- `ensureWindow()` checks if a window for the given path already exists:
  - **Exists** → activates and brings it to front
  - **New** → creates a floating window, staggered 28px from the last
- Users can drag windows freely, resize them, minimize, or maximize
- Each window is independent — closing one does not affect others
- Window state is held in `WindowManagerContext` (not persisted across reloads)

### Design Principles

1. **Open, don't navigate** — Clicking "View Item" should open a new window, never replace the current view
2. **No duplicates** — `ensureWindow` de-dupes by path; clicking the same link twice activates the existing window
3. **Consistent sizing** — Use presets from `WINDOW_PRESETS` so windows of the same type always start at the same size
4. **Let users arrange** — Windows are freely draggable and resizable; don't force layouts

### Multi-Monitor Tips

- Enterprise users typically tile windows across screens: transactions on one monitor, products/items on another
- Large monitors benefit from `LIST` preset for wider table views
- The app shell (sidebar + router content) stays in the main browser window; floating windows render inside the same viewport
- Future enhancement: persist window positions per user/workflow

---

## Future Considerations

- **Bulk open** — Select multiple lines → open all items in windows
- **Breadcrumb trail** — Track parent→child window relationships for back-navigation
- **Window layout persistence** — Save/restore window arrangements per workflow
- **Cross-model links** — Generic "open related" button that reads `refs.links` to discover linkable records
- **External monitors** — Explore `window.open()` with `WindowProxy` for true multi-monitor window detachment

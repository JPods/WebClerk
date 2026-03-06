# Copilot Instructions — React2025 (r25)

These instructions govern AI-assisted development in the **React2025** frontend.
Read them fully before generating or modifying any code.

---

## 1. Project Identity

| Key | Value |
|-----|-------|
| Alias | **r25** |
| Stack | React 19 · TypeScript · Vite · pnpm |
| Backend | WebClerk3 (**wc3**) — Django 5 on `localhost:8000` |
| Legacy | 4D Sources (**wc2**) + Vue 2020 — migration targets, not active dev |
| Ports | r25 → `localhost:5173`, wc3 → `localhost:8000` |

---

## 2. Architecture at a Glance

### Domain-Driven Folder Structure

```
src/
├── api/               # Axios client, wcapi SDK, model name resolver, auth
├── apps/              # Domain modules (mirrors wc3 app structure)
│   ├── accounts/      # GL, ledgers, currencies, tax, terms, audits
│   ├── communications/# email, phone, address, domain
│   ├── core/          # contact, action, setting, template, notification, report
│   ├── docs/          # document, linkage, tag, question_answer
│   ├── orgs/          # customer, vendor, manufacturer, employee, rep, organization
│   ├── products/      # item, catalog, inventory, warehouse, BOM, delivery
│   ├── support/       # shared support utilities
│   ├── sync/          # connections, bundles, external integrations
│   └── transactions/  # proposal, order, invoice, purchase, requisition, workorder + lines
├── components/        # Shared / reusable UI components
├── constants/         # App-wide constants
├── context/           # React context providers
├── generated/         # Auto-generated types (do not edit manually)
├── hooks/             # Shared custom hooks
├── icons/             # Icon components
├── layout/            # App shell, navigation, sidebar
├── lib/               # Utility libraries
├── model/             # Shared TypeScript model interfaces
├── pages/             # Top-level route pages
├── routes/            # React Router configuration
├── shared/            # Cross-cutting shared code
├── store/             # Redux Toolkit store & slices
├── test/              # Test setup and helpers
├── tools/             # Dev tools (DevTools badge, dataset switching)
├── type/              # Shared TypeScript type definitions
├── utils/             # General utility functions
└── validations/       # Shared Zod schemas
```

### Per-Model File Organization

Each model lives under `src/apps/{app}/models/{model}/` with sub-folders:

```
src/apps/transactions/models/order/
├── pages/
│   ├── OrderDetailPage.tsx    # Edit/create form
│   ├── OrderListPage.tsx      # Data table list
│   └── OrderDisplayPage.tsx   # Read-only view (optional)
├── services/
│   └── orderApi.ts            # WCAPI SDK calls for this model
├── types/
│   └── Order.ts               # TypeScript interface
└── utils/
    └── orderHelpers.ts        # Model-specific helpers
```

### Key Libraries

| Purpose | Library |
|---------|---------|
| Forms | `react-hook-form` + `@hookform/resolvers` |
| Validation | `zod` |
| Global state | `@reduxjs/toolkit` |
| Server state | `@tanstack/react-query` |
| HTTP | `axios` (via `src/api/axios.ts`) |
| Data tables | `react-data-table-component` |
| Icons | `lucide-react` |
| CSS | Tailwind utility classes via `clsx` |
| Testing | `vitest` + `jsdom` |

---

## 3. Unified API Gateway (wcapi)

All data operations route through wc3's **centralized wcapi endpoints** — never create per-model REST routes.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/wcapi/get/` | GET | Fetch records (list or single) |
| `/wcapi/save/` | POST | Create or update records |
| `/wcapi/delete/` | GET/POST | Soft-delete records |
| `/wcapi/query/` | POST | Complex queries with filters |
| `/wcapi/manage/` | POST | Administrative operations |

### SDK Functions (`src/api/wcapi.ts`)

All API files **must** import from `@/api/wcapi`:

```typescript
import { getRecords, getRecord, saveRecord, deleteRecord } from '@/api/wcapi';
```

| SDK Function | Endpoint | Usage |
|-------------|----------|-------|
| `getRecords(model_name, params?)` | `/wcapi/get/` | List with pagination/filters |
| `getRecord(model_name, id)` | `/wcapi/get/` | Single record by ID |
| `saveRecord(model_name, data)` | `/wcapi/save/` | Create (no `id`) or update (with `id`) |
| `deleteRecord(model_name, id)` | `/wcapi/delete/` | Soft-delete |
| `getModelNames()` | `/wcapi/model_name/list/` | Registry introspection |
| `getModelDetail(model_name)` | `/wcapi/model_name/detail/` | Field metadata |

### Model Name Resolution

`resolveModelName()` in `src/api/modelNameResolver.ts` translates aliases to canonical names:

| Alias | Canonical |
|-------|-----------|
| `po` | `purchase` |
| `quote` | `proposal` |
| `wo` | `workorder` |
| `bom` | `bill_of_material` |
| `product` | `item` |

RESTful path patterns (e.g. `transactions/order`) also resolve automatically.

### Service File Template

New API service files follow this pattern:

```typescript
import { getRecords, getRecord, saveRecord, deleteRecord } from '@/api/wcapi';

const MODEL = 'model_name';  // singular snake_case

export const fetchModelNames = (params?: { limit?: number; offset?: number; search?: string }) =>
  getRecords(MODEL, params);

export const fetchModelName = (id: number) =>
  getRecord(MODEL, id);

export const createModelName = (data: CreateModelNameRequest) =>
  saveRecord(MODEL, data);

export const updateModelName = (id: number, data: UpdateModelNameRequest) =>
  saveRecord(MODEL, { id, ...data });

export const deleteModelName = (id: number) =>
  deleteRecord(MODEL, id);
```

---

## 4. API Response Envelope (MANDATORY)

Every wc3 JSON response uses this envelope. Frontend code **must** expect it.

```typescript
interface ApiEnvelope<T = any> {
  status: 'success' | 'fail' | 'error';
  message: string;
  data: T | null;
  error?: { code: string; details?: any } | null;
  meta?: { total: number; page_size: number; next?: string; previous?: string | null };
}
```

Key rules:
- HTTP 2xx → `status: "success"`, payload in `data`
- HTTP 4xx → `status: "fail"` (client/validation errors)
- HTTP 5xx → `status: "error"`
- Version conflicts → HTTP 412, `error.code: "version_conflict"`
- Related/nested data → always under `data.related` (plural keys)

---

## 5. Naming Conventions (STRICT)

### Model Names

| Context | Convention | Example |
|---------|-----------|---------|
| API `model_name` param | **singular** snake_case | `invoice`, `order_line` |
| Collections / related data keys | **plural** snake_case | `invoices`, `order_lines` |
| TypeScript interface | PascalCase singular | `Invoice`, `OrderLine` |
| React component | PascalCase | `OrderDetailPage`, `InvoiceListPage` |
| Component file | PascalCase `.tsx` | `OrderDetailPage.tsx` |
| Service file | camelCase `.ts` | `orderApi.ts` |
| API function | camelCase | `getRecords`, `saveRecord` |
| Zod schema file | camelCase `.ts` | `orderSchema.ts` |
| CSS classes | Tailwind utilities | `className="flex items-center gap-2"` |

### Canonical Renames (ENFORCED)

Legacy names are **banned** in all new code:

| Banned Legacy Name | Canonical Name |
|-------------------|---------------|
| `sales_order` / `SalesOrder` | `order` / `Order` |
| `sales_order_line` / `SalesOrderLine` | `order_line` / `OrderLine` |
| `purchase_order` / `PurchaseOrder` | `purchase` / `Purchase` |
| `purchase_order_line` / `PurchaseOrderLine` | `purchase_line` / `PurchaseLine` |
| `location` (as model name) | `address` / `Address` |

### Deprecated Field Names

| Deprecated | Canonical |
|-----------|-----------|
| `dt_end` | `dt_completed` |
| `dt_updated` | `dt_modified` |
| `duration` | removed — compute from dates |

### General Casing

- Variables / functions: `camelCase`
- Components / types / interfaces: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Date/time fields from backend: `dt_` prefix (e.g. `dt_created`, `dt_modified`)
- FK fields from backend: `{model_name}_id` format

---

## 6. Authentication & HTTP Client

### Token Flow

- **Access tokens: memory-only** — never stored in localStorage (XSS protection)
- **Refresh tokens: httpOnly cookies** — set by wc3 server
- On page reload, `bootstrapAuth()` acquires a fresh token from `/wcapi/token_refresh/`
- 401 responses trigger automatic token refresh with request queuing

### Axios Clients (`src/api/axios.ts`)

| Client | Purpose | Auth |
|--------|---------|------|
| `apiClient` | All protected API calls | Bearer token auto-injected |
| `authClient` | Token refresh only | `withCredentials: true` (cookies) |
| `notionClient` | Notion integration | Separate auth |

### Caching Rules

**`WCAPI = Database = NEVER HTTP-CACHED`**

- All `/wcapi/*` calls pass `{ cache: false }` — the axios wrapper enforces this
- Non-wcapi calls use session cache (`sessionStorage`, key prefix `wc_cache_v2:`)
- If you need to cache wcapi data, store it in JavaScript state (Redux, React Query, context)
- Cache is cleared on logout via `clearTokens()` → `clearResponseCache()`

---

## 7. Environment Variables

All frontend env vars use `VITE_` prefix (Vite requirement).

| Variable | Example | Notes |
|----------|---------|-------|
| `VITE_API_URL` | `http://localhost:8000` | **Must NOT include `/wcapi`** — SDK appends it |
| `VITE_DATA_SET_ID` | `DEV` | Environment identifier |
| `VITE_DATA_SET_NAME` | `Development Server` | Display name |
| `VITE_NOTION_TOKEN` | (secret) | Notion API key |
| `VITE_NOTION_DATABASE_ID` | (uuid) | Notion DB for notes |

### Database Switching

Use the DevTools badge (bottom-left) or CLI:

```bash
cd webClerk3/tools
./switch-dataset.sh remote   # Team collaboration (green badge)
./switch-dataset.sh local    # Local debugging (blue badge)
```

---

## 8. Detail Page Pattern

### Default Mode: Always Edit

**All detail pages open in edit mode by default.** There is no separate "display" vs "edit" experience — the form is always editable when a record loads. If a page must be read-only (e.g., audit logs, locked records), enforce that explicitly on a case-by-case basis; do **not** default to view mode.

Implementation by pattern:
- **Contact-style** (`initialUiMode`): return `"edit"` for existing records, not `"view"`
- **TransactionDetailBase**: `effectiveMode` returns `"edit"` (not `null`) for existing records
- **OrgDetail**: `editing` starts `true` when an `id` is present
- **Simple-style**: already default to `"add"` (editable) — no change needed

### Standard Layout

```
SimpleDetailHeader → SimpleDetailToolbar → Basic Info Panel → DetailTabs → Tab Content
```

### Key Components

| Component | Purpose |
|-----------|---------|
| `SimpleDetailHeader` | Entity name, ID, mode (Add/Edit/View), back nav |
| `SimpleDetailToolbar` | Edit/Save/Cancel/Delete with loading states |
| `HorizontalField` | Label-left field layout (responsive) |
| `useColumnCount` | 2/3 column selector with localStorage persistence |
| `DetailTabs` | Tab navigation with badges, admin-only tabs |

### Standard Tabs

Every detail page includes: **Overview**, **Comments**, **Actions**, **Documents**, **History** (admin), **Raw** (admin).

Model-specific tabs: Communications, Contacts, Financials, Lines, Q&A, Linkages.

### Page Patterns by Complexity

| Pattern | Used By |
|---------|---------|
| `TransactionDetailBase` | Order, Invoice, Proposal, Purchase, Receipt, Workorder |
| `DetailTabs` (standalone) | Project, Requisition |
| Accordion + Panels | ItemDetail |
| `SimpleDetailHeader` + Toolbar | 40+ simple entity forms |

---

## 9. Forms & Validation

### react-hook-form + Zod

All forms use `react-hook-form` with Zod schemas for validation:

```typescript
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { orderSchema, type OrderFormData } from './orderSchema';

const form = useForm<OrderFormData>({
  resolver: zodResolver(orderSchema),
  defaultValues: { ... },
});
```

### Zod Schema Conventions

- Schema files: `{model}Schema.ts` in the model's `types/` or `validations/` folder
- Export both the schema and the inferred type: `z.infer<typeof schema>`
- Validate at form boundaries, not deep in business logic

---

## 10. State Management

### Redux Toolkit — Global / Cross-Cutting State

- Store in `src/store/`
- Slices for auth, UI preferences, global notifications
- Use `createSlice` and `createAsyncThunk` patterns
- Access via typed `useAppSelector` / `useAppDispatch` hooks

### React Query — Server State

- Use `@tanstack/react-query` for data fetching, caching, and cache invalidation
- Wrap wcapi SDK calls in query functions
- Stale times tuned per data type (static lookups longer, transactional data shorter)

### When to Use Which

| Data Type | Tool |
|-----------|------|
| Auth state, UI prefs, sidebar state | Redux Toolkit |
| Server data (records, lists) | React Query |
| Form state | react-hook-form |
| Component-local state | `useState` / `useReducer` |

---

## 11. Transaction System (Frontend)

### Document Types

| Type | Direction | Lines Model | Flow |
|------|-----------|------------|------|
| Proposal | Sell | `ProposalLine` | proposal → order |
| Order | Sell | `OrderLine` | order → invoice |
| Invoice | Sell | `InvoiceLine` | terminal |
| Purchase | Buy | `PurchaseLine` | purchase → receipt |
| Work Order | Exec | `WorkOrderLine` | standalone |
| Requisition | Internal | `RequisitionLine` | requisition → purchase |

### Calculation Rules

- **Backend is authoritative** for all saved totals
- Frontend shows **optimistic estimates** for real-time UX; syncs on save
- Rounding: `Math.round(value * 10^decimals) / 10^decimals` (2-decimal for currency)
- Sales documents: `price` fields are primary
- Purchase documents: `cost` fields are primary

### Dirty Tracking on Save

Lines carry a `_dirty` flag:
- `_dirty: true` + no `id` → **create** new line
- `_dirty: true` + `id` → **update** existing line
- `_dirty: false` → **skip** (not sent to backend)

### Item ID Immutability

`item_id` cannot change on existing lines. UI must prevent it; backend validates as backstop.

### Line Identity — `line_number` System

**Stable keys for React state handlers.** Every line carries a scalar `line_number` (auto-assigned by the backend in increments of 10). R25 uses two helpers from `@/apps/transactions/utils/lineHelpers.ts`:

| Helper | Returns | Purpose |
|--------|---------|--------|
| `lineKey(line, idx)` | `line.line_number ?? line.id ?? idx` | Stable identity for delete / update / duplicate handlers |
| `getNextLineNumber(lines)` | `max(line_numbers) + 10` | Assign `line_number` to client-side new/duplicated lines |

**Rules:**
- All `handleDeleteLine`, `handleLineChange`, `handleDuplicateLine`, and `handleAddItem` handlers **must** use `lineKey(l, i)` for identity.
- Never use bare `line.id ?? idx` — it breaks for unsaved lines whose `id` is `undefined`.
- New lines added client-side get `line_number: getNextLineNumber(lines)` immediately.
- Transfer pre-population assigns sequential `line_number` values (10, 20, 30…).
- The backend persists `line_number` and returns it in the save response.

### Two Save Endpoints

| Action | Endpoint | SDK Function | When |
|--------|----------|-------------|------|
| Save transaction + lines | `POST /wcapi/transaction/save/` | `saveTransactionWithLines(modelName, payload)` | Creating/editing any transaction with lines |
| Deactivate source doc | `POST /wcapi/save/` | `saveRecord(modelName, { id, is_active: false })` | After transfer (e.g. deactivate order after creating invoice) |

### Transfer Flow (Order → Invoice)

1. R25 builds invoice header from order data, sets `parent_id` and `parent_model: "order"`
2. R25 stamps each invoice line with `refs.source.order_line_id` pointing to the source order line
3. R25 calls `saveTransactionWithLines("invoice", payload)` → `POST /wcapi/transaction/save/`
4. **Backend creates exactly one Pending per line** — captures `on_in`, `on_so` release, and `on_hand` deduction in a single record
5. R25 calls `saveRecord("order", { id, is_active: false })` → `POST /wcapi/save/` to deactivate the order (no lines, no pending)

> **Backend is authoritative for pending creation.** R25 provides `refs.source` for traceability, but the backend derives pending type, transfer status, and quantity buckets from its own data. Do not send pending-related fields from the frontend.

---

## 12. JSONB Fields & refs.links

Backend models carry JSONB columns: `metadata`, `refs`, `prefs`, `comments`.

### `refs.links` — Related Record Source of Truth

`refs.links` stores **denormalized snapshots** of related entities as arrays (or a single dict for 1:1 org roles). This is the **authoritative source** for which records belong to a parent.

```jsonc
{
  "refs": {
    "links": {
      "customer": { "id": 42, "company": "Acme Corp", ... },       // 1:1 dict
      "contact":  [{ "id": 6, "display_name": "Jane", ... }, ...], // 1:N array
      "action":   [{ "id": 101, "ida": "101", "name": "Follow up" }, ...],
      "document": [{ "id": 55, "name": "PO.pdf" }, ...],
      "email":    [{ "id": 12, "email": "billing@acme.com" }, ...]
    }
  }
}
```

### Golden Rule: Tabs Read from `refs.links`, Not Separate Queries

| Correct | Wrong |
|---------|-------|
| `data.refs?.links?.contact` | `getRecords("contact", { parent_id })` |
| `data.refs?.links?.action`  | `getRecords("action", { parent_model, parent_id })` |
| `data.refs?.links?.email`   | `getRecords("email", { contact_id })` |

Blanket FK queries return **all** records matching the FK — not just those scoped to this parent. `refs.links` is curated and correct.

### Tab Data Binding

```ts
// Extract IDs from refs.links, then fetch full records by those IDs
const actionIds = (data.refs?.links?.action ?? [])
  .map((a: any) => typeof a === "number" ? a : a?.id)
  .filter((id: any): id is number => typeof id === "number");
```

### Writing Back

When adding a related record, update `refs.links` on the parent:

```ts
await saveRecord("order", {
  id: orderId,
  refs: { mode: "merge", value: { links: { action: updatedSnapshots } } },
});
```

- **Always** use `mode: "merge"` — never overwrite the entire `refs` object
- Preserve existing snapshot dicts; add `{ id }` stubs for new entries
- Backend hydrates stubs to full snapshots on next save

### Communication Records

On Contact/Org pages, emails, phones, addresses, domains come from `refs.links` — **never query communication models separately**. Only fetch a full record when the user clicks Edit.

> **Deep dive:** `readmes/topics/refs-links.md` · Backend: `webClerk3/readmes/denorm-fields.md`

---

## 13. Testing Requirements

### Running Tests

```bash
pnpm test              # Run vitest (watch mode)
pnpm test -- --run     # Single run
pnpm test -- --run --coverage  # With coverage
```

### Configuration

- Framework: **Vitest** with `jsdom` environment
- Setup file: `src/test/setup.ts`
- `globals: true` — no need to import `describe`, `it`, `expect`

### Conventions

- Place test files adjacent to source: `Component.test.tsx` or under `__tests__/`
- Use React Testing Library for component tests
- Mock wcapi SDK calls, not axios directly
- Assert that components handle the API envelope correctly
- Always add/adjust tests alongside code changes

---

## 14. Code Generation Rules

### Do

- Import all data operations from `@/api/wcapi` — never call axios directly for CRUD
- Use `model_name` (singular snake_case) in all API calls
- Use `resolveModelName()` for any user-facing or URL-sourced model name
- Follow the per-model folder structure: `apps/{app}/models/{model}/{pages,services,types,utils}/`
- Use `react-hook-form` + `zod` for all forms
- Use Tailwind utilities via `clsx` for styling — no inline style objects
- Use `lucide-react` for icons
- Type all props and state — no `any` except when wrapping untyped third-party code
- Use path aliases (`@/api/...`, `@/components/...`) — never relative `../../..` beyond two levels
- Handle loading, error, and empty states in every data-fetching component
- Use `refs.links` as the source of truth for related records on detail page tabs — never query by FK alone
- Paginate all list endpoints with `limit`/`offset`
- Include version in save payloads (optimistic concurrency)

### Don't

- Don't duplicate the `/wcapi` prefix — `VITE_API_URL` must NOT include it
- Don't use legacy model names (`sales_order`, `purchase_order`, `location` as model)
- Don't HTTP-cache wcapi calls — they are live database operations
- Don't store access tokens in localStorage or sessionStorage
- Don't bypass the `ApiEnvelope` type — always unwrap `res.data.data`
- Don't query communication models separately on Contact/Org pages — use `refs.links`
- Don't populate detail page tabs (Actions, Contacts, Documents) via blanket FK queries — read IDs from `refs.links` first
- Don't create per-model REST endpoints — all CRUD goes through wcapi
- Don't use `class` components — functional components with hooks only
- Don't use deprecated field names (`dt_end`, `dt_updated`, `duration`)
- Don't hard-code field lists for denormalized data — they come from the backend
- Don't create sandbox experiments without a dated cleanup note

---

## 15. Development-Mode UI Rules

During active development, every layout that displays or edits a record **must show the record's primary key (ID)** so developers can immediately tell whether a record has been persisted.

### Requirements

| Where | What to show | When no ID exists |
|-------|-------------|-------------------|
| **Detail page header** | `#{id}` next to the entity name | Show `(no ID — unsaved)` in amber |
| **Panel headers** (CommLinkPanel, OrgLinkPanel, etc.) | `c#{contactId}` (or the owning entity ID) | Omit the badge |
| **CommLinkPanel header** | Additionally show `→ {type}_id:{primaryId}` when a primary FK is set | — |
| **Email gate / pre-save screens** | `(no ID yet)` after the title | — |

### Implementation Pattern

```tsx
{/* DEV: record ID badge */}
{activeContactId ? (
  <span className="ml-2 text-sm font-normal text-slate-500">#{activeContactId}</span>
) : (
  <span className="ml-2 text-xs font-mono text-amber-500">(no ID — unsaved)</span>
)}
```

For panel headers use a smaller mono badge:

```tsx
{contactId && (
  <span className="text-[10px] font-mono text-slate-400 bg-slate-100 dark:bg-slate-700 px-1.5 py-0.5 rounded">
    c#{contactId}
  </span>
)}
```

### Cleanup

All dev-mode ID badges are marked with a `/* DEV: */` comment. When the project moves to production, search for `DEV:` and remove or gate behind `import.meta.env.DEV`.

---

## 16. Key File Locations

| Purpose | Path |
|---------|------|
| Axios client & interceptors | `src/api/axios.ts` |
| WCAPI SDK | `src/api/wcapi.ts` |
| Model name resolver | `src/api/modelNameResolver.ts` |
| REST→WCAPI migration map | `src/api/restToWcapi.ts` |
| Auth hook | `src/hooks/useAuth.ts` |
| Redux store | `src/store/` |
| Route definitions | `src/routes/` |
| Shared components | `src/components/` |
| App shell / layout | `src/layout/` |
| Line identity helpers | `src/apps/transactions/utils/lineHelpers.ts` |
| Transaction types | `src/apps/transactions/types/transactionTypes.ts` |
| Test setup | `src/test/setup.ts` |
| Vitest config | `vitest.config.ts` |
| Vite config | `vite.config.ts` |
| TypeScript config | `tsconfig.app.json` |
| Readmes | `readmes/` (numbered 00–03 for onboarding, topics/ for deep-dives) |
| refs.links frontend guide | `readmes/topics/refs-links.md` |

---

## 17. Documentation Practice

- **Readmes are essential** — update `readmes/` when architecture decisions change
- Files `00-` through `03-` are the core onboarding sequence
- Topic deep-dives go in `readmes/topics/{category}/`
- Migration tracking in `readmes/api-migration-rest-to-wcapi.md`
- Legacy reference: `vue2020/src/components/` for feature parity checks

---

## 18. Instruction File Sync (MANDATORY)

Copilot instructions exist in **two locations** in both repos:

| File | Role |
|------|------|
| `git_bypass/copilot.instructions.md` | **Source of truth** — committed to git, shared with the team |
| `.github/instructions/copilot.instructions.md` | **Active copy** — read by VS Code / Copilot |

In R25, both are committed (`.github/` is NOT gitignored here).  
In wc3, `.github/` is gitignored, so only `git_bypass/` is committed.

### Rules

1. **Always edit `git_bypass/copilot.instructions.md` first** — it's the canonical version.
2. **Immediately copy to the active location:**
   ```bash
   cp git_bypass/copilot.instructions.md .github/instructions/copilot.instructions.md
   ```
3. **Both repos must stay aligned** — when instructions change, update both:
   - `webClerk3/git_bypass/copilot.instructions.md`
   - `React2025/git_bypass/copilot.instructions.md`
   - Then copy each to its `.github/instructions/` counterpart.
4. **wc3 has a Django startup check** (`common/checks.py`) that warns if the files are out of sync.

---

## 19. AI Inventory Observer (Backend Integration)

The wc3 backend includes an **LLM-powered inventory observational learning system**. While the implementation lives in wc3, the frontend may eventually expose query interfaces.

### Backend Capabilities

| Feature | Backend Endpoint (Future) | Purpose |
|---------|--------------------------|---------|
| Event stream | `/api/inventory-events/` | Real-time event feed |
| Item narrative | `/api/item/{id}/narrative/` | LLM-generated item history |
| Pattern insights | `/api/inventory/patterns/` | Trend analysis dashboard |
| Q&A interface | `/api/inventory/ask/` | Natural language queries |

### Event Types

All transaction line operations automatically emit `InventoryEvent` records in wc3:
- `{type}_line_add`, `{type}_line_update`, `{type}_line_delete`, `{type}_line_item_change`
- Alerts: `below_reorder`, `below_safety`, `overstock`

### AGT Patent Alignment

The inventory observer architecture supports future integration with **U.S. Patent Application 19/356,062** (*3-Tiered Cargo Shipments*):
- Sensor data capture via `InventoryEvent.payload`
- LLM-defined scheduling windows via pattern detection
- Chain-of-custody audit trail via immutable event log

### Frontend Considerations (Future)

When building inventory observer UI:
- Use `react-query` for event stream subscription
- Display LLM summaries in activity feeds
- Pattern insights → dashboard charts
- Q&A → chat-style interface component

### Documentation

- wc3 implementation: `webClerk3/readmes/llm-inventory-observer.md`
- Patent reference: `webClerk3/readmes/topics/ai/patent.md`

---

## 20. Coding Journal (Backend)

The wc3 backend captures **coding sessions** for LLM learning from our development efforts.

### CLI Commands (in wc3)

```bash
# Log a session after completing work
python manage.py log_session --type feature \
  --problem "What I worked on" \
  --solution "How I solved it" \
  --apps transactions orgs \
  --tags "tag1,tag2"

# Ask about coding history
python manage.py journal ask "How did we handle X?"

# Find similar sessions
python manage.py journal find "signal totals"

# View recent sessions
python manage.py journal recent
```

### When to Log

Log a session after significant work:
- Implementing a new feature
- Fixing a non-trivial bug
- Learning something important about the codebase
- Refactoring that required deep understanding

This builds institutional knowledge that helps the LLM assist with similar problems later.

---

## 21. Git Observer (Backend)

The wc3 backend includes a **Git Observer** that watches commits for schema drift and outdated code. This catches when team members push code using deprecated field names or banned patterns.

### CLI Commands (in wc3)

```bash
# Scan recent commits for drift issues
python manage.py analyze_commits

# Analyze a specific commit
python manage.py analyze_commits --commit abc123

# Check staged files before commit
python manage.py analyze_commits --check-staged

# Show only commits with drift issues
python manage.py analyze_commits --drift-only
```

### What It Catches

| Issue | Example |
|-------|---------|
| Deprecated fields | `quantity.placed` (should be `quantity.staged`) |
| Banned patterns | `print()` instead of logging |
| Stale imports | Importing from moved modules |

### Frontend Impact

When the backend detects drift, coordinate with the team to:
1. Update TypeScript types if field names changed
2. Update API calls if shapes changed
3. Run `pnpm generate:types` to regenerate types

---

## 22. Session Context

When starting a coding session, establish:

1. **Which app/model?** (e.g., `transactions/order`, `products/item`)
2. **What task?** (new feature, bug fix, refactor, test)
3. **Which layer?** (page component, service, type, schema, test)

This helps scope changes correctly within the domain-driven folder structure.

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

- **`refs.links`** stores cross-model relationships: `{ "contact": [{ id: 6, name: "billing", ... }] }`
- Contact/Org pages show emails, addresses, phones from `refs.links` — **never query communication models separately**
- Denormalized snapshots are hydrated on save by the backend
- **Never overwrite entire JSONB** — always merge at the key level

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
- Use `refs.links` for cross-model relationships on detail pages
- Paginate all list endpoints with `limit`/`offset`
- Include version in save payloads (optimistic concurrency)

### Don't

- Don't duplicate the `/wcapi` prefix — `VITE_API_URL` must NOT include it
- Don't use legacy model names (`sales_order`, `purchase_order`, `location` as model)
- Don't HTTP-cache wcapi calls — they are live database operations
- Don't store access tokens in localStorage or sessionStorage
- Don't bypass the `ApiEnvelope` type — always unwrap `res.data.data`
- Don't query communication models separately on Contact/Org pages — use `refs.links`
- Don't create per-model REST endpoints — all CRUD goes through wcapi
- Don't use `class` components — functional components with hooks only
- Don't use deprecated field names (`dt_end`, `dt_updated`, `duration`)
- Don't hard-code field lists for denormalized data — they come from the backend
- Don't create sandbox experiments without a dated cleanup note

---

## 15. Key File Locations

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

---

## 16. Documentation Practice

- **Readmes are essential** — update `readmes/` when architecture decisions change
- Files `00-` through `03-` are the core onboarding sequence
- Topic deep-dives go in `readmes/topics/{category}/`
- Migration tracking in `readmes/api-migration-rest-to-wcapi.md`
- Legacy reference: `vue2020/src/components/` for feature parity checks

---

## 17. Instruction File Sync (MANDATORY)

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

## 18. Session Context

When starting a coding session, establish:

1. **Which app/model?** (e.g., `transactions/order`, `products/item`)
2. **What task?** (new feature, bug fix, refactor, test)
3. **Which layer?** (page component, service, type, schema, test)

This helps scope changes correctly within the domain-driven folder structure.

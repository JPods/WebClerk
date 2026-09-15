# Settings (React side)

> How the React app consumes configuration from the WC3 `Setting` model.

---

## Architecture

```
WC3 Setting record (JSONField)
        │
        ▼
  wcapi /get/?model_name=setting&...
        │
        ▼
  React hook (module-level cache)
        │
        ▼
  Components consume via hook
```

Settings are fetched **once** on first use and cached at module scope for
the session. Every component that calls the hook shares the same object
without triggering additional network requests.

---

## useTransactionDefaults

**File:** `src/hooks/useTransactionDefaults.ts`

Fetches the singleton Setting with `name="transaction_defaults"`,
`purpose="React_settings"` and returns a typed defaults object.

### Usage

```tsx
import { useTransactionDefaults, computeDueDate } from '@/hooks/useTransactionDefaults';

function MyComponent() {
  const { defaults, loading, refresh } = useTransactionDefaults();

  // defaults.terms          → "On Order"
  // defaults.due_date_period → 1
  // defaults.price_level    → "retail"
  // defaults.priority       → "standard"

  const dueDate = computeDueDate('2026-03-04', defaults.due_date_period);
  // → "2026-03-05"
}
```

### Return value

| Property  | Type                   | Description |
|-----------|------------------------|-------------|
| `defaults`| `TransactionDefaults`  | Current defaults (fallback values until fetch completes) |
| `loading` | `boolean`              | True while the initial fetch is in-flight |
| `refresh` | `() => Promise<void>`  | Clears cache and re-fetches from server |

### TransactionDefaults interface

```typescript
interface TransactionDefaults {
  terms: string;           // e.g. "On Order"
  due_date_period: number; // days to add to dt for due_date
  price_level: string;     // e.g. "retail"
  priority: string;        // e.g. "standard"
}
```

### Fallback values

If the Setting record is missing or the request fails, the hook returns
hardcoded fallbacks matching the seeded data:

```typescript
{ terms: 'On Order', due_date_period: 1, price_level: 'retail', priority: 'standard' }
```

### computeDueDate utility

```typescript
computeDueDate(dt: string, periodDays: number): string
```

Adds `periodDays` to an ISO date string and returns a new ISO date string.
Used by `TransactionDetailBase` when creating new transactions.

---

## Where defaults are applied

**File:** `src/apps/transactions/components/TransactionDetailBase.tsx`

When creating a new transaction (both "create" and "transfer" modes),
the hook values are spread as base defaults, then overridden by any
source-record fields (transfer) or query-param values (create):

```
base defaults (txDefaults)  →  source/query overrides  →  final record
```

Fields applied: `terms`, `price_level`, `priority`, `due_date`
(computed via `computeDueDate`).

---

## Adding new settings

To add a new category of defaults consumed by React:

1. **WC3:** Seed a new Setting record with `purpose="React_settings"` and
   a descriptive `name` (or add keys to an existing record's `data` JSON).
2. **React:** Create a new hook in `src/hooks/` following the
   `useTransactionDefaults` pattern (fetch → cache → fallback).
3. **Document** the `data` shape in both `webClerk3/readmes/settings.md`
   and this file.

When multiple settings are always consumed together, prefer nesting them
in a single record's `data` to minimize wcapi round-trips.

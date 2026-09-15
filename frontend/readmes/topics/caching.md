# Frontend Caching Strategy

## Core Philosophy

```
WCAPI = Database = NEVER CACHED
```

The React2025 frontend follows a simple rule:

| Source | Caching | How to Cache If Needed |
|--------|---------|----------------------|
| **WCAPI calls** (`/wcapi/*`) | ❌ NEVER | Store in JavaScript variables |
| **Non-WCAPI endpoints** | ✅ Session cache | Automatic via axios |

### Why?

- **WCAPI = Database operations**: Inventories, orders, customers can be changed by many sources at any time
- **Multi-user environment**: Another user, API integration, or background process may have modified data
- **Real-time accuracy**: Users expect to see current database state, not stale data

## WCAPI Calls - NEVER Cached

ALL calls to `/wcapi/` are database actions and are **never cached**:

```typescript
// In axios.ts:
const NEVER_CACHE_PATTERNS = [
  '/wcapi/',      // ALL wcapi calls - never cache
  '/api/wcapi/',  // Alternate mount - never cache
];
```

This includes:
- `/wcapi/get/?model_name=order` - Fetching orders
- `/wcapi/get/?model_name=customer&id=123` - Fetching a customer
- `/wcapi/save/` - Saving records
- `/wcapi/model_name/list/` - Even model lists
- Any URL containing `/wcapi/`

## Caching Static Data - Use Variables

If you have database values that rarely change and you want to "cache" them for performance:

**DON'T** use HTTP/session caching.

**DO** store them in JavaScript variables:

### Option 1: React State (component-level)
```typescript
const [modelNames, setModelNames] = useState<string[]>([]);

useEffect(() => {
  // Fetch once on mount
  getModelNames().then(setModelNames);
}, []);
```

### Option 2: React Context (app-level)
```typescript
// In a context provider
const [currencies, setCurrencies] = useState<Currency[]>([]);

// Fetch once, share across app
useEffect(() => {
  fetchCurrencies().then(data => setCurrencies(data.items));
}, []);
```

### Option 3: Redux Store (global state)
```typescript
// In a slice
const schemaSlice = createSlice({
  name: 'schema',
  initialState: { modelNames: [] },
  reducers: {
    setModelNames: (state, action) => {
      state.modelNames = action.payload;
    },
  },
});
```

### When to use variables for caching:
- Model schema definitions (field names, types)
- Currency lists
- Status code lookups
- User preferences
- Any reference data that doesn't change during a session

### When NOT to use variables (always fetch fresh):
- Inventory levels
- Order statuses
- Customer balances
- Any transactional data
- Anything another user might edit

## Non-WCAPI Calls - May Be Cached

Endpoints that are NOT wcapi (external APIs, static configs) use session caching:

```typescript
// These CAN be cached (not wcapi)
const res = await apiClient.get('/external/rates/');  // Cached
const res = await apiClient.get('/static/config/');   // Cached

// Force no-cache if needed
const res = await apiClient.get('/external/rates/', { 
  cache: false 
} as any);
```

## Session Cache Implementation

For non-wcapi endpoints, caching uses `sessionStorage`:

- **Scope**: Browser session only (cleared when tab closes)
- **Key format**: `wc_cache_v1:{baseURL}{url}?{params}`
- **Cleared on logout**: `clearTokens()` calls `clearResponseCache()`

## Clearing the Cache

### Programmatically
```typescript
import { clearResponseCache } from '../api/axios';
clearResponseCache();
```

### Manually (DevTools)
1. Open DevTools (F12)
2. **Application** tab → **Session Storage**
3. Delete entries starting with `wc_cache_v1:`

## Quick Reference

```
┌─────────────────────────────────────────────────────────────┐
│                    CACHING DECISION TREE                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Is it a /wcapi/ call?                                      │
│       │                                                     │
│       ├── YES → NEVER CACHE                                 │
│       │         Need to cache? → Use JavaScript variables   │
│       │                                                     │
│       └── NO  → Session cache OK                            │
│                 (can disable with cache: false)             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Summary

| What | Where | Why |
|------|-------|-----|
| Database records | NEVER cached | Multi-source changes |
| Static DB values to cache | JavaScript variables | Controlled, explicit |
| Non-wcapi endpoints | Session storage | Reduces network calls |
| User auth tokens | localStorage | Persist across sessions |

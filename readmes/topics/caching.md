# Frontend Caching Strategy

## Overview

The React2025 frontend uses a **session-scoped cache** for GET requests to reduce network traffic and improve perceived performance. However, certain endpoints are explicitly excluded from caching to ensure data freshness.

## Cache Implementation

The cache is implemented in `src/api/axios.ts` using `sessionStorage`:

- **Scope**: Session-only (cleared when browser tab closes)
- **Key format**: `wc_cache_v1:{baseURL}{url}?{params}`
- **Storage**: Browser's `sessionStorage`

## What Gets Cached

By default, all GET requests through `apiClient` are cached for the duration of the browser session.

### Cached Endpoints (examples)
- `/wcapi/model_name/list/` - Model name lists (rarely change)
- `/wcapi/model_name/detail/` - Model schema definitions
- Static configuration endpoints

## What Does NOT Get Cached

### Database Records (`/wcapi/get/`)

**All calls to `/wcapi/get/` bypass the cache** because:

1. **Data freshness**: Records can be modified by other users or processes
2. **Line items**: Transaction lines (sales order lines, invoice lines, etc.) may be added/removed
3. **Real-time accuracy**: Users expect to see current database state

This is enforced in `src/api/wcapi.ts`:

```typescript
// getRecords - list queries
const res = await apiClient.get(`/wcapi/get/`, { 
  params: { model_name, ...params },
  cache: false,  // Never cache
} as any);

// getRecord - single record detail
const res = await apiClient.get(`/wcapi/get/`, { 
  params: { model_name, id },
  cache: false,  // Never cache
} as any);
```

## How to Bypass Cache

### Option 1: `cache: false` in config
```typescript
const res = await apiClient.get('/some/endpoint/', {
  cache: false,
} as any);
```

### Option 2: `x-skip-cache` header
```typescript
const res = await apiClient.get('/some/endpoint/', {
  headers: { 'x-skip-cache': true },
});
```

## Clearing the Cache

### Programmatically
```typescript
import { clearResponseCache } from '../api/axios';
clearResponseCache();
```

### Automatically cleared when:
- User logs out (`clearTokens()` calls `clearResponseCache()`)
- Browser tab/window is closed (sessionStorage behavior)

### Manually (DevTools)
1. Open DevTools (F12)
2. Go to **Application** tab
3. Select **Session Storage** in the left panel
4. Right-click and **Clear** or delete entries starting with `wc_cache_v1:`

## Troubleshooting

### Symptom: Stale data displayed
**Cause**: Endpoint might be cached when it shouldn't be

**Solution**: 
1. Add `cache: false` to the API call
2. Or hard refresh the browser (Cmd+Shift+R / Ctrl+Shift+R)

### Symptom: No network request in DevTools
**Cause**: Response is being served from session cache

**Solution**: Check if the endpoint should be excluded from caching

## Design Decisions

### Why session cache instead of no cache?
- Reduces server load for repeated navigation
- Improves perceived performance for static data
- Acceptable for data that rarely changes within a session

### Why exclude `/wcapi/get/`?
- Database records are the core of the application
- Users expect real-time accuracy
- Multi-user environments require fresh data
- Transaction lines (FK relations) may change between views

### Why not use HTTP caching headers?
- More control over cache behavior per endpoint
- Easier to clear programmatically on logout
- Works consistently across all browsers

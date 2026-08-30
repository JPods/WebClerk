# App Bootstrap — Server-Driven Startup Data
**Built:** 2026-07-04

---

## Principle

Nothing hardcoded in React. All defaults, select lists, company info, payment terms, tax jurisdictions, warehouses, and campaigns come from the server via one bootstrap call at startup.

---

## How It Works

```
React app loads
  → useAppBootstrap(isAuthenticated)
    → POST /wcapi/manage/ { action: 'get_app_bootstrap' }
      → app_bootstrap.py gathers from:
         Setting (company_profile, admin_selectlist, db_defaults)
         Term (payment terms)
         TaxJurisdiction (tax rates)
         Warehouse (locations)
         Campaign (source attribution)
      ← returns all data in one response
    → cached 5 min in module state + localStorage fallback
```

One call, all data, cached. No waterfall of individual API calls.

---

## What Gets Loaded

| Data | Source | Used For |
|---|---|---|
| Company profile | Setting purpose='company_profile' | Print headers, logos, letterhead |
| Select lists | Setting purpose='admin_selectlist' | Dropdowns throughout the app |
| Payment terms | Term model | Invoice terms dropdown |
| Tax jurisdictions | TaxJurisdiction model | Tax rate dropdowns |
| Warehouses | Warehouse model | Location pickers |
| Campaigns | Setting purpose='campaign' (or Campaign model) | Source attribution dropdown |
| Defaults | Setting purpose='db_defaults' | Default values for new records |

---

## React Usage

```typescript
// In any component:
const bootstrap = useAppBootstrap(isAuthenticated);

// Company info for print header:
bootstrap.company.name          // "JPods LLC"
bootstrap.company.logos.primary  // "media/company/logos/jpods-logo-primary.png"

// Select list for a dropdown:
const statusOptions = getSelectList(bootstrap, 'status');
// → [{value: 'active', label: 'Active'}, ...]

// Payment terms for invoice form:
const termOptions = getPaymentTermOptions(bootstrap);
// → [{value: '5', label: 'Net 30 (30 days)'}, ...]

// Tax jurisdictions:
const taxOptions = getTaxJurisdictionOptions(bootstrap);
// → [{value: '3', label: 'Oklahoma (8.517%)'}, ...]

// Force refresh:
bootstrap.refresh(true);
```

---

## Adding a New Select List

1. Create a Setting record: `purpose='admin_selectlist'`, `config={key: [options]}`
2. Options can be: `['value']`, `['value', 'label']`, or `{value, label}`
3. React automatically picks it up on next bootstrap load
4. No React code change needed

---

## Admin Change Detection (dt_changed flag)

When an admin changes any default, select list, company profile, term, or jurisdiction:

```
Admin saves a Setting record
  → call touch_bootstrap()              — stamps dt_changed = now (epoch ms)
  → React polls get_bootstrap_dt every 60s
  → server dt_changed > cached dt_changed?
    → yes: auto-refresh all bootstrap data
    → no:  do nothing
```

No manual refresh needed. No page reload. Dropdowns update within 60 seconds of any admin change.

`touch_bootstrap()` should be called from any admin save path that modifies defaults or select lists.

## Offline / Fast Reload

Bootstrap data cached in localStorage. If the server is unreachable, React uses the cached version with a warning. On fast page reload, cached data shows immediately while fresh data loads in background.

---

## Files

| File | Purpose |
|------|---------|
| `backend/apps/core/services/app_bootstrap.py` | Server: gathers all data |
| `frontend/src/hooks/useAppBootstrap.ts` | Client: loads, caches, exposes |
| `frontend/src/constants/staticLists.ts` | DEPRECATED — replaced by bootstrap |
| `frontend/src/config/selectLists.ts` | DEPRECATED — replaced by bootstrap |

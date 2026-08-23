# Org App Pages Implementation Plan

## Overview

Rebuild all organization pages (List.tsx and Detail.tsx) to align with the current wc3 (webClerk3) schema. Remove filler/placeholder implementations and implement proper admin-only access.

---

## Current State Analysis

### Backend Schema (webClerk3)

The `OrgBase` model in `apps/orgs/models/base.py` uses a unified organization entity with:

**Core Fields:**
- `org_type` - Enum: customer, vendor, rep, employee, manufacturer, other
- `display_name` (aliased as `company`) - Primary identifier
- `status` - active, prospect, retired, etc.
- `is_active` - Boolean flag

**JSONB Aspect Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `contacts` | `[{id, name, role, phones, emails}]` | Related contacts (max 15) |
| `locations` | `[{id, type, address, geo}]` | Physical locations (max 10) |
| `domains` | `[{domain, verified, dt_verified}]` | Web domains (max 10) |
| `phones` | `[{id, type, number, ext, primary}]` | Phone numbers (max 10) |
| `emails` | `[{id, type, email, primary}]` | Email addresses (max 10) |
| `relations` | `{parents, children, linked_ids}` | Org relationships |
| `financial` | `{credit, balances, due_buckets, metrics}` | Financial data |
| `docs` | `[{id, kind, name, size, sha256}]` | Attached documents (max 25) |
| `connections` | `{email_svc: "vault:cred:123"}` | Service connections |
| `data` | `{}` | Miscellaneous data |
| `metrics` | `{counts, periods}` | Aggregated metrics |
| `gl_accounts` | `{}` | GL account mappings |

### Proxy Models

All org types share the same table via Django proxy models:
- `Customer` - `org_type='customer'`
- `Vendor` - `org_type='vendor'`
- `Rep` - `org_type='rep'`
- `Employee` - `org_type='employee'`
- `Manufacturer` - `org_type='manufacturer'`
= `Other` - `org_type='other'`

### Frontend Current State

```
src/apps/orgs/models/
├── base_org_model/        # Base org utilities (KEEP)
├── customer/
│   ├── pages/
│   │   ├── CustomerList.tsx      # REBUILD
│   │   ├── CustomerDisplay.tsx   # RENAME to CustomerDetail.tsx, REBUILD
│   │   └── CustomerListMob.tsx   # REMOVE (merge responsive into List)
│   ├── services/                  # UPDATE API calls
│   ├── types/                     # UPDATE to match schema
│   └── utils/
├── vendor/
│   ├── pages/
│   │   ├── VendorList.tsx        # REBUILD
│   │   ├── VendorDetail.tsx      # REBUILD
│   │   └── VendorListMob.tsx     # REMOVE
│   ├── services/
│   ├── types/
│   └── utils/
├── employee/                      # Same structure - REBUILD all
├── manufacturer/                  # Same structure - REBUILD all
├── rep/                           # Same structure - REBUILD all
├── other/                         # Same structure - REBUILD all
└── organization/                  # Generic org view - REBUILD all
```

---

## Implementation Plan

### Phase 1: Shared Infrastructure

#### 1.1 Create Unified Org Types
**File:** `src/apps/orgs/types/orgTypes.ts`

```typescript
// Match wc3 OrgBase schema exactly
export type OrgType = 'customer' | 'vendor' | 'rep' | 'employee' | 'manufacturer' | 'other';

export interface OrgContact {
  id: number | null;
  name: string;
  role?: string;
  phones?: OrgPhone[];
  emails?: OrgEmail[];
}

export interface OrgLocation {
  id: number | null;
  type?: string;
  address: {
    line1?: string;
    line2?: string;
    city?: string;
    state?: string;
    postal?: string;
    country?: string;
  };
  geo?: { lat: number; lng: number };
}

export interface OrgDomain {
  domain: string;
  verified: boolean;
  dt_verified?: number;
}

export interface OrgPhone {
  id: number | null;
  type?: string;
  number: string;
  ext?: string;
  primary?: boolean;
}

export interface OrgEmail {
  id: number | null;
  type?: string;
  email: string;
  primary?: boolean;
  bounce_count?: number;
}

export interface OrgRelations {
  parents: number[];
  children: number[];
  linked_ids: number[];
}

export interface OrgFinancial {
  credit?: { limit?: number; used?: number };
  balances?: { open?: number; [key: string]: number | undefined };
  due_buckets?: Array<{ range: string; amount: number }>;
  metrics?: { ytd?: { sales?: number } };
}

export interface OrgDoc {
  id: number | null;
  kind: string;
  name: string;
  size?: number;
  sha256?: string;
}

export interface OrgMetrics {
  counts: Record<string, number>;
  periods: Record<string, Record<string, number>>;
}

export interface Organization {
  id: number;
  uuid: string;
  org_type: OrgType;
  display_name: string;
  company: string; // alias for display_name
  status: string;
  is_active: boolean;
  
  // Aspect JSONB fields
  contacts: OrgContact[];
  locations: OrgLocation[];
  domains: OrgDomain[];
  phones: OrgPhone[];
  emails: OrgEmail[];
  relations: OrgRelations;
  financial: OrgFinancial;
  docs: OrgDoc[];
  connections: Record<string, string>;
  data: Record<string, unknown>;
  metrics: OrgMetrics;
  gl_accounts: Record<string, unknown>;
  
  // Timestamps
  dt_created: string;
  dt_modified: string;
  version: number;
}
```

#### 1.2 Create Unified Org API Service
**File:** `src/apps/orgs/services/orgApi.ts`

```typescript
import { wcapi } from '@/api/wcapi';
import type { Organization, OrgType } from '../types/orgTypes';

export const orgApi = {
  list: (orgType?: OrgType, params?: Record<string, unknown>) => 
    wcapi.get('organization', { org_type: orgType, ...params }),
    
  get: (id: number) => wcapi.get('organization', { id }),
  
  create: (data: Partial<Organization>) => wcapi.save('organization', data),
  
  update: (id: number, data: Partial<Organization>) => 
    wcapi.save('organization', { id, ...data }),
    
  delete: (id: number) => wcapi.delete('organization', id),
};

// Type-specific convenience wrappers
export const customerApi = {
  list: (params?: Record<string, unknown>) => orgApi.list('customer', params),
  get: (id: number) => orgApi.get(id),
  create: (data: Partial<Organization>) => orgApi.create({ ...data, org_type: 'customer' }),
  update: (id: number, data: Partial<Organization>) => orgApi.update(id, data),
  delete: (id: number) => orgApi.delete(id),
};

// ... repeat for vendor, employee, rep, manufacturer
```

#### 1.3 Create Admin Role Guard Component
**File:** `src/components/auth/AdminGuard.tsx`

```typescript
import { useAppSelector } from '@/store/hooks';
import { Navigate } from 'react-router-dom';

const ADMIN_ROLES = ['admin', 'Admin', 'superadmin', 'SuperAdmin'];

export const useIsAdmin = () => {
  const user = useAppSelector((state) => state.auth.user);
  return user && ADMIN_ROLES.some(r => user.role?.toLowerCase() === r.toLowerCase());
};

export const AdminGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAdmin = useIsAdmin();
  
  if (!isAdmin) {
    return <Navigate to="/unauthorized" replace />;
  }
  
  return <>{children}</>;
};
```

---

### Phase 2: Build Base Components

#### 2.1 Base OrgList Component
**File:** `src/apps/orgs/components/OrgList.tsx`

Features:
- DataTable with sorting, filtering, pagination
- Responsive design (no separate mobile component)
- Quick actions: View, Edit, Delete
- Bulk actions support
- Export functionality
- Column visibility toggle

#### 2.2 Base OrgDetail Component  
**File:** `src/apps/orgs/components/OrgDetail.tsx`

Features:
- Tabbed interface for aspects (Contacts, Locations, Financial, etc.)
- Inline editing with form validation
- Aspect limits enforcement (match ASPECT_LIMITS from backend)
- Activity timeline from refs.activity
- Related records linking

---

### Phase 3: Implement Org Type Pages

For each org type (customer, vendor, employee, rep, manufacturer):

#### 3.1 List Page Pattern
```
src/apps/orgs/models/{type}/pages/{Type}List.tsx
```

- Import base `OrgList` component
- Configure type-specific columns
- Set default filters for org_type
- Admin role check wrapper

#### 3.2 Detail Page Pattern
```
src/apps/orgs/models/{type}/pages/{Type}Detail.tsx
```

- Import base `OrgDetail` component
- Configure type-specific tabs/sections
- Custom fields per org type if needed
- Admin role check wrapper

---

### Phase 4: Route Configuration Updates

#### 4.1 Update protectedRoutesConfig.tsx

Add role requirement to org routes:

```typescript
// In protectedRoutesConfig.tsx
{ 
  path: PageRoutes.customerList, 
  element: <AdminGuard><CustomerList /></AdminGuard>,
  requiredRole: 'admin'
},
```

#### 4.2 Add Detail Routes

Currently missing detail routes for orgs. Add:

```typescript
{ path: '/org/customer/:id', element: <AdminGuard><CustomerDetail /></AdminGuard> },
{ path: '/org/vendor/:id', element: <AdminGuard><VendorDetail /></AdminGuard> },
{ path: '/org/employee/:id', element: <AdminGuard><EmployeeDetail /></AdminGuard> },
{ path: '/org/rep/:id', element: <AdminGuard><RepDetail /></AdminGuard> },
{ path: '/org/manufacturer/:id', element: <AdminGuard><ManufacturerDetail /></AdminGuard> },
```

---

## Files to Remove (Filler/Duplicates)

```bash
# Mobile-specific files (merge into responsive main component)
src/apps/orgs/models/customer/pages/CustomerListMob.tsx
src/apps/orgs/models/vendor/pages/VendorListMob.tsx
src/apps/orgs/models/employee/pages/EmployeeListMob.tsx
src/apps/orgs/models/rep/pages/RepListMob.tsx
src/apps/orgs/models/manufacturer/pages/ManufacturerListMob.tsx

# Rename CustomerDisplay.tsx to CustomerDetail.tsx
src/apps/orgs/models/customer/pages/CustomerDisplay.tsx → CustomerDetail.tsx
```

---

## Implementation Checklist

### Phase 1: Shared Infrastructure
- [x] Create `src/apps/orgs/types/orgTypes.ts` ✅ (2026-01-14)
- [x] Create `src/apps/orgs/services/orgApi.ts` ✅ (2026-01-14)
- [x] Create `src/components/auth/AdminGuard.tsx` ✅ (2026-01-14)
- [ ] Create unauthorized page component

### Phase 2: Base Components
- [x] Create `src/apps/orgs/components/OrgList.tsx` ✅ (2026-01-14)
- [x] Create `src/apps/orgs/components/OrgDetail.tsx` ✅ (2026-01-14)
- [ ] Create `src/apps/orgs/components/OrgContactsTab.tsx` (optional - built into OrgDetail)
- [ ] Create `src/apps/orgs/components/OrgLocationsTab.tsx` (optional - built into OrgDetail)
- [ ] Create `src/apps/orgs/components/OrgFinancialTab.tsx` (optional - built into OrgDetail)
- [ ] Create `src/apps/orgs/components/OrgDocsTab.tsx` (optional - built into OrgDetail)

### Phase 3: Customer Pages
- [ ] Rebuild `CustomerList.tsx`
- [ ] Rename & rebuild `CustomerDetail.tsx`
- [ ] Remove `CustomerListMob.tsx`
- [ ] Update `customerApi.ts` service

### Phase 4: Vendor Pages
- [ ] Rebuild `VendorList.tsx`
- [ ] Rebuild `VendorDetail.tsx`
- [ ] Remove `VendorListMob.tsx`
- [ ] Update `vendorApi.ts` service

### Phase 5: Employee Pages
- [x] Rebuild `EmployeeList.tsx` ✅ (2026-01-14)
- [x] Rebuild `EmployeeDetail.tsx` ✅ (2026-01-14)
- [x] Remove `EmployeeListMob.tsx` ✅ (2026-01-14)
- [x] Remove `EmployeeDisplay.tsx` ✅ (2026-01-14)
- [x] Update to use shared `orgApi.ts` service ✅ (2026-01-14)

### Phase 6: Rep Pages
- [ ] Rebuild `RepList.tsx`
- [ ] Rebuild `RepDetail.tsx`
- [ ] Remove `RepListMob.tsx`
- [ ] Update `repApi.ts` service

### Phase 7: Manufacturer Pages
- [ ] Rebuild `ManufacturerList.tsx`
- [ ] Rebuild `ManufacturerDetail.tsx`
- [ ] Remove `ManufacturerListMob.tsx`
- [ ] Update `manufacturerApi.ts` service

### Phase 8: Routes & Access Control
- [x] AdminGuard built into Employee components ✅ (2026-01-14)
- [ ] Update `protectedRoutesConfig.tsx` with AdminGuard for other org types
- [ ] Add detail routes for all org types
- [ ] Add `/unauthorized` route
- [ ] Test role-based access

---

## Estimated Effort

| Phase | Description | Hours |
|-------|-------------|-------|
| 1 | Shared Infrastructure | 2-3 |
| 2 | Base Components | 4-6 |
| 3-7 | Org Type Pages (5 types × 2hrs) | 10-12 |
| 8 | Routes & Access Control | 1-2 |
| **Total** | | **17-23 hours** |

---

## Notes

1. **Schema Alignment**: The frontend types must exactly match `OrgBase` fields in webClerk3
2. **Proxy Model Behavior**: All org types use the same `organization` endpoint with `org_type` filter
3. **Aspect Limits**: Enforce the same limits as backend (contacts: 15, locations: 10, etc.)
4. **Admin Access**: All org pages restricted to admin role only
5. **Responsive Design**: No separate mobile components - use Tailwind responsive classes

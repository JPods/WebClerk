# Role-Based Access Control (RBAC) - Frontend

**Status:** ✅ Implemented  
**Date:** March 5, 2026

---

## Overview

The frontend RBAC system provides role-based UI control through:
1. **Permissions API** - Fetch user's effective permissions from backend
2. **PermissionsContext** - React context with hooks for permission checks
3. **Permission Guards** - Components for conditional rendering

---

## Architecture

```
                  /wcapi/permissions/
                         │
                         ▼
              ┌─────────────────────┐
              │ PermissionsContext  │
              │   ├─ usePermissions │
              │   ├─ useModelPerms  │
              │   └─ useFieldPerms  │
              └─────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   PermissionGate   FieldGuard      ModelGuard
```

---

## Files

| File | Purpose |
|------|---------|
| [src/type/permissions.ts](../src/type/permissions.ts) | TypeScript types |
| [src/context/PermissionsContext.tsx](../src/context/PermissionsContext.tsx) | Context & hooks |
| [src/components/PermissionGuards.tsx](../src/components/PermissionGuards.tsx) | Guard components |

---

## Usage

### Setup Provider

Wrap your app with `PermissionsProvider`:

```tsx
import { PermissionsProvider } from '@/context/PermissionsContext';

function App() {
  return (
    <PermissionsProvider>
      <RouterProvider router={router} />
    </PermissionsProvider>
  );
}
```

### Using Hooks

```tsx
import { usePermissions, useModelPermissions, useFieldPermissions } from '@/context/PermissionsContext';

function OrderPage() {
  // Get full permissions object
  const { permissions, isLoading, hasRole } = usePermissions();
  
  // Check specific role
  if (hasRole('admin')) {
    // Show admin features
  }
  
  // Get model-specific permissions
  const orderPerms = useModelPermissions('order');
  // orderPerms = { canView, canEdit, canCreate, canDelete, viewFields, editFields }
  
  // Check specific field access
  const canViewTotal = useFieldPermissions('order', 'totals.total', 'view');
  const canEditStatus = useFieldPermissions('order', 'status', 'edit');
}
```

### Guard Components

```tsx
import { PermissionGate, FieldGuard, ModelGuard } from '@/components/PermissionGuards';

// Role-based visibility
<PermissionGate roles={['admin', 'user_sales']}>
  <AdminPanel />
</PermissionGate>

// Model permission guard
<ModelGuard model="order" action="create">
  <Button>Create Order</Button>
</ModelGuard>

// Field-level guard
<FieldGuard model="order" field="totals.total" action="view">
  <span>Total: ${order.totals.total}</span>
</FieldGuard>

// With fallback content
<PermissionGate 
  roles={['admin']} 
  fallback={<span>Insufficient permissions</span>}
>
  <DeleteButton />
</PermissionGate>
```

### Higher-Order Component

```tsx
import { withPermissions } from '@/components/PermissionGuards';

const AdminOnlyComponent = withPermissions(
  MyComponent,
  { roles: ['admin'] }
);
```

---

## API Response Structure

```typescript
// GET /wcapi/permissions/
interface UserPermissions {
  roles: string[];              // ["user_sales", "user_production"]
  org_ids: {
    customer: number[];
    vendor: number[];
    manufacturer: number[];
    employee: number[];
  };
  contact_id: number | null;
  models: {
    [model: string]: {
      view: boolean;
      view_fields: string[] | "*";
      edit: boolean;
      edit_fields: string[] | "*";
      create: boolean;
      delete: boolean;
    };
  };
}
```

---

## Roles

| Role | Type | Description |
|------|------|-------------|
| `user_customer` | Portal | Customer portal - view own orders/invoices |
| `user_vendor` | Portal | Vendor portal - view purchases, supplied items |
| `user_manufacturer` | Portal | Manufacturer portal - purchases, commission orders |
| `user_rep` | Portal | Sales rep - orders for assigned customers |
| `user_sales` | Internal | Internal sales - all customer transactions |
| `user_production` | Internal | Production - product/inventory management |
| `user_accounting` | Internal | Accounting - financial transactions |
| `user_warehouse` | Internal | Warehouse - inventory operations |
| `admin` | Internal | Administrator - full access |
| `superuser` | System | System owner - full access + Postgres |

---

## Field Permission Patterns

View/edit fields support dotted paths:

| Pattern | Meaning |
|---------|---------|
| `"*"` | All fields allowed |
| `"id"` | Top-level field |
| `"totals.total"` | Nested JSON field |
| `"refs.tags"` | Refs array |
| `"lines"` | Related model (all fields) |
| `"lines.status"` | Specific field on related model |

---

## Best Practices

1. **Check loading state** - Always handle `isLoading` before rendering permission-dependent content
2. **Use guards for UI** - Hide/show elements based on permissions
3. **Backend enforces** - Frontend guards are for UX only; backend validates all actions
4. **Cache permissions** - Context caches permissions; call `refetch()` after role changes

---

## See Also

- [webClerk3/readmes/topics/architecture/role-based-access-plan.md](../../webClerk3/readmes/topics/architecture/role-based-access-plan.md) — Full RBAC implementation
- [03-api-integration.md](03-api-integration.md) — API integration patterns

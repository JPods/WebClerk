/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
"use client";

import type React from "react";
import { usePermissions, useModelPermissions, useFieldPermissions } from "../context/PermissionsContext";
import type { RoleName } from "../type/permissions";

interface PermissionGateProps {
  /** Required roles (any of these) */
  roles?: RoleName | RoleName[];
  /** Required model and operation */
  model?: string;
  operation?: "view" | "edit" | "create" | "delete";
  /** Content to render when permission is granted */
  children: React.ReactNode;
  /** Content to render when permission is denied (default: null) */
  fallback?: React.ReactNode;
  /** Show loading spinner while permissions load (default: false) */
  showLoading?: boolean;
}

/**
 * Conditionally render content based on RBAC permissions.
 *
 * @example
 * ```tsx
 * // Role-based
 * <PermissionGate roles="user_sales">
 *   <SalesOnlyFeature />
 * </PermissionGate>
 *
 * // Model operation
 * <PermissionGate model="order" operation="create">
 *   <CreateOrderButton />
 * </PermissionGate>
 *
 * // With fallback
 * <PermissionGate
 *   model="order"
 *   operation="delete"
 *   fallback={<p>You cannot delete orders</p>}
 * >
 *   <DeleteOrderButton />
 * </PermissionGate>
 * ```
 */
export const PermissionGate: React.FC<PermissionGateProps> = ({
  roles,
  model,
  operation = "view",
  children,
  fallback = null,
  showLoading = false,
}) => {
  const { hasRole, hasModelAccess, loading, isSuperuser } = usePermissions();

  if (loading && showLoading) {
    return <span className="inline-block w-4 h-4 border-2 border-gray-300 border-t-primary rounded-full animate-spin" />;
  }

  // Superusers always have access
  if (isSuperuser) {
    return <>{children}</>;
  }

  // Check roles if specified
  if (roles) {
    if (!hasRole(roles)) {
      return <>{fallback}</>;
    }
  }

  // Check model access if specified
  if (model) {
    if (!hasModelAccess(model, operation)) {
      return <>{fallback}</>;
    }
  }

  return <>{children}</>;
};

interface FieldGuardProps {
  /** Model name */
  model: string;
  /** Field name or dotted path */
  field: string;
  /** Whether to check edit permission (default: view) */
  mode?: "view" | "edit";
  /** Content to render when permission is granted */
  children: React.ReactNode;
  /** Content to render when permission is denied (default: null) */
  fallback?: React.ReactNode;
}

/**
 * Conditionally render content based on field-level permissions.
 *
 * @example
 * ```tsx
 * // Hide field if user can't view it
 * <FieldGuard model="order" field="totals.margin">
 *   <MarginDisplay value={order.totals.margin} />
 * </FieldGuard>
 *
 * // Show input only if user can edit
 * <FieldGuard model="order" field="status" mode="edit">
 *   <StatusSelect {...props} />
 * </FieldGuard>
 * ```
 */
export const FieldGuard: React.FC<FieldGuardProps> = ({
  model,
  field,
  mode = "view",
  children,
  fallback = null,
}) => {
  const { canView, canEdit, loading, isSuperuser } = useFieldPermissions(model, field);

  if (loading) {
    return null;
  }

  // Superusers always have access
  if (isSuperuser) {
    return <>{children}</>;
  }

  const hasPermission = mode === "edit" ? canEdit : canView;

  return hasPermission ? <>{children}</> : <>{fallback}</>;
};

interface ModelGuardProps {
  /** Model name */
  model: string;
  /** Operation to check */
  operation: "view" | "edit" | "create" | "delete";
  /** Content to render when permission is granted */
  children: React.ReactNode;
  /** Content to render when permission is denied (default: null) */
  fallback?: React.ReactNode;
}

/**
 * Conditionally render content based on model-level permissions.
 *
 * @example
 * ```tsx
 * <ModelGuard model="order" operation="create">
 *   <CreateOrderButton />
 * </ModelGuard>
 * ```
 */
export const ModelGuard: React.FC<ModelGuardProps> = ({
  model,
  operation,
  children,
  fallback = null,
}) => {
  const { canView, canEdit, canCreate, canDelete, loading, isSuperuser } =
    useModelPermissions(model);

  if (loading) {
    return null;
  }

  // Superusers always have access
  if (isSuperuser) {
    return <>{children}</>;
  }

  const permissionMap = {
    view: canView,
    edit: canEdit,
    create: canCreate,
    delete: canDelete,
  };

  return permissionMap[operation] ? <>{children}</> : <>{fallback}</>;
};

/**
 * Higher-order component for permission-based rendering
 *
 * @example
 * ```tsx
 * const ProtectedComponent = withPermissions(MyComponent, {
 *   roles: "user_sales",
 * });
 *
 * // Or with model permission
 * const ProtectedEdit = withPermissions(EditForm, {
 *   model: "order",
 *   operation: "edit",
 * });
 * ```
 */
export function withPermissions<P extends object>(
  Component: React.ComponentType<P>,
  options: {
    roles?: RoleName | RoleName[];
    model?: string;
    operation?: "view" | "edit" | "create" | "delete";
    fallback?: React.ReactNode;
  }
): React.FC<P> {
  const WrappedComponent: React.FC<P> = (props) => (
    <PermissionGate
      roles={options.roles}
      model={options.model}
      operation={options.operation}
      fallback={options.fallback}
    >
      <Component {...props} />
    </PermissionGate>
  );

  WrappedComponent.displayName = `withPermissions(${
    Component.displayName || Component.name || "Component"
  })`;

  return WrappedComponent;
}

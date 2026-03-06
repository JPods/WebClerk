/**
 * RBAC Permission Types
 * 
 * Type definitions for role-based access control from the backend.
 */

/** Per-model permission configuration */
export interface ModelPermissions {
  /** Whether user can view records of this model */
  view: boolean;
  /** Fields user can view, or ["*"] for all */
  view_fields: string[];
  /** Whether user can edit records of this model */
  edit: boolean;
  /** Fields user can edit, or ["*"] for all */
  edit_fields: string[];
  /** Whether user can create new records */
  create: boolean;
  /** Whether user can delete records */
  delete: boolean;
}

/** User's complete permissions response from /wcapi/permissions/ */
export interface UserPermissions {
  /** Django user ID */
  user_id: number;
  /** User's assigned roles */
  roles: string[];
  /** Org IDs user is associated with by type */
  org_ids: {
    customer: number[];
    vendor: number[];
    manufacturer: number[];
    employee: number[];
  };
  /** Contact record ID if linked */
  contact_id: number | null;
  /** Whether user is a superuser */
  is_superuser: boolean;
  /** Per-model permissions */
  models: Record<string, ModelPermissions>;
}

/** Role identifiers */
export type RoleName =
  | "user_customer"
  | "user_vendor"
  | "user_manufacturer"
  | "user_rep"
  | "user_sales"
  | "user_production"
  | "user_accounting"
  | "user_warehouse"
  | "admin"
  | "superuser";

/** Common model names for type safety */
export type ModelName =
  | "order"
  | "invoice"
  | "proposal"
  | "purchase"
  | "workorder"
  | "customer"
  | "vendor"
  | "manufacturer"
  | "contact"
  | "action"
  | "document"
  | "item"
  | "category";

/** Check if a field is in allowed list (handles "*" wildcard) */
export function isFieldAllowed(
  field: string,
  allowedFields: string[]
): boolean {
  if (!allowedFields || allowedFields.length === 0) {
    return false;
  }
  
  if (allowedFields.includes("*")) {
    return true;
  }
  
  // Exact match
  if (allowedFields.includes(field)) {
    return true;
  }
  
  // Parent path allows children (e.g., "totals" allows "totals.total")
  const parts = field.split(".");
  for (let i = 0; i < parts.length; i++) {
    const parent = parts.slice(0, i + 1).join(".");
    if (allowedFields.includes(parent)) {
      return true;
    }
  }
  
  return false;
}

/** Check if user has any of the specified roles */
export function hasRole(
  permissions: UserPermissions | null,
  roles: RoleName | RoleName[]
): boolean {
  if (!permissions) return false;
  if (permissions.is_superuser) return true;
  
  const roleArray = Array.isArray(roles) ? roles : [roles];
  return roleArray.some((role) => permissions.roles.includes(role));
}

/** Check if user has access to a model for a specific operation */
export function hasModelAccess(
  permissions: UserPermissions | null,
  model: string,
  operation: "view" | "edit" | "create" | "delete"
): boolean {
  if (!permissions) return false;
  if (permissions.is_superuser) return true;
  
  const modelPerms = permissions.models[model];
  if (!modelPerms) return false;
  
  return modelPerms[operation] as boolean;
}

/** Check if user can view a specific field on a model */
export function canViewField(
  permissions: UserPermissions | null,
  model: string,
  field: string
): boolean {
  if (!permissions) return false;
  if (permissions.is_superuser) return true;
  
  const modelPerms = permissions.models[model];
  if (!modelPerms || !modelPerms.view) return false;
  
  return isFieldAllowed(field, modelPerms.view_fields);
}

/** Check if user can edit a specific field on a model */
export function canEditField(
  permissions: UserPermissions | null,
  model: string,
  field: string
): boolean {
  if (!permissions) return false;
  if (permissions.is_superuser) return true;
  
  const modelPerms = permissions.models[model];
  if (!modelPerms || !modelPerms.edit) return false;
  
  return isFieldAllowed(field, modelPerms.edit_fields);
}

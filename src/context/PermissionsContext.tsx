/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import type React from "react";
import {
  createContext,
  useState,
  useContext,
  useEffect,
  useCallback,
  useMemo,
} from "react";
import apiClient from "@/api/axios";
import type {
  UserPermissions,
  ModelPermissions,
  RoleName,
} from "../type/permissions";
import {
  hasRole as checkHasRole,
  hasModelAccess as checkModelAccess,
  canViewField as checkCanViewField,
  canEditField as checkCanEditField,
} from "../type/permissions";

interface PermissionsContextType {
  /** User's permissions, null if not loaded or not authenticated */
  permissions: UserPermissions | null;
  /** Whether permissions are currently being loaded */
  loading: boolean;
  /** Error message if permissions failed to load */
  error: string | null;
  /** Refresh permissions from the server */
  refresh: () => Promise<void>;
  /** Check if user has any of the specified roles */
  hasRole: (roles: RoleName | RoleName[]) => boolean;
  /** Check if user has access to a model operation */
  hasModelAccess: (
    model: string,
    operation: "view" | "edit" | "create" | "delete"
  ) => boolean;
  /** Check if user can view a specific field */
  canViewField: (model: string, field: string) => boolean;
  /** Check if user can edit a specific field */
  canEditField: (model: string, field: string) => boolean;
  /** Get permissions for a specific model */
  getModelPermissions: (model: string) => ModelPermissions | null;
  /** Whether user is authenticated (has permissions loaded) */
  isAuthenticated: boolean;
  /** Whether user is a superuser */
  isSuperuser: boolean;
}

const PermissionsContext = createContext<PermissionsContextType | undefined>(
  undefined
);

interface PermissionsProviderProps {
  children: React.ReactNode;
  /** API base URL (defaults to relative /wcapi/) */
  apiBaseUrl?: string;
}

export const PermissionsProvider: React.FC<PermissionsProviderProps> = ({
  children,
  apiBaseUrl = "/wcapi/",
}) => {
  const [permissions, setPermissions] = useState<UserPermissions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPermissions = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.get(`${apiBaseUrl}permissions/`);
      setPermissions(response.data);
    } catch (err: any) {
      if (err?.response?.status === 401) {
        // Not authenticated
        setPermissions(null);
      } else {
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(message);
        setPermissions(null);
      }
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl]);

  // Fetch permissions on mount
  useEffect(() => {
    fetchPermissions();
  }, [fetchPermissions]);

  // Memoized helper functions
  const hasRole = useCallback(
    (roles: RoleName | RoleName[]) => checkHasRole(permissions, roles),
    [permissions]
  );

  const hasModelAccess = useCallback(
    (model: string, operation: "view" | "edit" | "create" | "delete") =>
      checkModelAccess(permissions, model, operation),
    [permissions]
  );

  const canViewField = useCallback(
    (model: string, field: string) =>
      checkCanViewField(permissions, model, field),
    [permissions]
  );

  const canEditField = useCallback(
    (model: string, field: string) =>
      checkCanEditField(permissions, model, field),
    [permissions]
  );

  const getModelPermissions = useCallback(
    (model: string): ModelPermissions | null => {
      if (!permissions) return null;
      return permissions.models[model] || null;
    },
    [permissions]
  );

  const value = useMemo(
    () => ({
      permissions,
      loading,
      error,
      refresh: fetchPermissions,
      hasRole,
      hasModelAccess,
      canViewField,
      canEditField,
      getModelPermissions,
      isAuthenticated: permissions !== null,
      isSuperuser: permissions?.is_superuser ?? false,
    }),
    [
      permissions,
      loading,
      error,
      fetchPermissions,
      hasRole,
      hasModelAccess,
      canViewField,
      canEditField,
      getModelPermissions,
    ]
  );

  return (
    <PermissionsContext.Provider value={value}>
      {children}
    </PermissionsContext.Provider>
  );
};

/**
 * Hook to access RBAC permissions
 *
 * @example
 * ```tsx
 * const { hasRole, canEditField, loading } = usePermissions();
 *
 * if (loading) return <Spinner />;
 *
 * if (!hasRole("user_sales")) {
 *   return <AccessDenied />;
 * }
 *
 * return (
 *   <Form>
 *     <Input
 *       name="status"
 *       disabled={!canEditField("order", "status")}
 *     />
 *   </Form>
 * );
 * ```
 */
export const usePermissions = () => {
  const context = useContext(PermissionsContext);
  if (context === undefined) {
    throw new Error("usePermissions must be used within a PermissionsProvider");
  }
  return context;
};

/**
 * Hook to check model-level permissions
 *
 * @example
 * ```tsx
 * const { canView, canEdit, canCreate, canDelete } = useModelPermissions("order");
 *
 * return (
 *   <div>
 *     {canCreate && <CreateButton />}
 *     {canDelete && <DeleteButton />}
 *   </div>
 * );
 * ```
 */
export const useModelPermissions = (model: string) => {
  const { hasModelAccess, getModelPermissions, loading, permissions } =
    usePermissions();

  const modelPerms = getModelPermissions(model);

  return {
    loading,
    canView: hasModelAccess(model, "view"),
    canEdit: hasModelAccess(model, "edit"),
    canCreate: hasModelAccess(model, "create"),
    canDelete: hasModelAccess(model, "delete"),
    viewFields: modelPerms?.view_fields ?? [],
    editFields: modelPerms?.edit_fields ?? [],
    isSuperuser: permissions?.is_superuser ?? false,
  };
};

/**
 * Hook to check field-level permissions for a model
 *
 * @example
 * ```tsx
 * const { canView, canEdit } = useFieldPermissions("order", "status");
 *
 * return canView ? (
 *   <StatusBadge editable={canEdit} />
 * ) : null;
 * ```
 */
export const useFieldPermissions = (model: string, field: string) => {
  const { canViewField, canEditField, loading, permissions } = usePermissions();

  return {
    loading,
    canView: canViewField(model, field),
    canEdit: canEditField(model, field),
    isSuperuser: permissions?.is_superuser ?? false,
  };
};

export default PermissionsContext;

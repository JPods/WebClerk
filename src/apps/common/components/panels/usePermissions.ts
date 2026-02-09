/**
 * usePermissions - Hook for panel permission checking
 * Determines if current user can view or edit a panel based on their role
 */
import { useAppSelector } from "@/store/hooks";
import type { UserRole, PanelPermissions } from "./types";
import { ADMIN_ROLES, DEFAULT_PANEL_PERMISSIONS } from "./types";

export interface UsePermissionsOptions {
  /** Panel type for default permissions lookup */
  panelType?: string;
  /** Override view roles */
  viewRoles?: UserRole[];
  /** Override edit roles */
  editRoles?: UserRole[];
  /** Force read-only regardless of role */
  forceReadOnly?: boolean;
}

export interface UsePermissionsResult {
  /** Whether the panel should be visible */
  canView: boolean;
  /** Whether the user can edit (and panel is not forced read-only) */
  canEdit: boolean;
  /** Current user's role */
  userRole: string | null;
  /** Whether user has admin-level access */
  isAdmin: boolean;
}

/**
 * Check if a role matches any in the allowed list
 */
const roleMatches = (
  userRole: string | null | undefined,
  allowedRoles: UserRole[],
): boolean => {
  if (!userRole || typeof userRole !== "string") return false;

  const normalizedRole = userRole.toLowerCase().trim();

  return allowedRoles.some((allowed) => {
    const normalizedAllowed = allowed.toLowerCase();
    return (
      normalizedRole === normalizedAllowed ||
      normalizedRole.includes(normalizedAllowed)
    );
  });
};

/**
 * Hook to check panel permissions based on current user's role
 *
 * @example
 * const { canView, canEdit, isAdmin } = usePermissions({
 *   panelType: 'metadata',
 *   viewRoles: ['admin'],
 *   editRoles: ['admin'],
 * });
 *
 * if (!canView) return null;
 *
 * return (
 *   <Panel readOnly={!canEdit}>
 *     ...
 *   </Panel>
 * );
 */
export const usePermissions = (
  options: UsePermissionsOptions = {},
): UsePermissionsResult => {
  const { panelType, viewRoles, editRoles, forceReadOnly = false } = options;

  // Get current user from auth state
  const user = useAppSelector((state) => state.auth.user);
  const userRole: string | null =
    typeof user?.role === "string" ? user.role : null;

  // Check if user is admin
  const isAdmin = roleMatches(userRole, ADMIN_ROLES);

  // Get default permissions for panel type
  const defaults: PanelPermissions =
    panelType && DEFAULT_PANEL_PERMISSIONS[panelType]
      ? DEFAULT_PANEL_PERMISSIONS[panelType]
      : { viewRoles: [], editRoles: [] };

  // Use overrides or defaults
  const effectiveViewRoles = viewRoles ?? defaults.viewRoles;
  const effectiveEditRoles = editRoles ?? defaults.editRoles;

  // If no user role is available, be permissive (allow access for development)
  // This ensures the component works even before auth is fully set up
  const noRoleAvailable = !userRole;

  // Admin always has access, or if no role is set, default to allow
  const canView =
    noRoleAvailable || isAdmin || roleMatches(userRole, effectiveViewRoles);
  const canEdit =
    !forceReadOnly &&
    (noRoleAvailable || isAdmin || roleMatches(userRole, effectiveEditRoles));

  return {
    canView,
    canEdit,
    userRole,
    isAdmin,
  };
};

export default usePermissions;

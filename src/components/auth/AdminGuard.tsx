/**
 * AdminGuard - Role-based access control component
 * Restricts access to admin users only
 */
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAppSelector } from '@/store/hooks';

// Roles that grant admin access
const ADMIN_ROLES = ['admin', 'superadmin', 'super_admin', 'administrator'];

/**
 * Hook to check if current user has admin role
 */
export const useIsAdmin = (): boolean => {
  const user = useAppSelector((state) => state.auth.user);
  
  if (!user?.role) return false;
  
  const userRole = user.role.toLowerCase().trim();
  return ADMIN_ROLES.some(role => userRole === role || userRole.includes(role));
};

/**
 * Hook to get current user role
 */
export const useUserRole = (): string | null => {
  const user = useAppSelector((state) => state.auth.user);
  return user?.role ?? null;
};

interface AdminGuardProps {
  children: React.ReactNode;
  fallbackPath?: string;
  showMessage?: boolean;
}

/**
 * AdminGuard component - wraps content that requires admin access
 * 
 * @example
 * <AdminGuard>
 *   <SensitiveAdminPage />
 * </AdminGuard>
 */
export const AdminGuard: React.FC<AdminGuardProps> = ({ 
  children, 
  fallbackPath = '/unauthorized',
  showMessage = false 
}) => {
  const isAdmin = useIsAdmin();
  const location = useLocation();
  
  if (!isAdmin) {
    if (showMessage) {
      return (
        <div className="flex min-h-[400px] flex-col items-center justify-center p-8">
          <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-900/20">
            <h2 className="mb-2 text-xl font-semibold text-red-700 dark:text-red-400">
              Access Denied
            </h2>
            <p className="text-red-600 dark:text-red-300">
              You do not have permission to access this page.
              <br />
              Admin role required.
            </p>
          </div>
        </div>
      );
    }
    
    return <Navigate to={fallbackPath} state={{ from: location }} replace />;
  }
  
  return <>{children}</>;
};

/**
 * Higher-order component version for wrapping page components
 */
export function withAdminGuard<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  options?: Omit<AdminGuardProps, 'children'>
): React.FC<P> {
  const WithAdminGuard: React.FC<P> = (props) => (
    <AdminGuard {...options}>
      <WrappedComponent {...props} />
    </AdminGuard>
  );
  
  WithAdminGuard.displayName = `WithAdminGuard(${WrappedComponent.displayName || WrappedComponent.name || 'Component'})`;
  
  return WithAdminGuard;
}

export default AdminGuard;

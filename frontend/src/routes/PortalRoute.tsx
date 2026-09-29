/* The customer and vendor console's route (Bill, 2026-09-28): its own page, outside the staff
 * app — no sidebar, no windows, no company bootstrap (a portal login reads no Settings). A
 * staff login that lands here goes to the dashboard; the staff app sends portal logins here. */
import React from "react";
import { Navigate } from "react-router-dom";
import { useAppSelector } from "../store/hooks";
import LoadingSpinner from "@/components/common/LoadingSpinner";

const PortalDashboard = React.lazy(() => import("../pages/Dashboard/PortalDashboard"));

const PortalRoute: React.FC = () => {
  const { isLoading, isAuthenticated, user } = useAppSelector((state) => state.auth);
  const spinner = (
    <div className="flex justify-center items-center h-screen"><LoadingSpinner size="lg" label="Loading..." /></div>
  );
  if (isLoading) return spinner;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!user?.is_portal) return <Navigate to="/dashboard" replace />;
  return (
    <React.Suspense fallback={spinner}>
      <PortalDashboard />
    </React.Suspense>
  );
};

export default PortalRoute;

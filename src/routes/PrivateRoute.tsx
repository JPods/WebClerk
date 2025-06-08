import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAppSelector } from '../store/hooks';
import { SidebarProvider, useSidebar } from '../context/SidebarContext';
import AppSidebar from '../layout/AppSidebar';
import Backdrop from '../layout/Backdrop';
import AppHeader from '../layout/AppHeader';
import { useAuth } from '../hooks/useAuth';
import CustomHeader from '../layout/CustomHeader';

const AppLayout: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const { isExpanded, isHovered, isMobileOpen } = useSidebar();

  const location = useLocation();
  const pathSegments = location.pathname.split('/');
  const segment = pathSegments[1]; 
  console.log("data url", segment)
  //const { isLoading, isAuthenticated } = useAppSelector((state) => state.auth);
  if (isLoading) {
    return <div>Loading...</div>; // Or a loading spinner
  }

  return !isAuthenticated ? (
    <div className="min-h-screen xl:flex">
      <div>
        <AppSidebar />
        <Backdrop />
      </div>
      <div
        className={`flex-1 transition-all duration-300 ease-in-out ${
          isExpanded || isHovered ? "lg:ml-[290px]" : "lg:ml-[90px]"
        } ${isMobileOpen ? "ml-0" : ""}`}
      >
        <AppHeader />
        { segment === 'exam-list' && (
              <CustomHeader/>
        )}
        <div className="p-2 mx-auto max-w-(--breakpoint-2xl) md:px-6">
          <Outlet />
        </div>
      </div>
    </div>
    // <Outlet />
  ) : <Navigate to="/" replace />;
};

const PrivateRoute: React.FC = () => {
  return (
    <SidebarProvider>
      <AppLayout />
    </SidebarProvider>
  );
};

export default PrivateRoute;
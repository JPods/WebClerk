import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
//import { useAppSelector } from '../store/hooks';
import { SidebarProvider, useSidebar } from '../context/SidebarContext';
import AppSidebar from '../layout/AppSidebar';
import Backdrop from '../layout/Backdrop';
import AppHeader from '../layout/AppHeader';
import { useAppSelector } from '../store/hooks';

const AppLayout: React.FC = () => {
  
  //const { isAuthenticated, isLoading } = useAuth();
  const { isExpanded, isHovered, isMobileOpen } = useSidebar();

  // const location = useLocation();
  // const pathSegments = location.pathname.split('/');
  // const segment = pathSegments[1]; 

  const { isLoading, isAuthenticated } = useAppSelector((state) => state.auth);
    console.log("data url", isAuthenticated)
  if (isLoading) {
    return <div>Loading...</div>; // Or a loading spinner
  }
  
  const getToken = localStorage.getItem("accessToken");
  //const getToken = true

  return getToken ? (
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
        <div className="p-4 mx-auto max-w-(--breakpoint-2xl) md:p-6">
          <Outlet />
        </div>
      </div>
    </div>
    // <Outlet />
  ) : <Navigate to="/" replace />;
};

const PrivateRoute: React.FC = () => {
  const getToken = localStorage.getItem("accessToken");
  return getToken ? (
    <SidebarProvider>
      <AppLayout />
    </SidebarProvider>
  ) : <Navigate to="/" />;
};

export default PrivateRoute;


// const LayoutContent: React.FC = () => {
//   const { isExpanded, isHovered, isMobileOpen } = useSidebar();

//   return (
//     <div className="min-h-screen xl:flex">
//       <div>
//         <AppSidebar />
//         <Backdrop />
//       </div>
//       <div
//         className={`flex-1 transition-all duration-300 ease-in-out ${
//           isExpanded || isHovered ? "lg:ml-[290px]" : "lg:ml-[90px]"
//         } ${isMobileOpen ? "ml-0" : ""}`}
//       >
//         <AppHeader />
//         <div className="p-4 mx-auto max-w-(--breakpoint-2xl) md:p-6">
//           <Outlet />
//         </div>
//       </div>
//     </div>
//   );
// };

// const AppLayout: React.FC = () => {
//   return (
//     <SidebarProvider>
//       <LayoutContent />
//     </SidebarProvider>
//   );
// };
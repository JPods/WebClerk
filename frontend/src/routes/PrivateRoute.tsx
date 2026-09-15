/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import React, { useEffect } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { SidebarProvider, useSidebar } from "../context/SidebarContext";
import AppSidebar from "../layout/AppSidebar";
import Backdrop from "../layout/Backdrop";
import { useAppSelector } from "../store/hooks";
import MacTopBar from "../layout/MacTopBar";
import MacWindowChrome from "../layout/MacWindowChrome";
import { useWindowManager } from "../context/WindowManagerContext";
import { PageRoutes } from "./Routes";
import { resolveWindowElement } from "./protectedRoutesConfig";
import NotFoundPage from "../pages/NotFoundPage";
import LoadingSpinner from "@/components/common/LoadingSpinner";
import ZoneTooltip from "@/components/common/ZoneTooltip";
import { fetchBootstrap } from "@/store/slices/companySlice";
import { useDispatch } from "react-redux";
import type { AppDispatch } from "@/store";

const titleMap: Array<{ prefix: string; title: string }> = [
  { prefix: PageRoutes.dashboard, title: 'Dashboard' },
  { prefix: '/kanban', title: 'Kanban Board' },
  { prefix: '/core/contact', title: 'Contacts' },
  { prefix: '/core/report', title: 'Reports' },
  { prefix: '/core/setting', title: 'Settings' },
  { prefix: '/core/template', title: 'Templates' },
  { prefix: '/core/actions', title: 'Actions' },
  { prefix: '/accounts', title: 'Accounts' },
  { prefix: '/communications', title: 'Communications' },
  { prefix: '/docs', title: 'Docs' },
  { prefix: '/org', title: 'Organizations' },
  { prefix: '/products', title: 'Products' },
  { prefix: '/transactions', title: 'Transactions' },
  { prefix: '/databrowser', title: 'databrowser' },
  { prefix: '/admin-wb', title: 'databrowser' },
  { prefix: '/whitelist', title: 'Whitelist Tester' },
];

const deriveTitle = (path: string) => {
  const match = titleMap.find((t) => path.startsWith(t.prefix));
  if (match) return match.title;
  return path === '/' ? 'Login' : path;
};

const AppLayout: React.FC = () => {
  const { isLoading, isAuthenticated } = useAppSelector((state) => state.auth);
  const { ensureWindow, windows, activePath, skipAutoCreateForPathRef } = useWindowManager();
  const { isExpanded, isHovered, isMobileOpen, isVisible, toggleVisibility } = useSidebar();
  const location = useLocation();
  const appDispatch = useDispatch<AppDispatch>();

  // Load company bootstrap on auth
  useEffect(() => {
    if (isAuthenticated) appDispatch(fetchBootstrap());
  }, [isAuthenticated, appDispatch]);

  useEffect(() => {
    // If ensureWindow was just called explicitly (e.g. from a panel Add button),
    // it already created the window. Skip to avoid a duplicate from the auto-create.
    if (skipAutoCreateForPathRef.current === location.pathname) {
      skipAutoCreateForPathRef.current = null;
      return;
    }
    ensureWindow(location.pathname, deriveTitle(location.pathname));
  }, [location.pathname, ensureWindow, skipAutoCreateForPathRef]);

  // Show loading while auth state is being determined
  if (isLoading) {
    return <div className="flex justify-center items-center h-screen"><LoadingSpinner size="lg" label="Loading..." /></div>;
  }

  // Redirect if not authenticated (rely on Redux state, not localStorage directly)
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  const sidebarWidth = isVisible
    ? (isExpanded || isHovered || isMobileOpen ? 200 : 52)
    : 0;

  return (
    <div className="relative min-h-screen" style={{ backgroundColor: 'var(--wc-bg)', color: 'var(--wc-text)' }}>
      <ZoneTooltip />
      <MacTopBar activePath={activePath || ""} />
      <div className="relative h-[calc(100vh-40px)]">
        <AppSidebar />
        <Backdrop />

        {!isVisible && (
          <button
            className="fixed left-1 top-[52px] z-180 rounded-r border border-l-0 p-1.5 transition-colors"
            style={{ borderColor: 'var(--wc-border)', backgroundColor: 'var(--wc-surface)', color: 'var(--wc-text-muted)' }}
            onClick={toggleVisibility}
            title="Show navigation"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18l6-6-6-6"/></svg>
          </button>
        )}

        <div
          className="absolute inset-0 overflow-auto"
          style={{ paddingLeft: `${sidebarWidth}px` }}
        >
          <div className="relative h-full w-full">
            {windows
              .filter((w) => !w.minimized)
              .map((w, idx) => (
                <div key={w.openedAt} className={w.path === activePath ? 'z-30' : 'z-10'}>
                  <MacWindowChrome
                    path={w.path}
                    title={deriveTitle(w.path)}
                    x={w.x ?? idx * 24}
                    y={w.y ?? idx * 24}
                    maximized={w.maximized}
                    isActive={w.path === activePath}
                  >
                    {resolveWindowElement(w.path) ?? <NotFoundPage />}
                  </MacWindowChrome>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
};

const PrivateRoute: React.FC = () => {
  const { isLoading, isAuthenticated } = useAppSelector((state) => state.auth);
  
  // Show loading while auth state is being initialized
  if (isLoading) {
    return <div className="flex justify-center items-center h-screen"><LoadingSpinner size="lg" label="Loading..." /></div>;
  }
  
  // Once loading is done, check authentication
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return (
    <SidebarProvider>
      <AppLayout />
    </SidebarProvider>
  );
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
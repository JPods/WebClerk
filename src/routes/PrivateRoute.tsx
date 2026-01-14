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

const titleMap: Array<{ prefix: string; title: string }> = [
  { prefix: PageRoutes.dashboard, title: 'Dashboard' },
  { prefix: '/kanban-board', title: 'Kanban Board' },
  { prefix: '/svar-gantt', title: 'SVAR Gantt' },
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
  { prefix: '/admin-wb', title: 'Admin Workbench' },
  { prefix: '/whitelist', title: 'Whitelist Tester' },
];

const deriveTitle = (path: string) => {
  const match = titleMap.find((t) => path.startsWith(t.prefix));
  if (match) return match.title;
  return path === '/' ? 'Login' : path;
};

const AppLayout: React.FC = () => {
  const { isLoading } = useAppSelector((state) => state.auth);
  const { ensureWindow, windows, activePath } = useWindowManager();
  const { isExpanded, isHovered, isMobileOpen, isVisible, toggleVisibility } = useSidebar();
  const location = useLocation();

  useEffect(() => {
    ensureWindow(location.pathname, deriveTitle(location.pathname));
  }, [location.pathname, ensureWindow]);

  if (isLoading) {
    return <div className="flex h-screen items-center justify-center text-white">Loading...</div>;
  }

  const getToken = localStorage.getItem("accessToken");
  if (!getToken) return <Navigate to="/" replace />;

  const sidebarWidth = isVisible
    ? (isExpanded || isHovered || isMobileOpen ? 290 : 90)
    : 0;

  return (
    <div className="relative min-h-screen bg-transparent text-slate-900">
      <MacTopBar activePath={activePath || ""} />
      <div className="relative h-[calc(100vh-60px)]">
        <AppSidebar />
        <Backdrop />

        {!isVisible && (
          <button
            className="fixed left-3 top-16 z-[180] rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-semibold text-slate-700 shadow-sm hover:border-slate-300 hover:bg-slate-50"
            onClick={toggleVisibility}
          >
            Show Nav
          </button>
        )}

        <div
          className="absolute inset-0 overflow-auto p-4 md:p-6"
          style={{ paddingLeft: `${sidebarWidth + 20}px` }}
        >
          <div className="relative h-full w-full">
            {windows
              .filter((w) => !w.minimized)
              .map((w, idx) => (
                <div key={w.path} className={w.path === activePath ? 'z-30' : 'z-10'}>
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
/* LastChecked: 2026-08-02 | WhereUsed: App root | WhoCreated: Claude */
import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { WindowManagerNavigationSync } from "../context/WindowManagerContext";
import { DataSetBadge } from '../components/DataSetBadge';
import { DevTools } from '../components/DevTools';
import { AiHelpWidget } from '../components/AiHelpWidget';
import { IssueReporter } from '../components/IssueReporter';
import PrivateRoute from "./PrivateRoute";
import { ScrollToTop, Toster } from "../components/wrapper";
import { SignIn, SignUp, UserProfiles } from "../pages/wrapperPage";
import DataBrowser from "../pages/admin/DataBrowser";
import NotFoundPage from "../pages/NotFoundPage";
import DDCardDashboard from "../pages/Dashboard/DDCardDashboard";

const PortalDashboard = React.lazy(() => import("../pages/Dashboard/PortalDashboard"));
const UiDetail = React.lazy(() => import("../apps/transactions/components/TransactionDetail"));
const ShoppingCart = React.lazy(() => import("../apps/transactions/components/ShoppingCart"));
const AliceDashboard = React.lazy(() => import("../pages/admin/AliceDashboard"));
const AdminTools = React.lazy(() => import("../pages/admin/AdminTools"));
const HelpDashboard = React.lazy(() => import("../pages/admin/HelpDashboard"));
const InventoryDashboard = React.lazy(() => import("../pages/admin/InventoryDashboard"));
const ModelDetailPage = React.lazy(() => import("../components/common/ModelDetailPage"));
const KanbanBoardPage = React.lazy(() => import("../apps/utils/kanban/KanbanBoardPage"));
const UnifiedGanttPage = React.lazy(() => import("../apps/utils/gantt/UnifiedGanttPage"));
const JsonTreeApplet = React.lazy(() => import("../pages/tools/JsonTreeApplet"));
const JsonSchemaReference = React.lazy(() => import("../pages/tools/JsonSchemaReference"));
const InventoryAdjust = React.lazy(() => import("../apps/products/pages/InventoryAdjust"));
const CycleCountMobile = React.lazy(() => import("../apps/products/pages/CycleCountMobile"));
const CustomPageLoader = React.lazy(() => import("./CustomPageLoader"));
const TokenBuilderPage = React.lazy(() => import("./TokenBuilderPage"));
const FlightSimConsole = React.lazy(() => import("../pages/admin/FlightSimConsole"));
const Onboarding = React.lazy(() => import("../pages/Onboarding"));

// Print pages archived 2026-08-06 — all printing now via pdfme report templates

const S: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <React.Suspense fallback={<div style={{padding:40}}>Loading...</div>}>{children}</React.Suspense>
);

/** Redirect portal users to /portal, employees to /dashboard */
const HomeRedirect: React.FC = () => {
  // Read from localStorage to avoid flash — Redux may still be loading
  try {
    const raw = localStorage.getItem('userProfile');
    if (raw) {
      const u = JSON.parse(raw);
      if (u.is_portal) return <Navigate to="/portal" replace />;
    }
  } catch { /* ignore */ }
  return <Navigate to="/dashboard" replace />;
};

// Transaction models — use UiDetail
const TRANSACTION_MODELS = [
  'order', 'invoice', 'proposal', 'purchase', 'workorder',
  'receipt', 'requisition', 'payment',
];

/** Floating widgets — hidden on public tool pages (e.g. /json-tree) */
const FloatingWidgets: React.FC = () => {
  const { pathname } = useLocation();
  if (pathname.startsWith('/json-tree')) return null;
  return <>
    <DataSetBadge position="bottom-right" showDetails />
    <DevTools position="bottom-left" />
    <AiHelpWidget position="bottom-right" />
    <IssueReporter />
  </>;
};

const Router: React.FC = () => {
  return (
    <BrowserRouter basename={import.meta.env.VITE_BASE_PATH || '/'}>
      <WindowManagerNavigationSync />
      <ScrollToTop />
      <Toster />
      <FloatingWidgets />
      <Routes>
        {/* Public */}
        <Route path="/login" element={<SignIn />} />
        <Route path="/signin" element={<SignIn />} />
        <Route path="/register" element={<SignUp />} />
        <Route path="/cart" element={<S><ShoppingCart items={[]} onUpdateQuantity={() => {}} onRemoveItem={() => {}} onCheckout={() => {}} onContinueShopping={() => {}} /></S>} />
        <Route path="/json-tree" element={<S><JsonTreeApplet /></S>} />
        <Route path="/json-schema" element={<S><JsonSchemaReference /></S>} />
        <Route path="/setup" element={<S><Onboarding /></S>} />

        {/* Protected */}
        <Route element={<PrivateRoute />}>
          <Route index element={<HomeRedirect />} />
          <Route path="dashboard" element={<DDCardDashboard dashboardName="sales" />} />
          <Route path="portal" element={<S><PortalDashboard /></S>} />
          <Route path="browser" element={<DataBrowser />} />
          <Route path="profile" element={<UserProfiles />} />
          <Route path="alice-dashboard" element={<S><AliceDashboard /></S>} />
          <Route path="admin-tools" element={<S><AdminTools /></S>} />
          <Route path="help" element={<S><HelpDashboard /></S>} />
          <Route path="products" element={<DDCardDashboard dashboardName="products" />} />
          <Route path="orgs" element={<DDCardDashboard dashboardName="orgs" />} />
          <Route path="transactions" element={<DDCardDashboard dashboardName="transactions" />} />
          <Route path="operations" element={<DDCardDashboard dashboardName="operations" />} />
          <Route path="administration" element={<DDCardDashboard dashboardName="operations" />} />
          <Route path="accounting" element={<DDCardDashboard dashboardName="accounting" />} />
          <Route path="inventory-dashboard" element={<S><InventoryDashboard /></S>} />
          <Route path="inventory-adjust" element={<S><InventoryAdjust /></S>} />
          <Route path="cycle-count" element={<S><CycleCountMobile /></S>} />
          {/* page-designer removed — grapesjs dependency eliminated */}
          <Route path="databrowser" element={<DataBrowser />} />
          <Route path="admin-wb" element={<Navigate to="/databrowser" replace />} />
          <Route path="kanban" element={<S><KanbanBoardPage /></S>} />
          <Route path="gantt" element={<S><UnifiedGanttPage /></S>} />
          <Route path="flight-simulator" element={<S><FlightSimConsole /></S>} />
          <Route path="flight-sim" element={<S><FlightSimConsole /></S>} />
          <Route path="flight-sim/inventory" element={<S><FlightSimConsole /></S>} />

          {/* Legacy /db/ routes — keep working for bookmarks */}
          <Route path="db/:model" element={<DataBrowser />} />

          {/* /:model = list, /:model/:id = record */}
          {TRANSACTION_MODELS.map(m => <Route key={`${m}-id`} path={`${m}/:id`} element={<S><UiDetail modelName={m} /></S>} />)}
          {['contact', 'item', 'customer', 'vendor', 'manufacturer', 'employee', 'rep', 'action', 'touch'].map(m =>
            <Route key={`${m}-id`} path={`${m}/:id`} element={<S><ModelDetailPage modelName={m} /></S>} />
          )}
          {/* /td/:model/:id — alternate record route */}
          <Route path="td/:model/:id" element={<S><UiDetail /></S>} />

          {/* Token builder — {{field.path}} clipboard tool */}
          <Route path="tokens" element={<TokenBuilderPage />} />
          <Route path="tokens/:model" element={<TokenBuilderPage />} />

          {/* Custom user pages — registered via Report records */}
          <Route path="custom/:page" element={<S><CustomPageLoader /></S>} />

          {/* /:model — any model name → DataBrowser list */}
          <Route path=":model" element={<DataBrowser />} />
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
};

export default Router;

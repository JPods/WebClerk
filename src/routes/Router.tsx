/* LastChecked: 2026-08-02 | WhereUsed: App root | WhoCreated: Claude */
import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { WindowManagerNavigationSync } from "../context/WindowManagerContext";
import { DataSetBadge } from '../components/DataSetBadge';
import { DevTools } from '../components/DevTools';
import { AiHelpWidget } from '../components/AiHelpWidget';
import { UserIssueReporter } from '../components/UserIssueReporter';
import { DevIssueReporter } from '../components/DevIssueReporter';
import PrivateRoute from "./PrivateRoute";
import { ScrollToTop, Toster } from "../components/wrapper";
import { SignIn, SignUp, UserProfiles } from "../pages/wrapperPage";
import DataBrowser from "../pages/admin/DataBrowser";
import NotFoundPage from "../pages/NotFoundPage";
import DDCardDashboard from "../pages/Dashboard/DDCardDashboard";

const UiDetail = React.lazy(() => import("../apps/transactions/components/TransactionDetail"));
const ShoppingCart = React.lazy(() => import("../apps/transactions/components/ShoppingCart"));
const AliceDashboard = React.lazy(() => import("../pages/admin/AliceDashboard"));
const HelpDashboard = React.lazy(() => import("../pages/admin/HelpDashboard"));
const InventoryDashboard = React.lazy(() => import("../pages/admin/InventoryDashboard"));
const ContactDetailJson = React.lazy(() => import("../apps/core/models/contact/pages/ContactDetailJson"));
const OrgDetailJson = React.lazy(() => import("../apps/orgs/components/OrgDetail.json"));
const ItemDetailJson = React.lazy(() => import("../apps/products/pages/ItemDetailJson"));
const KanbanBoardPage = React.lazy(() => import("../apps/utils/kanban/KanbanBoardPage"));
const UnifiedGanttPage = React.lazy(() => import("../apps/utils/gantt/UnifiedGanttPage"));
const JsonTreeApplet = React.lazy(() => import("../pages/tools/JsonTreeApplet"));
const InventoryAdjust = React.lazy(() => import("../apps/products/pages/InventoryAdjust"));
const CycleCountMobile = React.lazy(() => import("../apps/products/pages/CycleCountMobile"));
const CustomPageLoader = React.lazy(() => import("./CustomPageLoader"));
const TokenBuilderPage = React.lazy(() => import("./TokenBuilderPage"));
const FlightSimConsole = React.lazy(() => import("../pages/admin/FlightSimConsole"));

// Print pages archived 2026-08-06 — all printing now via pdfme report templates

const S: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <React.Suspense fallback={<div style={{padding:40}}>Loading...</div>}>{children}</React.Suspense>
);

// Transaction models — use UiDetail
const TRANSACTION_MODELS = [
  'order', 'invoice', 'proposal', 'purchase', 'work_order', 'workorder',
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
    <UserIssueReporter />
    <DevIssueReporter />
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

        {/* Protected */}
        <Route element={<PrivateRoute />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DDCardDashboard dashboardName="sales" />} />
          <Route path="browser" element={<DataBrowser />} />
          <Route path="profile" element={<UserProfiles />} />
          <Route path="alice-dashboard" element={<S><AliceDashboard /></S>} />
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
          <Route path="flight-sim" element={<S><FlightSimConsole /></S>} />
          <Route path="flight-sim/inventory" element={<S><FlightSimConsole scenarioAction="get_flight_scenario" title="Flight Simulator: Transaction Lifecycle" description="Step through proposal → order → invoice → payment → purchase → receive and watch inventory, GL, and pending records change." /></S>} />

          {/* Legacy /db/ routes — keep working for bookmarks */}
          <Route path="db/:model" element={<DataBrowser />} />

          {/* /:model = list, /:model/:id = record */}
          {TRANSACTION_MODELS.map(m => <Route key={`${m}-id`} path={`${m}/:id`} element={<S><UiDetail modelName={m} /></S>} />)}
          <Route path="contact/:id" element={<S><ContactDetailJson /></S>} />
          <Route path="item/:id" element={<S><ItemDetailJson /></S>} />
          {['customer', 'vendor', 'manufacturer', 'employee', 'rep'].map(m =>
            <Route key={`${m}-id`} path={`${m}/:id`} element={<S><OrgDetailJson modelName={m} /></S>} />
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

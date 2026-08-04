/* LastChecked: 2026-08-02 | WhereUsed: App root | WhoCreated: Claude */
import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { WindowManagerNavigationSync } from "../context/WindowManagerContext";
import PrivateRoute from "./PrivateRoute";
import { ScrollToTop, Toster } from "../components/wrapper";
import { SignIn, SignUp, Home, UserProfiles } from "../pages/wrapperPage";
import AdminWorkbench from "../pages/admin/AdminWorkbench";
import NotFoundPage from "../pages/NotFoundPage";

const TransactionDetail = React.lazy(() => import("../apps/transactions/components/TransactionDetail"));
const ShoppingCart = React.lazy(() => import("../apps/transactions/components/ShoppingCart"));
const AliceDashboard = React.lazy(() => import("../pages/admin/AliceDashboard"));
const HelpDashboard = React.lazy(() => import("../pages/admin/HelpDashboard"));
const AccountingDashboard = React.lazy(() => import("../pages/admin/AccountingDashboard"));
const InventoryDashboard = React.lazy(() => import("../pages/admin/InventoryDashboard"));
const PageDesigner = React.lazy(() => import("../pages/tools/PageDesigner"));
const ContactDetailJson = React.lazy(() => import("../apps/core/models/contact/pages/ContactDetailJson"));
const OrgDetailJson = React.lazy(() => import("../apps/orgs/components/OrgDetail.json"));
const ItemDetailJson = React.lazy(() => import("../apps/products/pages/ItemDetailJson"));
const KanbanBoardPage = React.lazy(() => import("../apps/utils/kanban/KanbanBoardPage"));
const UnifiedGanttPage = React.lazy(() => import("../apps/utils/gantt/UnifiedGanttPage"));

const S: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <React.Suspense fallback={<div style={{padding:40}}>Loading...</div>}>{children}</React.Suspense>
);

// Transaction models — use TransactionDetail
const TRANSACTION_MODELS = [
  'order', 'invoice', 'proposal', 'purchase', 'work_order', 'workorder',
  'receipt', 'requisition', 'payment',
];

// All models that get a list view (/:model → AdminWorkbench)
const ALL_LIST_MODELS = [
  ...TRANSACTION_MODELS,
  'contact', 'customer', 'vendor', 'manufacturer', 'employee', 'rep',
  'item', 'action', 'document', 'setting', 'report',
];

const Router: React.FC = () => {
  return (
    <BrowserRouter basename={import.meta.env.VITE_BASE_PATH || '/'}>
      <WindowManagerNavigationSync />
      <ScrollToTop />
      <Toster />
      <Routes>
        {/* Public */}
        <Route path="/login" element={<SignIn />} />
        <Route path="/signin" element={<SignIn />} />
        <Route path="/register" element={<SignUp />} />
        <Route path="/cart" element={<S><ShoppingCart items={[]} onUpdateQuantity={() => {}} onRemoveItem={() => {}} onCheckout={() => {}} onContinueShopping={() => {}} /></S>} />

        {/* Protected */}
        <Route element={<PrivateRoute />}>
          <Route index element={<Home />} />
          <Route path="dashboard" element={<Home />} />
          <Route path="profile" element={<UserProfiles />} />
          <Route path="alice-dashboard" element={<S><AliceDashboard /></S>} />
          <Route path="help" element={<S><HelpDashboard /></S>} />
          <Route path="accounting" element={<S><AccountingDashboard /></S>} />
          <Route path="inventory-dashboard" element={<S><InventoryDashboard /></S>} />
          <Route path="page-designer" element={<S><PageDesigner /></S>} />
          <Route path="admin-wb" element={<AdminWorkbench />} />
          <Route path="kanban" element={<S><KanbanBoardPage /></S>} />
          <Route path="gantt" element={<S><UnifiedGanttPage /></S>} />

          {/* Legacy /db/ routes — keep working */}
          <Route path="db/:model" element={<AdminWorkbench />} />

          {/* /:model = list, /:model/:id = record */}
          {TRANSACTION_MODELS.map(m => <Route key={`${m}-id`} path={`${m}/:id`} element={<S><TransactionDetail modelName={m} /></S>} />)}
          <Route path="contact/:id" element={<S><ContactDetailJson /></S>} />
          <Route path="item/:id" element={<S><ItemDetailJson /></S>} />
          {['customer', 'vendor', 'manufacturer', 'employee', 'rep'].map(m =>
            <Route key={`${m}-id`} path={`${m}/:id`} element={<S><OrgDetailJson modelName={m} /></S>} />
          )}
          {ALL_LIST_MODELS.map(m => <Route key={m} path={m} element={<AdminWorkbench />} />)}

          {/* /td/:model/:id — alternate record route */}
          <Route path="td/:model/:id" element={<S><TransactionDetail /></S>} />
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
};

export default Router;

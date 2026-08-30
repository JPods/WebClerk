/* LastChecked: 2026-08-30 | WhereUsed: WindowManager route resolution | WhoCreated: Unknown */
/* Routes for WindowManager — /:model catch-all renders databrowser */
/* IMPORTANT: Keep in sync with Router.tsx — both consume this table */
import React from "react";
import { Navigate } from "react-router";
import { PageRoutes } from "./Routes";
import {
  UserProfiles,
  NotionTrackerPage,
  KanbanBoardDataPage,
} from "../pages/wrapperPage";
import DataBrowser from "../pages/admin/DataBrowser";
import DDCardDashboard from "../pages/Dashboard/DDCardDashboard";
import Placeholder from "../pages/Placeholder";

// Lazy imports — match Router.tsx to preserve code splitting
const UiDetail = React.lazy(() => import("../apps/transactions/components/TransactionDetail"));
const ModelDetailPage = React.lazy(() => import("../components/common/ModelDetailPage"));
const PortalDashboard = React.lazy(() => import("../pages/Dashboard/PortalDashboard"));
const AliceDashboard = React.lazy(() => import("../pages/admin/AliceDashboard"));
const AdminTools = React.lazy(() => import("../pages/admin/AdminTools"));
const HelpDashboard = React.lazy(() => import("../pages/admin/HelpDashboard"));
const InventoryDashboard = React.lazy(() => import("../pages/admin/InventoryDashboard"));
const FlightSimConsole = React.lazy(() => import("../pages/admin/FlightSimConsole"));
const InventoryAdjust = React.lazy(() => import("../apps/products/pages/InventoryAdjust"));
const CycleCountMobile = React.lazy(() => import("../apps/products/pages/CycleCountMobile"));
const CustomPageLoader = React.lazy(() => import("./CustomPageLoader"));
const TokenBuilderPage = React.lazy(() => import("./TokenBuilderPage"));
const JsonTreeApplet = React.lazy(() => import("../pages/tools/JsonTreeApplet"));
const JsonSchemaReference = React.lazy(() => import("../pages/tools/JsonSchemaReference"));
const KanbanBoardPage_Lazy = React.lazy(() => import("../apps/utils/kanban/KanbanBoardPage"));
const UnifiedGanttPage_Lazy = React.lazy(() => import("../apps/utils/gantt/UnifiedGanttPage"));

// Static imports — lightweight or always-needed
import JsonViewer from "../pages/admin/JsonViewer";
import CommerceDashboard from "../pages/admin/CommerceDashboard";
import AliceTraining from "../pages/admin/AliceTraining";
import TeamDashboard from "../pages/admin/TeamDashboard";
import WhitelistTester from "../pages/tools/WhitelistTester";
import FormParade from "../pages/tools/FormParade";
import SettingParade from "../pages/tools/SettingParade";
import SelectListBrowser from "../pages/tools/SelectListBrowser";
import AgendaView from "../pages/admin/AgendaView";
import ApplyPayments from "../apps/transactions/pages/ApplyPayments";
import AllModelsWorkbench from "../apps/utils/scaffold/AllModelsWorkbench";
import TestDashboard from "../pages/admin/TestDashboard";
const ReportDesigner = React.lazy(() => import("../pages/admin/ReportDesigner"));
import ParadeOfReportsPage from "../pages/admin/ParadeOfReportsPage";
import ActionDailyDashboard from "../apps/common/components/panels/ActionDailyDashboard";

const S: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <React.Suspense fallback={<div style={{padding:40}}>Loading...</div>}>{children}</React.Suspense>
);

export const protectedRoutesConfig = [
  { path: "/", element: <DDCardDashboard dashboardName="sales" /> },
  { path: PageRoutes.dashboard, element: <DDCardDashboard dashboardName="sales" /> },
  { path: "/portal", element: <S><PortalDashboard /></S> },
  { path: PageRoutes.profile, element: <UserProfiles /> },

  // User-facing: Contact
  { path: PageRoutes.coreContactList, element: <Navigate to="/contact" replace /> },
  { path: PageRoutes.coreContactDetail, element: <S><ModelDetailPage modelName="contact" /></S> },

  // User-facing: Customer
  { path: "/org/customer", element: <Navigate to="/customer" replace /> },
  { path: "/org/vendor", element: <Navigate to="/vendor" replace /> },
  { path: "/org/employee", element: <Navigate to="/employee" replace /> },
  { path: "/org/rep", element: <Navigate to="/rep" replace /> },
  { path: "/org/manufacturer", element: <Navigate to="/manufacturer" replace /> },
  { path: PageRoutes.customerList, element: <Navigate to="/customer" replace /> },
  { path: `${PageRoutes.customerDetail}/:id`, element: <S><ModelDetailPage modelName="customer" /></S> },
  { path: PageRoutes.customerAdd, element: <S><ModelDetailPage modelName="customer" /></S> },
  { path: `${PageRoutes.customerEdit}/:id`, element: <S><ModelDetailPage modelName="customer" /></S> },

  // User-facing: Actions
  { path: PageRoutes.actionList, element: <Navigate to="/action" replace /> },
  { path: PageRoutes.actionDetail, element: <Navigate to="/action" replace /> },

  // User-facing: Documents
  { path: PageRoutes.docs, element: <Placeholder title="Documents" /> },

  // User-facing: Products — app dashboard, lists via DataBrowser, detail via custom page
  { path: "/products", element: <DDCardDashboard dashboardName="products" /> },
  { path: PageRoutes.products, element: <Navigate to="/products" replace /> },
  { path: PageRoutes.productsItemList, element: <Navigate to="/item" replace /> },
  { path: PageRoutes.productsItemDetail, element: <S><ModelDetailPage modelName="item" /></S> },
  { path: "/item/:id", element: <S><ModelDetailPage modelName="item" /></S> },

  // User-facing: Transactions — app dashboard
  { path: "/transactions", element: <DDCardDashboard dashboardName="transactions" /> },

  // User-facing: Orgs — app dashboard
  { path: "/orgs", element: <DDCardDashboard dashboardName="orgs" /> },

  // User-facing: Operations — unified Accounting + Support + Sync
  { path: "/operations", element: <DDCardDashboard dashboardName="operations" /> },
  { path: "/administration", element: <DDCardDashboard dashboardName="operations" /> },
  { path: "/sync", element: <Navigate to="/operations?tab=sync" replace /> },
  { path: "/support", element: <Navigate to="/operations?tab=support" replace /> },
  { path: "/accounting", element: <DDCardDashboard dashboardName="accounting" /> },

  // User-facing: Transactions — lists via DataBrowser, details via custom pages
  { path: PageRoutes.transactionsProposalList, element: <Navigate to="/proposal" replace /> },
  { path: PageRoutes.transactionsProposalDetail, element: <S><UiDetail modelName="proposal" /></S> },
  { path: PageRoutes.transactionsOrderList, element: <Navigate to="/order" replace /> },
  { path: PageRoutes.transactionsOrderDetail, element: <S><UiDetail modelName="order" /></S> },
  { path: PageRoutes.transactionsInvoiceList, element: <Navigate to="/invoice" replace /> },
  { path: PageRoutes.transactionsInvoiceDetail, element: <S><UiDetail modelName="invoice" /></S> },
  { path: PageRoutes.transactionsApplyPayments, element: <ApplyPayments /> },
  { path: PageRoutes.transactionsPaymentList, element: <Navigate to="/payment" replace /> },
  { path: PageRoutes.transactionsPaymentDetail, element: <S><UiDetail modelName="payment" /></S> },
  { path: PageRoutes.transactionsPurchaseList, element: <Navigate to="/purchase" replace /> },
  { path: PageRoutes.transactionsPurchaseDetail, element: <S><UiDetail modelName="purchase" /></S> },
  { path: PageRoutes.transactionsWorkOrderList, element: <Navigate to="/workorder" replace /> },
  { path: PageRoutes.transactionsWorkOrderDetail, element: <S><UiDetail modelName="workorder" /></S> },
  { path: PageRoutes.transactionsReceiptList, element: <Navigate to="/receipt" replace /> },
  { path: PageRoutes.transactionsReceiptDetail, element: <S><UiDetail modelName="receipt" /></S> },
  { path: PageRoutes.transactionsAdjustmentList, element: <Navigate to="/inventory-dashboard" replace /> },

  // Tools
  { path: PageRoutes.notionTracker, element: <NotionTrackerPage /> },
  { path: PageRoutes.kanbanBoard, element: <S><KanbanBoardPage_Lazy /></S> },
  { path: PageRoutes.kanbanBoardData, element: <KanbanBoardDataPage /> },
  { path: PageRoutes.gantt, element: <S><UnifiedGanttPage_Lazy /></S> },
  { path: PageRoutes.kanbanGantt, element: <Navigate to="/gantt" replace /> },
  { path: PageRoutes.svarGantt, element: <Navigate to="/gantt" replace /> },
  { path: PageRoutes.multiProjectGantt, element: <Navigate to="/gantt" replace /> },

  // Inventory tools — must be before /:model catch-all
  { path: "/inventory-adjust", element: <S><InventoryAdjust /></S> },
  { path: "/cycle-count", element: <S><CycleCountMobile /></S> },

  // Token builder
  { path: "/tokens", element: <S><TokenBuilderPage /></S> },
  { path: "/tokens/:model", element: <S><TokenBuilderPage /></S> },

  // Custom user pages
  { path: "/custom/:page", element: <S><CustomPageLoader /></S> },

  // Legacy /db/ routes
  { path: "/db/:model", element: <DataBrowser /> },

  // /:model/:id = record detail pages
  { path: "/order/:id", element: <S><UiDetail modelName="order" /></S> },
  { path: "/invoice/:id", element: <S><UiDetail modelName="invoice" /></S> },
  { path: "/proposal/:id", element: <S><UiDetail modelName="proposal" /></S> },
  { path: "/purchase/:id", element: <S><UiDetail modelName="purchase" /></S> },
  { path: "/workorder/:id", element: <S><UiDetail modelName="workorder" /></S> },
  { path: "/receipt/:id", element: <S><UiDetail modelName="receipt" /></S> },
  { path: "/requisition/:id", element: <S><UiDetail modelName="requisition" /></S> },
  { path: "/payment/:id", element: <S><UiDetail modelName="payment" /></S> },
  { path: "/contact/:id", element: <S><ModelDetailPage modelName="contact" /></S> },
  { path: "/customer/:id", element: <S><ModelDetailPage modelName="customer" /></S> },
  { path: "/vendor/:id", element: <S><ModelDetailPage modelName="vendor" /></S> },
  { path: "/manufacturer/:id", element: <S><ModelDetailPage modelName="manufacturer" /></S> },
  { path: "/employee/:id", element: <S><ModelDetailPage modelName="employee" /></S> },
  { path: "/rep/:id", element: <S><ModelDetailPage modelName="rep" /></S> },
  // /td/:model/:id — alternate record route
  { path: "/td/:model/:id", element: <S><UiDetail /></S> },

  // Report Parade — onboarding tool, walks through reports with sample data
  { path: "/parade", element: <ParadeOfReportsPage /> },

  // Admin tools — must be before /:model catch-all
  { path: PageRoutes.adminWorkbench, element: <DataBrowser /> },
  { path: PageRoutes.jsonViewer, element: <JsonViewer /> },
  { path: PageRoutes.commerceDashboard, element: <CommerceDashboard /> },
  { path: PageRoutes.aliceTraining, element: <AliceTraining /> },
  { path: PageRoutes.flightSimulator, element: <S><FlightSimConsole /></S> },
  { path: PageRoutes.flightSim, element: <S><FlightSimConsole /></S> },
  { path: PageRoutes.flightSimInventory, element: <S><FlightSimConsole /></S> },
  { path: PageRoutes.modelWorkbench, element: <AllModelsWorkbench /> },
  { path: PageRoutes.whitelist, element: <WhitelistTester /> },
  { path: PageRoutes.formParade, element: <FormParade /> },
  { path: PageRoutes.settingParade, element: <SettingParade /> },
  { path: PageRoutes.selectLists, element: <SelectListBrowser /> },
  { path: PageRoutes.agenda, element: <AgendaView /> },
  { path: "/json-tree", element: <S><JsonTreeApplet /></S> },
  { path: "/json-schema", element: <S><JsonSchemaReference /></S> },
  { path: "/alice-dashboard", element: <S><AliceDashboard /></S> },
  { path: "/admin-tools", element: <S><AdminTools /></S> },
  { path: "/help", element: <S><HelpDashboard /></S> },
  { path: "/test-dashboard", element: <TestDashboard /> },
  { path: "/report-designer", element: <S><ReportDesigner /></S> },
  { path: "/inventory-dashboard", element: <S><InventoryDashboard /></S> },
  { path: "/action-dashboard", element: <ActionDailyDashboard /> },
  { path: "/submit-bonus", element: <Placeholder title="Submit for Bonus" /> },
  { path: PageRoutes.coreApiLogList, element: <Navigate to="/apilog" replace /> },
  { path: PageRoutes.coreUserActivityDashboard, element: <Navigate to="/agenda" replace /> },
  { path: PageRoutes.coreTeamDashboard, element: <TeamDashboard /> },

  // Placeholders
  { path: "/core/audit/list", element: <Placeholder title="Core Audit" /> },
  { path: "/core/notification/list", element: <Placeholder title="Notifications" /> },
  { path: "/core/pending/list", element: <Placeholder title="Pending Items" /> },

  // /:model catch-all — MUST be last, any model renders databrowser
  { path: "/:model", element: <DataBrowser /> },
];

export const resolveWindowElement = (path: string) => {
  const cleanPath = path.split("?")[0];
  // Check exact paths first, then parameterized. Prevents /:model catch-all
  // from swallowing /alice-dashboard, /help, /test-dashboard, etc.
  const exact = protectedRoutesConfig.find((r) =>
    r.path && !r.path.includes(":") && r.path === cleanPath
  );
  if (exact) return exact.element;
  const paramMatch = protectedRoutesConfig.find((r) => {
    if (!r.path?.includes(":")) return false;
    const base = r.path.split(":")[0];
    return cleanPath.startsWith(base) && cleanPath.length > base.length;
  });
  return paramMatch?.element ?? null;
};

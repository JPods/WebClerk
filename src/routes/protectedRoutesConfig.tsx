/* LastChecked: 2026-08-06 | WhereUsed: WindowManager route resolution | WhoCreated: Unknown */
/* Routes for WindowManager — /:model catch-all renders databrowser */
import React from "react";
import { Navigate } from "react-router";
import { PageRoutes } from "./Routes";
import {
  CustomerDetailPage,
  CustomerAddPage,
  CustomerEditPage,
  KanbanBoardDataPage,
  KanbanBoardPage,
  NotionTrackerPage,
  UnifiedGanttPage,
  UserProfiles,
  CoreContactDetail,
} from "../pages/wrapperPage";
import DataBrowser from "../pages/admin/DataBrowser";
import JsonViewer from "../pages/admin/JsonViewer";
import CommerceDashboard from "../pages/admin/CommerceDashboard";
import AliceTraining from "../pages/admin/AliceTraining";
import FlightSimConsole from "../pages/admin/FlightSimConsole";
import UserActivityDashboard from "../pages/admin/UserActivityDashboard";
import TeamDashboard from "../pages/admin/TeamDashboard";
import WhitelistTester from "../pages/tools/WhitelistTester";
import FormParade from "../pages/tools/FormParade";
import SelectListBrowser from "../pages/tools/SelectListBrowser";
import JsonTreeApplet from "../pages/tools/JsonTreeApplet";
import ItemDetailJson from "../apps/products/pages/ItemDetailJson";
import DDCardDashboard from "../pages/Dashboard/DDCardDashboard";
// All model-specific detail pages replaced by UiDetail / OrgDetailJson / ItemDetailJson
// Old imports archived to src/archive/replaced-2026-08-03/
import ApplyPayments from "../apps/transactions/pages/ApplyPayments";
import AllModelsWorkbench from "../apps/utils/scaffold/AllModelsWorkbench";
import AliceDashboard from "../pages/admin/AliceDashboard";
import HelpDashboard from "../pages/admin/HelpDashboard";
import TestDashboard from "../pages/admin/TestDashboard";
import ReportDesigner from "../pages/admin/ReportDesigner";
import ParadeOfReportsPage from "../pages/admin/ParadeOfReportsPage";
import InventoryDashboard from "../pages/admin/InventoryDashboard";
import ActionDailyDashboard from "../apps/common/components/panels/ActionDailyDashboard";
import Placeholder from "../pages/Placeholder";
import UiDetail from "../apps/transactions/components/TransactionDetail";
import OrgDetailJson from "../apps/orgs/components/OrgDetail.json";

export const protectedRoutesConfig = [
  { path: "/", element: <DDCardDashboard dashboardName="sales" /> },
  { path: PageRoutes.dashboard, element: <DDCardDashboard dashboardName="sales" /> },
  { path: PageRoutes.profile, element: <UserProfiles /> },

  // User-facing: Contact
  { path: PageRoutes.coreContactList, element: <Navigate to="/contact" replace /> },
  { path: PageRoutes.coreContactDetail, element: <CoreContactDetail /> },

  // User-facing: Customer
  { path: "/org/customer", element: <Navigate to="/customer" replace /> },
  { path: "/org/vendor", element: <Navigate to="/vendor" replace /> },
  { path: "/org/employee", element: <Navigate to="/employee" replace /> },
  { path: "/org/rep", element: <Navigate to="/rep" replace /> },
  { path: "/org/manufacturer", element: <Navigate to="/manufacturer" replace /> },
  { path: PageRoutes.customerList, element: <Navigate to="/customer" replace /> },
  { path: `${PageRoutes.customerDetail}/:id`, element: <CustomerDetailPage /> },
  { path: PageRoutes.customerAdd, element: <CustomerAddPage /> },
  { path: `${PageRoutes.customerEdit}/:id`, element: <CustomerEditPage /> },

  // User-facing: Actions
  { path: PageRoutes.actionList, element: <Navigate to="/action" replace /> },
  { path: PageRoutes.actionDetail, element: <Navigate to="/action" replace /> },

  // User-facing: Documents
  { path: PageRoutes.docs, element: <Placeholder title="Documents" /> },

  // User-facing: Products — app dashboard, lists via DataBrowser, detail via custom page
  { path: "/products", element: <DDCardDashboard dashboardName="products" /> },
  { path: PageRoutes.products, element: <Navigate to="/products" replace /> },
  { path: PageRoutes.productsItemList, element: <Navigate to="/item" replace /> },
  { path: PageRoutes.productsItemDetail, element: <ItemDetailJson /> },
  { path: "/item/:id", element: <ItemDetailJson /> },

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
  { path: PageRoutes.transactionsProposalDetail, element: <UiDetail modelName="proposal" /> },
  { path: PageRoutes.transactionsOrderList, element: <Navigate to="/order" replace /> },
  { path: PageRoutes.transactionsOrderDetail, element: <UiDetail modelName="order" /> },
  { path: PageRoutes.transactionsInvoiceList, element: <Navigate to="/invoice" replace /> },
  { path: PageRoutes.transactionsInvoiceDetail, element: <UiDetail modelName="invoice" /> },
  { path: PageRoutes.transactionsApplyPayments, element: <ApplyPayments /> },
  { path: PageRoutes.transactionsPaymentList, element: <Navigate to="/payment" replace /> },
  { path: PageRoutes.transactionsPaymentDetail, element: <UiDetail modelName="payment" /> },
  { path: PageRoutes.transactionsPurchaseList, element: <Navigate to="/purchase" replace /> },
  { path: PageRoutes.transactionsPurchaseDetail, element: <UiDetail modelName="purchase" /> },
  { path: PageRoutes.transactionsWorkOrderList, element: <Navigate to="/workorder" replace /> },
  { path: PageRoutes.transactionsWorkOrderDetail, element: <UiDetail modelName="workorder" /> },
  { path: PageRoutes.transactionsReceiptList, element: <Navigate to="/receipt" replace /> },
  { path: PageRoutes.transactionsReceiptDetail, element: <UiDetail modelName="receipt" /> },
  { path: PageRoutes.transactionsAdjustmentList, element: <Navigate to="/inventory-dashboard" replace /> },

  // Tools
  { path: PageRoutes.notionTracker, element: <NotionTrackerPage /> },
  { path: PageRoutes.kanbanBoard, element: <KanbanBoardPage /> },
  { path: PageRoutes.kanbanBoardData, element: <KanbanBoardDataPage /> },
  { path: PageRoutes.gantt, element: <UnifiedGanttPage /> },
  { path: PageRoutes.kanbanGantt, element: <Navigate to="/gantt" replace /> },
  { path: PageRoutes.svarGantt, element: <Navigate to="/gantt" replace /> },
  { path: PageRoutes.multiProjectGantt, element: <Navigate to="/gantt" replace /> },

  // /:model/:id = record detail pages
  { path: "/order/:id", element: <UiDetail modelName="order" /> },
  { path: "/invoice/:id", element: <UiDetail modelName="invoice" /> },
  { path: "/proposal/:id", element: <UiDetail modelName="proposal" /> },
  { path: "/purchase/:id", element: <UiDetail modelName="purchase" /> },
  { path: "/work_order/:id", element: <UiDetail modelName="work_order" /> },
  { path: "/receipt/:id", element: <UiDetail modelName="receipt" /> },
  { path: "/requisition/:id", element: <UiDetail modelName="requisition" /> },
  { path: "/payment/:id", element: <UiDetail modelName="payment" /> },
  { path: "/contact/:id", element: <CoreContactDetail /> },
  { path: "/customer/:id", element: <OrgDetailJson modelName="customer" /> },
  { path: "/vendor/:id", element: <OrgDetailJson modelName="vendor" /> },
  { path: "/manufacturer/:id", element: <OrgDetailJson modelName="manufacturer" /> },
  { path: "/employee/:id", element: <OrgDetailJson modelName="employee" /> },
  { path: "/rep/:id", element: <OrgDetailJson modelName="rep" /> },

  // Report Parade — onboarding tool, walks through reports with sample data
  { path: "/parade", element: <ParadeOfReportsPage /> },

  // /:model catch-all — any model renders databrowser
  { path: "/:model", element: <DataBrowser /> },

  // Admin tools
  { path: PageRoutes.adminWorkbench, element: <DataBrowser /> },
  { path: PageRoutes.jsonViewer, element: <JsonViewer /> },
  { path: PageRoutes.commerceDashboard, element: <CommerceDashboard /> },
  { path: PageRoutes.aliceTraining, element: <AliceTraining /> },
  { path: PageRoutes.flightSim, element: <FlightSimConsole /> },
  { path: PageRoutes.flightSimInventory, element: <FlightSimConsole scenarioAction="get_flight_scenario" title="Flight Simulator: Transaction Lifecycle" description="Step through proposal → order → invoice → payment → purchase → receive and watch inventory, GL, and pending records change." /> },
  { path: PageRoutes.modelWorkbench, element: <AllModelsWorkbench /> },
  { path: PageRoutes.whitelist, element: <WhitelistTester /> },
  { path: PageRoutes.formParade, element: <FormParade /> },
  { path: PageRoutes.selectLists, element: <SelectListBrowser /> },
  { path: "/json-tree", element: <JsonTreeApplet /> },
  { path: "/alice-dashboard", element: <AliceDashboard /> },
  { path: "/help", element: <HelpDashboard /> },
  { path: "/test-dashboard", element: <TestDashboard /> },
  { path: "/report-designer", element: <ReportDesigner /> },
  { path: "/inventory-dashboard", element: <InventoryDashboard /> },
  { path: "/action-dashboard", element: <ActionDailyDashboard /> },
  { path: "/submit-bonus", element: <Placeholder title="Submit for Bonus" /> },
  { path: PageRoutes.coreApiLogList, element: <Navigate to="/apilog" replace /> },
  { path: PageRoutes.coreUserActivityDashboard, element: <UserActivityDashboard /> },
  { path: PageRoutes.coreTeamDashboard, element: <TeamDashboard /> },

  // Placeholders
  { path: "/core/audit/list", element: <Placeholder title="Core Audit" /> },
  { path: "/core/notification/list", element: <Placeholder title="Notifications" /> },
  { path: "/core/pending/list", element: <Placeholder title="Pending Items" /> },
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

/* LastChecked: 2026-06-28 | WhereUsed: WindowManager route resolution | WhoCreated: Unknown */
/* Admin-managed models redirect to DataBrowser (/admin-wb?model=X) */
import React from "react";
import { Navigate } from "react-router";
import { PageRoutes } from "./Routes";
import {
  CustomerDetailPage,
  CustomerAddPage,
  CustomerEditPage,
  Home,
  KanbanBoardDataPage,
  KanbanBoardPage,
  NotionTrackerPage,
  UnifiedGanttPage,
  UserProfiles,
  CoreContactDetail,
} from "../pages/wrapperPage";
import AdminWorkbench from "../pages/admin/AdminWorkbench";
import JsonViewer from "../pages/admin/JsonViewer";
import CommerceDashboard from "../pages/admin/CommerceDashboard";
import AccountingDashboard from "../pages/admin/AccountingDashboard";
import AliceTraining from "../pages/admin/AliceTraining";
import DetailReview from "../pages/admin/DetailReview";
import UserActivityDashboard from "../pages/admin/UserActivityDashboard";
import TeamDashboard from "../pages/admin/TeamDashboard";
import WhitelistTester from "../pages/tools/WhitelistTester";
import ItemDetailJson from "../apps/products/pages/ItemDetailJson";
// OrderDetail replaced by TransactionDetail — import kept for compatibility
// import OrderDetail from "../apps/transactions/models/order/pages/OrderDetail";
import InvoiceDetail from "../apps/transactions/models/invoice/pages/InvoiceDetail";
import ApplyPayments from "../apps/transactions/pages/ApplyPayments";
import PaymentDetailPage from "../apps/transactions/models/payment/pages/PaymentDetailPage";
import PurchaseDetail from "../apps/transactions/models/purchase/pages/PurchaseDetail";
import ProposalDetail from "../apps/transactions/models/proposal/pages/ProposalDetail";
import WorkorderDetail from "../apps/transactions/models/workorder/pages/WorkorderDetail";
import ReceiptDetail from "../apps/transactions/models/receipt/pages/ReceiptDetail";
import ActionDetail from "../apps/core/models/action/pages/ActionDetail";
// VendorDetail replaced by OrgDetailJson
// import VendorDetail from "../apps/orgs/models/vendor/pages/VendorDetail";
import AllModelsWorkbench from "../apps/utils/scaffold/AllModelsWorkbench";
import AliceDashboard from "../pages/admin/AliceDashboard";
import HelpDashboard from "../pages/admin/HelpDashboard";
import TestDashboard from "../pages/admin/TestDashboard";
import ReportDesigner from "../pages/admin/ReportDesigner";
import InventoryDashboard from "../pages/admin/InventoryDashboard";
import Placeholder from "../pages/Placeholder";
import TransactionDetail from "../apps/transactions/components/TransactionDetail";
import OrgDetailJson from "../apps/orgs/components/OrgDetail.json";

export const protectedRoutesConfig = [
  { path: PageRoutes.dashboard, element: <Home /> },
  { path: PageRoutes.profile, element: <UserProfiles /> },

  // User-facing: Contact
  { path: PageRoutes.coreContactList, element: <Navigate to="/db/contact" replace /> },
  { path: PageRoutes.coreContactDetail, element: <CoreContactDetail /> },

  // User-facing: Customer
  { path: "/org/customer", element: <Navigate to="/db/customer" replace /> },
  { path: "/org/vendor", element: <Navigate to="/db/vendor" replace /> },
  { path: "/org/employee", element: <Navigate to="/db/employee" replace /> },
  { path: "/org/rep", element: <Navigate to="/db/rep" replace /> },
  { path: "/org/manufacturer", element: <Navigate to="/db/manufacturer" replace /> },
  { path: PageRoutes.customerList, element: <Navigate to="/db/customer" replace /> },
  { path: `${PageRoutes.customerDetail}/:id`, element: <CustomerDetailPage /> },
  { path: PageRoutes.customerAdd, element: <CustomerAddPage /> },
  { path: `${PageRoutes.customerEdit}/:id`, element: <CustomerEditPage /> },

  // User-facing: Actions
  { path: PageRoutes.actionList, element: <Navigate to="/db/action" replace /> },
  { path: PageRoutes.actionDetail, element: <ActionDetail /> },

  // User-facing: Documents
  { path: PageRoutes.docs, element: <Placeholder title="Documents" /> },

  // User-facing: Products — list via DataBrowser, detail via custom page
  { path: PageRoutes.products, element: <Navigate to="/db/item" replace /> },
  { path: PageRoutes.productsItemList, element: <Navigate to="/db/item" replace /> },
  { path: PageRoutes.productsItemDetail, element: <ItemDetailJson /> },
  { path: "/item/:id", element: <ItemDetailJson /> },

  // User-facing: Transactions — all lists via DataBrowser, details via custom pages
  { path: PageRoutes.transactionsProposalList, element: <Navigate to="/db/proposal" replace /> },
  { path: PageRoutes.transactionsProposalDetail, element: <ProposalDetail /> },
  { path: PageRoutes.transactionsOrderList, element: <Navigate to="/db/order" replace /> },
  { path: PageRoutes.transactionsOrderDetail, element: <TransactionDetail modelName="order" /> },
  { path: PageRoutes.transactionsInvoiceList, element: <Navigate to="/db/invoice" replace /> },
  { path: PageRoutes.transactionsInvoiceDetail, element: <InvoiceDetail /> },
  { path: PageRoutes.transactionsApplyPayments, element: <ApplyPayments /> },
  { path: PageRoutes.transactionsPaymentList, element: <Navigate to="/db/payment" replace /> },
  { path: PageRoutes.transactionsPaymentDetail, element: <PaymentDetailPage /> },
  { path: PageRoutes.transactionsPurchaseList, element: <Navigate to="/db/purchase" replace /> },
  { path: PageRoutes.transactionsPurchaseDetail, element: <PurchaseDetail /> },
  { path: PageRoutes.transactionsWorkOrderList, element: <Navigate to="/db/workorder" replace /> },
  { path: PageRoutes.transactionsWorkOrderDetail, element: <WorkorderDetail /> },
  { path: PageRoutes.transactionsReceiptList, element: <Navigate to="/db/receipt" replace /> },
  { path: PageRoutes.transactionsReceiptDetail, element: <ReceiptDetail /> },
  { path: PageRoutes.transactionsAdjustmentList, element: <Navigate to="/inventory-dashboard" replace /> },

  // Tools
  { path: PageRoutes.notionTracker, element: <NotionTrackerPage /> },
  { path: PageRoutes.kanbanBoard, element: <KanbanBoardPage /> },
  { path: PageRoutes.kanbanBoardData, element: <KanbanBoardDataPage /> },
  { path: PageRoutes.gantt, element: <UnifiedGanttPage /> },
  { path: PageRoutes.kanbanGantt, element: <Navigate to="/gantt" replace /> },
  { path: PageRoutes.svarGantt, element: <Navigate to="/gantt" replace /> },
  { path: PageRoutes.multiProjectGantt, element: <Navigate to="/gantt" replace /> },

  // Clean URLs: /:model = list, /:model/:id = record
  { path: "/order", element: <AdminWorkbench /> },
  { path: "/order/:id", element: <TransactionDetail modelName="order" /> },
  { path: "/invoice", element: <AdminWorkbench /> },
  { path: "/invoice/:id", element: <TransactionDetail modelName="invoice" /> },
  { path: "/proposal", element: <AdminWorkbench /> },
  { path: "/proposal/:id", element: <TransactionDetail modelName="proposal" /> },
  { path: "/purchase", element: <AdminWorkbench /> },
  { path: "/purchase/:id", element: <TransactionDetail modelName="purchase" /> },
  { path: "/work_order", element: <AdminWorkbench /> },
  { path: "/work_order/:id", element: <TransactionDetail modelName="work_order" /> },
  { path: "/receipt", element: <AdminWorkbench /> },
  { path: "/receipt/:id", element: <TransactionDetail modelName="receipt" /> },
  { path: "/requisition", element: <AdminWorkbench /> },
  { path: "/requisition/:id", element: <TransactionDetail modelName="requisition" /> },
  { path: "/payment", element: <AdminWorkbench /> },
  { path: "/payment/:id", element: <TransactionDetail modelName="payment" /> },
  { path: "/contact", element: <AdminWorkbench /> },
  { path: "/contact/:id", element: <CoreContactDetail /> },
  { path: "/customer/:id", element: <OrgDetailJson modelName="customer" /> },
  { path: "/vendor/:id", element: <OrgDetailJson modelName="vendor" /> },
  { path: "/manufacturer/:id", element: <OrgDetailJson modelName="manufacturer" /> },
  { path: "/employee/:id", element: <OrgDetailJson modelName="employee" /> },
  { path: "/rep/:id", element: <OrgDetailJson modelName="rep" /> },
  { path: "/customer", element: <AdminWorkbench /> },
  { path: "/vendor", element: <AdminWorkbench /> },
  { path: "/item", element: <AdminWorkbench /> },
  { path: "/action", element: <AdminWorkbench /> },
  { path: "/document", element: <AdminWorkbench /> },
  { path: "/setting", element: <AdminWorkbench /> },

  // Admin tools
  { path: "/db/:model", element: <AdminWorkbench /> },
  { path: PageRoutes.adminWorkbench, element: <AdminWorkbench /> },
  { path: PageRoutes.jsonViewer, element: <JsonViewer /> },
  { path: PageRoutes.commerceDashboard, element: <CommerceDashboard /> },
  { path: PageRoutes.accountingDashboard, element: <AccountingDashboard /> },
  { path: PageRoutes.aliceTraining, element: <AliceTraining /> },
  { path: PageRoutes.detailReview, element: <DetailReview /> },
  { path: PageRoutes.modelWorkbench, element: <AllModelsWorkbench /> },
  { path: PageRoutes.whitelist, element: <WhitelistTester /> },
  { path: "/alice-dashboard", element: <AliceDashboard /> },
  { path: "/help", element: <HelpDashboard /> },
  { path: "/test-dashboard", element: <TestDashboard /> },
  { path: "/report-designer", element: <ReportDesigner /> },
  { path: "/inventory-dashboard", element: <InventoryDashboard /> },
  { path: "/submit-bonus", element: <Placeholder title="Submit for Bonus" /> },
  { path: PageRoutes.coreApiLogList, element: <Navigate to="/db/apilog" replace /> },
  { path: PageRoutes.coreUserActivityDashboard, element: <UserActivityDashboard /> },
  { path: PageRoutes.coreTeamDashboard, element: <TeamDashboard /> },

  // Admin model redirects → DataBrowser
  { path: PageRoutes.employeeList, element: <Navigate to="/db/orgs.Employee" replace /> },
  { path: PageRoutes.manufacturerList, element: <Navigate to="/db/orgs.Manufacturer" replace /> },
  { path: PageRoutes.organizationList, element: <Navigate to="/db/orgs.Organization" replace /> },
  { path: PageRoutes.repList, element: <Navigate to="/db/orgs.Rep" replace /> },
  { path: PageRoutes.vendorList, element: <Navigate to="/db/vendor" replace /> },
  { path: PageRoutes.coreSettingList, element: <Navigate to="/db/core.Setting" replace /> },
  { path: PageRoutes.coreSettingDetail, element: <Navigate to="/db/core.Setting" replace /> },
  { path: PageRoutes.coreReportList, element: <Navigate to="/db/core.Report" replace /> },
  { path: PageRoutes.coreReportDetail, element: <Navigate to="/db/core.Report" replace /> },
  { path: PageRoutes.coreTemplateList, element: <Navigate to="/db/core.Template" replace /> },
  { path: PageRoutes.coreTemplateDetail, element: <Navigate to="/db/core.Template" replace /> },
  { path: PageRoutes.commDomainList, element: <Navigate to="/db/communications.Domain" replace /> },
  { path: PageRoutes.commDomainDetail, element: <Navigate to="/db/communications.Domain" replace /> },
  { path: PageRoutes.commEmailList, element: <Navigate to="/db/communications.Email" replace /> },
  { path: PageRoutes.commEmailDetail, element: <Navigate to="/db/communications.Email" replace /> },
  { path: PageRoutes.commAddressList, element: <Navigate to="/db/communications.Address" replace /> },
  { path: PageRoutes.commAddressDetail, element: <Navigate to="/db/communications.Address" replace /> },
  { path: PageRoutes.commPhoneList, element: <Navigate to="/db/communications.Phone" replace /> },
  { path: PageRoutes.commPhoneDetail, element: <Navigate to="/db/communications.Phone" replace /> },
  { path: PageRoutes.documentList, element: <Navigate to="/db/docs.Document" replace /> },
  { path: PageRoutes.documentDetail, element: <Navigate to="/db/docs.Document" replace /> },
  { path: PageRoutes.questionAnswerList, element: <Navigate to="/db/docs.QuestionAnswer" replace /> },
  { path: PageRoutes.tagList, element: <Navigate to="/db/docs.Tag" replace /> },
  { path: PageRoutes.productsBillOfMaterialList, element: <Navigate to="/db/products.BillOfMaterial" replace /> },
  { path: PageRoutes.productsCatalogList, element: <Navigate to="/db/products.Catalog" replace /> },
  { path: PageRoutes.productsFlowList, element: <Navigate to="/db/products.Flow" replace /> },
  { path: PageRoutes.productsItemXrefList, element: <Navigate to="/db/products.ItemXref" replace /> },
  { path: PageRoutes.productsMatricsList, element: <Navigate to="/db/products.Matrics" replace /> },
  { path: PageRoutes.productsOrgItemList, element: <Navigate to="/db/products.OrgItem" replace /> },
  { path: PageRoutes.productsSerialList, element: <Navigate to="/db/products.Serial" replace /> },
  { path: PageRoutes.productsServiceList, element: <Navigate to="/db/products.Service" replace /> },
  { path: PageRoutes.productsSpecificationList, element: <Navigate to="/db/products.Specification" replace /> },
  { path: PageRoutes.productsUsageList, element: <Navigate to="/db/products.Usage" replace /> },
  { path: PageRoutes.productsVariantList, element: <Navigate to="/db/products.Variant" replace /> },
  { path: PageRoutes.productsWarehouseList, element: <Navigate to="/db/products.Warehouse" replace /> },
  { path: PageRoutes.auditList, element: <Navigate to="/db/accounts.Audit" replace /> },
  { path: PageRoutes.auditDetail, element: <Navigate to="/db/accounts.Audit" replace /> },
  { path: PageRoutes.currencyList, element: <Navigate to="/db/accounts.Currency" replace /> },
  { path: PageRoutes.currencyDetail, element: <Navigate to="/db/accounts.Currency" replace /> },
  { path: PageRoutes.exchangeRateList, element: <Navigate to="/db/accounts.ExchangeRate" replace /> },
  { path: PageRoutes.exchangeRateDetail, element: <Navigate to="/db/accounts.ExchangeRate" replace /> },
  { path: PageRoutes.exchangeTransactionList, element: <Navigate to="/db/accounts.ExchangeTransaction" replace /> },
  { path: PageRoutes.exchangeTransactionDetail, element: <Navigate to="/db/accounts.ExchangeTransaction" replace /> },
  { path: PageRoutes.glAccountList, element: <Navigate to="/db/accounts.GLAccount" replace /> },
  { path: PageRoutes.glAccountDetail, element: <Navigate to="/db/accounts.GLAccount" replace /> },
  { path: PageRoutes.glJournalList, element: <Navigate to="/db/accounts.GlJournal" replace /> },
  { path: PageRoutes.glJournalDetail, element: <Navigate to="/db/accounts.GlJournal" replace /> },
  { path: PageRoutes.ledgerList, element: <Navigate to="/db/accounts.Ledger" replace /> },
  { path: PageRoutes.tallySummaryList, element: <Navigate to="/db/accounts.TallySummary" replace /> },
  { path: PageRoutes.salesDimensionTallyList, element: <Navigate to="/db/accounts.SalesDimensionTally" replace /> },
  { path: PageRoutes.inventoryUsageTallyList, element: <Navigate to="/db/accounts.InventoryUsageTally" replace /> },
  { path: PageRoutes.tallyRegistryList, element: <Navigate to="/db/accounts.TallyRegistry" replace /> },
  { path: PageRoutes.taxJurisdictionList, element: <Navigate to="/db/accounts.TaxJurisdiction" replace /> },
  { path: PageRoutes.termList, element: <Navigate to="/db/accounts.Term" replace /> },

  // Placeholders
  { path: "/core/audit/list", element: <Placeholder title="Core Audit" /> },
  { path: "/core/notification/list", element: <Placeholder title="Notifications" /> },
  { path: "/core/pending/list", element: <Placeholder title="Pending Items" /> },
];

export const resolveWindowElement = (path: string) => {
  const cleanPath = path.split("?")[0];
  const match = protectedRoutesConfig.find((r) => {
    if (r.path?.includes(":")) {
      const base = r.path.split(":")[0];
      const baseNoSlash = base.endsWith("/") ? base.slice(0, -1) : base;
      return cleanPath === baseNoSlash || cleanPath.startsWith(base);
    }
    return r.path === cleanPath;
  });
  return match?.element ?? null;
};

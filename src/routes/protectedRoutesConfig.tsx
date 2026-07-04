/* LastChecked: 2026-06-28 | WhereUsed: WindowManager route resolution | WhoCreated: Unknown */
/* Admin-managed models redirect to DataBrowser (/admin-wb?model=X) */
import React from "react";
import { Navigate } from "react-router";
import { PageRoutes } from "./Routes";
import {
  CustomerList,
  CustomerDetailPage,
  CustomerAddPage,
  CustomerEditPage,
  Home,
  KanbanBoardDataPage,
  KanbanBoardPage,
  NotionTrackerPage,
  UnifiedGanttPage,
  UserProfiles,
  CoreContactList,
  CoreContactDetail,
} from "../pages/wrapperPage";
import AdminWorkbench from "../pages/admin/AdminWorkbench";
import JsonViewer from "../pages/admin/JsonViewer";
import AccountingDashboard from "../pages/admin/AccountingDashboard";
import AliceTraining from "../pages/admin/AliceTraining";
import DetailReview from "../pages/admin/DetailReview";
import UserActivityDashboard from "../pages/admin/UserActivityDashboard";
import TeamDashboard from "../pages/admin/TeamDashboard";
import WhitelistTester from "../pages/tools/WhitelistTester";
import ItemDetail from "../apps/products/models/item/pages/ItemDetail";
import ItemList from "../apps/products/models/item/pages/ItemList";
import OrderDetail from "../apps/transactions/models/order/pages/OrderDetail";
import InvoiceList from "../apps/transactions/models/invoice/pages/InvoiceList";
import InvoiceDetail from "../apps/transactions/models/invoice/pages/InvoiceDetail";
import ApplyPayments from "../apps/transactions/pages/ApplyPayments";
import PaymentListPage from "../apps/transactions/models/payment/pages/PaymentListPage";
import PaymentDetailPage from "../apps/transactions/models/payment/pages/PaymentDetailPage";
import PurchaseDetail from "../apps/transactions/models/purchase/pages/PurchaseDetail";
import ProposalDetail from "../apps/transactions/models/proposal/pages/ProposalDetail";
import ProposalList from "../apps/transactions/models/proposal/pages/ProposalList";
import PurchaseList from "../apps/transactions/models/purchase/pages/PurchaseList";
import OrderList from "../apps/transactions/models/order/pages/OrderList";
import WorkorderList from "../apps/transactions/models/workorder/pages/WorkorderList";
import WorkorderDetail from "../apps/transactions/models/workorder/pages/WorkorderDetail";
import ReceiptList from "../apps/transactions/models/receipt/pages/ReceiptList";
import ReceiptDetail from "../apps/transactions/models/receipt/pages/ReceiptDetail";
// DocumentIndex removed (qqq_) — docs route uses Placeholder until Document Dashboard is built
import ActionListPage from "../apps/core/models/action/pages/ActionList";
import ActionDetail from "../apps/core/models/action/pages/ActionDetail";
import APILogList from "../apps/core/models/api_log/pages/APILogList";
import AllModelsWorkbench from "../apps/utils/scaffold/AllModelsWorkbench";
import AliceDashboard from "../pages/admin/AliceDashboard";
import HelpDashboard from "../pages/admin/HelpDashboard";
import TestDashboard from "../pages/admin/TestDashboard";
import ReportDesigner from "../pages/admin/ReportDesigner";
import InventoryDashboard from "../pages/admin/InventoryDashboard";
import Placeholder from "../pages/Placeholder";

export const protectedRoutesConfig = [
  { path: PageRoutes.dashboard, element: <Home /> },
  { path: PageRoutes.profile, element: <UserProfiles /> },

  // User-facing: Contact
  { path: PageRoutes.coreContactList, element: <CoreContactList /> },
  { path: PageRoutes.coreContactDetail, element: <CoreContactDetail /> },

  // User-facing: Customer
  { path: "/org/customer", element: <Navigate to="/admin-wb?model=customer" replace /> },
  { path: "/org/vendor", element: <Navigate to="/admin-wb?model=vendor" replace /> },
  { path: "/org/employee", element: <Navigate to="/admin-wb?model=employee" replace /> },
  { path: "/org/rep", element: <Navigate to="/admin-wb?model=rep" replace /> },
  { path: "/org/manufacturer", element: <Navigate to="/admin-wb?model=manufacturer" replace /> },
  { path: PageRoutes.customerList, element: <CustomerList /> },
  { path: `${PageRoutes.customerDetail}/:id`, element: <CustomerDetailPage /> },
  { path: PageRoutes.customerAdd, element: <CustomerAddPage /> },
  { path: `${PageRoutes.customerEdit}/:id`, element: <CustomerEditPage /> },

  // User-facing: Actions
  { path: PageRoutes.actionList, element: <ActionListPage /> },
  { path: PageRoutes.actionDetail, element: <ActionDetail /> },

  // User-facing: Documents
  { path: PageRoutes.docs, element: <Placeholder title="Documents" /> },

  // User-facing: Products
  { path: PageRoutes.products, element: <Navigate to="/admin-wb?model=item" replace /> },
  { path: PageRoutes.productsItemList, element: <Navigate to="/admin-wb?model=item" replace /> },
  { path: PageRoutes.productsItemDetail, element: <ItemDetail /> },

  // User-facing: Transactions (lists → DataBrowser, details → custom pages)
  { path: PageRoutes.transactionsOrderList, element: <Navigate to="/admin-wb?model=order" replace /> },
  { path: PageRoutes.transactionsOrderDetail, element: <OrderDetail /> },
  { path: PageRoutes.transactionsInvoiceList, element: <Navigate to="/admin-wb?model=invoice" replace /> },
  { path: PageRoutes.transactionsInvoiceDetail, element: <InvoiceDetail /> },
  { path: PageRoutes.transactionsApplyPayments, element: <ApplyPayments /> },
  { path: PageRoutes.transactionsPaymentList, element: <Navigate to="/admin-wb?model=payment" replace /> },
  { path: PageRoutes.transactionsPaymentDetail, element: <PaymentDetailPage /> },
  { path: PageRoutes.transactionsPurchaseList, element: <Navigate to="/admin-wb?model=purchase" replace /> },
  { path: PageRoutes.transactionsPurchaseDetail, element: <PurchaseDetail /> },
  { path: PageRoutes.transactionsProposalList, element: <Navigate to="/admin-wb?model=proposal" replace /> },
  { path: PageRoutes.transactionsProposalDetail, element: <ProposalDetail /> },
  { path: PageRoutes.transactionsWorkOrderList, element: <Navigate to="/admin-wb?model=work_order" replace /> },
  { path: PageRoutes.transactionsWorkOrderDetail, element: <WorkorderDetail /> },
  { path: PageRoutes.transactionsReceiptList, element: <Navigate to="/admin-wb?model=receipt" replace /> },
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

  // Admin tools
  { path: PageRoutes.adminWorkbench, element: <AdminWorkbench /> },
  { path: PageRoutes.jsonViewer, element: <JsonViewer /> },
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
  { path: PageRoutes.coreApiLogList, element: <APILogList /> },
  { path: PageRoutes.coreUserActivityDashboard, element: <UserActivityDashboard /> },
  { path: PageRoutes.coreTeamDashboard, element: <TeamDashboard /> },

  // Admin model redirects → DataBrowser
  { path: PageRoutes.employeeList, element: <Navigate to="/admin-wb?model=orgs.Employee" replace /> },
  { path: PageRoutes.manufacturerList, element: <Navigate to="/admin-wb?model=orgs.Manufacturer" replace /> },
  { path: PageRoutes.organizationList, element: <Navigate to="/admin-wb?model=orgs.Organization" replace /> },
  { path: PageRoutes.repList, element: <Navigate to="/admin-wb?model=orgs.Rep" replace /> },
  { path: PageRoutes.vendorList, element: <Navigate to="/admin-wb?model=orgs.Vendor" replace /> },
  { path: PageRoutes.coreSettingList, element: <Navigate to="/admin-wb?model=core.Setting" replace /> },
  { path: PageRoutes.coreSettingDetail, element: <Navigate to="/admin-wb?model=core.Setting" replace /> },
  { path: PageRoutes.coreReportList, element: <Navigate to="/admin-wb?model=core.Report" replace /> },
  { path: PageRoutes.coreReportDetail, element: <Navigate to="/admin-wb?model=core.Report" replace /> },
  { path: PageRoutes.coreTemplateList, element: <Navigate to="/admin-wb?model=core.Template" replace /> },
  { path: PageRoutes.coreTemplateDetail, element: <Navigate to="/admin-wb?model=core.Template" replace /> },
  { path: PageRoutes.commDomainList, element: <Navigate to="/admin-wb?model=communications.Domain" replace /> },
  { path: PageRoutes.commDomainDetail, element: <Navigate to="/admin-wb?model=communications.Domain" replace /> },
  { path: PageRoutes.commEmailList, element: <Navigate to="/admin-wb?model=communications.Email" replace /> },
  { path: PageRoutes.commEmailDetail, element: <Navigate to="/admin-wb?model=communications.Email" replace /> },
  { path: PageRoutes.commAddressList, element: <Navigate to="/admin-wb?model=communications.Address" replace /> },
  { path: PageRoutes.commAddressDetail, element: <Navigate to="/admin-wb?model=communications.Address" replace /> },
  { path: PageRoutes.commPhoneList, element: <Navigate to="/admin-wb?model=communications.Phone" replace /> },
  { path: PageRoutes.commPhoneDetail, element: <Navigate to="/admin-wb?model=communications.Phone" replace /> },
  { path: PageRoutes.documentList, element: <Navigate to="/admin-wb?model=docs.Document" replace /> },
  { path: PageRoutes.documentDetail, element: <Navigate to="/admin-wb?model=docs.Document" replace /> },
  { path: PageRoutes.questionAnswerList, element: <Navigate to="/admin-wb?model=docs.QuestionAnswer" replace /> },
  { path: PageRoutes.tagList, element: <Navigate to="/admin-wb?model=docs.Tag" replace /> },
  { path: PageRoutes.productsBillOfMaterialList, element: <Navigate to="/admin-wb?model=products.BillOfMaterial" replace /> },
  { path: PageRoutes.productsCatalogList, element: <Navigate to="/admin-wb?model=products.Catalog" replace /> },
  { path: PageRoutes.productsFlowList, element: <Navigate to="/admin-wb?model=products.Flow" replace /> },
  { path: PageRoutes.productsItemXrefList, element: <Navigate to="/admin-wb?model=products.ItemXref" replace /> },
  { path: PageRoutes.productsMatricsList, element: <Navigate to="/admin-wb?model=products.Matrics" replace /> },
  { path: PageRoutes.productsOrgItemList, element: <Navigate to="/admin-wb?model=products.OrgItem" replace /> },
  { path: PageRoutes.productsSerialList, element: <Navigate to="/admin-wb?model=products.Serial" replace /> },
  { path: PageRoutes.productsServiceList, element: <Navigate to="/admin-wb?model=products.Service" replace /> },
  { path: PageRoutes.productsSpecificationList, element: <Navigate to="/admin-wb?model=products.Specification" replace /> },
  { path: PageRoutes.productsUsageList, element: <Navigate to="/admin-wb?model=products.Usage" replace /> },
  { path: PageRoutes.productsVariantList, element: <Navigate to="/admin-wb?model=products.Variant" replace /> },
  { path: PageRoutes.productsWarehouseList, element: <Navigate to="/admin-wb?model=products.Warehouse" replace /> },
  { path: PageRoutes.auditList, element: <Navigate to="/admin-wb?model=accounts.Audit" replace /> },
  { path: PageRoutes.auditDetail, element: <Navigate to="/admin-wb?model=accounts.Audit" replace /> },
  { path: PageRoutes.currencyList, element: <Navigate to="/admin-wb?model=accounts.Currency" replace /> },
  { path: PageRoutes.currencyDetail, element: <Navigate to="/admin-wb?model=accounts.Currency" replace /> },
  { path: PageRoutes.exchangeRateList, element: <Navigate to="/admin-wb?model=accounts.ExchangeRate" replace /> },
  { path: PageRoutes.exchangeRateDetail, element: <Navigate to="/admin-wb?model=accounts.ExchangeRate" replace /> },
  { path: PageRoutes.exchangeTransactionList, element: <Navigate to="/admin-wb?model=accounts.ExchangeTransaction" replace /> },
  { path: PageRoutes.exchangeTransactionDetail, element: <Navigate to="/admin-wb?model=accounts.ExchangeTransaction" replace /> },
  { path: PageRoutes.glAccountList, element: <Navigate to="/admin-wb?model=accounts.GLAccount" replace /> },
  { path: PageRoutes.glAccountDetail, element: <Navigate to="/admin-wb?model=accounts.GLAccount" replace /> },
  { path: PageRoutes.glJournalList, element: <Navigate to="/admin-wb?model=accounts.GlJournal" replace /> },
  { path: PageRoutes.glJournalDetail, element: <Navigate to="/admin-wb?model=accounts.GlJournal" replace /> },
  { path: PageRoutes.ledgerList, element: <Navigate to="/admin-wb?model=accounts.Ledger" replace /> },
  { path: PageRoutes.tallySummaryList, element: <Navigate to="/admin-wb?model=accounts.TallySummary" replace /> },
  { path: PageRoutes.salesDimensionTallyList, element: <Navigate to="/admin-wb?model=accounts.SalesDimensionTally" replace /> },
  { path: PageRoutes.inventoryUsageTallyList, element: <Navigate to="/admin-wb?model=accounts.InventoryUsageTally" replace /> },
  { path: PageRoutes.tallyRegistryList, element: <Navigate to="/admin-wb?model=accounts.TallyRegistry" replace /> },
  { path: PageRoutes.taxJurisdictionList, element: <Navigate to="/admin-wb?model=accounts.TaxJurisdiction" replace /> },
  { path: PageRoutes.termList, element: <Navigate to="/admin-wb?model=accounts.Term" replace /> },

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

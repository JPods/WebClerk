/* LastChecked: 2026-06-28 | WhereUsed: App root | WhoCreated: Unknown */
import WcapiRouteHandler from "./WcapiRouteHandler";
import ItemDetail from "../apps/products/models/item/pages/ItemDetail";
import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { WindowManagerNavigationSync } from "../context/WindowManagerContext";
import PrivateRoute from "./PrivateRoute";
import { PageRoutes } from "./Routes";
import { ScrollToTop, Toster } from "../components/wrapper";
import {
  CustomerDetailPage,
  CustomerAddPage,
  CustomerEditPage,
  Home,
  KanbanBoardPage,
  KanbanBoardDataPage,
  NotionTrackerPage,
  SignIn,
  SignUp,
  UnifiedGanttPage,
  UserProfiles,
  // Core
  CoreContactDetail,
} from "../pages/wrapperPage";
import AdminWorkbench from "../pages/admin/AdminWorkbench";
import AliceDashboard from "../pages/admin/AliceDashboard";
import HelpDashboard from "../pages/admin/HelpDashboard";
import TestDashboard from "../pages/admin/TestDashboard";
import DetailReview from "../pages/admin/DetailReview";
import WhitelistTester from "../pages/tools/WhitelistTester";

const PageDesigner = React.lazy(() => import("../pages/tools/PageDesigner"));
const PdfDesigner = React.lazy(() => import("../pages/tools/PdfDesigner"));
const AccountingDashboard = React.lazy(() => import("../pages/admin/AccountingDashboard"));
const InventoryDashboard = React.lazy(() => import("../pages/admin/InventoryDashboard"));
import OrderDetail from "../apps/transactions/models/order/pages/OrderDetail";
import InvoiceDetail from "../apps/transactions/models/invoice/pages/InvoiceDetail";
import ApplyPayments from "../apps/transactions/pages/ApplyPayments";
import PaymentDetailPage from "../apps/transactions/models/payment/pages/PaymentDetailPage";
import PurchaseDetail from "../apps/transactions/models/purchase/pages/PurchaseDetail";
import ProposalDetail from "../apps/transactions/models/proposal/pages/ProposalDetail";
import WorkorderDetail from "../apps/transactions/models/workorder/pages/WorkorderDetail";
import ReceiptDetail from "../apps/transactions/models/receipt/pages/ReceiptDetail";
import CustomerPage from "../apps/orgs/pages/CustomerPage";
import VendorPage from "../apps/orgs/pages/VendorPage";
import EmployeePage from "../apps/orgs/pages/EmployeePage";
import RepPage from "../apps/orgs/pages/RepPage";
import ManufacturerPage from "../apps/orgs/pages/ManufacturerPage";
import InvoicePrint from "../apps/transactions/print/InvoicePrint";
import OrderPrint from "../apps/transactions/print/OrderPrint";
import ProposalPrint from "../apps/transactions/print/ProposalPrint";
import PurchasePrint from "../apps/transactions/print/PurchasePrint";
import QAPrint from "../apps/transactions/print/QAPrint";
import Test from "../pages/test/Test";
import QATestPage from "../pages/test/QATestPage";
import NotFoundPage from "../pages/NotFoundPage";
// All list views use DataBrowser at /db/:model — no ModelList imports
import ActionDetail from "../apps/core/models/action/pages/ActionDetail";
import AllModelsWorkbench from "../apps/utils/scaffold/AllModelsWorkbench";
import Placeholder from "../pages/Placeholder";

const Router: React.FC = () => {
  return (
    <BrowserRouter basename={import.meta.env.VITE_BASE_PATH || '/'}>
      <WindowManagerNavigationSync />
      <ScrollToTop />
      <Toster />
      <Routes>
        {/* Public routes */}
        <Route path={PageRoutes.login} element={<SignIn />} />
        <Route path={PageRoutes.register} element={<SignUp />} />
        <Route path="/test" element={<Test />} />
        <Route path="/test/qa" element={<QATestPage />} />
        {/* Protected routes */}
        <Route element={<PrivateRoute />}>
          {/* Universal WCAPI route handler */}
          <Route path="/wcapi/get/" element={<WcapiRouteHandler />} />
          <Route path={PageRoutes.dashboard} element={<Home />} />
          <Route path={PageRoutes.profile} element={<UserProfiles />} />

          {/* ── User-facing: Contact ── */}
          <Route path={PageRoutes.coreContactList} element={<Navigate to="/db/contact" replace />} />
          <Route path={PageRoutes.coreContactDetail} element={<CoreContactDetail />} />

          {/* ── Orgs — shared OrgPage with config-driven views ── */}
          <Route path="/org/customer" element={<CustomerPage />} />
          <Route path="/org/vendor" element={<VendorPage />} />
          <Route path="/org/employee" element={<EmployeePage />} />
          <Route path="/org/rep" element={<RepPage />} />
          <Route path="/org/manufacturer" element={<ManufacturerPage />} />
          {/* Legacy customer routes → new page */}
          <Route path={PageRoutes.customerList} element={<Navigate to="/org/customer" replace />} />
          <Route path={`${PageRoutes.customerDetail}/:id`} element={<CustomerDetailPage />} />
          <Route path={PageRoutes.customerAdd} element={<CustomerAddPage />} />
          <Route path={`${PageRoutes.customerEdit}/:id`} element={<CustomerEditPage />} />

          {/* ── All lists → DataBrowser at /db/:model ── */}
          <Route path={PageRoutes.actionList} element={<Navigate to="/db/action" replace />} />
          <Route path={PageRoutes.actionDetail} element={<ActionDetail />} />
          <Route path={PageRoutes.docs} element={<Placeholder title="Documents" />} />
          <Route path={PageRoutes.products} element={<Navigate to="/db/item" replace />} />
          <Route path={PageRoutes.productsItemList} element={<Navigate to="/db/item" replace />} />
          <Route path={PageRoutes.productsItemDetail} element={<ItemDetail />} />

          {/* ── Transaction lists → DataBrowser, details → custom pages ── */}
          <Route path={PageRoutes.transactionsOrderList} element={<Navigate to="/db/order" replace />} />
          <Route path={PageRoutes.transactionsOrderDetail} element={<OrderDetail />} />
          <Route path={PageRoutes.transactionsInvoiceList} element={<Navigate to="/db/invoice" replace />} />
          <Route path={PageRoutes.transactionsInvoiceDetail} element={<InvoiceDetail />} />
          <Route path={PageRoutes.transactionsApplyPayments} element={<ApplyPayments />} />
          <Route path={PageRoutes.transactionsPaymentList} element={<Navigate to="/db/payment" replace />} />
          <Route path={PageRoutes.transactionsPaymentDetail} element={<PaymentDetailPage />} />
          <Route path={PageRoutes.transactionsPurchaseList} element={<Navigate to="/db/purchase" replace />} />
          <Route path={PageRoutes.transactionsPurchaseDetail} element={<PurchaseDetail />} />
          <Route path={PageRoutes.transactionsProposalList} element={<Navigate to="/db/proposal" replace />} />
          <Route path={PageRoutes.transactionsProposalDetail} element={<ProposalDetail />} />
          <Route path={PageRoutes.transactionsWorkOrderList} element={<Navigate to="/db/workorder" replace />} />
          <Route path={PageRoutes.transactionsWorkOrderDetail} element={<WorkorderDetail />} />
          <Route path={PageRoutes.transactionsReceiptList} element={<Navigate to="/db/receipt" replace />} />
          <Route path={PageRoutes.transactionsReceiptDetail} element={<ReceiptDetail />} />
          <Route path={PageRoutes.transactionsAdjustmentList} element={<Navigate to="/inventory-dashboard" replace />} />

          {/* ── Tools ── */}
          <Route path={PageRoutes.notionTracker} element={<NotionTrackerPage />} />
          <Route path={PageRoutes.kanbanBoard} element={<KanbanBoardPage />} />
          <Route path={PageRoutes.kanbanBoardData} element={<KanbanBoardDataPage />} />
          <Route path={PageRoutes.gantt} element={<UnifiedGanttPage />} />
          <Route path={PageRoutes.kanbanGantt} element={<Navigate to={PageRoutes.gantt} replace />} />
          <Route path={PageRoutes.svarGantt} element={<Navigate to={PageRoutes.gantt} replace />} />
          <Route path={PageRoutes.multiProjectGantt} element={<Navigate to={PageRoutes.gantt} replace />} />

          {/* ── Print pages ── */}
          <Route path="/transactions/invoice/print/:id" element={<InvoicePrint />} />
          <Route path="/transactions/order/print/:id" element={<OrderPrint />} />
          <Route path="/transactions/proposal/print/:id" element={<ProposalPrint />} />
          <Route path="/transactions/purchase/print/:id" element={<PurchasePrint />} />
          <Route path="/transactions/qa/print/:model/:id" element={<QAPrint />} />

          {/* ── Admin tools ── */}
          <Route path={PageRoutes.adminWorkbench} element={<AdminWorkbench />} />
          <Route path="/db/:model" element={<AdminWorkbench />} />
          <Route path="/db" element={<Navigate to="/admin-wb" replace />} />
          <Route path="/alice-dashboard" element={<AliceDashboard />} />
          <Route path="/help" element={<HelpDashboard />} />
          <Route path="/test-dashboard" element={<TestDashboard />} />
          <Route path={PageRoutes.detailReview} element={<DetailReview />} />
          <Route path={PageRoutes.modelWorkbench} element={<AllModelsWorkbench />} />
          <Route path={PageRoutes.whitelist} element={<WhitelistTester />} />
          <Route path="/page-designer" element={<React.Suspense fallback={<div>Loading...</div>}><PageDesigner /></React.Suspense>} />
          <Route path="/pdf-designer" element={<React.Suspense fallback={<div>Loading...</div>}><PdfDesigner /></React.Suspense>} />
          <Route path="/accounting" element={<React.Suspense fallback={<div>Loading...</div>}><AccountingDashboard /></React.Suspense>} />
          <Route path="/inventory-dashboard" element={<React.Suspense fallback={<div>Loading...</div>}><InventoryDashboard /></React.Suspense>} />

          {/* ── Submit for Bonus (stub) ── */}
          <Route path="/submit-bonus" element={
            <div style={{ padding: 40, maxWidth: 600, margin: '0 auto' }}>
              <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 16 }}>Submit for Bonus</h1>
              <p style={{ color: '#666', lineHeight: 1.6 }}>
                Submit your layouts, views, React components, or other improvements to WebClerk HQ.
                Accepted submissions earn credit or cash bonuses based on adoption by other users.
              </p>
              <p style={{ color: '#666', lineHeight: 1.6, marginTop: 12 }}>
                Submissions are transported via sync (Connection + Bundle).
                Alice tracks adoption and manages rewards.
              </p>
              <p style={{ color: '#999', marginTop: 24, fontSize: 13 }}>Coming soon — this page will connect to the sync submission flow.</p>
            </div>
          } />

          {/* ── Admin model redirects → DataBrowser ── */}
          {/* Accounts */}
          <Route path={PageRoutes.auditList} element={<Navigate to="/db/accounts.Audit" replace />} />
          <Route path={PageRoutes.auditDetail} element={<Navigate to="/db/accounts.Audit" replace />} />
          <Route path={PageRoutes.currencyList} element={<Navigate to="/db/accounts.Currency" replace />} />
          <Route path={PageRoutes.currencyDetail} element={<Navigate to="/db/accounts.Currency" replace />} />
          <Route path={PageRoutes.exchangeRateList} element={<Navigate to="/db/accounts.ExchangeRate" replace />} />
          <Route path={PageRoutes.exchangeRateDetail} element={<Navigate to="/db/accounts.ExchangeRate" replace />} />
          <Route path={PageRoutes.exchangeTransactionList} element={<Navigate to="/db/accounts.ExchangeTransaction" replace />} />
          <Route path={PageRoutes.exchangeTransactionDetail} element={<Navigate to="/db/accounts.ExchangeTransaction" replace />} />
          <Route path={PageRoutes.glAccountList} element={<Navigate to="/db/accounts.GLAccount" replace />} />
          <Route path={PageRoutes.glAccountDetail} element={<Navigate to="/db/accounts.GLAccount" replace />} />
          <Route path={PageRoutes.glJournalList} element={<Navigate to="/db/accounts.GlJournal" replace />} />
          <Route path={PageRoutes.glJournalDetail} element={<Navigate to="/db/accounts.GlJournal" replace />} />
          <Route path={PageRoutes.ledgerList} element={<Navigate to="/db/accounts.Ledger" replace />} />
          <Route path={PageRoutes.tallySummaryList} element={<Navigate to="/db/accounts.TallySummary" replace />} />
          <Route path={PageRoutes.salesDimensionTallyList} element={<Navigate to="/db/accounts.SalesDimensionTally" replace />} />
          <Route path={PageRoutes.inventoryUsageTallyList} element={<Navigate to="/db/accounts.InventoryUsageTally" replace />} />
          <Route path={PageRoutes.tallyRegistryList} element={<Navigate to="/db/accounts.TallyRegistry" replace />} />
          <Route path={PageRoutes.taxJurisdictionList} element={<Navigate to="/db/accounts.TaxJurisdiction" replace />} />
          <Route path={PageRoutes.termList} element={<Navigate to="/db/accounts.Term" replace />} />
          {/* Core admin */}
          <Route path={PageRoutes.coreSettingList} element={<Navigate to="/db/core.Setting" replace />} />
          <Route path={PageRoutes.coreSettingDetail} element={<Navigate to="/db/core.Setting" replace />} />
          <Route path={PageRoutes.coreReportList} element={<Navigate to="/db/core.Report" replace />} />
          <Route path={PageRoutes.coreReportDetail} element={<Navigate to="/db/core.Report" replace />} />
          <Route path={PageRoutes.coreTemplateList} element={<Navigate to="/db/core.Template" replace />} />
          <Route path={PageRoutes.coreTemplateDetail} element={<Navigate to="/db/core.Template" replace />} />
          {/* Communications */}
          <Route path={PageRoutes.commDomainList} element={<Navigate to="/db/communications.Domain" replace />} />
          <Route path={PageRoutes.commDomainDetail} element={<Navigate to="/db/communications.Domain" replace />} />
          <Route path={PageRoutes.commEmailList} element={<Navigate to="/db/communications.Email" replace />} />
          <Route path={PageRoutes.commEmailDetail} element={<Navigate to="/db/communications.Email" replace />} />
          <Route path={PageRoutes.commAddressList} element={<Navigate to="/db/communications.Address" replace />} />
          <Route path={PageRoutes.commAddressDetail} element={<Navigate to="/db/communications.Address" replace />} />
          <Route path={PageRoutes.commPhoneList} element={<Navigate to="/db/communications.Phone" replace />} />
          <Route path={PageRoutes.commPhoneDetail} element={<Navigate to="/db/communications.Phone" replace />} />
          {/* Docs admin */}
          <Route path={PageRoutes.questionAnswerList} element={<Navigate to="/db/docs.QuestionAnswer" replace />} />
          <Route path={PageRoutes.tagList} element={<Navigate to="/db/docs.Tag" replace />} />
          {/* Products admin */}
          <Route path={PageRoutes.productsBillOfMaterialList} element={<Navigate to="/db/products.BillOfMaterial" replace />} />
          <Route path={PageRoutes.productsCatalogList} element={<Navigate to="/db/products.Catalog" replace />} />
          <Route path={PageRoutes.productsFlowList} element={<Navigate to="/db/products.Flow" replace />} />
          <Route path={PageRoutes.productsItemXrefList} element={<Navigate to="/db/products.ItemXref" replace />} />
          <Route path={PageRoutes.productsMatricsList} element={<Navigate to="/db/products.Matrics" replace />} />
          <Route path={PageRoutes.productsOrgItemList} element={<Navigate to="/db/products.OrgItem" replace />} />
          <Route path={PageRoutes.productsSerialList} element={<Navigate to="/db/products.Serial" replace />} />
          <Route path={PageRoutes.productsServiceList} element={<Navigate to="/db/products.Service" replace />} />
          <Route path={PageRoutes.productsSpecificationList} element={<Navigate to="/db/products.Specification" replace />} />
          <Route path={PageRoutes.productsUsageList} element={<Navigate to="/db/products.Usage" replace />} />
          <Route path={PageRoutes.productsVariantList} element={<Navigate to="/db/products.Variant" replace />} />
          <Route path={PageRoutes.productsWarehouseList} element={<Navigate to="/db/products.Warehouse" replace />} />
          {/* Orgs admin */}
          <Route path={PageRoutes.employeeList} element={<Navigate to="/db/orgs.Employee" replace />} />
          <Route path={PageRoutes.manufacturerList} element={<Navigate to="/db/orgs.Manufacturer" replace />} />
          <Route path={PageRoutes.organizationList} element={<Navigate to="/db/orgs.Organization" replace />} />
          <Route path={PageRoutes.repList} element={<Navigate to="/db/orgs.Rep" replace />} />
          <Route path={PageRoutes.vendorList} element={<Navigate to="/db/orgs.Vendor" replace />} />
          <Route path={PageRoutes.documentList} element={<Navigate to="/db/docs.Document" replace />} />
          <Route path={PageRoutes.documentDetail} element={<Navigate to="/db/docs.Document" replace />} />
        </Route>

        {/* 404 page */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
};

export default Router;

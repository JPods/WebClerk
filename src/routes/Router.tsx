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
  CustomerList,
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
  CoreContactList,
  CoreContactDetail,
} from "../pages/wrapperPage";
import AdminWorkbench from "../pages/admin/AdminWorkbench";
import AliceDashboard from "../pages/admin/AliceDashboard";
import HelpDashboard from "../pages/admin/HelpDashboard";
import TestDashboard from "../pages/admin/TestDashboard";
import DetailReview from "../pages/admin/DetailReview";
import WhitelistTester from "../pages/tools/WhitelistTester";
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
import InventoryAdjustmentList from "../apps/transactions/models/inventory_adjustment/pages/InventoryAdjustmentList";
import CustomerPage from "../apps/orgs/pages/CustomerPage";
import VendorPage from "../apps/orgs/pages/VendorPage";
import EmployeePage from "../apps/orgs/pages/EmployeePage";
import RepPage from "../apps/orgs/pages/RepPage";
import ManufacturerPage from "../apps/orgs/pages/ManufacturerPage";
import InvoicePrint from "../apps/transactions/print/InvoicePrint";
import OrderPrint from "../apps/transactions/print/OrderPrint";
import ProposalPrint from "../apps/transactions/print/ProposalPrint";
import QAPrint from "../apps/transactions/print/QAPrint";
import Test from "../pages/test/Test";
import QATestPage from "../pages/test/QATestPage";
import NotFoundPage from "../pages/NotFoundPage";
import ActionList from "../apps/core/models/action/pages/ActionList";
import ActionDetail from "../apps/core/models/action/pages/ActionDetail";
import AllModelsWorkbench from "../apps/utils/scaffold/AllModelsWorkbench";
import Placeholder from "../pages/Placeholder";

const Router: React.FC = () => {
  return (
    <BrowserRouter>
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
          <Route path={PageRoutes.coreContactList} element={<CoreContactList />} />
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

          {/* ── User-facing: Actions ── */}
          <Route path={PageRoutes.actionList} element={<ActionList />} />
          <Route path={PageRoutes.actionDetail} element={<ActionDetail />} />

          {/* ── User-facing: Documents ── */}
          <Route path={PageRoutes.docs} element={<Placeholder title="Documents" />} />

          {/* ── User-facing: Products (Item only — others via DataBrowser) ── */}
          <Route path={PageRoutes.products} element={<Navigate to={PageRoutes.productsItemList} replace />} />
          <Route path={PageRoutes.productsItemList} element={<ItemList />} />
          <Route path={PageRoutes.productsItemDetail} element={<ItemDetail />} />

          {/* ── User-facing: Transactions ── */}
          <Route path={PageRoutes.transactionsOrderList} element={<OrderList />} />
          <Route path={PageRoutes.transactionsOrderDetail} element={<OrderDetail />} />
          <Route path={PageRoutes.transactionsInvoiceList} element={<InvoiceList />} />
          <Route path={PageRoutes.transactionsInvoiceDetail} element={<InvoiceDetail />} />
          <Route path={PageRoutes.transactionsApplyPayments} element={<ApplyPayments />} />
          <Route path={PageRoutes.transactionsPaymentList} element={<PaymentListPage />} />
          <Route path={PageRoutes.transactionsPaymentDetail} element={<PaymentDetailPage />} />
          <Route path={PageRoutes.transactionsPurchaseList} element={<PurchaseList />} />
          <Route path={PageRoutes.transactionsPurchaseDetail} element={<PurchaseDetail />} />
          <Route path={PageRoutes.transactionsProposalList} element={<ProposalList />} />
          <Route path={PageRoutes.transactionsProposalDetail} element={<ProposalDetail />} />
          <Route path={PageRoutes.transactionsWorkOrderList} element={<WorkorderList />} />
          <Route path={PageRoutes.transactionsWorkOrderDetail} element={<WorkorderDetail />} />
          <Route path={PageRoutes.transactionsReceiptList} element={<ReceiptList />} />
          <Route path={PageRoutes.transactionsReceiptDetail} element={<ReceiptDetail />} />
          <Route path={PageRoutes.transactionsAdjustmentList} element={<InventoryAdjustmentList />} />

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
          <Route path="/transactions/qa/print/:model/:id" element={<QAPrint />} />

          {/* ── Admin tools ── */}
          <Route path={PageRoutes.adminWorkbench} element={<AdminWorkbench />} />
          <Route path="/db" element={<Navigate to="/admin-wb" replace />} />
          <Route path="/alice-dashboard" element={<AliceDashboard />} />
          <Route path="/help" element={<HelpDashboard />} />
          <Route path="/test-dashboard" element={<TestDashboard />} />
          <Route path={PageRoutes.detailReview} element={<DetailReview />} />
          <Route path={PageRoutes.modelWorkbench} element={<AllModelsWorkbench />} />
          <Route path={PageRoutes.whitelist} element={<WhitelistTester />} />

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
          <Route path={PageRoutes.auditList} element={<Navigate to="/admin-wb?model=accounts.Audit" replace />} />
          <Route path={PageRoutes.auditDetail} element={<Navigate to="/admin-wb?model=accounts.Audit" replace />} />
          <Route path={PageRoutes.currencyList} element={<Navigate to="/admin-wb?model=accounts.Currency" replace />} />
          <Route path={PageRoutes.currencyDetail} element={<Navigate to="/admin-wb?model=accounts.Currency" replace />} />
          <Route path={PageRoutes.exchangeRateList} element={<Navigate to="/admin-wb?model=accounts.ExchangeRate" replace />} />
          <Route path={PageRoutes.exchangeRateDetail} element={<Navigate to="/admin-wb?model=accounts.ExchangeRate" replace />} />
          <Route path={PageRoutes.exchangeTransactionList} element={<Navigate to="/admin-wb?model=accounts.ExchangeTransaction" replace />} />
          <Route path={PageRoutes.exchangeTransactionDetail} element={<Navigate to="/admin-wb?model=accounts.ExchangeTransaction" replace />} />
          <Route path={PageRoutes.glAccountList} element={<Navigate to="/admin-wb?model=accounts.GLAccount" replace />} />
          <Route path={PageRoutes.glAccountDetail} element={<Navigate to="/admin-wb?model=accounts.GLAccount" replace />} />
          <Route path={PageRoutes.glJournalList} element={<Navigate to="/admin-wb?model=accounts.GlJournal" replace />} />
          <Route path={PageRoutes.glJournalDetail} element={<Navigate to="/admin-wb?model=accounts.GlJournal" replace />} />
          <Route path={PageRoutes.ledgerList} element={<Navigate to="/admin-wb?model=accounts.Ledger" replace />} />
          <Route path={PageRoutes.tallySummaryList} element={<Navigate to="/admin-wb?model=accounts.TallySummary" replace />} />
          <Route path={PageRoutes.salesDimensionTallyList} element={<Navigate to="/admin-wb?model=accounts.SalesDimensionTally" replace />} />
          <Route path={PageRoutes.inventoryUsageTallyList} element={<Navigate to="/admin-wb?model=accounts.InventoryUsageTally" replace />} />
          <Route path={PageRoutes.tallyRegistryList} element={<Navigate to="/admin-wb?model=accounts.TallyRegistry" replace />} />
          <Route path={PageRoutes.taxJurisdictionList} element={<Navigate to="/admin-wb?model=accounts.TaxJurisdiction" replace />} />
          <Route path={PageRoutes.termList} element={<Navigate to="/admin-wb?model=accounts.Term" replace />} />
          {/* Core admin */}
          <Route path={PageRoutes.coreSettingList} element={<Navigate to="/admin-wb?model=core.Setting" replace />} />
          <Route path={PageRoutes.coreSettingDetail} element={<Navigate to="/admin-wb?model=core.Setting" replace />} />
          <Route path={PageRoutes.coreReportList} element={<Navigate to="/admin-wb?model=core.Report" replace />} />
          <Route path={PageRoutes.coreReportDetail} element={<Navigate to="/admin-wb?model=core.Report" replace />} />
          <Route path={PageRoutes.coreTemplateList} element={<Navigate to="/admin-wb?model=core.Template" replace />} />
          <Route path={PageRoutes.coreTemplateDetail} element={<Navigate to="/admin-wb?model=core.Template" replace />} />
          {/* Communications */}
          <Route path={PageRoutes.commDomainList} element={<Navigate to="/admin-wb?model=communications.Domain" replace />} />
          <Route path={PageRoutes.commDomainDetail} element={<Navigate to="/admin-wb?model=communications.Domain" replace />} />
          <Route path={PageRoutes.commEmailList} element={<Navigate to="/admin-wb?model=communications.Email" replace />} />
          <Route path={PageRoutes.commEmailDetail} element={<Navigate to="/admin-wb?model=communications.Email" replace />} />
          <Route path={PageRoutes.commAddressList} element={<Navigate to="/admin-wb?model=communications.Address" replace />} />
          <Route path={PageRoutes.commAddressDetail} element={<Navigate to="/admin-wb?model=communications.Address" replace />} />
          <Route path={PageRoutes.commPhoneList} element={<Navigate to="/admin-wb?model=communications.Phone" replace />} />
          <Route path={PageRoutes.commPhoneDetail} element={<Navigate to="/admin-wb?model=communications.Phone" replace />} />
          {/* Docs admin */}
          <Route path={PageRoutes.questionAnswerList} element={<Navigate to="/admin-wb?model=docs.QuestionAnswer" replace />} />
          <Route path={PageRoutes.tagList} element={<Navigate to="/admin-wb?model=docs.Tag" replace />} />
          {/* Products admin */}
          <Route path={PageRoutes.productsBillOfMaterialList} element={<Navigate to="/admin-wb?model=products.BillOfMaterial" replace />} />
          <Route path={PageRoutes.productsCatalogList} element={<Navigate to="/admin-wb?model=products.Catalog" replace />} />
          <Route path={PageRoutes.productsFlowList} element={<Navigate to="/admin-wb?model=products.Flow" replace />} />
          <Route path={PageRoutes.productsItemXrefList} element={<Navigate to="/admin-wb?model=products.ItemXref" replace />} />
          <Route path={PageRoutes.productsMatricsList} element={<Navigate to="/admin-wb?model=products.Matrics" replace />} />
          <Route path={PageRoutes.productsOrgItemList} element={<Navigate to="/admin-wb?model=products.OrgItem" replace />} />
          <Route path={PageRoutes.productsSerialList} element={<Navigate to="/admin-wb?model=products.Serial" replace />} />
          <Route path={PageRoutes.productsServiceList} element={<Navigate to="/admin-wb?model=products.Service" replace />} />
          <Route path={PageRoutes.productsSpecificationList} element={<Navigate to="/admin-wb?model=products.Specification" replace />} />
          <Route path={PageRoutes.productsUsageList} element={<Navigate to="/admin-wb?model=products.Usage" replace />} />
          <Route path={PageRoutes.productsVariantList} element={<Navigate to="/admin-wb?model=products.Variant" replace />} />
          <Route path={PageRoutes.productsWarehouseList} element={<Navigate to="/admin-wb?model=products.Warehouse" replace />} />
          {/* Orgs admin */}
          <Route path={PageRoutes.employeeList} element={<Navigate to="/admin-wb?model=orgs.Employee" replace />} />
          <Route path={PageRoutes.manufacturerList} element={<Navigate to="/admin-wb?model=orgs.Manufacturer" replace />} />
          <Route path={PageRoutes.organizationList} element={<Navigate to="/admin-wb?model=orgs.Organization" replace />} />
          <Route path={PageRoutes.repList} element={<Navigate to="/admin-wb?model=orgs.Rep" replace />} />
          <Route path={PageRoutes.vendorList} element={<Navigate to="/admin-wb?model=orgs.Vendor" replace />} />
          <Route path={PageRoutes.documentList} element={<Navigate to="/admin-wb?model=docs.Document" replace />} />
          <Route path={PageRoutes.documentDetail} element={<Navigate to="/admin-wb?model=docs.Document" replace />} />
        </Route>

        {/* 404 page */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
};

export default Router;

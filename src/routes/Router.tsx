import WcapiRouteHandler from "./WcapiRouteHandler";
// import { CustomerDashboard as CustomerDashboardPage } from '../apps/orgs/models/customer/pages/CustomerDashboard';
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
  EmployeeList,
  ManufacturerList,
  OrganizationsList,
  RepList,
  VendorList,
  Home,
  KanbanBoardDataPage,
  KanbanBoardPage,
  NotionTrackerPage,
  SignIn,
  SignUp,
  UnifiedGanttPage,
  UserProfiles,
  // Accounts
  AuditList,
  AuditDetail,
  CurrencyList,
  CurrencyDetail,
  ExchangeRateList,
  ExchangeRateDetail,
  ExchangeTransactionList,
  ExchangeTransactionDetail,
  GLAccountList,
  GLAccountDetail,
  GLJournalList,
  GLJournalDetail,
  LedgerList,
  TaxJurisdictionList,
  TermList,
  // Communications
  DomainList,
  DomainDetail,
  EmailList,
  EmailDetail,
  AppAddressList,
  AppAddressDetail,
  AppPhoneList,
  AppPhoneDetail,
  // Core
  CoreContactList,
  CoreContactDetail,
  CoreReportList,
  CoreReportDetail,
  CoreSettingList,
  CoreSettingDetail,
  CoreTemplateList,
  CoreTemplateDetail,
  // Docs
  DocumentList,
  DocumentDetail,
  QuestionAnswerList,
  TagList,
} from "../pages/wrapperPage";
import AdminWorkbench from "../pages/admin/AdminWorkbench";
import DetailReview from "../pages/admin/DetailReview";
import WhitelistTester from "../pages/tools/WhitelistTester";
import BillOfMaterialList from "../apps/products/models/bill_of_material/pages/BillOfMaterialList";
import CatalogList from "../apps/products/models/catalog/pages/CatalogList";
import FlowList from "../apps/products/models/flow/pages/FlowList";
import ItemList from "../apps/products/models/item/pages/ItemList";
import ItemXrefList from "../apps/products/models/item_xref/pages/ItemXrefList";
import MatricsList from "../apps/products/models/matrics/pages/MatricsList";
import OrgItemList from "../apps/products/models/org_item/pages/OrgItemList";
import SerialList from "../apps/products/models/serial/pages/SerialList";
import ServiceList from "../apps/products/models/service/pages/ServiceList";
import SpecificationList from "../apps/products/models/specification/pages/SpecificationList";
import UsageList from "../apps/products/models/usage/pages/UsageList";
import VariantList from "../apps/products/models/variant/pages/VariantList";
import WarehouseList from "../apps/products/models/warehouse/pages/WarehouseList";
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
// Redux store is not used directly here; pages connect as needed.
import Test from "../pages/test/Test";
import QATestPage from "../pages/test/QATestPage";
import NotFoundPage from "../pages/NotFoundPage";
import ActionList from "../apps/core/models/action/pages/ActionList";
import ActionDetail from "../apps/core/models/action/pages/ActionDetail";
import AllModelsWorkbench from "../apps/utils/scaffold/AllModelsWorkbench";
import DocumentIndex from "../apps/docs/models/document/pages/DocumentIndex";

const Router: React.FC = () => {
  return (
    // <Provider store={store}>
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
          <Route
            path={PageRoutes.coreContactList}
            element={<CoreContactList />}
          />
          <Route
            path={PageRoutes.coreContactDetail}
            element={<CoreContactDetail />}
          />
          <Route path={PageRoutes.customerList} element={<CustomerList />} />
          <Route
            path={`${PageRoutes.customerDetail}/:id`}
            element={<CustomerDetailPage />}
          />
          <Route path={PageRoutes.customerAdd} element={<CustomerAddPage />} />
          <Route
            path={`${PageRoutes.customerEdit}/:id`}
            element={<CustomerEditPage />}
          />
          {/* <Route path="/org/customer/dashboard/:customerId" element={<CustomerDashboardPage />} /> */}
          <Route path={PageRoutes.employeeList} element={<EmployeeList />} />
          <Route
            path={PageRoutes.manufacturerList}
            element={<ManufacturerList />}
          />
          <Route
            path={PageRoutes.organizationList}
            element={<OrganizationsList />}
          />
          <Route path={PageRoutes.repList} element={<RepList />} />
          <Route path={PageRoutes.vendorList} element={<VendorList />} />
          {/* <Route
            path={PageRoutes.customerDetail}
            element={<CustomerDetailPage />}
          /> */}
          <Route
            path={PageRoutes.coreSettingList}
            element={<CoreSettingList />}
          />
          <Route
            path={PageRoutes.coreSettingDetail}
            element={<CoreSettingDetail />}
          />
          <Route
            path={PageRoutes.coreReportList}
            element={<CoreReportList />}
          />
          <Route
            path={PageRoutes.coreReportDetail}
            element={<CoreReportDetail />}
          />
          <Route
            path={PageRoutes.coreTemplateList}
            element={<CoreTemplateList />}
          />
          <Route
            path={PageRoutes.coreTemplateDetail}
            element={<CoreTemplateDetail />}
          />
          <Route
            path={PageRoutes.commDomainList}
            element={<DomainList />}
          />
          <Route
            path={PageRoutes.commDomainDetail}
            element={<DomainDetail />}
          />
          <Route
            path={PageRoutes.commEmailList}
            element={<EmailList />}
          />
          <Route
            path={PageRoutes.commEmailDetail}
            element={<EmailDetail />}
          />
          <Route
            path={PageRoutes.commAddressList}
            element={<AppAddressList />}
          />
          <Route
            path={PageRoutes.commAddressDetail}
            element={<AppAddressDetail />}
          />
          <Route
            path={PageRoutes.commPhoneList}
            element={<AppPhoneList />}
          />
          <Route
            path={PageRoutes.commPhoneDetail}
            element={<AppPhoneDetail />}
          />

          <Route
            path={PageRoutes.notionTracker}
            element={<NotionTrackerPage />}
          />
          <Route path={PageRoutes.kanbanBoard} element={<KanbanBoardPage />} />
          <Route
            path={PageRoutes.kanbanBoardData}
            element={<KanbanBoardDataPage />}
          />
          <Route path={PageRoutes.gantt} element={<UnifiedGanttPage />} />
          <Route path={PageRoutes.kanbanGantt} element={<Navigate to={PageRoutes.gantt} replace />} />
          <Route path={PageRoutes.svarGantt} element={<Navigate to={PageRoutes.gantt} replace />} />
          <Route path={PageRoutes.multiProjectGantt} element={<Navigate to={PageRoutes.gantt} replace />} />
          <Route path={PageRoutes.actionList} element={<ActionList />} />
          <Route path={PageRoutes.actionDetail} element={<ActionDetail />} />
          <Route
            path={PageRoutes.adminWorkbench}
            element={<AdminWorkbench />}
          />
          <Route
            path={PageRoutes.detailReview}
            element={<DetailReview />}
          />
          <Route
            path={PageRoutes.modelWorkbench}
            element={<AllModelsWorkbench />}
          />
          <Route path={PageRoutes.whitelist} element={<WhitelistTester />} />
          <Route path={PageRoutes.docs} element={<DocumentIndex />} />
          <Route
            path={PageRoutes.documentList}
            element={<DocumentList />}
          />
          <Route
            path={PageRoutes.documentDetail}
            element={<DocumentDetail />}
          />
          <Route
            path={PageRoutes.questionAnswerList}
            element={<QuestionAnswerList />}
          />
          <Route path={PageRoutes.tagList} element={<TagList />} />
          {/* Products */}
          <Route
            path={PageRoutes.products}
            element={<Navigate to={PageRoutes.productsItemList} replace />}
          />
          <Route
            path={PageRoutes.productsBillOfMaterialList}
            element={<BillOfMaterialList />}
          />
          <Route
            path={PageRoutes.productsCatalogList}
            element={<CatalogList />}
          />
          <Route path={PageRoutes.productsFlowList} element={<FlowList />} />
          <Route
            path={PageRoutes.productsItemList}
            element={<ItemList />}
          />
          <Route
            path={PageRoutes.productsItemDetail}
            element={<ItemDetail />}
          />
          <Route
            path={PageRoutes.productsItemXrefList}
            element={<ItemXrefList />}
          />
          <Route
            path={PageRoutes.productsMatricsList}
            element={<MatricsList />}
          />
          <Route
            path={PageRoutes.productsOrgItemList}
            element={<OrgItemList />}
          />
          <Route
            path={PageRoutes.productsSerialList}
            element={<SerialList />}
          />
          <Route
            path={PageRoutes.productsServiceList}
            element={<ServiceList />}
          />
          <Route
            path={PageRoutes.productsSpecificationList}
            element={<SpecificationList />}
          />
          <Route
            path={PageRoutes.productsUsageList}
            element={<UsageList />}
          />
          <Route
            path={PageRoutes.productsVariantList}
            element={<VariantList />}
          />
          <Route
            path={PageRoutes.productsWarehouseList}
            element={<WarehouseList />}
          />
          {/* Transactions */}
          <Route
            path={PageRoutes.transactionsOrderList}
            element={<OrderList />}
          />
          <Route
            path={PageRoutes.transactionsOrderDetail}
            element={<OrderDetail />}
          />
          <Route
            path={PageRoutes.transactionsInvoiceList}
            element={<InvoiceList />}
          />
          <Route
            path={PageRoutes.transactionsInvoiceDetail}
            element={<InvoiceDetail />}
          />
          <Route
            path={PageRoutes.transactionsApplyPayments}
            element={<ApplyPayments />}
          />
          <Route
            path={PageRoutes.transactionsPaymentList}
            element={<PaymentListPage />}
          />
          <Route
            path={PageRoutes.transactionsPaymentDetail}
            element={<PaymentDetailPage />}
          />
          <Route
            path={PageRoutes.transactionsPurchaseList}
            element={<PurchaseList />}
          />
          <Route
            path={PageRoutes.transactionsPurchaseDetail}
            element={<PurchaseDetail />}
          />
          <Route
            path={PageRoutes.transactionsProposalList}
            element={<ProposalList />}
          />
          <Route
            path={PageRoutes.transactionsProposalDetail}
            element={<ProposalDetail />}
          />
          <Route
            path={PageRoutes.transactionsWorkOrderList}
            element={<WorkorderList />}
          />
          <Route
            path={PageRoutes.transactionsWorkOrderDetail}
            element={<WorkorderDetail />}
          />
          <Route
            path={PageRoutes.transactionsReceiptList}
            element={<ReceiptList />}
          />
          <Route
            path={PageRoutes.transactionsReceiptDetail}
            element={<ReceiptDetail />}
          />
          <Route
            path={PageRoutes.transactionsAdjustmentList}
            element={<InventoryAdjustmentList />}
          />
          {/* Accounts */}
          <Route path={PageRoutes.auditList} element={<AuditList />} />
          <Route path={PageRoutes.auditDetail} element={<AuditDetail />} />
          <Route path={PageRoutes.currencyList} element={<CurrencyList />} />
          <Route
            path={PageRoutes.currencyDetail}
            element={<CurrencyDetail />}
          />
          <Route
            path={PageRoutes.exchangeRateList}
            element={<ExchangeRateList />}
          />
          <Route
            path={PageRoutes.exchangeRateDetail}
            element={<ExchangeRateDetail />}
          />
          <Route
            path={PageRoutes.exchangeTransactionList}
            element={<ExchangeTransactionList />}
          />
          <Route
            path={PageRoutes.exchangeTransactionDetail}
            element={<ExchangeTransactionDetail />}
          />
          <Route
            path={PageRoutes.glAccountList}
            element={<GLAccountList />}
          />
          <Route
            path={PageRoutes.glAccountDetail}
            element={<GLAccountDetail />}
          />
          <Route
            path={PageRoutes.glJournalList}
            element={<GLJournalList />}
          />
          <Route
            path={PageRoutes.glJournalDetail}
            element={<GLJournalDetail />}
          />
          <Route path={PageRoutes.ledgerList} element={<LedgerList />} />
          <Route
            path={PageRoutes.taxJurisdictionList}
            element={<TaxJurisdictionList />}
          />
          <Route path={PageRoutes.termList} element={<TermList />} />
        </Route>

        {/* 404 page */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
    // </Provider>
  );
};

export default Router;

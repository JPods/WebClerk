import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import PrivateRoute from "./PrivateRoute";
import { PageRoutes } from "./Routes";
import { ScrollToTop, Toster } from "../components/wrapper";
import {
  ActionAdd,
  ActionList,
  BasicTables,
  Calendar,
  ContactDetail,
  ContactList,
  CustomerAddPage,
  CustomerDetailPage,
  DomainAdd,
  DomainList,
  FormElements,
  Home,
  KanbanBoardDataPage,
  KanbanBoardPage,
  KanbanGanttPage,
  NotionTrackerPage,
  SettingAdd,
  SettingList,
  SignIn,
  SignUp,
  SvarGanttPage,
  UserProfiles,
  // Accounts
  AuditList,
  AuditDetail,
  AuditDisplay,
  CurrencyList,
  CurrencyDetail,
  CurrencyDisplay,
  ExchangeRateList,
  ExchangeRateDetail,
  ExchangeRateDisplay,
  ExchangeTransactionList,
  ExchangeTransactionDetail,
  ExchangeTransactionDisplay,
  GLAccountList,
  GLAccountDetail,
  GLJournalList,
  GLJournalDetail,
  GLJournalDisplay,
  LedgerList,
  LedgerDisplay,
  TaxJurisdictionList,
  TaxJurisdictionDisplay,
  TermList,
  TermDisplay,
  // Communications
  AppDomainList,
  AppDomainDetail,
  AppEmailList,
  AppEmailDetail,
  AppLocationList,
  AppLocationDetail,
  AppPhoneList,
  AppPhoneDetail,
  // Core
  CoreContactList,
  CoreContactDetail,
  CoreReportList,
  CoreReportDetail,
  CoreReportDisplay,
  CoreSettingList,
  CoreSettingDetail,
  CoreSettingDisplay,
  CoreTemplateList,
  CoreTemplateDetail,
  CoreTemplateDisplay,
  // Docs
  DocumentList,
  DocumentDetail,
  DocumentDisplay,
  LinkageList,
  LinkageDisplay,
  LinkageIndexList,
  LinkageIndexDisplay,
  QuestionAnswerList,
  QuestionAnswerDisplay,
  TagList,
  TagDisplay,
} from "../pages/wrapperPage";
import AdminWorkbench from "../pages/admin/AdminWorkbench";
import WhitelistTester from "../pages/tools/WhitelistTester";
import ProductsPage from "../pages/items/ProductsPage";
import OrdersListPage from "../pages/transactions/OrdersListPage";
import OrderDetailPage from "../pages/transactions/OrderDetailPage";
import InvoicesListPage from "../pages/transactions/InvoicesListPage";
import InvoiceDetailPage from "../pages/transactions/InvoiceDetailPage";
import PurchaseOrderDetailPage from "../pages/transactions/PurchaseOrderDetailPage";
import ProposalDetailPage from "../pages/transactions/ProposalDetailPage";
import ProposalList from "../apps/transactions/models/proposal/pages/ProposalList";
import ProposalDetailVue from "../apps/transactions/models/proposal/pages/ProposalDetailVue";
import ProposalDetailVueReact from "../apps/transactions/models/proposal/pages/ProposalDetailVueReact";
import PurchaseOrderList from "../apps/transactions/models/purchase_order/pages/PurchaseOrderList";
import CallReportDetailPage from "../pages/actions/CallReportDetailPage";
import ServiceDetailPage from "../pages/actions/ServiceDetailPage";
import TaskMarkerDetailPage from "../pages/actions/TaskMarkerDetailPage";
// Redux store is not used directly here; pages connect as needed.
import Test from "../pages/test/Test";
import DocsIndex from "../pages/docs/DocsIndex";

const Router: React.FC = () => {
  return (
    // <Provider store={store}>
    <BrowserRouter>
      <ScrollToTop />
      <Toster />
      <Routes>
        {/* Public routes */}
        <Route path={PageRoutes.login} element={<SignIn />} />
        <Route path={PageRoutes.register} element={<SignUp />} />
        <Route path="/test" element={<Test />} />
        {/* Protected routes */}
        <Route element={<PrivateRoute />}>
          <Route path={PageRoutes.dashboard} element={<Home />} />
          <Route path={PageRoutes.profile} element={<UserProfiles />} />
          <Route path={PageRoutes.actionList} element={<ActionList />} />
          <Route path={PageRoutes.actionAdd} element={<ActionAdd />} />
          <Route path={PageRoutes.actionAdd + "/:id"} element={<ActionAdd />} />
          <Route
            path={PageRoutes.actionsCallReportAdd}
            element={<CallReportDetailPage defaultMode="add" />}
          />
          <Route
            path={PageRoutes.actionsCallReportDetail}
            element={<CallReportDetailPage />}
          />
          <Route
            path={PageRoutes.actionsServiceAdd}
            element={<ServiceDetailPage defaultMode="add" />}
          />
          <Route
            path={PageRoutes.actionsServiceDetail}
            element={<ServiceDetailPage />}
          />
          <Route
            path={PageRoutes.actionsTaskMarkerAdd}
            element={<TaskMarkerDetailPage defaultMode="add" />}
          />
          <Route
            path={PageRoutes.actionsTaskMarkerDetail}
            element={<TaskMarkerDetailPage />}
          />
          <Route path={PageRoutes.contactList} element={<ContactList />} />
          <Route path={PageRoutes.ContactDetail} element={<ContactDetail />} />
          <Route
            path={PageRoutes.ContactDetail + "/:id"}
            element={<ContactDetail />}
          />
          <Route path={PageRoutes.customerAdd} element={<CustomerAddPage />} />
          <Route
            path={PageRoutes.customerDetail}
            element={<CustomerDetailPage />}
          />
          <Route path={PageRoutes.settingList} element={<SettingList />} />
          <Route path={PageRoutes.settingAdd} element={<SettingAdd />} />
          <Route path={PageRoutes.domainList} element={<DomainList />} />
          <Route path={PageRoutes.domainAdd} element={<DomainAdd />} />
          <Route
            path={PageRoutes.notionTracker}
            element={<NotionTrackerPage />}
          />
          <Route path={PageRoutes.kanbanBoard} element={<KanbanBoardPage />} />
          <Route
            path={PageRoutes.kanbanBoardData}
            element={<KanbanBoardDataPage />}
          />
          <Route path={PageRoutes.kanbanGantt} element={<KanbanGanttPage />} />
          <Route path={PageRoutes.svarGantt} element={<SvarGanttPage />} />

          <Route path="/calendar" element={<Calendar />} />
          <Route path="/form-elements" element={<FormElements />} />
          <Route path="/basic-models" element={<BasicTables />} />
          <Route
            path={PageRoutes.adminWorkbench}
            element={<AdminWorkbench />}
          />
          <Route path={PageRoutes.whitelist} element={<WhitelistTester />} />
          <Route path={PageRoutes.docs} element={<DocsIndex />} />
          {/* Products */}
          <Route path={PageRoutes.products} element={<ProductsPage />} />
          {/* Transactions */}
          <Route
            path={PageRoutes.transactionsOrders}
            element={<OrdersListPage />}
          />
          <Route
            path={PageRoutes.transactionsOrderDetail}
            element={<OrderDetailPage />}
          />
          <Route
            path={PageRoutes.transactionsInvoices}
            element={<InvoicesListPage />}
          />
          <Route
            path={PageRoutes.transactionsInvoiceDetail}
            element={<InvoiceDetailPage />}
          />
          <Route
            path={PageRoutes.transactionsPurchaseOrderDetail}
            element={<PurchaseOrderDetailPage />}
          />
          <Route
            path={PageRoutes.transactionsProposals}
            element={<ProposalList />}
          />
          <Route
            path={PageRoutes.transactionsProposalDetail}
            element={<ProposalDetailPage />}
          />
          <Route path="/transactions/proposals/vue" element={<ProposalDetailVue />} />
          <Route path="/transactions/proposals/vuereact" element={<ProposalDetailVueReact />} />
          <Route
            path={PageRoutes.transactionsPurchaseOrders}
            element={<PurchaseOrderList />}
          />
          <Route
            path={PageRoutes.transactionsPurchaseOrderDetail}
            element={<PurchaseOrderDetailPage />}
          />
          {/* Accounts */}
          <Route path={PageRoutes.auditList} element={<AuditList />} />
          <Route path={PageRoutes.auditDetail} element={<AuditDetail />} />
          <Route path={PageRoutes.auditDisplay} element={<AuditDisplay />} />
          <Route path={PageRoutes.currencyList} element={<CurrencyList />} />
          <Route path={PageRoutes.currencyDetail} element={<CurrencyDetail />} />
          <Route path={PageRoutes.currencyDisplay} element={<CurrencyDisplay />} />
          <Route path={PageRoutes.exchangeRateList} element={<ExchangeRateList />} />
          <Route path={PageRoutes.exchangeRateDetail} element={<ExchangeRateDetail />} />
          <Route path={PageRoutes.exchangeRateDisplay} element={<ExchangeRateDisplay />} />
          <Route path={PageRoutes.exchangeTransactionList} element={<ExchangeTransactionList />} />
          <Route path={PageRoutes.exchangeTransactionDetail} element={<ExchangeTransactionDetail />} />
          <Route path={PageRoutes.exchangeTransactionDisplay} element={<ExchangeTransactionDisplay />} />
          <Route path={PageRoutes.glAccountList} element={<GLAccountList />} />
          <Route path={PageRoutes.glAccountDetail} element={<GLAccountDetail />} />
          <Route path={PageRoutes.glJournalList} element={<GLJournalList />} />
          <Route path={PageRoutes.glJournalDetail} element={<GLJournalDetail />} />
          <Route path={PageRoutes.glJournalDisplay} element={<GLJournalDisplay />} />
          <Route path={PageRoutes.ledgerList} element={<LedgerList />} />
          <Route path={PageRoutes.ledgerDisplay} element={<LedgerDisplay />} />
          <Route path={PageRoutes.taxJurisdictionList} element={<TaxJurisdictionList />} />
          <Route path={PageRoutes.taxJurisdictionDisplay} element={<TaxJurisdictionDisplay />} />
          <Route path={PageRoutes.termList} element={<TermList />} />
          <Route path={PageRoutes.termDisplay} element={<TermDisplay />} />

          {/* Communications */}
          <Route path={PageRoutes.commDomainList} element={<AppDomainList />} />
          <Route path={PageRoutes.commDomainDetail} element={<AppDomainDetail />} />
          <Route path={PageRoutes.commEmailList} element={<AppEmailList />} />
          <Route path={PageRoutes.commEmailDetail} element={<AppEmailDetail />} />
          <Route path={PageRoutes.commLocationList} element={<AppLocationList />} />
          <Route path={PageRoutes.commLocationDetail} element={<AppLocationDetail />} />
          <Route path={PageRoutes.commPhoneList} element={<AppPhoneList />} />
          <Route path={PageRoutes.commPhoneDetail} element={<AppPhoneDetail />} />

          {/* Core */}
          <Route path={PageRoutes.coreActionList} element={<ActionList />} />
          <Route path={PageRoutes.coreContactList} element={<CoreContactList />} />
          <Route path={PageRoutes.coreContactDetail} element={<CoreContactDetail />} />
          <Route path={PageRoutes.coreReportList} element={<CoreReportList />} />
          <Route path={PageRoutes.coreReportDetail} element={<CoreReportDetail />} />
          <Route path={PageRoutes.coreReportDisplay} element={<CoreReportDisplay />} />
          <Route path={PageRoutes.coreSettingList} element={<CoreSettingList />} />
          <Route path={PageRoutes.coreSettingDetail} element={<CoreSettingDetail />} />
          <Route path={PageRoutes.coreSettingDisplay} element={<CoreSettingDisplay />} />
          <Route path={PageRoutes.coreTemplateList} element={<CoreTemplateList />} />
          <Route path={PageRoutes.coreTemplateDetail} element={<CoreTemplateDetail />} />
          <Route path={PageRoutes.coreTemplateDisplay} element={<CoreTemplateDisplay />} />

          {/* Docs */}
          <Route path={PageRoutes.documentList} element={<DocumentList />} />
          <Route path={PageRoutes.documentDetail} element={<DocumentDetail />} />
          <Route path={PageRoutes.documentDisplay} element={<DocumentDisplay />} />
          <Route path={PageRoutes.linkageList} element={<LinkageList />} />
          <Route path={PageRoutes.linkageDisplay} element={<LinkageDisplay />} />
          <Route path={PageRoutes.linkageIndexList} element={<LinkageIndexList />} />
          <Route path={PageRoutes.linkageIndexDisplay} element={<LinkageIndexDisplay />} />
          <Route path={PageRoutes.questionAnswerList} element={<QuestionAnswerList />} />
          <Route path={PageRoutes.questionAnswerDisplay} element={<QuestionAnswerDisplay />} />
          <Route path={PageRoutes.tagList} element={<TagList />} />
          <Route path={PageRoutes.tagDisplay} element={<TagDisplay />} />
        </Route>

        {/* 404 page */}
        <Route path="*" element={<div>404 Not Found</div>} />
      </Routes>
    </BrowserRouter>
    // </Provider>
  );
};

export default Router;

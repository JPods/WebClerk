import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import PrivateRoute from "./PrivateRoute";
import { PageRoutes } from "./Routes";
import { ScrollToTop, Toster } from "../components/wrapper";
import {
  BasicTables,
  Calendar,
  ContactList,
  CustomerList,
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
  DomainList,
  EmailList,
  AppLocationList,
  AppPhoneList,
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
  SalesOrderDetailTest,
} from "../pages/wrapperPage";
import AdminWorkbench from "../pages/admin/AdminWorkbench";
import WhitelistTester from "../pages/tools/WhitelistTester";
import ItemList from "../apps/products/models/item/pages/ItemList";
import SalesOrderDetail from "../apps/transactions/models/sales_order/pages/SalesOrderDetail_test";
import InvoiceList from "../apps/transactions/models/invoice/pages/InvoiceList";
import InvoiceDetail from "../apps/transactions/models/invoice/pages/InvoiceDetail";
import PurchaseOrderDetail from "../apps/transactions/models/purchase_order/pages/PurchaseOrderDetail";
import ProposalDetail from "../apps/transactions/models/proposal/pages/ProposalDetail";
import ProposalList from "../apps/transactions/models/proposal/pages/ProposalList";
import ProposalDetailVue from "../apps/transactions/models/proposal/pages/ProposalDetailVue";
import ProposalDetailVueReact from "../apps/transactions/models/proposal/pages/ProposalDetailVueReact";
import PurchaseOrderList from "../apps/transactions/models/purchase_order/pages/PurchaseOrderList";
import SalesOrderList from "../apps/transactions/models/sales_order/pages/SalesOrderList";
// Redux store is not used directly here; pages connect as needed.
import Test from "../pages/test/Test";
import DocumentIndex from "../apps/docs/models/document/pages/DocumentIndex";

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
          <Route path={PageRoutes.contactList} element={<ContactList />} />
          <Route path={PageRoutes.customerList} element={<CustomerList />} />
          {/* <Route
            path={PageRoutes.customerDetail}
            element={<CustomerDetailPage />}
          /> */}
          <Route path={PageRoutes.settingList} element={<SettingList />} />
          <Route path={PageRoutes.settingAdd} element={<SettingAdd />} />
          <Route path={PageRoutes.domainList} element={<DomainList />} />
          <Route path={PageRoutes.emailList} element={<EmailList />} />
          <Route path={PageRoutes.locationList} element={<AppLocationList />} />
          <Route path={PageRoutes.phoneList} element={<AppPhoneList />} />

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
          <Route path={PageRoutes.docs} element={<DocumentIndex />} />
          {/* Products */}
          <Route path={PageRoutes.products} element={<ItemList />} />
          {/* Transactions */}
          <Route
            path={PageRoutes.transactionsOrders}
            element={<SalesOrderList />}
          />
          <Route
            path={PageRoutes.transactionsOrderDetail}
            element={<SalesOrderDetail />}
          />
          <Route
            path={PageRoutes.transactionsOrderDetailTest}
            element={<SalesOrderDetailTest />}
          />
          <Route
            path={PageRoutes.transactionsInvoices}
            element={<InvoiceList />}
          />
          <Route
            path={PageRoutes.transactionsInvoiceDetail}
            element={<InvoiceDetail />}
          />
          <Route
            path={PageRoutes.transactionsPurchaseOrderDetail}
            element={<PurchaseOrderDetail />}
          />
          <Route
            path={PageRoutes.transactionsProposals}
            element={<ProposalList />}
          />
          <Route
            path={PageRoutes.transactionsProposalDetail}
            element={<ProposalDetail />}
          />
          <Route
            path="/transactions/proposals/vue"
            element={<ProposalDetailVue />}
          />
          <Route
            path="/transactions/proposals/vuereact"
            element={<ProposalDetailVueReact />}
          />
          <Route
            path={PageRoutes.transactionsPurchaseOrders}
            element={<PurchaseOrderList />}
          />
          <Route
            path={PageRoutes.transactionsPurchaseOrderDetail}
            element={<PurchaseOrderDetail />}
          />
          {/* Accounts */}
          <Route path={PageRoutes.auditList} element={<AuditList />} />
          <Route path={PageRoutes.auditDetail} element={<AuditDetail />} />
          <Route path={PageRoutes.auditDisplay} element={<AuditDisplay />} />
          <Route path={PageRoutes.currencyList} element={<CurrencyList />} />
          <Route
            path={PageRoutes.currencyDisplay}
            element={<CurrencyDisplay />}
          />
          <Route
            path={PageRoutes.exchangeRateList}
            element={<ExchangeRateList />}
          />
          <Route
            path={PageRoutes.exchangeRateDisplay}
            element={<ExchangeRateDisplay />}
          />
          <Route
            path={PageRoutes.exchangeTransactionList}
            element={<ExchangeTransactionList />}
          />
          <Route
            path={PageRoutes.exchangeTransactionDisplay}
            element={<ExchangeTransactionDisplay />}
          />
        </Route>

        {/* 404 page */}
        <Route path="*" element={<div>404 Not Found</div>} />
      </Routes>
    </BrowserRouter>
    // </Provider>
  );
};

export default Router;

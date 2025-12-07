import NotFound from "./OtherPage/NotFound";
import SignIn from "./AuthPages/SignIn";
import SignUp from "./AuthPages/SignUp";
import Home from "./Dashboard/Home";
import UserProfiles from "./UserProfile";
import ContactDetail from "../apps/core/models/contact/pages/ContactDetail.tsx";
import ContactList from "../apps/core/models/contact/pages/ContactList";
import CustomerDetail from "../apps/core/models/customer/pages/CustomerDetail";
import SettingAdd from "./setting/SettingAdd";
import SettingList from "./setting/SettingList";
import DomainList from "../apps/communications/models/domain/pages/DomainList";
import DomainDetail from "../apps/communications/models/domain/pages/DomainDetail";

// Accounts
import AuditList from "../apps/accounts/models/audit/pages/AuditList";
import AuditDetail from "../apps/accounts/models/audit/pages/AuditDetail";
import AuditDisplay from "../apps/accounts/models/audit/pages/AuditDisplay";
import CurrencyList from "../apps/accounts/models/currency/pages/CurrencyList";
import CurrencyDetail from "../apps/accounts/models/currency/pages/CurrencyDetail";
import CurrencyDisplay from "../apps/accounts/models/currency/pages/CurrencyDisplay";
import ExchangeRateList from "../apps/accounts/models/exchange_rate/pages/ExchangeRateList";
import ExchangeRateDetail from "../apps/accounts/models/exchange_rate/pages/ExchangeRateDetail";
import ExchangeRateDisplay from "../apps/accounts/models/exchange_rate/pages/ExchangeRateDisplay";
import ExchangeTransactionList from "../apps/accounts/models/exchange_transaction/pages/ExchangeTransactionList";
import ExchangeTransactionDetail from "../apps/accounts/models/exchange_transaction/pages/ExchangeTransactionDetail";
import ExchangeTransactionDisplay from "../apps/accounts/models/exchange_transaction/pages/ExchangeTransactionDisplay";
import GLAccountList from "../apps/accounts/models/gl_account/pages/GLAccountList";
import GLAccountDetail from "../apps/accounts/models/gl_account/pages/GLAccountDetail";
import GLJournalList from "../apps/accounts/models/gl_journal/pages/GLJournalList";
import GLJournalDetail from "../apps/accounts/models/gl_journal/pages/GLJournalDetail";
import GLJournalDisplay from "../apps/accounts/models/gl_journal/pages/GLJournalDisplay";
import LedgerList from "../apps/accounts/models/ledger/pages/LedgerList";
import LedgerDisplay from "../apps/accounts/models/ledger/pages/LedgerDisplay";
import TaxJurisdictionList from "../apps/accounts/models/tax_jurisdiction/pages/TaxJurisdictionList";
import TaxJurisdictionDisplay from "../apps/accounts/models/tax_jurisdiction/pages/TaxJurisdictionDisplay";
import TermList from "../apps/accounts/models/term/pages/TermList";
import TermDisplay from "../apps/accounts/models/term/pages/TermDisplay";

// Communications
import AppDomainList from "../apps/communications/models/domain/pages/DomainList";
import AppDomainDetail from "../apps/communications/models/domain/pages/DomainDetail";
import AppEmailList from "../apps/communications/models/email/pages/EmailList";
import AppEmailDetail from "../apps/communications/models/email/pages/EmailDetail";
import AppLocationList from "../apps/communications/models/location/pages/LocationList";
import AppLocationDetail from "../apps/communications/models/location/pages/LocationDetail";
import AppPhoneList from "../apps/communications/models/phone/pages/PhoneList";
import AppPhoneDetail from "../apps/communications/models/phone/pages/PhoneDetail";

// Core
import CoreAction from "../apps/core/models/action/pages/Action";
import CoreContactList from "../apps/core/models/contact/pages/ContactList";
import CoreContactDetail from "../apps/core/models/contact/pages/ContactDetail";
import CoreReportList from "../apps/core/models/report/pages/ReportList";
import CoreReportDetail from "../apps/core/models/report/pages/ReportDetail";
import CoreReportDisplay from "../apps/core/models/report/pages/ReportDisplay";
import CoreSettingList from "../apps/core/models/setting/pages/SettingList";
import CoreSettingDetail from "../apps/core/models/setting/pages/SettingDetail";
import CoreSettingDisplay from "../apps/core/models/setting/pages/SettingDisplay";
import CoreTemplateList from "../apps/core/models/template/pages/TemplateList";
import CoreTemplateDetail from "../apps/core/models/template/pages/TemplateDetail";
import CoreTemplateDisplay from "../apps/core/models/template/pages/TemplateDisplay";

// Docs
import DocumentList from "../apps/docs/models/document/pages/DocumentList";
import DocumentDetail from "../apps/docs/models/document/pages/DocumentDetail";
import DocumentDisplay from "../apps/docs/models/document/pages/DocumentDisplay";
import LinkageList from "../apps/docs/models/linkage/pages/LinkageList";
import LinkageDisplay from "../apps/docs/models/linkage/pages/LinkageDisplay";
import LinkageIndexList from "../apps/docs/models/linkage_index/pages/LinkageIndexList";
import LinkageIndexDisplay from "../apps/docs/models/linkage_index/pages/LinkageIndexDisplay";
import QuestionAnswerList from "../apps/docs/models/question_answer/pages/QuestionAnswerList";
import QuestionAnswerDisplay from "../apps/docs/models/question_answer/pages/QuestionAnswerDisplay";
import TagList from "../apps/docs/models/tag/pages/TagList";
import TagDisplay from "../apps/docs/models/tag/pages/TagDisplay";

import Calendar from "./Calendar";
import FormElements from "./Forms/FormElements";
import BasicTables from "./Tables/BasicTables";
import AdminWorkbench from "./admin/AdminWorkbench";
import SalesOrderDetail from "../apps/transactions/models/sales_order/pages/SalesOrderDetail";
import InvoiceDetail from "../apps/transactions/models/invoice/pages/InvoiceDetail";
import PurchaseOrderDetail from "../apps/transactions/models/purchase_order/pages/PurchaseOrderDetail";
import ProposalDetail from "../apps/transactions/models/proposal/pages/ProposalDetail";
import ProposalList from "../apps/transactions/models/proposal/pages/ProposalList";
import PurchaseOrderList from "../apps/transactions/models/purchase_order/pages/PurchaseOrderList";
import NotionTrackerPage from "./notion/NotionTrackerPage.tsx";
import KanbanBoardPage from "./kanban/KanbanBoardPage";
import KanbanBoardDataPage from "./kanban/KanbanBoardDataPage";
import KanbanGanttPage from "./kanban/KanbanGanttPage";
import SvarGanttPage from "./kanban/SvarGanttPage";

export {
  SignIn,
  SignUp,
  NotFound,
  SalesOrderDetail,
  InvoiceDetail,
  PurchaseOrderDetail,
  ProposalDetail,
  ProposalList,
  PurchaseOrderList,
  Home,
  UserProfiles,
  ContactDetail,
  ContactList,
  CustomerDetail,
  SettingAdd,
  SettingList,
  DomainDetail,
  DomainList,
  Calendar,
  FormElements,
  BasicTables,
  AdminWorkbench,
  NotionTrackerPage,
  KanbanBoardPage,
  KanbanBoardDataPage,
  KanbanGanttPage,
  SvarGanttPage,
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
  CoreAction,
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
};

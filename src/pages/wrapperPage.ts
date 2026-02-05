import NotFound from "./OtherPage/NotFound";
import SignIn from "./AuthPages/SignIn";
import SignUp from "./AuthPages/SignUp";
import Home from "./Dashboard/Home";
import UserProfiles from "./UserProfile";

// Accounts
import AuditList from "../apps/accounts/models/audit/pages/AuditList";
import AuditDetail from "../apps/accounts/models/audit/pages/AuditDetail";
import CurrencyList from "../apps/accounts/models/currency/pages/CurrencyList";
import CurrencyDetail from "../apps/accounts/models/currency/pages/CurrencyDetail";
import ExchangeRateList from "../apps/accounts/models/exchange_rate/pages/ExchangeRateList";
import ExchangeRateDetail from "../apps/accounts/models/exchange_rate/pages/ExchangeRateDetail";
import ExchangeTransactionList from "../apps/accounts/models/exchange_transaction/pages/ExchangeTransactionList";
import ExchangeTransactionDetail from "../apps/accounts/models/exchange_transaction/pages/ExchangeTransactionDetail";
import GLAccountList from "../apps/accounts/models/gl_account/pages/GLAccountList";
import GLAccountDetail from "../apps/accounts/models/gl_account/pages/GLAccountDetail";
import GLJournalList from "../apps/accounts/models/gl_journal/pages/GLJournalList";
import GLJournalDetail from "../apps/accounts/models/gl_journal/pages/GLJournalDetail";
import LedgerList from "../apps/accounts/models/ledger/pages/LedgerList";
import TaxJurisdictionList from "../apps/accounts/models/tax_jurisdiction/pages/TaxJurisdictionList";
import TermList from "../apps/accounts/models/term/pages/TermList";

// Communications
import DomainList from "../apps/communications/models/domain/pages/DomainList";
import DomainDetail from "../apps/communications/models/domain/pages/DomainDetail";
import EmailList from "../apps/communications/models/email/pages/EmailList";
import EmailDetail from "../apps/communications/models/email/pages/EmailDetail";
import AppAddressList from "../apps/communications/models/address/pages/AddressList";
import AppAddressDetail from "../apps/communications/models/address/pages/AddressDetail";
import AppPhoneList from "../apps/communications/models/phone/pages/PhoneList";
import AppPhoneDetail from "../apps/communications/models/phone/pages/PhoneDetail";

// Orgs
import CustomerList from "../apps/orgs/models/customer/pages/CustomerList";
import CustomerDetailPage from "../apps/orgs/models/customer/pages/CustomerDetail";
import CustomerAddPage from "../apps/orgs/models/customer/pages/CustomerAddPage";
import CustomerEditPage from "../apps/orgs/models/customer/pages/CustomerEditPage";
import EmployeeList from "../apps/orgs/models/employee/pages/EmployeeList";
import ManufacturerList from "../apps/orgs/models/manufacturer/pages/ManufacturerList";
import OrganizationsList from "../apps/orgs/models/organization/pages/OrganizationList";
import RepList from "../apps/orgs/models/rep/pages/RepList";
import VendorList from "../apps/orgs/models/vendor/pages/VendorList";

// Core
import CoreContactList from "../apps/core/models/contact/pages/ContactList";
import CoreContactDetail from "../apps/core/models/contact/pages/ContactDetail";
import CoreReportList from "../apps/core/models/report/pages/ReportList";
import CoreReportDetail from "../apps/core/models/report/pages/ReportDetail";
import CoreSettingList from "../apps/core/models/setting/pages/SettingList";
import CoreSettingDetail from "../apps/core/models/setting/pages/SettingDetail";
import CoreTemplateList from "../apps/core/models/template/pages/TemplateList";
import CoreTemplateDetail from "../apps/core/models/template/pages/TemplateDetail";

// Docs
import DocumentList from "../apps/docs/models/document/pages/DocumentList";
import DocumentDetail from "../apps/docs/models/document/pages/DocumentDetail";
import LinkageList from "../apps/docs/models/linkage/pages/LinkageList";
import LinkageIndexList from "../apps/docs/models/linkage_index/pages/LinkageIndexList";
import QuestionAnswerList from "../apps/docs/models/question_answer/pages/QuestionAnswerList";
import TagList from "../apps/docs/models/tag/pages/TagList";

import KanbanBoardPage from "../apps/utils/kanban/KanbanBoardPage";
import KanbanBoardDataPage from "../apps/utils/kanban/KanbanBoardDataPage";
import KanbanGanttPage from "../apps/utils/gantt/GanttPage";
import SvarGanttPage from "../apps/utils/gantt/SvarGanttPage";
import MultiProjectGanttPage from "../apps/utils/gantt/MultiProjectGanttPage";
import NotionTrackerPage from "./notion/NotionTrackerPage";

export {
  SignIn,
  SignUp,
  NotFound,
  Home,
  UserProfiles,
  CustomerList,
  CustomerDetailPage,
  CustomerAddPage,
  CustomerEditPage,
  EmployeeList,
  ManufacturerList,
  OrganizationsList,
  RepList,
  VendorList,
  NotionTrackerPage,
  KanbanBoardPage,
  KanbanBoardDataPage,
  KanbanGanttPage,
  SvarGanttPage,
  MultiProjectGanttPage,
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
  DomainList,
  DomainDetail,
  EmailList,
  EmailDetail,
  AppAddressList,
  AppAddressDetail,
  AppPhoneList,
  AppPhoneDetail,
  CoreContactList,
  CoreContactDetail,
  CoreReportList,
  CoreReportDetail,
  CoreSettingList,
  CoreSettingDetail,
  CoreTemplateList,
  CoreTemplateDetail,
  DocumentList,
  DocumentDetail,
  LinkageList,
  LinkageIndexList,
  QuestionAnswerList,
  TagList,
};

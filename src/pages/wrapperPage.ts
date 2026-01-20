import NotFound from "./OtherPage/NotFound";
import SignIn from "./AuthPages/SignIn";
import SignUp from "./AuthPages/SignUp";
import Home from "./Dashboard/Home";
import UserProfiles from "./UserProfile";

// Accounts
import AuditList from "../api/apps/accounts/models/audit/pages/AuditList";
import AuditDetail from "../api/apps/accounts/models/audit/pages/AuditDetail";
import CurrencyList from "../api/apps/accounts/models/currency/pages/CurrencyList";
import CurrencyDetail from "../api/apps/accounts/models/currency/pages/CurrencyDetail";
import ExchangeRateList from "../api/apps/accounts/models/exchange_rate/pages/ExchangeRateList";
import ExchangeRateDetail from "../api/apps/accounts/models/exchange_rate/pages/ExchangeRateDetail";
import ExchangeTransactionList from "../api/apps/accounts/models/exchange_transaction/pages/ExchangeTransactionList";
import ExchangeTransactionDetail from "../api/apps/accounts/models/exchange_transaction/pages/ExchangeTransactionDetail";
import GLAccountList from "../api/apps/accounts/models/gl_account/pages/GLAccountList";
import GLAccountDetail from "../api/apps/accounts/models/gl_account/pages/GLAccountDetail";
import GLJournalList from "../api/apps/accounts/models/gl_journal/pages/GLJournalList";
import GLJournalDetail from "../api/apps/accounts/models/gl_journal/pages/GLJournalDetail";
import LedgerList from "../api/apps/accounts/models/ledger/pages/LedgerList";
import TaxJurisdictionList from "../api/apps/accounts/models/tax_jurisdiction/pages/TaxJurisdictionList";
import TermList from "../api/apps/accounts/models/term/pages/TermList";

// Communications
import DomainList from "../api/apps/communications/models/domain/pages/DomainList";
import DomainDetail from "../api/apps/communications/models/domain/pages/DomainDetail";
import EmailList from "../api/apps/communications/models/email/pages/EmailList";
import EmailDetail from "../api/apps/communications/models/email/pages/EmailDetail";
import AppLocationList from "../api/apps/communications/models/location/pages/LocationList";
import AppLocationDetail from "../api/apps/communications/models/location/pages/LocationDetail";
import AppPhoneList from "../api/apps/communications/models/phone/pages/PhoneList";
import AppPhoneDetail from "../api/apps/communications/models/phone/pages/PhoneDetail";

// Orgs
import CustomerList from "../api/apps/orgs/models/customer/pages/CustomerList";
import EmployeeList from "../api/apps/orgs/models/employee/pages/EmployeeList";
import ManufacturerList from "../api/apps/orgs/models/manufacturer/pages/ManufacturerList";
import OrganizationsList from "../api/apps/orgs/models/organization/pages/OrganizationList";
import RepList from "../api/apps/orgs/models/rep/pages/RepList";
import VendorList from "../api/apps/orgs/models/vendor/pages/VendorList";

// Core
import CoreContactList from "../api/apps/core/models/contact/pages/ContactList";
import CoreContactDetail from "../api/apps/core/models/contact/pages/ContactDetail";
import CoreReportList from "../api/apps/core/models/report/pages/ReportList";
import CoreReportDetail from "../api/apps/core/models/report/pages/ReportDetail";
import CoreSettingList from "../api/apps/core/models/setting/pages/SettingList";
import CoreSettingDetail from "../api/apps/core/models/setting/pages/SettingDetail";
import CoreTemplateList from "../api/apps/core/models/template/pages/TemplateList";
import CoreTemplateDetail from "../api/apps/core/models/template/pages/TemplateDetail";

// Docs
import DocumentList from "../api/apps/docs/models/document/pages/DocumentList";
import DocumentDetail from "../api/apps/docs/models/document/pages/DocumentDetail";
import LinkageList from "../api/apps/docs/models/linkage/pages/LinkageList";
import LinkageIndexList from "../api/apps/docs/models/linkage_index/pages/LinkageIndexList";
import QuestionAnswerList from "../api/apps/docs/models/question_answer/pages/QuestionAnswerList";
import TagList from "../api/apps/docs/models/tag/pages/TagList";

import KanbanBoardPage from "../api/apps/utils/kanban/KanbanBoardPage";
import KanbanBoardDataPage from "../api/apps/utils/kanban/KanbanBoardDataPage";
import KanbanGanttPage from "../api/apps/utils/gantt/GanttPage";
import SvarGanttPage from "../api/apps/utils/gantt/SvarGanttPage";
import MultiProjectGanttPage from "../api/apps/utils/gantt/MultiProjectGanttPage";
import NotionTrackerPage from "./notion/NotionTrackerPage";

export {
  SignIn,
  SignUp,
  NotFound,
  Home,
  UserProfiles,
  CustomerList,
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
  AppLocationList,
  AppLocationDetail,
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

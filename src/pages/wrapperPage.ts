import NotFound from "./OtherPage/NotFound";
import SignIn from "./AuthPages/SignIn";
import SignUp from "./AuthPages/SignUp";
import Home from "./Dashboard/Home";
import UserProfiles from "./UserProfile";
import ActionList from "./actions/ActionList";
import ActionAdd from "./actions/ActionAdd";
import ContactDetail from "../apps/core/models/contact/pages/ContactDetail.tsx";
import ContactList from "../apps/core/models/contact/pages/ContactList";
import CustomerDetailPage from "./contacts/CustomerDetailPage";
import CustomerAddPage from "./contacts/CustomerAddPage";
import SettingAdd from "./setting/SettingAdd";
import SettingList from "./setting/SettingList";
import DomainAdd from "../apps/communications/domain/pages/domain";
import DomainList from "./domain/DomainList";

// Accounts
import AuditList from "../apps/accounts/models/audit/pages/AuditList";
import AuditDisplay from "../apps/accounts/models/audit/pages/AuditDisplay";
import CurrencyList from "../apps/accounts/models/currency/pages/CurrencyList";
import CurrencyDisplay from "../apps/accounts/models/currency/pages/CurrencyDisplay";
import ExchangeRateList from "../apps/accounts/models/exchange_rate/pages/ExchangeRateList";
import ExchangeRateDisplay from "../apps/accounts/models/exchange_rate/pages/ExchangeRateDisplay";
import ExchangeTransactionList from "../apps/accounts/models/exchange_transaction/pages/ExchangeTransactionList";
import ExchangeTransactionDisplay from "../apps/accounts/models/exchange_transaction/pages/ExchangeTransactionDisplay";

import Calendar from "./Calendar";
import FormElements from "./Forms/FormElements";
import BasicTables from "./Tables/BasicTables";
import AdminWorkbench from "./admin/AdminWorkbench";
import OrderDetailPage from "./transactions/OrderDetailPage";
import InvoiceDetailPage from "./transactions/InvoiceDetailPage";
import NotionTrackerPage from "./notion/NotionTrackerPage.tsx";
import KanbanBoardPage from "./kanban/KanbanBoardPage";
import KanbanBoardDataPage from "./kanban/KanbanBoardDataPage";
import KanbanGanttPage from "./kanban/KanbanGanttPage";
import SvarGanttPage from "./kanban/SvarGanttPage";

export {
  SignIn,
  SignUp,
  NotFound,
  OrderDetailPage,
  InvoiceDetailPage,
  Home,
  UserProfiles,
  ActionList,
  ActionAdd,
  ContactDetail,
  ContactList,
  CustomerDetailPage,
  CustomerAddPage,
  SettingAdd,
  SettingList,
  DomainAdd,
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
  AuditDisplay,
  CurrencyList,
  CurrencyDisplay,
  ExchangeRateList,
  ExchangeRateDisplay,
  ExchangeTransactionList,
  ExchangeTransactionDisplay,
};

/* LastChecked: 2026-06-28 | WhereUsed: Router.tsx | WhoCreated: Unknown */
/* Admin-managed models removed — they use the DataBrowser (/admin-wb) now. */
import NotFound from "./OtherPage/NotFound";
import SignIn from "./AuthPages/SignIn";
import SignUp from "./AuthPages/SignUp";
import Home from "./Dashboard/Home";
import UserProfiles from "./UserProfile";

// Orgs — user-facing only
import CustomerList from "../apps/orgs/models/customer/pages/CustomerList";
import CustomerDetail from "../apps/orgs/models/customer/pages/CustomerDetail";

// Alias CustomerDetail for route compatibility
const CustomerDetailPage = CustomerDetail;
const CustomerAddPage = CustomerDetail;
const CustomerEditPage = CustomerDetail;

// Core — user-facing only
import CoreContactList from "../apps/core/models/contact/pages/ContactList";
import CoreContactDetail from "../apps/core/models/contact/pages/ContactDetail";

import KanbanBoardPage from "../apps/utils/kanban/KanbanBoardPage";
import KanbanBoardDataPage from "../apps/utils/kanban/KanbanBoardDataPage";
import UnifiedGanttPage from "../apps/utils/gantt/UnifiedGanttPage";
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
  CoreContactList,
  CoreContactDetail,
  NotionTrackerPage,
  KanbanBoardPage,
  KanbanBoardDataPage,
  UnifiedGanttPage,
};

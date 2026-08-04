/* LastChecked: 2026-07-10 | WhereUsed: Router.tsx, protectedRoutesConfig.tsx | WhoCreated: Unknown */
/* All list views use DataBrowser (/db/:model). Only detail pages and tools here. */
import NotFound from "./OtherPage/NotFound";
import SignIn from "./AuthPages/SignIn";
import SignUp from "./AuthPages/SignUp";
import Home from "./Dashboard/Home";
import UserProfiles from "./UserProfile";

// Orgs — now use OrgDetailJson (lists via DataBrowser)
import OrgDetailJson from "../apps/orgs/components/OrgDetail.json";

// Alias for route compatibility
const CustomerDetailPage = OrgDetailJson;
const CustomerAddPage = OrgDetailJson;
const CustomerEditPage = OrgDetailJson;

// Core — detail page only (list via DataBrowser)
import CoreContactDetail from "../apps/core/models/contact/pages/ContactDetailJson";

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
  CustomerDetailPage,
  CustomerAddPage,
  CustomerEditPage,
  CoreContactDetail,
  NotionTrackerPage,
  KanbanBoardPage,
  KanbanBoardDataPage,
  UnifiedGanttPage,
};

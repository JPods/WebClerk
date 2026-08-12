/* LastChecked: 2026-07-10 | WhereUsed: Router.tsx, protectedRoutesConfig.tsx | WhoCreated: Unknown */
/* All list views use DataBrowser (/:model). Only detail pages and tools here. */
import NotFound from "./NotFoundPage";
import SignIn from "./AuthPages/SignIn";
import SignUp from "./AuthPages/SignUp";
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
import Placeholder from "./Placeholder";
const NotionTrackerPage = () => Placeholder({ title: "Notion Tracker" });

export {
  SignIn,
  SignUp,
  NotFound,
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

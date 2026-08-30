/* LastChecked: 2026-08-30 | WhereUsed: Router.tsx, protectedRoutesConfig.tsx | WhoCreated: Unknown */
/* Heavy components (KanbanBoardPage, UnifiedGanttPage) removed — lazy-load directly */
import NotFound from "./NotFoundPage";
import SignIn from "./AuthPages/SignIn";
import SignUp from "./AuthPages/SignUp";
import UserProfiles from "./UserProfile";

import KanbanBoardDataPage from "../apps/utils/kanban/KanbanBoardDataPage";
import Placeholder from "./Placeholder";
const NotionTrackerPage = () => Placeholder({ title: "Notion Tracker" });

export {
  SignIn,
  SignUp,
  NotFound,
  UserProfiles,
  NotionTrackerPage,
  KanbanBoardDataPage,
};

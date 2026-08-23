/* LastChecked: 2026-08-21 | WhereUsed: Router.tsx, protectedRoutesConfig.tsx | WhoCreated: Unknown */
import NotFound from "./NotFoundPage";
import SignIn from "./AuthPages/SignIn";
import SignUp from "./AuthPages/SignUp";
import UserProfiles from "./UserProfile";

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
  NotionTrackerPage,
  KanbanBoardPage,
  KanbanBoardDataPage,
  UnifiedGanttPage,
};

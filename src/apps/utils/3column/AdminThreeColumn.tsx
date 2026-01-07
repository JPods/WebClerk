import type { AdminWorkspaceConfig } from "./types";
import { AdminWorkspaceProvider } from "./AdminWorkspaceProvider";
import { AppTableColumn } from "./components/AppTableColumn";
import { RecordListColumn } from "./components/RecordListColumn";
import { RecordDetailColumn } from "./components/RecordDetailColumn";

type AdminThreeColumnProps = {
  config: AdminWorkspaceConfig;
  className?: string;
};

export const AdminThreeColumn = ({ config, className }: AdminThreeColumnProps) => (
  <AdminWorkspaceProvider config={config}>
    <div className={`flex h-full min-h-[640px] w-full flex-col overflow-hidden rounded-xl border border-slate-200 bg-slate-100 shadow-lg dark:border-slate-800 dark:bg-slate-950 ${className ?? ""}`}>
      <div className="flex h-full flex-1 flex-col lg:flex-row">
        <div className="lg:w-1/4 xl:w-[22%]">
          <AppTableColumn />
        </div>
        <div className="lg:w-2/5 xl:w-[38%]">
          <RecordListColumn />
        </div>
        <div className="flex-1">
          <RecordDetailColumn />
        </div>
      </div>
    </div>
  </AdminWorkspaceProvider>
);

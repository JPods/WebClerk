/**
 * ProjectDetail - Refactored to use TransactionDetailBase
 * Standardized to match OrderDetail.tsx pattern
 */
import React, { useCallback } from "react";
import {
  FaProjectDiagram,
  FaCalendar,
  FaTasks,
} from "react-icons/fa";

// Import base component and shared types
import TransactionDetailBase, { TransactionTab } from "../../../components/TransactionDetailBase";
import FieldLabel from "../../../components/FieldLabel";

// Import types
import type { Transaction, TransactionStatus } from "../../../types/transactionTypes";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

// Project specific fields that extend base Transaction
interface Project extends Transaction {
  ida?: string;
  name?: string;
  description?: string;
  status: TransactionStatus;
  start_date?: string;
  end_date?: string;
}

// Status Badge Component  
const StatusBadge: React.FC<{ status?: string }> = ({ status }) => {
  const statusStyles: Record<string, string> = {
    planned: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
    active: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    completed: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    on_hold: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
    cancelled: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  };

  const styleKey = status ?? "planned";
  const styleClass = statusStyles[styleKey] ?? statusStyles.planned;

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${styleClass}`}>
      {status?.replace("_", " ") ?? "planned"}
    </span>
  );
};

// Format date for display
const formatDate = (dateStr?: string): string => {
  if (!dateStr) return "--";
  try {
    return new Date(dateStr).toLocaleDateString();
  } catch {
    return dateStr;
  }
};

// Dynamic tabs generator with badges based on data (like OrderDetail)
const getProjectTabsAfter = (_data: Transaction): TransactionTab[] => {
  // No additional tabs - actions are now in base
  return [];
};

// Custom Project Header Component
const ProjectHeader: React.FC<{
  data: Project;
  isEditing: boolean;
  onChange?: (field: keyof Project, value: unknown) => void;
}> = ({ data, isEditing, onChange }) => {
  // Extract customer info from refs.links
  const customerInfo = data.refs?.links?.customer?.[0];

  return (
    <div className="space-y-6">
      {/* Project Header Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Project Details */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaProjectDiagram className="text-blue-500" />
            Project Details
          </h3>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between items-center">
              <FieldLabel label="Name" mandatory className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <input
                  type="text"
                  value={data.name ?? ""}
                  onChange={(e) => onChange("name", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white font-medium">{data.name ?? "--"}</dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="ID" locked className="text-slate-500 dark:text-slate-400" />
              <dd className="font-mono text-slate-600 dark:text-slate-300">{data.id ?? "--"}</dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="IDA" locked className="text-slate-500 dark:text-slate-400" />
              <dd className="font-mono text-slate-600 dark:text-slate-300">{data.ida ?? "--"}</dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Status" mandatory className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <select
                  value={data.status ?? "planned"}
                  onChange={(e) => onChange("status", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                >
                  <option value="planned">Planned</option>
                  <option value="active">Active</option>
                  <option value="on_hold">On Hold</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              ) : (
                <dd><StatusBadge status={data.status} /></dd>
              )}
            </div>
          </dl>
        </div>

        {/* Center: Schedule */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaCalendar className="text-green-500" />
            Schedule
          </h3>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between items-center">
              <FieldLabel label="Start Date" className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <input
                  type="date"
                  value={data.start_date ? new Date(data.start_date).toISOString().split("T")[0] : ""}
                  onChange={(e) => onChange("start_date", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">{formatDate(data.start_date)}</dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="End Date" className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <input
                  type="date"
                  value={data.end_date ? new Date(data.end_date).toISOString().split("T")[0] : ""}
                  onChange={(e) => onChange("end_date", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">{formatDate(data.end_date)}</dd>
              )}
            </div>
          </dl>
        </div>

        {/* Right: Customer Info */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
            Customer
          </h3>
          {customerInfo ? (
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between">
                <FieldLabel label="Name" className="text-slate-500 dark:text-slate-400" />
                <dd className="text-slate-900 dark:text-white font-medium">{customerInfo.display_name ?? "--"}</dd>
              </div>
              <div className="flex justify-between">
                <FieldLabel label="IDA" className="text-slate-500 dark:text-slate-400" />
                <dd className="font-mono text-slate-600 dark:text-slate-300">{customerInfo.ida ?? "--"}</dd>
              </div>
            </dl>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400 italic">No customer linked</p>
          )}
        </div>
      </div>

      {/* Description */}
      {(data.description || isEditing) && (
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Description</h3>
          {isEditing && onChange ? (
            <textarea
              value={data.description ?? ""}
              onChange={(e) => onChange("description", e.target.value)}
              rows={4}
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
              placeholder="Project description..."
            />
          ) : (
            <p className="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
              {data.description || <span className="italic text-slate-400">No description</span>}
            </p>
          )}
        </div>
      )}
    </div>
  );
};

// Props interface
interface ProjectDetailProps {
  modeProp?: "view" | "edit" | "add";
  dataProp?: Project;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
  isAdmin?: boolean;
}

// Main Component
const ProjectDetail: React.FC<ProjectDetailProps> = (props) => {
  // Custom tab content renderer for actions
  const renderCustomTab = useCallback(
    (
      tabId: string,
      data: Transaction,
      _isEditing: boolean,
      _onFieldChange?: (field: string, value: unknown) => void,
    ) => {
      const projectData = data as Project;

      switch (tabId) {
        case "actions": {
          const actions = projectData.actions?.items ?? [];
          const statusClass = (status?: string) =>
            status === "done"
              ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
              : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";

          return (
            <div className="p-4">
              {actions.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <FaTasks size={32} className="mx-auto mb-3 opacity-50" />
                  <p>No actions on this project</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {actions.map((action, idx) => (
                    <div
                      key={action.id ?? idx}
                      className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700"
                    >
                      <div className="flex justify-between items-center">
                        <span className="font-medium text-slate-900 dark:text-white">
                          {typeof action.action === "object"
                            ? action.action?.en
                            : action.action ?? action.what ?? "--"}
                        </span>
                        <span className={`px-2 py-1 text-xs rounded-full ${statusClass(action.status)}`}>
                          {action.status ?? "pending"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        }
        default:
          return null;
      }
    },
    [],
  );

  // Custom header renderer
  const renderHeader = useCallback(
    (
      data: Transaction,
      isEditing: boolean,
      onChange?: (field: string, value: unknown) => void,
    ) => (
      <ProjectHeader
        data={data as Project}
        isEditing={isEditing}
        onChange={onChange as ((field: keyof Project, value: unknown) => void) | undefined}
      />
    ),
    [],
  );

  // Empty lines renderer (projects don't have lines)
  const renderLines = useCallback(() => null, []);

  // Check if project can be edited
  const canEdit = useCallback((data: Transaction) => {
    const status = data.status?.toLowerCase();
    return status !== "completed" && status !== "cancelled";
  }, []);

  return (
    <TransactionDetailBase
      transactionType="project"
      typeLabel="Project"
      modelName="tx_projects"
      getCustomTabsAfter={getProjectTabsAfter}
      renderCustomTab={renderCustomTab}
      renderHeader={renderHeader}
      renderLines={renderLines}
      isAdmin={props.isAdmin}
      canEdit={canEdit}
      inline={props.inline}
      modeProp={props.modeProp}
      dataProp={props.dataProp}
      onSaved={props.onSaved}
    />
  );
};

export default withDevIdentifier(ProjectDetail, 'ProjectDetail');
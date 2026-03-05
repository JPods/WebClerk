/**
 * RequisitionDetail - Refactored to use TransactionDetailBase
 * Standardized to match OrderDetail.tsx pattern
 */
import React, { useCallback } from "react";
import {
  FaClipboardList,
  FaInfoCircle,
  FaTasks,
} from "react-icons/fa";

// Import base component and shared types
import TransactionDetailBase, { TransactionTab } from "../../../components/TransactionDetailBase";
import FieldLabel from "../../../components/FieldLabel";

// Import types
import type { Transaction, TransactionStatus } from "../../../types/transactionTypes";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

// Requisition specific fields that extend base Transaction
interface Requisition extends Transaction {
  ida?: string;
  requisition_no?: string;
  status: TransactionStatus;
  requested_by?: string;
  department?: string;
  priority?: string;
  notes?: string;
}

// Status Badge Component  
const StatusBadge: React.FC<{ status?: string }> = ({ status }) => {
  const statusStyles: Record<string, string> = {
    draft: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
    pending: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
    approved: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    rejected: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    completed: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  };

  const styleKey = status ?? "draft";
  const styleClass = statusStyles[styleKey] ?? statusStyles.draft;

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${styleClass}`}>
      {status?.replace("_", " ") ?? "draft"}
    </span>
  );
};

// Priority Badge Component
const PriorityBadge: React.FC<{ priority?: string }> = ({ priority }) => {
  const priorityStyles: Record<string, string> = {
    low: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
    normal: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    high: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
    urgent: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  };

  const styleKey = priority ?? "normal";
  const styleClass = priorityStyles[styleKey] ?? priorityStyles.normal;

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${styleClass}`}>
      {priority ?? "normal"}
    </span>
  );
};

// Dynamic tabs generator with badges based on data (like OrderDetail)
const getRequisitionTabsAfter = (_data: Transaction): TransactionTab[] => {
  // No additional tabs - actions are now in base
  return [];
};

// Custom Requisition Header Component
const RequisitionHeader: React.FC<{
  data: Requisition;
  isEditing: boolean;
  onChange?: (field: keyof Requisition, value: unknown) => void;
}> = ({ data, isEditing, onChange }) => {
  return (
    <div className="space-y-6">
      {/* Requisition Header Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Requisition Details */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaClipboardList className="text-blue-500" />
            Requisition Details
          </h3>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between items-center">
              <FieldLabel label="Requisition No" mandatory className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <input
                  type="text"
                  value={data.requisition_no ?? ""}
                  onChange={(e) => onChange("requisition_no", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white font-medium font-mono">{data.requisition_no ?? "--"}</dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="ID" locked className="text-slate-500 dark:text-slate-400" />
              <dd className="font-mono text-slate-600 dark:text-slate-300">{data.id ?? "--"}</dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Status" mandatory className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <select
                  value={data.status ?? "draft"}
                  onChange={(e) => onChange("status", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                >
                  <option value="draft">Draft</option>
                  <option value="pending">Pending</option>
                  <option value="approved">Approved</option>
                  <option value="rejected">Rejected</option>
                  <option value="completed">Completed</option>
                </select>
              ) : (
                <dd><StatusBadge status={data.status} /></dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Priority" className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <select
                  value={data.priority ?? "normal"}
                  onChange={(e) => onChange("priority", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                >
                  <option value="low">Low</option>
                  <option value="normal">Normal</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              ) : (
                <dd><PriorityBadge priority={data.priority} /></dd>
              )}
            </div>
          </dl>
        </div>

        {/* Center: Requestor Info */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaInfoCircle className="text-green-500" />
            Requestor Info
          </h3>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between items-center">
              <FieldLabel label="Requested By" className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <input
                  type="text"
                  value={data.requested_by ?? ""}
                  onChange={(e) => onChange("requested_by", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">{data.requested_by ?? "--"}</dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Department" className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <input
                  type="text"
                  value={data.department ?? ""}
                  onChange={(e) => onChange("department", e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">{data.department ?? "--"}</dd>
              )}
            </div>
          </dl>
        </div>

        {/* Right: Notes */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
            Notes
          </h3>
          {isEditing && onChange ? (
            <textarea
              value={data.notes ?? ""}
              onChange={(e) => onChange("notes", e.target.value)}
              rows={4}
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
              placeholder="Add notes..."
            />
          ) : (
            <p className="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
              {data.notes || <span className="italic text-slate-400">No notes</span>}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

// Props interface
interface RequisitionDetailProps {
  modeProp?: "view" | "edit" | "add";
  dataProp?: Requisition;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
  isAdmin?: boolean;
}

// Main Component
const RequisitionDetail: React.FC<RequisitionDetailProps> = (props) => {
  // Custom tab content renderer for actions
  const renderCustomTab = useCallback(
    (
      tabId: string,
      data: Transaction,
      _isEditing: boolean,
      _onFieldChange?: (field: string, value: unknown) => void,
    ) => {
      const reqData = data as Requisition;

      switch (tabId) {
        case "actions": {
          const actions = reqData.actions?.items ?? [];
          const statusClass = (status?: string) =>
            status === "done" || status === "approved"
              ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
              : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";

          return (
            <div className="p-4">
              {actions.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <FaTasks size={32} className="mx-auto mb-3 opacity-50" />
                  <p>No actions on this requisition</p>
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
      <RequisitionHeader
        data={data as Requisition}
        isEditing={isEditing}
        onChange={onChange as ((field: keyof Requisition, value: unknown) => void) | undefined}
      />
    ),
    [],
  );

  // Empty lines renderer (requisitions don't have lines)
  const renderLines = useCallback(() => null, []);

  // Check if requisition can be edited
  const canEdit = useCallback((data: Transaction) => {
    const status = data.status?.toLowerCase();
    return status !== "completed" && status !== "rejected";
  }, []);

  return (
    <TransactionDetailBase
      transactionType="requisition"
      typeLabel="Requisition"
      modelName="tx_requisitions"
      getCustomTabsAfter={getRequisitionTabsAfter}
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

export default withDevIdentifier(RequisitionDetail, 'RequisitionDetail');
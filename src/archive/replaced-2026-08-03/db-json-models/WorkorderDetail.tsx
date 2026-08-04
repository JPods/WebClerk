/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * WorkorderDetail - Refactored to use TransactionDetailBase
 * Extends base with work order-specific fields and functionality
 */
import React, { useCallback } from 'react';
import {
  FaTasks,
} from 'react-icons/fa';

// Import base component and shared types
import TransactionDetailBase, { TransactionTab } from '../../../components/TransactionDetailBase';
import LinesCard from '../../../components/LinesCard';

// Import types
import type { Transaction, TransactionLine } from '../../../types/transactionTypes';
import { lineKey, getNextLineNumber } from '../../../utils/lineHelpers';

// Work Order specific fields that extend base Transaction
interface WorkOrder extends Transaction {
  ida?: string;
  workorder_no?: string;
  dt?: string;
  due_date?: string;
  start_date?: string;
  end_date?: string;
  priority?: string;
  assigned_to?: string;
  description?: string;
  notes?: string;
}

// Status Badge Component
const StatusBadge: React.FC<{ status?: string }> = ({ status }) => {
  const statusStyles: Record<string, string> = {
    draft: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
    pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    in_progress: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    canceled: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  };

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusStyles[status ?? 'draft'] ?? statusStyles.draft}`}>
      {status?.replace('_', ' ') ?? 'draft'}
    </span>
  );
};

// Priority Badge Component
const PriorityBadge: React.FC<{ priority?: string }> = ({ priority }) => {
  const priorityStyles: Record<string, string> = {
    low: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
    normal: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
    urgent: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  };

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${priorityStyles[priority ?? 'normal'] ?? priorityStyles.normal}`}>
      {priority ?? 'normal'}
    </span>
  );
};

// Custom Work Order Header Component
import SummaryCard from '../../../components/SummaryCard';
import { withDevIdentifier } from '@/components/common/DevIdentifier';
const WorkOrderHeader: React.FC<{
  data: WorkOrder;
  isEditing: boolean;
  onChange?: (field: keyof WorkOrder, value: unknown) => void;
}> = ({ data, isEditing, onChange }) => {
  return (
    <SummaryCard
      data={data}
      isEditing={isEditing}
      onChange={onChange}
      transactionLabel="Work Order"
      documentNoLabel="WO No"
      dueDateLabel="Due Date"
      showShipping={false}
      showCostMargin={true}
    />
  );
};

// Props interface
interface WorkOrderDetailProps {
  modeProp?: 'view' | 'edit' | 'add';
  dataProp?: WorkOrder;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
  isAdmin?: boolean;
}

// Dynamic tabs generator with badges based on data (like OrderDetail)
const getWorkorderTabsAfter = (_data: Transaction): TransactionTab[] => {
  // No additional tabs - actions are now in base
  return [];
};

// Main Component
const WorkorderDetail: React.FC<WorkOrderDetailProps> = (props) => {
  // Custom tab content renderer for actions
  const renderCustomTab = useCallback(
    (
      tabId: string,
      data: Transaction,
      isEditing: boolean,
      _onFieldChange?: (field: string, value: unknown) => void,
    ) => {
      const workorderData = data as WorkOrder;

      switch (tabId) {
        case "actions":
          const actions = workorderData.actions?.items ?? [];
          return (
            <div className="p-4">
              {actions.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <FaTasks size={32} className="mx-auto mb-3 opacity-50" />
                  <p>No actions on this work order</p>
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
                        <span
                          className={`px-2 py-1 text-xs rounded-full ${
                            action.status === "done"
                              ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                              : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                          }`}
                        >
                          {action.status ?? "pending"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        default:
          return null;
      }
    },
    [],
  );

  // Custom lines renderer using LinesCard
  const renderLines = useCallback(
    (
      lines: TransactionLine[],
      isEditing: boolean,
      data?: Transaction,
      onLinesChange?: (lines: TransactionLine[]) => void,
    ) => {
      return (
        <LinesCard
          lines={lines}
          isEditing={isEditing}
          isLocked={data?.is_locked}
          priceLevel="base"
          onDeleteLine={(lineId) => {
            if (onLinesChange) {
              onLinesChange(lines.filter((l, i) => lineKey(l, i) !== lineId));
            }
          }}
          transactionType="workorder"
          onDuplicateLine={(lineId) => {
            if (onLinesChange) {
              const lineToDup = lines.find((l, i) => lineKey(l, i) === lineId);
              if (lineToDup) {
                const { id, ...rest } = lineToDup;
                const newLine: TransactionLine = {
                  ...rest,
                  id: Date.now(),
                  line_number: getNextLineNumber(lines),
                };
                onLinesChange([...lines, newLine]);
              }
            }
          }}
          onLinesChange={onLinesChange}
        />
      );
    },
    [],
  );

  // Check if work order can be edited
  const canEdit = useCallback((data: Transaction) => {
    const status = data.status?.toLowerCase();
    return status !== "completed" && status !== "canceled" && status !== "closed";
  }, []);

  return (
    <TransactionDetailBase
      transactionType="workorder"
      typeLabel="Work Order"
      modelName="workorder"
      renderHeader={(data, isEditing, onChange) => (
        <WorkOrderHeader data={data as WorkOrder} isEditing={isEditing} onChange={onChange as any} />
      )}
      renderLines={renderLines}
      getCustomTabsAfter={getWorkorderTabsAfter}
      renderCustomTab={renderCustomTab}
      inline={props.inline}
      modeProp={props.modeProp}
      dataProp={props.dataProp}
      onCancelInline={props.onCancelInline}
      onSaved={props.onSaved}
      isAdmin={props.isAdmin}
      canEdit={canEdit}
    />
  );
};

export default withDevIdentifier(WorkorderDetail, 'WorkorderDetail');
/**
 * WorkorderDetail - Refactored to use TransactionDetailBase
 * Extends base with work order-specific fields and functionality
 */
import React from 'react';
import { 
  FaTools,
  FaClipboardList,
  FaCheck,
  FaClock,
} from 'react-icons/fa';

// Import base component and shared types
import TransactionDetailBase, { TransactionTab } from '../../../components/TransactionDetailBase';
import FieldLabel from '../../../components/FieldLabel';

// Import types
import type { Transaction } from '../../../types/transactionTypes';

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
const WorkOrderHeader: React.FC<{
  data: WorkOrder;
  isEditing: boolean;
  onChange?: (field: keyof WorkOrder, value: unknown) => void;
}> = ({ data, isEditing, onChange }) => {
  return (
    <div className="space-y-6">
      {/* Work Order Header Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Work Order Details */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaTools className="text-blue-500" />
            Work Order Details
          </h3>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between items-center">
              <FieldLabel label="WO No" mandatory locked className="text-slate-500 dark:text-slate-400" />
              <dd className="font-mono font-medium text-slate-900 dark:text-white">{data.ida ?? data.workorder_no ?? '--'}</dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="ID" locked className="text-slate-500 dark:text-slate-400" />
              <dd className="font-mono text-slate-600 dark:text-slate-300">{data.id ?? '--'}</dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Date" mandatory className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <input
                  type="date"
                  value={data.dt ? new Date(data.dt).toISOString().split('T')[0] : ''}
                  onChange={(e) => onChange('dt', e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.dt ? new Date(data.dt).toLocaleDateString() : '--'}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Due Date" className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <input
                  type="date"
                  value={data.due_date ? new Date(data.due_date).toISOString().split('T')[0] : ''}
                  onChange={(e) => onChange('due_date', e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.due_date ? new Date(data.due_date).toLocaleDateString() : '--'}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Status" mandatory className="text-slate-500 dark:text-slate-400" />
              <dd>
                <StatusBadge status={data.status} />
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Priority" className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <select
                  value={data.priority ?? 'normal'}
                  onChange={(e) => onChange('priority', e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                >
                  <option value="low">Low</option>
                  <option value="normal">Normal</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              ) : (
                <dd>
                  <PriorityBadge priority={data.priority} />
                </dd>
              )}
            </div>
          </dl>
        </div>

        {/* Middle: Schedule */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaClock className="text-green-500" />
            Schedule
          </h3>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between items-center">
              <FieldLabel label="Start Date" className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <input
                  type="date"
                  value={data.start_date ? new Date(data.start_date).toISOString().split('T')[0] : ''}
                  onChange={(e) => onChange('start_date', e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.start_date ? new Date(data.start_date).toLocaleDateString() : '--'}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="End Date" className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <input
                  type="date"
                  value={data.end_date ? new Date(data.end_date).toISOString().split('T')[0] : ''}
                  onChange={(e) => onChange('end_date', e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.end_date ? new Date(data.end_date).toLocaleDateString() : '--'}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Assigned To" className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <input
                  type="text"
                  value={data.assigned_to ?? ''}
                  onChange={(e) => onChange('assigned_to', e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">{data.assigned_to ?? '--'}</dd>
              )}
            </div>
          </dl>
        </div>

        {/* Right: Description */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaClipboardList className="text-purple-500" />
            Description
          </h3>
          <div className="text-sm">
            {isEditing && onChange ? (
              <textarea
                value={data.description ?? ''}
                onChange={(e) => onChange('description', e.target.value)}
                rows={4}
                className="w-full px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                placeholder="Work order description..."
              />
            ) : (
              <p className="text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
                {data.description || <span className="italic text-slate-400">No description</span>}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Notes Section */}
      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
        <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Notes</h3>
        {isEditing && onChange ? (
          <textarea
            value={data.notes ?? ''}
            onChange={(e) => onChange('notes', e.target.value)}
            rows={3}
            className="w-full px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
            placeholder="Additional notes..."
          />
        ) : (
          <p className="text-slate-700 dark:text-slate-300 text-sm whitespace-pre-wrap">
            {data.notes || <span className="italic text-slate-400">No notes</span>}
          </p>
        )}
      </div>
    </div>
  );
};

// Work Order Lines Tab Content
const WorkOrderLinesContent: React.FC<{
  data: WorkOrder;
  isEditing: boolean;
  onChange?: (field: keyof WorkOrder, value: unknown) => void;
}> = ({ data }) => {
  const lines = data.lines ?? [];

  if (lines.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500 dark:text-slate-400">
        <FaTools className="mx-auto text-4xl mb-4 opacity-50" />
        <p>No line items</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 dark:border-slate-700">
            <th className="text-left p-3 text-slate-600 dark:text-slate-300">Item</th>
            <th className="text-left p-3 text-slate-600 dark:text-slate-300">Description</th>
            <th className="text-right p-3 text-slate-600 dark:text-slate-300">Qty</th>
            <th className="text-center p-3 text-slate-600 dark:text-slate-300">Status</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line: any, index: number) => (
            <tr key={line.id || index} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50">
              <td className="p-3 font-mono text-slate-900 dark:text-white">{line.item_no ?? line.sku ?? '--'}</td>
              <td className="p-3 text-slate-700 dark:text-slate-300">{line.description ?? '--'}</td>
              <td className="p-3 text-right text-slate-900 dark:text-white">{line.quantity ?? '--'}</td>
              <td className="p-3 text-center">
                {line.completed ? (
                  <span className="inline-flex items-center gap-1 text-green-600">
                    <FaCheck size={12} /> Complete
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-slate-400">
                    <FaClock size={12} /> Pending
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
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

// Main Component
const WorkorderDetail: React.FC<WorkOrderDetailProps> = (props) => {
  return (
    <TransactionDetailBase
      transactionType="workorder"
      typeLabel="Work Order"
      modelName="work_order"
      renderHeader={(data, isEditing, onChange) => (
        <WorkOrderHeader data={data as WorkOrder} isEditing={isEditing} onChange={onChange as any} />
      )}
      renderLines={(lines, isEditing, data) => (
        <WorkOrderLinesContent data={data as WorkOrder} isEditing={isEditing} />
      )}
      inline={props.inline}
      modeProp={props.modeProp}
      dataProp={props.dataProp}
      onSaved={props.onSaved}
      onCancelInline={props.onCancelInline}
      isAdmin={props.isAdmin}
    />
  );
};

export default WorkorderDetail;
/**
 * WorkorderDetail - Refactored to use TransactionDetailBase
 * Extends base with work order-specific fields and functionality
 */
import React, { useCallback } from 'react';
import { 
  FaTools,
  FaClipboardList,
  FaCheck,
  FaClock,
  FaTasks,
} from 'react-icons/fa';

// Import base component and shared types
import TransactionDetailBase, { TransactionTab } from '../../../components/TransactionDetailBase';
import LinesCard from '../../../components/LinesCard';
import FieldLabel from '../../../components/FieldLabel';

// Import types
import type { Transaction, TransactionLine } from '../../../types/transactionTypes';

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

// Utility functions
const formatCurrency = (value?: number | null): string => {
  if (value === undefined || value === null) return '--';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value);
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
  onLinesChange?: (lines: TransactionLine[]) => void;
}> = ({ data, isEditing, onLinesChange }) => {
  const lines = data.lines ?? [];

  // Handler for adding items from search - uses COST for work orders
  const handleAddItem = useCallback((item: ItemSearchResult, quantity: number) => {
    if (!onLinesChange) return;
    
    const idaItem = resolveItemCode(item);
    const description = resolveItemDescription(item);
    const unitCost = resolveUnitCost(item);
    const unitPrice = resolveUnitPrice(item);
    const itemId = item.id ?? item.item_id ?? item.itemId ?? null;
    const unitMeasure = String(item.unit_of_measure ?? item.unitOfMeasure ?? item.unit_measure ?? 'EA');
    
    const newLine: TransactionLine = {
      _dirty: true,
      item: {
        item_id: itemId as number | null,
        ida_item: idaItem,
        description: description,
        unit_measure: unitMeasure,
      },
      quantity: {
        placed: quantity,
      },
      cost: {
        unit: unitCost,
        extended: unitCost * quantity,
      },
      price: {
        unit: unitPrice,
      },
    } as unknown as TransactionLine;
    
    onLinesChange([...lines, newLine]);
  }, [lines, onLinesChange]);

  return (
    <div className="space-y-6">
      {/* Item Search Panel - only in edit mode */}
      {isEditing && onLinesChange && (
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-2">Add Items</h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
            Search the catalog and add items to this work order.
          </p>
          <TransactionItemSearch onAddItem={handleAddItem} useCost={true} defaultQuantity={1} />
        </div>
      )}

      {/* Lines Table */}
      {!lines.length ? (
        <div className="text-center py-12 text-slate-500 dark:text-slate-400">
          <FaTools className="mx-auto text-4xl mb-4 opacity-50" />
          <p>No line items</p>
          {isEditing && (
            <p className="mt-2 text-sm">Use the search above to find and add products</p>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700">
                <th className="text-left p-3 text-slate-600 dark:text-slate-300">Item</th>
                <th className="text-left p-3 text-slate-600 dark:text-slate-300">Description</th>
                <th className="text-right p-3 text-slate-600 dark:text-slate-300">Qty</th>
                <th className="text-right p-3 text-slate-600 dark:text-slate-300">Unit Cost</th>
                <th className="text-right p-3 text-slate-600 dark:text-slate-300">Amount</th>
                <th className="text-center p-3 text-slate-600 dark:text-slate-300">Status</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line: any, index: number) => (
                <tr key={line.id || index} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                  <td className="p-3 font-mono text-slate-900 dark:text-white">{line.item?.ida_item ?? line.item_no ?? line.sku ?? '--'}</td>
                  <td className="p-3 text-slate-700 dark:text-slate-300">{line.item?.description ?? line.description ?? '--'}</td>
                  <td className="p-3 text-right text-slate-900 dark:text-white">{line.quantity?.placed ?? line.quantity ?? '--'}</td>
                  <td className="p-3 text-right text-slate-900 dark:text-white">{formatCurrency(line.cost?.unit ?? line.unit_cost)}</td>
                  <td className="p-3 text-right font-medium text-slate-900 dark:text-white">{formatCurrency(line.cost?.extended ?? line.amount)}</td>
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
      )}
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
              onLinesChange(lines.filter((l) => l.id !== lineId));
            }
          }}
          onUpdateLine={(lineId, field, value) => {
            if (onLinesChange) {
              onLinesChange(
                lines.map((l) => {
                  if (l.id !== lineId) return l;
                  const baseUpdate = { ...l, _dirty: true };
                  switch (field) {
                    case "qty":
                      return {
                        ...baseUpdate,
                        quantity: { ...l.quantity, placed: Number(value) },
                      };
                    case "description":
                      return {
                        ...baseUpdate,
                        item: { ...l.item, description: String(value) },
                      };
                    case "unit_price":
                      const newPrice = Number(value);
                      const qty = l.quantity?.placed ?? 0;
                      return {
                        ...baseUpdate,
                        price: {
                          ...l.price,
                          unit: newPrice,
                          extended: newPrice * qty,
                        },
                      };
                    default:
                      return { ...baseUpdate, [field]: value };
                  }
                }),
              );
            }
          }}
          onDuplicateLine={(lineId) => {
            if (onLinesChange) {
              const lineToDup = lines.find((l) => l.id === lineId);
              if (lineToDup) {
                const { id, ...rest } = lineToDup;
                const newLine: TransactionLine = {
                  ...rest,
                  id: Date.now(),
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
      onSaved={props.onSaved}
      isAdmin={props.isAdmin}
      canEdit={canEdit}
    />
  );
};

export default WorkorderDetail;
/**
 * ReceiptDetail - Refactored to use TransactionDetailBase
 * Extends base with receipt-specific fields and functionality
 */
import React, { useCallback } from 'react';
import { 
  FaBoxes,
  FaTruck,
  FaWarehouse,
} from 'react-icons/fa';

// Import base component and shared types
import TransactionDetailBase from '../../../components/TransactionDetailBase';
import FieldLabel from '../../../components/FieldLabel';
import {
  TransactionItemSearch,
  resolveItemCode,
  resolveItemDescription,
  resolveUnitCost,
  ItemSearchResult,
} from '../../../components';

// Import types
import type { Transaction, TransactionLine } from '../../../types/transactionTypes';
import { getNextLineNumber } from '../../../utils/lineHelpers';
import { withDevIdentifier } from '@/components/common/DevIdentifier';

// Receipt specific fields that extend base Transaction
interface Receipt extends Transaction {
  ida?: string;
  source_type?: 'purchase_receipt' | 'workorder_completion' | 'inventory_adjustment';
  dt_received?: string;
  notes?: string;
  purchase_id?: number;
  workorder_id?: number;
  // Related data from refs
  purchase?: { id: number; ida?: string };
  workorder?: { id: number; ida?: string };
}

// Status Badge Component
const StatusBadge: React.FC<{ status?: string }> = ({ status }) => {
  const statusStyles: Record<string, string> = {
    draft: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
    pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    canceled: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  };

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusStyles[status ?? 'draft'] ?? statusStyles.draft}`}>
      {status?.replace('_', ' ') ?? 'draft'}
    </span>
  );
};

// Source Type Badge Component
const SourceTypeBadge: React.FC<{ sourceType?: string }> = ({ sourceType }) => {
  const typeStyles: Record<string, { bg: string; label: string }> = {
    purchase_receipt: { bg: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400', label: 'Purchase Receipt' },
    workorder_completion: { bg: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400', label: 'WorkOrder Completion' },
    inventory_adjustment: { bg: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400', label: 'Inventory Adjustment' },
  };

  const style = typeStyles[sourceType ?? 'purchase_receipt'] ?? typeStyles.purchase_receipt;

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${style.bg}`}>
      {style.label}
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

// Custom Receipt Header Component
const ReceiptHeader: React.FC<{
  data: Receipt;
  isEditing: boolean;
  onChange?: (field: keyof Receipt, value: unknown) => void;
}> = ({ data, isEditing, onChange }) => {
  return (
    <div className="space-y-6">
      {/* Receipt Header Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Receipt Details */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaBoxes className="text-blue-500" />
            Receipt Details
          </h3>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between items-center">
              <FieldLabel label="Receipt No" mandatory locked className="text-slate-500 dark:text-slate-400" />
              <dd className="font-mono font-medium text-slate-900 dark:text-white">{data.ida ?? '--'}</dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="ID" locked className="text-slate-500 dark:text-slate-400" />
              <dd className="font-mono text-slate-600 dark:text-slate-300">{data.id ?? '--'}</dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Received" mandatory className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <input
                  type="datetime-local"
                  value={data.dt_received ? new Date(data.dt_received).toISOString().slice(0, 16) : ''}
                  onChange={(e) => onChange('dt_received', e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.dt_received ? new Date(data.dt_received).toLocaleString() : '--'}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Status" mandatory className="text-slate-500 dark:text-slate-400" />
              <dd>
                <StatusBadge status={data.status} />
              </dd>
            </div>
          </dl>
        </div>

        {/* Middle: Source Information */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaTruck className="text-green-500" />
            Source Information
          </h3>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between items-center">
              <FieldLabel label="Source Type" mandatory className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <select
                  value={data.source_type ?? 'purchase_receipt'}
                  onChange={(e) => onChange('source_type', e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                >
                  <option value="purchase_receipt">Purchase Receipt</option>
                  <option value="workorder_completion">WorkOrder Completion</option>
                  <option value="inventory_adjustment">Inventory Adjustment</option>
                </select>
              ) : (
                <dd><SourceTypeBadge sourceType={data.source_type} /></dd>
              )}
            </div>
            {(data.source_type === 'purchase_receipt' || !data.source_type) && (
              <div className="flex justify-between items-center">
                <FieldLabel label="Purchase Order" className="text-slate-500 dark:text-slate-400" />
                <dd className="text-slate-900 dark:text-white font-mono">
                  {data.purchase?.ida ?? data.purchase_id ?? '--'}
                </dd>
              </div>
            )}
            {data.source_type === 'workorder_completion' && (
              <div className="flex justify-between items-center">
                <FieldLabel label="Work Order" className="text-slate-500 dark:text-slate-400" />
                <dd className="text-slate-900 dark:text-white font-mono">
                  {data.workorder?.ida ?? data.workorder_id ?? '--'}
                </dd>
              </div>
            )}
          </dl>
        </div>

        {/* Right: Notes */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaWarehouse className="text-purple-500" />
            Notes
          </h3>
          {isEditing && onChange ? (
            <textarea
              value={data.notes ?? ''}
              onChange={(e) => onChange('notes', e.target.value)}
              rows={4}
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
              placeholder="Enter notes..."
            />
          ) : (
            <p className="text-sm text-slate-700 dark:text-slate-300">
              {data.notes || <span className="text-slate-400 italic">No notes</span>}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

// Receipt Lines Tab Content
const ReceiptLinesContent: React.FC<{
  data: Receipt;
  lines: TransactionLine[];
  isEditing: boolean;
  onLinesChange?: (lines: TransactionLine[]) => void;
}> = ({ lines, isEditing, onLinesChange }) => {
  // Handler for adding items from search - uses COST for receipts
  const handleAddItem = useCallback((item: ItemSearchResult, quantity: number) => {
    if (!onLinesChange) return;
    
    const idaItem = resolveItemCode(item);
    const description = resolveItemDescription(item);
    const unitCost = resolveUnitCost(item);
    const itemId = item.id ?? item.item_id ?? item.itemId ?? null;
    const unitMeasure = String(item.unit_of_measure ?? item.unitOfMeasure ?? item.unit_measure ?? 'EA');
    
    const newLine: TransactionLine = {
      _dirty: true,
      line_number: getNextLineNumber(lines),
      item: {
        item_id: itemId as number | null,
        ida_item: idaItem,
        description: description,
        unit_measure: unitMeasure,
      },
      quantity: {
        placed: quantity,
        received: quantity,
      },
      cost: {
        unit: unitCost,
        extended: unitCost * quantity,
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
            Search the catalog and add items to this receipt.
          </p>
          <TransactionItemSearch onAddItem={handleAddItem} useCost={true} defaultQuantity={1} />
        </div>
      )}

      {/* Lines Table */}
      {!lines.length ? (
        <div className="text-center py-12 text-slate-500 dark:text-slate-400">
          <FaBoxes className="mx-auto text-4xl mb-4 opacity-50" />
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
                <th className="text-right p-3 text-slate-600 dark:text-slate-300">Qty Received</th>
                <th className="text-right p-3 text-slate-600 dark:text-slate-300">Unit Cost</th>
                <th className="text-right p-3 text-slate-600 dark:text-slate-300">Amount</th>
                <th className="text-left p-3 text-slate-600 dark:text-slate-300">Warehouse</th>
                <th className="text-left p-3 text-slate-600 dark:text-slate-300">Lot/Serial</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line: any, index: number) => (
                <tr key={line.id || index} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                  <td className="p-3 font-mono text-slate-900 dark:text-white">{line.item?.ida_item ?? line.item_no ?? line.sku ?? '--'}</td>
                  <td className="p-3 text-slate-700 dark:text-slate-300">{line.item?.description ?? line.description ?? line.item_description ?? '--'}</td>
                  <td className="p-3 text-right text-slate-900 dark:text-white">{line.quantity?.staged ?? quantity?.placed ?? line.quantity?.received ?? line.qty_received ?? '--'}</td>
                  <td className="p-3 text-right text-slate-900 dark:text-white">{formatCurrency(line.cost?.unit ?? line.unit_cost)}</td>
                  <td className="p-3 text-right font-medium text-slate-900 dark:text-white">{formatCurrency(line.cost?.extended ?? line.amount ?? line.line_total)}</td>
                  <td className="p-3 text-slate-700 dark:text-slate-300">{line.warehouse?.name ?? line.warehouse_id ?? '--'}</td>
                  <td className="p-3 text-slate-700 dark:text-slate-300">{line.lot || line.serial_batch || '--'}</td>
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
interface ReceiptDetailProps {
  modeProp?: 'view' | 'edit' | 'add';
  dataProp?: Receipt;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
  isAdmin?: boolean;
  /** Direct ID prop for /wcapi/get/?id=X style routes */
  idProp?: number | string;
  id?: number | string;
  recordId?: number | string;
}

// Main Component
const ReceiptDetail: React.FC<ReceiptDetailProps> = (props) => {
  // Resolve ID from various prop names
  const resolvedId = props.idProp ?? props.id ?? props.recordId;

  return (
    <TransactionDetailBase
      transactionType="receipt"
      typeLabel="Receipt"
      modelName="receipt"
      renderHeader={(data, isEditing, onChange) => (
        <ReceiptHeader data={data as Receipt} isEditing={isEditing} onChange={onChange as any} />
      )}
      renderLines={(lines, isEditing, data, onLinesChange) => (
        <ReceiptLinesContent data={data as Receipt} lines={lines} isEditing={isEditing} onLinesChange={onLinesChange} />
      )}
      inline={props.inline}
      modeProp={props.modeProp}
      dataProp={props.dataProp}
      idProp={resolvedId}
      onSaved={props.onSaved}
      isAdmin={props.isAdmin}
    />
  );
};

export default withDevIdentifier(ReceiptDetail, 'ReceiptDetail');
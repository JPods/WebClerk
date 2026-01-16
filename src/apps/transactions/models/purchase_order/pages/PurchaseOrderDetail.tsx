/**
 * PurchaseOrderDetail - Refactored to use TransactionDetailBase
 * Extends base with purchase order-specific fields and functionality
 */
import React, { useCallback } from 'react';
import { 
  FaShoppingBag,
  FaTruck,
  FaCheck,
  FaTimes,
} from 'react-icons/fa';

// Import base component and shared types
import TransactionDetailBase, { TransactionTab } from '../../../components/TransactionDetailBase';
import FieldLabel from '../../../components/FieldLabel';
import { VendorSelector } from '../../../components/PartySelector';
import {
  TransactionItemSearch,
  resolveItemCode,
  resolveItemDescription,
  resolveUnitPrice,
  resolveUnitCost,
  ItemSearchResult,
} from '../../../components';

// Import types
import type { Transaction, TransactionLine } from '../../../types/transactionTypes';

// Purchase Order specific fields that extend base Transaction
interface PurchaseOrder extends Transaction {
  ida?: string;
  purchase_order_no?: string;
  receipt_id?: string;
  vendor_pack_list?: string;
  vendor_pack_date?: string;
  dt?: string;
  terms?: string;
  due_date?: string;
  ship_date?: string;
  id_vendor?: number;
  // Computed totals
  subtotal?: number;
  tax?: number;
  total?: number;
}

// Status Badge Component
const StatusBadge: React.FC<{ status?: string }> = ({ status }) => {
  const statusStyles: Record<string, string> = {
    draft: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
    approved: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    rejected: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    received: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    closed: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400',
  };

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusStyles[status ?? 'draft'] ?? statusStyles.draft}`}>
      {status?.replace('_', ' ') ?? 'draft'}
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

// Custom Purchase Order Header Component
const PurchaseOrderHeader: React.FC<{
  data: PurchaseOrder;
  isEditing: boolean;
  onChange?: (field: keyof PurchaseOrder, value: unknown) => void;
}> = ({ data, isEditing, onChange }) => {
  // Extract vendor info from refs.links
  const vendorInfo = data.refs?.links?.vendor?.[0];

  return (
    <div className="space-y-6">
      {/* Purchase Order Header Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: PO Details */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaShoppingBag className="text-blue-500" />
            Purchase Order Details
          </h3>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between items-center">
              <FieldLabel label="PO No" mandatory locked className="text-slate-500 dark:text-slate-400" />
              <dd className="font-mono font-medium text-slate-900 dark:text-white">{data.ida ?? data.purchase_order_no ?? '--'}</dd>
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
              <FieldLabel label="Terms" className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <input
                  type="text"
                  value={data.terms ?? ''}
                  onChange={(e) => onChange('terms', e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">{data.terms ?? '--'}</dd>
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

        {/* Middle: Vendor Info */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaTruck className="text-green-500" />
            Vendor Information
          </h3>
          {isEditing && onChange && (
            <div className="mb-4">
              <VendorSelector value={data.id_vendor ?? null} onChange={(p)=>onChange('id_vendor', p?.id ?? null)} />
            </div>
          )}
          {vendorInfo ? (
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between">
                <FieldLabel label="Vendor" className="text-slate-500 dark:text-slate-400" />
                <dd className="text-slate-900 dark:text-white font-medium">{vendorInfo.name ?? '--'}</dd>
              </div>
              {vendorInfo.contact && (
                <div className="flex justify-between">
                  <FieldLabel label="Contact" className="text-slate-500 dark:text-slate-400" />
                  <dd className="text-slate-900 dark:text-white">{vendorInfo.contact}</dd>
                </div>
              )}
              {vendorInfo.phone && (
                <div className="flex justify-between">
                  <FieldLabel label="Phone" className="text-slate-500 dark:text-slate-400" />
                  <dd className="text-slate-900 dark:text-white">{vendorInfo.phone}</dd>
                </div>
              )}
            </dl>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400 italic">No vendor assigned</p>
          )}
        </div>

        {/* Right: Receiving Info */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaTruck className="text-purple-500" />
            Receiving Information
          </h3>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between items-center">
              <FieldLabel label="Receipt ID" className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <input
                  type="text"
                  value={data.receipt_id ?? ''}
                  onChange={(e) => onChange('receipt_id', e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">{data.receipt_id ?? '--'}</dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Vendor Pack List" className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <input
                  type="text"
                  value={data.vendor_pack_list ?? ''}
                  onChange={(e) => onChange('vendor_pack_list', e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">{data.vendor_pack_list ?? '--'}</dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Pack Date" className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <input
                  type="date"
                  value={data.vendor_pack_date ? new Date(data.vendor_pack_date).toISOString().split('T')[0] : ''}
                  onChange={(e) => onChange('vendor_pack_date', e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.vendor_pack_date ? new Date(data.vendor_pack_date).toLocaleDateString() : '--'}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Ship Date" className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <input
                  type="date"
                  value={data.ship_date ? new Date(data.ship_date).toISOString().split('T')[0] : ''}
                  onChange={(e) => onChange('ship_date', e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.ship_date ? new Date(data.ship_date).toLocaleDateString() : '--'}
                </dd>
              )}
            </div>
          </dl>
        </div>
      </div>

      {/* Order Totals Summary */}
      <div className="bg-gradient-to-r from-slate-50 to-slate-100 dark:from-slate-800/50 dark:to-slate-700/50 rounded-lg p-6 border border-slate-200 dark:border-slate-700">
        <div className="grid grid-cols-3 gap-8 text-center">
          <div>
            <dt className="text-sm text-slate-500 dark:text-slate-400 mb-1">Subtotal</dt>
            <dd className="text-2xl font-bold text-slate-900 dark:text-white">{formatCurrency(data.subtotal)}</dd>
          </div>
          <div>
            <dt className="text-sm text-slate-500 dark:text-slate-400 mb-1">Tax</dt>
            <dd className="text-2xl font-bold text-slate-900 dark:text-white">{formatCurrency(data.tax)}</dd>
          </div>
          <div>
            <dt className="text-sm text-slate-500 dark:text-slate-400 mb-1">Total</dt>
            <dd className="text-3xl font-bold text-green-600 dark:text-green-400">{formatCurrency(data.total)}</dd>
          </div>
        </div>
      </div>
    </div>
  );
};

// Purchase Order Lines Tab Content
const PurchaseOrderLinesContent: React.FC<{
  data: PurchaseOrder;
  isEditing: boolean;
  onLinesChange?: (lines: TransactionLine[]) => void;
}> = ({ data, isEditing, onLinesChange }) => {
  const lines = data.lines ?? [];

  // Handler for adding items from search - uses COST for purchase orders
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
        ordered: quantity,
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
            Search the catalog and add items to this purchase order.
          </p>
          <TransactionItemSearch onAddItem={handleAddItem} useCost={true} defaultQuantity={1} />
        </div>
      )}

      {/* Lines Table */}
      {!lines.length ? (
        <div className="text-center py-12 text-slate-500 dark:text-slate-400">
          <FaShoppingBag className="mx-auto text-4xl mb-4 opacity-50" />
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
                  <td className="p-3 text-slate-700 dark:text-slate-300">{line.item?.description ?? line.description ?? line.item_description ?? '--'}</td>
                  <td className="p-3 text-right text-slate-900 dark:text-white">{line.quantity?.ordered ?? line.qty_ordered ?? line.quantity ?? '--'}</td>
                  <td className="p-3 text-right text-slate-900 dark:text-white">{formatCurrency(line.cost?.unit ?? line.unit_cost ?? line.price)}</td>
                  <td className="p-3 text-right font-medium text-slate-900 dark:text-white">{formatCurrency(line.cost?.extended ?? line.amount ?? line.line_total)}</td>
                  <td className="p-3 text-center">
                    {line.is_received ? (
                      <span className="inline-flex items-center gap-1 text-green-600">
                        <FaCheck size={12} /> Received
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-slate-400">
                        <FaTimes size={12} /> Pending
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
interface PurchaseOrderDetailProps {
  modeProp?: 'view' | 'edit' | 'add';
  dataProp?: PurchaseOrder;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
  isAdmin?: boolean;
}

// Main Component
const PurchaseOrderDetail: React.FC<PurchaseOrderDetailProps> = (props) => {
  // Dynamic tabs generator
  const getTabsAfter = (): TransactionTab[] => {
    return [
      { id: 'receiving', label: 'Receiving', icon: <FaTruck size={14} /> },
    ];
  };

  return (
    <TransactionDetailBase
      transactionType="purchaseorder"
      typeLabel="Purchase Order"
      modelName="purchase_order"
      renderHeader={(data, isEditing, onChange) => (
        <PurchaseOrderHeader data={data as PurchaseOrder} isEditing={isEditing} onChange={onChange as any} />
      )}
      renderLines={(lines, isEditing, data, onLinesChange) => (
        <PurchaseOrderLinesContent data={data as PurchaseOrder} isEditing={isEditing} onLinesChange={onLinesChange} />
      )}
      customTabsAfter={getTabsAfter()}
      inline={props.inline}
      modeProp={props.modeProp}
      dataProp={props.dataProp}
      onSaved={props.onSaved}
      onCancelInline={props.onCancelInline}
      isAdmin={props.isAdmin}
    />
  );
};

export default PurchaseOrderDetail;

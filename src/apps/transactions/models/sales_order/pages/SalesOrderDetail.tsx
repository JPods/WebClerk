/**
 * SalesOrderDetail - Refactored to use TransactionDetailBase
 * Extends base with sales order-specific fields and functionality
 * Keeps item search and lines management capabilities
 */
import React, { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  FaFileInvoice, 
  FaShoppingCart,
  FaTruck,
  FaPrint,
  FaEnvelope,
  FaPlus,
  FaTrash,
} from 'react-icons/fa';

// Import base component and shared types
import TransactionDetailBase, { TransactionTab } from '../../../components/TransactionDetailBase';
import TransactionToolbar, { type TransactionType } from '../../../components/TransactionToolbar';
import FieldLabel from '../../../components/FieldLabel';

// Import existing components
import SalesOrderItemSearch from '../components/SalesOrderItemSearch';
import SalesOrderStatus from '../components/SalesOrderStatus';
import type { ItemSearchResult } from '../types/itemSearchType';

// Import types
import type { 
  Transaction, 
  TransactionLine 
} from '../../../types/transactionTypes';

// Sales Order specific fields that extend base Transaction
interface SalesOrder extends Transaction {
  ida?: string;
  sales_order_no?: string;
  po_number?: string;
  reference?: string;
  dt?: string;
  terms?: string;
  due_date?: string;
  ship_date?: string;
  ship_via?: string;
  fob?: string;
  weight?: number;
  price_level?: string;
  priority?: string;
  // Computed from base totals
  subtotal?: number;
  tax?: number;
  total?: number;
  balance?: number;
}

// Sales Order specific tabs
const SALES_ORDER_TABS_BEFORE: TransactionTab[] = [];

const SALES_ORDER_TABS_AFTER: TransactionTab[] = [
  { id: 'shipping', label: 'Shipping', icon: <FaTruck size={14} /> },
  { id: 'add-items', label: 'Add Items', icon: <FaPlus size={14} /> },
];

// Status Badge Component
const StatusBadge: React.FC<{ status?: string }> = ({ status }) => {
  const statusStyles: Record<string, string> = {
    planned: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
    released: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    in_progress: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    hold: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
    complete: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    canceled: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  };

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusStyles[status ?? 'planned'] ?? statusStyles.planned}`}>
      {status?.replace('_', ' ') ?? 'planned'}
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

const formatNumber = (value?: number | null): string => {
  if (value === undefined || value === null) return '--';
  return value.toLocaleString();
};

// Custom Sales Order Header Component
const SalesOrderHeader: React.FC<{
  data: SalesOrder;
  isEditing: boolean;
  onChange?: (field: keyof SalesOrder, value: unknown) => void;
  onStatusChange?: (status: string) => void;
}> = ({ data, isEditing, onStatusChange }) => {
  // Extract customer info from refs.links
  const customerInfo = data.refs?.links?.customer?.[0];
  const billingContact = data.refs?.links?.contact?.find(c => c.purpose === 'billto');
  const shippingContact = data.refs?.links?.contact?.find(c => c.purpose === 'shipto');

  return (
    <div className="space-y-6">
      {/* Sales Order Header Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Order Details */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaShoppingCart className="text-blue-500" />
            Sales Order Details
          </h3>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between items-center">
              <FieldLabel label="Order No" mandatory locked className="text-slate-500 dark:text-slate-400" />
              <dd className="font-mono font-medium text-slate-900 dark:text-white">{data.ida ?? '--'}</dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="ID" locked className="text-slate-500 dark:text-slate-400" />
              <dd className="font-mono text-slate-600 dark:text-slate-300">{data.id ?? '--'}</dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Date" mandatory className="text-slate-500 dark:text-slate-400" />
              <dd className="text-slate-900 dark:text-white">
                {data.dt ? new Date(data.dt).toLocaleDateString() : '--'}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Due Date" className="text-slate-500 dark:text-slate-400" />
              <dd className="text-slate-900 dark:text-white">
                {data.due_date ? new Date(data.due_date).toLocaleDateString() : '--'}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Terms" className="text-slate-500 dark:text-slate-400" />
              <dd className="text-slate-900 dark:text-white">{data.terms ?? '--'}</dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="PO Number" className="text-slate-500 dark:text-slate-400" />
              <dd className="text-slate-900 dark:text-white">{data.po_number ?? data.reference ?? '--'}</dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Priority" className="text-slate-500 dark:text-slate-400" />
              <dd className="text-slate-900 dark:text-white">{data.priority ?? '--'}</dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Price Level" className="text-slate-500 dark:text-slate-400" />
              <dd className="text-slate-900 dark:text-white">{data.price_level ?? '--'}</dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Status" mandatory className="text-slate-500 dark:text-slate-400" />
              <dd>
                <StatusBadge status={data.status} />
              </dd>
            </div>
          </dl>
          
          {/* Status Flow */}
          {onStatusChange && (
            <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
              <SalesOrderStatus
                currentStatus={(data.status ?? 'planned') as 'planned' | 'released' | 'in_progress' | 'hold' | 'complete' | 'canceled'}
                onStatusChange={onStatusChange}
                readonly={!isEditing}
                showHistory={false}
              />
            </div>
          )}
        </div>

        {/* Center: Customer Info */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Customer</h3>
          {customerInfo ? (
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between items-center">
                <FieldLabel label="Customer ID" locked className="text-slate-500 dark:text-slate-400" />
                <dd className="font-mono text-slate-600 dark:text-slate-300">{data.customer_id ?? '--'}</dd>
              </div>
              <div className="flex justify-between items-center">
                <FieldLabel label="Name" className="text-slate-500 dark:text-slate-400" />
                <dd className="text-slate-900 dark:text-white">{customerInfo.display_name ?? '--'}</dd>
              </div>
              <div className="flex justify-between items-center">
                <FieldLabel label="IDA" className="text-slate-500 dark:text-slate-400" />
                <dd className="font-mono text-slate-600 dark:text-slate-300">{customerInfo.ida ?? '--'}</dd>
              </div>
            </dl>
          ) : (
            <p className="text-slate-400 text-sm">No customer linked</p>
          )}

          {billingContact && (
            <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
              <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">Bill To</h4>
              <p className="text-sm text-slate-900 dark:text-white">{billingContact.display_name}</p>
              {billingContact.email && <p className="text-sm text-slate-600 dark:text-slate-300">{billingContact.email}</p>}
              {billingContact.phone && <p className="text-sm text-slate-600 dark:text-slate-300">{billingContact.phone}</p>}
            </div>
          )}

          {shippingContact && (
            <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
              <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">Ship To</h4>
              <p className="text-sm text-slate-900 dark:text-white">{shippingContact.display_name}</p>
              {shippingContact.email && <p className="text-sm text-slate-600 dark:text-slate-300">{shippingContact.email}</p>}
              {shippingContact.phone && <p className="text-sm text-slate-600 dark:text-slate-300">{shippingContact.phone}</p>}
            </div>
          )}
        </div>

        {/* Right: Totals */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Order Totals</h3>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between items-center">
              <FieldLabel label="Subtotal" locked className="text-slate-500 dark:text-slate-400" />
              <dd className="font-mono text-slate-900 dark:text-white">
                {formatCurrency(data.totals?.subtotal ?? data.subtotal)}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Discount" className="text-slate-500 dark:text-slate-400" />
              <dd className="font-mono text-red-600 dark:text-red-400">
                {data.totals?.discount ? `-${formatCurrency(data.totals.discount)}` : '--'}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Tax" locked className="text-slate-500 dark:text-slate-400" />
              <dd className="font-mono text-slate-900 dark:text-white">
                {formatCurrency(data.totals?.tax ?? data.tax)}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Shipping" className="text-slate-500 dark:text-slate-400" />
              <dd className="font-mono text-slate-900 dark:text-white">
                {formatCurrency(data.totals?.shipping)}
              </dd>
            </div>
            <div className="flex justify-between items-center pt-2 border-t border-slate-200 dark:border-slate-700">
              <FieldLabel label="Total" mandatory locked className="text-slate-700 dark:text-slate-200 text-base" />
              <dd className="text-lg font-bold text-slate-900 dark:text-white">
                {formatCurrency(data.totals?.total ?? data.total)}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Cost" locked className="text-slate-500 dark:text-slate-400" />
              <dd className="font-mono text-slate-600 dark:text-slate-400">
                {formatCurrency(data.totals?.cost)}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Margin" locked className="text-slate-500 dark:text-slate-400" />
              <dd className={`font-mono ${(data.totals?.margin ?? 0) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                {formatCurrency(data.totals?.margin)}
                {data.totals?.margin_pc != null && (
                  <span className="ml-1 text-xs">({data.totals.margin_pc.toFixed(1)}%)</span>
                )}
              </dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex gap-2">
        <button 
          type="button"
          className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors flex items-center gap-2"
        >
          <FaPrint size={14} />
          Print
        </button>
        <button 
          type="button"
          className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors flex items-center gap-2"
        >
          <FaEnvelope size={14} />
          Email
        </button>
      </div>
    </div>
  );
};

// Sales Order Lines Component
const SalesOrderLines: React.FC<{
  lines: TransactionLine[];
  isEditing: boolean;
  onDeleteLine?: (lineId: number) => void;
  onUpdateLine?: (lineId: number, field: string, value: unknown) => void;
}> = ({ lines, isEditing, onDeleteLine }) => {
  if (!lines.length) {
    return (
      <div className="text-center py-12 text-slate-400">
        <FaShoppingCart size={32} className="mx-auto mb-3 opacity-50" />
        <p>No line items on this order</p>
        {isEditing && (
          <p className="mt-2 text-sm">Use the "Add Items" tab to search and add products</p>
        )}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-slate-50 dark:bg-slate-900/50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide w-16">#</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide w-32">Item Code</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Description</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide w-24">Qty</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide w-24">UOM</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide w-28">Unit Price</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide w-28">Unit Cost</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide w-28">Extended</th>
            {isEditing && (
              <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide w-16">Actions</th>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
          {lines.map((line, idx) => {
            // Handle different line data structures
            const lineNo = (line as Record<string, unknown>).line_no ?? line.item?.line_number ?? idx + 1;
            const itemCode = (line as Record<string, unknown>).ida_item ?? line.item?.ida_item ?? '--';
            const description = (line as Record<string, unknown>).description ?? line.item?.description ?? '--';
            const qty = (line as Record<string, unknown>).qty ?? line.quantity?.ordered ?? 0;
            const uom = (line as Record<string, unknown>).unit_measure ?? line.item?.unit_measure ?? 'EA';
            const unitPrice = ((line as Record<string, unknown>).price as Record<string, unknown>)?.sell ?? 
                             ((line as Record<string, unknown>).price as Record<string, unknown>)?.unit ?? 
                             line.price?.unit ?? 0;
            const unitCost = ((line as Record<string, unknown>).cost as Record<string, unknown>)?.unit ?? 
                            line.cost?.unit ?? 0;
            const extended = ((line as Record<string, unknown>).price as Record<string, unknown>)?.extended ?? 
                            line.price?.extended ?? 
                            (Number(qty) * Number(unitPrice));

            return (
              <tr 
                key={line.id ?? idx} 
                className="hover:bg-slate-50 dark:hover:bg-slate-800/50"
              >
                <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">
                  {lineNo}
                </td>
                <td className="px-4 py-3 text-sm font-mono font-medium text-slate-900 dark:text-white">
                  {String(itemCode)}
                </td>
                <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">
                  {String(description)}
                </td>
                <td className="px-4 py-3 text-sm text-right text-slate-900 dark:text-white">
                  {formatNumber(Number(qty))}
                </td>
                <td className="px-4 py-3 text-sm text-right text-slate-600 dark:text-slate-300">
                  {String(uom)}
                </td>
                <td className="px-4 py-3 text-sm text-right text-slate-900 dark:text-white">
                  {formatCurrency(Number(unitPrice))}
                </td>
                <td className="px-4 py-3 text-sm text-right text-slate-600 dark:text-slate-300">
                  {formatCurrency(Number(unitCost))}
                </td>
                <td className="px-4 py-3 text-sm text-right font-medium text-slate-900 dark:text-white">
                  {formatCurrency(Number(extended))}
                </td>
                {isEditing && onDeleteLine && line.id && (
                  <td className="px-4 py-3 text-center">
                    <button
                      type="button"
                      onClick={() => onDeleteLine(line.id!)}
                      className="p-1 text-slate-400 hover:text-red-500 transition-colors"
                      title="Delete line"
                    >
                      <FaTrash size={14} />
                    </button>
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
        <tfoot className="bg-slate-50 dark:bg-slate-900/50 border-t-2 border-slate-300 dark:border-slate-600">
          <tr>
            <td colSpan={isEditing ? 6 : 6}></td>
            <td className="px-4 py-2 text-sm font-medium text-slate-500 dark:text-slate-400 text-right">Lines Total:</td>
            <td className="px-4 py-2 text-sm font-bold text-slate-900 dark:text-white text-right">
              {formatCurrency(lines.reduce((sum, l) => {
                const extended = ((l as Record<string, unknown>).price as Record<string, unknown>)?.extended ?? 
                                l.price?.extended ?? 0;
                return sum + Number(extended);
              }, 0))}
            </td>
            {isEditing && <td></td>}
          </tr>
        </tfoot>
      </table>
    </div>
  );
};

// Shipping Tab Content
const ShippingTab: React.FC<{
  data: SalesOrder;
  isEditing: boolean;
}> = ({ data }) => {
  const shippingContact = data.refs?.links?.contact?.find(c => c.purpose === 'shipto');
  const shippingLocation = data.refs?.links?.location?.find(l => l.type === 'shipto');

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
        <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Shipping Details</h3>
        <dl className="space-y-3 text-sm">
          <div className="flex justify-between">
            <FieldLabel label="Ship Date" className="text-slate-500 dark:text-slate-400" />
            <dd className="text-slate-900 dark:text-white">
              {data.ship_date ? new Date(data.ship_date).toLocaleDateString() : '--'}
            </dd>
          </div>
          <div className="flex justify-between">
            <FieldLabel label="Ship Via" className="text-slate-500 dark:text-slate-400" />
            <dd className="text-slate-900 dark:text-white">{data.ship_via ?? '--'}</dd>
          </div>
          <div className="flex justify-between">
            <FieldLabel label="FOB" className="text-slate-500 dark:text-slate-400" />
            <dd className="text-slate-900 dark:text-white">{data.fob ?? '--'}</dd>
          </div>
          <div className="flex justify-between">
            <FieldLabel label="Weight" className="text-slate-500 dark:text-slate-400" />
            <dd className="text-slate-900 dark:text-white">
              {data.weight ? `${data.weight} kg` : '--'}
            </dd>
          </div>
        </dl>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
        <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Ship To Address</h3>
        {shippingContact ? (
          <div className="text-sm text-slate-700 dark:text-slate-300 space-y-1">
            <p className="font-medium">{shippingContact.display_name}</p>
            {shippingContact.company && <p>{shippingContact.company}</p>}
            {shippingLocation?.address && (
              <>
                <p>{(shippingLocation.address as Record<string, string>).street}</p>
                <p>
                  {(shippingLocation.address as Record<string, string>).city}, {' '}
                  {(shippingLocation.address as Record<string, string>).state} {' '}
                  {(shippingLocation.address as Record<string, string>).zip}
                </p>
                {(shippingLocation.address as Record<string, string>).country && (
                  <p>{(shippingLocation.address as Record<string, string>).country}</p>
                )}
              </>
            )}
            {shippingContact.phone && <p className="mt-2">Tel: {shippingContact.phone}</p>}
          </div>
        ) : (
          <p className="text-slate-400 text-sm">No shipping address specified</p>
        )}
      </div>
    </div>
  );
};

// Add Items Tab Content
const AddItemsTab: React.FC<{
  onAddItem: (item: ItemSearchResult) => void;
  isEditing: boolean;
}> = ({ onAddItem, isEditing }) => {
  if (!isEditing) {
    return (
      <div className="text-center py-12 text-slate-400">
        <FaPlus size={32} className="mx-auto mb-3 opacity-50" />
        <p>Enable edit mode to add items</p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
      <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Search & Add Items</h3>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
        Search the catalog and append matching items to this sales order.
      </p>
      <SalesOrderItemSearch onAddItem={onAddItem} />
    </div>
  );
};

// Main SalesOrderDetail Component
const SalesOrderDetail: React.FC<{ isAdmin?: boolean }> = ({ isAdmin = false }) => {
  const navigate = useNavigate();
  const [pendingItems, setPendingItems] = useState<ItemSearchResult[]>([]);

  // Handle adding item from search
  const handleAddItem = useCallback((item: ItemSearchResult) => {
    setPendingItems(prev => [...prev, item]);
    // TODO: Convert item to line and add to transaction
    console.log('Add item to order:', item);
  }, []);

  // Handle status change
  const handleStatusChange = useCallback((newStatus: string) => {
    // TODO: Implement status update API call
    console.log('Status changed to:', newStatus);
  }, []);

  // Custom tab content renderer
  const renderCustomTab = useCallback((tabId: string, data: Transaction, isEditing: boolean) => {
    const salesOrderData = data as SalesOrder;
    
    switch (tabId) {
      case 'shipping':
        return <ShippingTab data={salesOrderData} isEditing={isEditing} />;
      case 'add-items':
        return <AddItemsTab onAddItem={handleAddItem} isEditing={isEditing} />;
      default:
        return null;
    }
  }, [handleAddItem]);

  // Custom header renderer
  const renderHeader = useCallback((data: Transaction, isEditing: boolean) => (
    <SalesOrderHeader 
      data={data as SalesOrder} 
      isEditing={isEditing} 
      onStatusChange={handleStatusChange}
    />
  ), [handleStatusChange]);

  // Custom lines renderer
  const renderLines = useCallback((lines: TransactionLine[], isEditing: boolean) => (
    <SalesOrderLines 
      lines={lines} 
      isEditing={isEditing}
      onDeleteLine={(lineId) => console.log('Delete line:', lineId)}
    />
  ), []);

  // Check if order can be edited
  const canEdit = useCallback((data: Transaction) => {
    const status = data.status?.toLowerCase();
    return status !== 'complete' && status !== 'canceled';
  }, []);

  return (
    <TransactionDetailBase
      transactionType="sales_order"
      typeLabel="Sales Order"
      modelName="salesorder"
      customTabsBefore={SALES_ORDER_TABS_BEFORE}
      customTabsAfter={SALES_ORDER_TABS_AFTER}
      renderCustomTab={renderCustomTab}
      renderHeader={renderHeader}
      renderLines={renderLines}
      isAdmin={isAdmin}
      canEdit={canEdit}
    />
  );
};

export default SalesOrderDetail;

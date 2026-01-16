/**
 * InvoiceDetail - Refactored to use TransactionDetailBase
 * Extends base with invoice-specific fields and functionality
 */
import React, { useCallback } from 'react';
import { 
  FaFileInvoiceDollar, 
  FaPercent, 
  FaShippingFast,
  FaPrint,
  FaEnvelope
} from 'react-icons/fa';

// Import base component and shared types
import TransactionDetailBase, { TransactionTab } from '../../../components/TransactionDetailBase';
import FieldLabel from '../../../components/FieldLabel';
import { InvoiceItemSearch } from '../components/InvoiceItemSearch';
import { 
  resolveItemCode, 
  resolveItemDescription, 
  resolveUnitPrice, 
  resolveUnitCost 
} from '../utils/itemSearchHelpers';
import type { ItemSearchResult } from '../types/itemSearchType';

// Import types
import type { 
  Transaction, 
  TransactionLine 
} from '../../../types/transactionTypes';

// Invoice-specific fields that extend base Transaction
interface Invoice extends Transaction {
  invoice_no?: string;
  ida?: string;
  po_number?: string;
  reference?: string;
  dt?: string;
  terms?: string;
  due_date?: string;
  ship_date?: string;
  ship_via?: string;
  fob?: string;
  weight?: number;
  tax_rate?: number;
  tax_exempt?: boolean;
  tax_exempt_id?: string;
  discount_percent?: number;
  discount_amount?: number;
  balance_due?: number;
  amount_paid?: number;
  // Computed from base totals
  subtotal?: number;
  tax?: number;
  total?: number;
}

// Invoice-specific tabs
const INVOICE_TABS_BEFORE: TransactionTab[] = [];

const INVOICE_TABS_AFTER: TransactionTab[] = [
  { id: 'shipping', label: 'Shipping', icon: <FaShippingFast size={14} /> },
  { id: 'tax', label: 'Tax', icon: <FaPercent size={14} /> },
];

// Custom Invoice Header Component
const InvoiceHeader: React.FC<{
  data: Invoice;
  isEditing: boolean;
  onChange?: (field: keyof Invoice, value: unknown) => void;
}> = ({ data, isEditing, onChange }) => {
  // Extract customer info from refs.links
  const customerInfo = data.refs?.links?.customer?.[0];
  const billingContact = data.refs?.links?.contact?.find(c => c.purpose === 'billto');

  return (
    <div className="space-y-6">
      {/* Invoice Header Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Invoice Details */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaFileInvoiceDollar className="text-blue-500" />
            Invoice Details
          </h3>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between items-center">
              <FieldLabel label="Invoice No" mandatory locked className="text-slate-500 dark:text-slate-400" />
              <dd className="font-mono font-medium text-slate-900 dark:text-white">{data.ida ?? '--'}</dd>
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
              <FieldLabel label="PO Number" className="text-slate-500 dark:text-slate-400" />
              {isEditing && onChange ? (
                <input
                  type="text"
                  value={data.po_number ?? data.reference ?? ''}
                  onChange={(e) => onChange('po_number', e.target.value)}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">{data.po_number ?? data.reference ?? '--'}</dd>
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
            </div>
          )}
        </div>

        {/* Right: Totals */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Invoice Totals</h3>
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
                {data.discount_amount ? `-${formatCurrency(data.discount_amount)}` : '--'}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Tax" locked className="text-slate-500 dark:text-slate-400" />
              <dd className="font-mono text-slate-900 dark:text-white">
                {formatCurrency(data.totals?.tax ?? data.tax)}
              </dd>
            </div>
            <div className="flex justify-between items-center pt-2 border-t border-slate-200 dark:border-slate-700">
              <FieldLabel label="Total" mandatory locked className="text-slate-700 dark:text-slate-200 text-base" />
              <dd className="text-lg font-bold text-slate-900 dark:text-white">
                {formatCurrency(data.totals?.total ?? data.total)}
              </dd>
            </div>
            <div className="flex justify-between items-center text-green-600 dark:text-green-400">
              <FieldLabel label="Amount Paid" locked className="text-green-600 dark:text-green-400" />
              <dd className="font-mono">{formatCurrency(data.amount_paid)}</dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel label="Balance Due" mandatory locked className="text-slate-700 dark:text-slate-200" />
              <dd className={`font-mono font-bold ${(data.balance_due ?? 0) > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-green-600 dark:text-green-400'}`}>
                {formatCurrency(data.balance_due)}
              </dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex gap-2">
        <button className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors flex items-center gap-2">
          <FaPrint size={14} />
          Print
        </button>
        <button className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors flex items-center gap-2">
          <FaEnvelope size={14} />
          Email
        </button>
      </div>
    </div>
  );
};

// Invoice Lines Component
const InvoiceLines: React.FC<{
  lines: TransactionLine[];
  isEditing: boolean;
  onLinesChange?: (lines: TransactionLine[]) => void;
}> = ({ lines, isEditing, onLinesChange }) => {
  // Handler for adding items from search
  const handleAddItem = useCallback((item: ItemSearchResult, quantity: number) => {
    if (!onLinesChange) return;
    
    // Use helper functions to extract item data consistently
    const idaItem = resolveItemCode(item);
    const description = resolveItemDescription(item);
    const unitPrice = resolveUnitPrice(item);
    const unitCost = resolveUnitCost(item);
    
    // Extract item ID
    const itemId = item.id ?? item.item_id ?? item.itemId ?? null;
    
    // Extract unit of measure
    const unitMeasure = String(item.unit_of_measure ?? item.unitOfMeasure ?? item.unit_measure ?? 'EA');
    
    // Convert item to line and add to lines array
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
      price: {
        unit: unitPrice,
        extended: unitPrice * quantity,
      },
      cost: {
        unit: unitCost,
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
            Search the catalog and add items to this invoice.
          </p>
          <InvoiceItemSearch onAddItem={handleAddItem} />
        </div>
      )}

      {/* Lines Table */}
      {!lines.length ? (
        <div className="text-center py-12 text-slate-400">
          <FaFileInvoiceDollar size={32} className="mx-auto mb-3 opacity-50" />
          <p>No line items on this invoice</p>
          {isEditing && (
            <p className="mt-2 text-sm">Use the search above to find and add products</p>
          )}
        </div>
      ) : (
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
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide w-24">Disc %</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide w-28">Line Total</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
          {lines.map((line, idx) => (
            <tr 
              key={line.id ?? idx} 
              className="hover:bg-slate-50 dark:hover:bg-slate-800/50"
            >
              <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">
                {line.item?.line_number ?? idx + 1}
              </td>
              <td className="px-4 py-3 text-sm font-mono font-medium text-slate-900 dark:text-white">
                {line.item?.ida_item ?? '--'}
              </td>
              <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">
                {line.item?.description ?? '--'}
              </td>
              <td className="px-4 py-3 text-sm text-right text-slate-900 dark:text-white">
                {formatNumber(line.quantity?.ordered)}
              </td>
              <td className="px-4 py-3 text-sm text-right text-slate-600 dark:text-slate-300">
                {line.item?.unit_measure ?? 'EA'}
              </td>
              <td className="px-4 py-3 text-sm text-right text-slate-900 dark:text-white">
                {formatCurrency(line.price?.unit)}
              </td>
              <td className="px-4 py-3 text-sm text-right text-slate-600 dark:text-slate-300">
                {line.price?.discount_percent ? `${line.price.discount_percent}%` : '--'}
              </td>
              <td className="px-4 py-3 text-sm text-right font-medium text-slate-900 dark:text-white">
                {formatCurrency(line.price?.extended)}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot className="bg-slate-50 dark:bg-slate-900/50 border-t-2 border-slate-300 dark:border-slate-600">
          <tr>
            <td colSpan={6}></td>
            <td className="px-4 py-2 text-sm font-medium text-slate-500 dark:text-slate-400 text-right">Subtotal:</td>
            <td className="px-4 py-2 text-sm font-bold text-slate-900 dark:text-white text-right">
              {formatCurrency(lines.reduce((sum, l) => sum + (l.price?.extended ?? 0), 0))}
            </td>
          </tr>
        </tfoot>
      </table>
        </div>
      )}
    </div>
  );
};

// Shipping Tab Content
const ShippingTab: React.FC<{
  data: Invoice;
  isEditing: boolean;
}> = ({ data }) => {
  const shippingContact = data.refs?.links?.contact?.find(c => c.purpose === 'shipto');
  // Get shipping location if available
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
                <p>{(shippingLocation.address as Record<string, string>).city}, {(shippingLocation.address as Record<string, string>).state} {(shippingLocation.address as Record<string, string>).zip}</p>
                {(shippingLocation.address as Record<string, string>).country && <p>{(shippingLocation.address as Record<string, string>).country}</p>}
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

// Tax Tab Content
const TaxTab: React.FC<{
  data: Invoice;
  isEditing: boolean;
}> = ({ data }) => {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6 max-w-lg">
      <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Tax Information</h3>
      <dl className="space-y-3 text-sm">
        <div className="flex justify-between items-center">
          <FieldLabel label="Tax Exempt" className="text-slate-500 dark:text-slate-400" />
          <dd>
            {data.tax_exempt ? (
              <span className="px-2 py-1 text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded">
                Yes
              </span>
            ) : (
              <span className="px-2 py-1 text-xs bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400 rounded">
                No
              </span>
            )}
          </dd>
        </div>
        {data.tax_exempt && (
          <div className="flex justify-between">
            <FieldLabel label="Exempt ID" className="text-slate-500 dark:text-slate-400" />
            <dd className="font-mono text-slate-900 dark:text-white">{data.tax_exempt_id ?? '--'}</dd>
          </div>
        )}
        <div className="flex justify-between">
          <FieldLabel label="Tax Rate" className="text-slate-500 dark:text-slate-400" />
          <dd className="text-slate-900 dark:text-white">
            {data.tax_rate != null ? `${data.tax_rate}%` : '--'}
          </dd>
        </div>
        <div className="flex justify-between pt-2 border-t border-slate-200 dark:border-slate-700">
          <FieldLabel label="Tax Amount" locked className="text-slate-500 dark:text-slate-400" />
          <dd className="font-medium text-slate-900 dark:text-white">
            {formatCurrency(data.totals?.tax ?? data.tax)}
          </dd>
        </div>
      </dl>
    </div>
  );
};

// Status Badge Component
const StatusBadge: React.FC<{ status?: string }> = ({ status }) => {
  const statusStyles: Record<string, string> = {
    draft: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
    pending: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    sent: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    partial: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
    paid: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    overdue: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    void: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-500',
  };

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusStyles[status ?? 'draft'] ?? statusStyles.draft}`}>
      {status ?? 'draft'}
    </span>
  );
};

// Utility functions
const formatCurrency = (value?: number): string => {
  if (value === undefined || value === null) return '--';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value);
};

const formatNumber = (value?: number): string => {
  if (value === undefined || value === null) return '--';
  return value.toLocaleString();
};

// Main InvoiceDetail Component
const InvoiceDetail: React.FC<{ isAdmin?: boolean }> = ({ isAdmin = false }) => {
  // Custom tab content renderer - memoized to prevent infinite loops
  const renderCustomTab = useCallback((tabId: string, data: Transaction, isEditing: boolean) => {
    const invoiceData = data as Invoice;
    
    switch (tabId) {
      case 'shipping':
        return <ShippingTab data={invoiceData} isEditing={isEditing} />;
      case 'tax':
        return <TaxTab data={invoiceData} isEditing={isEditing} />;
      default:
        return null;
    }
  }, []);

  // Custom header renderer - memoized
  const renderHeader = useCallback((data: Transaction, isEditing: boolean) => (
    <InvoiceHeader data={data as Invoice} isEditing={isEditing} />
  ), []);

  // Custom lines renderer - memoized
  const renderLines = useCallback((
    lines: TransactionLine[], 
    isEditing: boolean, 
    _data?: Transaction,
    onLinesChange?: (lines: TransactionLine[]) => void
  ) => (
    <InvoiceLines lines={lines} isEditing={isEditing} onLinesChange={onLinesChange} />
  ), []);

  // Check if invoice can be edited - memoized
  const canEdit = useCallback((data: Transaction) => {
    const status = data.status?.toLowerCase();
    return status !== 'paid' && status !== 'void' && status !== 'closed';
  }, []);

  return (
    <TransactionDetailBase
      transactionType="invoice"
      typeLabel="Invoice"
      modelName="invoice"
      customTabsBefore={INVOICE_TABS_BEFORE}
      customTabsAfter={INVOICE_TABS_AFTER}
      renderCustomTab={renderCustomTab}
      renderHeader={renderHeader}
      renderLines={renderLines}
      isAdmin={isAdmin}
      canEdit={canEdit}
    />
  );
};

export default InvoiceDetail;

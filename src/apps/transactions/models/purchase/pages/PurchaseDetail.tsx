/**
 * PurchaseDetail - Refactored to use TransactionDetailBase
 * Extends base with purchase-specific fields and SummaryCard
 */
import React, { useCallback } from 'react';
import {
  FaShoppingBag,
  FaTruck,
  FaCheck,
  FaTimes,
  FaTasks,
} from 'react-icons/fa';

// Import base component and shared types
import TransactionDetailBase, { TransactionTab } from '../../../components/TransactionDetailBase';
import SummaryCard from '../../../components/SummaryCard';
import LinesCard from '../../../components/LinesCard';
import TransactionItemSearch, {
  resolveItemCode,
  resolveItemDescription,
  resolveUnitPrice,
  resolveUnitCost,
} from '../../../components/TransactionItemSearch';
import type { ItemSearchResult } from '../../../components/TransactionItemSearch';

// Import types
import type { Transaction, TransactionLine } from '../../../types/transactionTypes';
import { lineKey, getNextLineNumber } from '../../../utils/lineHelpers';
import { withDevIdentifier } from '@/components/common/DevIdentifier';

// Purchase-specific fields that extend base Transaction
interface Purchase extends Transaction {
  ida?: string;
  purchase_no?: string;
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

// Utility functions
const formatCurrency = (value?: number | null): string => {
  if (value === undefined || value === null) return '--';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value);
};

// Custom Purchase Header Component using SummaryCard
const PurchaseHeader: React.FC<{
  data: Purchase;
  isEditing: boolean;
  onChange?: (field: keyof Purchase, value: unknown) => void;
}> = ({ data, isEditing, onChange }) => {
  // Extract vendor info from refs.links
  const vendorInfo = data.refs?.links?.vendor?.[0];
  return (
    <SummaryCard
      data={data}
      isEditing={isEditing}
      onChange={onChange}
      customerInfo={vendorInfo}
      transactionLabel="Purchase Order"
      documentNoLabel="PO No"
      dueDateLabel="Due Date"
      showShipping={true}
      showCostMargin={true}
    />
  );
};

// Purchase Lines Tab Content
const PurchaseLinesContent: React.FC<{
  data: Purchase;
  lines: TransactionLine[];  // Use lines prop directly from renderLines
  isEditing: boolean;
  onLinesChange?: (lines: TransactionLine[]) => void;
}> = ({ data, lines, isEditing, onLinesChange }) => {
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
      line_number: getNextLineNumber(lines),
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
                  <td className="p-3 text-right text-slate-900 dark:text-white">{line.quantity?.staged ?? quantity?.placed ?? line.qty_ordered ?? line.quantity ?? '--'}</td>
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
interface PurchaseDetailProps {
  modeProp?: 'view' | 'edit' | 'add';
  dataProp?: Purchase;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
  isAdmin?: boolean;
  /** Direct ID prop for /wcapi/get/?id=X style routes */
  idProp?: number | string;
  id?: number | string; // Alias for idProp
  recordId?: number | string; // Alias for idProp
}

// Dynamic tabs generator with badges based on data (like OrderDetail)
const getPurchaseTabsAfter = (_data: Transaction): TransactionTab[] => {
  return [
    { id: 'receiving', label: 'Receiving', icon: <FaTruck size={14} /> },
  ];
};

// Main Component
const PurchaseDetail: React.FC<PurchaseDetailProps> = (props) => {
  // Resolve ID from various prop names
  const resolvedId = props.idProp ?? props.id ?? props.recordId;

  // Custom tab content renderer for actions
  const renderCustomTab = useCallback(
    (
      tabId: string,
      data: Transaction,
      isEditing: boolean,
      _onFieldChange?: (field: string, value: unknown) => void,
    ) => {
      const purchaseData = data as Purchase;

      switch (tabId) {
        case "actions":
          const actions = purchaseData.actions?.items ?? [];
          return (
            <div className="p-4">
              {actions.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <FaTasks size={32} className="mx-auto mb-3 opacity-50" />
                  <p>No actions on this purchase order</p>
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
        case "receiving":
          return (
            <div className="p-4 text-center text-slate-400">
              <FaTruck size={32} className="mx-auto mb-3 opacity-50" />
              <p>Receiving details for this PO</p>
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
          onUpdateLine={(lineId, field, value) => {
            if (onLinesChange) {
              onLinesChange(
                lines.map((l, i) => {
                  if (lineKey(l, i) !== lineId) return l;
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
                      const qty = l.quantity?.staged ?? quantity?.placed ?? 0;
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

  // Check if PO can be edited
  const canEdit = useCallback((data: Transaction) => {
    const status = data.status?.toLowerCase();
    return status !== "received" && status !== "closed" && status !== "canceled";
  }, []);

  return (
    <TransactionDetailBase
      transactionType="purchase"
      typeLabel="Purchase Order"
      modelName="purchase"
      renderHeader={(data, isEditing, onChange) => (
        <PurchaseHeader data={data as Purchase} isEditing={isEditing} onChange={onChange as any} />
      )}
      renderLines={renderLines}
      getCustomTabsAfter={getPurchaseTabsAfter}
      renderCustomTab={renderCustomTab}
      inline={props.inline}
      modeProp={props.modeProp}
      dataProp={props.dataProp}
      idProp={resolvedId}
      onCancelInline={props.onCancelInline}
      onSaved={props.onSaved}
      isAdmin={props.isAdmin}
      canEdit={canEdit}
    />
  );
};

export default withDevIdentifier(PurchaseDetail, 'PurchaseDetail');
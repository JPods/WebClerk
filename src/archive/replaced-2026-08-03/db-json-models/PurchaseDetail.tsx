/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * PurchaseDetail - Refactored to use TransactionDetailBase
 * Extends base with purchase-specific fields and SummaryCard
 */
import React, { useCallback } from 'react';
import ManageActionPanel from '@/components/common/ManageActionPanel';
import {
  FaTruck,
  FaTasks,
} from 'react-icons/fa';

// Import base component and shared types
import TransactionDetailBase, { TransactionTab } from '../../../components/TransactionDetailBase';
import SummaryCard from '../../../components/SummaryCard';
import LinesCard from '../../../components/LinesCard';

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
      orgLabel="Vendor"
      orgIdField="vendor_id"
    />
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
          transactionType="purchase"
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
    <>
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
      {resolvedId && (
        <div className="mt-4 px-4">
          <ManageActionPanel modelName="purchase" recordId={resolvedId} record={props.dataProp} />
        </div>
      )}
    </>
  );
};

export default withDevIdentifier(PurchaseDetail, 'PurchaseDetail');
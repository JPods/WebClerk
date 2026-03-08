/**
 * InvoiceDetail - Refactored to use TransactionDetailBase
 * Extends base with invoice-specific fields and functionality
 */
import React, { useCallback, useState } from "react";
import SummaryCard from "../../../components/SummaryCard";
import {
  FaPercent,
  FaShippingFast,
  FaMoneyBillWave,
  FaTasks,
} from "react-icons/fa";

// Import Apply Payment Modal
import ApplyPaymentModal from "../../../components/ApplyPaymentModal";
import type { InvoiceRecord } from "../../../hooks/usePaymentApplication";

// Import base component and shared types
import TransactionDetailBase, {
  TransactionTab,
} from "../../../components/TransactionDetailBase";
import LinesCard from "../../../components/LinesCard";
import FieldLabel from "../../../components/FieldLabel";
import { lineKey, getNextLineNumber } from "../../../utils/lineHelpers";

// Import types
import type {
  Transaction,
  TransactionLine,
} from "../../../types/transactionTypes";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

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

// Dynamic tabs generator with badges based on data (like OrderDetail)
const getInvoiceTabsAfter = (_data: Transaction): TransactionTab[] => {
  return [
    { id: "shipping", label: "Shipping", icon: <FaShippingFast size={14} /> },
    { id: "tax", label: "Tax", icon: <FaPercent size={14} /> },
  ];
};

// Custom Invoice Header Component - uses SummaryCard + Apply Payment
const InvoiceHeader: React.FC<{
  data: Invoice;
  isEditing: boolean;
  onChange?: (field: keyof Invoice, value: unknown) => void;
  onPaymentApplied?: () => void;
}> = ({ data, isEditing, onChange, onPaymentApplied }) => {
  // State for Apply Payment modal
  const [showApplyPaymentModal, setShowApplyPaymentModal] = useState(false);

  // Extract customer info from refs.links
  const customerInfo = data.refs?.links?.customer?.[0];
  const billingContact = data.refs?.links?.contact?.find(
    (c) => c.purpose === "billto",
  );
  const shippingContact = data.refs?.links?.contact?.find(
    (c) => c.purpose === "shipto",
  );

  return (
    <>
      <SummaryCard
        data={data}
        isEditing={isEditing}
        onChange={onChange}
        customerInfo={customerInfo}
        billingContact={billingContact}
        shippingContact={shippingContact}
        transactionLabel="Invoice"
        documentNoLabel="Invoice No"
        dueDateLabel="Due Date"
        showShipping={true}
        showCostMargin={true}
      />
      {/* Apply Payment button and modal */}
      <div className="mt-4">
        <button
          onClick={() => setShowApplyPaymentModal(true)}
          className="w-full px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600 rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          <FaMoneyBillWave size={14} />
          Apply Payment
        </button>
        <ApplyPaymentModal
          isOpen={showApplyPaymentModal}
          onClose={() => setShowApplyPaymentModal(false)}
          invoice={data as unknown as InvoiceRecord}
          onPaymentApplied={() => {
            setShowApplyPaymentModal(false);
            onPaymentApplied?.();
          }}
        />
      </div>
    </>
  );
};

// Shipping Tab Content
const ShippingTab: React.FC<{
  data: Invoice;
  isEditing: boolean;
}> = ({ data }) => {
  const shippingContact = data.refs?.links?.contact?.find(
    (c) => c.purpose === "shipto",
  );
  // Get shipping address if available
  const shippingLocation = (data.refs?.links?.location as Array<{ id: number; type?: string; address?: Record<string, string> }> | undefined)?.find(
    (l) => l.type === "shipto",
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
        <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
          Shipping Details
        </h3>
        <dl className="space-y-3 text-sm">
          <div className="flex justify-between">
            <FieldLabel
              label="Ship Date"
              className="text-slate-500 dark:text-slate-400"
            />
            <dd className="text-slate-900 dark:text-white">
              {data.ship_date
                ? new Date(data.ship_date).toLocaleDateString()
                : "--"}
            </dd>
          </div>
          <div className="flex justify-between">
            <FieldLabel
              label="Ship Via"
              className="text-slate-500 dark:text-slate-400"
            />
            <dd className="text-slate-900 dark:text-white">
              {data.ship_via ?? "--"}
            </dd>
          </div>
          <div className="flex justify-between">
            <FieldLabel
              label="FOB"
              className="text-slate-500 dark:text-slate-400"
            />
            <dd className="text-slate-900 dark:text-white">
              {data.fob ?? "--"}
            </dd>
          </div>
          <div className="flex justify-between">
            <FieldLabel
              label="Weight"
              className="text-slate-500 dark:text-slate-400"
            />
            <dd className="text-slate-900 dark:text-white">
              {data.weight ? `${data.weight} kg` : "--"}
            </dd>
          </div>
        </dl>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
        <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
          Ship To Address
        </h3>
        {shippingContact ? (
          <div className="text-sm text-slate-700 dark:text-slate-300 space-y-1">
            <p className="font-medium">{shippingContact.display_name}</p>
            {shippingContact.company && <p>{shippingContact.company}</p>}
            {shippingLocation?.address && (
              <>
                <p>
                  {(shippingLocation.address as Record<string, string>).street}
                </p>
                <p>
                  {(shippingLocation.address as Record<string, string>).city},{" "}
                  {(shippingLocation.address as Record<string, string>).state}{" "}
                  {(shippingLocation.address as Record<string, string>).zip}
                </p>
                {(shippingLocation.address as Record<string, string>)
                  .country && (
                  <p>
                    {
                      (shippingLocation.address as Record<string, string>)
                        .country
                    }
                  </p>
                )}
              </>
            )}
            {shippingContact.phone && (
              <p className="mt-2">Tel: {shippingContact.phone}</p>
            )}
          </div>
        ) : (
          <p className="text-slate-400 text-sm">
            No shipping address specified
          </p>
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
      <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
        Tax Information
      </h3>
      <dl className="space-y-3 text-sm">
        <div className="flex justify-between items-center">
          <FieldLabel
            label="Tax Exempt"
            className="text-slate-500 dark:text-slate-400"
          />
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
            <FieldLabel
              label="Exempt ID"
              className="text-slate-500 dark:text-slate-400"
            />
            <dd className="font-mono text-slate-900 dark:text-white">
              {data.tax_exempt_id ?? "--"}
            </dd>
          </div>
        )}
        <div className="flex justify-between">
          <FieldLabel
            label="Tax Rate"
            className="text-slate-500 dark:text-slate-400"
          />
          <dd className="text-slate-900 dark:text-white">
            {data.tax_rate != null ? `${data.tax_rate}%` : "--"}
          </dd>
        </div>
        <div className="flex justify-between pt-2 border-t border-slate-200 dark:border-slate-700">
          <FieldLabel
            label="Tax Amount"
            locked
            className="text-slate-500 dark:text-slate-400"
          />
          <dd className="font-medium text-slate-900 dark:text-white">
            {formatCurrency(data.totals?.tax ?? data.tax)}
          </dd>
        </div>
      </dl>
    </div>
  );
};

// Utility functions
const formatCurrency = (value?: number): string => {
  if (value === undefined || value === null) return "--";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(value);
};

// Main InvoiceDetail Component
const InvoiceDetail: React.FC<{ isAdmin?: boolean }> = ({
  isAdmin = false,
}) => {
  // Custom tab content renderer - memoized to prevent infinite loops
  const renderCustomTab = useCallback(
    (tabId: string, data: Transaction, isEditing: boolean) => {
      const invoiceData = data as Invoice;

      switch (tabId) {
        case "actions":
          // Simple placeholder for actions - can be expanded like OrderDetail
          const actions = invoiceData.actions?.items ?? [];
          return (
            <div className="p-4">
              {actions.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <FaTasks size={32} className="mx-auto mb-3 opacity-50" />
                  <p>No actions on this invoice</p>
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
        case "shipping":
          return <ShippingTab data={invoiceData} isEditing={isEditing} />;
        case "tax":
          return <TaxTab data={invoiceData} isEditing={isEditing} />;
        default:
          return null;
      }
    },
    [],
  );

  // Custom header renderer - memoized
  const renderHeader = useCallback(
    (data: Transaction, isEditing: boolean) => (
      <InvoiceHeader 
        data={data as Invoice} 
        isEditing={isEditing}
        onPaymentApplied={() => {
          // Reload to refresh invoice data after payment applied
          window.location.reload();
        }}
      />
    ),
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
          transactionType="invoice"
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

  // Check if invoice can be edited - memoized
  const canEdit = useCallback((data: Transaction) => {
    const status = data.status?.toLowerCase();
    return status !== "paid" && status !== "void" && status !== "closed";
  }, []);

  return (
    <TransactionDetailBase
      transactionType="invoice"
      typeLabel="Invoice"
      modelName="invoice"
      customTabsBefore={INVOICE_TABS_BEFORE}
      getCustomTabsAfter={getInvoiceTabsAfter}
      renderCustomTab={renderCustomTab}
      renderHeader={renderHeader}
      renderLines={renderLines}
      isAdmin={isAdmin}
      canEdit={canEdit}
    />
  );
};

export default withDevIdentifier(InvoiceDetail, 'InvoiceDetail');
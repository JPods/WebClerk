/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * PaymentPanel — Flat-list panel showing payments linked to an entity.
 *
 * Used on OrderDetail, InvoiceDetail, and org detail pages to display
 * related payments in a compact, column-header row layout.
 *
 * Follows the ContactPanel pattern:
 *   useColumnSetups → ColumnSetupDialog → visibility-aware rows.
 *
 * Legacy wc2 reference: Table 28 "Included" form (Panel) columns:
 *   TypePay, Invoice#, DateReceived, Amount, AmountAvailable, NameOnAcct, Comment
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  FaChevronDown,
  FaChevronUp,
  FaDollarSign,
  FaExternalLinkAlt,
  FaPlus,
  FaSlidersH,
  FaSpinner,
  FaSyncAlt,
} from 'react-icons/fa';
import { getRecords } from '@/api/wcapi';
import { useWindowManager } from '@/context/WindowManagerContext';
import { getModelDetailPath, getModelWindowTitle } from './getModelDetailPath';
import { ColumnSetupDialog } from '@/components/common/ColumnSetupDialog';
import { useColumnSetups } from '@/hooks/useColumnSetups';
import { withDevIdentifier } from '@/components/common/DevIdentifier';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PaymentRow {
  id: number;
  ida?: string;
  amount?: number;
  amount_available?: number;
  status?: string;
  gateway?: string;
  payment_method_name?: string;
  reference_number?: string;
  invoice_number?: string;
  invoice_id?: number;
  contact_name?: string;
  customer_name?: string;
  dt_payment?: string;
  dt_created?: string;
  notes?: string;
  refs?: { order_ids?: number[]; invoice_ids?: number[] };
}

interface PaymentPanelProps {
  /** Filter by org (customer) ID — fetches all payments for this org */
  org_id?: number;
  /** Filter by invoice ID — fetches payments linked to this invoice */
  invoice_id?: number;
  /** Filter by order ID — fetches payments whose refs.order_ids contains this */
  order_id?: number;
  /** Externally supplied payment data (skips internal fetch) */
  payments?: PaymentRow[];
  /** Show Add Payment button */
  onAdd?: () => void;
  /** Panel title override */
  title?: string;
  /** Start collapsed */
  defaultCollapsed?: boolean;
}

// Column metadata for ColumnSetupDialog
const PAYMENT_COLUMN_METAS = [
  { key: 'status', label: 'status' },
  { key: 'amount', label: 'amount' },
  { key: 'amount_available', label: 'amount_available' },
  { key: 'payment_method', label: 'payment_method' },
  { key: 'reference', label: 'reference_number' },
  { key: 'invoice', label: 'invoice' },
  { key: 'dt_payment', label: 'dt_payment' },
  { key: 'notes', label: 'notes' },
];

// Helpers
const formatCurrency = (v?: number | null) => {
  if (v == null) return '--';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(v);
};

const formatDate = (d?: string | null) => {
  if (!d) return '--';
  return new Date(d).toLocaleDateString();
};

const STATUS_STYLES: Record<string, string> = {
  completed: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  processing: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  failed: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  cancelled: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
  refunded: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
};

// ---------------------------------------------------------------------------
// PaymentRowItem
// ---------------------------------------------------------------------------

const PaymentRowItem: React.FC<{
  payment: PaymentRow;
  visibleCols: Set<string>;
  onOpen?: () => void;
}> = ({ payment, visibleCols, onOpen }) => (
  <div className="flex items-center gap-3 px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-700/50 text-xs group">
    {/* Status badge */}
    {visibleCols.has('status') && (
      <span
        className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide shrink-0 min-w-[60px] text-center ${
          STATUS_STYLES[payment.status || ''] || STATUS_STYLES.pending
        }`}
      >
        {payment.status || '--'}
      </span>
    )}

    {/* Amount */}
    {visibleCols.has('amount') && (
      <span className="font-medium text-green-600 dark:text-green-400 shrink-0 w-[80px] text-right">
        {formatCurrency(payment.amount)}
      </span>
    )}

    {/* Amount Available */}
    {visibleCols.has('amount_available') && (
      <span className="text-slate-600 dark:text-slate-400 shrink-0 w-[80px] text-right">
        {formatCurrency(payment.amount_available)}
      </span>
    )}

    {/* Payment Method */}
    {visibleCols.has('payment_method') && (
      <span className="text-slate-700 dark:text-slate-300 truncate min-w-[70px] max-w-[100px]">
        {payment.payment_method_name || payment.gateway || '--'}
      </span>
    )}

    {/* Reference */}
    {visibleCols.has('reference') && (
      <span className="text-slate-600 dark:text-slate-400 truncate min-w-[60px] max-w-[100px] font-mono">
        {payment.reference_number || '--'}
      </span>
    )}

    {/* Invoice */}
    {visibleCols.has('invoice') && (
      <span className="text-slate-600 dark:text-slate-400 truncate w-[60px]">
        {payment.invoice_number || (payment.invoice_id ? `#${payment.invoice_id}` : '--')}
      </span>
    )}

    {/* Date */}
    {visibleCols.has('dt_payment') && (
      <span className="text-slate-500 dark:text-slate-400 shrink-0 w-[75px]">
        {formatDate(payment.dt_payment)}
      </span>
    )}

    {/* Notes (truncated) */}
    {visibleCols.has('notes') && (
      <span className="text-slate-400 dark:text-slate-500 truncate flex-1 min-w-0">
        {payment.notes || ''}
      </span>
    )}

    {/* Open button */}
    <button
      onClick={(e) => {
        e.stopPropagation();
        onOpen?.();
      }}
      className="p-1 opacity-0 group-hover:opacity-100 text-blue-500 hover:text-blue-700 transition-opacity shrink-0"
      title="Open payment detail"
    >
      <FaExternalLinkAlt size={10} />
    </button>
  </div>
);

// ---------------------------------------------------------------------------
// PaymentPanel
// ---------------------------------------------------------------------------

const PaymentPanel: React.FC<PaymentPanelProps> = ({
  org_id,
  invoice_id,
  order_id,
  payments: externalPayments,
  onAdd,
  title = 'Payments',
  defaultCollapsed = false,
}) => {
  const windowManager = useWindowManager();
  const [payments, setPayments] = useState<PaymentRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const [showSetup, setShowSetup] = useState(false);

  const columnSetups = useColumnSetups('panel:payments');

  // Build default config from column metas
  const defaultConfig = useMemo<import('@/hooks/useColumnSetups').ColumnSetupEntry>(() => {
    const order = PAYMENT_COLUMN_METAS.map((m) => m.key);
    const visibility: Record<string, boolean> = {};
    PAYMENT_COLUMN_METAS.forEach((m) => { visibility[m.key] = true; });
    return { order, visibility, widths: {}, sort: null };
  }, []);

  // Apply active setup (if any) over default
  const activeConfig = useMemo(() => {
    if (!columnSetups.activeSetupName) return defaultConfig;
    const applied = columnSetups.applySetup(columnSetups.activeSetupName);
    return applied ?? defaultConfig;
  }, [columnSetups, defaultConfig]);

  const visibleCols = useMemo(() => {
    const vis = activeConfig.visibility;
    const result = new Set<string>();
    for (const m of PAYMENT_COLUMN_METAS) {
      if (vis[m.key] !== false) result.add(m.key);
    }
    return result;
  }, [activeConfig]);

  const hiddenCount = PAYMENT_COLUMN_METAS.length - visibleCols.size;

  // Fetch payments
  const fetchData = useCallback(async () => {
    if (externalPayments) {
      setPayments(externalPayments);
      return;
    }

    const params: Record<string, unknown> = { limit: 100 };
    if (org_id) params.org_id = org_id;
    if (invoice_id) params.invoice_id = invoice_id;
    // Order-level filtering done client-side via refs
    if (!org_id && !invoice_id && !order_id) return;

    setLoading(true);
    try {
      const res = await getRecords('payment', params);
      let rows: PaymentRow[] = res?.results || [];

      // Client-side filter for order_id (payment refs)
      if (order_id && !invoice_id && !org_id) {
        rows = rows.filter((p) => p.refs?.order_ids?.includes(order_id));
      }

      setPayments(rows);
    } catch (err) {
      console.error('PaymentPanel fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [org_id, invoice_id, order_id, externalPayments]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Open payment detail in a floating window
  const openPayment = useCallback(
    (payment: PaymentRow) => {
      const path = getModelDetailPath('payment', payment.id);
      const windowTitle = getModelWindowTitle(
        'payment',
        payment.id,
        payment.ida,
      );
      windowManager.ensureWindow(path, windowTitle);
    },
    [windowManager],
  );

  // Totals
  const totalAmount = useMemo(
    () => payments.reduce((s, p) => s + (p.amount ?? 0), 0),
    [payments],
  );
  const totalAvailable = useMemo(
    () => payments.reduce((s, p) => s + (p.amount_available ?? 0), 0),
    [payments],
  );

  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between px-3 py-2 bg-slate-50 dark:bg-slate-800 cursor-pointer select-none"
        onClick={() => setCollapsed((c) => !c)}
      >
        <div className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300">
          <FaDollarSign className="text-green-500" size={14} />
          {title}
          <span className="text-xs text-slate-400">({payments.length})</span>
          {payments.length > 0 && (
            <span className="text-xs text-green-600 dark:text-green-400 font-normal">
              {formatCurrency(totalAmount)}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {/* Column setup badge */}
          {hiddenCount > 0 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowSetup(true);
              }}
              className="relative p-1 text-slate-400 hover:text-blue-500"
              title="Column settings"
            >
              <FaSlidersH size={12} />
              <span className="absolute -top-1 -right-1 bg-blue-500 text-white text-[8px] rounded-full w-3 h-3 flex items-center justify-center">
                {hiddenCount}
              </span>
            </button>
          )}
          {!hiddenCount && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowSetup(true);
              }}
              className="p-1 text-slate-400 hover:text-blue-500"
              title="Column settings"
            >
              <FaSlidersH size={12} />
            </button>
          )}

          {/* Refresh */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              fetchData();
            }}
            className="p-1 text-slate-400 hover:text-blue-500"
            title="Refresh"
          >
            <FaSyncAlt size={12} />
          </button>

          {/* Add */}
          {onAdd && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAdd();
              }}
              className="p-1 text-green-500 hover:text-green-700"
              title="Add payment"
            >
              <FaPlus size={12} />
            </button>
          )}

          {collapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
        </div>
      </div>

      {/* Body */}
      {!collapsed && (
        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          {/* Column headers */}
          <div className="flex items-center gap-3 px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 bg-slate-25 dark:bg-slate-850">
            {visibleCols.has('status') && <span className="shrink-0 min-w-[60px] text-center">status</span>}
            {visibleCols.has('amount') && <span className="shrink-0 w-[80px] text-right">amount</span>}
            {visibleCols.has('amount_available') && (
              <span className="shrink-0 w-[80px] text-right">available</span>
            )}
            {visibleCols.has('payment_method') && (
              <span className="min-w-[70px] max-w-[100px] truncate">method</span>
            )}
            {visibleCols.has('reference') && (
              <span className="min-w-[60px] max-w-[100px] truncate">reference</span>
            )}
            {visibleCols.has('invoice') && <span className="w-[60px] truncate">invoice</span>}
            {visibleCols.has('dt_payment') && <span className="shrink-0 w-[75px]">date</span>}
            {visibleCols.has('notes') && <span className="flex-1 min-w-0">notes</span>}
            <span className="shrink-0 w-[18px]" />
          </div>

          {loading && (
            <div className="flex items-center justify-center py-4 text-slate-400">
              <FaSpinner className="animate-spin mr-2" size={12} />
              Loading...
            </div>
          )}

          {!loading && payments.length === 0 && (
            <div className="text-center py-4 text-xs text-slate-400">
              No payments
            </div>
          )}

          {!loading &&
            payments.map((p) => (
              <PaymentRowItem
                key={p.id}
                payment={p}
                visibleCols={visibleCols}
                onOpen={() => openPayment(p)}
              />
            ))}

          {/* Footer totals */}
          {!loading && payments.length > 1 && (
            <div className="flex items-center gap-3 px-3 py-1.5 text-xs font-medium bg-slate-50 dark:bg-slate-800/50">
              {visibleCols.has('status') && <span className="shrink-0 min-w-[60px]" />}
              {visibleCols.has('amount') && (
                <span className="shrink-0 w-[80px] text-right text-green-600 dark:text-green-400">
                  {formatCurrency(totalAmount)}
                </span>
              )}
              {visibleCols.has('amount_available') && (
                <span className="shrink-0 w-[80px] text-right text-slate-600 dark:text-slate-400">
                  {formatCurrency(totalAvailable)}
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Column Setup Dialog */}
      <ColumnSetupDialog
        open={showSetup}
        title="Payment Columns"
        columnMetas={PAYMENT_COLUMN_METAS}
        config={activeConfig}
        onSave={(entry) => {
          columnSetups.saveSetup('current', entry);
          setShowSetup(false);
        }}
        onClose={() => setShowSetup(false)}
        namedSetups={columnSetups.setups}
        onSaveNamed={(name, config) => columnSetups.saveSetup(name, config)}
      />
    </div>
  );
};

export default withDevIdentifier(PaymentPanel, 'PaymentPanel', 'teal');

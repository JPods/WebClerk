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
  FaSpinner,
  FaSyncAlt,
} from 'react-icons/fa';
import { getRecords } from '@/api/wcapi';
import { formatDt } from '@/utils/fieldFormatters';
import { useWindowManager } from '@/context/WindowManagerContext';
import { getModelDetailPath, getModelWindowTitle } from './getModelDetailPath';
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import { formatCurrency } from '@/utils/stringUtils';

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

const formatDate = (d?: string | null) => {
  if (!d) return '--';
  return formatDt(d, 'date');
};

const STATUS_BADGE_STYLES: Record<string, React.CSSProperties> = {
  completed: { background: 'var(--db-badge-green-bg)', color: 'var(--db-badge-green-text)' },
  pending: { background: 'var(--db-badge-amber-bg)', color: 'var(--db-badge-amber-text)' },
  processing: { background: 'var(--db-badge-blue-bg)', color: 'var(--db-badge-blue-text)' },
  failed: { background: 'var(--db-badge-red-bg)', color: 'var(--db-badge-red-text)' },
  cancelled: { background: 'var(--db-surface-alt)', color: 'var(--db-text)' },
  refunded: { background: 'var(--db-badge-purple-bg)', color: 'var(--db-badge-purple-text)' },
};

const DEFAULT_STATUS_STYLE: React.CSSProperties = { background: 'var(--db-badge-amber-bg)', color: 'var(--db-badge-amber-text)' };

// ---------------------------------------------------------------------------
// PaymentRowItem
// ---------------------------------------------------------------------------

const PaymentRowItem: React.FC<{
  payment: PaymentRow;
  visibleCols: Set<string>;
  onOpen?: () => void;
}> = ({ payment, visibleCols, onOpen }) => (
  <div className="db-list-row flex items-center gap-3 px-3 py-2 text-xs group">
    {/* Status badge */}
    {visibleCols.has('status') && (
      <span
        className="px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide shrink-0 min-w-[60px] text-center"
        style={STATUS_BADGE_STYLES[payment.status || ''] || DEFAULT_STATUS_STYLE}
      >
        {payment.status || '--'}
      </span>
    )}

    {/* Amount */}
    {visibleCols.has('amount') && (
      <span className="font-medium shrink-0 w-[80px] text-right db-text-green">
        {formatCurrency(payment.amount)}
      </span>
    )}

    {/* Amount Available */}
    {visibleCols.has('amount_available') && (
      <span className="shrink-0 w-[80px] text-right db-text-muted">
        {formatCurrency(payment.amount_available)}
      </span>
    )}

    {/* Payment Method */}
    {visibleCols.has('payment_method') && (
      <span className="truncate min-w-[70px] max-w-[100px] db-text">
        {payment.payment_method_name || payment.gateway || '--'}
      </span>
    )}

    {/* Reference */}
    {visibleCols.has('reference') && (
      <span className="truncate min-w-[60px] max-w-[100px] font-mono db-text-muted">
        {payment.reference_number || '--'}
      </span>
    )}

    {/* Invoice */}
    {visibleCols.has('invoice') && (
      <span className="truncate w-[60px] db-text-muted">
        {payment.invoice_number || (payment.invoice_id ? `#${payment.invoice_id}` : '--')}
      </span>
    )}

    {/* Date */}
    {visibleCols.has('dt_payment') && (
      <span className="shrink-0 w-[75px] db-text-muted">
        {formatDate(payment.dt_payment)}
      </span>
    )}

    {/* Notes (truncated) */}
    {visibleCols.has('notes') && (
      <span className="truncate flex-1 min-w-0 db-text-dim">
        {payment.notes || ''}
      </span>
    )}

    {/* Open button */}
    <button
      onClick={(e) => {
        e.stopPropagation();
        onOpen?.();
      }}
      className="p-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0 db-text-accent"
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

  // All columns visible
  const visibleCols = new Set(PAYMENT_COLUMN_METAS.map((m) => m.key));

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

  // Aggregate of server-provided per-record values — no server-side aggregate available
  const totalAmount = useMemo(
    () => payments.reduce((s, p) => s + (p.amount ?? 0), 0),
    [payments],
  );
  const totalAvailable = useMemo(
    () => payments.reduce((s, p) => s + (p.amount_available ?? 0), 0),
    [payments],
  );

  return (
    <div className="rounded-lg overflow-hidden db-border-all">
      {/* Header */}
      <div
        className="flex items-center justify-between px-3 py-2 cursor-pointer select-none db-bg-surface-alt"
        onClick={() => setCollapsed((c) => !c)}
      >
        <div className="flex items-center gap-2 text-sm font-medium db-text">
          <FaDollarSign className="db-text-green" size={14} />
          {title}
          <span className="text-xs db-text-dim">({payments.length})</span>
          {payments.length > 0 && (
            <span className="text-xs font-normal db-text-green">
              {formatCurrency(totalAmount)}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {/* Refresh */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              fetchData();
            }}
            className="p-1 db-text-dim"
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
              className="p-1 db-text-green"
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
        <div>
          {/* Column headers */}
          <div className="flex items-center gap-3 px-3 py-1 text-[10px] font-semibold uppercase tracking-wider db-surface-alt-muted db-border-bottom-light">
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
            <div className="flex items-center justify-center py-4 db-text-dim">
              <FaSpinner className="animate-spin mr-2" size={12} />
              Loading...
            </div>
          )}

          {!loading && payments.length === 0 && (
            <div className="text-center py-4 text-xs db-text-dim">
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
            <div className="flex items-center gap-3 px-3 py-1.5 text-xs font-medium db-bg-surface-alt" style={{ borderTop: '1px solid var(--db-border-light)' }}>
              {visibleCols.has('status') && <span className="shrink-0 min-w-[60px]" />}
              {visibleCols.has('amount') && (
                <span className="shrink-0 w-[80px] text-right db-text-green">
                  {formatCurrency(totalAmount)}
                </span>
              )}
              {visibleCols.has('amount_available') && (
                <span className="shrink-0 w-[80px] text-right db-text-muted">
                  {formatCurrency(totalAvailable)}
                </span>
              )}
            </div>
          )}
        </div>
      )}

    </div>
  );
};

export default withDevIdentifier(PaymentPanel, 'PaymentPanel', 'teal', 'apps/common/components/panels/PaymentPanel.tsx');

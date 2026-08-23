/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * TransactionPanel - Header bar showing key record fields + TransactionToolbar
 *
 * Displays: ida, status, attention, email, phone, total, balance, priority
 * Renders TransactionToolbar below the header for action buttons.
 *
 * Used by TransactionDetailBase and other detail pages that need
 * a combined record summary + action toolbar.
 */
import React from "react";
import TransactionToolbar, {
  type TransactionToolbarProps,
} from "@/apps/common/components/TransactionToolbar";

/** Record header fields displayed above the toolbar */
export interface TransactionHeaderData {
  ida?: string;
  status?: string;
  attention?: string;
  email?: string;
  phone?: string;
  total?: number | null;
  balance?: number | null;
  priority?: string;
}

export interface TransactionPanelProps extends TransactionToolbarProps {
  /** Record data for the header row */
  record?: TransactionHeaderData;
}

const formatCurrency = (value?: number | null): string => {
  if (value == null) return "--";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(value);
};

const statusColors: Record<string, { bg: string; color: string }> = {
  planned: { bg: 'var(--db-surface-alt)', color: 'var(--db-text-muted)' },
  released: { bg: 'var(--db-surface-alt)', color: 'var(--db-accent)' },
  in_progress: { bg: 'var(--db-surface-alt)', color: 'var(--db-text)' },
  hold: { bg: 'var(--db-surface-alt)', color: 'var(--db-text-muted)' },
  complete: { bg: 'var(--db-surface-alt)', color: 'var(--db-text)' },
  canceled: { bg: 'var(--db-surface-alt)', color: 'var(--db-text-dim)' },
};

const priorityColors: Record<string, { color: string }> = {
  low: { color: 'var(--db-text-dim)' },
  normal: { color: 'var(--db-accent)' },
  high: { color: 'var(--db-text)' },
  urgent: { color: 'var(--db-text)' },
};

const HeaderField: React.FC<{
  label: string;
  value?: string | null;
  className?: string;
}> = ({ label, value, className = "" }) => {
  if (!value) return null;
  return (
    <div className={className} style={{ color: 'var(--db-text-muted)' }}>
      <span style={{ color: 'var(--db-text-muted)' }}>{label}</span>{" "}
      {value}
    </div>
  );
};

const TransactionPanel: React.FC<TransactionPanelProps> = ({
  record,
  className,
  ...toolbarProps
}) => {
  const r = record;
  const hasHeader = r && (r.ida || r.status || r.attention || r.email || r.phone || r.total != null || r.balance != null || r.priority);

  return (
    <div className={`flex flex-col gap-0 ${className ?? ""}`}>
      {/* Header row — record summary */}
      {hasHeader && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-3 py-2 text-xs rounded-t-lg" style={{ background: 'var(--db-surface)', border: '1px solid var(--db-border)' }}>
          {/* ida */}
          {r.ida && (
            <span className="font-semibold" style={{ color: 'var(--db-text)' }}>
              {r.ida}
            </span>
          )}

          {/* status badge */}
          {r.status && (
            <span
              className="px-2 py-0.5 rounded-full font-medium"
              style={statusColors[r.status] ?? statusColors.planned}
            >
              {r.status.replace("_", " ")}
            </span>
          )}

          {/* attention */}
          <HeaderField label="Attn:" value={r.attention} />

          {/* email */}
          {r.email && (
            <div
              className="truncate max-w-[200px]"
              style={{ color: 'var(--db-text-muted)' }}
              title={r.email}
            >
              {r.email}
            </div>
          )}

          {/* phone */}
          <HeaderField label="" value={r.phone} />

          {/* spacer */}
          <div className="flex-1" />

          {/* total */}
          {r.total != null && (
            <div style={{ color: 'var(--db-text)' }}>
              <span style={{ color: 'var(--db-text-muted)' }}>Total:</span>{" "}
              <span className="font-medium">{formatCurrency(r.total)}</span>
            </div>
          )}

          {/* balance */}
          {r.balance != null && (
            <div style={{ color: 'var(--db-text)' }}>
              <span style={{ color: 'var(--db-text-muted)' }}>Bal:</span>{" "}
              <span className="font-medium">{formatCurrency(r.balance)}</span>
            </div>
          )}

          {/* priority */}
          {r.priority && (
            <span
              className="font-medium capitalize"
              style={priorityColors[r.priority] ?? { color: 'var(--db-text-muted)' }}
            >
              {r.priority}
            </span>
          )}
        </div>
      )}

      {/* Toolbar */}
      <TransactionToolbar
        {...toolbarProps}
        className={hasHeader ? "rounded-t-none border-t-0" : undefined}
      />
    </div>
  );
};

export default TransactionPanel;

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

const statusColors: Record<string, string> = {
  planned: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
  released:
    "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  in_progress:
    "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  hold: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  complete:
    "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  canceled:
    "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

const priorityColors: Record<string, string> = {
  low: "text-slate-500 dark:text-slate-400",
  normal: "text-blue-600 dark:text-blue-400",
  high: "text-orange-600 dark:text-orange-400",
  urgent: "text-red-600 dark:text-red-400",
};

const HeaderField: React.FC<{
  label: string;
  value?: string | null;
  className?: string;
}> = ({ label, value, className = "" }) => {
  if (!value) return null;
  return (
    <div className={`text-slate-600 dark:text-slate-400 ${className}`}>
      <span className="text-slate-400 dark:text-slate-500">{label}</span>{" "}
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
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-3 py-2 text-xs bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-t-lg">
          {/* ida */}
          {r.ida && (
            <span className="font-semibold text-slate-900 dark:text-slate-100">
              {r.ida}
            </span>
          )}

          {/* status badge */}
          {r.status && (
            <span
              className={`px-2 py-0.5 rounded-full font-medium ${
                statusColors[r.status] ?? statusColors.planned
              }`}
            >
              {r.status.replace("_", " ")}
            </span>
          )}

          {/* attention */}
          <HeaderField label="Attn:" value={r.attention} />

          {/* email */}
          {r.email && (
            <div
              className="text-slate-600 dark:text-slate-400 truncate max-w-[200px]"
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
            <div className="text-slate-700 dark:text-slate-300">
              <span className="text-slate-400 dark:text-slate-500">Total:</span>{" "}
              <span className="font-medium">{formatCurrency(r.total)}</span>
            </div>
          )}

          {/* balance */}
          {r.balance != null && (
            <div className="text-slate-700 dark:text-slate-300">
              <span className="text-slate-400 dark:text-slate-500">Bal:</span>{" "}
              <span className="font-medium">{formatCurrency(r.balance)}</span>
            </div>
          )}

          {/* priority */}
          {r.priority && (
            <span
              className={`font-medium capitalize ${
                priorityColors[r.priority] ?? "text-slate-600 dark:text-slate-400"
              }`}
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

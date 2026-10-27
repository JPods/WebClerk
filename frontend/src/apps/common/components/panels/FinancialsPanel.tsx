/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * FinancialsPanel - Summary of totals and cost with margin calculation
 *
 * Shared/common version used by detail pages.
 */
import React, { useMemo } from "react";
import { usePanelFrame } from "@/apps/common/components/CollapsiblePanel";
import {
  FaDollarSign,
  FaPercentage,
  FaChartLine,
  FaArrowUp,
  FaArrowDown,
} from "react-icons/fa";
import type { TransactionTotals } from "@/apps/transactions/types/transactionTypes";
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import { formatCurrency, formatPercent } from '@/utils/stringUtils';

interface FinancialsPanelProps {
  totals?: TransactionTotals | null;
  currency?: string;
  /** Back-compat with old FinancialsCard usage (not used currently) */
  isEditing?: boolean;
}


const StatBox: React.FC<{
  label: string;
  value: string;
  sublabel?: string;
  trend?: "up" | "down" | "neutral";
  highlight?: boolean;
  mandatory?: boolean;
  locked?: boolean;
}> = ({ label, value, sublabel, trend, highlight, mandatory, locked }) => (
  <div
    className={`p-3 rounded-lg ${highlight ? 'db-bg-row-active' : 'db-bg-surface-alt'}`}
  >
    <div className="db-font-xs mb-1 flex items-center gap-2 db-text-muted">
      <span className={mandatory ? "font-semibold" : ""}>{label}</span>
      {locked && (
        <span className="db-font-xs px-1.5 py-0.5 rounded db-surface-alt-text">
          Locked
        </span>
      )}
    </div>
    <div className="flex items-baseline gap-2">
      <span
        className={`text-lg font-semibold ${highlight ? 'db-text-accent' : 'db-text'}`}
      >
        {value}
      </span>
      {trend && trend !== "neutral" && (
        <span
          className={`db-font-xs ${trend === "up" ? 'db-text-green' : 'db-text-red'}`}
        >
          {trend === "up" ? <FaArrowUp size={10} /> : <FaArrowDown size={10} />}
        </span>
      )}
    </div>
    {sublabel && <span className="db-font-xs db-text-dim">{sublabel}</span>}
  </div>
);

const FinancialsPanel: React.FC<FinancialsPanelProps> = ({
  totals: totalsProp,
  currency = "USD",
}) => {
  // A default parameter covers undefined, not null. Records carry null envelopes,
  // and reading a field off null crashed the whole purchase form.
  // totals is the only total (Bill, 2026-09-18) — the old sell envelope is gone, and so is
  // the Cost Breakdown: header cost.line_sum_* came from the retired per-model totals and
  // the engine never writes it, so it showed $0 on every document (Bill, 2026-10-25).
  const totals = totalsProp ?? ({} as TransactionTotals);
  // WC3-aligned: margin lives on the totals envelope
  const marginAmount = totals.margin ?? 0;
  const marginPercent = totals.margin_pc ?? undefined;
  const marginTrend =
    marginPercent !== undefined
      ? marginPercent >= 20
        ? "up"
        : marginPercent >= 10
          ? "neutral"
          : "down"
      : "neutral";

  // The frame draws the header (label from the layout); the panel says only what is its own:
  // the currency (Bill, 2026-10-27 — panels inherit; this one drew a second header inside it).
  const currencyTag = useMemo(
    () => <span className="db-font-xs db-text-dim flex items-center gap-1"><FaDollarSign size={10} />{currency}</span>,
    [currency]);
  usePanelFrame({ headerActions: currencyTag });

  return (
    <div>

      {/* ── Totals ────────────────────────────────────────────── */}
      <div className="p-4 border-b db-border-color">
        <h4 className="db-font-xs font-semibold uppercase tracking-wide mb-3 flex items-center gap-2 db-text-muted">
          <FaChartLine size={10} />
          Totals
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatBox
            label="Subtotal"
            value={formatCurrency(totals.amount)}
            sublabel="Σ extended"
            mandatory
          />
          <StatBox
            label="Discount"
            value={formatCurrency(totals.discount)}
          />
          <StatBox
            label="Tax"
            value={formatCurrency(totals.tax)}
          />
          <StatBox
            label="Total"
            value={formatCurrency(totals.total)}
            highlight
          />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-2 gap-3 mt-3">
          <StatBox
            label="Shipping"
            value={formatCurrency(totals.shipping)}
          />
          <StatBox
            label="Other"
            value={formatCurrency(totals.other)}
          />
        </div>
      </div>

      {/* ── Totals & Margin ───────────────────────────────────── */}
      <div className="p-4 border-b db-border-color">
        <h4 className="db-font-xs font-semibold uppercase tracking-wide mb-3 flex items-center gap-2 db-text-muted">
          <FaPercentage size={10} />
          Margin Analysis
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatBox
            label="Grand Total"
            value={formatCurrency(totals.total)}
            highlight
            mandatory
          />
          <StatBox
            label="Total Cost"
            value={formatCurrency(totals.cost)}
          />
          <StatBox
            label="Margin $"
            value={formatCurrency(marginAmount)}
            trend={marginTrend}
          />
          <StatBox
            label="Margin %"
            value={marginPercent != null ? formatPercent(marginPercent, 2) : "--"}
            trend={marginTrend}
            highlight
          />
        </div>
      </div>

      {/* ── Cash status ────────────────────────────────────── */}
      <div className="p-4 db-bg-surface-alt">
        <h4 className="db-font-xs font-semibold uppercase tracking-wide mb-3 db-text-muted">
          Cash Status
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-2 gap-3">
          <StatBox
            label="Received"
            value={formatCurrency(totals.received ?? 0)}
          />
          <StatBox
            label="Balance"
            value={formatCurrency(totals.balance ?? 0)}
            trend={(totals.balance ?? 0) <= 0 ? "up" : "down"}
          />
        </div>
      </div>
    </div>
  );
};

export default withDevIdentifier(FinancialsPanel, 'FinancialsPanel', 'teal', 'apps/common/components/panels/FinancialsPanel.tsx');
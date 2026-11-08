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
import { useFormatting } from '@/context/FormattingContext';

/** The parent document's value and what is left unfilled on it — served by the GET as
 *  parent_summary (Bill, 2026-11-08: "it is ok to have in financials the order value and unfilled
 *  value of the remaining order. But the totals ... should be just for this specific invoice"). */
export interface ParentSummary {
  model: string; id: number; ida: string; status: string;
  amount: number; total: number; unfilled: number;
}

interface FinancialsPanelProps {
  totals?: TransactionTotals | null;
  currency?: string;
  parent?: ParentSummary | null;
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
  parent = null,
}) => {
  const fmt = useFormatting();
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
            value={formatCurrency(totals.amount, fmt)}
            sublabel="Σ extended"
            mandatory
          />
          <StatBox
            label="Discount"
            value={formatCurrency(totals.discount, fmt)}
          />
          <StatBox
            label="Tax"
            value={formatCurrency(totals.tax, fmt)}
          />
          <StatBox
            label="Total"
            value={formatCurrency(totals.total, fmt)}
            highlight
          />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-2 gap-3 mt-3">
          <StatBox
            label="Shipping"
            value={formatCurrency(totals.shipping, fmt)}
          />
          <StatBox
            label="Other"
            value={formatCurrency(totals.other, fmt)}
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
            value={formatCurrency(totals.total, fmt)}
            highlight
            mandatory
          />
          <StatBox
            label="Total Cost"
            value={formatCurrency(totals.cost, fmt)}
          />
          <StatBox
            label="Margin $"
            value={formatCurrency(marginAmount, fmt)}
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
      <div className={`p-4 db-bg-surface-alt${parent ? ' border-b db-border-color' : ''}`}>
        <h4 className="db-font-xs font-semibold uppercase tracking-wide mb-3 db-text-muted">
          Cash Status
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-2 gap-3">
          <StatBox
            label="Received"
            value={formatCurrency(totals.received ?? 0, fmt)}
          />
          <StatBox
            label="Balance"
            value={formatCurrency(totals.balance ?? 0, fmt)}
            trend={(totals.balance ?? 0) <= 0 ? "up" : "down"}
          />
        </div>
      </div>

      {/* ── The parent document — its figures, not this one's ───────── */}
      {parent && (
        <div className="p-4" data-wc="financials-parent">
          <h4 className="db-font-xs font-semibold uppercase tracking-wide mb-3 db-text-muted">
            {parent.model} {parent.ida} — the parent, not this document
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-2 gap-3">
            <StatBox
              label={`${parent.model} value`}
              value={formatCurrency(parent.total, fmt)}
              sublabel={`${parent.model} total incl. tax and shipping`}
            />
            <StatBox
              label="Unfilled"
              value={formatCurrency(parent.unfilled, fmt)}
              sublabel={`lines still open on the ${parent.model}`}
              trend={parent.unfilled > 0 ? "down" : "up"}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default withDevIdentifier(FinancialsPanel, 'FinancialsPanel', 'teal', 'apps/common/components/panels/FinancialsPanel.tsx');
/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * FinancialsPanel - Summary of totals, cost, sell with margin calculation
 *
 * Shared/common version used by detail pages.
 */
import React from "react";
import {
  FaDollarSign,
  FaPercentage,
  FaChartLine,
  FaArrowUp,
  FaArrowDown,
} from "react-icons/fa";
import type {
  TransactionTotals,
  TransactionCost,
  TransactionSell,
} from "@/apps/transactions/types/transactionTypes";
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import { formatCurrency, formatPercent } from '@/utils/stringUtils';

interface FinancialsPanelProps {
  totals?: TransactionTotals;
  cost?: TransactionCost;
  sell?: TransactionSell;
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
    <div className="text-xs mb-1 flex items-center gap-2 db-text-muted">
      <span className={mandatory ? "font-semibold" : ""}>{label}</span>
      {locked && (
        <span className="text-[10px] px-1.5 py-0.5 rounded db-surface-alt-text">
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
          className={`text-xs ${trend === "up" ? 'db-text-green' : 'db-text-red'}`}
        >
          {trend === "up" ? <FaArrowUp size={10} /> : <FaArrowDown size={10} />}
        </span>
      )}
    </div>
    {sublabel && <span className="text-xs db-text-dim">{sublabel}</span>}
  </div>
);

const FinancialsPanel: React.FC<FinancialsPanelProps> = ({
  totals = {} as TransactionTotals,
  cost = {} as TransactionCost,
  sell = {} as TransactionSell,
  currency = "USD",
}) => {
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

  return (
    <div className="rounded-lg border overflow-hidden db-panel">
      <div className="px-4 py-3 border-b db-section-bg">
        <div className="flex items-center gap-2">
          <FaDollarSign className="db-text-green" size={16} />
          <h3 className="font-semibold db-text">
            Financials
          </h3>
          <span className="text-xs ml-auto db-text-dim">{currency}</span>
        </div>
      </div>

      {/* ── Sell summary ──────────────────────────────────────── */}
      <div className="p-4 border-b db-border-color">
        <h4 className="text-xs font-semibold uppercase tracking-wide mb-3 flex items-center gap-2 db-text-muted">
          <FaChartLine size={10} />
          Sell Totals
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatBox
            label="Line Goods"
            value={formatCurrency(sell.line_sum_goods)}
            sublabel="Σ extended"
            mandatory
          />
          <StatBox
            label="Discount"
            value={formatCurrency(sell.discount)}
            sublabel="Line discounts"
          />
          <StatBox
            label="Tax"
            value={formatCurrency(sell.tax)}
          />
          <StatBox
            label="Sell Total"
            value={formatCurrency(sell.total)}
            highlight
          />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-3">
          <StatBox
            label="Shipping"
            value={formatCurrency(sell.shipping)}
          />
          <StatBox
            label="Handling"
            value={formatCurrency(sell.handling)}
          />
          <StatBox
            label="Other"
            value={formatCurrency(sell.other)}
          />
        </div>
      </div>

      {/* ── Cost breakdown ────────────────────────────────────── */}
      <div className="p-4 border-b db-border-color">
        <h4 className="text-xs font-semibold uppercase tracking-wide mb-3 db-text-muted">
          Cost Breakdown
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <StatBox
            label="Line Goods"
            value={formatCurrency(cost.line_sum_goods)}
            sublabel="Σ cost extended"
          />
          <StatBox
            label="Shipping"
            value={formatCurrency(cost.line_sum_shipping)}
          />
          <StatBox
            label="Handling"
            value={formatCurrency(cost.line_sum_handling)}
          />
          <StatBox
            label="Freight"
            value={formatCurrency(cost.freight)}
          />
          <StatBox
            label="Commissions"
            value={formatCurrency(cost.commissions)}
          />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-3">
          <StatBox
            label="Tax"
            value={formatCurrency(cost.tax)}
          />
          <StatBox
            label="Tax Rate"
            value={cost.tax_rate != null ? formatPercent(cost.tax_rate, 2) : "--"}
          />
          <StatBox
            label="Total Cost"
            value={formatCurrency(cost.total)}
            highlight
            mandatory
            locked
          />
        </div>
      </div>

      {/* ── Totals & Margin ───────────────────────────────────── */}
      <div className="p-4 border-b db-border-color">
        <h4 className="text-xs font-semibold uppercase tracking-wide mb-3 flex items-center gap-2 db-text-muted">
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

      {/* ── Payment status ────────────────────────────────────── */}
      <div className="p-4 db-bg-surface-alt">
        <h4 className="text-xs font-semibold uppercase tracking-wide mb-3 db-text-muted">
          Payment Status
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
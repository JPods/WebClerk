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

interface FinancialsPanelProps {
  totals?: TransactionTotals;
  cost?: TransactionCost;
  sell?: TransactionSell;
  currency?: string;
  /** Back-compat with old FinancialsCard usage (not used currently) */
  isEditing?: boolean;
}

const formatCurrency = (value?: number, currency: string = "USD"): string => {
  if (value === undefined || value === null) return "--";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(value);
};

const formatPercent = (value?: number): string => {
  if (value === undefined || value === null) return "--";
  return `${value.toFixed(2)}%`;
};

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
    className="p-3 rounded-lg"
    style={{ background: highlight ? 'var(--db-row-active)' : 'var(--db-surface-alt)' }}
  >
    <div className="text-xs mb-1 flex items-center gap-2" style={{ color: 'var(--db-text-muted)' }}>
      <span className={mandatory ? "font-semibold" : ""}>{label}</span>
      {locked && (
        <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: 'var(--db-surface-alt)', color: 'var(--db-text)' }}>
          Locked
        </span>
      )}
    </div>
    <div className="flex items-baseline gap-2">
      <span
        className="text-lg font-semibold"
        style={{ color: highlight ? 'var(--db-accent)' : 'var(--db-text)' }}
      >
        {value}
      </span>
      {trend && trend !== "neutral" && (
        <span
          className="text-xs"
          style={{ color: trend === "up" ? 'var(--db-accent-green)' : 'var(--db-accent-red)' }}
        >
          {trend === "up" ? <FaArrowUp size={10} /> : <FaArrowDown size={10} />}
        </span>
      )}
    </div>
    {sublabel && <span className="text-xs" style={{ color: 'var(--db-text-dim)' }}>{sublabel}</span>}
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
    <div className="rounded-lg border overflow-hidden" style={{ background: 'var(--db-surface)', borderColor: 'var(--db-border)' }}>
      <div className="px-4 py-3 border-b" style={{ background: 'var(--db-surface-alt)', borderColor: 'var(--db-border)' }}>
        <div className="flex items-center gap-2">
          <FaDollarSign style={{ color: 'var(--db-accent-green)' }} size={16} />
          <h3 className="font-semibold" style={{ color: 'var(--db-text)' }}>
            Financials
          </h3>
          <span className="text-xs ml-auto" style={{ color: 'var(--db-text-dim)' }}>{currency}</span>
        </div>
      </div>

      {/* ── Sell summary ──────────────────────────────────────── */}
      <div className="p-4 border-b" style={{ borderColor: 'var(--db-border)' }}>
        <h4 className="text-xs font-semibold uppercase tracking-wide mb-3 flex items-center gap-2" style={{ color: 'var(--db-text-muted)' }}>
          <FaChartLine size={10} />
          Sell Totals
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatBox
            label="Line Goods"
            value={formatCurrency(sell.line_sum_goods, currency)}
            sublabel="Σ extended"
            mandatory
          />
          <StatBox
            label="Discount"
            value={formatCurrency(sell.discount, currency)}
            sublabel="Line discounts"
          />
          <StatBox
            label="Tax"
            value={formatCurrency(sell.tax, currency)}
          />
          <StatBox
            label="Sell Total"
            value={formatCurrency(sell.total, currency)}
            highlight
          />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-3">
          <StatBox
            label="Shipping"
            value={formatCurrency(sell.shipping, currency)}
          />
          <StatBox
            label="Handling"
            value={formatCurrency(sell.handling, currency)}
          />
          <StatBox
            label="Other"
            value={formatCurrency(sell.other, currency)}
          />
        </div>
      </div>

      {/* ── Cost breakdown ────────────────────────────────────── */}
      <div className="p-4 border-b" style={{ borderColor: 'var(--db-border)' }}>
        <h4 className="text-xs font-semibold uppercase tracking-wide mb-3" style={{ color: 'var(--db-text-muted)' }}>
          Cost Breakdown
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <StatBox
            label="Line Goods"
            value={formatCurrency(cost.line_sum_goods, currency)}
            sublabel="Σ cost extended"
          />
          <StatBox
            label="Shipping"
            value={formatCurrency(cost.line_sum_shipping, currency)}
          />
          <StatBox
            label="Handling"
            value={formatCurrency(cost.line_sum_handling, currency)}
          />
          <StatBox
            label="Freight"
            value={formatCurrency(cost.freight, currency)}
          />
          <StatBox
            label="Commissions"
            value={formatCurrency(cost.commissions, currency)}
          />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-3">
          <StatBox
            label="Tax"
            value={formatCurrency(cost.tax, currency)}
          />
          <StatBox
            label="Tax Rate"
            value={cost.tax_rate != null ? formatPercent(cost.tax_rate) : "--"}
          />
          <StatBox
            label="Total Cost"
            value={formatCurrency(cost.total, currency)}
            highlight
            mandatory
            locked
          />
        </div>
      </div>

      {/* ── Totals & Margin ───────────────────────────────────── */}
      <div className="p-4 border-b" style={{ borderColor: 'var(--db-border)' }}>
        <h4 className="text-xs font-semibold uppercase tracking-wide mb-3 flex items-center gap-2" style={{ color: 'var(--db-text-muted)' }}>
          <FaPercentage size={10} />
          Margin Analysis
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatBox
            label="Grand Total"
            value={formatCurrency(totals.total, currency)}
            highlight
            mandatory
          />
          <StatBox
            label="Total Cost"
            value={formatCurrency(totals.cost, currency)}
          />
          <StatBox
            label="Margin $"
            value={formatCurrency(marginAmount, currency)}
            trend={marginTrend}
          />
          <StatBox
            label="Margin %"
            value={marginPercent != null ? formatPercent(marginPercent) : "--"}
            trend={marginTrend}
            highlight
          />
        </div>
      </div>

      {/* ── Payment status ────────────────────────────────────── */}
      <div className="p-4" style={{ background: 'var(--db-surface-alt)' }}>
        <h4 className="text-xs font-semibold uppercase tracking-wide mb-3" style={{ color: 'var(--db-text-muted)' }}>
          Payment Status
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-2 gap-3">
          <StatBox
            label="Received"
            value={formatCurrency(totals.received ?? 0, currency)}
          />
          <StatBox
            label="Balance"
            value={formatCurrency(totals.balance ?? 0, currency)}
            trend={(totals.balance ?? 0) <= 0 ? "up" : "down"}
          />
        </div>
      </div>
    </div>
  );
};

export default withDevIdentifier(FinancialsPanel, 'FinancialsPanel', 'teal', 'apps/common/components/panels/FinancialsPanel.tsx');
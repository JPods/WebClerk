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
    className={`p-3 rounded-lg ${
      highlight
        ? "bg-blue-50 dark:bg-blue-900/20"
        : "bg-slate-50 dark:bg-slate-800/50"
    }`}
  >
    <div className="text-xs text-slate-500 dark:text-slate-400 mb-1 flex items-center gap-2">
      <span className={mandatory ? "font-semibold" : ""}>{label}</span>
      {locked && (
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
          Locked
        </span>
      )}
    </div>
    <div className="flex items-baseline gap-2">
      <span
        className={`text-lg font-semibold ${
          highlight
            ? "text-blue-600 dark:text-blue-400"
            : "text-slate-900 dark:text-white"
        }`}
      >
        {value}
      </span>
      {trend && trend !== "neutral" && (
        <span
          className={`text-xs ${
            trend === "up" ? "text-green-500" : "text-red-500"
          }`}
        >
          {trend === "up" ? <FaArrowUp size={10} /> : <FaArrowDown size={10} />}
        </span>
      )}
    </div>
    {sublabel && <span className="text-xs text-slate-400">{sublabel}</span>}
  </div>
);

const FinancialsPanel: React.FC<FinancialsPanelProps> = ({
  totals = {},
  cost = {},
  sell = {},
  currency = "USD",
}) => {
  const grossMarginAmount = (totals.ex ?? 0) - (cost.total ?? 0);
  const grossMarginPercent =
    totals.ex && totals.ex > 0
      ? (grossMarginAmount / totals.ex) * 100
      : undefined;
  const marginTrend =
    grossMarginPercent !== undefined
      ? grossMarginPercent >= 20
        ? "up"
        : grossMarginPercent >= 10
          ? "neutral"
          : "down"
      : "neutral";

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
      <div className="px-4 py-3 bg-slate-50 dark:bg-slate-900/50 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-2">
          <FaDollarSign className="text-green-500" size={16} />
          <h3 className="font-semibold text-slate-900 dark:text-white">
            Financials
          </h3>
          <span className="text-xs text-slate-400 ml-auto">{currency}</span>
        </div>
      </div>

      <div className="p-4 border-b border-slate-200 dark:border-slate-700">
        <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-3 flex items-center gap-2">
          <FaChartLine size={10} />
          Transaction Totals
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatBox
            label="Total (ex Tax)"
            value={formatCurrency(totals.ex, currency)}
            mandatory
          />
          <StatBox label="Tax" value={formatCurrency(totals.tax, currency)} />
          <StatBox
            label="Total (inc Tax)"
            value={formatCurrency(totals.inc, currency)}
            highlight
          />
          <StatBox
            label="Deposit"
            value={formatCurrency(totals.deposit, currency)}
          />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
          <StatBox label="Net Total" value={formatCurrency(totals.net, currency)} />
          <StatBox label="Quantity" value={totals.qty?.toString() ?? "--"} />
          <StatBox label="Pieces" value={totals.pcs?.toString() ?? "--"} />
          <StatBox
            label="Weight"
            value={totals.wt ? `${totals.wt} kg` : "--"}
          />
        </div>
      </div>

      <div className="p-4 border-b border-slate-200 dark:border-slate-700">
        <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-3">
          Cost Breakdown
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <StatBox
            label="Items"
            value={formatCurrency(cost.items, currency)}
            sublabel="Product cost"
          />
          <StatBox label="Freight" value={formatCurrency(cost.freight, currency)} />
          <StatBox
            label="Landing"
            value={formatCurrency(cost.landing, currency)}
            sublabel="Duties/fees"
          />
          <StatBox
            label="Overhead"
            value={formatCurrency(cost.overhead, currency)}
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

      <div className="p-4 border-b border-slate-200 dark:border-slate-700">
        <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-3">
          Sell Pricing
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <StatBox
            label="Retail"
            value={formatCurrency(sell.retail, currency)}
            sublabel="List price"
          />
          <StatBox
            label="Trade"
            value={formatCurrency(sell.trade, currency)}
            sublabel="Wholesale"
          />
          <StatBox
            label="Contract"
            value={formatCurrency(sell.contract, currency)}
            sublabel="Agreed price"
          />
          <StatBox
            label="Promo"
            value={formatCurrency(sell.promo, currency)}
            sublabel="Special"
          />
          <StatBox
            label="Selling Price"
            value={formatCurrency(sell.total, currency)}
            highlight
          />
        </div>
      </div>

      <div className="p-4 bg-slate-50 dark:bg-slate-900/30">
        <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-3 flex items-center gap-2">
          <FaPercentage size={10} />
          Margin Analysis
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <StatBox
            label="Gross Margin $"
            value={formatCurrency(grossMarginAmount, currency)}
            trend={marginTrend}
          />
          <StatBox
            label="Gross Margin %"
            value={formatPercent(grossMarginPercent)}
            trend={marginTrend}
            highlight
          />
          <StatBox
            label="Target Margin"
            value={formatPercent(sell.target_margin_percent)}
            sublabel="Goal"
          />
        </div>
      </div>
    </div>
  );
};

export default FinancialsPanel;

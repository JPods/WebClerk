/**
 * FinancialsCard - Summary of totals, cost, sell with margin calculation
 * Shows tax-exclusive totals, gross margins, and cost breakdowns
 */
import React from 'react';
import { FaDollarSign, FaPercentage, FaChartLine, FaArrowUp, FaArrowDown } from 'react-icons/fa';
import FieldLabel from './FieldLabel';
import type { 
  TransactionTotals, 
  TransactionCost, 
  TransactionSell 
} from '../types/transactionTypes';

interface FinancialsCardProps {
  totals?: TransactionTotals;
  cost?: TransactionCost;
  sell?: TransactionSell;
  currency?: string;
  isEditing?: boolean;
  onChange?: (field: 'totals' | 'cost' | 'sell', value: unknown) => void;
}

const formatCurrency = (value?: number, currency: string = 'USD'): string => {
  if (value === undefined || value === null) return '--';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(value);
};

const formatPercent = (value?: number): string => {
  if (value === undefined || value === null) return '--';
  return `${value.toFixed(2)}%`;
};

const StatBox: React.FC<{
  label: string;
  value: string;
  sublabel?: string;
  trend?: 'up' | 'down' | 'neutral';
  highlight?: boolean;
  mandatory?: boolean;
  locked?: boolean;
}> = ({ label, value, sublabel, trend, highlight, mandatory, locked }) => (
  <div className={`p-3 rounded-lg ${highlight ? 'bg-blue-50 dark:bg-blue-900/20' : 'bg-slate-50 dark:bg-slate-800/50'}`}>
    <FieldLabel label={label} mandatory={mandatory} locked={locked} className="text-xs text-slate-500 dark:text-slate-400 mb-1" />
    <div className="flex items-baseline gap-2">
      <span className={`text-lg font-semibold ${highlight ? 'text-blue-600 dark:text-blue-400' : 'text-slate-900 dark:text-white'}`}>
        {value}
      </span>
      {trend && trend !== 'neutral' && (
        <span className={`text-xs ${trend === 'up' ? 'text-green-500' : 'text-red-500'}`}>
          {trend === 'up' ? <FaArrowUp size={10} /> : <FaArrowDown size={10} />}
        </span>
      )}
    </div>
    {sublabel && <span className="text-xs text-slate-400">{sublabel}</span>}
  </div>
);

const FinancialsCard: React.FC<FinancialsCardProps> = ({
  totals = {},
  cost = {},
  sell = {},
  currency = 'USD',
  isEditing = false,
  onChange,
}) => {
  const toNumber = (value?: number | null): number => (value ?? 0);

  // Normalize totals from backend (subtotal/tax/total) or legacy (ex/inc)
  const subtotal = toNumber(totals.subtotal ?? (totals as Record<string, number | null>).ex);
  const discount = toNumber(totals.discount);
  const taxable = toNumber(totals.taxable ?? subtotal - discount);
  const tax = toNumber(totals.tax);
  const shipping = toNumber(totals.shipping);
  const other = toNumber(totals.other);
  const total = toNumber(
    totals.total ?? (totals as Record<string, number | null>).inc ?? taxable + tax + shipping + other,
  );
  const received = toNumber(totals.received ?? (totals as Record<string, number | null>).deposit);
  const balance = toNumber(totals.balance ?? total - received);

  const costTotal = toNumber(cost.total ?? totals.cost);
  const marginAmount = toNumber(totals.margin ?? total - costTotal);
  const marginPercent = totals.margin_pc !== undefined && totals.margin_pc !== null
    ? totals.margin_pc
    : total > 0
      ? (marginAmount / total) * 100
      : undefined;

  const marginTrend = marginPercent !== undefined 
    ? marginPercent >= 20 ? 'up' : marginPercent >= 10 ? 'neutral' : 'down'
    : 'neutral';

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-slate-50 dark:bg-slate-900/50 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-2">
          <FaDollarSign className="text-green-500" size={16} />
          <h3 className="font-semibold text-slate-900 dark:text-white">Financials</h3>
          <span className="text-xs text-slate-400 ml-auto">{currency}</span>
        </div>
      </div>

      {/* Totals Section */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-700">
        <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-3 flex items-center gap-2">
          <FaChartLine size={10} />
          Transaction Totals
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatBox 
            label="Subtotal" 
            value={formatCurrency(subtotal, currency)} 
            mandatory 
          />
          <StatBox 
            label="Discount" 
            value={formatCurrency(discount, currency)} 
          />
          <StatBox 
            label="Tax" 
            value={formatCurrency(tax, currency)} 
          />
          <StatBox 
            label="Total" 
            value={formatCurrency(total, currency)} 
            highlight 
          />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
          <StatBox 
            label="Shipping" 
            value={formatCurrency(shipping, currency)} 
          />
          <StatBox 
            label="Other" 
            value={formatCurrency(other, currency)} 
          />
          <StatBox 
            label="Received" 
            value={formatCurrency(received, currency)} 
          />
          <StatBox 
            label="Balance" 
            value={formatCurrency(balance, currency)} 
          />
        </div>
      </div>

      {/* Cost Section */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-700">
        <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-3">
          Cost Breakdown
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          <StatBox 
            label="Items" 
            value={formatCurrency(cost.line_sum_goods, currency)} 
            sublabel="Product cost"
          />
          <StatBox 
            label="Tax" 
            value={formatCurrency(cost.line_sum_tax, currency)} 
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
            label="Total Cost" 
            value={formatCurrency(costTotal, currency)} 
            highlight 
            mandatory 
            locked 
          />
        </div>
      </div>

      {/* Sell Section */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-700">
        <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-3">
          Sell Pricing
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <StatBox 
            label="Line Sum" 
            value={formatCurrency(sell.line_sum_goods, currency)} 
          />
          <StatBox 
            label="Discount" 
            value={formatCurrency(sell.discount, currency)} 
          />
          <StatBox 
            label="Tax" 
            value={formatCurrency(sell.tax, currency)} 
          />
          <StatBox 
            label="Other" 
            value={formatCurrency(sell.other, currency)} 
          />
          <StatBox 
            label="Sell Total" 
            value={formatCurrency(sell.total ?? total, currency)} 
            highlight 
          />
        </div>
      </div>

      {/* Margin Section */}
      <div className="p-4 bg-slate-50 dark:bg-slate-900/30">
        <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-3 flex items-center gap-2">
          <FaPercentage size={10} />
          Margin Analysis
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <StatBox 
            label="Margin $" 
            value={formatCurrency(marginAmount, currency)} 
            trend={marginTrend}
          />
          <StatBox 
            label="Margin %" 
            value={formatPercent(marginPercent)} 
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

export default FinancialsCard;

/**
 * FinancialSummaryPanel - Single-row summary of org financial data
 * 
 * Displays key financial metrics inline as label: value pairs.
 * Always expanded - no collapse functionality.
 */
import React from 'react';
import { FaDollarSign } from 'react-icons/fa';
import type { OrgFinancialCustomer, OrgFinancialCommon, OrgFinancialVendor } from '@/apps/orgs/types/orgTypes';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FinancialSummaryPanelProps {
  /** Customer-specific financial data */
  customer?: OrgFinancialCustomer;
  /** Vendor-specific financial data */
  vendor?: OrgFinancialVendor;
  /** Common financial data (shared across org types) */
  common?: OrgFinancialCommon;
  /** Currency code (default: USD) */
  currency?: string;
  /** Additional CSS classes */
  className?: string;
  /** Panel title */
  title?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const fmt = {
  currency: (v: number | undefined | null, c: string = 'USD'): string => {
    if (v === undefined || v === null) return '—';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: c, minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(v);
  },
  pct: (v: number | undefined | null): string => {
    if (v === undefined || v === null) return '—';
    return `${v.toFixed(1)}%`;
  },
};

// ---------------------------------------------------------------------------
// Inline Metric Component
// ---------------------------------------------------------------------------

interface MetricProps {
  label: string;
  value: string;
  warn?: boolean;
}

const Metric: React.FC<MetricProps> = ({ label, value, warn }) => (
  <span className="inline-flex items-center gap-1">
    <span className="text-xs text-slate-500 dark:text-slate-400">{label}:</span>
    <span className={`text-xs font-semibold font-mono ${
      warn ? 'text-amber-600' : 'text-slate-700 dark:text-slate-200'
    }`}>
      {value}
    </span>
  </span>
);

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

const FinancialSummaryPanel: React.FC<FinancialSummaryPanelProps> = ({
  customer,
  vendor,
  common,
  currency = 'USD',
  className = '',
  title = 'Financial Summary',
}) => {
  // Determine org type based on which data is present
  const isCustomer = !!customer;
  const isVendor = !!vendor && !customer;

  // Extract key metrics
  const creditLimit = customer?.credit?.limit ?? vendor?.credit?.limit;
  const creditAvailable = customer?.credit?.available ?? vendor?.credit?.available;
  const balanceDue = customer?.balances?.due ?? vendor?.balances?.due;
  const balanceCurrent = customer?.balances?.current ?? vendor?.balances?.current;
  const ytdSales = customer?.sales?.ytd ?? vendor?.purchases?.ytd;
  const hasAging = customer?.aging && (customer.aging.period_2 || customer.aging.period_3);
  const agingOverdue = (customer?.aging?.period_2 ?? 0) + (customer?.aging?.period_3 ?? 0);
  const onHold = common?.account?.hold;

  if (!customer && !vendor && !common) {
    return null;
  }

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-lg border border-green-200 dark:border-green-800 ${className}`}>
      <div className="flex items-center justify-between px-4 py-2 bg-green-50 dark:bg-green-900/20 rounded-lg">
        {/* Title */}
        <div className="flex items-center gap-2">
          <FaDollarSign className="text-green-500" size={14} />
          <span className="text-sm font-semibold text-green-700 dark:text-green-300">{title}</span>
        </div>

        {/* Metrics row */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          {/* Credit */}
          {creditLimit !== undefined && (
            <Metric label="Credit" value={fmt.currency(creditLimit, currency)} />
          )}
          {creditAvailable !== undefined && (
            <Metric label="Available" value={fmt.currency(creditAvailable, currency)} />
          )}

          {/* Balance */}
          {balanceDue !== undefined && (
            <Metric label="Due" value={fmt.currency(balanceDue, currency)} warn={true} />
          )}
          {balanceCurrent !== undefined && !balanceDue && (
            <Metric label="Current" value={fmt.currency(balanceCurrent, currency)} />
          )}

          {/* YTD Sales/Purchases */}
          {ytdSales !== undefined && (
            <Metric label={isVendor ? "YTD Purch" : "YTD Sales"} value={fmt.currency(ytdSales, currency)} />
          )}

          {/* Aging (customer only) */}
          {isCustomer && hasAging && agingOverdue > 0 && (
            <Metric label="Overdue" value={fmt.currency(agingOverdue, currency)} warn={true} />
          )}

          {/* Margin % (customer only) */}
          {customer?.margin?.pct !== undefined && (
            <Metric label="Margin" value={fmt.pct(customer.margin.pct)} />
          )}

          {/* Discount */}
          {common?.settings?.discount_pct !== undefined && common.settings.discount_pct > 0 && (
            <Metric label="Discount" value={fmt.pct(common.settings.discount_pct)} />
          )}

          {/* Status badges */}
          {onHold && (
            <span className="px-1.5 py-0.5 text-[10px] bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded font-semibold">
              HOLD
            </span>
          )}
          {common?.account?.cod_only && (
            <span className="px-1.5 py-0.5 text-[10px] bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 rounded font-semibold">
              COD
            </span>
          )}
          {common?.settings?.tax_exempt && (
            <span className="px-1.5 py-0.5 text-[10px] bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded font-semibold">
              TAX EXEMPT
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default FinancialSummaryPanel;

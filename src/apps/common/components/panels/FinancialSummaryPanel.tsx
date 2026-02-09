/**
 * FinancialSummaryPanel - Collapsible summary of org financial data
 * 
 * Displays key financial metrics in a compact, collapsible format.
 * Collapsed by default - shows only header with total/balance due.
 * Expand to see key metrics: Credit, Balance, YTD Sales, Aging.
 */
import React, { useState } from 'react';
import { FaDollarSign, FaChevronDown, FaChevronUp } from 'react-icons/fa';
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
  /** Start collapsed (default: true) */
  defaultCollapsed?: boolean;
  /** Panel title */
  title?: string;
  /** Number of columns for metric cards (default: 3) */
  columns?: 2 | 3;
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
// Metric Card Component
// ---------------------------------------------------------------------------

interface MetricCardProps {
  label: string;
  value: string;
  subValue?: string;
  warn?: boolean;
  neg?: boolean;
}

const MetricCard: React.FC<MetricCardProps> = ({ label, value, subValue, warn, neg }) => (
  <div className="bg-slate-50 dark:bg-slate-900/50 rounded px-3 py-2">
    <div className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-0.5">
      {label}
    </div>
    <div className={`text-sm font-semibold font-mono ${
      neg ? 'text-red-600' : warn ? 'text-amber-600' : 'text-slate-700 dark:text-slate-200'
    }`}>
      {value}
    </div>
    {subValue && (
      <div className="text-[10px] text-slate-400 dark:text-slate-500">{subValue}</div>
    )}
  </div>
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
  defaultCollapsed = true,
  title = 'Financial Summary',
  columns = 3,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);

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

  // Header summary value
  const headerValue = balanceDue ?? ytdSales;

  if (!customer && !vendor && !common) {
    return null;
  }

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-lg border border-green-200 dark:border-green-800 ${className}`}>
      {/* Header - Always visible */}
      <div
        className="flex items-center justify-between px-4 py-2 bg-green-50 dark:bg-green-900/20 cursor-pointer rounded-lg"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaDollarSign className="text-green-500" size={14} />
          <span className="text-sm font-semibold text-green-700 dark:text-green-300">{title}</span>
          {onHold && (
            <span className="px-1.5 py-0.5 text-[10px] bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded font-semibold uppercase">
              Hold
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {/* Show key value in collapsed state */}
          {isCollapsed && headerValue !== undefined && (
            <span className={`text-sm font-mono font-semibold ${
              balanceDue ? 'text-amber-600' : 'text-green-600'
            }`}>
              {balanceDue ? `Due: ${fmt.currency(balanceDue, currency)}` : fmt.currency(headerValue, currency)}
            </span>
          )}
          {isCollapsed ? (
            <FaChevronDown size={12} className="text-slate-400" />
          ) : (
            <FaChevronUp size={12} className="text-slate-400" />
          )}
        </div>
      </div>

      {/* Expanded Content */}
      {!isCollapsed && (
        <div className="px-4 py-3 border-t border-green-200 dark:border-green-800">
          <div className={`grid grid-cols-1 sm:grid-cols-2 ${columns === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-2'} gap-2`}>
            {/* Credit */}
            {creditLimit !== undefined && (
              <MetricCard
                label="Credit Limit"
                value={fmt.currency(creditLimit, currency)}
                subValue={creditAvailable !== undefined ? `Avail: ${fmt.currency(creditAvailable, currency)}` : undefined}
              />
            )}

            {/* Balance */}
            {(balanceDue !== undefined || balanceCurrent !== undefined) && (
              <MetricCard
                label={balanceDue ? "Balance Due" : "Current"}
                value={fmt.currency(balanceDue ?? balanceCurrent, currency)}
                warn={!!balanceDue}
              />
            )}

            {/* YTD Sales/Purchases */}
            {ytdSales !== undefined && (
              <MetricCard
                label={isVendor ? "YTD Purchases" : "YTD Sales"}
                value={fmt.currency(ytdSales, currency)}
              />
            )}

            {/* Aging (customer only) */}
            {isCustomer && hasAging && (
              <MetricCard
                label="Overdue (31+)"
                value={fmt.currency(agingOverdue, currency)}
                warn={agingOverdue > 0}
              />
            )}

            {/* Margin % (customer only) */}
            {customer?.margin?.pct !== undefined && (
              <MetricCard
                label="Margin %"
                value={fmt.pct(customer.margin.pct)}
              />
            )}

            {/* Settings */}
            {common?.settings?.discount_pct !== undefined && common.settings.discount_pct > 0 && (
              <MetricCard
                label="Discount"
                value={fmt.pct(common.settings.discount_pct)}
              />
            )}
          </div>

          {/* Warnings row */}
          {(onHold || common?.account?.cod_only || common?.settings?.tax_exempt) && (
            <div className="flex gap-2 mt-2 pt-2 border-t border-slate-200 dark:border-slate-700">
              {onHold && (
                <span className="px-2 py-0.5 text-xs bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded">
                  Account on Hold
                </span>
              )}
              {common?.account?.cod_only && (
                <span className="px-2 py-0.5 text-xs bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 rounded">
                  COD Only
                </span>
              )}
              {common?.settings?.tax_exempt && (
                <span className="px-2 py-0.5 text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded">
                  Tax Exempt
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FinancialSummaryPanel;

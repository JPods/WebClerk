/**
 * CustomerFinancialPanel - Compact read-only display of customer financial data
 * 
 * Displays OrgFinancialCustomer fields with italic labels on left, values on right.
 * Designed for compact embedding in detail views.
 */
import React from 'react';
import type { OrgFinancialCustomer, OrgFinancialCommon } from '@/apps/orgs/types/orgTypes';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CustomerFinancialPanelProps {
  /** Customer financial data */
  customer?: OrgFinancialCustomer;
  /** Common financial data (shared across org types) */
  common?: OrgFinancialCommon;
  /** Currency code (default: USD) */
  currency?: string;
  /** Additional CSS classes */
  className?: string;
  /** Show all sections (default: true shows only populated) */
  showAll?: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const fmt = {
  currency: (v: number | undefined | null, c: string = 'USD'): string => {
    if (v === undefined || v === null) return '—';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: c, minimumFractionDigits: 2 }).format(v);
  },
  pct: (v: number | undefined | null): string => {
    if (v === undefined || v === null) return '—';
    return `${v.toFixed(1)}%`;
  },
  num: (v: number | undefined | null): string => {
    if (v === undefined || v === null) return '—';
    return new Intl.NumberFormat('en-US').format(v);
  },
  date: (v: string | null | undefined): string => {
    if (!v) return '—';
    return new Date(v).toLocaleDateString();
  },
  days: (v: number | undefined | null): string => {
    if (v === undefined || v === null) return '—';
    return `${v}d`;
  },
};

// ---------------------------------------------------------------------------
// Row Component - Compact label/value pair
// ---------------------------------------------------------------------------

interface RowProps {
  label: string;
  value: string;
  warn?: boolean;
  neg?: boolean;
}

const Row: React.FC<RowProps> = ({ label, value, warn, neg }) => (
  <div className="flex justify-between items-baseline py-0.5 text-xs">
    <span className="italic text-slate-500 dark:text-slate-400">{label}</span>
    <span className={`font-mono ${neg ? 'text-red-600' : warn ? 'text-amber-600' : 'text-slate-700 dark:text-slate-300'}`}>
      {value}
    </span>
  </div>
);

// ---------------------------------------------------------------------------
// Section Header
// ---------------------------------------------------------------------------

const SectionHeader: React.FC<{ title: string }> = ({ title }) => (
  <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 mt-2 mb-0.5 border-b border-slate-200 dark:border-slate-700">
    {title}
  </div>
);

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

const CustomerFinancialPanel: React.FC<CustomerFinancialPanelProps> = ({
  customer,
  common,
  currency = 'USD',
  className = '',
  showAll = false,
}) => {
  if (!customer && !common) {
    return <div className={`text-xs text-slate-400 ${className}`}>No financial data</div>;
  }

  const c = customer;
  const hasCredit = c?.credit && (c.credit.limit || c.credit.available || c.credit.high);
  const hasBalances = c?.balances && (c.balances.due || c.balances.current || c.balances.open_orders);
  const hasAging = c?.aging && (c.aging.period_1 || c.aging.period_2 || c.aging.period_3);
  const hasSales = c?.sales && (c.sales.mtd || c.sales.ytd || c.sales.lifetime);
  const hasMargin = c?.margin && (c.margin.mtd || c.margin.ytd || c.margin.pct);
  const hasPayment = c?.payment && (c.payment.days_avg_paid || c.payment.dt_last_payment);
  const hasReturns = c?.returns && (c.returns.mtd || c.returns.ytd || c.returns.count);
  const hasDeposits = c?.deposits?.unapplied;
  const hasCollection = c?.collection && (c.collection.cost_mtd || c.collection.cost_ytd);
  const hasMinimums = c?.minimums && (c.minimums.order || c.minimums.payment);
  const hasCommon = common && (common.account?.hold || common.settings?.discount_pct || common.settings?.tax_exempt);

  return (
    <div className={`space-y-1 ${className}`}>
      {/* Credit */}
      {(showAll || hasCredit) && (
        <>
          <SectionHeader title="Credit" />
          <Row label="Limit" value={fmt.currency(c?.credit?.limit, currency)} />
          <Row label="Available" value={fmt.currency(c?.credit?.available, currency)} />
          <Row label="High" value={fmt.currency(c?.credit?.high, currency)} />
        </>
      )}

      {/* Balances */}
      {(showAll || hasBalances) && (
        <>
          <SectionHeader title="Balances" />
          <Row label="Due" value={fmt.currency(c?.balances?.due, currency)} warn={!!c?.balances?.due} />
          <Row label="Current" value={fmt.currency(c?.balances?.current, currency)} />
          <Row label="Open Orders" value={fmt.currency(c?.balances?.open_orders, currency)} />
          <Row label="Exposure" value={fmt.currency(c?.balances?.total_exposure, currency)} />
        </>
      )}

      {/* Aging */}
      {(showAll || hasAging) && (
        <>
          <SectionHeader title="Aging" />
          <Row label="Future" value={fmt.currency(c?.aging?.future, currency)} />
          <Row label="1-30" value={fmt.currency(c?.aging?.period_1, currency)} />
          <Row label="31-60" value={fmt.currency(c?.aging?.period_2, currency)} warn={!!c?.aging?.period_2} />
          <Row label="61-90+" value={fmt.currency(c?.aging?.period_3, currency)} warn={!!c?.aging?.period_3} />
        </>
      )}

      {/* Sales */}
      {(showAll || hasSales) && (
        <>
          <SectionHeader title="Sales" />
          <Row label="MTD" value={fmt.currency(c?.sales?.mtd, currency)} />
          <Row label="YTD" value={fmt.currency(c?.sales?.ytd, currency)} />
          <Row label="Lifetime" value={fmt.currency(c?.sales?.lifetime, currency)} />
          <Row label="Last Sale" value={fmt.date(c?.sales?.dt_last_sale)} />
          <Row label="Last Amt" value={fmt.currency(c?.sales?.last_sale_amount, currency)} />
        </>
      )}

      {/* Margin */}
      {(showAll || hasMargin) && (
        <>
          <SectionHeader title="Margin" />
          <Row label="MTD" value={fmt.currency(c?.margin?.mtd, currency)} />
          <Row label="YTD" value={fmt.currency(c?.margin?.ytd, currency)} />
          <Row label="Pct" value={fmt.pct(c?.margin?.pct)} />
        </>
      )}

      {/* Payment */}
      {(showAll || hasPayment) && (
        <>
          <SectionHeader title="Payment" />
          <Row label="Avg Days" value={fmt.days(c?.payment?.days_avg_paid)} />
          <Row label="Terms" value={fmt.days(c?.payment?.days_pay)} />
          <Row label="Last Pmt" value={fmt.date(c?.payment?.dt_last_payment)} />
          <Row label="Last Amt" value={fmt.currency(c?.payment?.last_payment_amount, currency)} />
        </>
      )}

      {/* Returns */}
      {(showAll || hasReturns) && (
        <>
          <SectionHeader title="Returns" />
          <Row label="MTD" value={fmt.currency(c?.returns?.mtd, currency)} neg />
          <Row label="YTD" value={fmt.currency(c?.returns?.ytd, currency)} neg />
          <Row label="Count" value={fmt.num(c?.returns?.count)} />
        </>
      )}

      {/* Deposits */}
      {(showAll || hasDeposits) && (
        <>
          <SectionHeader title="Deposits" />
          <Row label="Unapplied" value={fmt.currency(c?.deposits?.unapplied, currency)} />
        </>
      )}

      {/* Collection */}
      {(showAll || hasCollection) && (
        <>
          <SectionHeader title="Collection" />
          <Row label="Cost MTD" value={fmt.currency(c?.collection?.cost_mtd, currency)} neg />
          <Row label="Cost YTD" value={fmt.currency(c?.collection?.cost_ytd, currency)} neg />
          <Row label="All-time" value={fmt.currency(c?.collection?.cost_alltime, currency)} neg />
        </>
      )}

      {/* Minimums */}
      {(showAll || hasMinimums) && (
        <>
          <SectionHeader title="Minimums" />
          <Row label="Order" value={fmt.currency(c?.minimums?.order, currency)} />
          <Row label="Payment" value={fmt.currency(c?.minimums?.payment, currency)} />
        </>
      )}

      {/* Common Settings */}
      {(showAll || hasCommon) && (
        <>
          <SectionHeader title="Settings" />
          {common?.account?.hold && <Row label="Hold" value="YES" warn />}
          {common?.account?.cod_only && <Row label="COD Only" value="YES" warn />}
          <Row label="Discount" value={fmt.pct(common?.settings?.discount_pct)} />
          <Row label="Tax Exempt" value={common?.settings?.tax_exempt ? 'Yes' : 'No'} />
        </>
      )}
    </div>
  );
};

export default CustomerFinancialPanel;

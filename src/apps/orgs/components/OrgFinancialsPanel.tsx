/**
 * OrgFinancialsPanel - Display type-keyed financial data for organizations
 * 
 * Shows tabbed view based on org types (customer, vendor, rep, employee, manufacturer)
 * Each tab displays relevant financial metrics for that org role.
 */
import React, { useState } from 'react';
import { 
  FaDollarSign, FaChevronDown, FaChevronUp, FaPercent, 
  FaUser, FaBuilding, FaUserTie, FaIdBadge, FaIndustry,
  FaCreditCard, FaExclamationTriangle, FaChartLine, FaClock,
  FaBalanceScale, FaFileInvoice, FaMoneyCheckAlt, FaHandHoldingUsd
} from 'react-icons/fa';
import type { 
  OrgFinancial, OrgFinancialCustomer, OrgFinancialVendor, 
  OrgFinancialRep, OrgFinancialEmployee, OrgFinancialManufacturer,
  OrgFinancialCommon, OrgType
} from '../types/orgTypes';
import { withDevIdentifier } from '@/components/common/DevIdentifier';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface OrgFinancialsPanelProps {
  /** Financial data from org */
  financial?: OrgFinancial;
  /** Org type(s) to determine which tabs to show */
  orgType?: OrgType;
  /** Additional org types (for multi-type orgs) */
  orgTypes?: OrgType[];
  /** Editing mode */
  editing?: boolean;
  /** Change handler */
  onChange?: (financial: OrgFinancial) => void;
  /** Panel title */
  title?: string;
  /** Start collapsed */
  defaultCollapsed?: boolean;
  /** Compact mode */
  compact?: boolean;
  /** Currency for display */
  currency?: string;
  /** Additional CSS classes */
  className?: string;
}

type FinancialTabKey = 'common' | 'customer' | 'vendor' | 'rep' | 'employee' | 'manufacturer';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const formatCurrency = (value: number | undefined | null, currency: string = 'USD'): string => {
  if (value === undefined || value === null) return '--';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

const formatPercent = (value: number | undefined | null): string => {
  if (value === undefined || value === null) return '--';
  return `${value.toFixed(2)}%`;
};

const formatNumber = (value: number | undefined | null): string => {
  if (value === undefined || value === null) return '--';
  return new Intl.NumberFormat('en-US').format(value);
};

const formatDate = (value: string | null | undefined): string => {
  if (!value) return '--';
  return new Date(value).toLocaleDateString();
};

// ---------------------------------------------------------------------------
// Line Item Component
// ---------------------------------------------------------------------------

interface LineItemProps {
  label: string;
  value: string;
  icon?: React.ReactNode;
  isHeader?: boolean;
  isNegative?: boolean;
  indent?: boolean;
  warning?: boolean;
}

const LineItem: React.FC<LineItemProps> = ({ 
  label, value, icon, isHeader = false, isNegative = false, indent = false, warning = false
}) => (
  <div className={`flex items-center justify-between py-1 ${indent ? 'pl-4' : ''} ${isHeader ? 'border-b border-slate-200 dark:border-slate-700 pb-2 mb-2' : ''}`}>
    <div className="flex items-center gap-2 text-sm">
      {icon && <span className={`${warning ? 'text-amber-500' : 'text-slate-400'}`}>{icon}</span>}
      <span className={`${isHeader ? 'font-semibold text-slate-700 dark:text-slate-200' : 'text-slate-600 dark:text-slate-400'}`}>
        {label}
      </span>
    </div>
    <span className={`text-sm font-mono ${
      isHeader ? 'font-bold text-slate-800 dark:text-slate-100' :
      isNegative ? 'text-red-600' :
      warning ? 'text-amber-600' :
      'text-slate-700 dark:text-slate-300'
    }`}>
      {isNegative && value !== '--' ? `(${value})` : value}
    </span>
  </div>
);

// ---------------------------------------------------------------------------
// Section Component
// ---------------------------------------------------------------------------

interface SectionProps {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

const Section: React.FC<SectionProps> = ({ title, icon, children, defaultOpen = true }) => {
  const [open, setOpen] = useState(defaultOpen);
  
  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-lg mb-3">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 bg-slate-50 dark:bg-slate-800 rounded-t-lg text-left"
      >
        <div className="flex items-center gap-2">
          {icon && <span className="text-slate-500">{icon}</span>}
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{title}</span>
        </div>
        {open ? <FaChevronUp size={10} /> : <FaChevronDown size={10} />}
      </button>
      {open && <div className="px-3 py-2">{children}</div>}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Tab Content Components
// ---------------------------------------------------------------------------

const CommonTab: React.FC<{ data?: OrgFinancialCommon; currency: string }> = ({ data, currency: _currency }) => {
  if (!data) return <div className="text-slate-400 text-sm">No common data</div>;
  
  return (
    <div className="space-y-2">
      <Section title="Account Status" icon={<FaIdBadge size={12} />}>
        <LineItem label="Currency" value={data.currency || 'USD'} />
        <LineItem label="Account Opened" value={formatDate(data.account?.dt_opened)} />
        <LineItem label="Last Activity" value={formatDate(data.account?.dt_last_activity)} />
        {data.account?.hold && <LineItem label="Credit Hold" value="YES" warning icon={<FaExclamationTriangle size={12} />} />}
        {data.account?.cod_only && <LineItem label="COD Only" value="YES" warning />}
        {data.account?.inactive && <LineItem label="Status" value="INACTIVE" isNegative />}
      </Section>
      
      <Section title="Rating" icon={<FaChartLine size={12} />}>
        <LineItem label="Internal Rating" value={String(data.rating?.internal ?? '--')} />
        <LineItem label="Credit Score" value={String(data.rating?.credit_score ?? '--')} />
        {data.rating?.comments && (
          <div className="text-xs text-slate-500 mt-1 italic">"{data.rating.comments}"</div>
        )}
      </Section>
      
      <Section title="Settings" icon={<FaCreditCard size={12} />}>
        <LineItem label="Discount %" value={formatPercent(data.settings?.discount_pct)} />
        <LineItem label="Tax Exempt" value={data.settings?.tax_exempt ? 'Yes' : 'No'} />
        {data.settings?.tax_exempt_id && <LineItem label="Tax Exempt ID" value={data.settings.tax_exempt_id} indent />}
      </Section>
    </div>
  );
};

const CustomerTab: React.FC<{ data?: OrgFinancialCustomer; currency: string }> = ({ data, currency }) => {
  if (!data) return <div className="text-slate-400 text-sm">No customer data</div>;
  
  const hasAging = data.aging && (data.aging.period_1 || data.aging.period_2 || data.aging.period_3);
  
  return (
    <div className="space-y-2">
      <Section title="Credit & Balances" icon={<FaCreditCard size={12} />}>
        <LineItem label="Credit Limit" value={formatCurrency(data.credit?.limit, currency)} />
        <LineItem label="High Balance" value={formatCurrency(data.credit?.high, currency)} />
        <LineItem label="Available" value={formatCurrency(data.credit?.available, currency)} />
        <div className="border-t border-slate-100 dark:border-slate-700 my-2" />
        <LineItem label="Balance Due" value={formatCurrency(data.balances?.due, currency)} isHeader />
        <LineItem label="Current" value={formatCurrency(data.balances?.current, currency)} indent />
        <LineItem label="Open Orders" value={formatCurrency(data.balances?.open_orders, currency)} indent />
        <LineItem label="Total Exposure" value={formatCurrency(data.balances?.total_exposure, currency)} />
      </Section>

      {hasAging && (
        <Section title="Aging" icon={<FaClock size={12} />}>
          <LineItem label="Future" value={formatCurrency(data.aging?.future, currency)} />
          <LineItem label="1-30 Days" value={formatCurrency(data.aging?.period_1, currency)} />
          <LineItem label="31-60 Days" value={formatCurrency(data.aging?.period_2, currency)} warning={!!data.aging?.period_2} />
          <LineItem label="61-90+ Days" value={formatCurrency(data.aging?.period_3, currency)} warning={!!data.aging?.period_3} />
        </Section>
      )}

      <Section title="Sales Activity" icon={<FaChartLine size={12} />}>
        <LineItem label="Sales MTD" value={formatCurrency(data.sales?.mtd, currency)} />
        <LineItem label="Sales YTD" value={formatCurrency(data.sales?.ytd, currency)} />
        <LineItem label="Lifetime Sales" value={formatCurrency(data.sales?.lifetime, currency)} isHeader />
        <LineItem label="Last Sale" value={formatDate(data.sales?.dt_last_sale)} />
        <LineItem label="Last Amount" value={formatCurrency(data.sales?.last_sale_amount, currency)} />
      </Section>

      <Section title="Margin" icon={<FaPercent size={12} />} defaultOpen={false}>
        <LineItem label="Margin MTD" value={formatCurrency(data.margin?.mtd, currency)} />
        <LineItem label="Margin YTD" value={formatCurrency(data.margin?.ytd, currency)} />
        <LineItem label="Margin %" value={formatPercent(data.margin?.pct)} />
      </Section>

      <Section title="Payment History" icon={<FaMoneyCheckAlt size={12} />} defaultOpen={false}>
        <LineItem label="Avg Days to Pay" value={`${data.payment?.days_avg_paid ?? '--'} days`} />
        <LineItem label="Terms (Days)" value={`${data.payment?.days_pay ?? '--'} days`} />
        <LineItem label="Last Payment" value={formatDate(data.payment?.dt_last_payment)} />
        <LineItem label="Last Amount" value={formatCurrency(data.payment?.last_payment_amount, currency)} />
      </Section>

      {(data.collection?.cost_alltime ?? 0) > 0 && (
        <Section title="Collection Costs" icon={<FaExclamationTriangle size={12} />} defaultOpen={false}>
          <LineItem label="Cost MTD" value={formatCurrency(data.collection?.cost_mtd, currency)} isNegative />
          <LineItem label="Cost YTD" value={formatCurrency(data.collection?.cost_ytd, currency)} isNegative />
          <LineItem label="Cost All-Time" value={formatCurrency(data.collection?.cost_alltime, currency)} isNegative />
        </Section>
      )}

      {data.small_stings && (
        <Section title="Small Stings" icon={<FaBalanceScale size={12} />} defaultOpen={false}>
          <LineItem label="Received (Our Errors)" value={`${data.small_stings.received?.count ?? 0} / ${formatCurrency(data.small_stings.received?.value, currency)}`} isNegative />
          <LineItem label="Issued (Their Errors)" value={`${data.small_stings.issued?.count ?? 0} / ${formatCurrency(data.small_stings.issued?.value, currency)}`} />
        </Section>
      )}
    </div>
  );
};

const VendorTab: React.FC<{ data?: OrgFinancialVendor; currency: string }> = ({ data, currency }) => {
  if (!data) return <div className="text-slate-400 text-sm">No vendor data</div>;
  
  return (
    <div className="space-y-2">
      <Section title="Payables" icon={<FaFileInvoice size={12} />}>
        <LineItem label="Balance Due" value={formatCurrency(data.balances?.due, currency)} isHeader />
        <LineItem label="Current" value={formatCurrency(data.balances?.current, currency)} indent />
        <LineItem label="Open POs" value={formatCurrency(data.balances?.open_pos, currency)} indent />
      </Section>

      <Section title="Aging" icon={<FaClock size={12} />}>
        <LineItem label="Future" value={formatCurrency(data.aging?.future, currency)} />
        <LineItem label="1-30 Days" value={formatCurrency(data.aging?.period_1, currency)} />
        <LineItem label="31-60 Days" value={formatCurrency(data.aging?.period_2, currency)} />
        <LineItem label="61-90+ Days" value={formatCurrency(data.aging?.period_3, currency)} />
      </Section>

      <Section title="Purchases" icon={<FaChartLine size={12} />}>
        <LineItem label="Purchases MTD" value={formatCurrency(data.purchases?.mtd, currency)} />
        <LineItem label="Purchases YTD" value={formatCurrency(data.purchases?.ytd, currency)} />
        <LineItem label="Lifetime Purchases" value={formatCurrency(data.purchases?.lifetime, currency)} isHeader />
      </Section>

      <Section title="Payments Made" icon={<FaMoneyCheckAlt size={12} />} defaultOpen={false}>
        <LineItem label="Paid MTD" value={formatCurrency(data.payments_made?.mtd, currency)} />
        <LineItem label="Paid YTD" value={formatCurrency(data.payments_made?.ytd, currency)} />
        <LineItem label="Last Payment" value={formatDate(data.payments_made?.dt_last_payment)} />
      </Section>

      {data.small_stings && (
        <Section title="Small Stings" icon={<FaBalanceScale size={12} />} defaultOpen={false}>
          <LineItem label="Received (Our Errors)" value={`${data.small_stings.received?.count ?? 0} / ${formatCurrency(data.small_stings.received?.value, currency)}`} isNegative />
          <LineItem label="Issued (Their Errors)" value={`${data.small_stings.issued?.count ?? 0} / ${formatCurrency(data.small_stings.issued?.value, currency)}`} />
        </Section>
      )}
    </div>
  );
};

const RepTab: React.FC<{ data?: OrgFinancialRep; currency: string }> = ({ data, currency }) => {
  if (!data) return <div className="text-slate-400 text-sm">No rep data</div>;
  
  return (
    <div className="space-y-2">
      <Section title="Commissions" icon={<FaHandHoldingUsd size={12} />}>
        <LineItem label="Commission MTD" value={formatCurrency(data.commissions?.mtd, currency)} />
        <LineItem label="Commission YTD" value={formatCurrency(data.commissions?.ytd, currency)} />
        <LineItem label="Lifetime" value={formatCurrency(data.commissions?.lifetime, currency)} isHeader />
        <LineItem label="Pending" value={formatCurrency(data.commissions?.pending, currency)} />
        <LineItem label="Paid" value={formatCurrency(data.commissions?.paid, currency)} />
        <LineItem label="Rate" value={formatPercent(data.commissions?.rate_pct)} />
      </Section>

      <Section title="Sales Credited" icon={<FaChartLine size={12} />}>
        <LineItem label="Sales MTD" value={formatCurrency(data.sales_credited?.mtd, currency)} />
        <LineItem label="Sales YTD" value={formatCurrency(data.sales_credited?.ytd, currency)} />
        <LineItem label="Lifetime" value={formatCurrency(data.sales_credited?.lifetime, currency)} isHeader />
        <LineItem label="Customer Count" value={formatNumber(data.customers_count)} />
      </Section>
    </div>
  );
};

const EmployeeTab: React.FC<{ data?: OrgFinancialEmployee; currency: string }> = ({ data, currency }) => {
  if (!data) return <div className="text-slate-400 text-sm">No employee data</div>;
  
  return (
    <div className="space-y-2">
      <Section title="Payroll" icon={<FaDollarSign size={12} />}>
        <LineItem label="Salary" value={formatCurrency(data.payroll?.salary, currency)} />
        <LineItem label="Hourly Rate" value={formatCurrency(data.payroll?.rate_hourly, currency)} />
        <LineItem label="Type" value={data.payroll?.rate_type || '--'} />
      </Section>

      <Section title="Expenses" icon={<FaFileInvoice size={12} />}>
        <LineItem label="Expenses MTD" value={formatCurrency(data.expenses?.mtd, currency)} />
        <LineItem label="Expenses YTD" value={formatCurrency(data.expenses?.ytd, currency)} />
        <LineItem label="Pending" value={formatCurrency(data.expenses?.pending, currency)} />
      </Section>

      <Section title="Commissions" icon={<FaHandHoldingUsd size={12} />} defaultOpen={false}>
        <LineItem label="Commission MTD" value={formatCurrency(data.commissions?.mtd, currency)} />
        <LineItem label="Commission YTD" value={formatCurrency(data.commissions?.ytd, currency)} />
      </Section>

      <Section title="Time" icon={<FaClock size={12} />} defaultOpen={false}>
        <LineItem label="Hours MTD" value={formatNumber(data.time?.hours_mtd)} />
        <LineItem label="Hours YTD" value={formatNumber(data.time?.hours_ytd)} />
      </Section>
    </div>
  );
};

const ManufacturerTab: React.FC<{ data?: OrgFinancialManufacturer; currency: string }> = ({ data, currency }) => {
  if (!data) return <div className="text-slate-400 text-sm">No manufacturer data</div>;
  
  return (
    <div className="space-y-2">
      <Section title="Purchases" icon={<FaChartLine size={12} />}>
        <LineItem label="Purchases MTD" value={formatCurrency(data.purchases?.mtd, currency)} />
        <LineItem label="Purchases YTD" value={formatCurrency(data.purchases?.ytd, currency)} />
        <LineItem label="Lifetime" value={formatCurrency(data.purchases?.lifetime, currency)} isHeader />
      </Section>

      <Section title="Rebates" icon={<FaHandHoldingUsd size={12} />}>
        <LineItem label="Earned YTD" value={formatCurrency(data.rebates?.earned_ytd, currency)} />
        <LineItem label="Received YTD" value={formatCurrency(data.rebates?.received_ytd, currency)} />
        <LineItem label="Pending" value={formatCurrency(data.rebates?.pending, currency)} />
      </Section>

      <Section title="Terms" icon={<FaIndustry size={12} />}>
        <LineItem label="Pricing Tier" value={data.pricing_tier || '--'} />
        <LineItem label="Lead Time" value={`${data.lead_time_days ?? '--'} days`} />
        <LineItem label="Freight Terms" value={data.freight_terms || '--'} />
        <LineItem label="Min Order" value={formatCurrency(data.min_order, currency)} />
      </Section>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Category Configuration
// ---------------------------------------------------------------------------

const CATEGORY_CONFIG: Record<FinancialTabKey, { label: string; icon: React.ReactNode; orgTypes: OrgType[] }> = {
  common: { label: 'Common', icon: <FaIdBadge size={12} />, orgTypes: [] }, // Always shown
  customer: { label: 'Customer', icon: <FaUser size={12} />, orgTypes: ['customer'] },
  vendor: { label: 'Vendor', icon: <FaBuilding size={12} />, orgTypes: ['vendor'] },
  rep: { label: 'Rep', icon: <FaUserTie size={12} />, orgTypes: ['rep'] },
  employee: { label: 'Employee', icon: <FaIdBadge size={12} />, orgTypes: ['employee'] },
  manufacturer: { label: 'Manufacturer', icon: <FaIndustry size={12} />, orgTypes: ['manufacturer'] },
};

// ---------------------------------------------------------------------------
// Category Card Wrapper
// ---------------------------------------------------------------------------

interface CategoryCardProps {
  label: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

const CategoryCard: React.FC<CategoryCardProps> = ({ label, icon, children, defaultOpen = true }) => {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-lg">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-slate-50 dark:bg-slate-800 rounded-t-lg text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-green-500">{icon}</span>
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">{label}</span>
        </div>
        {open ? <FaChevronUp size={10} className="text-slate-400" /> : <FaChevronDown size={10} className="text-slate-400" />}
      </button>
      {open && <div className="p-3">{children}</div>}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

const OrgFinancialsPanel: React.FC<OrgFinancialsPanelProps> = ({
  financial,
  orgType,
  orgTypes = [],
  editing: _editing = false,
  onChange: _onChange,
  title = 'Financials',
  defaultCollapsed = false,
  compact = false,
  currency = 'USD',
  className = '',
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  
  // Determine which categories to show based on org type(s)
  const allOrgTypes = orgType ? [orgType, ...orgTypes] : orgTypes;
  const displayCurrency = financial?.common?.currency || currency;
  
  // Build list of visible categories
  const visibleCategories: FinancialTabKey[] = ['common'];
  (Object.keys(CATEGORY_CONFIG) as FinancialTabKey[]).forEach((catKey) => {
    if (catKey === 'common') return;
    const catOrgTypes = CATEGORY_CONFIG[catKey].orgTypes;
    // Show category if org has that type OR if financial data exists for it
    if (
      catOrgTypes.some(t => allOrgTypes.includes(t)) ||
      (financial && financial[catKey as keyof OrgFinancial] && Object.keys(financial[catKey as keyof OrgFinancial] as object).length > 0)
    ) {
      visibleCategories.push(catKey);
    }
  });

  const renderCategory = (catKey: FinancialTabKey) => {
    const config = CATEGORY_CONFIG[catKey];
    let content: React.ReactNode = null;

    switch (catKey) {
      case 'common':
        content = <CommonTab data={financial?.common} currency={displayCurrency} />;
        break;
      case 'customer':
        content = <CustomerTab data={financial?.customer} currency={displayCurrency} />;
        break;
      case 'vendor':
        content = <VendorTab data={financial?.vendor} currency={displayCurrency} />;
        break;
      case 'rep':
        content = <RepTab data={financial?.rep} currency={displayCurrency} />;
        break;
      case 'employee':
        content = <EmployeeTab data={financial?.employee} currency={displayCurrency} />;
        break;
      case 'manufacturer':
        content = <ManufacturerTab data={financial?.manufacturer} currency={displayCurrency} />;
        break;
    }

    return (
      <CategoryCard
        key={catKey}
        label={config.label}
        icon={config.icon}
        defaultOpen={catKey !== 'common'}
      >
        {content}
      </CategoryCard>
    );
  };

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-lg border border-green-200 dark:border-green-800 ${className}`}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-green-50 dark:bg-green-900/20 border-b border-green-200 dark:border-green-800 cursor-pointer rounded-t-lg"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaDollarSign className="text-green-500" size={14} />
          <h3 className="text-sm font-semibold text-green-700 dark:text-green-300">{title}</h3>
          {financial?.common?.account?.hold && (
            <span className="px-2 py-0.5 text-xs bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 rounded">
              HOLD
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
        </div>
      </div>

      {/* Content — all categories stacked */}
      {!isCollapsed && (
        <div className={`${compact ? 'p-2' : 'p-3'} space-y-3 max-h-[700px] overflow-y-auto`}>
          {visibleCategories.map((catKey) => renderCategory(catKey))}
        </div>
      )}
    </div>
  );
};

export default withDevIdentifier(OrgFinancialsPanel, 'OrgFinancialsPanel', 'teal');
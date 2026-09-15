/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import React from "react";
import { FaChartLine, FaClock, FaShoppingCart, FaDollarSign } from "react-icons/fa";
import { withDevIdentifier } from "@/components/common/DevIdentifier";
import { formatCurrency } from "@/utils/stringUtils";

interface OrgMetricsPanelProps {
  orgType?: "customer" | "vendor";
  financial?: any;
  className?: string;
}


const formatDays = (value?: number | null): string => {
  if (value === undefined || value === null) return "--";
  return `${value}`;
};

const MetricRow: React.FC<{ label: string; value: string; icon?: React.ReactNode }> = ({
  label,
  value,
  icon,
}) => (
  <div className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-slate-700/70 last:border-b-0">
    <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
      {icon ? <span className="text-slate-400">{icon}</span> : null}
      <span>{label}</span>
    </div>
    <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">{value}</div>
  </div>
);

const OrgMetricsPanel: React.FC<OrgMetricsPanelProps> = ({
  orgType = "customer",
  financial,
  className = "",
}) => {
  const customer = financial?.customer ?? {};
  const vendor = financial?.vendor ?? {};

  const isVendor = orgType === "vendor";

  const orderCountPeriod = isVendor
    ? vendor?.counts?.orders_period ?? vendor?.counts?.purchases_period
    : customer?.counts?.orders_period;

  const salesPeriod = isVendor
    ? vendor?.purchases?.mtd ?? vendor?.sales?.mtd
    : customer?.sales?.mtd;

  const salesYtd = isVendor
    ? vendor?.purchases?.ytd ?? vendor?.sales?.ytd
    : customer?.sales?.ytd;

  const salesAllTime = isVendor
    ? vendor?.purchases?.lifetime ?? vendor?.sales?.lifetime
    : customer?.sales?.lifetime;

  const daysPaid = isVendor
    ? vendor?.payment?.days_avg_paid ?? vendor?.payments_made?.days_avg_paid
    : customer?.payment?.days_avg_paid;

  const balanceDue = isVendor
    ? vendor?.balances?.due
    : customer?.balances?.due;

  const openOrders = isVendor
    ? vendor?.balances?.open_pos
    : customer?.balances?.open_orders;

  return (
    <div
      className={`bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 ${className}`}
    >
      <div className="flex items-center gap-2 mb-3">
        <FaChartLine className="text-indigo-500" size={14} />
        <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
          Metrics Snapshot
        </h3>
      </div>

      <div className="space-y-0">
        <MetricRow
          label={isVendor ? "Purchases in Period" : "Orders in Period"}
          value={orderCountPeriod != null ? String(orderCountPeriod) : "--"}
          icon={<FaShoppingCart size={11} />}
        />
        <MetricRow
          label={isVendor ? "Purchases MTD" : "Sales MTD"}
          value={formatCurrency(salesPeriod)}
          icon={<FaDollarSign size={11} />}
        />
        <MetricRow
          label={isVendor ? "Purchases YTD" : "Sales YTD"}
          value={formatCurrency(salesYtd)}
          icon={<FaDollarSign size={11} />}
        />
        <MetricRow
          label={isVendor ? "Purchases All-Time" : "Sales All-Time"}
          value={formatCurrency(salesAllTime)}
          icon={<FaDollarSign size={11} />}
        />
        <MetricRow
          label="Days Paid"
          value={formatDays(daysPaid)}
          icon={<FaClock size={11} />}
        />
        <MetricRow
          label="Balance Due"
          value={formatCurrency(balanceDue)}
          icon={<FaDollarSign size={11} />}
        />
        <MetricRow
          label={isVendor ? "Open POs" : "Open Orders"}
          value={formatCurrency(openOrders)}
          icon={<FaShoppingCart size={11} />}
        />
      </div>
    </div>
  );
};

export default withDevIdentifier(OrgMetricsPanel, "OrgMetricsPanel", "indigo", 'apps/orgs/components/OrgMetricsPanel.tsx');

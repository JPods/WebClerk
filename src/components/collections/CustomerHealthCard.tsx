/**
 * CustomerHealthCard — compact aging, credit, and payment velocity panel.
 *
 * Shows at-a-glance financial health for a single customer:
 *   - Aging buckets (colored bars)
 *   - Credit limit / balance / available
 *   - Payment velocity + trend
 *   - Last payment
 *   - Open invoices
 *
 * Data source: POST /wcapi/manage/ { action: "get_customer_health", params: { customer_id } }
 *
 * LastChecked: 2026-08-10 | WhereUsed: OrgPage (customer detail) | WhoCreated: Bill+Claude
 */
import React, { useEffect, useState } from 'react';
import apiClient from '@/api/axios';
import { formatDt } from '@/utils/fieldFormatters';

interface HealthData {
  aging: { current: number; past_1_30: number; past_31_60: number; past_61: number; balance_due: number };
  credit_limit: number;
  available_credit: number;
  payment_velocity: number;       // avg days to pay
  velocity_trend: 'improving' | 'stable' | 'deteriorating';
  last_payment: { date: string; amount: number } | null;
  open_invoices: { count: number; total: number };
  health_score: 'green' | 'yellow' | 'red';
}

const fmt = (n: number) => n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const HEALTH_COLORS = {
  green: { bg: 'bg-green-50 border-green-200', dot: 'bg-green-500', label: 'Good Standing' },
  yellow: { bg: 'bg-amber-50 border-amber-200', dot: 'bg-amber-500', label: 'Watch' },
  red: { bg: 'bg-red-50 border-red-200', dot: 'bg-red-500', label: 'At Risk' },
};

const TREND_ICONS: Record<string, string> = {
  improving: '↗',
  stable: '→',
  deteriorating: '↘',
};

const TREND_COLORS: Record<string, string> = {
  improving: 'text-green-600',
  stable: 'text-gray-500',
  deteriorating: 'text-red-600',
};

interface Props {
  customerId: number;
}

const CustomerHealthCard: React.FC<Props> = ({ customerId }) => {
  const [data, setData] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!customerId) return;
    setLoading(true);
    apiClient.post('/wcapi/manage/', {
      action: 'get_customer_health',
      params: { customer_id: customerId },
    }).then(res => {
      setData(res.data?.data ?? res.data);
    }).catch(() => {})
    .finally(() => setLoading(false));
  }, [customerId]);

  if (loading) return <div className="text-xs text-gray-400 p-2">Loading health...</div>;
  if (!data) return null;

  const h = HEALTH_COLORS[data.health_score] || HEALTH_COLORS.green;
  const total = data.aging.balance_due || 1;
  const pctCurrent = (data.aging.current / total) * 100;
  const pct30 = (data.aging.past_1_30 / total) * 100;
  const pct60 = (data.aging.past_31_60 / total) * 100;
  const pct90 = (data.aging.past_61 / total) * 100;

  return (
    <div className={`rounded-lg border p-3 ${h.bg}`} data-wc="customer-health-card">
      {/* Health score badge */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">Account Health</span>
        <span className="flex items-center gap-1.5 text-xs font-bold">
          <span className={`w-2 h-2 rounded-full ${h.dot}`} />
          {h.label}
        </span>
      </div>

      {/* Aging bar */}
      <div className="mb-3">
        <div className="flex h-3 rounded-full overflow-hidden bg-gray-200">
          {pctCurrent > 0 && <div className="bg-green-500" style={{ width: `${pctCurrent}%` }} title={`Current: $${fmt(data.aging.current)}`} />}
          {pct30 > 0 && <div className="bg-amber-400" style={{ width: `${pct30}%` }} title={`1-30: $${fmt(data.aging.past_1_30)}`} />}
          {pct60 > 0 && <div className="bg-orange-500" style={{ width: `${pct60}%` }} title={`31-60: $${fmt(data.aging.past_31_60)}`} />}
          {pct90 > 0 && <div className="bg-red-600" style={{ width: `${pct90}%` }} title={`61+: $${fmt(data.aging.past_61)}`} />}
        </div>
        <div className="flex justify-between text-[10px] text-gray-500 mt-0.5">
          <span>Current ${fmt(data.aging.current)}</span>
          <span>1-30 ${fmt(data.aging.past_1_30)}</span>
          <span>31-60 ${fmt(data.aging.past_31_60)}</span>
          <span>61+ ${fmt(data.aging.past_61)}</span>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <div className="flex justify-between">
          <span className="text-gray-500">Balance Due</span>
          <span className="font-mono font-medium">${fmt(data.aging.balance_due)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Credit Limit</span>
          <span className="font-mono font-medium">${fmt(data.credit_limit)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Available</span>
          <span className={`font-mono font-medium ${data.available_credit < 0 ? 'text-red-600' : ''}`}>
            ${fmt(data.available_credit)}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Open Invoices</span>
          <span className="font-mono font-medium">{data.open_invoices.count} (${fmt(data.open_invoices.total)})</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Avg Days to Pay</span>
          <span className="font-mono font-medium">
            {Math.round(data.payment_velocity)}d
            <span className={`ml-1 ${TREND_COLORS[data.velocity_trend]}`}>
              {TREND_ICONS[data.velocity_trend]}
            </span>
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Last Payment</span>
          <span className="font-mono text-gray-700">
            {data.last_payment
              ? <>{formatDt(data.last_payment.date, 'date')} ${fmt(data.last_payment.amount)}</>
              : <span className="text-red-400">None</span>
            }
          </span>
        </div>
      </div>
    </div>
  );
};

export default CustomerHealthCard;

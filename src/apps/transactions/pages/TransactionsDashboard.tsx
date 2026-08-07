/**
 * Transactions Dashboard — sales, purchasing, invoicing, payments.
 *
 * Comparison table: rows = models, columns = period pairs (this/last).
 * All periods visible at once — no buttons to click.
 * + button on each row for quick record creation.
 * Money panel: AR aging, journal, inventory.
 * Tools panel: Apply Payments, Inventory Adjust, Commerce.
 */
import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '@/api/axios';
import { useDashboardCounts, buildPeriods } from '@/hooks/useDashboardCounts';
import { useWindowManager } from '@/context/WindowManagerContext';

// ─── Config ─────────────────────────────────────────────────────────
const TX_MODELS = [
  { model: 'order', label: 'Orders' },
  { model: 'proposal', label: 'Proposals' },
  { model: 'invoice', label: 'Invoices' },
  { model: 'purchase', label: 'Purchases' },
  { model: 'payment', label: 'Payments' },
  { model: 'receipt', label: 'Receipts' },
  { model: 'workorder', label: 'Work Orders' },
  { model: 'requisition', label: 'Requisitions' },
];

const fmtInt = (n: number) => n.toLocaleString('en-US');
const fmt = (n: number) => n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

// Trend arrow: compare current to prior
function Trend({ current, prior }: { current: number; prior: number }) {
  if (current === prior) return <span className="text-slate-300 text-xs">—</span>;
  if (current > prior) return <span className="text-green-600 text-xs">▲</span>;
  return <span className="text-red-500 text-xs">▼</span>;
}

const Panel: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div className="border border-slate-200 rounded-lg p-4 mb-4">
    <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wide mb-3">{title}</h2>
    {children}
  </div>
);

const Stat: React.FC<{ label: string; value: string | number; alert?: boolean }> = ({ label, value, alert }) => (
  <div className="flex justify-between py-0.5 text-sm">
    <span className="text-slate-500">{label}</span>
    <span className={`font-mono font-medium ${alert ? 'text-red-600' : 'text-slate-900'}`}>{value}</span>
  </div>
);

// ─── Main component ─────────────────────────────────────────────────
export default function TransactionsDashboard() {
  const navigate = useNavigate();
  const { ensureWindow, activateWindow } = useWindowManager();
  const modelNames = useMemo(() => TX_MODELS.map(m => m.model), []);
  const { counts, loading, periods } = useDashboardCounts(modelNames);
  const [acct, setAcct] = useState<any>(null);
  const [acctLoading, setAcctLoading] = useState(true);

  // Fetch accounting summary
  const fetchAcct = useCallback(async () => {
    setAcctLoading(true);
    try {
      const res = await apiClient.post('/wcapi/manage/', { action: 'get_accounting_dashboard', params: {} });
      setAcct(res.data?.data ?? res.data);
    } catch { /* ignore */ }
    setAcctLoading(false);
  }, []);

  useEffect(() => { fetchAcct(); }, [fetchAcct]);

  const openDb = (path: string, title: string) => {
    ensureWindow(path, title);
    activateWindow(path);
  };
  const goDb = (model: string) => openDb(`/${model}`, model);

  // Build DataBrowser URL filtered to a model + date range
  const periodMap = Object.fromEntries(periods.map(p => [p.key, p]));

  const dbUrl = (model: string, periodKey: string) => {
    const p = periodMap[periodKey];
    if (!p) return `/${model}`;
    return `/${model}?dt_created__gte=${p.from}&dt_created__lte=${p.to}`;
  };

  // Inline cell value — NOT a component (avoids remount dropping event handlers)
  const cell = (model: string, periodKey: string) => {
    const v = counts[model]?.[periodKey] ?? 0;
    if (loading) return <span className="font-mono text-sm tabular-nums">·</span>;
    return (
      <button
        onClick={() => openDb(dbUrl(model, periodKey), model)}
        className="font-mono text-sm tabular-nums hover:text-blue-600 hover:underline transition-colors cursor-pointer"
      >
        {fmtInt(v)}
      </button>
    );
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-xl font-bold text-gray-900 mb-1">Transactions</h1>
      <p className="text-xs text-slate-500 mb-5">
        Sales, purchasing, invoicing, and payments.
      </p>

      {/* ─── Comparison table ───────────────────────────────────────── */}
      <Panel title="Activity">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 pr-3 text-xs font-semibold text-slate-500 w-32"></th>
                <th colSpan={3} className="text-center px-1 py-2 text-xs font-semibold text-slate-500">Month</th>
                <th colSpan={3} className="text-center px-1 py-2 text-xs font-semibold text-slate-500 border-l border-slate-100">Month YoY</th>
                <th colSpan={3} className="text-center px-1 py-2 text-xs font-semibold text-slate-500 border-l border-slate-100">Quarter</th>
                <th colSpan={3} className="text-center px-1 py-2 text-xs font-semibold text-slate-500 border-l border-slate-100">Year</th>
              </tr>
              <tr className="border-b border-slate-100 text-[10px] text-slate-400">
                <th></th>
                <th className="text-right px-2 py-1">This</th>
                <th className="text-right px-2 py-1">Last</th>
                <th className="px-1 py-1"></th>
                <th className="text-right px-2 py-1 border-l border-slate-100">This</th>
                <th className="text-right px-2 py-1">LY</th>
                <th className="px-1 py-1"></th>
                <th className="text-right px-2 py-1 border-l border-slate-100">This</th>
                <th className="text-right px-2 py-1">Last</th>
                <th className="px-1 py-1"></th>
                <th className="text-right px-2 py-1 border-l border-slate-100">YTD</th>
                <th className="text-right px-2 py-1">Prior</th>
                <th className="px-1 py-1"></th>
              </tr>
            </thead>
            <tbody>
              {TX_MODELS.map(({ model, label }) => {
                const mc = counts[model] || {};
                return (
                  <tr
                    key={model}
                    className="border-b border-slate-50 hover:bg-slate-50 transition-colors"
                  >
                    <td className="py-2 pr-3">
                      <button onClick={() => goDb(model)} className="font-medium text-slate-700 hover:text-blue-600 hover:underline transition-colors">
                        {label}
                      </button>
                    </td>
                    {/* Month */}
                    <td className="text-right px-2 py-2">{cell(model,"this_mo")}</td>
                    <td className="text-right px-2 py-2 text-slate-400">{cell(model,"last_mo")}</td>
                    <td className="px-1 py-2">{!loading && <Trend current={mc.this_mo ?? 0} prior={mc.last_mo ?? 0} />}</td>
                    {/* Month YoY */}
                    <td className="text-right px-2 py-2 border-l border-slate-100">{cell(model,"this_mo")}</td>
                    <td className="text-right px-2 py-2 text-slate-400">{cell(model,"this_mo_ly")}</td>
                    <td className="px-1 py-2">{!loading && <Trend current={mc.this_mo ?? 0} prior={mc.this_mo_ly ?? 0} />}</td>
                    {/* Quarter */}
                    <td className="text-right px-2 py-2 border-l border-slate-100">{cell(model,"this_qtr")}</td>
                    <td className="text-right px-2 py-2 text-slate-400">{cell(model,"last_qtr")}</td>
                    <td className="px-1 py-2">{!loading && <Trend current={mc.this_qtr ?? 0} prior={mc.last_qtr ?? 0} />}</td>
                    {/* Year */}
                    <td className="text-right px-2 py-2 border-l border-slate-100">{cell(model,"ytd")}</td>
                    <td className="text-right px-2 py-2 text-slate-400">{cell(model,"last_ytd")}</td>
                    <td className="px-1 py-2">{!loading && <Trend current={mc.ytd ?? 0} prior={mc.last_ytd ?? 0} />}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* ─── Money panel ────────────────────────────────────────────── */}
      <Panel title="Money">
        {acctLoading ? (
          <div className="text-sm text-slate-400">Loading...</div>
        ) : acct ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <div className="text-xs font-semibold text-slate-500 mb-1">Accounts Receivable</div>
              <Stat label="Current" value={`$${fmt(acct.aging_summary?.current ?? 0)}`} />
              <Stat label="1-30 Days" value={`$${fmt(acct.aging_summary?.period_1_30 ?? 0)}`} alert={(acct.aging_summary?.period_1_30 ?? 0) > 0} />
              <Stat label="31-60 Days" value={`$${fmt(acct.aging_summary?.period_2_60 ?? 0)}`} alert={(acct.aging_summary?.period_2_60 ?? 0) > 0} />
              <Stat label="60+ Days" value={`$${fmt(acct.aging_summary?.period_3_90_plus ?? 0)}`} alert={(acct.aging_summary?.period_3_90_plus ?? 0) > 0} />
              <div className="border-t mt-1 pt-1">
                <Stat label="Total AR" value={`$${fmt(acct.aging_summary?.total_ar ?? 0)}`} />
              </div>
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-500 mb-1">Journal</div>
              <Stat label="GL Entries" value={fmtInt(acct.journal_status?.total_journal_entries ?? 0)} />
              <Stat label="Pending Invoices" value={fmtInt(acct.journal_status?.pending_invoices ?? 0)} alert={(acct.journal_status?.pending_invoices ?? 0) > 10} />
              <Stat label="Pending Payments" value={fmtInt(acct.journal_status?.pending_payments ?? 0)} alert={(acct.journal_status?.pending_payments ?? 0) > 10} />
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-500 mb-1">Inventory</div>
              <Stat label="Unprocessed" value={fmtInt(acct.pending_inventory?.unprocessed_count ?? 0)} alert={(acct.pending_inventory?.unprocessed_count ?? 0) > 0} />
              <Stat label="Oldest Age" value={`${acct.pending_inventory?.oldest_age_minutes ?? 0} min`} alert={(acct.pending_inventory?.oldest_age_minutes ?? 0) > 5} />
            </div>
          </div>
        ) : (
          <div className="text-sm text-slate-400">Unavailable</div>
        )}
      </Panel>

      {/* ─── Tools panel ────────────────────────────────────────────── */}
      <Panel title="Tools">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div onClick={() => navigate('/apply-payments')} className="border border-slate-200 rounded-lg px-4 py-3 cursor-pointer transition-colors hover:border-blue-400">
            <div className="text-sm font-semibold">Apply Payments</div>
            <div className="text-xs text-slate-500 mt-0.5">Match payments to invoices</div>
          </div>
          <div onClick={() => navigate('/inventory-adjust')} className="border border-slate-200 rounded-lg px-4 py-3 cursor-pointer transition-colors hover:border-blue-400">
            <div className="text-sm font-semibold">Inventory Adjust</div>
            <div className="text-xs text-slate-500 mt-0.5">Adjustments, cycle counts, transfers</div>
          </div>
          <div onClick={() => navigate('/commerce')} className="border border-slate-200 rounded-lg px-4 py-3 cursor-pointer transition-colors hover:border-blue-400">
            <div className="text-sm font-semibold">Commerce</div>
            <div className="text-xs text-slate-500 mt-0.5">Sales, purchasing, inventory, velocity</div>
          </div>
        </div>
      </Panel>
    </div>
  );
}

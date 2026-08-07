/**
 * Administration Dashboard — single-page view.
 *
 * Header: Open actions by priority.
 * Panel 1: Accounting — GL balance, journal status, aging, pending.
 * Panel 2: Activity — comparison table (rows = models, columns = period pairs).
 *          All periods visible at once — no buttons to click.
 * Panel 3: Sync — connections, bundles, conversion projects.
 */
import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWindowManager } from '@/context/WindowManagerContext';
import apiClient from '@/api/axios';
import { useDashboardCounts } from '@/hooks/useDashboardCounts';
import {
  FaCheckCircle, FaExclamationTriangle, FaLock, FaClock, FaSync,
} from 'react-icons/fa';

// ─── Types ──────────────────────────────────────────────────────────
type ActionSummary = {
  total: number;
  high: number;
  medium: number;
  low: number;
  none: number;
};

type AccountingData = {
  journal_status: {
    total_journal_entries: number;
    pending_invoices: number;
    pending_payments: number;
  };
  gl_balance: {
    total_debit: number;
    total_credit: number;
    imbalance: number;
    balanced: boolean;
  };
  aging_summary: {
    current: number;
    period_1_30: number;
    period_2_60: number;
    period_3_90_plus: number;
    total_ar: number;
  };
  pending_inventory: {
    unprocessed_count: number;
    oldest_age_minutes: number;
  };
};

// ─── Activity config ────────────────────────────────────────────────
const ACTIVITY_MODELS = [
  { model: 'order', label: 'Orders' },
  { model: 'invoice', label: 'Invoices' },
  { model: 'proposal', label: 'Proposals' },
  { model: 'purchase', label: 'Purchases' },
  { model: 'workorder', label: 'Work Orders' },
  { model: 'payment', label: 'Payments' },
  { model: 'support.Quality', label: 'Quality' },
  { model: 'docs.Document', label: 'Documents' },
  { model: 'setting', label: 'Settings' },
  { model: 'core.Report', label: 'Reports' },
];

const fmtInt = (n: number) => n.toLocaleString('en-US');
const fmt = (n: number) => n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

// Trend arrow: compare current to prior
function Trend({ current, prior }: { current: number; prior: number }) {
  if (current === prior) return <span className="text-slate-300 text-xs">&mdash;</span>;
  if (current > prior) return <span className="text-green-600 text-xs">&#9650;</span>;
  return <span className="text-red-500 text-xs">&#9660;</span>;
}

// ─── Panel wrapper ──────────────────────────────────────────────────
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
export default function OperationsDashboard() {
  const navigate = useNavigate();
  const { ensureWindow, activateWindow } = useWindowManager();
  const modelNames = useMemo(() => ACTIVITY_MODELS.map(m => m.model), []);
  const { counts, loading: activityLoading, periods } = useDashboardCounts(modelNames);
  const [actions, setActions] = useState<ActionSummary | null>(null);
  const [accounting, setAccounting] = useState<AccountingData | null>(null);
  const [acctLoading, setAcctLoading] = useState(true);
  const [acctError, setAcctError] = useState<string | null>(null);
  const [syncCounts, setSyncCounts] = useState<Record<string, number>>({});
  const [syncLoading, setSyncLoading] = useState(true);

  // Fetch open actions by priority
  useEffect(() => {
    apiClient.get('/wcapi/get/?model_name=action&limit=1&status=open')
      .then(r => {
        const total = r.data?.data?.total ?? 0;
        return apiClient.get('/wcapi/get/?model_name=action&status=open&limit=500&fields=priority')
          .then(detail => {
            const records = detail.data?.data?.results ?? [];
            let high = 0, medium = 0, low = 0, none = 0;
            records.forEach((r: any) => {
              const p = (r.priority || '').toLowerCase();
              if (p === 'high' || p === 'urgent') high++;
              else if (p === 'medium' || p === 'normal') medium++;
              else if (p === 'low') low++;
              else none++;
            });
            setActions({ total, high, medium, low, none });
          })
          .catch(() => setActions({ total, high: 0, medium: 0, low: 0, none: total }));
      })
      .catch(() => setActions({ total: 0, high: 0, medium: 0, low: 0, none: 0 }));
  }, []);

  // Fetch accounting data
  const fetchAccounting = useCallback(async () => {
    setAcctLoading(true);
    setAcctError(null);
    try {
      const res = await apiClient.post('/wcapi/manage/', { action: 'get_accounting_dashboard', params: {} });
      setAccounting(res.data?.data ?? res.data);
    } catch (err: any) {
      setAcctError(err?.message || 'Failed to load');
    } finally {
      setAcctLoading(false);
    }
  }, []);

  useEffect(() => { fetchAccounting(); }, [fetchAccounting]);

  // Fetch sync counts
  useEffect(() => {
    Promise.all(
      ['sync.Connection', 'sync.Bundle', 'conversion.ConversionProject'].map(m =>
        apiClient.get(`/wcapi/get/?model_name=${m}&limit=1`)
          .then(r => [m, r.data?.data?.total ?? r.data?.data?.count ?? 0] as [string, number])
          .catch(() => [m, 0] as [string, number])
      )
    ).then(pairs => {
      setSyncCounts(Object.fromEntries(pairs));
      setSyncLoading(false);
    });
  }, []);

  const openDb = (path: string, title: string) => {
    ensureWindow(path, title);
    activateWindow(path);
  };
  const goDb = (model: string) => openDb('/' + model, model);

  // Build DataBrowser URL filtered to a model + date range
  const periodMap = Object.fromEntries(periods.map(p => [p.key, p]));

  const dbUrl = (model: string, periodKey: string) => {
    const p = periodMap[periodKey];
    if (!p) return `/${model}`;
    return `/${model}?dt_created__gte=${p.from}&dt_created__lte=${p.to}`;
  };

  // Cell renderer — plain function call (not a component) to avoid React remount on every render
  const cell = (model: string, periodKey: string) => {
    const v = counts[model]?.[periodKey] ?? 0;
    if (activityLoading) return <span className="font-mono text-sm tabular-nums">&middot;</span>;
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
      <h1 className="text-xl font-bold text-gray-900 mb-1">Administration</h1>
      <p className="text-xs text-slate-500 mb-5">
        Accounting, activity, and integration.
      </p>

      {/* ─── Actions header ─────────────────────────────────────────── */}
      <div
        className="flex items-center gap-4 mb-5 bg-slate-50 border border-slate-200 rounded-lg px-5 py-3 cursor-pointer hover:bg-slate-100 transition-colors"
        onClick={() => goDb('action')}
      >
        <div className="text-base font-semibold">Actions</div>
        <div className="flex items-center gap-3 text-sm">
          <span className="font-bold text-slate-900">{actions?.total ?? '...'} open</span>
          {actions && actions.high > 0 && (
            <span className="text-red-600 font-medium">{actions.high} high</span>
          )}
          {actions && actions.medium > 0 && (
            <span className="text-amber-600 font-medium">{actions.medium} medium</span>
          )}
          {actions && actions.low > 0 && (
            <span className="text-slate-500">{actions.low} low</span>
          )}
        </div>
        <span className="ml-auto text-xs text-slate-400">Open in DataBrowser &rarr;</span>
      </div>

      {/* ─── Accounting panel ───────────────────────────────────────── */}
      <Panel title="Accounting">
        {acctLoading ? (
          <div className="text-sm text-slate-400">Loading...</div>
        ) : acctError ? (
          <div className="text-sm text-red-500">{acctError}</div>
        ) : accounting ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 mb-1">
                {accounting.gl_balance.balanced
                  ? <FaCheckCircle className="text-green-500" size={11} />
                  : <FaExclamationTriangle className="text-red-500" size={11} />}
                GL Balance
              </div>
              <Stat label="Debits" value={`$${fmt(accounting.gl_balance.total_debit)}`} />
              <Stat label="Credits" value={`$${fmt(accounting.gl_balance.total_credit)}`} />
              <Stat label="Imbalance" value={`$${fmt(accounting.gl_balance.imbalance)}`} alert={!accounting.gl_balance.balanced} />
            </div>
            <div>
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 mb-1">
                <FaClock className="text-slate-400" size={11} /> AR Aging
              </div>
              <Stat label="Current" value={`$${fmt(accounting.aging_summary.current)}`} />
              <Stat label="1-30 Days" value={`$${fmt(accounting.aging_summary.period_1_30)}`} alert={accounting.aging_summary.period_1_30 > 0} />
              <Stat label="31-60 Days" value={`$${fmt(accounting.aging_summary.period_2_60)}`} alert={accounting.aging_summary.period_2_60 > 0} />
              <Stat label="60+ Days" value={`$${fmt(accounting.aging_summary.period_3_90_plus)}`} alert={accounting.aging_summary.period_3_90_plus > 0} />
            </div>
            <div>
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 mb-1">
                <FaLock className="text-slate-400" size={11} /> Journal
              </div>
              <Stat label="GL Entries" value={fmtInt(accounting.journal_status.total_journal_entries)} />
              <Stat label="Pending Invoices" value={fmtInt(accounting.journal_status.pending_invoices)} alert={accounting.journal_status.pending_invoices > 10} />
              <Stat label="Pending Payments" value={fmtInt(accounting.journal_status.pending_payments)} alert={accounting.journal_status.pending_payments > 10} />
            </div>
            <div>
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 mb-1">
                {accounting.pending_inventory.unprocessed_count > 0
                  ? <FaClock className="text-amber-500" size={11} />
                  : <FaCheckCircle className="text-green-500" size={11} />}
                Pending Inventory
              </div>
              <Stat label="Unprocessed" value={fmtInt(accounting.pending_inventory.unprocessed_count)} alert={accounting.pending_inventory.unprocessed_count > 0} />
              <Stat label="Oldest Age" value={`${accounting.pending_inventory.oldest_age_minutes} min`} alert={accounting.pending_inventory.oldest_age_minutes > 5} />
            </div>
          </div>
        ) : null}
        {!acctLoading && accounting && (
          <div className="mt-2 text-right">
            <button onClick={fetchAccounting} className="text-xs text-blue-600 hover:text-blue-800">
              <FaSync size={10} className="inline mr-1" /> Refresh
            </button>
          </div>
        )}
      </Panel>

      {/* ─── Activity panel — comparison table ─────────────────────── */}
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
              {ACTIVITY_MODELS.map(({ model, label }) => {
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
                    <td className="text-right px-2 py-2">{cell(model, "this_mo")}</td>
                    <td className="text-right px-2 py-2 text-slate-400">{cell(model, "last_mo")}</td>
                    <td className="px-1 py-2">{!activityLoading && <Trend current={mc.this_mo ?? 0} prior={mc.last_mo ?? 0} />}</td>
                    {/* Month YoY */}
                    <td className="text-right px-2 py-2 border-l border-slate-100">{cell(model, "this_mo")}</td>
                    <td className="text-right px-2 py-2 text-slate-400">{cell(model, "this_mo_ly")}</td>
                    <td className="px-1 py-2">{!activityLoading && <Trend current={mc.this_mo ?? 0} prior={mc.this_mo_ly ?? 0} />}</td>
                    {/* Quarter */}
                    <td className="text-right px-2 py-2 border-l border-slate-100">{cell(model, "this_qtr")}</td>
                    <td className="text-right px-2 py-2 text-slate-400">{cell(model, "last_qtr")}</td>
                    <td className="px-1 py-2">{!activityLoading && <Trend current={mc.this_qtr ?? 0} prior={mc.last_qtr ?? 0} />}</td>
                    {/* Year */}
                    <td className="text-right px-2 py-2 border-l border-slate-100">{cell(model, "ytd")}</td>
                    <td className="text-right px-2 py-2 text-slate-400">{cell(model, "last_ytd")}</td>
                    <td className="px-1 py-2">{!activityLoading && <Trend current={mc.ytd ?? 0} prior={mc.last_ytd ?? 0} />}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex gap-3">
          <button onClick={() => navigate('/kanban')} className="text-xs text-blue-600 hover:text-blue-800">Kanban &rarr;</button>
          <button onClick={() => navigate('/gantt')} className="text-xs text-blue-600 hover:text-blue-800">Gantt &rarr;</button>
        </div>
      </Panel>

      {/* ─── Sync panel ─────────────────────────────────────────────── */}
      <Panel title="Sync">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {[
            { model: 'sync.Connection', label: 'Connections' },
            { model: 'sync.Bundle', label: 'Bundles' },
            { model: 'conversion.ConversionProject', label: 'Conversion Projects' },
          ].map(({ model, label }) => (
            <div
              key={model}
              onClick={() => goDb(model)}
              className="bg-slate-50 border border-slate-200 rounded-lg px-4 py-3 cursor-pointer transition-colors hover:border-blue-400 hover:bg-blue-50"
            >
              <div className="text-2xl font-bold text-slate-900">
                {syncLoading ? '...' : fmtInt(syncCounts[model] ?? 0)}
              </div>
              <div className="text-xs text-slate-500">{label}</div>
            </div>
          ))}
        </div>
        <div className="mt-3">
          <button onClick={() => navigate('/json-tree')} className="text-xs text-blue-600 hover:text-blue-800">JSON Tree &rarr;</button>
        </div>
      </Panel>
    </div>
  );
}

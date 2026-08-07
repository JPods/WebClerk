/**
 * Products Dashboard — items, variants, bills of material, catalogs, and inventory.
 *
 * Comparison table: rows = models, columns = period pairs (this/last).
 * All periods visible at once — no buttons to click.
 * Tools panel: Matrix Builder, JSON Tree, Inventory Adjust.
 */
import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWindowManager } from '@/context/WindowManagerContext';
import { useDashboardCounts } from '@/hooks/useDashboardCounts';

// ─── Config ─────────────────────────────────────────────────────────
const PRODUCT_MODELS = [
  { model: 'item', label: 'Items' },
  { model: 'products.Variant', label: 'Variants' },
  { model: 'products.BillOfMaterial', label: 'Bill of Materials' },
  { model: 'products.Catalog', label: 'Catalogs' },
  { model: 'products.Serial', label: 'Serials' },
  { model: 'products.Specification', label: 'Specifications' },
  { model: 'products.Warehouse', label: 'Warehouses' },
];

const fmtInt = (n: number) => n.toLocaleString('en-US');

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

// ─── Main component ─────────────────────────────────────────────────
export default function ProductsDashboard() {
  const navigate = useNavigate();
  const { ensureWindow, activateWindow } = useWindowManager();
  const modelNames = useMemo(() => PRODUCT_MODELS.map(m => m.model), []);
  const { counts, loading, periods } = useDashboardCounts(modelNames);

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
      <h1 className="text-xl font-bold text-gray-900 mb-1">Products</h1>
      <p className="text-xs text-slate-500 mb-5">
        Items, variants, bills of material, catalogs, and inventory.
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
              {PRODUCT_MODELS.map(({ model, label }) => {
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
                    <td className="px-1 py-2">{!loading && <Trend current={mc.this_mo ?? 0} prior={mc.last_mo ?? 0} />}</td>
                    {/* Month YoY */}
                    <td className="text-right px-2 py-2 border-l border-slate-100">{cell(model, "this_mo")}</td>
                    <td className="text-right px-2 py-2 text-slate-400">{cell(model, "this_mo_ly")}</td>
                    <td className="px-1 py-2">{!loading && <Trend current={mc.this_mo ?? 0} prior={mc.this_mo_ly ?? 0} />}</td>
                    {/* Quarter */}
                    <td className="text-right px-2 py-2 border-l border-slate-100">{cell(model, "this_qtr")}</td>
                    <td className="text-right px-2 py-2 text-slate-400">{cell(model, "last_qtr")}</td>
                    <td className="px-1 py-2">{!loading && <Trend current={mc.this_qtr ?? 0} prior={mc.last_qtr ?? 0} />}</td>
                    {/* Year */}
                    <td className="text-right px-2 py-2 border-l border-slate-100">{cell(model, "ytd")}</td>
                    <td className="text-right px-2 py-2 text-slate-400">{cell(model, "last_ytd")}</td>
                    <td className="px-1 py-2">{!loading && <Trend current={mc.ytd ?? 0} prior={mc.last_ytd ?? 0} />}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* ─── Tools panel ────────────────────────────────────────────── */}
      <Panel title="Tools">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div onClick={() => window.open('/matrix-builder', '_blank')} className="border border-slate-200 rounded-lg px-4 py-3 cursor-pointer transition-colors hover:border-blue-400">
            <div className="text-sm font-semibold">
              Matrix Builder
              <span className="text-[10px] text-slate-400 ml-1.5">external</span>
            </div>
            <div className="text-xs text-slate-500 mt-0.5">Generate item variants from axes (color, size, etc.)</div>
          </div>
          <div onClick={() => navigate('/json-tree')} className="border border-slate-200 rounded-lg px-4 py-3 cursor-pointer transition-colors hover:border-blue-400">
            <div className="text-sm font-semibold">JSON Tree</div>
            <div className="text-xs text-slate-500 mt-0.5">View, edit, and post JSON bundles</div>
          </div>
          <div onClick={() => navigate('/inventory-adjust')} className="border border-slate-200 rounded-lg px-4 py-3 cursor-pointer transition-colors hover:border-blue-400">
            <div className="text-sm font-semibold">Inventory Adjust</div>
            <div className="text-xs text-slate-500 mt-0.5">Physical count and adjustment entry</div>
          </div>
        </div>
      </Panel>
    </div>
  );
}

import { useCallback, useEffect, useMemo, useState } from "react";
import { useDispatch } from "react-redux";

import { manageAction } from "@/api/wcapi";
import ComponentCard from "@/components/common/ComponentCard";
import DataGrid, { type RichColumn } from "@/components/common/DataGrid";
import { showToast } from "@/store/slices/toastSlice";

type Row = {
  dimension_id: number;
  dimension_name: string;
  count: number;
  total: number;
  month?: string;
  year?: number;
  previous_total?: number;
  delta?: number;
  delta_percent?: number | null;
};

type SalesDimensionResponse = {
  start_date: string;
  end_date: string;
  rows: Row[];
  totals: {
    count: number;
    total: number;
  };
};

type Dimension = "customer" | "manufacturer";
type Mode = "monthly" | "yoy";

function monthStartIso(): string {
  const d = new Date();
  d.setDate(1);
  return d.toISOString().slice(0, 10);
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function money(v: number): string {
  return v.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });
}

function actionForSelection(mode: Mode, dimension: Dimension): string {
  if (mode === "yoy") return "get_tally_sales_by_customer_year";
  return dimension === "customer"
    ? "get_tally_sales_by_customer_month"
    : "get_tally_sales_by_manufacturer_month";
}

const gridTheme = {
  surface: '#fff', surfaceAlt: '#f8fafc', text: '#1e293b', textMuted: '#64748b',
  border: '#e2e8f0', borderLight: '#f1f5f9', accent: '#2563eb', accentGold: '#d97706',
  accentRed: '#dc2626', rowActive: '#2563eb', rowChecked: '#eff6ff', rowHover: '#f8fafc',
  inputBg: '#fff', inputBorder: '#cbd5e1', resizeHandle: '#94a3b8',
};

const numId = (v: unknown) => (typeof v === 'number' ? v : null);
const noop = () => {};

export default function SalesDimensionTallyList() {
  const dispatch = useDispatch();
  const [mode, setMode] = useState<Mode>("monthly");
  const [dimension, setDimension] = useState<Dimension>("customer");
  const [startDate, setStartDate] = useState(monthStartIso());
  const [endDate, setEndDate] = useState(todayIso());
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<SalesDimensionResponse | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [sort, setSort] = useState<{ field: string; direction: 'asc' | 'desc' } | null>(null);

  const fetchReport = useCallback(async () => {
    try {
      setLoading(true);
      const action = actionForSelection(mode, dimension);
      const res = (await manageAction(action, {
        start_date: startDate,
        end_date: endDate,
      })) as SalesDimensionResponse;
      setData(res);
    } catch (err) {
      console.error("Failed to load sales dimension tally", err);
      dispatch(showToast({ type: "error", message: "Failed to load sales dimension tally" }));
    } finally {
      setLoading(false);
    }
  }, [dimension, dispatch, endDate, mode, startDate]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const records = useMemo(() =>
    (data?.rows ?? []).map((r, i) => ({
      ...r,
      id: i,
      period: mode === "yoy" ? r.year : r.month,
    })),
    [data, mode]
  );

  const columns = useMemo(() => {
    const cols = ['period', 'dimension_name', 'count', 'total'];
    if (mode === 'yoy') cols.push('previous_total', 'delta', 'delta_percent');
    return cols;
  }, [mode]);

  const colWidths = useMemo(() => {
    const w: Record<string, number> = { period: 100, dimension_name: 200, count: 100, total: 140 };
    if (mode === 'yoy') { w.previous_total = 140; w.delta = 120; w.delta_percent = 120; }
    return w;
  }, [mode]);

  const fieldBehaviors = useMemo(() => {
    const b: Record<string, any> = {
      period: { type: 'readonly' },
      dimension_name: { type: 'readonly' },
      count: { type: 'number' },
      total: { type: 'currency' },
    };
    if (mode === 'yoy') {
      b.previous_total = { type: 'currency' };
      b.delta = { type: 'currency' };
      b.delta_percent = { type: 'number' };
    }
    return b;
  }, [mode]);

  const richColumns = useMemo((): RichColumn[] => {
    const cols: RichColumn[] = [
      { name: 'period', field: 'period', width: '100px', sortable: true,
        cell: (row: any) => <span className="font-mono text-xs">{row.period}</span> },
      { name: 'dimension_name', field: 'dimension_name', width: '200px', sortable: true },
      { name: 'count', field: 'count', width: '100px', sortable: true,
        cell: (row: any) => <span className="text-right w-full block">{row.count}</span> },
      { name: 'total', field: 'total', width: '140px', sortable: true,
        cell: (row: any) => <span className="text-right w-full block">{money(row.total)}</span> },
    ];
    if (mode === 'yoy') {
      cols.push(
        { name: 'previous_total', field: 'previous_total', width: '140px', sortable: true,
          cell: (row: any) => <span className="text-right w-full block">{money(row.previous_total ?? 0)}</span> },
        { name: 'delta', field: 'delta', width: '120px', sortable: true,
          cell: (row: any) => <span className="text-right w-full block">{money(row.delta ?? 0)}</span> },
        { name: 'delta_percent', field: 'delta_percent', width: '120px', sortable: true,
          cell: (row: any) => (
            <span className="text-right w-full block">
              {typeof row.delta_percent === "number" ? `${row.delta_percent.toFixed(1)}%` : "-"}
            </span>
          ) },
      );
    }
    return cols;
  }, [mode]);

  const handleSort = useCallback((field: string) => {
    setSort(prev => {
      if (prev?.field === field) return prev.direction === 'asc' ? { field, direction: 'desc' as const } : null;
      return { field, direction: 'asc' as const };
    });
  }, []);

  return (
    <div className="space-y-4" data-wc="sales-dimension-tally-list">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Sales Tallies</h1>
        <div className="text-sm text-gray-500 dark:text-gray-400">wc2 tally parity (phase 2)</div>
      </div>

      <ComponentCard>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-600 dark:text-gray-300">mode</span>
            <select
              value={mode}
              onChange={(e) => { const m = e.target.value as Mode; setMode(m); if (m === "yoy") setDimension("customer"); }}
              className="rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900"
            >
              <option value="monthly">monthly</option>
              <option value="yoy">yoy</option>
            </select>
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-600 dark:text-gray-300">dimension</span>
            <select
              value={dimension}
              onChange={(e) => setDimension(e.target.value as Dimension)}
              disabled={mode === "yoy"}
              className="rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900"
            >
              <option value="customer">customer</option>
              <option value="manufacturer">manufacturer</option>
            </select>
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-600 dark:text-gray-300">start_date</span>
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)}
              className="rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900" />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-600 dark:text-gray-300">end_date</span>
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)}
              className="rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900" />
          </label>

          <button onClick={fetchReport} disabled={loading}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60">
            {loading ? "Loading..." : "Refresh"}
          </button>
        </div>
      </ComponentCard>

      <ComponentCard>
        <DataGrid
          records={records}
          columns={columns}
          richColumns={richColumns}
          colWidths={colWidths}
          fieldBehaviors={fieldBehaviors}
          selectedId={selectedId}
          selectedRowIds={new Set<number>()}
          sort={sort}
          onSelectRecord={setSelectedId}
          onToggleRow={noop}
          onSelectAll={noop}
          onClearSelection={noop}
          onSort={handleSort}
          onColumnDrop={noop as any}
          onResizeStart={noop as any}
          numId={numId}
          theme={gridTheme}
          fontSize={13}
        />
      </ComponentCard>
    </div>
  );
}

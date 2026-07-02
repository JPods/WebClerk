import { useCallback, useEffect, useMemo, useState } from "react";
import { useDispatch } from "react-redux";

import { manageAction } from "@/api/wcapi";
import ComponentCard from "@/components/common/ComponentCard";
import DataGrid, { type RichColumn } from "@/components/common/DataGrid";
import { showToast } from "@/store/slices/toastSlice";

type MonthlyRow = {
  item_id: number;
  item_name: string;
  month: string;
  receipt_qty: number;
  issue_qty: number;
  adjust_qty: number;
  net_qty: number;
  net_value: number;
};

type YearlyRow = {
  item_id: number;
  item_name: string;
  year: number;
  usage_qty: number;
  usage_value: number;
  receipt_qty: number;
  net_qty: number;
  net_value: number;
};

type MonthlyResponse = { start_date: string; end_date: string; rows: MonthlyRow[]; totals: Record<string, number> };
type YearlyResponse = { start_date: string; end_date: string; rows: YearlyRow[]; totals: Record<string, number> };
type Mode = "monthly" | "yearly";

function monthStartIso(): string { const d = new Date(); d.setDate(1); return d.toISOString().slice(0, 10); }
function todayIso(): string { return new Date().toISOString().slice(0, 10); }
function money(v: number): string { return v.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 }); }

const gridTheme = {
  surface: '#fff', surfaceAlt: '#f8fafc', text: '#1e293b', textMuted: '#64748b',
  border: '#e2e8f0', borderLight: '#f1f5f9', accent: '#2563eb', accentGold: '#d97706',
  accentRed: '#dc2626', rowActive: '#2563eb', rowChecked: '#eff6ff', rowHover: '#f8fafc',
  inputBg: '#fff', inputBorder: '#cbd5e1', resizeHandle: '#94a3b8',
};

const numId = (v: unknown) => (typeof v === 'number' ? v : null);
const noop = () => {};

const rightCell = (val: string | number) => <span className="text-right w-full block">{val}</span>;

const monthlyRichColumns: RichColumn[] = [
  { name: 'month', field: 'month', width: '100px', sortable: true, cell: (r: any) => <span className="font-mono text-xs">{r.month}</span> },
  { name: 'item_name', field: 'item_name', width: '200px', sortable: true },
  { name: 'receipt_qty', field: 'receipt_qty', width: '110px', sortable: true, cell: (r: any) => rightCell(r.receipt_qty) },
  { name: 'issue_qty', field: 'issue_qty', width: '110px', sortable: true, cell: (r: any) => rightCell(r.issue_qty) },
  { name: 'adjust_qty', field: 'adjust_qty', width: '110px', sortable: true, cell: (r: any) => rightCell(r.adjust_qty) },
  { name: 'net_qty', field: 'net_qty', width: '110px', sortable: true, cell: (r: any) => rightCell(r.net_qty) },
  { name: 'net_value', field: 'net_value', width: '130px', sortable: true, cell: (r: any) => rightCell(money(r.net_value)) },
];

const yearlyRichColumns: RichColumn[] = [
  { name: 'year', field: 'year', width: '80px', sortable: true, cell: (r: any) => <span className="font-mono text-xs">{r.year}</span> },
  { name: 'item_name', field: 'item_name', width: '200px', sortable: true },
  { name: 'usage_qty', field: 'usage_qty', width: '110px', sortable: true, cell: (r: any) => rightCell(r.usage_qty) },
  { name: 'usage_value', field: 'usage_value', width: '130px', sortable: true, cell: (r: any) => rightCell(money(r.usage_value)) },
  { name: 'receipt_qty', field: 'receipt_qty', width: '110px', sortable: true, cell: (r: any) => rightCell(r.receipt_qty) },
  { name: 'net_qty', field: 'net_qty', width: '110px', sortable: true, cell: (r: any) => rightCell(r.net_qty) },
  { name: 'net_value', field: 'net_value', width: '130px', sortable: true, cell: (r: any) => rightCell(money(r.net_value)) },
];

const monthlyColumns = ['month', 'item_name', 'receipt_qty', 'issue_qty', 'adjust_qty', 'net_qty', 'net_value'];
const yearlyColumns = ['year', 'item_name', 'usage_qty', 'usage_value', 'receipt_qty', 'net_qty', 'net_value'];

const monthlyFieldBehaviors: Record<string, any> = {
  month: { type: 'readonly' }, item_name: { type: 'readonly' },
  receipt_qty: { type: 'number' }, issue_qty: { type: 'number' },
  adjust_qty: { type: 'number' }, net_qty: { type: 'number' }, net_value: { type: 'currency' },
};

const yearlyFieldBehaviors: Record<string, any> = {
  year: { type: 'readonly' }, item_name: { type: 'readonly' },
  usage_qty: { type: 'number' }, usage_value: { type: 'currency' },
  receipt_qty: { type: 'number' }, net_qty: { type: 'number' }, net_value: { type: 'currency' },
};

const monthlyColWidths: Record<string, number> = { month: 100, item_name: 200, receipt_qty: 110, issue_qty: 110, adjust_qty: 110, net_qty: 110, net_value: 130 };
const yearlyColWidths: Record<string, number> = { year: 80, item_name: 200, usage_qty: 110, usage_value: 130, receipt_qty: 110, net_qty: 110, net_value: 130 };

export default function InventoryUsageTallyList() {
  const dispatch = useDispatch();
  const [mode, setMode] = useState<Mode>("monthly");
  const [startDate, setStartDate] = useState(monthStartIso());
  const [endDate, setEndDate] = useState(todayIso());
  const [loading, setLoading] = useState(false);
  const [monthlyData, setMonthlyData] = useState<MonthlyResponse | null>(null);
  const [yearlyData, setYearlyData] = useState<YearlyResponse | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [sort, setSort] = useState<{ field: string; direction: 'asc' | 'desc' } | null>(null);

  const fetchReport = useCallback(async () => {
    try {
      setLoading(true);
      if (mode === "monthly") {
        const res = (await manageAction("get_tally_inventory_usage_by_month", { start_date: startDate, end_date: endDate })) as MonthlyResponse;
        setMonthlyData(res);
      } else {
        const res = (await manageAction("get_tally_inventory_yearly_summary", { start_date: startDate, end_date: endDate })) as YearlyResponse;
        setYearlyData(res);
      }
    } catch (err) {
      console.error("Failed to load inventory usage tally", err);
      dispatch(showToast({ type: "error", message: "Failed to load inventory usage tally" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch, endDate, mode, startDate]);

  useEffect(() => { fetchReport(); }, [fetchReport]);

  const records = useMemo(() => {
    const rows = mode === "monthly" ? (monthlyData?.rows ?? []) : (yearlyData?.rows ?? []);
    return rows.map((r: any, i: number) => ({ ...r, id: i }));
  }, [mode, monthlyData, yearlyData]);

  const handleSort = useCallback((field: string) => {
    setSort(prev => {
      if (prev?.field === field) return prev.direction === 'asc' ? { field, direction: 'desc' as const } : null;
      return { field, direction: 'asc' as const };
    });
  }, []);

  return (
    <div className="space-y-4" data-wc="inventory-usage-tally-list">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Inventory Usage Tallies</h1>
        <div className="text-sm text-gray-500 dark:text-gray-400">wc2 tally parity (phase 3)</div>
      </div>

      <ComponentCard>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-600 dark:text-gray-300">mode</span>
            <select value={mode} onChange={(e) => setMode(e.target.value as Mode)}
              className="rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900">
              <option value="monthly">monthly</option>
              <option value="yearly">yearly</option>
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
          columns={mode === "monthly" ? monthlyColumns : yearlyColumns}
          richColumns={mode === "monthly" ? monthlyRichColumns : yearlyRichColumns}
          colWidths={mode === "monthly" ? monthlyColWidths : yearlyColWidths}
          fieldBehaviors={mode === "monthly" ? monthlyFieldBehaviors : yearlyFieldBehaviors}
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

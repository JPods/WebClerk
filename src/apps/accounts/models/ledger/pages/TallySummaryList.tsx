import { useCallback, useEffect, useMemo, useState } from "react";
import { useDispatch } from "react-redux";

import { manageAction } from "@/api/wcapi";
import ComponentCard from "@/components/common/ComponentCard";
import DataGrid, { type RichColumn } from "@/components/common/DataGrid";
import { showToast } from "@/store/slices/toastSlice";

type SummaryRow = {
  model_name: string;
  label: string;
  count: number;
  total: number;
};

type SummaryResponse = {
  start_date: string;
  end_date: string;
  rows: SummaryRow[];
  totals: {
    count: number;
    total: number;
  };
  missing_models?: string[];
};

function firstDayOfMonthIso(): string {
  const d = new Date();
  d.setDate(1);
  return d.toISOString().slice(0, 10);
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

const gridTheme = {
  surface: '#fff',
  surfaceAlt: '#f8fafc',
  text: '#1e293b',
  textMuted: '#64748b',
  border: '#e2e8f0',
  borderLight: '#f1f5f9',
  accent: '#2563eb',
  accentGold: '#d97706',
  accentRed: '#dc2626',
  rowActive: '#2563eb',
  rowChecked: '#eff6ff',
  rowHover: '#f8fafc',
  inputBg: '#fff',
  inputBorder: '#cbd5e1',
  resizeHandle: '#94a3b8',
};

const columns = ['model_name', 'label', 'count', 'total'];

const colWidths: Record<string, number> = {
  model_name: 180,
  label: 200,
  count: 100,
  total: 140,
};

const fieldBehaviors: Record<string, any> = {
  model_name: { type: 'readonly' },
  label: { type: 'readonly' },
  count: { type: 'number' },
  total: { type: 'currency' },
};

const richColumns: RichColumn[] = [
  { name: 'model_name', field: 'model_name', width: '180px', sortable: true,
    cell: (row: any) => <span className="font-mono text-xs">{row.model_name}</span> },
  { name: 'label', field: 'label', width: '200px', sortable: true },
  { name: 'count', field: 'count', width: '100px', sortable: true,
    cell: (row: any) => <span className="text-right w-full block">{row.count}</span> },
  { name: 'total', field: 'total', width: '140px', sortable: true,
    cell: (row: any) => (
      <span className="text-right w-full block">
        {row.total.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 })}
      </span>
    ) },
];

const numId = (v: unknown) => (typeof v === 'number' ? v : null);
const noop = () => {};

export default function TallySummaryList() {
  const dispatch = useDispatch();
  const [loading, setLoading] = useState(false);
  const [startDate, setStartDate] = useState(firstDayOfMonthIso());
  const [endDate, setEndDate] = useState(todayIso());
  const [data, setData] = useState<SummaryResponse | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [sort, setSort] = useState<{ field: string; direction: 'asc' | 'desc' } | null>(null);

  const fetchSummary = useCallback(async () => {
    try {
      setLoading(true);
      const res = (await manageAction("get_tally_summary_by_period", {
        start_date: startDate,
        end_date: endDate,
      })) as SummaryResponse;
      setData(res);
    } catch (err) {
      console.error("Failed to load tally summary", err);
      dispatch(
        showToast({
          type: "error",
          message: "Failed to load period summary",
        }),
      );
    } finally {
      setLoading(false);
    }
  }, [dispatch, endDate, startDate]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  // Add synthetic id for DataGrid (keyed by model_name)
  const records = useMemo(() =>
    (data?.rows ?? []).map((r, i) => ({ ...r, id: i })),
    [data]
  );

  const handleSort = useCallback((field: string) => {
    setSort(prev => {
      if (prev?.field === field) {
        return prev.direction === 'asc' ? { field, direction: 'desc' as const } : null;
      }
      return { field, direction: 'asc' as const };
    });
  }, []);

  return (
    <div className="space-y-4" data-wc="tally-summary-list">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
          Period Summary
        </h1>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          wc2 tally parity (phase 1)
        </div>
      </div>

      <ComponentCard>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-600 dark:text-gray-300">start_date</span>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-600 dark:text-gray-300">end_date</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900"
            />
          </label>

          <button
            onClick={fetchSummary}
            disabled={loading}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
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

        {data?.missing_models && data.missing_models.length > 0 && (
          <p className="mt-3 text-xs text-amber-700 dark:text-amber-300">
            missing_models: {data.missing_models.join(", ")}
          </p>
        )}
      </ComponentCard>
    </div>
  );
}

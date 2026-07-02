import { useCallback, useEffect, useMemo, useState } from "react";
import { useDispatch } from "react-redux";

import { manageAction } from "@/api/wcapi";
import ComponentCard from "@/components/common/ComponentCard";
import DataGrid, { type RichColumn } from "@/components/common/DataGrid";
import { showToast } from "@/store/slices/toastSlice";

type RegistryEntry = {
  report_key: string;
  action: string;
  label: string;
  description: string;
  default_params: Record<string, unknown>;
};

type RegistryResponse = {
  reports: RegistryEntry[];
  count: number;
};

type ExecuteResponse = {
  report_key: string;
  report_params: Record<string, unknown>;
  result: {
    rows?: Array<Record<string, unknown>>;
    totals?: Record<string, number>;
    [key: string]: unknown;
  };
};

type ExportFormat = "csv" | "json";

function monthStartIso(): string {
  const d = new Date();
  d.setDate(1);
  return d.toISOString().slice(0, 10);
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function parseJsonObject(input: string): Record<string, unknown> {
  const trimmed = input.trim();
  if (!trimmed) return {};
  const parsed = JSON.parse(trimmed) as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("extra_params_json must be a JSON object");
  }
  return parsed as Record<string, unknown>;
}

function downloadText(content: string, filename: string, format: ExportFormat) {
  const mimeType = format === "json" ? "application/json" : "text/csv;charset=utf-8";
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

const gridTheme = {
  surface: '#fff', surfaceAlt: '#f8fafc', text: '#1e293b', textMuted: '#64748b',
  border: '#e2e8f0', borderLight: '#f1f5f9', accent: '#2563eb', accentGold: '#d97706',
  accentRed: '#dc2626', rowActive: '#2563eb', rowChecked: '#eff6ff', rowHover: '#f8fafc',
  inputBg: '#fff', inputBorder: '#cbd5e1', resizeHandle: '#94a3b8',
};

const numId = (v: unknown) => (typeof v === 'number' ? v : null);
const noop = () => {};

// Registry table columns (static)
const registryColumns = ['report_key', 'action', 'description'];
const registryColWidths: Record<string, number> = { report_key: 200, action: 200, description: 300 };
const registryFieldBehaviors: Record<string, any> = {
  report_key: { type: 'readonly' }, action: { type: 'readonly' }, description: { type: 'readonly' },
};
const registryRichColumns: RichColumn[] = [
  { name: 'report_key', field: 'report_key', width: '200px', sortable: true,
    cell: (row: any) => <span className="font-mono text-xs">{row.report_key}</span> },
  { name: 'action', field: 'action', width: '200px', sortable: true,
    cell: (row: any) => <span className="font-mono text-xs">{row.action}</span> },
  { name: 'description', field: 'description', width: '300px', sortable: true },
];

export default function TallyRegistryList() {
  const dispatch = useDispatch();
  const [loadingRegistry, setLoadingRegistry] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [exporting, setExporting] = useState(false);

  const [registry, setRegistry] = useState<RegistryEntry[]>([]);
  const [selectedReportKey, setSelectedReportKey] = useState("");

  const [startDate, setStartDate] = useState(monthStartIso());
  const [endDate, setEndDate] = useState(todayIso());
  const [extraParamsJson, setExtraParamsJson] = useState("{}");
  const [columnsCsv, setColumnsCsv] = useState("");
  const [format, setFormat] = useState<ExportFormat>("csv");

  const [resultData, setResultData] = useState<ExecuteResponse | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [sort, setSort] = useState<{ field: string; direction: 'asc' | 'desc' } | null>(null);

  const selectedReport = useMemo(
    () => registry.find((r) => r.report_key === selectedReportKey) ?? null,
    [registry, selectedReportKey],
  );

  const buildReportParams = useCallback(() => {
    const extraParams = parseJsonObject(extraParamsJson);
    return { start_date: startDate, end_date: endDate, ...extraParams } as Record<string, unknown>;
  }, [endDate, extraParamsJson, startDate]);

  const fetchRegistry = useCallback(async () => {
    try {
      setLoadingRegistry(true);
      const res = (await manageAction("get_tally_report_registry", {})) as RegistryResponse;
      const reports = res.reports ?? [];
      setRegistry(reports);
      if (!selectedReportKey && reports.length > 0) {
        setSelectedReportKey(reports[0].report_key);
      }
    } catch (err) {
      console.error("Failed to load tally report registry", err);
      dispatch(showToast({ type: "error", message: "Failed to load tally report registry" }));
    } finally {
      setLoadingRegistry(false);
    }
  }, [dispatch, selectedReportKey]);

  useEffect(() => { fetchRegistry(); }, [fetchRegistry]);

  const rows = useMemo(() => {
    if (!resultData?.result || !Array.isArray(resultData.result.rows)) return [] as Array<Record<string, unknown>>;
    return resultData.result.rows;
  }, [resultData]);

  // Dynamic columns from result data
  const rowColumns = useMemo(() => {
    const ordered: string[] = [];
    const seen = new Set<string>();
    rows.forEach((row) => {
      Object.keys(row).forEach((key) => {
        if (!seen.has(key)) { seen.add(key); ordered.push(key); }
      });
    });
    return ordered;
  }, [rows]);

  // Dynamic DataGrid config for result rows
  const resultRecords = useMemo(() => rows.map((r, i) => ({ ...r, id: i })), [rows]);
  const resultColWidths = useMemo(() => Object.fromEntries(rowColumns.map(c => [c, 150])), [rowColumns]);
  const resultFieldBehaviors = useMemo(() => Object.fromEntries(rowColumns.map(c => [c, { type: 'readonly' }])), [rowColumns]);
  const resultRichColumns = useMemo((): RichColumn[] =>
    rowColumns.map(col => ({
      name: col,
      field: col,
      width: '150px',
      sortable: true,
      cell: (row: any) => {
        const v = row[col];
        return <span className="truncate block">{typeof v === 'object' && v !== null ? JSON.stringify(v) : String(v ?? '')}</span>;
      },
    })),
    [rowColumns]
  );

  const registryRecords = useMemo(() => registry.map((r, i) => ({ ...r, id: i })), [registry]);

  const onExecute = useCallback(async () => {
    if (!selectedReportKey) { dispatch(showToast({ type: "info", message: "report_key is required" })); return; }
    try {
      setExecuting(true);
      const reportParams = buildReportParams();
      const res = (await manageAction("execute_tally_report", { report_key: selectedReportKey, report_params: reportParams })) as ExecuteResponse;
      setResultData(res);
      dispatch(showToast({ type: "success", message: "Report executed" }));
    } catch (err) {
      console.error("Failed to execute tally report", err);
      dispatch(showToast({ type: "error", message: "Failed to execute tally report" }));
    } finally {
      setExecuting(false);
    }
  }, [buildReportParams, dispatch, selectedReportKey]);

  const onExport = useCallback(async () => {
    if (!selectedReportKey) { dispatch(showToast({ type: "info", message: "report_key is required" })); return; }
    try {
      setExporting(true);
      const reportParams = buildReportParams();
      const columns = columnsCsv.split(",").map((v) => v.trim()).filter(Boolean);
      const payload = { report_key: selectedReportKey, format, report_params: reportParams, ...(columns.length > 0 ? { columns } : {}) };
      const res = (await manageAction("export_tally_report", payload)) as { filename: string; format: ExportFormat; content: string; row_count: number };
      downloadText(res.content ?? "", res.filename ?? `${selectedReportKey}.${format}`, res.format ?? format);
      dispatch(showToast({ type: "success", message: `Exported ${res.row_count ?? 0} rows` }));
    } catch (err) {
      console.error("Failed to export tally report", err);
      dispatch(showToast({ type: "error", message: "Failed to export tally report" }));
    } finally {
      setExporting(false);
    }
  }, [buildReportParams, columnsCsv, dispatch, format, selectedReportKey]);

  const handleSort = useCallback((field: string) => {
    setSort(prev => {
      if (prev?.field === field) return prev.direction === 'asc' ? { field, direction: 'desc' as const } : null;
      return { field, direction: 'asc' as const };
    });
  }, []);

  return (
    <div className="space-y-4" data-wc="tally-registry-list">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Tally Registry</h1>
        <div className="text-sm text-gray-500 dark:text-gray-400">wc2 tally parity (phase 4)</div>
      </div>

      <ComponentCard>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-600 dark:text-gray-300">report_key</span>
            <select value={selectedReportKey} onChange={(e) => setSelectedReportKey(e.target.value)}
              className="rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900">
              {registry.map((entry) => (
                <option key={entry.report_key} value={entry.report_key}>{entry.report_key}</option>
              ))}
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

          <label className="flex flex-col gap-1 text-sm lg:col-span-2">
            <span className="text-gray-600 dark:text-gray-300">extra_params_json</span>
            <textarea value={extraParamsJson} onChange={(e) => setExtraParamsJson(e.target.value)} rows={3}
              className="rounded border border-gray-300 bg-white px-3 py-2 text-sm font-mono dark:border-gray-700 dark:bg-gray-900"
              placeholder='{"some_param": "value"}' />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-600 dark:text-gray-300">format</span>
            <select value={format} onChange={(e) => setFormat(e.target.value as ExportFormat)}
              className="rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900">
              <option value="csv">csv</option>
              <option value="json">json</option>
            </select>
          </label>

          <label className="flex flex-col gap-1 text-sm lg:col-span-2">
            <span className="text-gray-600 dark:text-gray-300">columns_csv</span>
            <input value={columnsCsv} onChange={(e) => setColumnsCsv(e.target.value)}
              className="rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900"
              placeholder="model_name,count,total" />
          </label>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button onClick={fetchRegistry} disabled={loadingRegistry}
            className="rounded bg-gray-700 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-60">
            {loadingRegistry ? "Loading..." : "Refresh Registry"}
          </button>
          <button onClick={onExecute} disabled={executing || !selectedReportKey}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60">
            {executing ? "Executing..." : "Execute"}
          </button>
          <button onClick={onExport} disabled={exporting || !selectedReportKey}
            className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60">
            {exporting ? "Exporting..." : "Export"}
          </button>
        </div>

        {selectedReport && (
          <p className="mt-3 text-xs text-gray-600 dark:text-gray-300">
            description: {selectedReport.description}
          </p>
        )}
      </ComponentCard>

      <ComponentCard>
        <div className="mb-3 text-sm text-gray-600 dark:text-gray-300">
          registry_count: {registry.length}
        </div>
        <DataGrid
          records={registryRecords}
          columns={registryColumns}
          richColumns={registryRichColumns}
          colWidths={registryColWidths}
          fieldBehaviors={registryFieldBehaviors}
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

      <ComponentCard>
        <div className="mb-3 text-sm text-gray-600 dark:text-gray-300">
          result_report_key: {resultData?.report_key ?? "-"}
        </div>
        <div className="mb-3 text-sm text-gray-600 dark:text-gray-300">
          result_row_count: {rows.length}
        </div>
        {resultData?.result?.totals && (
          <pre className="mb-3 overflow-x-auto rounded border border-gray-200 bg-gray-50 p-3 text-xs dark:border-gray-700 dark:bg-gray-900">
            {JSON.stringify(resultData.result.totals, null, 2)}
          </pre>
        )}

        {rowColumns.length > 0 ? (
          <DataGrid
            records={resultRecords}
            columns={rowColumns}
            richColumns={resultRichColumns}
            colWidths={resultColWidths}
            fieldBehaviors={resultFieldBehaviors}
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
        ) : (
          <div className="py-6 text-center text-sm text-gray-500">No result rows loaded</div>
        )}
      </ComponentCard>
    </div>
  );
}

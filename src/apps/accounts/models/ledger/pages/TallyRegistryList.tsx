import { useCallback, useEffect, useMemo, useState } from "react";
import { useDispatch } from "react-redux";

import { manageAction } from "@/api/wcapi";
import ComponentCard from "@/components/common/ComponentCard";
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
  if (!trimmed) {
    return {};
  }
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

  const selectedReport = useMemo(
    () => registry.find((r) => r.report_key === selectedReportKey) ?? null,
    [registry, selectedReportKey],
  );

  const buildReportParams = useCallback(() => {
    const extraParams = parseJsonObject(extraParamsJson);
    return {
      start_date: startDate,
      end_date: endDate,
      ...extraParams,
    } as Record<string, unknown>;
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
      dispatch(
        showToast({
          type: "error",
          message: "Failed to load tally report registry",
        }),
      );
    } finally {
      setLoadingRegistry(false);
    }
  }, [dispatch, selectedReportKey]);

  useEffect(() => {
    fetchRegistry();
  }, [fetchRegistry]);

  const rows = useMemo(() => {
    if (!resultData?.result || !Array.isArray(resultData.result.rows)) {
      return [] as Array<Record<string, unknown>>;
    }
    return resultData.result.rows;
  }, [resultData]);

  const rowColumns = useMemo(() => {
    const ordered: string[] = [];
    const seen = new Set<string>();
    rows.forEach((row) => {
      Object.keys(row).forEach((key) => {
        if (!seen.has(key)) {
          seen.add(key);
          ordered.push(key);
        }
      });
    });
    return ordered;
  }, [rows]);

  const onExecute = useCallback(async () => {
    if (!selectedReportKey) {
      dispatch(showToast({ type: "info", message: "report_key is required" }));
      return;
    }

    try {
      setExecuting(true);
      const reportParams = buildReportParams();
      const res = (await manageAction("execute_tally_report", {
        report_key: selectedReportKey,
        report_params: reportParams,
      })) as ExecuteResponse;
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
    if (!selectedReportKey) {
      dispatch(showToast({ type: "info", message: "report_key is required" }));
      return;
    }

    try {
      setExporting(true);
      const reportParams = buildReportParams();
      const columns = columnsCsv
        .split(",")
        .map((v) => v.trim())
        .filter(Boolean);

      const payload = {
        report_key: selectedReportKey,
        format,
        report_params: reportParams,
        ...(columns.length > 0 ? { columns } : {}),
      };

      const res = (await manageAction("export_tally_report", payload)) as {
        filename: string;
        format: ExportFormat;
        content: string;
        row_count: number;
      };

      downloadText(res.content ?? "", res.filename ?? `${selectedReportKey}.${format}`, res.format ?? format);
      dispatch(
        showToast({
          type: "success",
          message: `Exported ${res.row_count ?? 0} rows`,
        }),
      );
    } catch (err) {
      console.error("Failed to export tally report", err);
      dispatch(showToast({ type: "error", message: "Failed to export tally report" }));
    } finally {
      setExporting(false);
    }
  }, [buildReportParams, columnsCsv, dispatch, format, selectedReportKey]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Tally Registry</h1>
        <div className="text-sm text-gray-500 dark:text-gray-400">wc2 tally parity (phase 4)</div>
      </div>

      <ComponentCard>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-600 dark:text-gray-300">report_key</span>
            <select
              value={selectedReportKey}
              onChange={(e) => setSelectedReportKey(e.target.value)}
              className="rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900"
            >
              {registry.map((entry) => (
                <option key={entry.report_key} value={entry.report_key}>
                  {entry.report_key}
                </option>
              ))}
            </select>
          </label>

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

          <label className="flex flex-col gap-1 text-sm lg:col-span-2">
            <span className="text-gray-600 dark:text-gray-300">extra_params_json</span>
            <textarea
              value={extraParamsJson}
              onChange={(e) => setExtraParamsJson(e.target.value)}
              rows={3}
              className="rounded border border-gray-300 bg-white px-3 py-2 text-sm font-mono dark:border-gray-700 dark:bg-gray-900"
              placeholder='{"some_param": "value"}'
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-600 dark:text-gray-300">format</span>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value as ExportFormat)}
              className="rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900"
            >
              <option value="csv">csv</option>
              <option value="json">json</option>
            </select>
          </label>

          <label className="flex flex-col gap-1 text-sm lg:col-span-2">
            <span className="text-gray-600 dark:text-gray-300">columns_csv</span>
            <input
              value={columnsCsv}
              onChange={(e) => setColumnsCsv(e.target.value)}
              className="rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900"
              placeholder="model_name,count,total"
            />
          </label>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button
            onClick={fetchRegistry}
            disabled={loadingRegistry}
            className="rounded bg-gray-700 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-60"
          >
            {loadingRegistry ? "Loading..." : "Refresh Registry"}
          </button>
          <button
            onClick={onExecute}
            disabled={executing || !selectedReportKey}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {executing ? "Executing..." : "Execute"}
          </button>
          <button
            onClick={onExport}
            disabled={exporting || !selectedReportKey}
            className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
          >
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
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="px-3 py-2 text-left">report_key</th>
                <th className="px-3 py-2 text-left">action</th>
                <th className="px-3 py-2 text-left">description</th>
              </tr>
            </thead>
            <tbody>
              {registry.map((entry) => (
                <tr key={entry.report_key} className="border-b border-gray-100 dark:border-gray-800">
                  <td className="px-3 py-2 font-mono text-xs">{entry.report_key}</td>
                  <td className="px-3 py-2 font-mono text-xs">{entry.action}</td>
                  <td className="px-3 py-2">{entry.description}</td>
                </tr>
              ))}
              {registry.length === 0 && !loadingRegistry && (
                <tr>
                  <td className="px-3 py-6 text-center text-gray-500" colSpan={3}>
                    No registry entries available
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
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

        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                {rowColumns.map((col) => (
                  <th key={col} className="px-3 py-2 text-left">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <tr key={`${idx}-${selectedReportKey}`} className="border-b border-gray-100 dark:border-gray-800">
                  {rowColumns.map((col) => (
                    <td key={col} className="px-3 py-2 align-top">
                      {typeof row[col] === "object" && row[col] !== null
                        ? JSON.stringify(row[col])
                        : String(row[col] ?? "")}
                    </td>
                  ))}
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td className="px-3 py-6 text-center text-gray-500" colSpan={Math.max(rowColumns.length, 1)}>
                    No result rows loaded
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </ComponentCard>
    </div>
  );
}

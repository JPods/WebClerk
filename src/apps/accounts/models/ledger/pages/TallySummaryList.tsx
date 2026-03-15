import { useCallback, useEffect, useMemo, useState } from "react";
import { useDispatch } from "react-redux";

import { manageAction } from "@/api/wcapi";
import ComponentCard from "@/components/common/ComponentCard";
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

function money(v: number): string {
  return v.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  });
}

export default function TallySummaryList() {
  const dispatch = useDispatch();
  const [loading, setLoading] = useState(false);
  const [startDate, setStartDate] = useState(firstDayOfMonthIso());
  const [endDate, setEndDate] = useState(todayIso());
  const [data, setData] = useState<SummaryResponse | null>(null);

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

  const rows = useMemo(() => data?.rows ?? [], [data]);

  return (
    <div className="space-y-4">
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
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="px-3 py-2 text-left">model_name</th>
                <th className="px-3 py-2 text-left">label</th>
                <th className="px-3 py-2 text-right">count</th>
                <th className="px-3 py-2 text-right">total</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.model_name}
                  className="border-b border-gray-100 dark:border-gray-800"
                >
                  <td className="px-3 py-2 font-mono text-xs">{r.model_name}</td>
                  <td className="px-3 py-2">{r.label}</td>
                  <td className="px-3 py-2 text-right">{r.count}</td>
                  <td className="px-3 py-2 text-right">{money(r.total)}</td>
                </tr>
              ))}
              {rows.length === 0 && !loading && (
                <tr>
                  <td
                    className="px-3 py-6 text-center text-gray-500"
                    colSpan={4}
                  >
                    No summary rows for selected period
                  </td>
                </tr>
              )}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-gray-300 font-semibold dark:border-gray-600">
                <td className="px-3 py-2" colSpan={2}>
                  totals
                </td>
                <td className="px-3 py-2 text-right">{data?.totals.count ?? 0}</td>
                <td className="px-3 py-2 text-right">
                  {money(data?.totals.total ?? 0)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>

        {data?.missing_models && data.missing_models.length > 0 && (
          <p className="mt-3 text-xs text-amber-700 dark:text-amber-300">
            missing_models: {data.missing_models.join(", ")}
          </p>
        )}
      </ComponentCard>
    </div>
  );
}

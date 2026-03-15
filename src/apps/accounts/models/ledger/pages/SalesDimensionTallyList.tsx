import { useCallback, useEffect, useMemo, useState } from "react";
import { useDispatch } from "react-redux";

import { manageAction } from "@/api/wcapi";
import ComponentCard from "@/components/common/ComponentCard";
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
  return v.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  });
}

function actionForSelection(mode: Mode, dimension: Dimension): string {
  if (mode === "yoy") {
    return "get_tally_sales_by_customer_year";
  }
  return dimension === "customer"
    ? "get_tally_sales_by_customer_month"
    : "get_tally_sales_by_manufacturer_month";
}

export default function SalesDimensionTallyList() {
  const dispatch = useDispatch();
  const [mode, setMode] = useState<Mode>("monthly");
  const [dimension, setDimension] = useState<Dimension>("customer");
  const [startDate, setStartDate] = useState(monthStartIso());
  const [endDate, setEndDate] = useState(todayIso());
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<SalesDimensionResponse | null>(null);

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
      dispatch(
        showToast({
          type: "error",
          message: "Failed to load sales dimension tally",
        }),
      );
    } finally {
      setLoading(false);
    }
  }, [dimension, dispatch, endDate, mode, startDate]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const rows = useMemo(() => data?.rows ?? [], [data]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
          Sales Tallies
        </h1>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          wc2 tally parity (phase 2)
        </div>
      </div>

      <ComponentCard>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-600 dark:text-gray-300">mode</span>
            <select
              value={mode}
              onChange={(e) => {
                const nextMode = e.target.value as Mode;
                setMode(nextMode);
                if (nextMode === "yoy") {
                  setDimension("customer");
                }
              }}
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
            onClick={fetchReport}
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
                <th className="px-3 py-2 text-left">{mode === "yoy" ? "year" : "month"}</th>
                <th className="px-3 py-2 text-left">dimension_name</th>
                <th className="px-3 py-2 text-right">count</th>
                <th className="px-3 py-2 text-right">total</th>
                {mode === "yoy" && (
                  <>
                    <th className="px-3 py-2 text-right">previous_total</th>
                    <th className="px-3 py-2 text-right">delta</th>
                    <th className="px-3 py-2 text-right">delta_percent</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={`${r.dimension_id}-${mode === "yoy" ? r.year : r.month}`}
                  className="border-b border-gray-100 dark:border-gray-800"
                >
                  <td className="px-3 py-2 font-mono text-xs">{mode === "yoy" ? r.year : r.month}</td>
                  <td className="px-3 py-2">{r.dimension_name}</td>
                  <td className="px-3 py-2 text-right">{r.count}</td>
                  <td className="px-3 py-2 text-right">{money(r.total)}</td>
                  {mode === "yoy" && (
                    <>
                      <td className="px-3 py-2 text-right">{money(r.previous_total ?? 0)}</td>
                      <td className="px-3 py-2 text-right">{money(r.delta ?? 0)}</td>
                      <td className="px-3 py-2 text-right">
                        {typeof r.delta_percent === "number" ? `${r.delta_percent.toFixed(1)}%` : "-"}
                      </td>
                    </>
                  )}
                </tr>
              ))}
              {rows.length === 0 && !loading && (
                <tr>
                  <td className="px-3 py-6 text-center text-gray-500" colSpan={mode === "yoy" ? 7 : 4}>
                    No sales tally rows for selected period
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
      </ComponentCard>
    </div>
  );
}

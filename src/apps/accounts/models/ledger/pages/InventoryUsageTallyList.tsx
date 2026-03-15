import { useCallback, useEffect, useMemo, useState } from "react";
import { useDispatch } from "react-redux";

import { manageAction } from "@/api/wcapi";
import ComponentCard from "@/components/common/ComponentCard";
import { showToast } from "@/store/slices/toastSlice";

type MonthlyRow = {
  item_id: number;
  item_name: string;
  month: string;
  count: number;
  receipt_qty: number;
  issue_qty: number;
  adjust_qty: number;
  net_qty: number;
  receipt_value: number;
  issue_value: number;
  adjust_value: number;
  net_value: number;
};

type YearlyRow = {
  item_id: number;
  item_name: string;
  year: number;
  count: number;
  usage_qty: number;
  usage_value: number;
  receipt_qty: number;
  adjust_qty: number;
  net_qty: number;
  net_value: number;
};

type MonthlyResponse = {
  start_date: string;
  end_date: string;
  rows: MonthlyRow[];
  totals: Record<string, number>;
};

type YearlyResponse = {
  start_date: string;
  end_date: string;
  rows: YearlyRow[];
  totals: Record<string, number>;
};

type Mode = "monthly" | "yearly";

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

export default function InventoryUsageTallyList() {
  const dispatch = useDispatch();
  const [mode, setMode] = useState<Mode>("monthly");
  const [startDate, setStartDate] = useState(monthStartIso());
  const [endDate, setEndDate] = useState(todayIso());
  const [loading, setLoading] = useState(false);
  const [monthlyData, setMonthlyData] = useState<MonthlyResponse | null>(null);
  const [yearlyData, setYearlyData] = useState<YearlyResponse | null>(null);

  const fetchReport = useCallback(async () => {
    try {
      setLoading(true);
      if (mode === "monthly") {
        const res = (await manageAction("get_tally_inventory_usage_by_month", {
          start_date: startDate,
          end_date: endDate,
        })) as MonthlyResponse;
        setMonthlyData(res);
      } else {
        const res = (await manageAction("get_tally_inventory_yearly_summary", {
          start_date: startDate,
          end_date: endDate,
        })) as YearlyResponse;
        setYearlyData(res);
      }
    } catch (err) {
      console.error("Failed to load inventory usage tally", err);
      dispatch(
        showToast({
          type: "error",
          message: "Failed to load inventory usage tally",
        }),
      );
    } finally {
      setLoading(false);
    }
  }, [dispatch, endDate, mode, startDate]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const monthlyRows = useMemo(() => monthlyData?.rows ?? [], [monthlyData]);
  const yearlyRows = useMemo(() => yearlyData?.rows ?? [], [yearlyData]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
          Inventory Usage Tallies
        </h1>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          wc2 tally parity (phase 3)
        </div>
      </div>

      <ComponentCard>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-600 dark:text-gray-300">mode</span>
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as Mode)}
              className="rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900"
            >
              <option value="monthly">monthly</option>
              <option value="yearly">yearly</option>
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

      {mode === "monthly" ? (
        <ComponentCard>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="px-3 py-2 text-left">month</th>
                  <th className="px-3 py-2 text-left">item_name</th>
                  <th className="px-3 py-2 text-right">receipt_qty</th>
                  <th className="px-3 py-2 text-right">issue_qty</th>
                  <th className="px-3 py-2 text-right">adjust_qty</th>
                  <th className="px-3 py-2 text-right">net_qty</th>
                  <th className="px-3 py-2 text-right">net_value</th>
                </tr>
              </thead>
              <tbody>
                {monthlyRows.map((row) => (
                  <tr key={`${row.item_id}-${row.month}`} className="border-b border-gray-100 dark:border-gray-800">
                    <td className="px-3 py-2 font-mono text-xs">{row.month}</td>
                    <td className="px-3 py-2">{row.item_name}</td>
                    <td className="px-3 py-2 text-right">{row.receipt_qty}</td>
                    <td className="px-3 py-2 text-right">{row.issue_qty}</td>
                    <td className="px-3 py-2 text-right">{row.adjust_qty}</td>
                    <td className="px-3 py-2 text-right">{row.net_qty}</td>
                    <td className="px-3 py-2 text-right">{money(row.net_value)}</td>
                  </tr>
                ))}
                {monthlyRows.length === 0 && !loading && (
                  <tr>
                    <td className="px-3 py-6 text-center text-gray-500" colSpan={7}>
                      No inventory usage rows for selected period
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </ComponentCard>
      ) : (
        <ComponentCard>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="px-3 py-2 text-left">year</th>
                  <th className="px-3 py-2 text-left">item_name</th>
                  <th className="px-3 py-2 text-right">usage_qty</th>
                  <th className="px-3 py-2 text-right">usage_value</th>
                  <th className="px-3 py-2 text-right">receipt_qty</th>
                  <th className="px-3 py-2 text-right">net_qty</th>
                  <th className="px-3 py-2 text-right">net_value</th>
                </tr>
              </thead>
              <tbody>
                {yearlyRows.map((row) => (
                  <tr key={`${row.item_id}-${row.year}`} className="border-b border-gray-100 dark:border-gray-800">
                    <td className="px-3 py-2 font-mono text-xs">{row.year}</td>
                    <td className="px-3 py-2">{row.item_name}</td>
                    <td className="px-3 py-2 text-right">{row.usage_qty}</td>
                    <td className="px-3 py-2 text-right">{money(row.usage_value)}</td>
                    <td className="px-3 py-2 text-right">{row.receipt_qty}</td>
                    <td className="px-3 py-2 text-right">{row.net_qty}</td>
                    <td className="px-3 py-2 text-right">{money(row.net_value)}</td>
                  </tr>
                ))}
                {yearlyRows.length === 0 && !loading && (
                  <tr>
                    <td className="px-3 py-6 text-center text-gray-500" colSpan={7}>
                      No yearly inventory summary rows for selected period
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </ComponentCard>
      )}
    </div>
  );
}

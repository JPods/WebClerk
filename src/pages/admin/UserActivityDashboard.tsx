/**
 * UserActivityDashboard.tsx — Admin page showing daily user API usage,
 * response patterns, and diagnostic hints.
 *
 * Fetches UserDailyLog records and renders stat cards, a day-by-day
 * table, and expandable hint/error panels.
 *
 * Route: /core/user-activity
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Calendar,
  ChevronDown,
  ChevronRight,
  Clock,
  Info,
  Loader2,
  RefreshCw,
  Server,
  ShieldAlert,
  XCircle,
  Zap,
} from "lucide-react";
import {
  fetchUserDailyLogs,
  fetchDailyLogsByDate,
} from "../../apps/core/services/userDailyLogApi";
import type {
  UserDailyLog,
  DailyHint,
  ErrorDetail,
} from "../../apps/core/models/log/UserDailyLog";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const HINT_ICON: Record<string, typeof AlertTriangle> = {
  info: Info,
  warning: AlertTriangle,
  error: XCircle,
};

const HINT_STYLE: Record<string, string> = {
  info: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-800",
  warning:
    "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-300 dark:border-amber-800",
  error:
    "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-800",
};

function fmtDate(d: string) {
  return new Date(d + "T00:00:00").toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function fmtNum(n: number) {
  return n.toLocaleString();
}

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

/* ------------------------------------------------------------------ */
/*  Stat Card                                                          */
/* ------------------------------------------------------------------ */

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  accent = "text-indigo-600",
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: typeof Activity;
  accent?: string;
}) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 ${accent} dark:bg-slate-800`}
      >
        <Icon size={18} />
      </div>
      <div>
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
          {label}
        </p>
        <p className="text-lg font-semibold text-slate-800 dark:text-slate-100">
          {typeof value === "number" ? fmtNum(value) : value}
        </p>
        {sub && (
          <p className="text-[11px] text-slate-400 dark:text-slate-500">
            {sub}
          </p>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Hint Row                                                           */
/* ------------------------------------------------------------------ */

function HintRow({ hint }: { hint: DailyHint }) {
  const Icon = HINT_ICON[hint.level] ?? Info;
  const style = HINT_STYLE[hint.level] ?? HINT_STYLE.info;
  return (
    <div
      className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-sm ${style}`}
    >
      <Icon size={14} className="mt-0.5 shrink-0" />
      <span>{hint.message}</span>
      <span className="ml-auto shrink-0 rounded bg-white/60 px-1.5 text-xs font-medium dark:bg-slate-800/40">
        ×{hint.count}
      </span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Expandable Day Row                                                 */
/* ------------------------------------------------------------------ */

function DayRow({ log }: { log: UserDailyLog }) {
  const [open, setOpen] = useState(false);
  const errRate = log.response_summary?.error_rate ?? 0;
  const hasHints = (log.hints?.length ?? 0) > 0;
  const hasErrors = (log.error_details?.length ?? 0) > 0;

  return (
    <div className="border-b border-slate-100 last:border-0 dark:border-slate-800">
      {/* Summary row */}
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800/50"
      >
        {open ? (
          <ChevronDown size={14} className="text-slate-400" />
        ) : (
          <ChevronRight size={14} className="text-slate-400" />
        )}
        <span className="w-32 font-medium text-slate-700 dark:text-slate-200">
          {fmtDate(log.log_date)}
        </span>
        <span className="w-20 text-right tabular-nums text-slate-600 dark:text-slate-300">
          {fmtNum(log.total_calls)}
        </span>
        <span className="w-20 text-right tabular-nums text-slate-600 dark:text-slate-300">
          {fmtNum(log.total_errors)}
        </span>
        <span
          className={`w-16 text-right tabular-nums ${
            errRate > 0.1
              ? "text-red-600"
              : errRate > 0.05
              ? "text-amber-600"
              : "text-green-600"
          }`}
        >
          {pct(errRate)}
        </span>
        <span className="w-20 text-right tabular-nums text-slate-500 dark:text-slate-400">
          {log.avg_duration_ms}ms
        </span>
        <div className="ml-auto flex items-center gap-1">
          {hasHints && (
            <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
              {log.hints.length} hint{log.hints.length !== 1 ? "s" : ""}
            </span>
          )}
          {hasErrors && (
            <span className="rounded bg-red-100 px-1.5 py-0.5 text-[10px] font-medium text-red-700 dark:bg-red-900/30 dark:text-red-300">
              {log.error_details.length} error group
              {log.error_details.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </button>

      {/* Expanded details */}
      {open && (
        <div className="space-y-3 bg-slate-50/50 px-6 py-3 dark:bg-slate-800/30">
          {/* Call breakdown */}
          <div className="grid grid-cols-3 gap-4 text-xs">
            <div>
              <p className="mb-1 font-semibold text-slate-600 dark:text-slate-300">
                By Method
              </p>
              {Object.entries(log.call_counts?.by_method ?? {}).map(
                ([method, count]) => (
                  <div
                    key={method}
                    className="flex justify-between text-slate-500 dark:text-slate-400"
                  >
                    <span className="font-mono">{method}</span>
                    <span>{fmtNum(count as number)}</span>
                  </div>
                ),
              )}
            </div>
            <div>
              <p className="mb-1 font-semibold text-slate-600 dark:text-slate-300">
                By Endpoint
              </p>
              {Object.entries(log.call_counts?.by_endpoint ?? {}).map(
                ([ep, count]) => (
                  <div
                    key={ep}
                    className="flex justify-between text-slate-500 dark:text-slate-400"
                  >
                    <span className="font-mono">{ep}</span>
                    <span>{fmtNum(count as number)}</span>
                  </div>
                ),
              )}
            </div>
            <div>
              <p className="mb-1 font-semibold text-slate-600 dark:text-slate-300">
                Top Models
              </p>
              {Object.entries(log.call_counts?.by_model ?? {})
                .sort((a, b) => (b[1] as number) - (a[1] as number))
                .slice(0, 8)
                .map(([model, count]) => (
                  <div
                    key={model}
                    className="flex justify-between text-slate-500 dark:text-slate-400"
                  >
                    <span className="font-mono">{model}</span>
                    <span>{fmtNum(count as number)}</span>
                  </div>
                ))}
            </div>
          </div>

          {/* Status codes */}
          {log.response_summary?.status_codes && (
            <div>
              <p className="mb-1 text-xs font-semibold text-slate-600 dark:text-slate-300">
                Status Codes
              </p>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(log.response_summary.status_codes)
                  .sort((a, b) => Number(b[0]) - Number(a[0]))
                  .map(([code, count]) => {
                    const n = Number(code);
                    const color =
                      n >= 500
                        ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300"
                        : n >= 400
                        ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
                        : "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300";
                    return (
                      <span
                        key={code}
                        className={`rounded px-2 py-0.5 text-xs font-mono ${color}`}
                      >
                        {code}: {count}
                      </span>
                    );
                  })}
              </div>
            </div>
          )}

          {/* Hints */}
          {hasHints && (
            <div className="space-y-1.5">
              <p className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                Diagnostic Hints
              </p>
              {log.hints.map((h, i) => (
                <HintRow key={i} hint={h} />
              ))}
            </div>
          )}

          {/* Error details */}
          {hasErrors && (
            <div>
              <p className="mb-1 text-xs font-semibold text-slate-600 dark:text-slate-300">
                Error Groups
              </p>
              <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
                <table className="w-full text-xs">
                  <thead className="bg-slate-100 dark:bg-slate-800">
                    <tr>
                      <th className="px-2 py-1 text-left font-medium text-slate-600 dark:text-slate-300">
                        Endpoint
                      </th>
                      <th className="px-2 py-1 text-left font-medium text-slate-600 dark:text-slate-300">
                        Status
                      </th>
                      <th className="px-2 py-1 text-right font-medium text-slate-600 dark:text-slate-300">
                        Count
                      </th>
                      <th className="px-2 py-1 text-left font-medium text-slate-600 dark:text-slate-300">
                        Message
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {log.error_details.map((ed: ErrorDetail, i: number) => (
                      <tr
                        key={i}
                        className="border-t border-slate-100 dark:border-slate-800"
                      >
                        <td className="px-2 py-1 font-mono text-slate-600 dark:text-slate-300">
                          {ed.endpoint}
                        </td>
                        <td className="px-2 py-1">
                          <span className="rounded bg-red-100 px-1 text-red-700 dark:bg-red-900/30 dark:text-red-300">
                            {ed.status_code}
                          </span>
                        </td>
                        <td className="px-2 py-1 text-right tabular-nums">
                          {ed.count}
                        </td>
                        <td className="max-w-xs truncate px-2 py-1 text-slate-500 dark:text-slate-400">
                          {ed.error_message}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Page                                                          */
/* ------------------------------------------------------------------ */

type ViewMode = "recent" | "date";

export default function UserActivityDashboard() {
  const [logs, setLogs] = useState<UserDailyLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("recent");
  const [selectedDate, setSelectedDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 1);
    return d.toISOString().split("T")[0];
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (viewMode === "date") {
        const result = await fetchDailyLogsByDate(selectedDate);
        setLogs(result);
      } else {
        const resp = await fetchUserDailyLogs({
          ordering: "-log_date",
          limit: 30,
        });
        setLogs(resp.results);
      }
    } catch (err: any) {
      setError(err?.message ?? "Failed to fetch daily logs");
    } finally {
      setLoading(false);
    }
  }, [viewMode, selectedDate]);

  useEffect(() => {
    load();
  }, [load]);

  /* ── Aggregated stats across loaded logs ── */
  const stats = useMemo(() => {
    if (logs.length === 0)
      return {
        totalCalls: 0,
        totalErrors: 0,
        avgDuration: 0,
        daysCount: 0,
        hintCount: 0,
        avgErrorRate: 0,
      };
    const totalCalls = logs.reduce((s, l) => s + l.total_calls, 0);
    const totalErrors = logs.reduce((s, l) => s + l.total_errors, 0);
    const avgDuration = Math.round(
      logs.reduce((s, l) => s + l.avg_duration_ms, 0) / logs.length,
    );
    const hintCount = logs.reduce((s, l) => s + (l.hints?.length ?? 0), 0);
    return {
      totalCalls,
      totalErrors,
      avgDuration,
      daysCount: logs.length,
      hintCount,
      avgErrorRate: totalCalls > 0 ? totalErrors / totalCalls : 0,
    };
  }, [logs]);

  return (
    <div className="mx-auto max-w-6xl space-y-5 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">
            User Activity Dashboard
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Daily API usage, response patterns, and diagnostic hints from
            UserDailyLog
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* View mode toggle */}
          <div className="flex rounded-lg border border-slate-200 text-sm dark:border-slate-700">
            <button
              onClick={() => setViewMode("recent")}
              className={`px-3 py-1.5 ${
                viewMode === "recent"
                  ? "bg-indigo-600 text-white"
                  : "text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
              } rounded-l-lg`}
            >
              Recent
            </button>
            <button
              onClick={() => setViewMode("date")}
              className={`px-3 py-1.5 ${
                viewMode === "date"
                  ? "bg-indigo-600 text-white"
                  : "text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
              } rounded-r-lg`}
            >
              By Date
            </button>
          </div>

          {viewMode === "date" && (
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            />
          )}

          <button
            onClick={load}
            disabled={loading}
            className="flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <StatCard
          label="Total Calls"
          value={stats.totalCalls}
          sub={`across ${stats.daysCount} day${stats.daysCount !== 1 ? "s" : ""}`}
          icon={BarChart3}
          accent="text-indigo-600"
        />
        <StatCard
          label="Total Errors"
          value={stats.totalErrors}
          icon={XCircle}
          accent="text-red-600"
        />
        <StatCard
          label="Error Rate"
          value={pct(stats.avgErrorRate)}
          icon={ShieldAlert}
          accent={
            stats.avgErrorRate > 0.1
              ? "text-red-600"
              : stats.avgErrorRate > 0.05
              ? "text-amber-600"
              : "text-green-600"
          }
        />
        <StatCard
          label="Avg Duration"
          value={`${stats.avgDuration}ms`}
          icon={Clock}
          accent="text-blue-600"
        />
        <StatCard
          label="Diagnostic Hints"
          value={stats.hintCount}
          icon={Zap}
          accent="text-amber-600"
        />
        <StatCard
          label="Days Covered"
          value={stats.daysCount}
          icon={Calendar}
          accent="text-slate-600"
        />
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 size={24} className="animate-spin text-indigo-600" />
        </div>
      )}

      {/* Day list */}
      {!loading && logs.length === 0 && (
        <div className="rounded-xl border border-slate-200 bg-white px-6 py-12 text-center dark:border-slate-700 dark:bg-slate-900">
          <Server
            size={36}
            className="mx-auto mb-3 text-slate-300 dark:text-slate-600"
          />
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
            No daily logs found for this period
          </p>
          <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
            The nightly aggregation task runs at 1:30 AM UTC. Logs will appear
            after the first run processes APILog entries.
          </p>
        </div>
      )}

      {!loading && logs.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
          {/* Column headers */}
          <div className="flex items-center gap-3 border-b border-slate-200 bg-slate-50 px-4 py-2 text-xs font-medium text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
            <span className="w-5" /> {/* chevron spacer */}
            <span className="w-32">Date</span>
            <span className="w-20 text-right">Calls</span>
            <span className="w-20 text-right">Errors</span>
            <span className="w-16 text-right">Err %</span>
            <span className="w-20 text-right">Avg ms</span>
            <span className="ml-auto">Diagnostics</span>
          </div>
          {logs.map((log) => (
            <DayRow key={log.id ?? log.log_date} log={log} />
          ))}
        </div>
      )}
    </div>
  );
}

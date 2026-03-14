/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import apiClient from "../../api/axios";
import { PostLoginURL, NetworkInfo } from "../../routes/network";
import { useAppSelector } from "../../store/hooks";
import {
  formatNetworkError,
  logNetworkDiagnostics,
} from "../../utils/networkDiagnostics";

type StatCard = {
  label: string;
  value: string;
  change?: string;
  trend?: "up" | "down" | "flat";
  accent?: string;
};

type TimelineItem = {
  title: string;
  meta?: string;
  detail?: string;
};

type NotificationItem = {
  title: string;
  time?: string;
  badge?: string;
};

type ActionItem = {
  title: string;
  owner?: string;
  due?: string;
  severity?: "high" | "medium" | "low" | string;
};

type PulseMetric = { label: string; value: string | number };

type DashboardPayload = {
  stats?: StatCard[] | Record<string, any>;
  notifications?: NotificationItem[];
  activities?: TimelineItem[];
  actions?: ActionItem[];
  shortcuts?: { label: string; to?: string; desc?: string }[];
  pulse?: PulseMetric[];
  [key: string]: any;
};

const severityColor: Record<string, string> = {
  high: "bg-rose-100 text-rose-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-emerald-100 text-emerald-700",
};

const normalizeStats = (input: DashboardPayload["stats"]): StatCard[] => {
  if (!input) return [];
  if (Array.isArray(input)) {
    return input.map((item, idx) => ({
      label: String(
        (item as any).label ?? (item as any).name ?? `Metric ${idx + 1}`,
      ),
      value: String((item as any).value ?? (item as any).count ?? "0"),
      change: (item as any).change ? String((item as any).change) : undefined,
      trend: (item as any).trend ?? "flat",
      accent: (item as any).accent,
    }));
  }

  return Object.entries(input).map(([key, val]) => ({
    label: key,
    value: typeof val === "number" ? val.toLocaleString() : String(val ?? ""),
    trend: "flat",
  }));
};

const normalizeNotifications = (input?: any): NotificationItem[] => {
  if (!input) return [];
  if (Array.isArray(input))
    return input.map((item) => ({
      title: String(item.title ?? item.message ?? item.text ?? ""),
      time: item.time ?? item.created_at ?? item.when ?? "",
      badge: item.badge ?? item.category ?? item.type ?? "",
    }));
  return [];
};

const normalizeActivities = (input?: any): TimelineItem[] => {
  if (!input) return [];
  if (Array.isArray(input))
    return input.map((item) => ({
      title: String(item.title ?? item.event ?? item.name ?? ""),
      meta: item.meta ?? item.by ?? item.actor ?? item.time ?? "",
      detail: item.detail ?? item.description ?? item.note ?? "",
    }));
  return [];
};

const normalizeActions = (input?: any): ActionItem[] => {
  if (!input) return [];
  if (Array.isArray(input))
    return input.map((item) => {
      // Handle owner - may be string or object {id, name}
      let ownerStr = "";
      const rawOwner = item.owner ?? item.assignee ?? item.by;
      if (rawOwner) {
        ownerStr =
          typeof rawOwner === "object"
            ? rawOwner.name ?? rawOwner.id ?? ""
            : String(rawOwner);
      }
      return {
        title: String(item.title ?? item.task ?? item.name ?? ""),
        owner: ownerStr,
        due: item.due ?? item.due_date ?? item.when ?? "",
        severity: item.severity ?? item.priority ?? "low",
      };
    });
  return [];
};

const normalizeShortcuts = (
  input?: any,
): { label: string; to?: string; desc?: string }[] => {
  if (!input) return [];
  if (Array.isArray(input))
    return input.map((item, idx) => ({
      label: String(
        item.label ?? item.title ?? item.name ?? `Shortcut ${idx + 1}`,
      ),
      to: item.to ?? item.href ?? item.url ?? "#",
      desc: item.desc ?? item.description ?? "",
    }));
  return [];
};

const normalizePulse = (input?: any): PulseMetric[] => {
  if (!input) return [];
  if (Array.isArray(input))
    return input.map((item, idx) => ({
      label: String(item.label ?? item.name ?? `Metric ${idx + 1}`),
      value: item.value ?? item.score ?? 0,
    }));
  if (typeof input === "object")
    return Object.entries(input).map(([label, value]) => ({ label, value }));
  return [];
};

export default function Home() {
  const { user } = useAppSelector((state) => state.auth);
  const [data, setData] = useState<DashboardPayload>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const cacheKey = "dashboard_cache_v1";

  useEffect(() => {
    let mounted = true;
    let cached: DashboardPayload | null = null;
    if (typeof sessionStorage !== "undefined") {
      try {
        const raw = sessionStorage.getItem(cacheKey);
        if (raw) {
          cached = JSON.parse(raw);
          if (mounted && cached) {
            setData(cached);
          }
        }
      } catch {
        // ignore malformed cache
      }
    }
    const fetchDashboard = async () => {
      setLoading(!cached);
      setError(null);
      try {
        const res = await apiClient.get(
          PostLoginURL.allTypes + "model_name=dashboard",
        );
        const body = (res as any)?.data ?? res;
        const payload = body?.data ?? body; // handle enveloped or direct
        if (mounted) {
          setData(payload ?? {});
          if (typeof sessionStorage !== "undefined" && payload) {
            try {
              sessionStorage.setItem(cacheKey, JSON.stringify(payload));
            } catch {}
          }
        }
      } catch (err: any) {
        if (mounted) {
          const formatted = formatNetworkError(err);
          const message = `${formatted.message} (${formatted.code})${
            formatted.status ? ` [${formatted.status}]` : ""
          }`;
          setError(message);

          // Log diagnostics for debugging
          if (formatted.code === "ERR_NETWORK") {
            console.error("Network error detected. Running diagnostics...");
            logNetworkDiagnostics(NetworkInfo.API_URL).catch(console.error);
          }
        }
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchDashboard();
    return () => {
      mounted = false;
    };
  }, []);

  const stats = useMemo(
    () =>
      normalizeStats(data.stats ?? data.metrics ?? data.summary ?? data.cards),
    [data],
  );
  const notifications = useMemo(
    () =>
      normalizeNotifications(
        data.notifications ?? data.alerts ?? data.messages,
      ),
    [data],
  );
  const activities = useMemo(
    () => normalizeActivities(data.activities ?? data.events ?? data.timeline),
    [data],
  );
  const actions = useMemo(
    () => normalizeActions(data.actions ?? data.tasks ?? data.assigned),
    [data],
  );
  const shortcuts = useMemo(
    () =>
      normalizeShortcuts(
        data.shortcuts ?? data.quick_links ?? data.quick_actions,
      ),
    [data],
  );
  const pulse = useMemo(
    () => normalizePulse(data.pulse ?? data.health ?? data.project_pulse),
    [data],
  );

  const accentFallback = [
    "bg-emerald-100 text-emerald-700",
    "bg-blue-100 text-blue-700",
    "bg-amber-100 text-amber-700",
    "bg-rose-100 text-rose-700",
  ];

  return (
    <div className="space-y-8 p-6 lg:p-8">
      <header className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.08em] text-blue-500">
            Overview
          </p>
          <h1 className="text-3xl font-semibold text-gray-900 dark:text-white">
            Welcome back{user?.name_first ? `, ${user.name_first}` : ""}
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Live data from your workspace.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link
            to="/orders/create"
            className="rounded-full bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-blue-500/30 transition hover:-translate-y-[1px] hover:bg-blue-700"
          >
            Create Order
          </Link>
          <Link
            to="/reports"
            className="rounded-full border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-800 transition hover:-translate-y-[1px] hover:border-blue-300 hover:text-blue-700 dark:border-gray-700 dark:text-gray-200 dark:hover:border-blue-500"
          >
            View Reports
          </Link>
        </div>
      </header>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-200">
          <div className="flex items-center justify-between gap-2">
            <span>{error}</span>
            <button
              onClick={() => {
                console.clear();
                logNetworkDiagnostics(NetworkInfo.API_URL);
              }}
              className="whitespace-nowrap rounded bg-rose-200 px-2 py-1 text-xs font-semibold text-rose-900 hover:bg-rose-300 dark:bg-rose-900 dark:text-rose-100"
            >
              Debug
            </button>
          </div>
        </div>
      )}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {loading && stats.length === 0 ? (
          Array.from({ length: 4 }).map((_, idx) => (
            <div
              key={idx}
              className="h-28 rounded-2xl border border-gray-100 bg-white/60 p-4 shadow-sm ring-1 ring-black/5 animate-pulse dark:border-gray-800 dark:bg-gray-900/60 dark:ring-white/5"
            />
          ))
        ) : stats.length ? (
          stats.map((item, idx) => (
            <div
              key={`${item.label}-${idx}`}
              className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm ring-1 ring-black/5 transition hover:-translate-y-[2px] hover:shadow-md dark:border-gray-800 dark:bg-gray-900 dark:ring-white/5"
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  {item.label}
                </p>
                {item.change && (
                  <span
                    className={`rounded-full px-2 py-1 text-xs font-semibold ${
                      item.accent ?? accentFallback[idx % accentFallback.length]
                    }`}
                  >
                    {item.change}
                  </span>
                )}
              </div>
              <p className="mt-3 text-3xl font-semibold text-gray-900 dark:text-white">
                {item.value}
              </p>
              {item.trend && (
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  {item.trend === "up"
                    ? "Improving"
                    : item.trend === "down"
                    ? "Needs attention"
                    : "Stable"}
                </p>
              )}
            </div>
          ))
        ) : (
          <div className="col-span-full rounded-2xl border border-dashed border-gray-200 bg-gray-50 p-6 text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900/60 dark:text-gray-300">
            No metrics available yet.
          </div>
        )}
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm ring-1 ring-black/5 dark:border-gray-800 dark:bg-gray-900 dark:ring-white/5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Recent Notifications
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Updates from your data source.
                </p>
              </div>
              <Link
                to="/notifications"
                className="text-sm font-semibold text-blue-600 hover:text-blue-700"
              >
                View all
              </Link>
            </div>
            <div className="mt-4 space-y-3">
              {loading && notifications.length === 0 ? (
                Array.from({ length: 3 }).map((_, idx) => (
                  <div
                    key={idx}
                    className="h-16 rounded-xl border border-gray-100 bg-gray-50/60 p-3 animate-pulse dark:border-gray-800 dark:bg-gray-800/60"
                  />
                ))
              ) : notifications.length ? (
                notifications.map((note, idx) => (
                  <div
                    key={`${note.title}-${idx}`}
                    className="flex items-start gap-3 rounded-xl border border-gray-100 bg-gray-50/60 p-3 transition hover:border-blue-200 hover:bg-blue-50 dark:border-gray-800 dark:bg-gray-800/50 dark:hover:border-blue-500/40"
                  >
                    <div
                      className="mt-0.5 h-2 w-2 rounded-full bg-blue-500"
                      aria-hidden
                    />
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-semibold text-gray-900 dark:text-white">
                          {note.title}
                        </p>
                        {note.time && (
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {note.time}
                          </span>
                        )}
                      </div>
                      {note.badge && (
                        <span className="mt-1 inline-flex rounded-full bg-gray-200 px-2 py-0.5 text-xs font-semibold text-gray-700 dark:bg-gray-700 dark:text-gray-200">
                          {note.badge}
                        </span>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 p-4 text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900/60 dark:text-gray-300">
                  No notifications available.
                </div>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm ring-1 ring-black/5 dark:border-gray-800 dark:bg-gray-900 dark:ring-white/5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Activity Timeline
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Latest movements from the backend.
                </p>
              </div>
              <Link
                to="/activity"
                className="text-sm font-semibold text-blue-600 hover:text-blue-700"
              >
                See timeline
              </Link>
            </div>
            <div className="mt-4 space-y-4">
              {loading && activities.length === 0 ? (
                Array.from({ length: 4 }).map((_, idx) => (
                  <div
                    key={idx}
                    className="h-20 rounded-xl border border-gray-100 bg-gray-50/60 p-3 animate-pulse dark:border-gray-800 dark:bg-gray-800/60"
                  />
                ))
              ) : activities.length ? (
                activities.map((item, idx) => (
                  <div key={`${item.title}-${idx}`} className="relative pl-6">
                    {idx !== activities.length - 1 && (
                      <span
                        className="absolute left-2 top-3 h-full w-px bg-gray-200 dark:bg-gray-700"
                        aria-hidden
                      />
                    )}
                    <span
                      className="absolute left-0 top-2 h-3 w-3 rounded-full bg-blue-500"
                      aria-hidden
                    />
                    <div className="rounded-xl border border-gray-100 bg-gray-50/70 p-3 dark:border-gray-800 dark:bg-gray-800/60">
                      <p className="text-sm font-semibold text-gray-900 dark:text-white">
                        {item.title}
                      </p>
                      {item.meta && (
                        <p className="text-xs font-semibold text-gray-500 dark:text-gray-400">
                          {item.meta}
                        </p>
                      )}
                      {item.detail && (
                        <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
                          {item.detail}
                        </p>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 p-4 text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900/60 dark:text-gray-300">
                  No recent activities.
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm ring-1 ring-black/5 dark:border-gray-800 dark:bg-gray-900 dark:ring-white/5">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Quick Shortcuts
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Rendered from backend links.
            </p>
            <div className="mt-4 grid gap-3">
              {loading && shortcuts.length === 0 ? (
                Array.from({ length: 4 }).map((_, idx) => (
                  <div
                    key={idx}
                    className="h-14 rounded-xl border border-gray-100 bg-gray-50/60 p-3 animate-pulse dark:border-gray-800 dark:bg-gray-800/60"
                  />
                ))
              ) : shortcuts.length ? (
                shortcuts.map((action, idx) => (
                  <Link
                    key={`${action.label}-${idx}`}
                    to={action.to ?? "#"}
                    className="group rounded-xl border border-gray-100 bg-gray-50/60 p-3 text-left shadow-sm transition hover:-translate-y-[1px] hover:border-blue-200 hover:bg-blue-50 dark:border-gray-800 dark:bg-gray-800/60 dark:hover:border-blue-500/50"
                  >
                    <p className="text-sm font-semibold text-gray-900 group-hover:text-blue-700 dark:text-white">
                      {action.label}
                    </p>
                    {action.desc && (
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {action.desc}
                      </p>
                    )}
                  </Link>
                ))
              ) : (
                <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 p-4 text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900/60 dark:text-gray-300">
                  No shortcuts provided.
                </div>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm ring-1 ring-black/5 dark:border-gray-800 dark:bg-gray-900 dark:ring-white/5">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Developer Tools
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              API documentation and testing tools
            </p>
            <div className="mt-4 grid gap-3">
              <a
                href={`${NetworkInfo.API_URL}/wcapi/swagger/`}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex items-center justify-between rounded-xl border border-gray-100 bg-gray-50/60 p-3 text-left shadow-sm transition hover:-translate-y-[1px] hover:border-blue-200 hover:bg-blue-50 dark:border-gray-800 dark:bg-gray-800/60 dark:hover:border-blue-500/50"
              >
                <div>
                  <p className="text-sm font-semibold text-gray-900 group-hover:text-blue-700 dark:text-white">
                    📚 API Documentation (Swagger)
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Interactive API documentation and testing
                  </p>
                </div>
                <svg className="h-5 w-5 text-gray-400 group-hover:text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
              <Link
                to="/whitelist"
                className="group flex items-center justify-between rounded-xl border border-gray-100 bg-gray-50/60 p-3 text-left shadow-sm transition hover:-translate-y-[1px] hover:border-blue-200 hover:bg-blue-50 dark:border-gray-800 dark:bg-gray-800/60 dark:hover:border-blue-500/50"
              >
                <div>
                  <p className="text-sm font-semibold text-gray-900 group-hover:text-blue-700 dark:text-white">
                    🧪 Whitelist API Tester
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Test whitelisted API endpoints
                  </p>
                </div>
                <svg className="h-5 w-5 text-gray-400 group-hover:text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
            </div>
          </div>

          <div className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm ring-1 ring-black/5 dark:border-gray-800 dark:bg-gray-900 dark:ring-white/5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Assigned Actions
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Directly from backend payload.
                </p>
              </div>
              <Link
                to="/tasks"
                className="text-sm font-semibold text-blue-600 hover:text-blue-700"
              >
                Open tasks
              </Link>
            </div>
            <div className="mt-4 space-y-3">
              {loading && actions.length === 0 ? (
                Array.from({ length: 3 }).map((_, idx) => (
                  <div
                    key={idx}
                    className="h-16 rounded-xl border border-gray-100 bg-gray-50/60 p-3 animate-pulse dark:border-gray-800 dark:bg-gray-800/60"
                  />
                ))
              ) : actions.length ? (
                actions.map((item, idx) => (
                  <div
                    key={`${item.title}-${idx}`}
                    className="rounded-xl border border-gray-100 bg-gray-50/60 p-3 shadow-sm transition hover:border-blue-200 hover:bg-blue-50 dark:border-gray-800 dark:bg-gray-800/60 dark:hover:border-blue-500/40"
                  >
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold text-gray-900 dark:text-white">
                        {item.title}
                      </p>
                      {item.severity && (
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                            severityColor[
                              String(item.severity).toLowerCase()
                            ] ?? "bg-gray-200 text-gray-700"
                          }`}
                        >
                          {item.severity}
                        </span>
                      )}
                    </div>
                    {item.owner && (
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Owner: {item.owner}
                      </p>
                    )}
                    {item.due && (
                      <p className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                        Due: {item.due}
                      </p>
                    )}
                  </div>
                ))
              ) : (
                <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 p-4 text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900/60 dark:text-gray-300">
                  No assigned actions.
                </div>
              )}
            </div>
          </div>

          <div className="rounded-2xl bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 p-5 text-white shadow-lg">
            <h2 className="text-lg font-semibold">Project Pulse</h2>
            <p className="text-sm text-white/80">
              Surfaced from backend metrics.
            </p>
            <div className="mt-4 space-y-3">
              {loading && pulse.length === 0 ? (
                Array.from({ length: 3 }).map((_, idx) => (
                  <div
                    key={idx}
                    className="h-6 rounded-full bg-white/20 animate-pulse"
                  />
                ))
              ) : pulse.length ? (
                pulse.map((item, idx) => (
                  <div key={`${item.label}-${idx}`} className="space-y-1">
                    <div className="flex items-center justify-between text-xs font-semibold">
                      <span>{item.label}</span>
                      <span>{item.value}</span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-white/20">
                      <div
                        className="h-2 rounded-full bg-white shadow-inner"
                        style={{
                          width:
                            typeof item.value === "number"
                              ? `${Math.min(100, Math.max(0, item.value))}%`
                              : undefined,
                        }}
                      />
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-xl border border-white/30 bg-white/10 p-4 text-sm text-white/80">
                  No pulse metrics provided.
                </div>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

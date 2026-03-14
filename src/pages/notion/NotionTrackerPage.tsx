/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useMemo, useState } from "react";
import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import ComponentCard from "../../components/common/ComponentCard";
import { useNotionProgress } from "../../hooks/useNotionProgress";
import Chart from "react-apexcharts";
import { ApexOptions } from "apexcharts";
import { NotionModule, NotionSummary } from "../../type/notion";
import { useDispatch } from "react-redux";
import { showToast } from "../../store/slices/toastSlice";

const statusColors: Record<string, string> = {
  completed: "bg-emerald-500/10 text-emerald-600",
  "in progress": "bg-amber-500/10 text-amber-600",
  "in-progress": "bg-amber-500/10 text-amber-600",
  blocked: "bg-rose-500/10 text-rose-600",
  pending: "bg-sky-500/10 text-sky-600",
  "not started": "bg-gray-500/10 text-gray-600",
};

const defaultStatuses = ["Not Started", "In Progress", "Blocked", "Completed"];

const toPercent = (value?: number) => {
  if (value == null || Number.isNaN(value)) return 0;
  return Math.min(100, Math.max(0, Math.round(value)));
};

type SummaryMetric = { label: string; value: number; suffix?: string };

const summaryCards = (
  summary?: NotionSummary,
  modules: NotionModule[] = []
): SummaryMetric[] => {
  const totalItems = summary?.totalItems ?? modules.length;
  const completed = summary?.completedItems ?? modules.filter((m) => (m.status || "").toLowerCase().includes("complete")).length;
  const inProgress = summary?.inProgressItems ?? modules.filter((m) => (m.status || "").toLowerCase().includes("progress")).length;
  const streak = summary?.streakDays ?? 0;

  return [
    { label: "Total items", value: totalItems },
    { label: "Completed", value: completed },
    { label: "In progress", value: inProgress },
    { label: "Streak", value: streak, suffix: "days" },
  ];
};

const buildChartOptions = (percent: number): { options: ApexOptions; series: number[] } => ({
  series: [percent],
  options: {
    chart: {
      type: "radialBar",
      sparkline: { enabled: true },
      height: 200,
    },
    colors: [percent >= 80 ? "#10B981" : percent >= 50 ? "#F59E0B" : "#6366F1"],
    plotOptions: {
      radialBar: {
        startAngle: -90,
        endAngle: 90,
        hollow: { size: "70%" },
        track: { background: "#E5E7EB", strokeWidth: "100%" },
        dataLabels: {
          name: { show: false },
          value: {
            offsetY: -10,
            fontSize: "28px",
            fontWeight: 600,
            formatter: (val) => `${Math.round(Number(val))}%`,
          },
        },
      },
    },
    fill: { type: "gradient", gradient: { shade: "light", type: "horizontal" } },
    stroke: { lineCap: "round" },
    labels: ["Completion"],
  },
});

const StatusBadge: React.FC<{ status?: string }> = ({ status }) => {
  if (!status) return null;
  const key = status.toLowerCase();
  const classes = statusColors[key] || "bg-indigo-500/10 text-indigo-600";
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium capitalize ${classes}`}>
      {status}
    </span>
  );
};

const ProgressBar: React.FC<{ percent: number }> = ({ percent }) => (
  <div className="h-2.5 w-full rounded-full bg-gray-100 dark:bg-gray-800">
    <div
      className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-sky-500 to-emerald-400 transition-all"
      style={{ width: `${percent}%` }}
    />
  </div>
);

export default function NotionTrackerPage() {
  const dispatch = useDispatch();
  const {
    data,
    loading,
    syncing,
    connecting,
    error,
    refresh,
    syncNow,
    updateModule,
    needsAuth,
    statusMessage,
    initiateLogin,
  } = useNotionProgress();
  const summary = data?.summary;
  const modules = data?.modules ?? [];
  const timeline = data?.timeline ?? [];
  const resources = data?.resources ?? [];
  const trackings = data?.trackings ?? [];

  const [expandedModule, setExpandedModule] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const completion = toPercent(summary?.completionRate ?? (summary && summary.totalItems
    ? (summary.completedItems / summary.totalItems) * 100
    : modules.length
    ? (modules.reduce((acc, curr) => acc + (curr.percentComplete ?? 0), 0) / (modules.length * 100)) * 100
    : 0));

  const chart = useMemo(() => buildChartOptions(completion), [completion]);

  const statusOptions = useMemo(() => {
    const dynamicStatuses = Array.from(new Set(modules.map((m) => m.status).filter(Boolean))) as string[];
    const normalized = dynamicStatuses.map((s) => s.trim()).filter(Boolean);
    const merged = Array.from(new Set([...normalized, ...defaultStatuses]));
    return merged.map((label) => ({
      value: label.toLowerCase().replace(/\s+/g, "-"),
      label,
    }));
  }, [modules]);

  const handleModuleUpdate = async (module: NotionModule, field: "status" | "percentComplete", value: string | number) => {
    if (needsAuth) {
      dispatch(showToast({ message: "Connect your Notion account before updating modules.", type: "info" }));
      return;
    }
    try {
      setUpdatingId(module.id);
      const payload: Partial<NotionModule> = {
        status: field === "status" ? value.toString() : module.status,
        percentComplete: field === "percentComplete" ? Number(value) : module.percentComplete,
      };
      await updateModule(module.id, payload);
      dispatch(showToast({ message: "Module updated successfully", type: "success" }));
    } catch (err: any) {
      dispatch(showToast({ message: err?.message || "Failed to update module", type: "error" }));
    } finally {
      setUpdatingId(null);
    }
  };

  const handleSync = async () => {
    if (needsAuth) {
      dispatch(showToast({ message: "Connect your Notion account before syncing.", type: "info" }));
      return;
    }
    try {
      await syncNow();
      dispatch(showToast({ message: "Synced with Notion", type: "success" }));
    } catch (err: any) {
      dispatch(showToast({ message: err?.message || "Failed to sync", type: "error" }));
    }
  };

  const handleRefresh = async () => {
    try {
      await refresh();
      dispatch(showToast({ message: "Progress refreshed", type: "info" }));
    } catch (err: any) {
      dispatch(showToast({ message: err?.message || "Failed to refresh", type: "error" }));
    }
  };

  const handleConnect = async () => {
    await initiateLogin();
    dispatch(showToast({ message: "Continue in the new tab to authorize Notion.", type: "info" }));
  };

  return (
    <div className="space-y-6">
      <PageBreadcrumb pageTitle="Notion Progress Tracker" />

      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Keep learners on track</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Monitor Notion modules, timelines, and resources in one place. Trigger a manual sync or tweak progress inline.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
          >
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
            Refresh Data
          </button>
          <button
            onClick={handleSync}
            disabled={syncing || needsAuth}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-indigo-400"
          >
            {syncing ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            ) : (
              <svg className="h-4 w-4" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path
                  d="M4 4v4h4"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d="M16 16v-4h-4"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d="M6.343 6.343a6 6 0 018.485 0L16 7.515"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
                <path
                  d="M13.657 13.657a6 6 0 01-8.485 0L4 12.485"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
            )}
            Sync Now
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-500/40 dark:bg-rose-500/10 dark:text-rose-100">
          {error}
        </div>
      )}

      {needsAuth && !loading ? (
        <ComponentCard
          title="Connect your Notion workspace"
          desc="Authorize the integration so we can read progress data securely."
          className="border-dashed"
        >
          <div className="space-y-4">
            <p className="text-sm text-gray-600 dark:text-gray-300">
              {statusMessage ||
                "You'll be redirected to Notion to grant access. Once you complete the authorization, return here and press Refresh."}
            </p>
            <button
              onClick={handleConnect}
              disabled={connecting}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-indigo-400"
            >
              {connecting ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path
                    d="M12 5v14m0 0l-4-4m4 4l4-4"
                    stroke="currentColor"
                    strokeWidth="1.6"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M16 9V5H5v14h7"
                    stroke="currentColor"
                    strokeWidth="1.6"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              )}
              Connect Notion
            </button>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Already authorized? Click
              <button className="ml-1 underline" onClick={handleRefresh}>
                Refresh
              </button>
              to load your latest progress.
            </p>
          </div>
        </ComponentCard>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            {loading
              ? Array.from({ length: 4 }).map((_, index) => (
                  <div
                    key={`skeleton-${index}`}
                    className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900"
                  >
                    <div className="space-y-3 animate-pulse">
                      <div className="h-3 w-1/3 rounded bg-gray-200 dark:bg-gray-800" />
                      <div className="h-6 w-1/2 rounded bg-gray-300 dark:bg-gray-700" />
                    </div>
                  </div>
                ))
              : summaryCards(summary, modules).map((metric) => (
                  <div
                    key={metric.label}
                    className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900"
                  >
                    <p className="text-sm uppercase tracking-wide text-gray-500 dark:text-gray-400">
                      {metric.label}
                    </p>
                    <p className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
                      {metric.value}
                      {metric.suffix ? (
                        <span className="ml-1 text-base font-medium text-gray-500 dark:text-gray-400">
                          {metric.suffix}
                        </span>
                      ) : null}
                    </p>
                  </div>
                ))}
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <ComponentCard className="lg:col-span-2" title="Module breakdown" desc="Track each module pulled from Notion.">
              {loading && (
                <div className="space-y-4 animate-pulse">
                  {Array.from({ length: 3 }).map((_, idx) => (
                    <div key={idx} className="rounded-2xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-800 dark:bg-gray-800/40">
                      <div className="h-4 w-1/3 rounded bg-gray-200 dark:bg-gray-700" />
                      <div className="mt-3 h-3 rounded bg-gray-200 dark:bg-gray-700" />
                    </div>
                  ))}
                </div>
              )}

              {!loading && modules.length === 0 && (
                <div className="rounded-xl border border-dashed border-gray-300 bg-white p-8 text-center text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-400">
                  No modules available yet. Sync with Notion to pull the latest content.
                </div>
              )}

              {!loading && modules.length > 0 && (
                <div className="space-y-4">
                  {modules.map((module) => {
                    const percent = toPercent(module.percentComplete);
                    const isExpanded = expandedModule === module.id;
                    return (
                      <div key={module.id} className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm transition hover:shadow-md dark:border-gray-800 dark:bg-gray-900">
                        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                          <div className="space-y-2">
                            <div className="flex flex-wrap items-center gap-2">
                              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{module.title}</h3>
                              <StatusBadge status={module.status} />
                            </div>
                            {module.description && (
                              <p className="text-sm text-gray-500 dark:text-gray-400 line-clamp-2">
                                {module.description}
                              </p>
                            )}
                            <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                              {module.owner && <span>Owner: <span className="font-medium text-gray-700 dark:text-gray-300">{module.owner}</span></span>}
                              {module.dueDate && <span>Due {new Date(module.dueDate).toLocaleDateString()}</span>}
                              {module.lastUpdated && <span>Updated {new Date(module.lastUpdated).toLocaleDateString()}</span>}
                            </div>
                          </div>
                          <div className="flex flex-col items-end gap-3">
                            <button
                              onClick={() => setExpandedModule(isExpanded ? null : module.id)}
                              className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-600 hover:bg-indigo-100 dark:bg-indigo-500/10 dark:text-indigo-300"
                            >
                              {isExpanded ? "Hide controls" : "Update"}
                            </button>
                            {module.notionUrl && (
                              <a
                                href={module.notionUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-300"
                              >
                                Open in Notion
                              </a>
                            )}
                          </div>
                        </div>

                        <div className="mt-4 space-y-3">
                          <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
                            <span>Progress</span>
                            <span className="font-medium text-gray-700 dark:text-gray-200">{percent}%</span>
                          </div>
                          <ProgressBar percent={percent} />
                        </div>

                        {expandedModule === module.id && (
                          <div className="mt-4 grid grid-cols-1 gap-4 rounded-2xl border border-gray-100 bg-gray-50/70 p-4 transition dark:border-gray-800 dark:bg-gray-800/40 md:grid-cols-5">
                            <div className="md:col-span-2">
                              <label className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                                Status
                              </label>
                              <select
                                className="mt-1 w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200 disabled:opacity-70 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200"
                                value={module.status?.toLowerCase().replace(/\s+/g, "-") ?? ""}
                                onChange={(event) => handleModuleUpdate(module, "status", event.target.selectedOptions[0]?.text || event.target.value)}
                                disabled={updatingId === module.id}
                              >
                                {statusOptions.map((option) => (
                                  <option key={option.value} value={option.value}>
                                    {option.label}
                                  </option>
                                ))}
                              </select>
                            </div>
                            <div className="md:col-span-3">
                              <label className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                                Percent complete
                              </label>
                              <div className="mt-2 flex items-center gap-3">
                                <input
                                  type="range"
                                  min={0}
                                  max={100}
                                  step={5}
                                  value={percent}
                                  className="w-full accent-indigo-600"
                                  onChange={(event) => handleModuleUpdate(module, "percentComplete", Number(event.target.value))}
                                  disabled={updatingId === module.id}
                                />
                                <span className="w-10 text-sm font-medium text-gray-700 dark:text-gray-200">{percent}%</span>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </ComponentCard>

            <ComponentCard title="Overall completion" desc="Completion rate across all modules.">
              {loading ? (
                <div className="flex h-full items-center justify-center">
                  <div className="h-12 w-12 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-500" />
                </div>
              ) : (
                <div className="flex flex-col items-center gap-4">
                  <Chart options={chart.options} series={chart.series} type="radialBar" height={240} />
                  <div className="text-center">
                    <p className="text-lg font-semibold text-gray-900 dark:text-white">{completion}% complete</p>
                    {summary?.lastSynced && (
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Last synced {new Date(summary.lastSynced).toLocaleString()}
                      </p>
                    )}
                    {summary?.upcomingDueCount !== undefined && (
                      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                        {summary.upcomingDueCount} upcoming due within 7 days
                      </p>
                    )}
                  </div>
                </div>
              )}
            </ComponentCard>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <ComponentCard className="lg:col-span-2" title="Timeline" desc="Recent milestones and upcoming checkpoints.">
              {loading ? (
                <div className="space-y-3 animate-pulse">
                  {Array.from({ length: 4 }).map((_, idx) => (
                    <div key={idx} className="h-14 rounded-xl bg-gray-100 dark:bg-gray-800" />
                  ))}
                </div>
              ) : timeline.length === 0 ? (
                <div className="rounded-xl border border-dashed border-gray-300 bg-white p-8 text-center text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-400">
                  No timeline events yet.
                </div>
              ) : (
                <ol className="relative space-y-6 border-l border-gray-200 pl-6 dark:border-gray-800">
                  {timeline.map((event) => (
                    <li key={event.id} className="ml-2">
                      <span className="absolute -left-2 flex h-3 w-3 items-center justify-center">
                        <span className="h-3 w-3 rounded-full border-2 border-white bg-indigo-500 dark:border-gray-900" />
                      </span>
                      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900">
                        <div className="flex items-center justify-between">
                          <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{event.title}</h4>
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {new Date(event.date).toLocaleDateString()}
                          </span>
                        </div>
                        {event.description && (
                          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{event.description}</p>
                        )}
                        {event.percentComplete !== undefined && (
                          <div className="mt-3">
                            <ProgressBar percent={toPercent(event.percentComplete)} />
                          </div>
                        )}
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </ComponentCard>

            <ComponentCard title="Resources" desc="Reference docs curated in Notion.">
              {loading ? (
                <div className="space-y-3 animate-pulse">
                  {Array.from({ length: 5 }).map((_, idx) => (
                    <div key={idx} className="h-12 rounded-xl bg-gray-100 dark:bg-gray-800" />
                  ))}
                </div>
              ) : resources.length === 0 ? (
                <div className="rounded-xl border border-dashed border-gray-300 bg-white p-8 text-center text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-400">
                  No resources shared yet.
                </div>
              ) : (
                <ul className="space-y-3">
                  {resources.map((resource) => (
                    <li key={resource.id} className="group rounded-2xl border border-gray-200 bg-white p-4 transition hover:border-indigo-200 hover:shadow-md dark:border-gray-800 dark:bg-gray-900 dark:hover:border-indigo-500/40">
                      <a href={resource.url} target="_blank" rel="noopener noreferrer" className="flex items-start justify-between gap-3">
                        <div>
                          <h4 className="text-sm font-semibold text-gray-900 transition group-hover:text-indigo-600 dark:text-white dark:group-hover:text-indigo-300">
                            {resource.title}
                          </h4>
                          {resource.description && (
                            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
                              {resource.description}
                            </p>
                          )}
                          {resource.type && (
                            <span className="mt-2 inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-[11px] font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-300">
                              {resource.type}
                            </span>
                          )}
                        </div>
                        <svg
                          className="mt-1 h-4 w-4 text-gray-300 group-hover:text-indigo-400 dark:text-gray-600"
                          viewBox="0 0 20 20"
                          fill="currentColor"
                        >
                          <path d="M12.293 2.293a1 1 0 011.414 0L18 6.586V13a1 1 0 01-1 1h-3v-2h2V7.414l-3.293-3.293-5.853 5.853a1 1 0 01-1.414-1.414l5.853-5.853z" />
                          <path d="M5 4a1 1 0 00-1 1v11h11a1 1 0 010 2H3a1 1 0 01-1-1V5a3 3 0 013-3h5a1 1 0 010 2H5z" />
                        </svg>
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </ComponentCard>
          </div>

          {trackings.length > 0 && (
            <ComponentCard title="Target vs actual" desc="Compare actual progress against your target goals.">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {trackings.map((tracking, idx) => {
                  const target = tracking.target ?? 100;
                  const valuePercent = target > 0 ? Math.round((tracking.value / target) * 100) : 0;
                  const capped = Math.max(0, Math.min(100, valuePercent));
                  return (
                    <div key={idx} className="rounded-2xl border border-gray-200 bg-gradient-to-br from-white via-white to-indigo-50 p-4 shadow-sm dark:border-gray-800 dark:from-gray-900 dark:via-gray-900 dark:to-indigo-950/40">
                      <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">{tracking.label}</p>
                      <p className="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">
                        {tracking.value}
                        {tracking.target && (
                          <span className="ml-1 text-sm font-medium text-gray-500 dark:text-gray-400">/ {tracking.target}</span>
                        )}
                      </p>
                      <div className="mt-3">
                        <ProgressBar percent={capped} />
                      </div>
                      <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">{capped}% of target</p>
                    </div>
                  );
                })}
              </div>
            </ComponentCard>
          )}
        </>
      )}
    </div>
  );
}

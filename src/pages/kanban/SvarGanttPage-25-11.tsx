import { useCallback, useEffect, useState } from "react";
import { Gantt, Willow } from "@svar-ui/react-gantt";
import type { IColumnConfig, ILink, ITask } from "@svar-ui/react-gantt";
import "@svar-ui/react-gantt/all.css";
import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import { Actions } from "../../api/userProfile";
import { createBoardDataFromApi, extractKanbanItems } from "./kanbanDataMapper";
import type { BoardData, KanbanTask } from "../../type/kanban";
const screenshotInspiredTasks = [
  { id: 1, text: "Project planning", start: new Date(2024, 3, 2), duration: 16, type: "summary", progress: 65 },
  { id: 2, parent: 1, text: "Marketing analysis", start: new Date(2024, 3, 3), duration: 3, type: "task" },
  { id: 3, parent: 1, text: "Discussions", start: new Date(2024, 3, 6), duration: 2, type: "task" },
  { id: 4, parent: 1, text: "Project management", start: new Date(2024, 3, 2), duration: 10, type: "task" },
  { id: 5, parent: 1, text: "Approval of strategy", start: new Date(2024, 3, 9), duration: 0, type: "milestone" },
  { id: 6, parent: 1, text: "New Task", start: new Date(2024, 3, 3), duration: 1, type: "task" },
  { id: 7, text: "Development", start: new Date(2024, 3, 2), duration: 43, type: "summary", progress: 40 },
  { id: 8, parent: 7, text: "Prototyping", start: new Date(2024, 3, 2), duration: 13, type: "task" },
  { id: 9, parent: 7, text: "Basic functionality", start: new Date(2024, 3, 15), duration: 15, type: "task" },
  { id: 10, parent: 7, text: "Finalizing MVA", start: new Date(2024, 3, 30), duration: 11, type: "task" },
  { id: 11, text: "Testing", start: new Date(2024, 3, 2), duration: 46, type: "summary" },
  { id: 12, parent: 11, text: "Testing prototype", start: new Date(2024, 3, 2), duration: 6, type: "task" },
  { id: 13, parent: 11, text: "Testing basic features", start: new Date(2024, 3, 8), duration: 15, type: "task" },
  { id: 14, parent: 11, text: "Testing MVA", start: new Date(2024, 3, 23), duration: 15, type: "task" },
  { id: 15, parent: 11, text: "Beta testing", start: new Date(2024, 4, 8), duration: 10, type: "task" },
  { id: 16, text: "Release 1.0.0", start: new Date(2024, 4, 25), duration: 0, type: "milestone" },
];

const screenshotInspiredLinks = [
  { id: 1, source: 2, target: 3, type: "e2e" },
  { id: 2, source: 3, target: 4, type: "e2s" },
  { id: 3, source: 4, target: 5, type: "fs" },
  { id: 4, source: 8, target: 9, type: "fs" },
  { id: 5, source: 9, target: 10, type: "fs" },
  { id: 6, source: 12, target: 13, type: "fs" },
  { id: 7, source: 13, target: 14, type: "fs" },
  { id: 8, source: 14, target: 15, type: "fs" },
  { id: 9, source: 15, target: 16, type: "fs" },
];

const DAY_IN_MS = 24 * 60 * 60 * 1000;

type GanttDataState = { tasks: ITask[]; links: ILink[] };
type ColumnFilterOption = { id: string; label: string; count: number };
type GanttDataset = GanttDataState & { filters: ColumnFilterOption[] };

const parseDateValue = (value?: string | null): Date | null => {
  if (!value) {
    return null;
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

const buildFallbackStartDate = (offset: number): Date => {
  const base = new Date();
  base.setDate(base.getDate() + offset);
  return base;
};

const deriveDurationInDays = (start: Date, end?: Date | null): number => {
  if (start && end) {
    const diffMs = end.getTime() - start.getTime();
    if (diffMs > 0) {
      return Math.max(1, Math.ceil(diffMs / DAY_IN_MS));
    }
  }
  return 1;
};

const ensureEndDate = (start: Date, end?: Date | null, duration?: number): Date => {
  if (end) {
    return end;
  }
  const copy = new Date(start.getTime());
  const safeDuration = Math.max(1, Math.ceil(duration ?? 1));
  copy.setDate(copy.getDate() + safeDuration);
  return copy;
};


const mapKanbanTaskToSvarTask = (
  task: KanbanTask,
  fallbackOffset: number,
  parentId?: string,
  columnId?: string,
  columnTitle?: string
): ITask => {
  const explicitStart = parseDateValue(task.startDate) ?? parseDateValue(task.endDate);
  const fallbackStart = parseDateValue(task.dueDate) ?? buildFallbackStartDate(fallbackOffset);
  const start = explicitStart ?? fallbackStart;
  const explicitEnd = parseDateValue(task.endDate) ?? parseDateValue(task.dueDate);
  const duration = deriveDurationInDays(start, explicitEnd);
  const end = ensureEndDate(start, explicitEnd, duration);

  return {
    id: task.id,
    text: task.title,
    parent: parentId,
    start,
    end,
    duration,
    type: "task",
    progress: typeof task.progress === "number" ? task.progress : undefined,
    details: task.description,
    assignee: task.assignee,
    priority: task.priority,
    status: task.status,
    tags: task.tags,
    columnId,
    columnTitle,
  };
};

const mapChildEntryToSvarTask = (
  child: { id: string | number; name: string },
  parentTask: ITask,
  fallbackOffset: number
): ITask => {
  const start = parentTask.start instanceof Date ? new Date(parentTask.start) : buildFallbackStartDate(fallbackOffset);
  const end = parentTask.end instanceof Date ? new Date(parentTask.end) : ensureEndDate(start, null, parentTask.duration);
  const duration = deriveDurationInDays(start, end);

  return {
    id: `${parentTask.id}-sub-${child.id ?? fallbackOffset}`,
    parent: parentTask.id,
    text: child.name ?? `Subtask ${fallbackOffset + 1}`,
    start,
    end,
    duration,
    type: "task",
    columnId: parentTask.columnId,
    columnTitle: parentTask.columnTitle,
  };
};


const createLinksForColumn = (childTasks: ITask[]): ILink[] => {
  if (childTasks.length < 2) {
    return [];
  }
  const sorted = [...childTasks].sort((a, b) => {
    const aTime = a.start instanceof Date ? a.start.getTime() : 0;
    const bTime = b.start instanceof Date ? b.start.getTime() : 0;
    if (aTime === bTime) {
      return String(a.id ?? "").localeCompare(String(b.id ?? ""));
    }
    return aTime - bTime;
  });

  const links: ILink[] = [];
  for (let index = 1; index < sorted.length; index += 1) {
    const previous = sorted[index - 1];
    const current = sorted[index];
    if (!previous.id || !current.id) {
      continue;
    }
    links.push({
      source: previous.id,
      target: current.id,
      type: "e2s",
    });
  }
  return links;
};

const mapBoardToSvarGantt = (boardData: BoardData): GanttDataset => {
  const mappedTasks: ITask[] = [];
  const mappedLinks: ILink[] = [];
  const filters: ColumnFilterOption[] = [];

  boardData.columnOrder.forEach((columnId) => {
    const column = boardData.columns[columnId];
    if (!column) {
      return;
    }

    const columnTasks: ITask[] = [];

    column.taskIds.forEach((taskId, index) => {
      const kanbanTask = boardData.tasks[taskId];
      if (!kanbanTask) {
        return;
      }

      const task = mapKanbanTaskToSvarTask(kanbanTask, index, undefined, column.id, column.title);
      mappedTasks.push(task);
      columnTasks.push(task);

      if (kanbanTask.children?.length) {
        kanbanTask.children.forEach((child, childIndex) => {
          const subTask = mapChildEntryToSvarTask(child, task, childIndex);
          mappedTasks.push(subTask);
        });
      }
    });

    filters.push({ id: column.id, label: column.title, count: columnTasks.length });
    mappedLinks.push(...createLinksForColumn(columnTasks));
  });

  return { tasks: mappedTasks, links: mappedLinks, filters };
};

const buildFallbackGanttData = (): GanttDataset => {
  const fallbackTasks: ITask[] = screenshotInspiredTasks.map((task) => ({
    ...task,
    columnId: "sample",
    columnTitle: "Sample data",
  }));

  const fallbackLinks: ILink[] = screenshotInspiredLinks.map((link) => ({
    ...link,
    type: link.type === "fs" ? ("e2s" as ILink["type"]) : (link.type as ILink["type"]),
  }));

  const rootTaskCount = fallbackTasks.filter((task) => !task.parent).length || fallbackTasks.length;

  return {
    tasks: fallbackTasks,
    links: fallbackLinks,
    filters: [{ id: "sample", label: "Sample data", count: rootTaskCount }],
  };
};

const applyColumnFilter = (dataset: GanttDataset | null, filterId: string): GanttDataState => {
  if (!dataset) {
    return { tasks: [], links: [] };
  }
  if (filterId === "all") {
    return { tasks: dataset.tasks, links: dataset.links };
  }

  const filteredTasks = dataset.tasks.filter((task) => task.columnId === filterId);
  const allowedIds = new Set(filteredTasks.map((task) => String(task.id)));
  const filteredLinks = dataset.links.filter(
    (link) => allowedIds.has(String(link.source)) && allowedIds.has(String(link.target))
  );

  return { tasks: filteredTasks, links: filteredLinks };
};

const ganttDateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
});

const formatDate = (value?: Date) => (value ? ganttDateFormatter.format(value) : "-");

const ganttColumns: IColumnConfig[] = [
  { id: "text", header: "Task name", flexgrow: 1, sort: true },
  {
    id: "start",
    header: "Start date",
    width: 140,
    align: "center",
    sort: true,
    template: (task: ITask) => formatDate(task.start),
  },
  {
    id: "duration",
    header: "Duration",
    width: 110,
    align: "center",
    template: (task: ITask) => (task.duration ? `${task.duration} d` : "-"),
  },
  {
    id: "add-task",
    header: "",
    width: 48,
    align: "center",
    resize: false,
  },
];

type ScalePresetKey = "month" | "week";
type ScaleConfig = { unit: string; step: number; format: string };

const scalePresets: Record<ScalePresetKey, ScaleConfig[]> = {
  month: [
    { unit: "month", step: 1, format: "MMMM yyyy" },
    { unit: "day", step: 1, format: "d" },
  ],
  week: [
    { unit: "week", step: 1, format: "'Week' w" },
    { unit: "day", step: 1, format: "EEE d" },
  ],
};

const scaleButtons: Array<{ id: ScalePresetKey; label: string }> = [
  { id: "month", label: "Month" },
  { id: "week", label: "Week" },
];

const SvarGanttPage: React.FC = () => {
  const [fullDataset, setFullDataset] = useState<GanttDataset | null>(null);
  const [visibleData, setVisibleData] = useState<GanttDataState>({ tasks: [], links: [] });
  const [columnFilters, setColumnFilters] = useState<ColumnFilterOption[]>([]);
  const [selectedColumnFilter, setSelectedColumnFilter] = useState<string>("all");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [usingFallback, setUsingFallback] = useState<boolean>(false);
  const [scalePreset, setScalePreset] = useState<ScalePresetKey>("month");
  const [ganttKey, setGanttKey] = useState<number>(0);
  const activeScales = scalePresets[scalePreset];

  const fetchGanttTasks = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const response = await Actions();
      if (!response || response.status !== 200) {
        throw new Error("Request failed");
      }

      const items = extractKanbanItems(response);
      if (!items.length) {
        setFetchError("No Kanban actions available. Showing sample data.");
        const fallback = buildFallbackGanttData();
        setFullDataset(fallback);
        setColumnFilters(fallback.filters);
        setUsingFallback(true);
        return;
      }

      const boardData = createBoardDataFromApi(items);
      const mapped = mapBoardToSvarGantt(boardData);
      if (!mapped.tasks.length) {
        setFetchError("No schedulable tasks were returned. Showing sample data.");
        const fallback = buildFallbackGanttData();
        setFullDataset(fallback);
        setColumnFilters(fallback.filters);
        setUsingFallback(true);
        return;
      }

      setFullDataset(mapped);
      setColumnFilters(mapped.filters);
      setUsingFallback(false);
    } catch (error) {
      console.error("Failed to fetch gantt tasks", error);
      setFetchError("Unable to load tasks from the API. Showing sample data.");
      const fallback = buildFallbackGanttData();
      setFullDataset(fallback);
      setColumnFilters(fallback.filters);
      setUsingFallback(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGanttTasks();
  }, [fetchGanttTasks]);

  useEffect(() => {
    if (!fullDataset) {
      setVisibleData({ tasks: [], links: [] });
      return;
    }
    setVisibleData(applyColumnFilter(fullDataset, selectedColumnFilter));
  }, [fullDataset, selectedColumnFilter]);

  useEffect(() => {
    setGanttKey((prev) => prev + 1);
  }, [selectedColumnFilter]);

  useEffect(() => {
    if (selectedColumnFilter === "all") {
      return;
    }
    const isValid = columnFilters.some((option) => option.id === selectedColumnFilter);
    if (!isValid) {
      setSelectedColumnFilter("all");
    }
  }, [columnFilters, selectedColumnFilter]);

  const totalTaskCount = fullDataset?.tasks.length ?? 0;
  const filterOptions: ColumnFilterOption[] = [
    { id: "all", label: "All tasks", count: totalTaskCount },
    ...columnFilters,
  ];

  return (
    <div className="space-y-6">
      <PageBreadcrumb pageTitle="SVAR React Gantt" />

      <section className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900/70">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Classic timeline view</h1>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
              This layout mirrors the official SVAR demo: tree grid on the left, fully interactive bars on the right,
              and default plus buttons for adding work items directly inside the chart.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            <span className="rounded-full bg-gray-100 px-3 py-1 dark:bg-gray-800">Drag & drop</span>
            <span className="rounded-full bg-gray-100 px-3 py-1 dark:bg-gray-800">Dependencies</span>
            <span className="rounded-full bg-gray-100 px-3 py-1 dark:bg-gray-800">Milestones</span>
          </div>
        </div>

        <div className="mt-5 rounded-2xl border border-gray-200 bg-gray-50/70 dark:border-gray-800 dark:bg-gray-900">
          <div className="flex flex-col gap-4 border-b border-gray-100 px-4 py-3 text-sm dark:border-gray-800 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex flex-col gap-2">
              <div className="flex flex-wrap gap-2">
                {scaleButtons.map((button) => (
                  <button
                    key={button.id}
                    type="button"
                    onClick={() => setScalePreset(button.id)}
                    className={`rounded-full px-4 py-1 font-semibold transition ${
                      scalePreset === button.id
                        ? "bg-indigo-600 text-white shadow-sm"
                        : "border border-gray-300 text-gray-600 hover:border-indigo-300 hover:text-indigo-600 dark:border-gray-700 dark:text-gray-300"
                    }`}
                  >
                    {button.label}
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap gap-2">
                {filterOptions.map((option) => {
                  const isActive = selectedColumnFilter === option.id;
                  const isDisabled = option.id !== "all" && option.count === 0;
                  return (
                    <button
                      key={option.id}
                      type="button"
                      onClick={() => setSelectedColumnFilter(option.id)}
                      disabled={isDisabled}
                      className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide transition ${
                        isActive
                          ? "border-indigo-500 bg-indigo-50 text-indigo-700 dark:border-indigo-400 dark:bg-indigo-900/30 dark:text-indigo-200"
                          : "border-gray-300 text-gray-600 hover:border-indigo-300 hover:text-indigo-600 dark:border-gray-700 dark:text-gray-300"
                      } ${isDisabled ? "cursor-not-allowed opacity-60" : ""}`}
                    >
                      {option.label}
                      <span className="ml-2 rounded-full bg-white/60 px-2 py-0.5 text-[11px] font-bold text-gray-600 dark:bg-gray-800/60 dark:text-gray-200">
                        {option.count}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
            <div className="flex flex-col items-start gap-2 text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400 lg:items-end">
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={fetchGanttTasks}
                  disabled={isLoading}
                  className="inline-flex items-center gap-2 rounded-full bg-indigo-600 px-4 py-1.5 font-semibold text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-indigo-400"
                >
                  {isLoading ? "Loading…" : "Sync with API"}
                </button>
                
              </div>
              <div className="text-[11px] font-semibold normal-case">
                {isLoading && <span className="text-gray-600 dark:text-gray-300">Fetching tasks from API…</span>}
                {!isLoading && fetchError && (
                  <span className="text-rose-600 dark:text-rose-400">{fetchError}</span>
                )}
                {!isLoading && !fetchError && usingFallback && (
                  <span className="text-amber-600 dark:text-amber-400">Showing fallback dataset</span>
                )}
                {!isLoading && !fetchError && !usingFallback && visibleData.tasks.length > 0 && (
                  <span className="text-emerald-600 dark:text-emerald-400">
                    Live data loaded ({visibleData.tasks.length} tasks)
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="min-h-screen overflow-y-auto overflow-x-hidden rounded-b-2xl">
            <Willow>
              <Gantt key={ganttKey} tasks={visibleData.tasks} links={visibleData.links} columns={ganttColumns} scales={activeScales} />
            </Willow>
          </div>
        </div>
      </section>
    </div>
  );
};

export default SvarGanttPage;

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Gantt, Willow } from "@svar-ui/react-gantt";
import type { IApi, IColumnConfig, ILink, ITask } from "@svar-ui/react-gantt";
import "@svar-ui/react-gantt/all.css";
import PageBreadcrumb from "../../../components/common/PageBreadCrumb";
import KanbanTaskModal from "../../utils/kanban/KanbanTaskModal";
import type { TaskFormEditableField, TaskFormState, TranslationFormEntry } from "../kanban/taskFormTypes";
import { Actions, patchAction } from "../../../api/userProfile";
import { createBoardDataFromApi, createEmptyBoardData, extractKanbanItems } from "../kanban/kanbanDataMapper";
import type { BoardData, KanbanTask } from "../kanban/type/kanban";
import {
  DEFAULT_LANGUAGE_ORDER,
  DEFAULT_DIFFICULTY,
  DEFAULT_PROGRESS,
  DIFFICULTY_OPTIONS,
  FALLBACK_COLUMN_ID,
  PRIORITY_TO_VALUE,
  PROGRESS_OPTIONS,
  calculateDueDate,
  createInitialTaskFormState,
  createTranslationEntriesFromTask,
  createTranslationEntry,
  extendNumericOptionStrings,
  findNextLanguageCode,
  getLanguageLabel,
  normalizeIncomingDateValue,
  normalizeLanguageCode,
  normalizeNumericSelectValue,
  priorityOptions,
  toTimestampMilliseconds,
  updateTaskFormState,
} from "./GanttPage";
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

const COLUMN_COLOR_RULES: Array<{ keywords: string[]; color: string }> = [
  { keywords: ["backlog", "todo", "idea"], color: "#0ea5e9" },
  { keywords: ["progress", "inprogress", "doing"], color: "#f59e0b" },
  { keywords: ["review", "qa", "test"], color: "#8b5cf6" },
  { keywords: ["complete", "completed", "done"], color: "#10b981" },
];

const DEFAULT_COLUMN_COLOR = "#94a3b8"; // slate-400

const normalizeHexColor = (color?: string | null): string | null => {
  if (!color) {
    return null;
  }
  const trimmed = color.trim();
  if (/^#?[0-9a-fA-F]{6}$/.test(trimmed)) {
    return trimmed.startsWith("#") ? trimmed : `#${trimmed}`;
  }
  return null;
};

type ParsedHexColor = { normalized: string; r: number; g: number; b: number };

const parseHexColor = (color: string): ParsedHexColor | null => {
  const normalized = normalizeHexColor(color);
  if (!normalized) {
    return null;
  }
  return {
    normalized,
    r: parseInt(normalized.slice(1, 3), 16),
    g: parseInt(normalized.slice(3, 5), 16),
    b: parseInt(normalized.slice(5, 7), 16),
  };
};

const applyAlphaToColor = (color: string, alpha: number): string => {
  const parsed = parseHexColor(color);
  if (!parsed) {
    return color;
  }
  const clampedAlpha = Math.min(1, Math.max(0, alpha));
  const { r, g, b } = parsed;
  return `rgba(${r}, ${g}, ${b}, ${clampedAlpha})`;
};

const combineClassNames = (
  ...classes: Array<string | false | null | undefined>
) => classes.filter(Boolean).join(" ");

const resolveColumnColor = (value?: string | null): string => {
  if (!value) {
    return DEFAULT_COLUMN_COLOR;
  }
  const normalized = value.toLowerCase();
  const condensed = normalized.replace(/[\s_-]+/g, "");
  for (const rule of COLUMN_COLOR_RULES) {
    const hasMatch = rule.keywords.some((keyword) => {
      const condensedKeyword = keyword.replace(/[\s_-]+/g, "");
      return normalized.includes(keyword) || condensed.includes(condensedKeyword);
    });
    if (hasMatch) {
      return rule.color;
    }
  }
  return DEFAULT_COLUMN_COLOR;
};

type RgbChannels = { r: number; g: number; b: number };

const getRgbChannels = (color: string): RgbChannels | null => {
  const parsed = parseHexColor(color);
  if (!parsed) {
    return null;
  }
  const { r, g, b } = parsed;
  return { r, g, b };
};

const getRelativeLuminance = ({ r, g, b }: RgbChannels): number => {
  const normalizeChannel = (value: number) => {
    const channel = value / 255;
    return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  };
  const rLum = normalizeChannel(r);
  const gLum = normalizeChannel(g);
  const bLum = normalizeChannel(b);
  return 0.2126 * rLum + 0.7152 * gLum + 0.0722 * bLum;
};

const pickReadableTextColor = (background: string): string => {
  const channels = getRgbChannels(background);
  if (!channels) {
    return "#0f172a";
  }
  const luminance = getRelativeLuminance(channels);
  return luminance > 0.45 ? "#0f172a" : "#ffffff";
};

const mixHexColors = (source: string, target: string, ratio: number): string => {
  const sourceChannels = getRgbChannels(source);
  const targetChannels = getRgbChannels(target);
  if (!sourceChannels || !targetChannels) {
    return source;
  }
  const clampedRatio = Math.min(1, Math.max(0, ratio));
  const mixChannel = (base: number, mix: number) => Math.round(base * (1 - clampedRatio) + mix * clampedRatio);
  const r = mixChannel(sourceChannels.r, targetChannels.r);
  const g = mixChannel(sourceChannels.g, targetChannels.g);
  const b = mixChannel(sourceChannels.b, targetChannels.b);
  return `rgb(${r}, ${g}, ${b})`;
};

const lightenColor = (color: string, amount: number) => mixHexColors(color, "#ffffff", amount);
const darkenColor = (color: string, amount: number) => mixHexColors(color, "#000000", amount);

const DAY_IN_MS = 24 * 60 * 60 * 1000;

type GanttDataState = { tasks: ITask[]; links: ILink[] };
type ColumnFilterOption = { id: string; label: string; count: number; color?: string };
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

const toProgressPercentage = (value?: number | null): number => {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return 0;
  }
  if (value >= 0 && value <= 1) {
    return Math.round(value * 100);
  }
  return Math.round(Math.max(0, Math.min(100, value)));
};

const toProgressRatio = (value?: number | null): number | undefined => {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return undefined;
  }
  if (value > 1) {
    return Math.max(0, Math.min(1, value / 100));
  }
  return Math.max(0, Math.min(1, value));
};

const padTwoDigits = (value: number) => value.toString().padStart(2, "0");

const formatDateTimeLocal = (date: Date): string =>
  `${date.getFullYear()}-${padTwoDigits(date.getMonth() + 1)}-${padTwoDigits(date.getDate())}T${padTwoDigits(
    date.getHours()
  )}:${padTwoDigits(date.getMinutes())}`;

const createFallbackEndFromStart = (startValue: string): string => {
  if (!startValue) {
    return "";
  }
  const parsed = new Date(startValue);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }
  const adjusted = new Date(parsed.getTime());
  adjusted.setHours(adjusted.getHours() + 1);
  return formatDateTimeLocal(adjusted);
};


const mapKanbanTaskToSvarTask = (
  task: KanbanTask,
  fallbackOffset: number,
  parentId?: string,
  columnId?: string,
  columnTitle?: string
): ITask => {
  const explicitStart = parseDateValue(task.dt_start as any) ?? parseDateValue(task.dt_expected as any);
  const fallbackStart = parseDateValue(task.dt_deadline as any) ?? buildFallbackStartDate(fallbackOffset);
  const start = explicitStart ?? fallbackStart;
  const explicitEnd = parseDateValue(task.dt_expected as any) ?? parseDateValue(task.dt_deadline as any);
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
    progress: toProgressRatio(task.progress),
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

  boardData.column_order.forEach((columnId) => {
    const column = boardData.columns[columnId];
    if (!column) {
      return;
    }

    const columnTasks: ITask[] = [];

    column.task_ids.forEach((taskId, index) => {
      const kanbanTask = boardData.tasks[taskId];
      if (!kanbanTask) {
        return;
      }

      const columnColor = resolveColumnColor(column.title);
      const parentId = kanbanTask.refs?.links?.parent;
      const task = mapKanbanTaskToSvarTask(kanbanTask, index, parentId, column.id, column.title);
      if (columnColor) {
        (task as unknown as { color?: string; progressColor?: string }).color = columnColor;
        (task as unknown as { color?: string; progressColor?: string }).progressColor = columnColor;
      }
      mappedTasks.push(task);
      columnTasks.push(task);

      if (kanbanTask.children?.length) {
        kanbanTask.children.forEach((child, childIndex) => {
          const subTask = mapChildEntryToSvarTask(child, task, childIndex);
          mappedTasks.push(subTask);
        });
      }
    });

    const columnColor = resolveColumnColor(column.title);
    filters.push({ id: column.id, label: column.title, count: columnTasks.length, color: columnColor });
    mappedLinks.push(...createLinksForColumn(columnTasks));
  });

  return { tasks: mappedTasks, links: mappedLinks, filters };
};

const buildFallbackGanttData = (): GanttDataset => {
  const fallbackColor = resolveColumnColor("sample");
  const fallbackTasks: ITask[] = screenshotInspiredTasks.map((task) => ({
    ...task,
    columnId: "sample",
    columnTitle: "Sample data",
    color: fallbackColor,
    progressColor: fallbackColor,
    progress: toProgressRatio(task.progress),
  })) as unknown as ITask[];

  const fallbackLinks: ILink[] = screenshotInspiredLinks.map((link) => ({
    ...link,
    type: link.type === "fs" ? ("e2s" as ILink["type"]) : (link.type as ILink["type"]),
  }));

  const rootTaskCount = fallbackTasks.filter((task) => !task.parent).length || fallbackTasks.length;

  return {
    tasks: fallbackTasks,
    links: fallbackLinks,
    filters: [{ id: "sample", label: "Sample data", count: rootTaskCount, color: fallbackColor }],
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

type TaskWithColor = ITask & {
  color?: string;
  progressColor?: string;
  columnId?: string | number | null;
  columnTitle?: string | null;
};

type TaskColorInfo = {
  color: string;
  textColor: string;
  type?: ITask["type"];
};

const GANTT_COLOR_EVENT_TAG = "gantt-column-colors";

const SvarGanttPage: React.FC = () => {
  const [board, setBoard] = useState<BoardData>(() => createEmptyBoardData());
  const [fullDataset, setFullDataset] = useState<GanttDataset | null>(null);
  const [visibleData, setVisibleData] = useState<GanttDataState>({ tasks: [], links: [] });
  const [columnFilters, setColumnFilters] = useState<ColumnFilterOption[]>([]);
  const [selectedColumnFilter, setSelectedColumnFilter] = useState<string>("all");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [usingFallback, setUsingFallback] = useState<boolean>(false);
  const [scalePreset, setScalePreset] = useState<ScalePresetKey>("month");
  const [ganttKey, setGanttKey] = useState<number>(0);
  const [isEditModalOpen, setIsEditModalOpen] = useState<boolean>(false);
  const [editingTask, setEditingTask] = useState<KanbanTask | null>(null);
  const [editTaskState, setEditTaskState] = useState<TaskFormState>(() => createInitialTaskFormState(FALLBACK_COLUMN_ID));
  const [isSavingEdit, setIsSavingEdit] = useState<boolean>(false);
  const [editModalError, setEditModalError] = useState<string | null>(null);
  const [editLanguagePickerOpen, setEditLanguagePickerOpen] = useState<boolean>(false);
  const [editLanguageSelection, setEditLanguageSelection] = useState<string>("");
  const [editCustomLanguage, setEditCustomLanguage] = useState<string>("");
  const [editLanguagePickerError, setEditLanguagePickerError] = useState<string | null>(null);
  const activeScales = scalePresets[scalePreset];
  const ganttContainerRef = useRef<HTMLDivElement | null>(null);
  const ganttApiRef = useRef<IApi | null>(null);
  const taskColorMapRef = useRef<Map<string, TaskColorInfo>>(new Map());
  const progressUpdateQueueRef = useRef<Set<string>>(new Set());
  const pendingProgressPayloadRef = useRef<Map<string, Record<string, unknown>>>(new Map());
  const progressDebounceTimersRef = useRef<Map<string, number>>(new Map());
  const sequenceUpdateQueueRef = useRef<Set<string>>(new Set());
  const pendingSequencePayloadRef = useRef<Map<string, Record<string, unknown>>>(new Map());
  const sequenceDebounceTimersRef = useRef<Map<string, number>>(new Map());

  const scheduleProgressUpdate = useCallback(
    (taskId: string, progressValue: number) => {
      setBoard((currentBoard) => {
        const kanbanTask = currentBoard.tasks[taskId];
        if (!kanbanTask) {
          return currentBoard;
        }

        const payload: Record<string, unknown> = {
          model_name: "action",
          id: kanbanTask.id,
          "prefs.userdefined.progress": {
            mode: "update",
            value: progressValue,
          },
        };

        pendingProgressPayloadRef.current.set(taskId, payload);
        progressUpdateQueueRef.current.add(taskId);

        const existingTimer = progressDebounceTimersRef.current.get(taskId);
        if (existingTimer) {
          window.clearTimeout(existingTimer);
        }

        const timer = window.setTimeout(() => {
          progressDebounceTimersRef.current.delete(taskId);
          if (!progressUpdateQueueRef.current.has(taskId)) {
            return;
          }

          const queued = pendingProgressPayloadRef.current.get(taskId);
          if (!queued) {
            progressUpdateQueueRef.current.delete(taskId);
            return;
          }

          patchAction(queued as any)
            .then(() => {
              console.log("Progress updated successfully for task", taskId, "to", progressValue);
              progressUpdateQueueRef.current.delete(taskId);
              pendingProgressPayloadRef.current.delete(taskId);
            })
            .catch((error) => {
              console.error("Failed to update progress for task", taskId, error);
              progressUpdateQueueRef.current.delete(taskId);
              pendingProgressPayloadRef.current.delete(taskId);
            });
        }, 400);

        progressDebounceTimersRef.current.set(taskId, timer);

        return currentBoard;
      });
    },
    []
  );

  const updateLocalTaskSequence = useCallback((taskId: string, sequenceValue: number) => {
    setBoard((prev) => {
      const existingTask = prev.tasks[taskId];
      if (!existingTask) {
        return prev;
      }
      return {
        ...prev,
        tasks: {
          ...prev.tasks,
          [taskId]: { ...existingTask, sequence: sequenceValue },
        },
      };
    });

    setFullDataset((prev) => {
      if (!prev) {
        return prev;
      }
      const updatedTasks = prev.tasks.map((task) =>
        String(task.id) === taskId ? { ...task, sequence: sequenceValue } : task
      );
      return { ...prev, tasks: updatedTasks };
    });
  }, []);

  const scheduleSequenceUpdate = useCallback(
    (taskId: string, sequenceValue: number) => {
      // Use callback to get current board state
      setBoard((currentBoard) => {
        const kanbanTask = currentBoard.tasks[taskId];
        if (!kanbanTask) {
          return currentBoard;
        }

        const payload: Record<string, unknown> = {
          model_name: "action",
          id: kanbanTask.id,
          sequence: {
            mode: "update",
            value: sequenceValue,
          },
        };

        pendingSequencePayloadRef.current.set(taskId, payload);
        sequenceUpdateQueueRef.current.add(taskId);

        const existingTimer = sequenceDebounceTimersRef.current.get(taskId);
        if (existingTimer) {
          window.clearTimeout(existingTimer);
        }

        const timer = window.setTimeout(() => {
          sequenceDebounceTimersRef.current.delete(taskId);
          if (!sequenceUpdateQueueRef.current.has(taskId)) {
            return;
          }

          const queued = pendingSequencePayloadRef.current.get(taskId);
          if (!queued) {
            sequenceUpdateQueueRef.current.delete(taskId);
            return;
          }

          patchAction(queued as any)
            .then(() => {
              console.log("Sequence updated successfully for task", taskId, "to", sequenceValue);
              sequenceUpdateQueueRef.current.delete(taskId);
              pendingSequencePayloadRef.current.delete(taskId);
            })
            .catch((error) => {
              console.error("Failed to update sequence for task", taskId, error);
              sequenceUpdateQueueRef.current.delete(taskId);
              pendingSequencePayloadRef.current.delete(taskId);
            });
        }, 400);

        sequenceDebounceTimersRef.current.set(taskId, timer);

        return currentBoard; // Don't modify board here
      });
    },
    []
  );

  const resolveDefaultColumnId = useCallback(
     () => board.column_order[0] ?? FALLBACK_COLUMN_ID,
     [board.column_order]
  );

  const columnOptions = useMemo(
    () =>
      board.column_order
        .map((columnId) => board.columns[columnId])
        .filter((column): column is NonNullable<(typeof board.columns)[string]> => Boolean(column))
        .map((column) => ({ id: column.id, title: column.title })),
    [board]
  );

  const editDifficultyOptions = useMemo(
    () => extendNumericOptionStrings(DIFFICULTY_OPTIONS, editTaskState.difficulty),
    [editTaskState.difficulty]
  );

  const editProgressOptions = useMemo(
    () => extendNumericOptionStrings(PROGRESS_OPTIONS, editTaskState.progress),
    [editTaskState.progress]
  );

  const languageOptions = useMemo(() => {
    const codes = new Set<string>(DEFAULT_LANGUAGE_ORDER);
    Object.values(board.tasks).forEach((task) => {
      if (!task) {
        return;
      }
      task.language_codes?.forEach((code) => codes.add(normalizeLanguageCode(code)));
      Object.keys(task.title_translations ?? {}).forEach((code) => codes.add(normalizeLanguageCode(code)));
      Object.keys(task.description_translations ?? {}).forEach((code) => codes.add(normalizeLanguageCode(code)));
    });

    const orderedCodes = Array.from(codes).sort((a, b) => {
      const aIndex = DEFAULT_LANGUAGE_ORDER.indexOf(a);
      const bIndex = DEFAULT_LANGUAGE_ORDER.indexOf(b);
      if (aIndex === -1 && bIndex === -1) return a.localeCompare(b);
      if (aIndex === -1) return 1;
      if (bIndex === -1) return -1;
      return aIndex - bIndex;
    });

    return orderedCodes.map((code) => ({ value: code, label: getLanguageLabel(code) }));
  }, [board]);

  const updateEditTranslations = useCallback(
    (updater: (current: TranslationFormEntry[]) => TranslationFormEntry[]) => {
      setEditTaskState((prev) => ({
        ...prev,
        translations: updater(prev.translations),
      }));
    },
    []
  );

  const deriveFormStateFromTask = useCallback(
    (task: KanbanTask, overrides?: Partial<TaskFormState>): TaskFormState => {
      const taskColumn = Object.values(board.columns).find((column) => column?.taskIds.includes(task.id));
       const normalizedStart = normalizeIncomingDateValue(task.dt_start);
       const normalizedEnd = normalizeIncomingDateValue(task.dt_expected ?? task.dt_end);
       const normalizedDue = normalizeIncomingDateValue(task.dt_deadline);
      const shouldFallbackStart = !normalizedStart && !normalizedEnd && !normalizedDue;
      const resolvedStartDate = shouldFallbackStart ? formatDateTimeLocal(new Date()) : normalizedStart;
      const resolvedEndDate = normalizedEnd || createFallbackEndFromStart(resolvedStartDate);
      const resolvedDueDate = normalizedDue || calculateDueDate(resolvedStartDate, resolvedEndDate);
      const normalizedDifficulty = normalizeNumericSelectValue(
        task.difficulty ?? PRIORITY_TO_VALUE[task.priority],
        DEFAULT_DIFFICULTY
      );
      const normalizedProgressValue = toProgressPercentage(task.progress);
      const normalizedProgress = normalizeNumericSelectValue(normalizedProgressValue, DEFAULT_PROGRESS);

       return {
         translations: createTranslationEntriesFromTask(task),
         columnId: taskColumn?.id ?? resolveDefaultColumnId(),
         priority: task.priority,
          dt_deadline: resolvedDueDate,
          dt_start: resolvedStartDate,
          dt_expected: resolvedEndDate,
         assignee: task.assignee || task.assignedTo?.[0]?.name || "",
         difficulty: normalizedDifficulty,
         progress: normalizedProgress,
         percent_complete: normalizedProgress,
         ...overrides,
       } as TaskFormState;
    },
    [board.columns, resolveDefaultColumnId]
  );

  const handleEditTranslationFieldChange = useCallback(
    (entryId: string, field: "language" | "title" | "description", value: string) => {
      updateEditTranslations((current) =>
        current.map((entry) => {
          if (entry.id !== entryId) {
            return entry;
          }

          if (field === "language") {
            const normalized = normalizeLanguageCode(value);
            if (!normalized) {
              return { ...entry, language: normalized };
            }
            const duplicate = current.some(
              (other) => other.id !== entryId && normalizeLanguageCode(other.language) === normalized
            );
            if (duplicate) {
              return entry;
            }
            return { ...entry, language: normalized };
          }

          return { ...entry, [field]: value };
        })
      );
    },
    [updateEditTranslations]
  );

  const handleAddEditTranslation = useCallback(
    (explicitLanguage?: string): { success: boolean; error?: string } => {
      const used = new Set<string>(
        editTaskState.translations
          .map((translation) => normalizeLanguageCode(translation.language))
          .filter(Boolean)
      );

      let languageToUse = explicitLanguage ? normalizeLanguageCode(explicitLanguage) : "";
      if (languageToUse && used.has(languageToUse)) {
        return { success: false, error: "Language already added." };
      }

      if (!languageToUse) {
        languageToUse = findNextLanguageCode(used, languageOptions);
      }

      updateEditTranslations((current) => [...current, createTranslationEntry(languageToUse)]);
      return { success: true };
    },
    [editTaskState.translations, languageOptions, updateEditTranslations]
  );

  const handleRemoveEditTranslation = useCallback(
    (entryId: string) => {
      if (editTaskState.translations.length <= 1) {
        return;
      }
      updateEditTranslations((current) => current.filter((entry) => entry.id !== entryId));
    },
    [editTaskState.translations.length, updateEditTranslations]
  );

  const availableEditLanguages = useMemo(() => {
    const used = new Set(
      editTaskState.translations
        .map((translation) => normalizeLanguageCode(translation.language))
        .filter(Boolean)
    );
    return languageOptions.filter((option) => !used.has(option.value));
  }, [editTaskState.translations, languageOptions]);

  const handleEditLanguagePickerToggle = useCallback(() => {
    setEditLanguagePickerError(null);
    setEditLanguagePickerOpen((prev) => {
      const next = !prev;
      if (next) {
        if (availableEditLanguages.length > 0) {
          setEditLanguageSelection("");
          setEditCustomLanguage("");
        } else {
          setEditLanguageSelection("__custom");
          setEditCustomLanguage("");
        }
      }
      return next;
    });
  }, [availableEditLanguages.length]);

  const handleEditLanguageSelectionChange = useCallback((value: string) => {
    setEditLanguageSelection(value);
    if (value !== "__custom") {
      setEditCustomLanguage("");
    }
    setEditLanguagePickerError(null);
  }, []);

  const handleEditLanguageCustomChange = useCallback((value: string) => {
    setEditCustomLanguage(value);
    setEditLanguagePickerError(null);
  }, []);

  const handleEditLanguagePickerSubmit = useCallback(() => {
    const selection = editLanguageSelection === "__custom" ? editCustomLanguage.trim() : editLanguageSelection;
    if (!selection) {
      setEditLanguagePickerError("Choose a language before adding.");
      return;
    }
    const result = handleAddEditTranslation(selection);
    if (!result.success) {
      setEditLanguagePickerError(result.error ?? "Unable to add language.");
      return;
    }
    setEditLanguagePickerOpen(false);
    setEditLanguageSelection("");
    setEditCustomLanguage("");
  }, [editCustomLanguage, editLanguageSelection, handleAddEditTranslation]);

  const handleEditLanguagePickerCancel = useCallback(() => {
    setEditLanguagePickerOpen(false);
    setEditLanguageSelection("");
    setEditCustomLanguage("");
    setEditLanguagePickerError(null);
  }, []);

  const editLanguagePickerState = {
    isOpen: editLanguagePickerOpen,
    selection: editLanguageSelection,
    customValue: editCustomLanguage,
    error: editLanguagePickerError,
  };

  const handleEditTaskChange = useCallback(
    (field: TaskFormEditableField, value: string) => {
      setEditTaskState((prev) => updateTaskFormState(prev, field, value));
    },
    []
  );

  const buildEditActionPayload = useCallback(
    (state: TaskFormState, baseTask: KanbanTask | null): { payload: Record<string, unknown> } | { error: string } => {
      if (!baseTask) {
        return { error: "No task selected for editing." };
      }

      const normalized = new Map<string, { title: string; description: string }>();

      state.translations.forEach((entry) => {
        const language = normalizeLanguageCode(entry.language);
        if (!language) {
          return;
        }
        const current = normalized.get(language) ?? { title: "", description: "" };
        const title = entry.title.trim();
        const description = entry.description.trim();
        normalized.set(language, {
          title: title || current.title,
          description: description || current.description,
        });
      });

      const hasTitle = Array.from(normalized.values()).some((value) => value.title.length > 0);
      if (!hasTitle) {
        return { error: "Add at least one language with a title." };
      }

      const translationFields: Record<string, { mode: string; value: string | string[] }> = {};

      normalized.forEach((value, language) => {
        translationFields[`action.${language}`] = {
          mode: "update",
          value: value.title || "",
        };
        translationFields[`description.${language}`] = {
          mode: "update",
          value: value.description || "",
        };
      });

      translationFields.languages = {
        mode: "update",
        value: Array.from(normalized.keys()),
      };

      const column = board.columns[state.columnId] ?? board.columns[FALLBACK_COLUMN_ID];
      const assignedTo = state.assignee
        ? [{ name: state.assignee }]
        : baseTask.assignedTo?.map((assignment) => ({ name: assignment.name })) ?? [];

       const dueTimestamp = toTimestampMilliseconds(state.dt_deadline);
       const startTimestamp = toTimestampMilliseconds(state.dt_start);
       const endTimestamp = toTimestampMilliseconds(state.dt_expected);
      const resolvedProgress = Number(state.progress) || 0;

      const payloadItem: Record<string, unknown> = {
        model_name: "action",
        ...translationFields,
        kanban_column: {
          mode: "update",
          value: column?.title ?? "Uncategorized",
        },
        kanban_column_id: {
          mode: "update",
          value: column?.id ?? FALLBACK_COLUMN_ID,
        },
        priority: {
          mode: "update",
          value: PRIORITY_TO_VALUE[state.priority],
        },
        difficulty: {
          mode: "update",
          value: Number(state.difficulty) || PRIORITY_TO_VALUE[state.priority],
        },
        status: {
          mode: "update",
          value: baseTask.status ?? "In progress",
        },
        dt_deadline: {
          mode: "update",
          value: dueTimestamp,
        },
        dt_start: {
          mode: "update",
          value: startTimestamp,
        },
         dt_expected: {
           mode: "update",
           value: endTimestamp,
         },
        assigned_to: {
          mode: "update",
          value: assignedTo,
        },
        progress: {
          mode: "update",
          value: resolvedProgress,
        },
        id: baseTask.id,
      };

      if (!state.assignee && assignedTo.length === 0) {
        delete payloadItem.assigned_to;
      }

      return { payload: payloadItem };
    },
    [board.columns]
  );

  const handleOpenEditModal = useCallback(
    (task: KanbanTask | null) => {
      if (!task || usingFallback) {
        return;
      }
      setEditingTask(task);
      setEditTaskState(deriveFormStateFromTask(task));
      setEditModalError(null);
      setEditLanguagePickerOpen(false);
      setEditLanguageSelection("");
      setEditCustomLanguage("");
      setEditLanguagePickerError(null);
      setIsEditModalOpen(true);
    },
    [deriveFormStateFromTask, usingFallback]
  );

  const handleCloseEditModal = useCallback(() => {
    setIsEditModalOpen(false);
    setEditingTask(null);
    setEditModalError(null);
    setEditLanguagePickerOpen(false);
    setEditLanguageSelection("");
    setEditCustomLanguage("");
    setEditLanguagePickerError(null);
    setEditTaskState(createInitialTaskFormState(resolveDefaultColumnId()));
  }, [resolveDefaultColumnId]);


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
        setBoard(createEmptyBoardData());
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
        setBoard(createEmptyBoardData());
        return;
      }

      setBoard(boardData);
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
      setBoard(createEmptyBoardData());
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleEditTaskSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!editingTask || isSavingEdit) {
        return;
      }

      setEditModalError(null);
      const result = buildEditActionPayload(editTaskState, editingTask);

      if ("error" in result) {
        setEditModalError(result.error);
        return;
      }

      try {
        setIsSavingEdit(true);
        const response = await patchAction(result.payload);
        if (response?.status !== 200 && response?.status !== 201) {
          throw new Error("Failed to update task.");
        }
        await fetchGanttTasks();
        handleCloseEditModal();
      } catch (error) {
        console.error("Failed to update kanban task", error);
        const message =
          (error as any)?.response?.data?.message ||
          (error as any)?.message ||
          "Unable to update task. Please try again.";
        setEditModalError(message);
      } finally {
        setIsSavingEdit(false);
      }
    },
    [buildEditActionPayload, editTaskState, editingTask, fetchGanttTasks, handleCloseEditModal, isSavingEdit]
  );

  // Track last click to distinguish between single and double clicks
  const lastClickRef = useRef<{ id: string; time: number } | null>(null);

  const handleShowEditor = useCallback(
    (event?: { id?: string | number }) => {
      if (!event?.id || usingFallback) {
        return false;
      }
      
      const resolvedId = String(event.id);
      const now = Date.now();
      const lastClick = lastClickRef.current;
      
      // Check if this is a double-click (within 300ms of last click on same task)
      const isDoubleClick = 
        lastClick && 
        lastClick.id === resolvedId && 
        now - lastClick.time < 300;
      
      if (isDoubleClick) {
        // Reset click tracking
        lastClickRef.current = null;
        
        // Open modal on double-click
        const targetTask = board.tasks[resolvedId];
        if (targetTask) {
          handleOpenEditModal(targetTask);
        }
      } else {
        // Track this click
        lastClickRef.current = { id: resolvedId, time: now };
      }
      
      return false;
    },
    [board.tasks, handleOpenEditModal, usingFallback]
  );

  const handleSvarUpdateTask = useCallback(
    (event: { id?: string | number; task?: Partial<ITask>; inProgress?: boolean }) => {
      if (!event?.id || !event?.task || usingFallback) {
        return;
      }

      // Only process when drag is complete (inProgress === false)
      if (event.inProgress) {
        return;
      }

      const taskId = String(event.id);
      const updatedTask = event.task;

      // Handle progress changes
      if (typeof updatedTask.progress === "number") {
        const progressPercentage = toProgressPercentage(updatedTask.progress);
        console.log("Progress changed for task", taskId, "to", progressPercentage);
        
        // Update fullDataset to persist the change
        setFullDataset((prev) => {
          if (!prev) {
            return prev;
          }
          const updatedTasks = prev.tasks.map((task) =>
            String(task.id) === taskId ? { ...task, progress: updatedTask.progress } : task
          );
          return { ...prev, tasks: updatedTasks };
        });

        // Update board state
        setBoard((prev) => {
          const existingTask = prev.tasks[taskId];
          if (!existingTask) {
            return prev;
          }
          return {
            ...prev,
            tasks: {
              ...prev.tasks,
              [taskId]: { ...existingTask, progress: progressPercentage },
            },
          };
        });

        // Trigger background API call
        scheduleProgressUpdate(taskId, progressPercentage);
      }
    },
    [scheduleProgressUpdate, usingFallback]
  );

  const handleSvarMoveTask = useCallback(
    (event: { id?: string | number; mode?: string; target?: string | number; source?: number; inProgress?: boolean }) => {
      console.log("onMoveTask triggered:", event);
      
      if (!event?.id || usingFallback) {
        console.log("Move rejected - no id or using fallback");
        return false;
      }

      const taskId = String(event.id);
      const targetId = event.target ? String(event.target) : null;
      
      // Calculate new index and reorder
      setFullDataset((prev) => {
        if (!prev) {
          return prev;
        }
        
        const tasks = [...prev.tasks];
        const currentIdx = tasks.findIndex((t) => String(t.id) === taskId);
        if (currentIdx === -1) {
          console.log("Task not found in dataset");
          return prev;
        }

        // Calculate target index based on mode and target
        let newIndex: number;
        if (targetId) {
          const targetIdx = tasks.findIndex((t) => String(t.id) === targetId);
          if (targetIdx === -1) {
            console.log("Target task not found");
            return prev;
          }
          // 'after' means insert after target, 'before' means insert before target
          newIndex = event.mode === 'after' ? targetIdx + 1 : targetIdx;
          // Adjust if current task is before target
          if (currentIdx < targetIdx) {
            newIndex--;
          }
        } else {
          newIndex = typeof event.source === 'number' ? event.source : currentIdx;
        }

        console.log("Moving task", taskId, "from index", currentIdx, "to", newIndex);

        const [moved] = tasks.splice(currentIdx, 1);
        const clampedIndex = Math.max(0, Math.min(tasks.length, newIndex));
        tasks.splice(clampedIndex, 0, moved);

        // Update sequence and trigger API call
        const newSequence = clampedIndex;
        console.log("Scheduling sequence update to:", newSequence);
        
        // Schedule the API call
        setTimeout(() => {
          updateLocalTaskSequence(taskId, newSequence);
          scheduleSequenceUpdate(taskId, newSequence);
        }, 0);

        return { ...prev, tasks };
      });

      return true;
    },
    [scheduleSequenceUpdate, updateLocalTaskSequence, usingFallback]
  );

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

  const filterButtonBaseClasses = "rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide transition";
  const filterCountBaseClasses = "ml-2 rounded-full px-2 py-0.5 text-[11px] font-bold";

  const refreshTaskColorCache = useCallback(() => {
    const nextMap = new Map<string, TaskColorInfo>();
    visibleData.tasks.forEach((task) => {
      if (!task?.id) {
        return;
      }
      const taskId = String(task.id);
      const taskColor = (task as TaskWithColor).color ?? resolveColumnColor(task.columnTitle ?? task.columnId?.toString());
      if (!taskColor) {
        return;
      }
      nextMap.set(taskId, {
        color: taskColor,
        textColor: pickReadableTextColor(taskColor),
        type: task.type,
      });
    });
    taskColorMapRef.current = nextMap;
  }, [visibleData.tasks]);

  const resetTaskBarStyles = useCallback((bar: HTMLElement) => {
    const styleKeys = [
      "--wx-gantt-task-color",
      "--wx-gantt-task-fill-color",
      "--wx-gantt-task-font-color",
      "--wx-gantt-task-border-color",
      "--wx-gantt-task-border",
      "--wx-gantt-summary-color",
      "--wx-gantt-summary-fill-color",
      "--wx-gantt-summary-font-color",
      "--wx-gantt-summary-border-color",
      "--wx-gantt-summary-border",
      "--wx-gantt-milestone-color",
      "--wx-gantt-progress-border-color",
    ];
    styleKeys.forEach((key) => {
      bar.style.removeProperty(key);
    });
    bar.style.removeProperty("background-color");
    bar.style.removeProperty("border-color");
    const contentElement = bar.querySelector<HTMLElement>(".wx-content");
    if (contentElement) {
      contentElement.style.removeProperty("color");
    }
    const progressElement = bar.querySelector<HTMLElement>(".wx-progress-percent");
    if (progressElement) {
      progressElement.style.removeProperty("background-color");
    }
    const markerElement = bar.querySelector<HTMLElement>(".wx-progress-marker");
    if (markerElement) {
      markerElement.style.removeProperty("background-color");
      markerElement.style.removeProperty("border-color");
    }
  }, []);

  const applyColorsToChart = useCallback(() => {
    const container = ganttContainerRef.current;
    if (!container) {
      return;
    }
    const colorMap = taskColorMapRef.current;
    if (!colorMap.size) {
      return;
    }

    const bars = container.querySelectorAll<HTMLElement>(".wx-bar[data-id]");
    bars.forEach((bar) => {
      const identifier = bar.getAttribute("data-id");
      if (!identifier) {
        resetTaskBarStyles(bar);
        return;
      }
      const taskInfo = colorMap.get(identifier);
      if (!taskInfo) {
        resetTaskBarStyles(bar);
        return;
      }

      const { color, textColor } = taskInfo;
      const progressElement = bar.querySelector<HTMLElement>(".wx-progress-percent");
      const markerElement = bar.querySelector<HTMLElement>(".wx-progress-marker");
      const contentElement = bar.querySelector<HTMLElement>(".wx-content");
      const isSummary = bar.classList.contains("wx-summary");
      const isTask = bar.classList.contains("wx-task");
      const isMilestone = bar.classList.contains("wx-milestone");
      const progressFillColor = lightenColor(color, 0.5);
      const summaryFillColor = lightenColor(color, 0.35);
      const borderAccentColor = darkenColor(color, 0.25);
      const markerAccentColor = darkenColor(color, 0.15);

      if (isMilestone) {
        bar.style.setProperty("--wx-gantt-milestone-color", color);
        bar.style.backgroundColor = color;
        bar.style.borderColor = color;
      } else if (isSummary) {
        bar.style.setProperty("--wx-gantt-summary-color", color);
        bar.style.setProperty("--wx-gantt-summary-fill-color", summaryFillColor);
        bar.style.setProperty("--wx-gantt-summary-border-color", borderAccentColor);
        bar.style.setProperty("--wx-gantt-summary-border", `1px solid ${borderAccentColor}`);
        bar.style.setProperty("--wx-gantt-summary-font-color", textColor);
      } else if (isTask) {
        bar.style.setProperty("--wx-gantt-task-color", color);
        bar.style.setProperty("--wx-gantt-task-fill-color", progressFillColor);
        bar.style.setProperty("--wx-gantt-task-border-color", borderAccentColor);
        bar.style.setProperty("--wx-gantt-task-border", `1px solid ${borderAccentColor}`);
        bar.style.setProperty("--wx-gantt-task-font-color", textColor);
      } else {
        bar.style.backgroundColor = color;
        bar.style.borderColor = color;
      }

      if (contentElement) {
        contentElement.style.color = textColor;
      }

      if (progressElement) {
        progressElement.style.backgroundColor = progressFillColor;
      }

      if (markerElement) {
        markerElement.style.backgroundColor = markerAccentColor;
        markerElement.style.borderColor = borderAccentColor;
      }

      bar.style.setProperty("--wx-gantt-progress-border-color", markerAccentColor);
    });
  }, [resetTaskBarStyles]);

  const scheduleColorRefresh = useCallback(() => {
    if (typeof window === "undefined") {
      return;
    }
    window.requestAnimationFrame(() => {
      applyColorsToChart();
    });
  }, [applyColorsToChart]);

  useEffect(() => {
    refreshTaskColorCache();
    scheduleColorRefresh();
  }, [refreshTaskColorCache, scheduleColorRefresh]);

  useEffect(() => {
    return () => {
      if (ganttApiRef.current) {
        ganttApiRef.current.detach(GANTT_COLOR_EVENT_TAG);
      }
    };
  }, []);

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
                  const isAllFilter = option.id === "all";
                  const accentColor = !isAllFilter ? option.color : undefined;

                  const buttonClassName = combineClassNames(
                    filterButtonBaseClasses,
                    isDisabled ? "cursor-not-allowed opacity-60" : undefined,
                    !accentColor
                      ? isActive
                        ? "border-indigo-500 bg-indigo-50 text-indigo-700 dark:border-indigo-400 dark:bg-indigo-900/30 dark:text-indigo-200"
                        : "border-gray-300 text-gray-600 hover:border-indigo-300 hover:text-indigo-600 dark:border-gray-700 dark:text-gray-300"
                      : undefined,
                    accentColor ? "shadow-sm" : undefined,
                    accentColor && isActive ? "text-white" : undefined,
                    accentColor && !isActive ? "text-gray-700 dark:text-gray-200" : undefined
                  );

                  const buttonStyle = accentColor
                    ? {
                        borderColor: accentColor,
                        backgroundColor: isActive
                          ? accentColor
                          : applyAlphaToColor(accentColor, isDisabled ? 0.08 : 0.12),
                        color: isActive ? "#ffffff" : accentColor,
                      }
                    : undefined;

                  const countClassName = combineClassNames(
                    filterCountBaseClasses,
                    accentColor
                      ? undefined
                      : "bg-white/60 text-gray-600 dark:bg-gray-800/60 dark:text-gray-200",
                    accentColor && isActive ? "text-white" : undefined
                  );

                  const countStyle = accentColor
                    ? {
                        backgroundColor: isActive
                          ? applyAlphaToColor("#ffffff", 0.25)
                          : applyAlphaToColor(accentColor, 0.2),
                        color: isActive ? "#ffffff" : accentColor,
                      }
                    : undefined;

                  return (
                    <button
                      key={option.id}
                      type="button"
                      onClick={() => setSelectedColumnFilter(option.id)}
                      disabled={isDisabled}
                      className={buttonClassName}
                      style={buttonStyle}
                    >
                      {option.label}
                      <span className={countClassName} style={countStyle}>
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
            <div ref={ganttContainerRef}>
              <Willow>
                <Gantt
                  key={ganttKey}
                  tasks={visibleData.tasks}
                  links={visibleData.links}
                  columns={ganttColumns}
                  scales={activeScales}
                  onShowEditor={handleShowEditor}
                  onItemDoubleClick={handleShowEditor}
                  onMoveTask={handleSvarMoveTask}
                  onUpdateTask={handleSvarUpdateTask}
                  init={(api) => {
                    ganttApiRef.current = api;
                    api.detach(GANTT_COLOR_EVENT_TAG);
                    const rerender = () => scheduleColorRefresh();
                    api.on("render-data", rerender, { tag: GANTT_COLOR_EVENT_TAG });
                    api.on("update-task", rerender, { tag: GANTT_COLOR_EVENT_TAG });
                    api.on("add-task", rerender, { tag: GANTT_COLOR_EVENT_TAG });
                    api.on("delete-task", rerender, { tag: GANTT_COLOR_EVENT_TAG });
                    scheduleColorRefresh();
                  }}
                />
              </Willow>
            </div>
          </div>
        </div>
      </section>

      <KanbanTaskModal
        mode="edit"
        isOpen={isEditModalOpen && Boolean(editingTask)}
        title="Edit task"
        description="Update task details and keep the SVAR timeline in sync."
        isSaving={isSavingEdit}
        submitLabel={isSavingEdit ? "Saving…" : "Save changes"}
        onClose={handleCloseEditModal}
        onSubmit={handleEditTaskSubmit}
        modalError={editModalError}
        formState={editTaskState}
        onFieldChange={handleEditTaskChange}
        columnOptions={columnOptions}
        priorityOptions={priorityOptions}
        difficultyOptions={editDifficultyOptions}
        progressOptions={editProgressOptions}
        translations={editTaskState.translations}
        onTranslationFieldChange={(entryId, field, value) =>
          handleEditTranslationFieldChange(entryId, field as "language" | "title" | "description", value)
        }
        onRemoveTranslation={handleRemoveEditTranslation}
        languagePickerOptions={availableEditLanguages}
        languagePickerState={editLanguagePickerState}
        onLanguagePickerToggle={handleEditLanguagePickerToggle}
        onLanguageSelectionChange={handleEditLanguageSelectionChange}
        onLanguageCustomChange={handleEditLanguageCustomChange}
        onLanguagePickerSubmit={handleEditLanguagePickerSubmit}
        onLanguagePickerCancel={handleEditLanguagePickerCancel}
        currentTask={editingTask}
      />
    </div>
  );
};

export default SvarGanttPage;

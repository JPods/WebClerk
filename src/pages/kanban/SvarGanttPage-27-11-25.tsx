import { CSSProperties, FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Gantt, Willow } from "@svar-ui/react-gantt";
import type { IColumnConfig, ILink, ITask } from "@svar-ui/react-gantt";
import "@svar-ui/react-gantt/all.css";
import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import clsx from "clsx";
import KanbanTaskModal from "../../components/kanban/KanbanTaskModal";
import type { TaskFormEditableField, TaskFormState, TranslationFormEntry } from "../../apps/utils/kanban/taskFormTypes";
import { Actions, patchAction } from "../../api/userProfile";
import { createBoardDataFromApi, createEmptyBoardData, extractKanbanItems } from "./kanbanDataMapper";
import type { BoardData, KanbanTask, TaskPriority } from "../../type/kanban";
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
  priorityColors,
  priorityOptions,
  toTimestampMilliseconds,
  updateTaskFormState,
} from "./KanbanGanttPage";
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

const fallbackPriorityCycle: TaskPriority[] = ["low", "medium", "high", "critical"];

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
  const fallbackTasks: ITask[] = screenshotInspiredTasks.map((task, index) => ({
    ...task,
    columnId: "sample",
    columnTitle: "Sample data",
    priority: fallbackPriorityCycle[index % fallbackPriorityCycle.length],
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

const COLUMN_COLOR_PALETTE: readonly string[] = [
  "#0ea5e9", // sky-500
  "#6366f1", // indigo-500
  "#10b981", // emerald-500
  "#f59e0b", // amber-500
  "#f43f5e", // rose-500
  "#a855f7", // purple-500
  "#06b6d4", // cyan-500
  "#d946ef", // fuchsia-500
];

const COLUMN_KEYWORD_COLOR_RULES: Array<{ keywords: string[]; color: string }> = [
  { keywords: ["backlog", "todo", "idea"], color: "#0ea5e9" },
  { keywords: ["inprogress", "progress", "doing"], color: "#f59e0b" },
  { keywords: ["review", "qa", "testing"], color: "#8b5cf6" },
  { keywords: ["complete", "completed", "done", "launch"], color: "#10b981" },
];

const DEFAULT_COLUMN_ACCENT_COLOR = "#94a3b8"; // slate-400

const resolvePaletteIndex = (input: string): number => {
  if (!input) {
    return 0;
  }
  let hash = 0;
  for (let index = 0; index < input.length; index += 1) {
    hash = (hash + input.charCodeAt(index) * (index + 1)) % COLUMN_COLOR_PALETTE.length;
  }
  return hash;
};

const resolveKeywordColorMatch = (value?: string | null): string | null => {
  if (!value) {
    return null;
  }
  const normalized = value.toLowerCase();
  const condensed = normalized.replace(/[\s_-]+/g, "");
  for (const rule of COLUMN_KEYWORD_COLOR_RULES) {
    const hasMatch = rule.keywords.some((keyword) => {
      const keywordCondensed = keyword.replace(/[\s_-]+/g, "");
      return normalized.includes(keyword) || condensed.includes(keywordCondensed);
    });
    if (hasMatch) {
      return rule.color;
    }
  }
  return null;
};

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

const applyAlphaToColor = (color: string, alphaHex: string): string => {
  const normalized = normalizeHexColor(color);
  if (!normalized) {
    return color;
  }
  const hex = normalized.replace("#", "");
  return `#${hex}${alphaHex}`;
};

const createFilterButtonStyles = (color: string, isActive: boolean): CSSProperties => {
  const normalized = normalizeHexColor(color);
  if (!normalized) {
    return {};
  }
  if (isActive) {
    return {
      backgroundColor: normalized,
      borderColor: normalized,
      color: "#ffffff",
    };
  }
  return {
    backgroundColor: applyAlphaToColor(normalized, "22"),
    borderColor: applyAlphaToColor(normalized, "55"),
    color: normalized,
  };
};

const createFilterCountStyles = (color: string, isActive: boolean): CSSProperties => {
  const normalized = normalizeHexColor(color);
  if (!normalized) {
    return {};
  }
  if (isActive) {
    return {
      backgroundColor: "rgba(255,255,255,0.25)",
      color: "#ffffff",
    };
  }
  return {
    backgroundColor: applyAlphaToColor(normalized, "33"),
    color: normalized,
  };
};

const createTaskBarStyles = (color: string): CSSProperties => {
  const normalized = normalizeHexColor(color);
  if (!normalized) {
    return {};
  }
  return {
    backgroundColor: normalized,
    borderColor: normalized,
    color: "#ffffff",
    boxShadow: `0 2px 6px ${applyAlphaToColor(normalized, "55")}`,
  };
};

interface TaskTemplateProps {
  data: ITask;
  onaction?: (event: { action: string; data: Record<string, unknown> }) => void;
}

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
  const progressUpdateQueueRef = useRef<Set<string>>(new Set());

  const resolveDefaultColumnId = useCallback(
    () => board.columnOrder[0] ?? FALLBACK_COLUMN_ID,
    [board.columnOrder]
  );

  const columnOptions = useMemo(
    () =>
      board.columnOrder
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
      task.languageCodes?.forEach((code) => codes.add(normalizeLanguageCode(code)));
      Object.keys(task.titleTranslations ?? {}).forEach((code) => codes.add(normalizeLanguageCode(code)));
      Object.keys(task.descriptionTranslations ?? {}).forEach((code) => codes.add(normalizeLanguageCode(code)));
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
    (updater: (current: TranslationFormEntry[]) => TranslationFormEntry[] ) => {
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
      const normalizedStart = normalizeIncomingDateValue(task.startDate);
      const normalizedEnd = normalizeIncomingDateValue(task.endDate);
      const normalizedDue = normalizeIncomingDateValue(task.dueDate);
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
        dueDate: normalizedDue || calculateDueDate(normalizedStart, normalizedEnd),
        startDate: normalizedStart,
        endDate: normalizedEnd,
        assignee: task.assignee || task.assignedTo?.[0]?.name || "",
        difficulty: normalizedDifficulty,
        progress: normalizedProgress,
        ...overrides,
      };
    },
    [board.columns, resolveDefaultColumnId]
  );

  const columnColorMap = useMemo(() => {
    const map = new Map<string, string>();
    board.columnOrder.forEach((columnId, index) => {
      const column = board.columns[columnId];
      const keywordColor = resolveKeywordColorMatch(column?.title ?? columnId);
      const fallbackColor = COLUMN_COLOR_PALETTE[index % COLUMN_COLOR_PALETTE.length];
      map.set(columnId, keywordColor ?? fallbackColor);
    });
    return map;
  }, [board]);

  const getColumnAccentColor = useCallback(
    (columnId?: string | number | null) => {
      if (!columnId) {
        return DEFAULT_COLUMN_ACCENT_COLOR;
      }
      const normalized = String(columnId);
      const mapped = columnColorMap.get(normalized);
      if (mapped) {
        return mapped;
      }
      const fallbackIndex = resolvePaletteIndex(normalized);
      return COLUMN_COLOR_PALETTE[fallbackIndex] ?? DEFAULT_COLUMN_ACCENT_COLOR;
    },
    [columnColorMap]
  );

  const updateLocalTaskProgress = useCallback((taskId: string, progressValue: number) => {
    const progressRatio = toProgressRatio(progressValue) ?? 0;
    setBoard((prev) => {
      const existingTask = prev.tasks[taskId];
      if (!existingTask) {
        return prev;
      }
      return {
        ...prev,
        tasks: {
          ...prev.tasks,
          [taskId]: { ...existingTask, progress: progressValue },
        },
      };
    });

    setFullDataset((prev) => {
      if (!prev) {
        return prev;
      }
      const updatedTasks = prev.tasks.map((task) =>
        String(task.id) === taskId ? { ...task, progress: progressRatio } : task
      );
      return { ...prev, tasks: updatedTasks };
    });

    setVisibleData((prev) => ({
      tasks: prev.tasks.map((task) =>
        String(task.id) === taskId ? { ...task, progress: progressRatio } : task
      ),
      links: prev.links,
    }));
  }, []);

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

      const dueTimestamp = toTimestampMilliseconds(state.dueDate);
      const startTimestamp = toTimestampMilliseconds(state.startDate);
      const endTimestamp = toTimestampMilliseconds(state.endDate);
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
        dt_due: {
          mode: "update",
          value: dueTimestamp,
        },
        dt_start: {
          mode: "update",
          value: startTimestamp,
        },
        dt_end: {
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
      setBoard(boardData);
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

  const handleSvarTaskDoubleClick = useCallback(
    (taskIdentifier: ITask["id"]) => {
      if (usingFallback || !taskIdentifier) {
        return;
      }
      const resolvedId = String(taskIdentifier);
      const targetTask = board.tasks[resolvedId];
      if (targetTask) {
        handleOpenEditModal(targetTask);
      }
    },
    [board.tasks, handleOpenEditModal, usingFallback]
  );

  const TaskBarTemplate = useCallback(
    ({ data }: TaskTemplateProps) => {
      const priorityCandidate = data.priority as TaskPriority;
      const resolvedPriority = priorityOptions.includes(priorityCandidate) ? priorityCandidate : "medium";
      const progressValue = toProgressPercentage(data.progress);
      const columnAccentColor = getColumnAccentColor(data.columnId);
      const taskBarStyle = createTaskBarStyles(columnAccentColor);

      return (
        <div
          className="flex h-full w-full flex-col justify-center gap-1 rounded-lg border px-2 py-1 text-white"
          style={taskBarStyle}
          onDoubleClick={(event) => {
            event.stopPropagation();
            handleSvarTaskDoubleClick(data.id);
          }}
        >
          <div className="flex items-center justify-end gap-2">
            <span className="rounded-full bg-white/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide">
              {resolvedPriority}
            </span>
          </div>
          <div className="flex flex-col gap-1 text-[10px] font-semibold">
            <div className="relative flex-1 overflow-hidden rounded-md bg-white/25">
              <div
                className={clsx("absolute left-0 top-0 h-full", priorityColors[resolvedPriority])}
                style={{ width: `${progressValue}%` }}
              />
              <div className="relative z-10 flex h-10 w-full items-center justify-center px-2 text-center text-xs font-semibold uppercase tracking-wide leading-tight">
                <p className="w-full break-words text-center leading-tight">{data.text}</p>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold">Progress</span>
              <span className="text-[11px] font-semibold">{progressValue}%</span>
            </div>
          </div>
        </div>
      );
    },
    [getColumnAccentColor, handleSvarTaskDoubleClick]
  );

  const handleShowEditor = useCallback(
    (event?: { id?: string | number }) => {
      if (!event?.id) {
        return false;
      }
      handleSvarTaskDoubleClick(event.id);
      return false;
    },
    [handleSvarTaskDoubleClick]
  );

  const handleSvarTaskUpdate = useCallback(
    (event?: {
      id?: string | number;
      task?: Partial<ITask>;
      inProgress?: boolean;
      eventSource?: string;
    }) => {
      if (!event || usingFallback || event.inProgress) {
        return;
      }

      const taskId = event.id !== undefined ? String(event.id) : "";
      if (!taskId) {
        return;
      }

      const updatedProgress = event.task?.progress;
      if (typeof updatedProgress !== "number") {
        return;
      }

      const targetTask = board.tasks[taskId];
      if (!targetTask) {
        return;
      }

      const normalizedProgress = toProgressPercentage(updatedProgress);
      const previousProgress =
        typeof targetTask.progress === "number"
          ? Math.max(0, Math.min(100, Math.round(targetTask.progress)))
          : 0;

      if (normalizedProgress === previousProgress) {
        return;
      }

      updateLocalTaskProgress(taskId, normalizedProgress);

      const updatedTask: KanbanTask = { ...targetTask, progress: normalizedProgress };
      const derivedState = deriveFormStateFromTask(updatedTask, {
        progress: String(normalizedProgress),
      });
      const payloadResult = buildEditActionPayload(derivedState, updatedTask);
      if ("error" in payloadResult) {
        console.warn("Unable to sync task progress", payloadResult.error);
        return;
      }

      const syncProgress = async () => {
        if (progressUpdateQueueRef.current.has(taskId)) {
          return;
        }
        progressUpdateQueueRef.current.add(taskId);
        try {
          await patchAction(payloadResult.payload);
        } catch (error) {
          console.error("Failed to sync task progress", error);
        } finally {
          progressUpdateQueueRef.current.delete(taskId);
        }
      };

      void syncProgress();
    },
    [
      board.tasks,
      buildEditActionPayload,
      deriveFormStateFromTask,
      updateLocalTaskProgress,
      usingFallback,
    ]
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

  return (
    <div className="space-y-6 svar-kanban-gantt">
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
                  const accentColor = !isAllFilter ? getColumnAccentColor(option.id) : null;
                  const buttonStyle = accentColor ? createFilterButtonStyles(accentColor, isActive) : undefined;
                  const countStyle = accentColor ? createFilterCountStyles(accentColor, isActive) : undefined;
                  return (
                    <button
                      key={option.id}
                      type="button"
                      onClick={() => setSelectedColumnFilter(option.id)}
                      disabled={isDisabled}
                      style={buttonStyle}
                      className={clsx(
                        "rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide transition",
                        {
                          "cursor-not-allowed opacity-60": isDisabled,
                        },
                        isAllFilter
                          ? isActive
                            ? "border-indigo-500 bg-indigo-50 text-indigo-700 dark:border-indigo-400 dark:bg-indigo-900/30 dark:text-indigo-200"
                            : "border-gray-300 text-gray-600 hover:border-indigo-300 hover:text-indigo-600 dark:border-gray-700 dark:text-gray-300"
                          : "border-transparent text-gray-700 dark:text-gray-200"
                      )}
                    >
                      {option.label}
                      <span
                        className={clsx(
                          "ml-2 rounded-full px-2 py-0.5 text-[11px] font-bold",
                          isAllFilter &&
                            "bg-white/60 text-gray-600 dark:bg-gray-800/60 dark:text-gray-200"
                        )}
                        style={countStyle}
                      >
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
              <Gantt
                key={ganttKey}
                tasks={visibleData.tasks}
                links={visibleData.links}
                columns={ganttColumns}
                scales={activeScales}
                taskTemplate={TaskBarTemplate}
                onShowEditor={handleShowEditor}
                onUpdateTask={handleSvarTaskUpdate}
              />
            </Willow>
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
        languageOptions={languageOptions}
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

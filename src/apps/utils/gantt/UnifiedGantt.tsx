/**
 * UnifiedGantt - Core Gantt chart component
 * 
 * Supports both single-project and multi-project modes.
 * Can be embedded in other pages or used standalone.
 * 
 * TODO: Type cleanup needed - this file uses patterns from the legacy
 * MultiProjectGanttPage that have evolved out of sync with current type
 * definitions. See kanban/type/kanban.ts and kanban/taskFormTypes.ts.
 */
// @ts-nocheck - Temporary: types need alignment with current definitions

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { format as dateFnsFormat } from "date-fns";
import { Gantt, Willow } from "@svar-ui/react-gantt";
import type { IApi, IColumnConfig, ITask } from "@svar-ui/react-gantt";
import "@svar-ui/react-gantt/all.css";
import KanbanTaskModal from "../kanban/KanbanTaskModal";
import type { TaskFormEditableField, TaskFormState } from "../kanban/taskFormTypes";
import { patchAction } from "../../../api/userProfile";
import { createEmptyBoardData } from "../kanban/kanbanDataMapper";
import type { BoardData, KanbanTask, TaskPriority } from "../kanban/type/kanban";
import {
  DEFAULT_LANGUAGE_ORDER,
  DEFAULT_DIFFICULTY,
  DEFAULT_PROGRESS,
  DIFFICULTY_OPTIONS,
  FALLBACK_COLUMN_ID,
  PRIORITY_TO_VALUE,
  PROGRESS_OPTIONS,
  createInitialTaskFormState,
  createTranslationEntry,
  createTranslationEntriesFromTask,
  extendNumericOptionStrings,
  getLanguageLabel,
  normalizeIncomingDateValue,
  normalizeLanguageCode,
  normalizeNumericSelectValue,
  priorityOptions,
  toTimestampMilliseconds,
  updateTaskFormState,
} from "../shared/taskFormUtils";

import { GanttProjectSelector, getProjectColor } from "./GanttProjectSelector";
import { useGanttData, AUTO_REFRESH_INTERVAL_MS } from "./useGanttData";
import type { GanttMappedTask } from "./ganttDataMapper";
import { getGanttDateRange } from "./ganttDataMapper";
import { GanttTaskTemplate } from "./GanttTaskTemplate";
import { DualScrollbar } from "../../../components/common/DualScrollbar";

// =============================================================================
// Types
// =============================================================================

export interface UnifiedGanttProps {
  /** Single project mode - provide ID to show only this project */
  projectId?: string;
  
  /** Multi-project mode - initial selection of project IDs */
  initialProjectIds?: string[];
  
  /** Show the project selector sidebar (default: true, false if projectId provided) */
  showSelector?: boolean;
  
  /** Compact mode with reduced padding */
  compact?: boolean;
  
  /** Additional CSS classes */
  className?: string;
  
  /** Enable auto-refresh (default: true) */
  autoRefresh?: boolean;
  
  /** Callback when a task is clicked */
  onTaskClick?: (task: GanttMappedTask) => void;
}

// =============================================================================
// Constants
// =============================================================================

const ganttDateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
});

const formatDate = (value?: Date) => (value ? ganttDateFormatter.format(value) : "-");

// SVAR template signature: (value: string, task: ITask, column: IColumnConfig)
// The task with all custom properties is in the 2nd argument

// Factory function to create columns (taskLookup no longer needed since task is in arg[1])
const createGanttColumns = (_taskLookup: Map<string, GanttMappedTask>): IColumnConfig[] => [
  {
    id: "taskIda",
    header: "IDA",
    width: 60,
    align: "center",
    template: (_value: unknown, task: GanttMappedTask) => task?.taskIda || "-",
  },
  {
    id: "projectIda",
    header: "Proj",
    width: 60,
    align: "center",
    template: (_value: unknown, task: GanttMappedTask) => task?.projectIda || "-",
  },
  {
    id: "start",
    header: "Start",
    width: 85,
    align: "center",
    template: (_value: unknown, task: GanttMappedTask) => {
      const startDate = task?.start;
      if (startDate instanceof Date) {
        return formatDate(startDate);
      }
      if (typeof startDate === "string") {
        return formatDate(new Date(startDate));
      }
      return "-";
    },
  },
  {
    id: "duration",
    header: "Dur",
    width: 50,
    align: "center",
    template: (_value: unknown, task: GanttMappedTask) => {
      const d = task?.duration;
      if (typeof d === "number" && d > 0) {
        return `${d}d`;
      }
      return "-";
    },
  },
  {
    id: "progress",
    header: "%",
    width: 50,
    align: "center",
    template: (_value: unknown, task: GanttMappedTask) => {
      const pct = task?.percentComplete ?? task?.progress ?? 0;
      return `${pct}%`;
    },
  },
  {
    id: "slack",
    header: "Slack",
    width: 55,
    align: "center",
    template: (_value: unknown, task: GanttMappedTask) => {
      const slack = task?.slack;
      if (typeof slack !== "number") return "-";
      if (slack === 0) return `<span style="color:#dc2626;font-weight:600">0d</span>`;
      return `${slack}d`;
    },
  },
  {
    id: "baseline",
    header: "Δ Base",
    width: 60,
    align: "center",
    template: (_value: unknown, task: GanttMappedTask) => {
      // Show variance from original (positive = delayed, negative = ahead)
      if (!task?.dtStartOriginal || !task?.start) return "-";
      const originalMs = task.dtStartOriginal instanceof Date ? task.dtStartOriginal.getTime() : 0;
      const actualMs = task.start instanceof Date ? task.start.getTime() : 0;
      if (!originalMs || !actualMs) return "-";
      const varianceDays = Math.round((actualMs - originalMs) / (1000 * 60 * 60 * 24));
      if (varianceDays === 0) return `<span style="color:#059669">±0</span>`;
      if (varianceDays > 0) return `<span style="color:#dc2626;font-weight:600">+${varianceDays}d</span>`;
      return `<span style="color:#059669">${varianceDays}d</span>`;
    },
  },
];

// Factory for single-project mode (hides project column)
const createGanttColumnsSingleProject = (taskLookup: Map<string, GanttMappedTask>): IColumnConfig[] => 
  createGanttColumns(taskLookup).filter((col) => col.id !== "projectIda");

type ScalePresetKey = "day" | "week" | "month" | "quarter";
type ScaleConfig = { unit: string; step: number; format: (date: Date) => string };

const scalePresets: Record<ScalePresetKey, ScaleConfig[]> = {
  day: [
    { unit: "month", step: 1, format: (d: Date) => dateFnsFormat(d, "MMMM yyyy") },
    { unit: "day", step: 1, format: (d: Date) => dateFnsFormat(d, "EEE d") },
  ],
  week: [
    { unit: "month", step: 1, format: (d: Date) => dateFnsFormat(d, "MMMM yyyy") },
    { unit: "day", step: 1, format: (d: Date) => dateFnsFormat(d, "d") },
  ],
  month: [
    { unit: "month", step: 1, format: (d: Date) => dateFnsFormat(d, "MMMM yyyy") },
    { unit: "week", step: 1, format: (d: Date) => dateFnsFormat(d, "d") },
  ],
  quarter: [
    { unit: "month", step: 12, format: (d: Date) => dateFnsFormat(d, "yyyy") },
    { unit: "month", step: 1, format: (d: Date) => dateFnsFormat(d, "MMM") },
  ],
};

const scaleButtons: Array<{ id: ScalePresetKey; label: string }> = [
  { id: "day", label: "Day" },
  { id: "week", label: "Week" },
  { id: "month", label: "Month" },
  { id: "quarter", label: "Quarter" },
];

const GANTT_COLOR_EVENT_TAG = "gantt-project-colors";

// =============================================================================
// Utilities
// =============================================================================

const parseHexColor = (color: string) => {
  const hex = color.startsWith("#") ? color.slice(1) : color;
  if (!/^[0-9a-fA-F]{6}$/.test(hex)) return null;
  return {
    r: parseInt(hex.slice(0, 2), 16),
    g: parseInt(hex.slice(2, 4), 16),
    b: parseInt(hex.slice(4, 6), 16),
  };
};

const getRelativeLuminance = ({ r, g, b }: { r: number; g: number; b: number }): number => {
  const normalizeChannel = (value: number) => {
    const channel = value / 255;
    return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * normalizeChannel(r) + 0.7152 * normalizeChannel(g) + 0.0722 * normalizeChannel(b);
};

const pickReadableTextColor = (background: string): string => {
  const channels = parseHexColor(background);
  if (!channels) return "#0f172a";
  return getRelativeLuminance(channels) > 0.45 ? "#0f172a" : "#ffffff";
};

const combineClassNames = (...classes: Array<string | false | null | undefined>) =>
  classes.filter(Boolean).join(" ");

const toProgressPercentage = (value?: number | null): number => {
  if (typeof value !== "number" || Number.isNaN(value)) return 0;
  if (value >= 0 && value <= 1) return Math.round(value * 100);
  return Math.round(Math.max(0, Math.min(100, value)));
};

const padTwoDigits = (value: number) => value.toString().padStart(2, "0");

const formatDateTimeLocal = (date: Date): string => {
  const year = date.getFullYear();
  const month = padTwoDigits(date.getMonth() + 1);
  const day = padTwoDigits(date.getDate());
  const hours = padTwoDigits(date.getHours());
  const minutes = padTwoDigits(date.getMinutes());
  return `${year}-${month}-${day}T${hours}:${minutes}`;
};

const formatLastRefresh = (date: Date | null): string => {
  if (!date) return "Never";
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  
  if (diffSecs < 10) return "Just now";
  if (diffSecs < 60) return `${diffSecs}s ago`;
  if (diffMins < 60) return `${diffMins}m ago`;
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
};

type TaskColorInfo = {
  color: string;
  textColor: string;
  type?: ITask["type"];
};

// =============================================================================
// Component
// =============================================================================

export const UnifiedGantt: React.FC<UnifiedGanttProps> = ({
  projectId,
  initialProjectIds = [],
  showSelector: showSelectorProp,
  compact = false,
  className,
  autoRefresh = true,
  onTaskClick,
}) => {
  // Determine if we should show selector
  const isSingleProjectMode = Boolean(projectId);
  const showSelector = showSelectorProp ?? !isSingleProjectMode;
  
  // Sidebar collapsed state (collapsed by default)
  const [selectorCollapsed, setSelectorCollapsed] = useState(true);
  
  // Task list (grid) collapsed state - shows only minimal columns when collapsed
  const [taskListCollapsed, setTaskListCollapsed] = useState(false);
  
  // Project selection state
  const [selectedProjectIds, setSelectedProjectIds] = useState<string[]>(() => {
    if (projectId) return [projectId];
    return initialProjectIds;
  });
  
  // Sync with projectId prop changes
  useEffect(() => {
    if (projectId) {
      setSelectedProjectIds([projectId]);
    }
  }, [projectId]);
  
  // Modal state
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editAssigneeUIMode, setEditAssigneeUIMode] = useState<'dropdown' | 'chips'>('dropdown');
  
  // Data fetching
  const {
    projects,
    isLoadingProjects,
    projectsError,
    ganttData,
    isLoadingActions,
    actionsError,
    lastRefreshTime,
    isRefreshing,
    refetchActions,
    refetchAll,
    updateTaskLocally,
  } = useGanttData({
    selectedProjectIds,
    enabled: true,
    autoRefresh: autoRefresh,
    isModalOpen: isEditModalOpen,
  });
  
  // Gantt display state
  const [scalePreset, setScalePreset] = useState<ScalePresetKey>("week");
  const [ganttKey, setGanttKey] = useState(0);
  const activeScales = scalePresets[scalePreset];
  
  // Calculate date range
  const dateRange = useMemo(() => {
    return getGanttDateRange(ganttData.tasks);
  }, [ganttData.tasks]);
  
  // Board state for task editing
  const [board] = useState<BoardData>(() => createEmptyBoardData());
  
  // Edit modal state
  const [editingTask, setEditingTask] = useState<KanbanTask | null>(null);
  const [editTaskState, setEditTaskState] = useState<TaskFormState>(() =>
    createInitialTaskFormState(FALLBACK_COLUMN_ID)
  );
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [editModalError, setEditModalError] = useState<string | null>(null);
  const [editLanguagePickerOpen, setEditLanguagePickerOpen] = useState(false);
  const [editLanguageSelection, setEditLanguageSelection] = useState("");
  const [editCustomLanguage, setEditCustomLanguage] = useState("");
  const [editLanguagePickerError, setEditLanguagePickerError] = useState<string | null>(null);

  // Link context menu state
  const [linkContextMenu, setLinkContextMenu] = useState<{
    x: number;
    y: number;
    linkId: string;
  } | null>(null);

  // Undo/Redo history stacks
  type HistoryEntry = { taskId: string; field: string; oldValue: unknown; newValue: unknown };
  const [undoStack, setUndoStack] = useState<HistoryEntry[]>([]);
  const [redoStack, setRedoStack] = useState<HistoryEntry[]>([]);
  
  // Helper to push to undo stack (called from task update handlers)
  const pushToUndoStack = useCallback((entry: HistoryEntry) => {
    setUndoStack((stack) => [...stack.slice(-49), entry]); // Keep last 50 entries
    setRedoStack([]); // Clear redo stack on new action
  }, []);
  
  // Refs
  const ganttContainerRef = useRef<HTMLDivElement | null>(null);
  const ganttApiRef = useRef<IApi | null>(null);
  const taskColorMapRef = useRef<Map<string, TaskColorInfo>>(new Map());
  // Ref to hold latest update handler for use in init callback
  const handleSvarUpdateTaskRef = useRef<((ev: { id: string | number; task: Partial<ITask> }) => Promise<boolean>) | null>(null);

  // Column options for KanbanTaskModal
  const columnOptions = useMemo(() => {
    return (board.column_order || [])
      .map((colId) => board.columns[colId])
      .filter((col): col is NonNullable<typeof col> => Boolean(col))
      .map((col) => ({ id: col.id, title: col.title }));
  }, [board.column_order, board.columns]);

  // Difficulty and progress options
  const editDifficultyOptions = useMemo(
    () => extendNumericOptionStrings(DIFFICULTY_OPTIONS, editTaskState.difficulty),
    [editTaskState.difficulty]
  );
  const editProgressOptions = useMemo(
    () => extendNumericOptionStrings(PROGRESS_OPTIONS, editTaskState.progress),
    [editTaskState.progress]
  );

  // Language options
  const languageOptions = useMemo(() => {
    return DEFAULT_LANGUAGE_ORDER.map((code) => ({
      value: code,
      label: getLanguageLabel(code),
    }));
  }, []);

  const availableEditLanguages = useMemo(() => {
    const usedCodes = new Set(editTaskState.translations.map((t) => normalizeLanguageCode(t.language)));
    return languageOptions.filter((opt) => !usedCodes.has(normalizeLanguageCode(opt.value)));
  }, [editTaskState.translations, languageOptions]);

  const editLanguagePickerState = useMemo(() => {
    return {
      isOpen: editLanguagePickerOpen,
      selection: editLanguageSelection,
      selectedValue: editLanguageSelection,
      customValue: editCustomLanguage,
      error: editLanguagePickerError,
    };
  }, [editLanguagePickerOpen, editLanguageSelection, editCustomLanguage, editLanguagePickerError]);

  // Color refresh logic
  const refreshTaskColorCache = useCallback(() => {
    const container = ganttContainerRef.current;
    if (!container) return;

    const rows = container.querySelectorAll<HTMLElement>("[data-id]");
    const newMap = new Map<string, TaskColorInfo>();

    rows.forEach((row) => {
      const taskId = row.getAttribute("data-id");
      if (!taskId) return;

      const task = ganttData.tasks.find((t) => String(t.id) === taskId);
      if (!task) return;

      const color = getProjectColor(task.projectId, selectedProjectIds);
      const textColor = pickReadableTextColor(color);

      newMap.set(taskId, { color, textColor, type: task.type });

      // Apply colors to row elements
      const bar = row.querySelector<HTMLElement>(".wx-bar");
      const progress = row.querySelector<HTMLElement>(".wx-progress");
      const textEl = row.querySelector<HTMLElement>(".wx-content");

      if (bar) {
        bar.style.backgroundColor = color;
        bar.style.borderColor = color;
      }
      if (progress) {
        progress.style.backgroundColor = color;
        progress.style.opacity = "0.7";
      }
      if (textEl) {
        textEl.style.color = textColor;
      }
    });

    taskColorMapRef.current = newMap;
  }, [ganttData.tasks, selectedProjectIds]);

  const scheduleColorRefresh = useCallback(() => {
    requestAnimationFrame(() => {
      refreshTaskColorCache();
    });
  }, [refreshTaskColorCache]);

  // Derive form state from a task
  const deriveFormStateFromTask = useCallback(
    (task: KanbanTask): TaskFormState => {
      const taskColumn = Object.values(board.columns).find((column) => column?.task_ids?.includes(task.id));
      const normalizedStart = normalizeIncomingDateValue((task as any).dt_start);
      const normalizedDue = normalizeIncomingDateValue((task as any).dt_deadline);
      const shouldFallbackStart = !normalizedStart && !normalizedDue;
      const resolvedStartDate = shouldFallbackStart ? formatDateTimeLocal(new Date()) : normalizedStart;
      const resolvedDueDate = normalizedDue || "";
      const normalizedDifficulty = normalizeNumericSelectValue(
        task.difficulty ?? PRIORITY_TO_VALUE[task.priority],
        DEFAULT_DIFFICULTY
      );
      const normalizedProgressValue = toProgressPercentage(task.progress);
      const normalizedProgress = normalizeNumericSelectValue(normalizedProgressValue, DEFAULT_PROGRESS);

      return {
        translations: createTranslationEntriesFromTask(task),
        columnId: taskColumn?.id ?? task.status ?? FALLBACK_COLUMN_ID,
        priority: task.priority,
        dt_deadline: resolvedDueDate,
        dt_start: resolvedStartDate,
        dt_completed: "",
        dt_expected: resolvedDueDate,
        assignee: task.assignee || task.assigned_to?.[0]?.name || "",
        difficulty: String(normalizedDifficulty),
        progress: String(normalizedProgress),
        percent_complete: String(normalizedProgress),
      };
    },
    [board.columns]
  );

  // Task editing handlers
  const handleShowEditor = useCallback(
    ({ id }: { id: string | number }) => {
      const ganttTask = ganttData.tasks.find((t) => String(t.id) === String(id));
      if (!ganttTask) return;

      // Optional callback
      if (onTaskClick) {
        onTaskClick(ganttTask);
      }

      // Create a KanbanTask-like object
      const kanbanTask: KanbanTask = {
        id: String(ganttTask.id),
        title: ganttTask.text || "",
        description: ganttTask.details || "",
        priority: (ganttTask.priority as TaskPriority) || "medium",
        status: ganttTask.columnTitle || "Uncategorized",
        dt_deadline: ganttTask.end instanceof Date ? ganttTask.end.toISOString() : undefined,
        dt_start: ganttTask.start instanceof Date ? ganttTask.start.toISOString() : undefined,
        progress: toProgressPercentage(ganttTask.progress),
        assignee: ganttTask.assignee,
        tags: [],
        title_translations: { en: ganttTask.text || "" },
        description_translations: { en: ganttTask.details || "" },
        language_codes: ["en"],
      };

      setEditingTask(kanbanTask);
      setEditTaskState(deriveFormStateFromTask(kanbanTask));
      setEditModalError(null);
      setIsEditModalOpen(true);
    },
    [ganttData.tasks, deriveFormStateFromTask, onTaskClick]
  );

  const handleCloseEditModal = useCallback(() => {
    setIsEditModalOpen(false);
    setEditingTask(null);
    setEditModalError(null);
    setEditLanguagePickerOpen(false);
  }, []);

  const handleEditTaskChange = useCallback(
    (field: TaskFormEditableField, value: string) => {
      setEditTaskState((prev) => updateTaskFormState(prev, field, value));
    },
    []
  );

  const handleEditTranslationFieldChange = useCallback(
    (entryId: string, field: "language" | "title" | "description", value: string) => {
      setEditTaskState((prev) => ({
        ...prev,
        translations: prev.translations.map((entry) =>
          entry.id === entryId ? { ...entry, [field]: value } : entry
        ),
      }));
    },
    []
  );

  const handleRemoveEditTranslation = useCallback((entryId: string) => {
    setEditTaskState((prev) => ({
      ...prev,
      translations: prev.translations.filter((entry) => entry.id !== entryId),
    }));
  }, []);

  const handleEditLanguagePickerToggle = useCallback(() => {
    setEditLanguagePickerOpen((prev) => !prev);
    if (!editLanguagePickerOpen) {
      setEditLanguageSelection("");
      setEditCustomLanguage("");
      setEditLanguagePickerError(null);
    }
  }, [editLanguagePickerOpen]);

  const handleEditLanguageSelectionChange = useCallback((value: string) => {
    setEditLanguageSelection(value);
    setEditLanguagePickerError(null);
  }, []);

  const handleEditLanguageCustomChange = useCallback((value: string) => {
    setEditCustomLanguage(value);
    setEditLanguagePickerError(null);
  }, []);

  const handleEditLanguagePickerSubmit = useCallback(() => {
    const code = editLanguageSelection === "custom" ? editCustomLanguage.trim() : editLanguageSelection;
    if (!code) {
      setEditLanguagePickerError("Please select or enter a language code.");
      return;
    }
    const normalized = normalizeLanguageCode(code);
    const alreadyUsed = editTaskState.translations.some(
      (t) => normalizeLanguageCode(t.language) === normalized
    );
    if (alreadyUsed) {
      setEditLanguagePickerError("This language is already added.");
      return;
    }
    const newEntry = createTranslationEntry(code);
    setEditTaskState((prev) => ({
      ...prev,
      translations: [...prev.translations, newEntry],
    }));
    setEditLanguagePickerOpen(false);
    setEditLanguageSelection("");
    setEditCustomLanguage("");
    setEditLanguagePickerError(null);
  }, [editLanguageSelection, editCustomLanguage, editTaskState.translations]);

  const handleEditLanguagePickerCancel = useCallback(() => {
    setEditLanguagePickerOpen(false);
    setEditLanguageSelection("");
    setEditCustomLanguage("");
    setEditLanguagePickerError(null);
  }, []);

  const buildEditActionPayload = useCallback(
    (state: TaskFormState, baseTask: KanbanTask | null): { payload: Record<string, unknown> } | { error: string } => {
      if (!baseTask) {
        return { error: "No task selected for editing." };
      }

      const normalized = new Map<string, { title: string; description: string }>();

      state.translations.forEach((entry) => {
        const language = normalizeLanguageCode(entry.language);
        if (!language) return;
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
        : baseTask.assigned_to?.map((assignment: any) => ({ name: assignment.name })) ?? [];

      const dueTimestamp = toTimestampMilliseconds(state.dt_deadline);
      const startTimestamp = toTimestampMilliseconds(state.dt_start);
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

  const handleEditTaskSubmit = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      if (isSavingEdit || !editingTask) return;

      setIsSavingEdit(true);
      setEditModalError(null);

      const result = buildEditActionPayload(editTaskState, editingTask);
      if ("error" in result) {
        setEditModalError(result.error);
        setIsSavingEdit(false);
        return;
      }

      try {
        await patchAction(result.payload);
        await refetchActions();
        handleCloseEditModal();
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to save changes";
        setEditModalError(message);
        console.error("Failed to update task:", error);
      } finally {
        setIsSavingEdit(false);
      }
    },
    [isSavingEdit, editingTask, editTaskState, buildEditActionPayload, refetchActions, handleCloseEditModal]
  );

  const handleSvarUpdateTask = useCallback(
    async ({ id, task }: { id: string | number; task: Partial<ITask> }) => {
      console.log("[Gantt] handleSvarUpdateTask called (before checks)", { id, task });
      if (!id) return false;

      console.log("[Gantt] handleSvarUpdateTask proceeding", { id, task });

      try {
        // Find the original task to record old values for undo
        const originalTask = ganttData.tasks.find((t) => String(t.id) === String(id));
        
        const payload: Record<string, unknown> = {
          model_name: "action",
          id: String(id),
        };

        if (task.start instanceof Date) {
          const oldValue = originalTask?.start instanceof Date ? originalTask.start.getTime() : null;
          const newValue = task.start.getTime();
          payload["dt_start"] = { mode: "update", value: newValue };
          console.log("[Gantt] dt_start changed:", { oldValue, newValue });
          // Record for undo
          if (oldValue !== newValue) {
            pushToUndoStack({ taskId: String(id), field: "dt_start", oldValue, newValue });
          }
        }
        if (task.end instanceof Date) {
          const oldValue = originalTask?.end instanceof Date ? originalTask.end.getTime() : null;
          const newValue = task.end.getTime();
          payload["dt_deadline"] = { mode: "update", value: newValue };
          console.log("[Gantt] dt_deadline changed:", { oldValue, newValue });
          if (oldValue !== newValue) {
            pushToUndoStack({ taskId: String(id), field: "dt_deadline", oldValue, newValue });
          }
        }
        
        // Calculate and save duration when both start and end are available
        const startDate = task.start instanceof Date ? task.start : (originalTask?.start instanceof Date ? originalTask.start : null);
        const endDate = task.end instanceof Date ? task.end : (originalTask?.end instanceof Date ? originalTask.end : null);
        if (startDate && endDate) {
          const durationDays = Math.max(1, Math.round((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)));
          payload["duration"] = { mode: "update", value: durationDays };
          console.log("[Gantt] duration calculated:", durationDays, "days");
        }
        
        if (typeof task.progress === "number") {
          payload["percent_complete"] = {
            mode: "update",
            value: Math.round(task.progress * 100),
          };
        }

        console.log("[Gantt] Saving payload:", payload);
        await patchAction(payload);
        console.log("[Gantt] Save completed for task", id);
        
        // Update local React state to keep ganttData in sync with the new values
        const localUpdates: { start?: Date; end?: Date; progress?: number } = {};
        if (task.start instanceof Date) localUpdates.start = task.start;
        if (task.end instanceof Date) localUpdates.end = task.end;
        if (typeof task.progress === "number") localUpdates.progress = task.progress;
        
        updateTaskLocally(id, localUpdates);
        console.log("[Gantt] Local state updated for task", id);
        
        return true;
      } catch (error) {
        console.error("Failed to update task:", error);
        return false;
      }
    },
    [ganttData.tasks, pushToUndoStack, updateTaskLocally]
  );

  // Keep ref updated for use in init callback
  handleSvarUpdateTaskRef.current = handleSvarUpdateTask;

  /**
   * Check if adding a link from source → target would create a circular dependency.
   * A cycle exists if target is already an ancestor of source.
   */
  const wouldCreateCircularDependency = useCallback(
    (sourceId: string, targetId: string): { wouldCreateCycle: boolean; cyclePath: string[] } => {
      // Self-reference check
      if (sourceId === targetId) {
        return { wouldCreateCycle: true, cyclePath: [sourceId] };
      }

      // Build a quick lookup of task parents
      const taskParentsMap = new Map<string, string[]>();
      for (const task of ganttData.tasks) {
        const parents = (task as any).refParents || [];
        taskParentsMap.set(String(task.id), parents.map(String));
      }

      // Check if targetId is an ancestor of sourceId by traversing up from source
      const visited = new Set<string>();
      const path: string[] = [sourceId];

      const hasAncestor = (currentId: string, lookingFor: string): boolean => {
        if (visited.has(currentId)) return false;
        visited.add(currentId);

        const parents = taskParentsMap.get(currentId) || [];
        for (const parentId of parents) {
          if (parentId === lookingFor) {
            path.push(parentId);
            return true;
          }
          path.push(parentId);
          if (hasAncestor(parentId, lookingFor)) {
            return true;
          }
          path.pop();
        }
        return false;
      };

      if (hasAncestor(sourceId, targetId)) {
        return { wouldCreateCycle: true, cyclePath: path };
      }

      return { wouldCreateCycle: false, cyclePath: [] };
    },
    [ganttData.tasks]
  );

  /**
   * Handle adding a new dependency link between tasks
   * Links are stored in refs.parents[] on the target action
   * 
   * SVAR link types:
   * - e2s: End-to-Start (finish-to-start) - most common
   * - s2s: Start-to-Start
   * - e2e: End-to-End
   * - s2e: Start-to-End
   */
  const handleAddLink = useCallback(
    async ({ link }: { id?: string | number; link: { source: string | number; target: string | number; type: string } }) => {
      const sourceId = String(link.source);
      const targetId = String(link.target);
      const linkType = link.type || "e2s";
      
      console.log(`[Gantt] Adding link: ${sourceId} → ${targetId} (${linkType})`);
      
      // Check for circular dependency BEFORE creating the link
      const circularCheck = wouldCreateCircularDependency(sourceId, targetId);
      if (circularCheck.wouldCreateCycle) {
        console.warn(
          `[Gantt] Cannot add link: would create circular dependency. Path: ${circularCheck.cyclePath.join(' → ')}`
        );
        // You could show a toast/alert here
        alert(`Cannot create this dependency: it would create a circular reference.\n\nCycle: ${circularCheck.cyclePath.join(' → ')}`);
        return false;
      }
      
      // Find the target task to get its current refs.parents
      const targetTask = ganttData.tasks.find((t) => String(t.id) === targetId);
      if (!targetTask) {
        console.warn(`[Gantt] Cannot add link: target task ${targetId} not found`);
        return false;
      }
      
      try {
        // Get existing parents from the target task's original action data
        // The parents array should already include existing dependencies
        const existingParents: string[] = (targetTask as any).refParents || [];
        
        // Add the new parent if not already present
        if (!existingParents.includes(sourceId)) {
          const updatedParents = [...existingParents, sourceId];
          
          const payload: Record<string, unknown> = {
            model_name: "action",
            id: targetId,
            "refs.parents": { mode: "update", value: updatedParents },
          };
          
          await patchAction(payload);
          console.log(`[Gantt] Link added successfully: ${sourceId} → ${targetId}`);
          
          // Refresh to show the new link and auto-scheduled dates
          await refetchActions();
          
          // Force Gantt re-render to reflect backend auto-scheduling changes
          setGanttKey((k) => k + 1);
        } else {
          console.log(`[Gantt] Link already exists: ${sourceId} → ${targetId}`);
        }
        
        return true;
      } catch (error) {
        console.error("[Gantt] Failed to add link:", error);
        return false;
      }
    },
    [ganttData.tasks, refetchActions, setGanttKey, wouldCreateCircularDependency]
  );

  /**
   * Handle deleting a dependency link between tasks
   */
  const handleDeleteLink = useCallback(
    async ({ id }: { id: string | number }) => {
      // The link ID format from our mapper is: "dep-{sourceId}-{targetId}"
      const linkIdStr = String(id);
      console.log(`[Gantt] Deleting link: ${linkIdStr}`);
      
      // Parse the link ID to get source and target
      const match = linkIdStr.match(/^dep-(.+)-(.+)$/);
      if (!match) {
        console.warn(`[Gantt] Cannot parse link ID: ${linkIdStr}`);
        return false;
      }
      
      const [, sourceId, targetId] = match;
      
      // Find the target task
      const targetTask = ganttData.tasks.find((t) => String(t.id) === targetId);
      if (!targetTask) {
        console.warn(`[Gantt] Cannot delete link: target task ${targetId} not found`);
        return false;
      }
      
      try {
        // Get existing parents and remove the source
        const existingParents: string[] = (targetTask as any).refParents || [];
        const updatedParents = existingParents.filter((p) => String(p) !== sourceId);
        
        const payload: Record<string, unknown> = {
          model_name: "action",
          id: targetId,
          "refs.parents": { mode: "update", value: updatedParents },
        };
        
        await patchAction(payload);
        console.log(`[Gantt] Link deleted successfully: ${sourceId} → ${targetId}`);
        
        // Refresh to update the display
        await refetchActions();
        
        // Force Gantt re-render
        setGanttKey((k) => k + 1);
        return true;
      } catch (error) {
        console.error("[Gantt] Failed to delete link:", error);
        return false;
      }
    },
    [ganttData.tasks, refetchActions, setGanttKey]
  );

  /**
   * Handle updating an existing link (e.g., changing link type)
   * Note: Our backend currently only stores parent references, not link types
   */
  const handleUpdateLink = useCallback(
    async ({ id, link }: { id: string | number; link: { type?: string } }) => {
      console.log(`[Gantt] Update link requested: ${id}`, link);
      // For now, we don't persist link types - just log the change
      // Link types would require extending the backend model
      return true;
    },
    []
  );

  // Force re-render when selection changes
  useEffect(() => {
    setGanttKey((prev) => prev + 1);
  }, [selectedProjectIds]);
  
  useEffect(() => {
    refreshTaskColorCache();
    scheduleColorRefresh();
  }, [ganttData.tasks, refreshTaskColorCache, scheduleColorRefresh]);
  
  // Link context menu handler
  useEffect(() => {
    const container = ganttContainerRef.current;
    if (!container) return;

    const handleContextMenu = (e: MouseEvent) => {
      // Check if clicked on a link element (SVG path within the chart area)
      const target = e.target as Element;
      
      // SVAR renders links as SVG paths with specific classes
      // Look for parent with data-link-id or similar, or check if it's a path in the chart
      let linkElement: Element | null = target;
      let linkId: string | null = null;
      
      // Walk up the DOM to find a link element
      while (linkElement && linkElement !== container) {
        // Check for data-id attribute on link-related elements
        const dataId = linkElement.getAttribute("data-id");
        if (dataId && dataId.startsWith("dep-")) {
          linkId = dataId;
          break;
        }
        
        // Check if it's an SVG path (links are rendered as paths)
        if (linkElement.tagName.toLowerCase() === "path") {
          // Look for the closest g element with data-id
          const parentG = linkElement.closest("g[data-id]");
          if (parentG) {
            const gDataId = parentG.getAttribute("data-id");
            if (gDataId && gDataId.startsWith("dep-")) {
              linkId = gDataId;
              break;
            }
          }
        }
        
        linkElement = linkElement.parentElement;
      }
      
      if (linkId) {
        e.preventDefault();
        e.stopPropagation();
        setLinkContextMenu({
          x: e.clientX,
          y: e.clientY,
          linkId,
        });
      }
    };

    const handleClick = () => {
      // Close context menu on any click
      setLinkContextMenu(null);
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setLinkContextMenu(null);
      }
    };

    container.addEventListener("contextmenu", handleContextMenu);
    document.addEventListener("click", handleClick);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      container.removeEventListener("contextmenu", handleContextMenu);
      document.removeEventListener("click", handleClick);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);
  
  const handleManualRefresh = useCallback(async () => {
    await refetchActions();
  }, [refetchActions]);
  
  // Helper to format date for display
  const formatDateShort = (date: Date | null | undefined): string => {
    if (!date) return '—';
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' });
  };
  
  // Print handler - opens a new window with task list table + timeline visualization
  const handlePrint = useCallback(async () => {
    const container = ganttContainerRef.current;
    if (!container) {
      alert("Unable to print: Gantt container not found");
      return;
    }
    
    // Build project names header
    const projectNames = selectedProjectIds.map(id => {
      const proj = projects.find(p => String(p.id) === String(id));
      return proj?.title || proj?.project_name || `Project ${id}`;
    }).join(', ');
    
    // Calculate date range for the timeline
    let minDate = new Date();
    let maxDate = new Date();
    ganttData.tasks.forEach(task => {
      if (task.start instanceof Date) {
        if (task.start < minDate) minDate = new Date(task.start);
        if (task.start > maxDate) maxDate = new Date(task.start);
      }
      if (task.end instanceof Date) {
        if (task.end < minDate) minDate = new Date(task.end);
        if (task.end > maxDate) maxDate = new Date(task.end);
      }
    });
    
    // Add padding to date range
    minDate.setDate(minDate.getDate() - 2);
    maxDate.setDate(maxDate.getDate() + 2);
    const totalDays = Math.max(1, Math.ceil((maxDate.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24)));
    
    // Build task list table rows with visual timeline bars (using inline styles for print compatibility)
    const taskRows = ganttData.tasks.map(task => {
      const mapped = task as GanttMappedTask;
      const startDate = task.start instanceof Date ? formatDateShort(task.start) : '—';
      const endDate = task.end instanceof Date ? formatDateShort(task.end) : '—';
      const progress = typeof task.progress === 'number' ? Math.round(task.progress * 100) : 0;
      const slack = typeof mapped.slack === 'number' ? `${mapped.slack}d` : '—';
      const critical = mapped.critical ? '●' : '';
      
      // Calculate bar position and width for timeline visualization
      let barLeft = 0;
      let barWidth = 0;
      if (task.start instanceof Date && task.end instanceof Date) {
        const startOffset = (task.start.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24);
        const duration = Math.max(1, (task.end.getTime() - task.start.getTime()) / (1000 * 60 * 60 * 24));
        barLeft = (startOffset / totalDays) * 100;
        barWidth = Math.max((duration / totalDays) * 100, 1);
      }
      
      const barColor = mapped.critical ? '#dc2626' : '#3b82f6';
      const progressWidth = Math.min(progress, 100);
      
      // Use fully inline styles for maximum print compatibility
      return `<tr>
        <td>${task.text || '—'}</td>
        <td style="text-align:center">${startDate}</td>
        <td style="text-align:center">${endDate}</td>
        <td style="text-align:center">${progress}%</td>
        <td style="text-align:center">${slack}</td>
        <td style="text-align:center;color:${mapped.critical ? '#dc2626' : '#9ca3af'}">${critical}</td>
        <td style="padding:2px 4px;min-width:300px;-webkit-print-color-adjust:exact;print-color-adjust:exact;color-adjust:exact;">
          <div style="position:relative;height:14px;background:#e5e7eb;border-radius:2px;-webkit-print-color-adjust:exact;print-color-adjust:exact;color-adjust:exact;">
            <div style="position:absolute;left:${barLeft}%;width:${barWidth}%;height:100%;background:${barColor};border-radius:2px;min-width:4px;-webkit-print-color-adjust:exact;print-color-adjust:exact;color-adjust:exact;">
              <div style="width:${progressWidth}%;height:100%;background:rgba(0,0,0,0.25);border-radius:2px 0 0 2px;-webkit-print-color-adjust:exact;print-color-adjust:exact;color-adjust:exact;"></div>
            </div>
          </div>
        </td>
      </tr>`;
    }).join('');
    
    // Generate month labels for timeline header
    const monthLabels: string[] = [];
    const monthPositions: { label: string; left: number }[] = [];
    const tempDate = new Date(minDate);
    while (tempDate <= maxDate) {
      const dayOffset = (tempDate.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24);
      const leftPos = (dayOffset / totalDays) * 100;
      if (tempDate.getDate() === 1 || monthLabels.length === 0) {
        monthPositions.push({
          label: tempDate.toLocaleDateString('en-US', { month: 'short', year: '2-digit' }),
          left: leftPos
        });
      }
      tempDate.setDate(tempDate.getDate() + 7); // Move week by week
    }
    
    const timelineHeader = monthPositions.map(m => 
      `<span style="position:absolute;left:${m.left}%;font-size:8px;color:#6b7280;">${m.label}</span>`
    ).join('');
    
    // Create a new window for printing
    const printWindow = window.open('', '_blank', 'width=1200,height=800');
    if (!printWindow) {
      alert("Please allow popups to print the Gantt chart");
      return;
    }
    
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Gantt Chart - ${projectNames}</title>
          <style>
            * { 
              box-sizing: border-box;
              -webkit-print-color-adjust: exact !important;
              print-color-adjust: exact !important;
              color-adjust: exact !important;
            }
            body { 
              margin: 0; 
              padding: 20px; 
              background: white;
              font-family: system-ui, -apple-system, sans-serif;
              font-size: 11px;
            }
            .print-header {
              margin-bottom: 15px;
              padding-bottom: 10px;
              border-bottom: 2px solid #e5e7eb;
            }
            .print-header h1 {
              margin: 0 0 4px 0;
              font-size: 16px;
              font-weight: 600;
              color: #111827;
            }
            .print-header p {
              margin: 0;
              font-size: 10px;
              color: #6b7280;
            }
            
            /* Task List Section */
            .task-list-section {
              margin-bottom: 20px;
            }
            .task-list-section h2 {
              font-size: 14px;
              font-weight: 600;
              margin: 0 0 10px 0;
              color: #374151;
            }
            .task-table {
              width: 100%;
              border-collapse: collapse;
              font-size: 9px;
            }
            .task-table th {
              background: #f3f4f6;
              border: 1px solid #d1d5db;
              padding: 4px 6px;
              text-align: left;
              font-weight: 600;
              color: #374151;
              white-space: nowrap;
            }
            .task-table td {
              border: 1px solid #e5e7eb;
              padding: 3px 6px;
              color: #4b5563;
            }
            .task-table tr:nth-child(even) {
              background: #f9fafb;
            }
            
            /* Timeline visualization */
            .timeline-header {
              position: relative;
              height: 16px;
              background: #f9fafb;
              border-bottom: 1px solid #e5e7eb;
            }
            .timeline-cell {
              padding: 2px 4px !important;
              min-width: 300px;
            }
            .timeline-bar-container {
              position: relative;
              height: 14px;
              background: #e5e7eb;
              border-radius: 2px;
              -webkit-print-color-adjust: exact !important;
              print-color-adjust: exact !important;
              color-adjust: exact !important;
            }
            .timeline-bar {
              position: absolute;
              height: 100%;
              border-radius: 2px;
              min-width: 4px;
              -webkit-print-color-adjust: exact !important;
              print-color-adjust: exact !important;
              color-adjust: exact !important;
            }
            .timeline-progress {
              height: 100%;
              background: rgba(0,0,0,0.25);
              border-radius: 2px 0 0 2px;
              -webkit-print-color-adjust: exact !important;
              print-color-adjust: exact !important;
              color-adjust: exact !important;
            }
            
            @media print {
              @page { 
                size: landscape; 
                margin: 0.3in; 
              }
              * {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                color-adjust: exact !important;
              }
              body { padding: 0; font-size: 8px; }
              .print-header { margin-bottom: 8px; }
              .task-table { font-size: 7px; }
              .task-table th, .task-table td { padding: 2px 4px; }
              .timeline-cell { min-width: 250px; }
              .timeline-bar-container {
                background: #e5e7eb !important;
              }
              .timeline-bar {
                background-color: inherit !important;
              }
            }
          </style>
        </head>
        <body>
          <div class="print-header">
            <h1>Project Gantt Chart</h1>
            <p>${projectNames} | Generated: ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString()} | ${ganttData.tasks.length} tasks</p>
          </div>
          
          <!-- Task List with Timeline -->
          <div class="task-list-section">
            <table class="task-table">
              <thead>
                <tr>
                  <th style="width:22%">Task Name</th>
                  <th style="width:8%;text-align:center">Start</th>
                  <th style="width:8%;text-align:center">End</th>
                  <th style="width:6%;text-align:center">Progress</th>
                  <th style="width:6%;text-align:center">Slack</th>
                  <th style="width:5%;text-align:center">Crit</th>
                  <th style="width:45%">
                    <div style="position:relative;height:16px;background:#f9fafb;border-bottom:1px solid #e5e7eb;-webkit-print-color-adjust:exact;print-color-adjust:exact;color-adjust:exact;">${timelineHeader}</div>
                  </th>
                </tr>
              </thead>
              <tbody>
                ${taskRows}
              </tbody>
            </table>
          </div>
          
          <script>
            window.onload = function() {
              setTimeout(function() {
                window.print();
              }, 200);
            };
          </script>
        </body>
      </html>
    `);
    
    printWindow.document.close();
  }, [projects, selectedProjectIds, ganttData.tasks]);
  
  // Export to SVG handler - creates a true vector graphic
  const handleExportSVG = useCallback(() => {
    if (ganttData.tasks.length === 0) {
      alert("No tasks to export");
      return;
    }
    
    // Helper to escape XML special characters
    const escapeXml = (str: string): string => {
      return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    };
    
    // Configuration
    const leftPanelWidth = 200;
    const rowHeight = 28;
    const headerHeight = 50;
    const padding = 10;
    const chartWidth = 800;
    const totalWidth = leftPanelWidth + chartWidth + padding * 2;
    const totalHeight = headerHeight + ganttData.tasks.length * rowHeight + padding * 2;
    
    // Calculate date range
    let minDate = new Date();
    let maxDate = new Date();
    ganttData.tasks.forEach(task => {
      if (task.start instanceof Date) {
        if (task.start < minDate) minDate = new Date(task.start);
        if (task.start > maxDate) maxDate = new Date(task.start);
      }
      if (task.end instanceof Date) {
        if (task.end < minDate) minDate = new Date(task.end);
        if (task.end > maxDate) maxDate = new Date(task.end);
      }
    });
    minDate.setDate(minDate.getDate() - 3);
    maxDate.setDate(maxDate.getDate() + 3);
    const totalDays = Math.max(1, Math.ceil((maxDate.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24)));
    
    // Build project names
    const projectNames = selectedProjectIds.map(id => {
      const proj = projects.find(p => String(p.id) === String(id));
      return proj?.title || proj?.project_name || `Project ${id}`;
    }).join(', ');
    
    // Generate month/week markers
    const dateMarkers: { label: string; x: number }[] = [];
    const tempDate = new Date(minDate);
    let lastMonth = -1;
    while (tempDate <= maxDate) {
      const dayOffset = (tempDate.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24);
      const xPos = leftPanelWidth + padding + (dayOffset / totalDays) * chartWidth;
      
      if (tempDate.getMonth() !== lastMonth) {
        dateMarkers.push({
          label: tempDate.toLocaleDateString('en-US', { month: 'short', year: '2-digit' }),
          x: xPos
        });
        lastMonth = tempDate.getMonth();
      }
      tempDate.setDate(tempDate.getDate() + 7);
    }
    
    // Generate SVG content
    let svgContent = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${totalWidth} ${totalHeight}" width="${totalWidth}" height="${totalHeight}">
  <defs>
    <style>
      .title { font: bold 14px system-ui, -apple-system, sans-serif; fill: #111827; }
      .subtitle { font: 9px system-ui, sans-serif; fill: #6b7280; }
      .task-name { font: 10px system-ui, sans-serif; fill: #374151; }
      .date-label { font: 8px system-ui, sans-serif; fill: #9ca3af; }
      .header-bg { fill: #f9fafb; }
      .grid-line { stroke: #e5e7eb; stroke-width: 0.5; }
      .task-bar { rx: 3; ry: 3; }
      .task-bar-normal { fill: #3b82f6; }
      .task-bar-critical { fill: #dc2626; }
      .progress-overlay { fill: rgba(0,0,0,0.2); }
    </style>
  </defs>
  
  <!-- Background -->
  <rect width="${totalWidth}" height="${totalHeight}" fill="white"/>
  
  <!-- Header -->
  <rect x="0" y="0" width="${totalWidth}" height="${headerHeight}" class="header-bg"/>
  <text x="${padding}" y="20" class="title">Project Gantt Chart</text>
  <text x="${padding}" y="35" class="subtitle">${escapeXml(projectNames)} | ${ganttData.tasks.length} tasks | ${new Date().toLocaleDateString()}</text>
  
  <!-- Date markers -->
  ${dateMarkers.map(m => `<text x="${m.x}" y="45" class="date-label">${m.label}</text>`).join('\n  ')}
  
  <!-- Separator line -->
  <line x1="0" y1="${headerHeight}" x2="${totalWidth}" y2="${headerHeight}" class="grid-line"/>
  <line x1="${leftPanelWidth}" y1="${headerHeight}" x2="${leftPanelWidth}" y2="${totalHeight}" class="grid-line"/>
`;
    
    // Add task rows
    ganttData.tasks.forEach((task, index) => {
      const mapped = task as GanttMappedTask;
      const y = headerHeight + index * rowHeight;
      const rawTaskName = (task.text || '—').slice(0, 30) + ((task.text || '').length > 30 ? '...' : '');
      const taskName = escapeXml(rawTaskName);
      const progress = typeof task.progress === 'number' ? Math.round(task.progress * 100) : 0;
      const isCritical = mapped.critical;
      
      // Calculate bar position
      let barX = leftPanelWidth + padding;
      let barWidth = 0;
      if (task.start instanceof Date && task.end instanceof Date) {
        const startOffset = (task.start.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24);
        const duration = Math.max(1, (task.end.getTime() - task.start.getTime()) / (1000 * 60 * 60 * 24));
        barX = leftPanelWidth + padding + (startOffset / totalDays) * chartWidth;
        barWidth = Math.max((duration / totalDays) * chartWidth, 4);
      }
      
      // Row background (alternating)
      if (index % 2 === 0) {
        svgContent += `  <rect x="0" y="${y}" width="${totalWidth}" height="${rowHeight}" fill="#fafafa"/>\n`;
      }
      
      // Grid line
      svgContent += `  <line x1="0" y1="${y + rowHeight}" x2="${totalWidth}" y2="${y + rowHeight}" class="grid-line"/>\n`;
      
      // Task name
      svgContent += `  <text x="${padding}" y="${y + rowHeight / 2 + 4}" class="task-name">${taskName}</text>\n`;
      
      // Task bar
      if (barWidth > 0) {
        const barY = y + 6;
        const barHeight = rowHeight - 12;
        const barClass = isCritical ? 'task-bar-critical' : 'task-bar-normal';
        
        svgContent += `  <rect x="${barX}" y="${barY}" width="${barWidth}" height="${barHeight}" class="task-bar ${barClass}"/>\n`;
        
        // Progress overlay
        if (progress > 0) {
          const progressWidth = (progress / 100) * barWidth;
          svgContent += `  <rect x="${barX}" y="${barY}" width="${progressWidth}" height="${barHeight}" class="progress-overlay" rx="3" ry="3"/>\n`;
        }
      }
    });
    
    svgContent += `</svg>`;
    
    // Download the SVG
    const blob = new Blob([svgContent], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    
    const fileProjectNames = selectedProjectIds.map(id => {
      const proj = projects.find(p => String(p.id) === String(id));
      return proj?.title || proj?.project_name || id;
    }).join('-').replace(/[^a-zA-Z0-9-]/g, '').slice(0, 50);
    
    link.download = `gantt-${fileProjectNames || 'chart'}-${new Date().toISOString().split("T")[0]}.svg`;
    link.href = url;
    link.click();
    
    URL.revokeObjectURL(url);
  }, [projects, selectedProjectIds, ganttData.tasks]);
  
  // Set baseline handler - saves current dates as original planned dates
  const handleSetBaseline = useCallback(async () => {
    if (ganttData.tasks.length === 0) return;
    
    const confirmed = window.confirm(
      "This will save the current start dates as the original planned dates for all tasks. Continue?"
    );
    if (!confirmed) return;
    
    try {
      // Update each task's original planned dates
      const updates = ganttData.tasks.map(async (task) => {
        const startMs = task.start instanceof Date ? task.start.getTime() : null;
        const endMs = task.end instanceof Date ? task.end.getTime() : null;
        
        if (!startMs) return;
        
        const payload: Record<string, unknown> = {
          model_name: "action",
          id: task.id,
          dt_start_original: { mode: "update", value: startMs },
          dt_end_original: { mode: "update", value: endMs },
        };
        
        return patchAction(payload);
      });
      
      await Promise.all(updates);
      await refetchActions();
      alert("Baseline dates saved successfully!");
    } catch (error) {
      console.error("Failed to set baseline:", error);
      alert("Failed to save baseline dates. Please try again.");
    }
  }, [ganttData.tasks, refetchActions]);
  
  // Undo handler
  const handleUndo = useCallback(async () => {
    if (undoStack.length === 0) return;
    
    const entry = undoStack[undoStack.length - 1];
    setUndoStack((stack) => stack.slice(0, -1));
    
    try {
      const payload: Record<string, unknown> = {
        model_name: "action",
        id: entry.taskId,
        [entry.field]: { mode: "update", value: entry.oldValue },
      };
      
      await patchAction(payload);
      await refetchActions();
      
      // Add to redo stack
      setRedoStack((stack) => [...stack, entry]);
    } catch (error) {
      console.error("Undo failed:", error);
      // Restore the entry to undo stack on failure
      setUndoStack((stack) => [...stack, entry]);
    }
  }, [undoStack, refetchActions]);
  
  // Redo handler
  const handleRedo = useCallback(async () => {
    if (redoStack.length === 0) return;
    
    const entry = redoStack[redoStack.length - 1];
    setRedoStack((stack) => stack.slice(0, -1));
    
    try {
      const payload: Record<string, unknown> = {
        model_name: "action",
        id: entry.taskId,
        [entry.field]: { mode: "update", value: entry.newValue },
      };
      
      await patchAction(payload);
      await refetchActions();
      
      // Add to undo stack
      setUndoStack((stack) => [...stack, entry]);
    } catch (error) {
      console.error("Redo failed:", error);
      // Restore the entry to redo stack on failure
      setRedoStack((stack) => [...stack, entry]);
    }
  }, [redoStack, refetchActions]);
  
  // Keyboard shortcut for undo/redo
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "z") {
        e.preventDefault();
        if (e.shiftKey) {
          handleRedo();
        } else {
          handleUndo();
        }
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "y") {
        e.preventDefault();
        handleRedo();
      }
    };
    
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleUndo, handleRedo]);
  
  const isLoading = isLoadingProjects || isLoadingActions;
  const error = projectsError || actionsError;
  
  // Create task lookup map for column templates (SVAR strips custom properties)
  const taskLookup = useMemo(() => {
    const lookup = new Map<string, GanttMappedTask>();
    for (const task of ganttData.tasks) {
      lookup.set(String(task.id), task as GanttMappedTask);
    }
    return lookup;
  }, [ganttData.tasks]);
  
  // Minimal column configuration when task list is collapsed
  const collapsedColumns: IColumnConfig[] = useMemo(() => [
    {
      id: "taskIda",
      header: "#",
      width: 50,
      align: "center",
      template: (_value: unknown, task: GanttMappedTask) => task?.taskIda || "-",
    },
  ], []);
  
  // Choose columns based on mode - create dynamically with task lookup
  const activeColumns = useMemo(() => {
    if (taskListCollapsed) {
      return collapsedColumns;
    }
    return isSingleProjectMode 
      ? createGanttColumnsSingleProject(taskLookup) 
      : createGanttColumns(taskLookup);
  }, [isSingleProjectMode, taskLookup, taskListCollapsed, collapsedColumns]);

  // Get the project name for single-project mode header
  const singleProjectName = useMemo(() => {
    if (!isSingleProjectMode) return null;
    const project = projects.find((p) => p.id === projectId);
    return project?.name || project?.slug || `Project ${projectId}`;
  }, [isSingleProjectMode, projects, projectId]);
  
  return (
    <>
      {/* Gantt today indicator styles */}
      <style>{`
        .today-highlight {
          background-color: rgba(239, 68, 68, 0.12) !important;
          position: relative;
        }
        .today-highlight::after {
          content: '';
          position: absolute;
          top: 0;
          left: 50%;
          transform: translateX(-50%);
          width: 2px;
          height: 100%;
          background-color: rgb(239, 68, 68);
          z-index: 5;
        }
        .dark .today-highlight {
          background-color: rgba(239, 68, 68, 0.15) !important;
        }
        /* Add resize cursor zones on task bar edges */
        .wx-bar:not(.wx-milestone) {
          cursor: move;
        }
        /* Left justify header date cells */
        .wx-scale .wx-cell {
          justify-content: flex-start !important;
          padding-left: 8px !important;
        }
        .wx-bar:not(.wx-milestone)::before,
        .wx-bar:not(.wx-milestone)::after {
          content: '';
          position: absolute;
          top: 0;
          width: 8px;
          height: 100%;
          cursor: ew-resize;
          z-index: 10;
        }
        .wx-bar:not(.wx-milestone)::before {
          left: 0;
        }
        .wx-bar:not(.wx-milestone)::after {
          right: 0;
        }
      `}</style>
      <div className={combineClassNames("flex h-[calc(100vh-4rem)]", className)}>
      {/* Project Selector Sidebar - Collapsible */}
      {showSelector && (
        <div className={combineClassNames(
          "shrink-0 transition-all duration-300 ease-in-out",
          selectorCollapsed ? "w-10" : (compact ? "w-56" : "w-72")
        )}>
          <div className="sticky top-0 h-full">
            {selectorCollapsed ? (
              // Collapsed state - just a toggle button
              <div className="flex h-full flex-col items-center rounded-l-2xl border border-gray-200 bg-white py-3 dark:border-gray-700 dark:bg-gray-900">
                <button
                  type="button"
                  onClick={() => setSelectorCollapsed(false)}
                  className="rounded-lg p-2 text-gray-500 transition hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
                  title="Expand project list"
                >
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                <span className="mt-2 text-xs font-medium text-gray-500 dark:text-gray-400 [writing-mode:vertical-lr]">
                  Projects ({selectedProjectIds.length})
                </span>
              </div>
            ) : (
              // Expanded state - full selector with collapse button
              <div className="relative h-full">
                <button
                  type="button"
                  onClick={() => setSelectorCollapsed(true)}
                  className="absolute -right-3 top-3 z-10 rounded-full border border-gray-200 bg-white p-1 text-gray-500 shadow-sm transition hover:bg-gray-100 hover:text-gray-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-200"
                  title="Collapse project list"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
                <GanttProjectSelector
                  projects={projects}
                  selectedIds={selectedProjectIds}
                  onSelectionChange={setSelectedProjectIds}
                  isLoading={isLoadingProjects}
                  disabled={isRefreshing}
                />
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Gantt Chart Area */}
      <div className="min-w-0 flex-1 flex flex-col">
        <section className={combineClassNames(
          "flex flex-1 min-h-0 flex-col rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-900",
        )}>
          {/* Header */}
          <div className={combineClassNames(
            "flex shrink-0 flex-wrap items-center justify-between gap-4 border-b border-gray-200 dark:border-gray-700",
            compact ? "px-4 py-3" : "px-6 py-4"
          )}>
            <div>
              <h2 className={combineClassNames(
                "font-semibold text-gray-900 dark:text-white",
                compact ? "text-base" : "text-lg"
              )}>
                {isSingleProjectMode ? singleProjectName : "Project Timeline"}
              </h2>
              <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
                {selectedProjectIds.length === 0
                  ? "Select projects to view tasks"
                  : `${ganttData.tasks.length} task${ganttData.tasks.length !== 1 ? "s" : ""}${
                      !isSingleProjectMode ? ` across ${selectedProjectIds.length} project${selectedProjectIds.length > 1 ? "s" : ""}` : ""
                    }`}
              </p>
            </div>
            
            <div className="flex items-center gap-3">
              {/* Scale buttons */}
              <div className="flex gap-1 rounded-lg bg-gray-100 p-1 dark:bg-gray-800">
                {scaleButtons.map((button) => (
                  <button
                    key={button.id}
                    type="button"
                    onClick={() => setScalePreset(button.id)}
                    className={combineClassNames(
                      "rounded-md px-3 py-1.5 text-xs font-medium transition",
                      scalePreset === button.id
                        ? "bg-white text-gray-900 shadow-sm dark:bg-gray-700 dark:text-white"
                        : "text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
                    )}
                  >
                    {button.label}
                  </button>
                ))}
              </div>
              
              {/* Task list collapse toggle */}
              <button
                type="button"
                onClick={() => setTaskListCollapsed(!taskListCollapsed)}
                className={combineClassNames(
                  "inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium shadow-sm transition",
                  taskListCollapsed
                    ? "border-indigo-300 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:border-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-200 dark:hover:bg-indigo-900/50"
                    : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
                )}
                title={taskListCollapsed ? "Expand task list columns" : "Collapse task list columns"}
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  {taskListCollapsed ? (
                    // Expand icon (columns expanding right)
                    <path d="M9 4h11M9 8h7M9 12h4M9 16h7M9 20h11M4 12l3-3v6l-3-3z" strokeLinecap="round" strokeLinejoin="round"/>
                  ) : (
                    // Collapse icon (columns collapsing left)
                    <path d="M4 4h11M4 8h7M4 12h4M4 16h7M4 20h11M21 12l-3-3v6l3-3z" strokeLinecap="round" strokeLinejoin="round"/>
                  )}
                </svg>
                {taskListCollapsed ? "Show List" : "Hide List"}
              </button>
              
              {/* Refresh button */}
              <button
                type="button"
                onClick={handleManualRefresh}
                disabled={isRefreshing || isLoading}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
                title={`Auto-refresh every ${AUTO_REFRESH_INTERVAL_MS / 60000} minutes${isEditModalOpen ? " (paused while editing)" : ""}`}
              >
                <svg
                  className={combineClassNames("h-4 w-4", isRefreshing && "animate-spin")}
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    stroke="currentColor"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                {isRefreshing ? "Refreshing..." : "Refresh"}
              </button>
              
              {/* Print button */}
              <button
                type="button"
                onClick={handlePrint}
                disabled={ganttData.tasks.length === 0}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
                title="Print Gantt chart"
              >
                <svg
                  className="h-4 w-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M6 9V2h12v7M6 18H4a2 2 0 01-2-2v-5a2 2 0 012-2h16a2 2 0 012 2v5a2 2 0 01-2 2h-2M6 14h12v8H6v-8z"
                    stroke="currentColor"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                Print
              </button>
              
              {/* Export SVG button */}
              <button
                type="button"
                onClick={handleExportSVG}
                disabled={ganttData.tasks.length === 0}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
                title="Export as scalable vector graphic (SVG)"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                SVG
              </button>              
              {/* Set Baseline button */}
              <button
                type="button"
                onClick={handleSetBaseline}
                disabled={ganttData.tasks.length === 0}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
                title="Save current dates as baseline"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z" strokeLinecap="round" strokeLinejoin="round"/>
                  <polyline points="17 21 17 13 7 13 7 21" strokeLinecap="round" strokeLinejoin="round"/>
                  <polyline points="7 3 7 8 15 8" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                Baseline
              </button>
              
              {/* Undo/Redo buttons */}
              <div className="flex gap-1 rounded-lg bg-gray-100 p-1 dark:bg-gray-800">
                <button
                  type="button"
                  onClick={handleUndo}
                  disabled={undoStack.length === 0}
                  className="rounded-md p-1.5 text-gray-600 transition hover:bg-white hover:text-gray-900 hover:shadow-sm disabled:cursor-not-allowed disabled:opacity-40 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
                  title={`Undo (${undoStack.length}) - Ctrl+Z`}
                >
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 7v6h6M21 17a9 9 0 00-9-9 9 9 0 00-6.36 2.64L3 13" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>
                <button
                  type="button"
                  onClick={handleRedo}
                  disabled={redoStack.length === 0}
                  className="rounded-md p-1.5 text-gray-600 transition hover:bg-white hover:text-gray-900 hover:shadow-sm disabled:cursor-not-allowed disabled:opacity-40 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
                  title={`Redo (${redoStack.length}) - Ctrl+Shift+Z`}
                >
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 7v6h-6M3 17a9 9 0 019-9 9 9 0 016.36 2.64L21 13" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>
              </div>
              
              <span className="text-xs text-gray-400 dark:text-gray-500">
                {formatLastRefresh(lastRefreshTime)}
              </span>
            </div>
          </div>
          
          {/* Error display */}
          {error && (
            <div className="mx-6 mt-4 flex shrink-0 items-center justify-between rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/30 dark:text-rose-200">
              <span>{error}</span>
              <button
                type="button"
                onClick={() => refetchAll()}
                className="rounded-md border border-rose-300 px-3 py-1 text-xs font-semibold transition hover:bg-rose-100 dark:border-rose-700 dark:hover:bg-rose-900/50"
              >
                Retry
              </button>
            </div>
          )}
          
          {/* Gantt Chart */}
          <DualScrollbar className="min-w-0 min-h-0 flex-1 rounded-b-2xl" scrollSelector=".wx-chart">
            {selectedProjectIds.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <svg
                  className="mb-4 h-16 w-16 text-gray-300 dark:text-gray-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1}
                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                  />
                </svg>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                  No projects selected
                </h3>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  {showSelector 
                    ? "Select one or more projects from the sidebar to view their tasks"
                    : "No project configured for this view"}
                </p>
              </div>
            ) : isLoading && ganttData.tasks.length === 0 ? (
              <div className="flex h-full items-center justify-center">
                <div className="text-center">
                  <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600 mx-auto" />
                  <p className="text-sm text-gray-500 dark:text-gray-400">Loading tasks...</p>
                </div>
              </div>
            ) : ganttData.tasks.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <svg
                  className="mb-4 h-16 w-16 text-gray-300 dark:text-gray-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1}
                    d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
                  />
                </svg>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                  No tasks found
                </h3>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  {isSingleProjectMode
                    ? "This project has no active actions"
                    : "The selected projects have no active actions"}
                </p>
              </div>
            ) : (
              <div ref={ganttContainerRef} className="h-full w-full [&_.wx-gantt]:!h-full [&_.wx-gantt]:!w-full [&_.wx-scale]:!sticky [&_.wx-scale]:!top-0 [&_.wx-scale]:!z-10 [&_.wx-scale]:!bg-white [&_.wx-scale]:dark:!bg-gray-900">
                <Willow>
                  <Gantt
                    key={ganttKey}
                    tasks={ganttData.tasks}
                    links={ganttData.links}
                    columns={activeColumns}
                    scales={activeScales}
                    start={dateRange.start}
                    end={dateRange.end}
                    onShowEditor={handleShowEditor}
                    onItemDoubleClick={handleShowEditor}
                    onUpdateTask={handleSvarUpdateTask}
                    onAddLink={handleAddLink}
                    onDeleteLink={handleDeleteLink}
                    onUpdateLink={handleUpdateLink}
                    cellHeight={38}
                    taskTemplate={GanttTaskTemplate}
                    highlightTime={(date: Date, unit: 'day' | 'hour') => {
                      // Highlight today's column
                      const today = new Date();
                      if (unit === 'day' && 
                          date.getFullYear() === today.getFullYear() &&
                          date.getMonth() === today.getMonth() &&
                          date.getDate() === today.getDate()) {
                        return 'today-highlight';
                      }
                      return '';
                    }}
                    init={(api) => {
                      console.log("[Gantt] init callback called, api:", api);
                      ganttApiRef.current = api;
                      api.detach(GANTT_COLOR_EVENT_TAG);
                      const rerender = () => scheduleColorRefresh();
                      api.on("render-data", rerender, { tag: GANTT_COLOR_EVENT_TAG });
                      // Intercept update-task to catch the event before it's processed
                      api.intercept("update-task", (ev: { id: string | number; task: Partial<ITask>; diff?: number; inProgress?: boolean; eventSource?: string }) => {
                        console.log("[Gantt API INTERCEPT] update-task event", {
                          id: ev.id,
                          task: ev.task,
                          diff: ev.diff,
                          inProgress: ev.inProgress,
                          eventSource: ev.eventSource,
                          hasStart: ev.task?.start !== undefined,
                          hasEnd: ev.task?.end !== undefined,
                        });
                        return ev; // Must return the event to continue processing
                      }, { tag: GANTT_COLOR_EVENT_TAG });
                      // Handle task updates from drag-and-drop via API event
                      api.on("update-task", (ev: { id: string | number; task: Partial<ITask> }) => {
                        console.log("[Gantt API] update-task event fired", ev);
                        if (handleSvarUpdateTaskRef.current) {
                          handleSvarUpdateTaskRef.current(ev);
                        }
                        rerender();
                      }, { tag: GANTT_COLOR_EVENT_TAG });
                      // Intercept drag-task to see what happens during drag
                      api.intercept("drag-task", (ev: { id?: string | number; width?: number; left?: number; top?: number; inProgress?: boolean }) => {
                        console.log("[Gantt API INTERCEPT] drag-task event", {
                          id: ev.id,
                          width: ev.width,
                          left: ev.left,
                          top: ev.top,
                          inProgress: ev.inProgress,
                          eventType: ev.width !== undefined ? "RESIZE (edge drag)" : "MOVE (center drag)"
                        });
                        return ev;
                      }, { tag: GANTT_COLOR_EVENT_TAG });
                      // Listen for drag-task events (might fire during drag)
                      api.on("drag-task", (ev: { id?: string | number; width?: number; left?: number; inProgress?: boolean }) => {
                        console.log("[Gantt API] drag-task event fired", {
                          id: ev.id,
                          width: ev.width,
                          left: ev.left,
                          inProgress: ev.inProgress
                        });
                      }, { tag: GANTT_COLOR_EVENT_TAG });
                      // Intercept move-task to prevent vertical row reordering
                      api.intercept("move-task", (ev: unknown) => {
                        console.log("[Gantt API INTERCEPT] move-task event blocked (vertical reorder disabled)", ev);
                        return false; // Return false to prevent vertical reordering
                      }, { tag: GANTT_COLOR_EVENT_TAG });
                      // Listen for move-task events (for logging only)
                      api.on("move-task", (ev: unknown) => {
                        console.log("[Gantt API] move-task event fired", ev);
                      }, { tag: GANTT_COLOR_EVENT_TAG });
                      // Also rerender when links change
                      api.on("add-link", rerender, { tag: GANTT_COLOR_EVENT_TAG });
                      api.on("delete-link", rerender, { tag: GANTT_COLOR_EVENT_TAG });
                      scheduleColorRefresh();
                    }}
                  />
                </Willow>
              </div>
            )}
          </DualScrollbar>
        </section>
      </div>
      
      {/* Edit Modal */}
      <KanbanTaskModal
        mode="edit"
        isOpen={isEditModalOpen && Boolean(editingTask)}
        title="Edit task"
        description="Update task details."
        isSaving={isSavingEdit}
        submitLabel={isSavingEdit ? "Saving..." : "Save changes"}
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
        assigneeUIMode={editAssigneeUIMode}
        onAssigneeUIModeChange={setEditAssigneeUIMode}
      />
      
      {/* Link Context Menu */}
      {linkContextMenu && (
        <div
          style={{
            position: "fixed",
            top: linkContextMenu.y,
            left: linkContextMenu.x,
            zIndex: 9999,
            backgroundColor: "white",
            borderRadius: "6px",
            boxShadow: "0 4px 12px rgba(0, 0, 0, 0.15)",
            border: "1px solid #e5e7eb",
            padding: "4px 0",
            minWidth: "140px",
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={async () => {
              const linkId = linkContextMenu.linkId;
              setLinkContextMenu(null);
              await handleDeleteLink({ id: linkId });
            }}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              width: "100%",
              padding: "8px 12px",
              textAlign: "left",
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: "14px",
              color: "#dc2626",
            }}
            onMouseEnter={(e) => {
              (e.target as HTMLElement).style.backgroundColor = "#fef2f2";
            }}
            onMouseLeave={(e) => {
              (e.target as HTMLElement).style.backgroundColor = "transparent";
            }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 6h18" />
              <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
              <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
            </svg>
            Delete Link
          </button>
        </div>
      )}
    </div>
    </>
  );
};

export default UnifiedGantt;

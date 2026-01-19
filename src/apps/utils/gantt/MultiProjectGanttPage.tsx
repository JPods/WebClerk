/**
 * Multi-Project Gantt Page
 * 
 * This page allows users to select multiple active projects and view all
 * their actions in a SVAR Gantt chart. Actions without start dates default
 * to today - 5 days.
 */

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Gantt, Willow } from "@svar-ui/react-gantt";
import type { IApi, IColumnConfig, ITask } from "@svar-ui/react-gantt";
import "@svar-ui/react-gantt/all.css";
import PageBreadcrumb from "../../../components/common/PageBreadCrumb";
import KanbanTaskModal from "../../utils/kanban/KanbanTaskModal";
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
} from "./GanttPage";

import { GanttProjectSelector, getProjectColor } from "./GanttProjectSelector";
import { useGanttData, AUTO_REFRESH_INTERVAL_MS } from "./useGanttData";
import type { GanttMappedTask } from "./ganttDataMapper";
import { getGanttDateRange } from "./ganttDataMapper";

// Gantt column configuration
const ganttDateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
});

const formatDate = (value?: Date) => (value ? ganttDateFormatter.format(value) : "-");

const ganttColumns: IColumnConfig[] = [
  {
    id: "text",
    header: "Task",
    width: 200,
    flexgrow: 1,
  },
  {
    id: "projectName",
    header: "Project",
    width: 120,
    template: (task: ITask) => (task as GanttMappedTask).projectName || "-",
  },
  {
    id: "start",
    header: "Start",
    width: 80,
    align: "center",
    template: (task: ITask) => formatDate(task.start as Date),
  },
  {
    id: "end",
    header: "End",
    width: 80,
    align: "center",
    template: (task: ITask) => formatDate(task.end as Date),
  },
  {
    id: "progress",
    header: "%",
    width: 50,
    align: "center",
    template: (task: ITask) => `${Math.round((task.progress || 0) * 100)}%`,
  },
];

// Scale presets
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

// Color utilities
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

// Progress utilities
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

// Type definitions
type TaskColorInfo = {
  color: string;
  textColor: string;
  type?: ITask["type"];
};

const GANTT_COLOR_EVENT_TAG = "gantt-project-colors";

const MultiProjectGanttPage: React.FC = () => {
  // Project selection state
  const [selectedProjectIds, setSelectedProjectIds] = useState<string[]>([]);
  
  // Use the custom hook for data fetching
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  
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
  } = useGanttData({
    selectedProjectIds,
    enabled: true,
    autoRefresh: true,
    isModalOpen: isEditModalOpen,
  });
  
  // Gantt display state
  const [scalePreset, setScalePreset] = useState<ScalePresetKey>("month");
  const [ganttKey, setGanttKey] = useState(0);
  const activeScales = scalePresets[scalePreset];
  
  // Calculate date range for the Gantt chart
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

  // Refs
  const ganttContainerRef = useRef<HTMLDivElement | null>(null);
  const ganttApiRef = useRef<IApi | null>(null);
  const taskColorMapRef = useRef<Map<string, TaskColorInfo>>(new Map());

  // Column options for select - need id/title format for KanbanTaskModal
  const columnOptions = useMemo(() => {
    return board.columnOrder
      .map((colId) => board.columns[colId])
      .filter((col): col is NonNullable<typeof col> => Boolean(col))
      .map((col) => ({ id: col.id, title: col.title }));
  }, [board.columnOrder, board.columns]);

  // Difficulty and progress options - need to include current value
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

  // Derive form state from a task (similar to SvarGanttPage)
  const deriveFormStateFromTask = useCallback(
    (task: KanbanTask): TaskFormState => {
      const taskColumn = Object.values(board.columns).find((column) => column?.taskIds.includes(task.id));
      const normalizedStart = normalizeIncomingDateValue((task as any).dt_start);
      const normalizedEnd = normalizeIncomingDateValue((task as any).dt_end);
      const normalizedDue = normalizeIncomingDateValue((task as any).dt_deadline);
      const shouldFallbackStart = !normalizedStart && !normalizedEnd && !normalizedDue;
      const resolvedStartDate = shouldFallbackStart ? formatDateTimeLocal(new Date()) : normalizedStart;
      const resolvedEndDate = normalizedEnd || "";
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
         dt_expected: resolvedEndDate,
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

      // Create a KanbanTask-like object from the Gantt task
      const kanbanTask: KanbanTask = {
        id: String(ganttTask.id),
        title: ganttTask.text || "",
        description: ganttTask.details || "",
        priority: (ganttTask.priority as TaskPriority) || "medium",
        status: ganttTask.columnTitle || "Uncategorized",
         dt_deadline: ganttTask.end instanceof Date ? ganttTask.end.toISOString() : undefined,
         dt_start: ganttTask.start instanceof Date ? ganttTask.start.toISOString() : undefined,
         dt_end: ganttTask.end instanceof Date ? ganttTask.end.toISOString() : undefined,
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
    [ganttData.tasks, deriveFormStateFromTask]
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
         : baseTask.assigned_to?.map((assignment: any) => ({ name: assignment.name })) ?? [];

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
      if (!id) return false;

      try {
        const payload: Record<string, unknown> = {
          model_name: "action",
          id: String(id),
        };

        if (task.start instanceof Date) {
          payload["dt_start"] = { mode: "update", value: task.start.getTime() };
        }
        if (task.end instanceof Date) {
          payload["dt_end"] = { mode: "update", value: task.end.getTime() };
          payload["dt_deadline"] = { mode: "update", value: task.end.getTime() };
        }
        if (typeof task.progress === "number") {
          payload["prefs.userdefined.progress"] = {
            mode: "update",
            value: Math.round(task.progress * 100),
          };
        }

        await patchAction(payload);
        return true;
      } catch (error) {
        console.error("Failed to update task:", error);
        return false;
      }
    },
    []
  );

  // Force Gantt re-render when selection changes
  useEffect(() => {
    setGanttKey((prev) => prev + 1);
  }, [selectedProjectIds]);
  
  useEffect(() => {
    refreshTaskColorCache();
    scheduleColorRefresh();
  }, [ganttData.tasks, refreshTaskColorCache, scheduleColorRefresh]);
  
  // Format refresh time
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
  
  const handleManualRefresh = useCallback(async () => {
    await refetchActions();
  }, [refetchActions]);
  
  const isLoading = isLoadingProjects || isLoadingActions;
  const error = projectsError || actionsError;
  
  return (
    <div className="mx-auto max-w-full space-y-5 px-4 py-4 md:px-6 lg:px-8 2xl:max-w-screen-2xl">
      <PageBreadcrumb pageTitle="Multi-Project Gantt Chart" />
      
      <div className="flex gap-6">
        {/* Project Selector Sidebar */}
        <div className="w-72 shrink-0">
          <div className="sticky top-4 h-[calc(100vh-8rem)]">
            <GanttProjectSelector
              projects={projects}
              selectedIds={selectedProjectIds}
              onSelectionChange={setSelectedProjectIds}
              isLoading={isLoadingProjects}
              disabled={isRefreshing}
            />
          </div>
        </div>
        
        {/* Gantt Chart Area */}
        <div className="min-w-0 flex-1">
          <section className="rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-900">
            {/* Header */}
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-200 px-6 py-4 dark:border-gray-700">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Project Timeline
                </h2>
                <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
                  {selectedProjectIds.length === 0
                    ? "Select projects from the sidebar to view tasks"
                    : `${ganttData.tasks.length} tasks across ${selectedProjectIds.length} project${selectedProjectIds.length > 1 ? "s" : ""}`}
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
                
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  {formatLastRefresh(lastRefreshTime)}
                </span>
              </div>
            </div>
            
            {/* Error display */}
            {error && (
              <div className="mx-6 mt-4 flex items-center justify-between rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/30 dark:text-rose-200">
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
            <div className="min-h-screen overflow-y-auto overflow-x-hidden rounded-b-2xl">
              {selectedProjectIds.length === 0 ? (
                <div className="flex h-96 flex-col items-center justify-center text-center">
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
                    Select one or more projects from the sidebar to view their tasks
                  </p>
                </div>
              ) : isLoading && ganttData.tasks.length === 0 ? (
                <div className="flex h-96 items-center justify-center">
                  <div className="text-center">
                    <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600 mx-auto" />
                    <p className="text-sm text-gray-500 dark:text-gray-400">Loading tasks...</p>
                  </div>
                </div>
              ) : ganttData.tasks.length === 0 ? (
                <div className="flex h-96 flex-col items-center justify-center text-center">
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
                    The selected projects have no active actions
                  </p>
                </div>
              ) : (
                <div ref={ganttContainerRef}>
                  <Willow>
                    <Gantt
                      key={ganttKey}
                      tasks={ganttData.tasks}
                      links={ganttData.links}
                      columns={ganttColumns}
                      scales={activeScales}
                      start={dateRange.start}
                      end={dateRange.end}
                      onShowEditor={handleShowEditor}
                      onItemDoubleClick={handleShowEditor}
                      onUpdateTask={handleSvarUpdateTask}
                      init={(api) => {
                        ganttApiRef.current = api;
                        api.detach(GANTT_COLOR_EVENT_TAG);
                        const rerender = () => scheduleColorRefresh();
                        api.on("render-data", rerender, { tag: GANTT_COLOR_EVENT_TAG });
                        api.on("update-task", rerender, { tag: GANTT_COLOR_EVENT_TAG });
                        scheduleColorRefresh();
                      }}
                    />
                  </Willow>
                </div>
              )}
            </div>
          </section>
        </div>
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
      />
    </div>
  );
};

export default MultiProjectGanttPage;

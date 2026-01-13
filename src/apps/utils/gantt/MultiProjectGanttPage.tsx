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
import KanbanTaskModal from "../../../components/kanban/KanbanTaskModal";
import type { TaskFormEditableField, TaskFormState, TranslationFormEntry } from "../../../components/kanban/taskFormTypes";
import { patchAction } from "../../../api/userProfile";
import { createEmptyBoardData } from "../kanban/kanbanDataMapper";
import type { BoardData, KanbanTask, TaskPriority } from "../../../type/kanban";
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
  createTranslationEntry,
  extendNumericOptionStrings,
  findNextLanguageCode,
  getLanguageLabel,
  normalizeLanguageCode,
  normalizeNumericSelectValue,
  priorityOptions,
  toTimestampMilliseconds,
  updateTaskFormState,
} from "../kanban/KanbanGanttPage";

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
  { id: "text", header: "Task", flexgrow: 1, sort: true },
  {
    id: "projectName",
    header: "Project",
    width: 140,
    sort: true,
    template: (task: ITask) => (task as GanttMappedTask).projectName || "-",
  },
  {
    id: "start",
    header: "Start",
    width: 100,
    align: "center",
    sort: true,
    template: (task: ITask) => formatDate(task.start),
  },
  {
    id: "duration",
    header: "Days",
    width: 60,
    align: "center",
    template: (task: ITask) => (task.duration ? `${task.duration}` : "-"),
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

const formatDateTimeLocal = (date: Date): string =>
  `${date.getFullYear()}-${padTwoDigits(date.getMonth() + 1)}-${padTwoDigits(date.getDate())}T${padTwoDigits(
    date.getHours()
  )}:${padTwoDigits(date.getMinutes())}`;

const createFallbackEndFromStart = (startValue: string): string => {
  if (!startValue) return "";
  const parsed = new Date(startValue);
  if (Number.isNaN(parsed.getTime())) return "";
  const adjusted = new Date(parsed.getTime());
  adjusted.setHours(adjusted.getHours() + 1);
  return formatDateTimeLocal(adjusted);
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
  
  // Debug: Log ganttData when it changes
  useEffect(() => {
    if (ganttData.tasks.length > 0) {
      console.log("[MultiProjectGantt] Tasks loaded:", ganttData.tasks.length);
      console.log("[MultiProjectGantt] Sample task:", {
        id: ganttData.tasks[0].id,
        text: ganttData.tasks[0].text,
        start: ganttData.tasks[0].start,
        end: ganttData.tasks[0].end,
        duration: ganttData.tasks[0].duration,
        startType: typeof ganttData.tasks[0].start,
        startIsDate: ganttData.tasks[0].start instanceof Date,
      });
    }
  }, [ganttData.tasks]);
  
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
  const ganttContainerRef = useRef<HTMLDivElement>(null);
  const ganttApiRef = useRef<IApi | null>(null);
  const taskColorMapRef = useRef<Map<string, TaskColorInfo>>(new Map());
  const colorRefreshTimerRef = useRef<number | null>(null);
  
  // Progress update refs
  const progressUpdateQueueRef = useRef<Set<string>>(new Set());
  const pendingProgressPayloadRef = useRef<Map<string, Record<string, unknown>>>(new Map());
  const progressDebounceTimersRef = useRef<Map<string, number>>(new Map());
  
  // Memoized values
  const resolveDefaultColumnId = useCallback(
    () => board.columnOrder[0] ?? FALLBACK_COLUMN_ID,
    [board.columnOrder]
  );
  
  const columnOptions = useMemo(
    () =>
      board.columnOrder
        .map((columnId) => board.columns[columnId])
        .filter((column): column is NonNullable<typeof column> => Boolean(column))
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
      if (!task) return;
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
  }, [board.tasks]);
  
  // Translation handlers
  const updateEditTranslations = useCallback(
    (updater: (current: TranslationFormEntry[]) => TranslationFormEntry[]) => {
      setEditTaskState((prev) => ({
        ...prev,
        translations: updater(prev.translations),
      }));
    },
    []
  );
  
  const handleEditTranslationFieldChange = useCallback(
    (entryId: string, field: "language" | "title" | "description", value: string) => {
      updateEditTranslations((current) =>
        current.map((entry) => {
          if (entry.id !== entryId) return entry;
          if (field === "language") {
            const normalized = normalizeLanguageCode(value);
            if (!normalized) return { ...entry, language: normalized };
            const duplicate = current.some(
              (other) => other.id !== entryId && normalizeLanguageCode(other.language) === normalized
            );
            if (duplicate) return entry;
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
      if (editTaskState.translations.length <= 1) return;
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
    if (value !== "__custom") setEditCustomLanguage("");
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
  
  const handleEditTaskChange = useCallback((field: TaskFormEditableField, value: string) => {
    setEditTaskState((prev) => updateTaskFormState(prev, field, value));
  }, []);
  
  // Derive form state from Gantt task
  const deriveFormStateFromGanttTask = useCallback(
    (task: GanttMappedTask): TaskFormState => {
      const normalizedStart = task.start ? formatDateTimeLocal(task.start) : "";
      const normalizedEnd = task.end ? formatDateTimeLocal(task.end) : "";
      const shouldFallbackStart = !normalizedStart && !normalizedEnd;
      const resolvedStartDate = shouldFallbackStart ? formatDateTimeLocal(new Date()) : normalizedStart;
      const resolvedEndDate = normalizedEnd || createFallbackEndFromStart(resolvedStartDate);
      const resolvedDueDate = calculateDueDate(resolvedStartDate, resolvedEndDate);
      const normalizedProgressValue = toProgressPercentage(task.progress);
      const normalizedProgress = normalizeNumericSelectValue(normalizedProgressValue, DEFAULT_PROGRESS);
      const normalizedDifficulty = normalizeNumericSelectValue(
        undefined,
        DEFAULT_DIFFICULTY
      );
      
      // Create minimal translation entry
      const translations: TranslationFormEntry[] = [
        createTranslationEntry("en", task.text, task.details || ""),
      ];
      
      return {
        translations,
        columnId: task.columnId || FALLBACK_COLUMN_ID,
        priority: (task.priority as TaskPriority) || "medium",
        dueDate: resolvedDueDate,
        startDate: resolvedStartDate,
        endDate: resolvedEndDate,
        assignee: task.assignee || "",
        difficulty: normalizedDifficulty,
        progress: normalizedProgress,
      };
    },
    []
  );
  
  // Build edit payload
  const buildEditActionPayload = useCallback(
    (state: TaskFormState, taskId: string): { payload: Record<string, unknown> } | { error: string } => {
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
        translationFields[`action.${language}`] = { mode: "update", value: value.title || "" };
        translationFields[`description.${language}`] = { mode: "update", value: value.description || "" };
      });
      translationFields.languages = { mode: "update", value: Array.from(normalized.keys()) };
      
      const dueTimestamp = toTimestampMilliseconds(state.dueDate);
      const startTimestamp = toTimestampMilliseconds(state.startDate);
      const endTimestamp = toTimestampMilliseconds(state.endDate);
      const resolvedProgress = Number(state.progress) || 0;
      
      const payloadItem: Record<string, unknown> = {
        model_name: "action",
        ...translationFields,
        kanban_column: { mode: "update", value: state.columnId },
        priority: { mode: "update", value: PRIORITY_TO_VALUE[state.priority] },
        dt_due: { mode: "update", value: dueTimestamp },
        dt_start: { mode: "update", value: startTimestamp },
        dt_end: { mode: "update", value: endTimestamp },
        progress: { mode: "update", value: resolvedProgress },
        id: taskId,
      };
      
      if (state.assignee) {
        payloadItem.assigned_to = { mode: "update", value: [{ name: state.assignee }] };
      }
      
      return { payload: payloadItem };
    },
    []
  );
  
  // Open edit modal from Gantt task
  const handleOpenEditModal = useCallback(
    (ganttTask: GanttMappedTask) => {
      // Convert GanttMappedTask to a minimal KanbanTask for the modal
      const kanbanTask: KanbanTask = {
        id: ganttTask.apiId,
        title: ganttTask.text || "Untitled",
        description: ganttTask.details,
        priority: (ganttTask.priority as TaskPriority) || "medium",
        status: "In progress",
        startDate: ganttTask.start?.toISOString(),
        endDate: ganttTask.end?.toISOString(),
        progress: ganttTask.progress ? ganttTask.progress * 100 : 0,
        assignee: ganttTask.assignee,
      };
      
      setEditingTask(kanbanTask);
      setEditTaskState(deriveFormStateFromGanttTask(ganttTask));
      setEditModalError(null);
      setEditLanguagePickerOpen(false);
      setEditLanguageSelection("");
      setEditCustomLanguage("");
      setEditLanguagePickerError(null);
      setIsEditModalOpen(true);
    },
    [deriveFormStateFromGanttTask]
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
  
  // Gantt event handlers
  const handleShowEditor = useCallback(
    (event: { id?: string | number }) => {
      if (!event?.id) return;
      const taskId = String(event.id);
      const ganttTask = ganttData.tasks.find((t) => String(t.id) === taskId);
      if (ganttTask) {
        handleOpenEditModal(ganttTask);
      }
    },
    [ganttData.tasks, handleOpenEditModal]
  );
  
  // Progress update handler
  const scheduleProgressUpdate = useCallback((taskId: string, progressValue: number) => {
    const ganttTask = ganttData.tasks.find((t) => String(t.id) === taskId);
    if (!ganttTask) return;
    
    const payload: Record<string, unknown> = {
      model_name: "action",
      id: ganttTask.apiId,
      "prefs.userdefined.progress": { mode: "update", value: progressValue },
    };
    
    pendingProgressPayloadRef.current.set(taskId, payload);
    progressUpdateQueueRef.current.add(taskId);
    
    const existingTimer = progressDebounceTimersRef.current.get(taskId);
    if (existingTimer) window.clearTimeout(existingTimer);
    
    const timer = window.setTimeout(() => {
      progressDebounceTimersRef.current.delete(taskId);
      if (!progressUpdateQueueRef.current.has(taskId)) return;
      
      const queued = pendingProgressPayloadRef.current.get(taskId);
      if (!queued) {
        progressUpdateQueueRef.current.delete(taskId);
        return;
      }
      
      patchAction(queued as any)
        .then(() => {
          console.log("Progress updated for task", taskId);
          progressUpdateQueueRef.current.delete(taskId);
          pendingProgressPayloadRef.current.delete(taskId);
        })
        .catch((error) => {
          console.error("Failed to update progress", taskId, error);
          progressUpdateQueueRef.current.delete(taskId);
          pendingProgressPayloadRef.current.delete(taskId);
        });
    }, 400);
    
    progressDebounceTimersRef.current.set(taskId, timer);
  }, [ganttData.tasks]);
  
  const handleSvarUpdateTask = useCallback(
    (event: { id?: string | number; task?: Partial<ITask> }) => {
      if (!event?.id || !event.task) return;
      
      const taskId = String(event.id);
      const { progress } = event.task;
      
      if (typeof progress === "number") {
        const progressPercentage = Math.round(progress * 100);
        scheduleProgressUpdate(taskId, progressPercentage);
      }
    },
    [scheduleProgressUpdate]
  );
  
  // Submit edit form
  const handleEditTaskSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!editingTask || isSavingEdit) return;
      
      setEditModalError(null);
      const result = buildEditActionPayload(editTaskState, editingTask.id);
      
      if ("error" in result) {
        setEditModalError(result.error);
        return;
      }
      
      setIsSavingEdit(true);
      try {
        await patchAction(result.payload as any);
        handleCloseEditModal();
        // Refresh data after successful save
        await refetchActions();
      } catch (error) {
        console.error("Failed to save task:", error);
        setEditModalError(error instanceof Error ? error.message : "Failed to save changes.");
      } finally {
        setIsSavingEdit(false);
      }
    },
    [editingTask, editTaskState, isSavingEdit, buildEditActionPayload, handleCloseEditModal, refetchActions]
  );
  
  // Color management
  const refreshTaskColorCache = useCallback(() => {
    const nextMap = new Map<string, TaskColorInfo>();
    ganttData.tasks.forEach((task) => {
      if (!task?.id) return;
      const taskId = String(task.id);
      const color = (task as any).color || getProjectColor(task.projectId, selectedProjectIds);
      if (!color) return;
      nextMap.set(taskId, {
        color,
        textColor: pickReadableTextColor(color),
        type: task.type,
      });
    });
    taskColorMapRef.current = nextMap;
  }, [ganttData.tasks, selectedProjectIds]);
  
  const applyColorsToChart = useCallback(() => {
    const container = ganttContainerRef.current;
    if (!container) return;
    const colorMap = taskColorMapRef.current;
    if (!colorMap.size) return;
    
    const bars = container.querySelectorAll<HTMLElement>(".wx-bar[data-id]");
    bars.forEach((bar) => {
      const identifier = bar.getAttribute("data-id");
      if (!identifier) return;
      const taskInfo = colorMap.get(identifier);
      if (!taskInfo) return;
      
      const { color, textColor } = taskInfo;
      bar.style.backgroundColor = color;
      bar.style.borderColor = color;
      
      const contentElement = bar.querySelector<HTMLElement>(".wx-content");
      if (contentElement) contentElement.style.color = textColor;
      
      const progressElement = bar.querySelector<HTMLElement>(".wx-progress-percent");
      if (progressElement) progressElement.style.backgroundColor = color;
    });
  }, []);
  
  const scheduleColorRefresh = useCallback(() => {
    if (colorRefreshTimerRef.current) {
      window.cancelAnimationFrame(colorRefreshTimerRef.current);
    }
    colorRefreshTimerRef.current = window.requestAnimationFrame(() => {
      refreshTaskColorCache();
      applyColorsToChart();
    });
  }, [refreshTaskColorCache, applyColorsToChart]);
  
  // Effects
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

export default MultiProjectGanttPage;

import { CSSProperties, FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import { KanbanColumn } from "../../components/kanban/KanbanColumn";
import type { BoardData, KanbanColumn as KanbanColumnType, KanbanTask, TaskPriority } from "../../type/kanban";
import type { DragItem, DropResult } from "../../components/kanban/dndTypes";
import { DRAG_TYPE_TASK } from "../../components/kanban/dndTypes";
import clsx from "clsx";
import { Actions, patchAction } from "../../api/userProfile";
import { createBoardDataFromApi, createEmptyBoardData, extractKanbanItems } from "./kanbanDataMapper";

const priorityPalette: Record<TaskPriority, string> = {
  low: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-300",
  medium: "bg-amber-500/10 text-amber-600 dark:text-amber-300",
  high: "bg-orange-500/10 text-orange-600 dark:text-orange-300",
  critical: "bg-rose-500/10 text-rose-600 dark:text-rose-300",
};

const PRIORITY_TO_VALUE: Record<TaskPriority, number> = {
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
};

const DEFAULT_LANGUAGE_ORDER = ["en", "ar", "bn", "es"];

const LANGUAGE_LABELS: Record<string, string> = {
  en: "English",
  ar: "Arabic",
  bn: "Bengali",
  es: "Spanish",
};

const getLanguageLabel = (code: string) => LANGUAGE_LABELS[code.toLowerCase()] ?? code.toUpperCase();

const createLocalId = () => {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `local-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
};

type TranslationFormEntry = {
  id: string;
  language: string;
  title: string;
  description: string;
};

type TaskFormState = {
  translations: TranslationFormEntry[];
  columnId: string;
  priority: TaskPriority;
  dueDate: string;
  startDate: string;
  endDate: string;
  assignee: string;
  difficulty: string;
  progress: string;
};

type TaskFormEditableField = Exclude<keyof TaskFormState, "translations">;

const DIFFICULTY_OPTIONS: readonly number[] = [1, 2, 3, 5, 8, 13, 21, 34, 55, 101];
const PROGRESS_OPTIONS: readonly number[] = [0, 5, 30, 50, 70, 90, 100];

const DEFAULT_DIFFICULTY = DIFFICULTY_OPTIONS[2] ?? DIFFICULTY_OPTIONS[0];
const DEFAULT_PROGRESS = PROGRESS_OPTIONS[0];

const DEFAULT_DIFFICULTY_STRING = String(DEFAULT_DIFFICULTY);
const DEFAULT_PROGRESS_STRING = String(DEFAULT_PROGRESS);

const createTranslationEntry = (language: string, title = "", description = ""): TranslationFormEntry => ({
  id: createLocalId(),
  language,
  title,
  description,
});

const normalizeLanguageCode = (code: string) => code.trim().toLowerCase();

const createInitialTaskFormState = (columnId: string): TaskFormState => ({
  translations: [createTranslationEntry(DEFAULT_LANGUAGE_ORDER[0])],
  columnId,
  priority: "medium",
  dueDate: "",
  startDate: "",
  endDate: "",
  assignee: "",
  difficulty: DEFAULT_DIFFICULTY_STRING,
  progress: DEFAULT_PROGRESS_STRING,
});

const findNextLanguageCode = (used: Set<string>, options: Array<{ value: string }>): string => {
  for (const code of DEFAULT_LANGUAGE_ORDER) {
    if (!used.has(code)) {
      return code;
    }
  }
  for (const option of options) {
    if (!used.has(option.value)) {
      return option.value;
    }
  }
  return "";
};

const createTranslationEntriesFromTask = (task: KanbanTask): TranslationFormEntry[] => {
  const languages = new Set<string>();
  task.languageCodes?.forEach((code) => languages.add(normalizeLanguageCode(code)));
  Object.keys(task.titleTranslations ?? {}).forEach((code) => languages.add(normalizeLanguageCode(code)));
  Object.keys(task.descriptionTranslations ?? {}).forEach((code) => languages.add(normalizeLanguageCode(code)));

  if (languages.size === 0) {
    languages.add("en");
  }

  const orderedLanguages = Array.from(languages).sort((a, b) => {
    const aIndex = DEFAULT_LANGUAGE_ORDER.indexOf(a);
    const bIndex = DEFAULT_LANGUAGE_ORDER.indexOf(b);
    if (aIndex === -1 && bIndex === -1) return a.localeCompare(b);
    if (aIndex === -1) return 1;
    if (bIndex === -1) return -1;
    return aIndex - bIndex;
  });

  return orderedLanguages.map((language) => {
    const fallbackTitle = language === "en" ? task.title : "";
    const fallbackDescription = language === "en" ? task.description ?? "" : "";
    return createTranslationEntry(
      language,
      task.titleTranslations?.[language] ?? fallbackTitle,
      task.descriptionTranslations?.[language] ?? fallbackDescription
    );
  });
};

interface OnDragEndArgs {
  item: DragItem;
  result: DropResult | null;
}

const priorityOptions: TaskPriority[] = ["low", "medium", "high", "critical"];

const handleBoardMove = (prev: BoardData, { item, result }: OnDragEndArgs): BoardData => {
  if (!result) return prev;

  const sourceColumn = prev.columns[item.sourceColumnId];
  const destinationColumn = prev.columns[result.columnId];

  if (!sourceColumn || !destinationColumn) return prev;

  const sourceIndex = sourceColumn.taskIds.indexOf(item.taskId);
  if (sourceIndex === -1) return prev;

  const destinationColumnId = result.columnId;
  const rawDestinationIndex = result.index;

  if (item.sourceColumnId === destinationColumnId && sourceIndex === rawDestinationIndex) {
    return prev;
  }

  const nextColumns: Record<string, KanbanColumnType> = { ...prev.columns };

  const removeFromSource = () => {
    const updated = [...sourceColumn.taskIds];
    updated.splice(sourceIndex, 1);
    nextColumns[sourceColumn.id] = { ...sourceColumn, taskIds: updated };
    return updated;
  };

  if (item.sourceColumnId === destinationColumnId) {
  const withoutTask = removeFromSource();
  let insertIndex = rawDestinationIndex;
    if (insertIndex > sourceIndex) {
      insertIndex -= 1;
    }
    const clampedIndex = Math.max(0, Math.min(insertIndex, withoutTask.length));
    const reordered = [...withoutTask];
    reordered.splice(clampedIndex, 0, item.taskId);

    if (sourceColumn.taskIds.join() === reordered.join()) {
      return prev;
    }

    nextColumns[sourceColumn.id] = { ...sourceColumn, taskIds: reordered };
    return { ...prev, columns: nextColumns };
  }

  removeFromSource();
  const destinationTaskIds = [...destinationColumn.taskIds];
  const clampedIndex = Math.max(0, Math.min(rawDestinationIndex, destinationTaskIds.length));
  destinationTaskIds.splice(clampedIndex, 0, item.taskId);

  nextColumns[destinationColumn.id] = { ...destinationColumn, taskIds: destinationTaskIds };

  return {
    ...prev,
    columns: nextColumns,
  };
};

const FALLBACK_COLUMN_ID = "column-uncategorized";

const padTwo = (value: number) => value.toString().padStart(2, "0");

const formatDateTimeLocalString = (date: Date) =>
  `${date.getFullYear()}-${padTwo(date.getMonth() + 1)}-${padTwo(date.getDate())}T${padTwo(date.getHours())}:${padTwo(
    date.getMinutes()
  )}`;

const parseDateTimeInputValue = (value?: string): Date | null => {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
};

const coerceDateFromUnknown = (value: unknown): Date | null => {
  if (value === null || value === undefined) {
    return null;
  }
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value;
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      return null;
    }
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }
    if (/^\d+$/.test(trimmed)) {
      const numeric = Number(trimmed);
      const date = trimmed.length <= 10 ? new Date(numeric * 1000) : new Date(numeric);
      return Number.isNaN(date.getTime()) ? null : date;
    }
    const parsed = new Date(trimmed);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }
  return null;
};

const normalizeIncomingDateValue = (value: unknown): string => {
  const date = coerceDateFromUnknown(value);
  return date ? formatDateTimeLocalString(date) : "";
};

const normalizeNumericSelectValue = (value: unknown, fallback: number): string => {
  if (value === null || value === undefined) {
    return String(fallback);
  }

  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) {
      return String(fallback);
    }
    const numeric = Number(trimmed);
    return Number.isNaN(numeric) ? String(fallback) : String(numeric);
  }

  const numeric = Number(value);
  return Number.isNaN(numeric) ? String(fallback) : String(numeric);
};

const extendNumericOptionStrings = (options: readonly number[], current: string): string[] => {
  const base = options.map((value) => String(value));
  if (current && !base.includes(current)) {
    return [...base, current];
  }
  return base;
};

const ensureEndAfterStart = (start: string, candidate: string): string => {
  const startDate = parseDateTimeInputValue(start);

  if (!candidate) {
    if (!startDate) {
      return "";
    }
    const adjusted = new Date(startDate.getTime());
    adjusted.setHours(adjusted.getHours() + 1);
    return formatDateTimeLocalString(adjusted);
  }

  const candidateDate = parseDateTimeInputValue(candidate);
  if (!startDate || !candidateDate) {
    return candidateDate ? formatDateTimeLocalString(candidateDate) : "";
  }
  if (candidateDate.getTime() <= startDate.getTime()) {
    const adjusted = new Date(startDate.getTime());
    adjusted.setHours(adjusted.getHours() + 1);
    return formatDateTimeLocalString(adjusted);
  }
  return formatDateTimeLocalString(candidateDate);
};

const calculateDueDate = (start: string, end: string): string => {
  const endDate = parseDateTimeInputValue(end);
  if (endDate) {
    return formatDateTimeLocalString(endDate);
  }
  const startDate = parseDateTimeInputValue(start);
  if (startDate) {
    const due = new Date(startDate.getTime());
    due.setDate(due.getDate() + 1);
    return formatDateTimeLocalString(due);
  }
  return "";
};

const toTimestampMilliseconds = (value: string): number | null => {
  const date = parseDateTimeInputValue(value);
  return date ? date.getTime() : null;
};

const updateTaskFormState = (
  prev: TaskFormState,
  field: TaskFormEditableField,
  value: string
): TaskFormState => {
  if (field === "startDate") {
    const next: TaskFormState = { ...prev, startDate: value };
    next.endDate = ensureEndAfterStart(value, prev.endDate);
    next.dueDate = calculateDueDate(next.startDate, next.endDate);
    return next;
  }

  if (field === "endDate") {
    const nextEnd = ensureEndAfterStart(prev.startDate, value);
    const next: TaskFormState = { ...prev, endDate: nextEnd };
    next.dueDate = calculateDueDate(next.startDate, next.endDate);
    return next;
  }

  if (field === "dueDate") {
    if (!value) {
      return { ...prev, dueDate: calculateDueDate(prev.startDate, prev.endDate) };
    }

    const parsedDue = parseDateTimeInputValue(value);
    if (!parsedDue) {
      return prev;
    }

    const endDate = parseDateTimeInputValue(prev.endDate);
    if (endDate && parsedDue.getTime() < endDate.getTime()) {
      return { ...prev, dueDate: formatDateTimeLocalString(endDate) };
    }

    const startDate = parseDateTimeInputValue(prev.startDate);
    if (!endDate && startDate && parsedDue.getTime() < startDate.getTime()) {
      return { ...prev, dueDate: formatDateTimeLocalString(startDate) };
    }

    return { ...prev, dueDate: formatDateTimeLocalString(parsedDue) };
  }

  if (field === "priority") {
    return { ...prev, priority: value as TaskPriority };
  }

  if (field === "columnId") {
    return { ...prev, columnId: value };
  }

  if (field === "assignee") {
    return { ...prev, assignee: value };
  }

  if (field === "difficulty") {
    return { ...prev, difficulty: value };
  }

  if (field === "progress") {
    return { ...prev, progress: value };
  }

  return prev;
};

const KanbanBoardPage: React.FC = () => {
  const [board, setBoard] = useState<BoardData>(() => createEmptyBoardData());
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<KanbanTask | null>(null);
  const [createTaskState, setCreateTaskState] = useState<TaskFormState>(() => createInitialTaskFormState(FALLBACK_COLUMN_ID));
  const [editTaskState, setEditTaskState] = useState<TaskFormState>(() => createInitialTaskFormState(FALLBACK_COLUMN_ID));
  const [columnsPerRow, setColumnsPerRow] = useState<number>(5);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [isSavingCreate, setIsSavingCreate] = useState<boolean>(false);
  const [isSavingEdit, setIsSavingEdit] = useState<boolean>(false);
  const [createModalError, setCreateModalError] = useState<string | null>(null);
  const [editModalError, setEditModalError] = useState<string | null>(null);
  const [createLanguagePickerOpen, setCreateLanguagePickerOpen] = useState<boolean>(false);
  const [createLanguageSelection, setCreateLanguageSelection] = useState<string>("");
  const [createCustomLanguage, setCreateCustomLanguage] = useState<string>("");
  const [createLanguagePickerError, setCreateLanguagePickerError] = useState<string | null>(null);
  const [editLanguagePickerOpen, setEditLanguagePickerOpen] = useState<boolean>(false);
  const [editLanguageSelection, setEditLanguageSelection] = useState<string>("");
  const [editCustomLanguage, setEditCustomLanguage] = useState<string>("");
  const [editLanguagePickerError, setEditLanguagePickerError] = useState<string | null>(null);

  const resolveDefaultColumnId = useCallback(
    () => board.columnOrder[0] ?? FALLBACK_COLUMN_ID,
    [board.columnOrder]
  );

  const handleDragEnd = useCallback(
    (item: DragItem, dropResult: DropResult | null) => {
      if (item.type !== DRAG_TYPE_TASK) return;
      setBoard((prev) => handleBoardMove(prev, { item, result: dropResult }));
    },
    []
  );

  const fetchActions = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const response = await Actions();
      if (!response || response.status !== 200) {
        throw new Error("Request failed");
      }

      const items = extractKanbanItems(response);
      if (items.length === 0) {
        setBoard(createEmptyBoardData());
      } else {
        setBoard(createBoardDataFromApi(items));
      }
    } catch (error) {
      console.error("Failed to fetch kanban actions", error);
      setFetchError("Unable to load kanban data. Displaying local state only.");
      setBoard(createEmptyBoardData());
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchActions();
  }, [fetchActions]);

  useEffect(() => {
    if (board.columnOrder.length === 0) {
      return;
    }
    setColumnsPerRow((prev) => {
      const baseline = prev > 1 ? prev : 5;
      const clamped = Math.min(Math.max(baseline, 1), Math.max(board.columnOrder.length, 1));
      return clamped;
    });
  }, [board.columnOrder]);

  useEffect(() => {
    const firstColumnId = resolveDefaultColumnId();
    setCreateTaskState((prev) => {
      if (board.columns[prev.columnId]) {
        return prev;
      }
      return {
        ...prev,
        columnId: firstColumnId,
      };
    });
  }, [board.columns, resolveDefaultColumnId]);

  const columns = useMemo(() =>
      board.columnOrder
        .map((columnId) => board.columns[columnId])
        .filter((column): column is KanbanColumnType => Boolean(column)),
    [board]
  );

  const columnOptions = useMemo(() => columns.map((column) => ({ id: column.id, title: column.title })), [columns]);
  const createDifficultyOptions = useMemo(
    () => extendNumericOptionStrings(DIFFICULTY_OPTIONS, createTaskState.difficulty),
    [createTaskState.difficulty]
  );
  const createProgressOptions = useMemo(
    () => extendNumericOptionStrings(PROGRESS_OPTIONS, createTaskState.progress),
    [createTaskState.progress]
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
  }, [board.tasks]);
  const columnDensityOptions = useMemo(() => {
    const maxOption = Math.max(5, columns.length || 1);
    const options: number[] = [];
    for (let count = 1; count <= Math.min(8, maxOption); count += 1) {
      options.push(count);
    }
    if (!options.includes(5)) {
      options.push(5);
    }
    return Array.from(new Set(options)).sort((a, b) => a - b);
  }, [columns.length]);

  const prioritySummary = useMemo(() => {
    const base: Record<TaskPriority, number> = {
      low: 0,
      medium: 0,
      high: 0,
      critical: 0,
    };

    Object.values(board.tasks).forEach((task) => {
      base[task.priority] += 1;
    });

    return base;
  }, [board.tasks]);

  const totalTasks = useMemo(() => Object.keys(board.tasks).length, [board.tasks]);

  const resetCreateState = useCallback(() => {
    const firstColumn = resolveDefaultColumnId();
    setCreateTaskState(createInitialTaskFormState(firstColumn));
    setCreateModalError(null);
    setCreateLanguagePickerOpen(false);
    setCreateLanguageSelection("");
    setCreateCustomLanguage("");
    setCreateLanguagePickerError(null);
  }, [resolveDefaultColumnId]);

  const handleOpenCreateModal = () => {
    resetCreateState();
    setIsCreateModalOpen(true);
  };

  const handleCloseCreateModal = () => {
    setIsCreateModalOpen(false);
    resetCreateState();
  };

  const handleOpenEditModal = (task: KanbanTask) => {
    setEditingTask(task);

    const taskColumn = Object.values(board.columns).find((column) => column.taskIds.includes(task.id));

    const normalizedStart = normalizeIncomingDateValue(task.startDate);
    const normalizedEnd = normalizeIncomingDateValue(task.endDate);
    const normalizedDue = normalizeIncomingDateValue(task.dueDate);
    const normalizedDifficulty = normalizeNumericSelectValue(
      task.difficulty ?? PRIORITY_TO_VALUE[task.priority],
      DEFAULT_DIFFICULTY
    );
    const normalizedProgress = normalizeNumericSelectValue(task.progress ?? 0, DEFAULT_PROGRESS);

    setEditTaskState({
      translations: createTranslationEntriesFromTask(task),
      columnId: taskColumn?.id || resolveDefaultColumnId(),
      priority: task.priority,
      dueDate: normalizedDue || calculateDueDate(normalizedStart, normalizedEnd),
      startDate: normalizedStart,
      endDate: normalizedEnd,
      assignee: task.assignee || task.assignedTo?.[0]?.name || "",
      difficulty: normalizedDifficulty,
      progress: normalizedProgress,
    });
    setEditModalError(null);
    setEditLanguagePickerOpen(false);
    setEditLanguageSelection("");
    setEditCustomLanguage("");
    setEditLanguagePickerError(null);

    setIsEditModalOpen(true);
  };

  const handleCloseEditModal = () => {
    setIsEditModalOpen(false);
    setEditingTask(null);
    setEditModalError(null);
    setEditLanguagePickerOpen(false);
    setEditLanguageSelection("");
    setEditCustomLanguage("");
    setEditLanguagePickerError(null);
  };

  const handleCreateTaskChange = (field: TaskFormEditableField, value: string) => {
    setCreateTaskState((prev: TaskFormState) => updateTaskFormState(prev, field, value));
  };

  const handleEditTaskChange = (field: TaskFormEditableField, value: string) => {
    setEditTaskState((prev: TaskFormState) => updateTaskFormState(prev, field, value));
  };

  const updateTranslations = (
    mode: "create" | "edit",
    updater: (current: TranslationFormEntry[]) => TranslationFormEntry[]
  ) => {
    if (mode === "create") {
      setCreateTaskState((prev: TaskFormState) => ({
        ...prev,
        translations: updater(prev.translations),
      }));
    } else {
      setEditTaskState((prev: TaskFormState) => ({
        ...prev,
        translations: updater(prev.translations),
      }));
    }
  };

  const handleTranslationFieldChange = (
    mode: "create" | "edit",
    entryId: string,
    field: "language" | "title" | "description",
    value: string
  ) => {
    updateTranslations(mode, (current) =>
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
  };

  const handleAddTranslation = (
    mode: "create" | "edit",
    explicitLanguage?: string
  ): { success: boolean; error?: string } => {
    const targetState = mode === "create" ? createTaskState : editTaskState;
    const used = new Set<string>(
      targetState.translations
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

    updateTranslations(mode, (current) => [...current, createTranslationEntry(languageToUse)]);
    return { success: true };
  };

  const handleRemoveTranslation = (mode: "create" | "edit", entryId: string) => {
    const targetState = mode === "create" ? createTaskState : editTaskState;
    if (targetState.translations.length <= 1) {
      return;
    }
    updateTranslations(mode, (current) => current.filter((entry) => entry.id !== entryId));
  };

  const getAvailableLanguages = useCallback(
    (mode: "create" | "edit") => {
      const targetState = mode === "create" ? createTaskState : editTaskState;
      const used = new Set(
        targetState.translations
          .map((translation) => normalizeLanguageCode(translation.language))
          .filter(Boolean)
      );
      return languageOptions.filter((option) => !used.has(option.value));
    },
    [createTaskState.translations, editTaskState.translations, languageOptions]
  );

  const availableCreateLanguages = useMemo(() => getAvailableLanguages("create"), [getAvailableLanguages]);
  const availableEditLanguages = useMemo(() => getAvailableLanguages("edit"), [getAvailableLanguages]);

  const buildActionPayload = (
    mode: "create" | "edit",
    state: TaskFormState,
    baseTask?: KanbanTask | null
  ): { payload: Record<string, unknown> } | { error: string } => {
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

    const translationFields: Record<string, string | null> = {};
    normalized.forEach((value, language) => {
      translationFields[`action_${language}`] = value.title || "";
      translationFields[`description_${language}`] = value.description || "";
    });

    const languages = Array.from(normalized.keys());

    const removalTokens: string[] = [];
    if (mode === "edit" && baseTask) {
      const originalLanguages = new Set<string>();
      baseTask.languageCodes?.forEach((code) => originalLanguages.add(normalizeLanguageCode(code)));
      Object.keys(baseTask.titleTranslations ?? {}).forEach((code) => originalLanguages.add(normalizeLanguageCode(code)));
      Object.keys(baseTask.descriptionTranslations ?? {}).forEach((code) => originalLanguages.add(normalizeLanguageCode(code)));

      originalLanguages.forEach((language) => {
        if (language && !normalized.has(language)) {
          removalTokens.push(`action_${language}`);
          removalTokens.push(`description_${language}`);
        }
      });
    }

    const column = board.columns[state.columnId] ?? board.columns[FALLBACK_COLUMN_ID];
    const columnTitle = column?.title ?? "Uncategorized";
    const assignedTo = state.assignee
      ? [{ name: state.assignee }]
      : baseTask?.assignedTo?.map((assignment) => ({ name: assignment.name })) ?? [];

    const startTimestamp = toTimestampMilliseconds(state.startDate);
    const endTimestamp = toTimestampMilliseconds(state.endDate);
    const dueTimestamp = toTimestampMilliseconds(state.dueDate);

    if (startTimestamp !== null && endTimestamp !== null && endTimestamp <= startTimestamp) {
      return { error: "End date must be after start date." };
    }

    if (endTimestamp !== null && dueTimestamp !== null && dueTimestamp < endTimestamp) {
      return { error: "Due date must be on or after end date." };
    }

    const fallbackDifficulty = baseTask?.difficulty ?? PRIORITY_TO_VALUE[state.priority];
    const parsedDifficulty = Number(state.difficulty);
    const resolvedDifficulty = Number.isNaN(parsedDifficulty) || parsedDifficulty <= 0 ? fallbackDifficulty : parsedDifficulty;

    const fallbackProgress = baseTask?.progress ?? 0;
    const parsedProgress = Number(state.progress);
    const resolvedProgress = Number.isNaN(parsedProgress) || parsedProgress < 0 ? fallbackProgress : parsedProgress;

    const payloadItem: Record<string, unknown> = {
      model_name: "action",
      ...translationFields,
      languages,
      needtoremove: removalTokens.join(","),
      kanban_column: columnTitle,
      kanban_column_id: column?.id ?? FALLBACK_COLUMN_ID,
      priority: PRIORITY_TO_VALUE[state.priority],
      difficulty: resolvedDifficulty,
      status: baseTask?.status ?? "In progress",
      dt_due: dueTimestamp,
      dt_start: startTimestamp,
      dt_end: endTimestamp,
      assigned_to: assignedTo,
      progress: resolvedProgress,
    };

    if (mode === "edit" && baseTask) {
      payloadItem.id = baseTask.id;
    }

    if (!state.assignee && assignedTo.length === 0) {
      delete payloadItem.assigned_to;
    }

    if (!removalTokens.length) {
      payloadItem.needtoremove = "";
    }

    return { payload: payloadItem };
  };

  const handleCreateTaskSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSavingCreate) {
      return;
    }

    setCreateModalError(null);
    const result = buildActionPayload("create", createTaskState);

    if ("error" in result) {
      setCreateModalError(result.error);
      return;
    }

    try {
      setIsSavingCreate(true);
      const response = await patchAction(result.payload);
      if (response?.status !== 200 && response?.status !== 201) {
        throw new Error("Failed to save task.");
      }
      await fetchActions();
      handleCloseCreateModal();
    } catch (error) {
      console.error("Failed to create kanban task", error);
      const message =
        (error as any)?.response?.data?.message ||
        (error as any)?.message ||
        "Unable to save task. Please try again.";
      setCreateModalError(message);
    } finally {
      setIsSavingCreate(false);
    }
  };

  const handleEditTaskSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editingTask || isSavingEdit) {
      return;
    }

    setEditModalError(null);
    const result = buildActionPayload("edit", editTaskState, editingTask);

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
      await fetchActions();
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
  };

  const gridStyle = useMemo<CSSProperties>(() => ({
    gridTemplateColumns: `repeat(${Math.max(1, columnsPerRow)}, minmax(0, 1fr))`,
  }), [columnsPerRow]);

  return (
    <div className="space-y-6">
      <PageBreadcrumb pageTitle="Kanban Board" />

      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Keep work flowing</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Drag tasks across columns to reshuffle priorities, track progress, and visualize throughput in real time.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-500 shadow-sm dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300">
            <span>Columns</span>
            <select
              value={columnsPerRow}
              onChange={(event) => setColumnsPerRow(Number(event.target.value))}
              className="rounded-md border border-gray-200 dark:bg-black px-2 py-1 text-xs font-semibold text-gray-700 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 dark:border-gray-700 dark:text-white"
            >
              {columnDensityOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <button
            onClick={handleOpenCreateModal}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 5v14m7-7H5" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            New Task
          </button>
          <button className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 8v8m-4-4h8" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
              <path d="M6.5 4h11a2.5 2.5 0 012.5 2.5v11a2.5 2.5 0 01-2.5 2.5h-11A2.5 2.5 0 014 17.5v-11A2.5 2.5 0 016.5 4z" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Manage Columns
          </button>
          <a href="/kanban-gantt" className="inline-flex items-center gap-2 rounded-lg border border-indigo-300 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-100 dark:border-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400 dark:hover:bg-indigo-500/20">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
              <path d="M9 22V12h6v10" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            View Gantt Chart
          </a>
        </div>
      </div>

      {fetchError && (
        <div className="flex items-center justify-between rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/30 dark:text-rose-200">
          <span>{fetchError}</span>
          <button
            type="button"
            onClick={() => fetchActions()}
            className="rounded-md border border-rose-300 px-3 py-1 text-xs font-semibold text-rose-700 transition hover:bg-rose-100 dark:border-rose-700 dark:text-rose-200 dark:hover:bg-rose-900/50"
          >
            Retry
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {(Object.keys(prioritySummary) as TaskPriority[]).map((priority) => (
          <div
            key={priority}
            className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900/40"
          >
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">{priority}</p>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-3xl font-semibold text-gray-900 dark:text-white">{prioritySummary[priority]}</span>
              <span className="text-xs font-medium text-gray-400">/ {totalTasks} tasks</span>
            </div>
            <span className={clsx("mt-4 inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold", priorityPalette[priority])}>
              Priority lane
            </span>
          </div>
        ))}
      </div>

      <DndProvider backend={HTML5Backend}>
        {isLoading ? (
          <div className="flex h-56 items-center justify-center rounded-3xl border border-dashed border-gray-200 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
            Loading kanban data…
          </div>
        ) : columns.length === 0 ? (
          <div className="flex h-56 flex-col items-center justify-center gap-3 rounded-3xl border border-dashed border-gray-200 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
            <span>No tasks found. Create a new card or refresh from the API.</span>
            <button
              type="button"
              onClick={() => fetchActions()}
              className="rounded-lg border border-gray-300 px-3 py-1 text-xs font-semibold text-gray-600 transition hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
            >
              Refresh
            </button>
          </div>
        ) : (
          <div className="grid gap-5 pb-6" style={gridStyle}>
            {columns.map((column) => {
              const tasks: KanbanTask[] = column.taskIds
                .map((taskId) => board.tasks[taskId])
                .filter((task): task is KanbanTask => Boolean(task));

              return (
                <KanbanColumn
                  key={column.id}
                  column={column}
                  tasks={tasks}
                  onDragEnd={handleDragEnd}
                  onTaskClick={handleOpenEditModal}
                  className="h-full"
                />
              );
            })}
          </div>
        )}
      </DndProvider>

      {isCreateModalOpen && (
        <div className="fixed inset-0 z-[200000] flex items-center justify-center bg-black/30 px-4 py-6 backdrop-blur-sm">
          <div className="w-full max-w-lg max-h-[calc(100vh-4rem)] overflow-y-auto rounded-3xl border border-gray-200 bg-white p-6 shadow-xl no-scrollbar dark:border-gray-800 dark:bg-gray-900">
            <div className="mb-4 flex items-start justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Create new task</h2>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Add the essentials and drop it in the right column.</p>
              </div>
              <button
                onClick={handleCloseCreateModal}
                className="rounded-full p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800"
                aria-label="Close"
              >
                <svg className="h-5 w-5" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M6 6l8 8M14 6l-8 8" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>

            <form className="space-y-5" onSubmit={handleCreateTaskSubmit}>
              {createModalError && (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/40 dark:text-rose-200">
                  {createModalError}
                </div>
              )}

              <datalist id="language-options-create">
                {languageOptions.map((option) => (
                  <option key={option.value} value={option.value} label={option.label} />
                ))}
              </datalist>

              <div className="space-y-4">
                {createTaskState.translations.map((translation, index) => {
                  const canRemove = createTaskState.translations.length > 1;
                  return (
                    <div
                      key={translation.id}
                      className="rounded-2xl border border-gray-200 bg-gray-50/80 p-4 shadow-sm dark:border-gray-800 dark:bg-gray-800/40"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-gray-900 dark:text-white">Language {index + 1}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {translation.language ? getLanguageLabel(translation.language) : "Set the language code"}
                          </p>
                        </div>
                        <div className="inline-flex items-center gap-2">
                          <span className="text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                            {translation.language || "—"}
                          </span>
                          <button
                            type="button"
                            onClick={() => handleRemoveTranslation("create", translation.id)}
                            disabled={!canRemove || isSavingCreate}
                            className="rounded-lg px-2 py-1 text-xs font-semibold text-rose-600 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:text-rose-300 dark:text-rose-300 dark:hover:bg-rose-900/40"
                          >
                            Remove
                          </button>
                        </div>
                      </div>

                      <div className="mt-4 space-y-3">
                        <div>
                          <label className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            Language code
                          </label>
                          <input
                            className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-900/30 dark:text-white"
                            value={translation.language}
                            onChange={(event) =>
                              handleTranslationFieldChange("create", translation.id, "language", event.target.value)
                            }
                            placeholder="e.g. en"
                            list="language-options-create"
                            disabled={isSavingCreate}
                          />
                        </div>

                        <div>
                          <label className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            Action
                          </label>
                          <input
                            className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-900/30 dark:text-white"
                            value={translation.title}
                            onChange={(event) =>
                              handleTranslationFieldChange("create", translation.id, "title", event.target.value)
                            }
                            placeholder="Localized task title"
                            required={index === 0}
                            disabled={isSavingCreate}
                          />
                        </div>

                        <div>
                          <label className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            Description
                          </label>
                          <textarea
                            className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-900/30 dark:text-white"
                            rows={3}
                            value={translation.description}
                            onChange={(event) =>
                              handleTranslationFieldChange("create", translation.id, "description", event.target.value)
                            }
                            placeholder="Localized context, acceptance criteria, or notes"
                            disabled={isSavingCreate}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => {
                    if (isSavingCreate) return;
                    setCreateLanguagePickerError(null);
                    setCreateLanguagePickerOpen((prev) => {
                      const next = !prev;
                      if (next) {
                        if (availableCreateLanguages.length > 0) {
                          setCreateLanguageSelection("");
                          setCreateCustomLanguage("");
                        } else {
                          setCreateLanguageSelection("__custom");
                          setCreateCustomLanguage("");
                        }
                      }
                      return next;
                    });
                  }}
                  className="inline-flex items-center gap-2 rounded-xl border border-dashed border-gray-300 px-3 py-2 text-sm font-semibold text-gray-600 transition hover:border-indigo-400 hover:text-indigo-500 disabled:cursor-not-allowed disabled:text-gray-400 dark:border-gray-700 dark:text-gray-300 dark:hover:border-indigo-500/40 dark:hover:text-indigo-300"
                  disabled={isSavingCreate}
                >
                  <svg className="h-4 w-4" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M10 4v12m6-6H4" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  {createLanguagePickerOpen ? "Hide language picker" : "Add language"}
                </button>

                {createLanguagePickerOpen && (
                  <div className="rounded-2xl border border-gray-200 bg-white/80 p-4 text-sm shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                      <div className="flex-1 space-y-1">
                        <label className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                          Select language
                        </label>
                        <select
                          className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-900/30 dark:text-white"
                          value={createLanguageSelection}
                          onChange={(event) => {
                            const value = event.target.value;
                            setCreateLanguageSelection(value);
                            if (value !== "__custom") {
                              setCreateCustomLanguage("");
                            }
                            setCreateLanguagePickerError(null);
                          }}
                          disabled={isSavingCreate}
                        >
                          <option value="">Select a language…</option>
                          {availableCreateLanguages.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                          <option value="__custom">Custom code…</option>
                        </select>
                      </div>

                      {createLanguageSelection === "__custom" && (
                        <div className="flex-1 space-y-1">
                          <label className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            Custom code
                          </label>
                          <input
                            className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-900/30 dark:text-white"
                            value={createCustomLanguage}
                            onChange={(event) => {
                              setCreateCustomLanguage(event.target.value);
                              setCreateLanguagePickerError(null);
                            }}
                            placeholder="e.g. fr"
                            disabled={isSavingCreate}
                          />
                        </div>
                      )}

                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => {
                            const selected =
                              createLanguageSelection === "__custom"
                                ? createCustomLanguage.trim()
                                : createLanguageSelection;
                            if (!selected) {
                              setCreateLanguagePickerError("Choose a language before adding.");
                              return;
                            }
                            const result = handleAddTranslation("create", selected);
                            if (!result.success) {
                              setCreateLanguagePickerError(result.error ?? "Unable to add language.");
                              return;
                            }
                            setCreateLanguagePickerOpen(false);
                            setCreateLanguageSelection("");
                            setCreateCustomLanguage("");
                          }}
                          className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-indigo-400"
                          disabled={isSavingCreate}
                        >
                          Add
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setCreateLanguagePickerOpen(false);
                            setCreateLanguageSelection("");
                            setCreateCustomLanguage("");
                            setCreateLanguagePickerError(null);
                          }}
                          className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                          disabled={isSavingCreate}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                    {createLanguagePickerError && (
                      <p className="mt-2 text-xs font-semibold text-rose-600 dark:text-rose-300">
                        {createLanguagePickerError}
                      </p>
                    )}
                  </div>
                )}
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Column</label>
                  <select
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={createTaskState.columnId}
                    onChange={(event) => handleCreateTaskChange("columnId", event.target.value)}
                    disabled={isSavingCreate}
                  >
                    {columnOptions.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.title}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Priority</label>
                  <select
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={createTaskState.priority}
                    onChange={(event) => handleCreateTaskChange("priority", event.target.value as TaskPriority)}
                    disabled={isSavingCreate}
                  >
                    {priorityOptions.map((priority) => (
                      <option key={priority} value={priority}>
                        {priority.charAt(0).toUpperCase() + priority.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Difficulty</label>
                  <select
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={createTaskState.difficulty}
                    onChange={(event) => handleCreateTaskChange("difficulty", event.target.value)}
                    disabled={isSavingCreate}
                  >
                    {createDifficultyOptions.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Progress (%)</label>
                  <select
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={createTaskState.progress}
                    onChange={(event) => handleCreateTaskChange("progress", event.target.value)}
                    disabled={isSavingCreate}
                  >
                    {createProgressOptions.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Start date &amp; time</label>
                  <input
                    type="datetime-local"
                    step={60}
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={createTaskState.startDate}
                    onChange={(event) => handleCreateTaskChange("startDate", event.target.value)}
                    disabled={isSavingCreate}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">End date &amp; time</label>
                  <input
                    type="datetime-local"
                    step={60}
                    min={createTaskState.startDate || undefined}
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={createTaskState.endDate}
                    onChange={(event) => handleCreateTaskChange("endDate", event.target.value)}
                    disabled={isSavingCreate}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Due date &amp; time</label>
                  <input
                    type="datetime-local"
                    step={60}
                    min={createTaskState.endDate || createTaskState.startDate || undefined}
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={createTaskState.dueDate}
                    onChange={(event) => handleCreateTaskChange("dueDate", event.target.value)}
                    disabled={isSavingCreate}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Assignee</label>
                  <input
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={createTaskState.assignee}
                    onChange={(event) => handleCreateTaskChange("assignee", event.target.value)}
                    placeholder="Who owns this?"
                    disabled={isSavingCreate}
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleCloseCreateModal}
                  disabled={isSavingCreate}
                  className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:text-gray-400 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSavingCreate}
                  className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-indigo-400"
                >
                  {isSavingCreate ? "Saving…" : "Add task"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Task Modal */}
      {isEditModalOpen && editingTask && (
        <div className="fixed inset-0 z-[200000] flex items-center justify-center bg-black/30 px-4 py-6 backdrop-blur-sm">
          <div className="w-full max-w-lg max-h-[calc(100vh-4rem)] overflow-y-auto rounded-3xl border border-gray-200 bg-white p-6 shadow-xl no-scrollbar dark:border-gray-800 dark:bg-gray-900">
            <div className="mb-4 flex items-start justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Edit task</h2>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Update task details and move between columns.</p>
              </div>
              <button
                onClick={handleCloseEditModal}
                className="rounded-full p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800"
                aria-label="Close"
              >
                <svg className="h-5 w-5" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M6 6l8 8M14 6l-8 8" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>

            <form className="space-y-5" onSubmit={handleEditTaskSubmit}>
              {editModalError && (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/40 dark:text-rose-200">
                  {editModalError}
                </div>
              )}

              <datalist id="language-options-edit">
                {languageOptions.map((option) => (
                  <option key={option.value} value={option.value} label={option.label} />
                ))}
              </datalist>

              <div className="space-y-4">
                {editTaskState.translations.map((translation, index) => {
                  const canRemove = editTaskState.translations.length > 1;
                  return (
                    <div
                      key={translation.id}
                      className="rounded-2xl border border-gray-200 bg-gray-50/80 p-4 shadow-sm dark:border-gray-800 dark:bg-gray-800/40"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-gray-900 dark:text-white">Language {index + 1}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {translation.language ? getLanguageLabel(translation.language) : "Set the language code"}
                          </p>
                        </div>
                        <div className="inline-flex items-center gap-2">
                          <span className="text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                            {translation.language || "—"}
                          </span>
                          <button
                            type="button"
                            onClick={() => handleRemoveTranslation("edit", translation.id)}
                            disabled={!canRemove || isSavingEdit}
                            className="rounded-lg px-2 py-1 text-xs font-semibold text-rose-600 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:text-rose-300 dark:text-rose-300 dark:hover:bg-rose-900/40"
                          >
                            Remove
                          </button>
                        </div>
                      </div>

                      <div className="mt-4 space-y-3">
                        <div>
                          <label className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            Language code
                          </label>
                          <input
                            className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-900/30 dark:text-white"
                            value={translation.language}
                            onChange={(event) =>
                              handleTranslationFieldChange("edit", translation.id, "language", event.target.value)
                            }
                            placeholder="e.g. en"
                            list="language-options-edit"
                            disabled={isSavingEdit}
                          />
                        </div>

                        <div>
                          <label className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            Title
                          </label>
                          <input
                            className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-900/30 dark:text-white"
                            value={translation.title}
                            onChange={(event) =>
                              handleTranslationFieldChange("edit", translation.id, "title", event.target.value)
                            }
                            placeholder="Localized task title"
                            required={index === 0}
                            disabled={isSavingEdit}
                          />
                        </div>

                        <div>
                          <label className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            Description
                          </label>
                          <textarea
                            className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-900/30 dark:text-white"
                            rows={3}
                            value={translation.description}
                            onChange={(event) =>
                              handleTranslationFieldChange("edit", translation.id, "description", event.target.value)
                            }
                            placeholder="Localized context, acceptance criteria, or notes"
                            disabled={isSavingEdit}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => {
                    if (isSavingEdit) return;
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
                  }}
                  className="inline-flex items-center gap-2 rounded-xl border border-dashed border-gray-300 px-3 py-2 text-sm font-semibold text-gray-600 transition hover:border-indigo-400 hover:text-indigo-500 disabled:cursor-not-allowed disabled:text-gray-400 dark:border-gray-700 dark:text-gray-300 dark:hover:border-indigo-500/40 dark:hover:text-indigo-300"
                  disabled={isSavingEdit}
                >
                  <svg className="h-4 w-4" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M10 4v12m6-6H4" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  {editLanguagePickerOpen ? "Hide language picker" : "Add language"}
                </button>

                {editLanguagePickerOpen && (
                  <div className="rounded-2xl border border-gray-200 bg-white/80 p-4 text-sm shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                      <div className="flex-1 space-y-1">
                        <label className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                          Select language
                        </label>
                        <select
                          className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-black dark:text-white"
                          value={editLanguageSelection}
                          onChange={(event) => {
                            const value = event.target.value;
                            setEditLanguageSelection(value);
                            if (value !== "__custom") {
                              setEditCustomLanguage("");
                            }
                            setEditLanguagePickerError(null);
                          }}
                          disabled={isSavingEdit}
                        >
                          <option value="">Select a language…</option>
                          {availableEditLanguages.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                          <option value="__custom">Custom code…</option>
                        </select>
                      </div>

                      {editLanguageSelection === "__custom" && (
                        <div className="flex-1 space-y-1">
                          <label className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            Custom code
                          </label>
                          <input
                            className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-900/30 dark:text-white"
                            value={editCustomLanguage}
                            onChange={(event) => {
                              setEditCustomLanguage(event.target.value);
                              setEditLanguagePickerError(null);
                            }}
                            placeholder="e.g. fr"
                            disabled={isSavingEdit}
                          />
                        </div>
                      )}

                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => {
                            const selected =
                              editLanguageSelection === "__custom"
                                ? editCustomLanguage.trim()
                                : editLanguageSelection;
                            if (!selected) {
                              setEditLanguagePickerError("Choose a language before adding.");
                              return;
                            }
                            const result = handleAddTranslation("edit", selected);
                            if (!result.success) {
                              setEditLanguagePickerError(result.error ?? "Unable to add language.");
                              return;
                            }
                            setEditLanguagePickerOpen(false);
                            setEditLanguageSelection("");
                            setEditCustomLanguage("");
                          }}
                          className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-indigo-400"
                          disabled={isSavingEdit}
                        >
                          Add
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setEditLanguagePickerOpen(false);
                            setEditLanguageSelection("");
                            setEditCustomLanguage("");
                            setEditLanguagePickerError(null);
                          }}
                          className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                          disabled={isSavingEdit}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                    {editLanguagePickerError && (
                      <p className="mt-2 text-xs font-semibold text-rose-600 dark:text-rose-300">
                        {editLanguagePickerError}
                      </p>
                    )}
                  </div>
                )}
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Column</label>
                  <select
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={editTaskState.columnId}
                    onChange={(event) => handleEditTaskChange("columnId", event.target.value)}
                    disabled={isSavingEdit}
                  >
                    {columnOptions.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.title}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Priority</label>
                  <select
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={editTaskState.priority}
                    onChange={(event) => handleEditTaskChange("priority", event.target.value as TaskPriority)}
                    disabled={isSavingEdit}
                  >
                    {priorityOptions.map((priority) => (
                      <option key={priority} value={priority}>
                        {priority.charAt(0).toUpperCase() + priority.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Difficulty</label>
                  <select
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={editTaskState.difficulty}
                    onChange={(event) => handleEditTaskChange("difficulty", event.target.value)}
                    disabled={isSavingEdit}
                  >
                    {editDifficultyOptions.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Progress (%)</label>
                  <select
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={editTaskState.progress}
                    onChange={(event) => handleEditTaskChange("progress", event.target.value)}
                    disabled={isSavingEdit}
                  >
                    {editProgressOptions.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Start date &amp; time</label>
                  <input
                    type="datetime-local"
                    step={60}
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={editTaskState.startDate}
                    onChange={(event) => handleEditTaskChange("startDate", event.target.value)}
                    disabled={isSavingEdit}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">End date &amp; time</label>
                  <input
                    type="datetime-local"
                    step={60}
                    min={editTaskState.startDate || undefined}
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={editTaskState.endDate}
                    onChange={(event) => handleEditTaskChange("endDate", event.target.value)}
                    disabled={isSavingEdit}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Due date &amp; time</label>
                  <input
                    type="datetime-local"
                    step={60}
                    min={editTaskState.endDate || editTaskState.startDate || undefined}
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={editTaskState.dueDate}
                    onChange={(event) => handleEditTaskChange("dueDate", event.target.value)}
                    disabled={isSavingEdit}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Assignee</label>
                  <input
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={editTaskState.assignee}
                    onChange={(event) => handleEditTaskChange("assignee", event.target.value)}
                    placeholder="Who owns this?"
                    disabled={isSavingEdit}
                  />
                </div>
              </div>

              {/* Current Task Info */}
              <div className="rounded-xl bg-gray-50 p-4 dark:bg-gray-800/50">
                <h4 className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">Current Task Status</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Progress:</span>
                    <span className="ml-1 font-medium text-gray-900 dark:text-white">{editingTask.progress || 0}%</span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Tags:</span>
                    <span className="ml-1 font-medium text-gray-900 dark:text-white">
                      {editingTask.tags?.join(", ") || "None"}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleCloseEditModal}
                  disabled={isSavingEdit}
                  className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:text-gray-400 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSavingEdit}
                  className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-indigo-400"
                >
                  {isSavingEdit ? "Saving…" : "Update task"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default KanbanBoardPage;
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import KanbanTaskModal from "../../components/kanban/KanbanTaskModal";
import type { BoardData } from "../../type/kanban";
import { KanbanTask, TaskPriority } from "../../type/kanban";
import clsx from "clsx";
import { Actions, patchAction } from "../../api/userProfile";
import { createBoardDataFromApi, createEmptyBoardData, extractKanbanItems } from "./kanbanDataMapper";
import type { TaskFormEditableField, TaskFormState, TranslationFormEntry } from "../../components/kanban/taskFormTypes";

// Sample data used as a fallback when the API is unavailable
// const FALLBACK_GANTT_TASKS: KanbanTask[] = [
//   {
//     id: "task-1",
//     title: "Persona maps & discovery notes",
//     description: "Synthesize user interviews into actionable personas for the growth epic.",
//     priority: "high",
//     assignee: "Maya Patel",
//     dueDate: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString(),
//     tags: ["Discovery", "Research"],
//     progress: 35,
//     children: [
//       { id: "task-1-1", name: "Conduct user interviews" },
//       { id: "task-1-2", name: "Create persona templates" }
//     ]
//   },
//   {
//     id: "task-1-1",
//     title: "Conduct user interviews",
//     description: "Schedule and conduct interviews with 5-8 target users",
//     priority: "medium",
//     assignee: "Maya Patel",
//     dueDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
//     tags: ["Research"],
//     progress: 80,
//   },
//   {
//     id: "task-1-2",
//     title: "Create persona templates",
//     description: "Design reusable persona templates based on research findings",
//     priority: "medium",
//     assignee: "Maya Patel",
//     dueDate: new Date(Date.now() + 10 * 24 * 60 * 60 * 1000).toISOString(),
//     tags: ["Design"],
//     progress: 20,
//   },
//   {
//     id: "task-2",
//     title: "Backend contract for v2 API",
//     description: "Define request/response schema and agree on pagination strategy with backend team.",
//     priority: "critical",
//     assignee: "Colin Rivera",
//     dueDate: new Date(Date.now() + 21 * 24 * 60 * 60 * 1000).toISOString(),
//     tags: ["API", "Backend"],
//     progress: 10,
//   },
//   {
//     id: "task-3",
//     title: "Visual design refresh",
//     description: "Update typography scale and audit existing color usage to match new design tokens.",
//     priority: "medium",
//     assignee: "Akari Watanabe",
//     dueDate: new Date(Date.now() + 28 * 24 * 60 * 60 * 1000).toISOString(),
//     tags: ["Design", "UI"],
//     progress: 55,
//   },
//   {
//     id: "task-4",
//     title: "QA regression suite",
//     description: "Automate the top ten revenue-critical flows in Playwright.",
//     priority: "high",
//     assignee: "Enzo García",
//     dueDate: new Date(Date.now() + 35 * 24 * 60 * 60 * 1000).toISOString(),
//     tags: ["QA", "Automation"],
//     progress: 20,
//   }
// ];

const priorityColors: Record<TaskPriority, string> = {
  low: "bg-emerald-500",
  medium: "bg-amber-500",
  high: "bg-orange-500",
  critical: "bg-rose-500",
};

const priorityBgColors: Record<TaskPriority, string> = {
  low: "bg-emerald-50 border-emerald-200 dark:bg-emerald-500/10 dark:border-emerald-500/20",
  medium: "bg-amber-50 border-amber-200 dark:bg-amber-500/10 dark:border-amber-500/20",
  high: "bg-orange-50 border-orange-200 dark:bg-orange-500/10 dark:border-orange-500/20",
  critical: "bg-rose-50 border-rose-200 dark:bg-rose-500/10 dark:border-rose-500/20",
};

const PRIORITY_TO_VALUE: Record<TaskPriority, number> = {
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
};

const priorityOptions: TaskPriority[] = ["low", "medium", "high", "critical"];

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

const DIFFICULTY_OPTIONS: readonly number[] = [1, 2, 3, 5, 8, 13, 21, 34, 55, 101];
const PROGRESS_OPTIONS: readonly number[] = [0, 5, 30, 50, 70, 90, 100];

const DEFAULT_DIFFICULTY = DIFFICULTY_OPTIONS[2] ?? DIFFICULTY_OPTIONS[0];
const DEFAULT_PROGRESS = PROGRESS_OPTIONS[0];

const DEFAULT_DIFFICULTY_STRING = String(DEFAULT_DIFFICULTY);
const DEFAULT_PROGRESS_STRING = String(DEFAULT_PROGRESS);

const normalizeLanguageCode = (code: string) => code.trim().toLowerCase();

const createTranslationEntry = (language: string, title = "", description = ""): TranslationFormEntry => ({
  id: createLocalId(),
  language,
  title,
  description,
});

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

const createFallbackBoardFromTasks = (tasks: KanbanTask[]): BoardData => ({
  tasks: tasks.reduce<Record<string, KanbanTask>>((accumulator, task) => {
    accumulator[task.id] = task;
    return accumulator;
  }, {}),
  columns: {
    [FALLBACK_COLUMN_ID]: {
      id: FALLBACK_COLUMN_ID,
      title: "Uncategorized",
      taskIds: tasks.map((task) => task.id),
    },
  },
  columnOrder: [FALLBACK_COLUMN_ID],
});

void createFallbackBoardFromTasks;

interface GanttDateRange {
  start: Date;
  end: Date;
}

interface GanttBarProps {
  task: KanbanTask;
  dateRange: GanttDateRange;
  isSubtask?: boolean;
  onEdit?: (task: KanbanTask) => void;
}

const GanttBar: React.FC<GanttBarProps> = ({ task, dateRange, isSubtask = false, onEdit }) => {
  const taskStart = new Date();
  const taskEnd = task.dueDate ? new Date(task.dueDate) : new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
  
  const totalDays = Math.ceil((dateRange.end.getTime() - dateRange.start.getTime()) / (1000 * 60 * 60 * 24));
  const startOffset = Math.ceil((taskStart.getTime() - dateRange.start.getTime()) / (1000 * 60 * 60 * 24));
  const duration = Math.ceil((taskEnd.getTime() - taskStart.getTime()) / (1000 * 60 * 60 * 24));
  
  const leftPercentage = (startOffset / totalDays) * 100;
  const widthPercentage = (duration / totalDays) * 100;

  const isOverdue = taskEnd < new Date() && (task.progress || 0) < 100;
  const isCritical = task.priority === 'critical';
  const isCompleted = (task.progress || 0) >= 100;

  return (
    <div 
      className="relative h-10 rounded-lg shadow-sm transition-all hover:shadow-md group"
      style={{
        left: `${Math.max(0, leftPercentage)}%`,
        width: `${Math.max(8, Math.min(widthPercentage, 100 - leftPercentage))}%`,
      }}
    >
      <div className={clsx(
        "h-full rounded-lg border-2 relative overflow-hidden transition-all",
        {
          [priorityBgColors[task.priority]]: !isOverdue && !isCompleted,
          "bg-rose-100 border-rose-300 dark:bg-rose-500/20 dark:border-rose-500/40": isOverdue,
          "bg-emerald-100 border-emerald-300 dark:bg-emerald-500/20 dark:border-emerald-500/40": isCompleted,
          "h-8 ml-4": isSubtask,
          "ring-2 ring-orange-400 ring-opacity-50": isCritical,
        }
      )}>
        {/* Progress bar */}
        <div 
          className={clsx(
            "h-full rounded-md transition-all",
            {
              [priorityColors[task.priority]]: !isOverdue && !isCompleted,
              "bg-rose-500": isOverdue,
              "bg-emerald-500": isCompleted,
            }
          )}
          style={{ width: `${task.progress || 0}%` }}
        />
        
        {/* Task title overlay */}
        <div className="absolute inset-0 flex items-center justify-between px-3">
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              onEdit?.(task);
            }}
            className={clsx(
              "text-left text-sm font-medium truncate flex-1 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/60",
              task.progress && task.progress > 50 ? "text-white" : "text-gray-700 dark:text-gray-300",
              isSubtask && "text-xs"
            )}
            title={task.title}
          >
            {task.title}
          </button>
          
          {/* Status indicators */}
          <div className="flex items-center gap-1 ml-2">
            {isCompleted && (
              <svg className="h-3 w-3 text-white" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            )}
            {isOverdue && (
              <svg className="h-3 w-3 text-white" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            )}
          </div>
        </div>

        {/* Hover tooltip */}
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 whitespace-nowrap">
          <div className="font-medium">{task.title}</div>
          <div className="text-gray-300">Progress: {task.progress || 0}%</div>
          <div className="text-gray-300">Due: {taskEnd.toLocaleDateString()}</div>
          {task.assignee && <div className="text-gray-300">Assignee: {task.assignee}</div>}
        </div>
      </div>
    </div>
  );
};

interface TimelineHeaderProps {
  dateRange: GanttDateRange;
}

const TimelineHeader: React.FC<TimelineHeaderProps> = ({ dateRange }) => {
  const days = useMemo(() => {
    const result: Date[] = [];
    const current = new Date(dateRange.start);
    
    while (current <= dateRange.end) {
      result.push(new Date(current));
      current.setDate(current.getDate() + 1);
    }
    
    return result;
  }, [dateRange]);

  return (
    <div className="flex border-b border-gray-200 dark:border-gray-700">
      {days.map((day, index) => {
        const isToday = day.toDateString() === new Date().toDateString();
        const isWeekend = day.getDay() === 0 || day.getDay() === 6;
        
        return (
          <div
            key={index}
            className={clsx(
              "flex-1 min-w-0 px-2 py-4 text-center border-r border-gray-100 dark:border-gray-800",
              {
                "bg-indigo-50 dark:bg-indigo-500/10": isToday,
                "bg-gray-50 dark:bg-gray-800/50": isWeekend,
              }
            )}
          >
            <div className="text-xs font-medium text-gray-500 dark:text-gray-400">
              {day.toLocaleDateString('en', { weekday: 'short' })}
            </div>
            <div className={clsx(
              "text-sm font-semibold",
              isToday ? "text-indigo-600 dark:text-indigo-400" : "text-gray-900 dark:text-white"
            )}>
              {day.getDate()}
            </div>
          </div>
        );
      })}
    </div>
  );
};

const KanbanGanttPage: React.FC = () => {
  const [board, setBoard] = useState<BoardData>(() => createEmptyBoardData());
  const [tasks, setTasks] = useState<KanbanTask[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [usingFallback, setUsingFallback] = useState<boolean>(false);
  const [selectedTimeRange, setSelectedTimeRange] = useState<'week' | 'month' | 'quarter'>('month');
  const [selectedTask, setSelectedTask] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'gantt' | 'timeline'>('gantt');
  const [showCompletedTasks, setShowCompletedTasks] = useState<boolean>(true);
  const [isEditModalOpen, setIsEditModalOpen] = useState<boolean>(false);
  const [editingTask, setEditingTask] = useState<KanbanTask | null>(null);
  const [editTaskState, setEditTaskState] = useState<TaskFormState>(() => createInitialTaskFormState(FALLBACK_COLUMN_ID));
  const [isSavingEdit, setIsSavingEdit] = useState<boolean>(false);
  const [editModalError, setEditModalError] = useState<string | null>(null);
  const [editLanguagePickerOpen, setEditLanguagePickerOpen] = useState<boolean>(false);
  const [editLanguageSelection, setEditLanguageSelection] = useState<string>("");
  const [editCustomLanguage, setEditCustomLanguage] = useState<string>("");
  const [editLanguagePickerError, setEditLanguagePickerError] = useState<string | null>(null);

  const resolveDefaultColumnId = useCallback(
    () => board.columnOrder[0] ?? FALLBACK_COLUMN_ID,
    [board.columnOrder]
  );

  const fetchGanttTasks = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const response = await Actions();
      if (!response || response.status !== 200) {
        throw new Error("Request failed");
      }

      const items = extractKanbanItems(response);
      if (items.length === 0) {
        setTasks([]);
        setBoard(createEmptyBoardData());
        setUsingFallback(false);
        return;
      }
      
      const boardData = createBoardDataFromApi(items);
      const mappedTasks = Object.values(boardData.tasks);
      const sortedTasks = [...mappedTasks].sort((a, b) => {
        const aDue = a.dueDate ? new Date(a.dueDate).getTime() : Number.POSITIVE_INFINITY;
        const bDue = b.dueDate ? new Date(b.dueDate).getTime() : Number.POSITIVE_INFINITY;
        if (aDue !== bDue) {
          return aDue - bDue;
        }
        return a.title.localeCompare(b.title);
      });

      setBoard(boardData);
      setTasks(sortedTasks);
      setUsingFallback(false);
    } catch (error) {
      console.error("Failed to fetch gantt tasks", error);
      setFetchError("Unable to load tasks from the API. Showing sample data.");
      //setTasks(FALLBACK_GANTT_TASKS);
      //setBoard(createFallbackBoardFromTasks(FALLBACK_GANTT_TASKS));
      setUsingFallback(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGanttTasks();
  }, [fetchGanttTasks]);

  useEffect(() => {
    if (!selectedTask) {
      return;
    }
    const exists = tasks.some((task) => task.id === selectedTask);
    if (!exists) {
      setSelectedTask(null);
    }
  }, [tasks, selectedTask]);

    const columnOptions = useMemo(() =>
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

    const updateEditTranslations = (
      updater: (current: TranslationFormEntry[]) => TranslationFormEntry[]
    ) => {
      setEditTaskState((prev) => ({
        ...prev,
        translations: updater(prev.translations),
      }));
    };

    const handleEditTranslationFieldChange = (
      entryId: string,
      field: "language" | "title" | "description",
      value: string
    ) => {
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
    };

    const handleAddEditTranslation = (
      explicitLanguage?: string
    ): { success: boolean; error?: string } => {
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
    };

    const handleRemoveEditTranslation = (entryId: string) => {
      if (editTaskState.translations.length <= 1) {
        return;
      }
      updateEditTranslations((current) => current.filter((entry) => entry.id !== entryId));
    };

    const availableEditLanguages = useMemo(() => {
      const used = new Set(
        editTaskState.translations
          .map((translation) => normalizeLanguageCode(translation.language))
          .filter(Boolean)
      );
      return languageOptions.filter((option) => !used.has(option.value));
    }, [editTaskState.translations, languageOptions]);

    const handleEditLanguagePickerToggle = () => {
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
    };

    const handleEditLanguageSelectionChange = (value: string) => {
      setEditLanguageSelection(value);
      if (value !== "__custom") {
        setEditCustomLanguage("");
      }
      setEditLanguagePickerError(null);
    };

    const handleEditLanguageCustomChange = (value: string) => {
      setEditCustomLanguage(value);
      setEditLanguagePickerError(null);
    };

    const handleEditLanguagePickerSubmit = () => {
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
    };

    const handleEditLanguagePickerCancel = () => {
      setEditLanguagePickerOpen(false);
      setEditLanguageSelection("");
      setEditCustomLanguage("");
      setEditLanguagePickerError(null);
    };

    const editLanguagePickerState = {
      isOpen: editLanguagePickerOpen,
      selection: editLanguageSelection,
      customValue: editCustomLanguage,
      error: editLanguagePickerError,
    };

    const handleEditTaskChange = (field: TaskFormEditableField, value: string) => {
      setEditTaskState((prev) => updateTaskFormState(prev, field, value));
    };

    const buildEditActionPayload = (
      state: TaskFormState,
      baseTask: KanbanTask | null
    ): { payload: Record<string, unknown> } | { error: string } => {
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

      const translationFields: Record<string, string | null> = {};
      normalized.forEach((value, language) => {
        translationFields[`action_${language}`] = value.title || "";
        translationFields[`description_${language}`] = value.description || "";
      });

      const languages = Array.from(normalized.keys());

      const removalTokens: string[] = [];
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

      const column = board.columns[state.columnId] ?? board.columns[FALLBACK_COLUMN_ID];
      const columnTitle = column?.title ?? "Uncategorized";
      const assignedTo = state.assignee
        ? [{ name: state.assignee }]
        : baseTask.assignedTo?.map((assignment) => ({ name: assignment.name })) ?? [];

      const startTimestamp = toTimestampMilliseconds(state.startDate);
      const endTimestamp = toTimestampMilliseconds(state.endDate);
      const dueTimestamp = toTimestampMilliseconds(state.dueDate);

      if (startTimestamp !== null && endTimestamp !== null && endTimestamp <= startTimestamp) {
        return { error: "End date must be after start date." };
      }

      if (endTimestamp !== null && dueTimestamp !== null && dueTimestamp < endTimestamp) {
        return { error: "Due date must be on or after end date." };
      }

      const fallbackDifficulty = baseTask.difficulty ?? PRIORITY_TO_VALUE[state.priority];
      const parsedDifficulty = Number(state.difficulty);
      const resolvedDifficulty =
        Number.isNaN(parsedDifficulty) || parsedDifficulty <= 0 ? fallbackDifficulty : parsedDifficulty;

      const fallbackProgress = baseTask.progress ?? 0;
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
        status: baseTask.status ?? "In progress",
        dt_due: dueTimestamp,
        dt_start: startTimestamp,
        dt_end: endTimestamp,
        assigned_to: assignedTo,
        progress: resolvedProgress,
        id: baseTask.id,
      };

      if (!state.assignee && assignedTo.length === 0) {
        delete payloadItem.assigned_to;
      }

      if (!removalTokens.length) {
        payloadItem.needtoremove = "";
      }

      return { payload: payloadItem };
    };

    const handleOpenEditModal = useCallback(
      (task: KanbanTask) => {
        setEditingTask(task);
        setSelectedTask(task.id);
        const taskColumn = Object.values(board.columns).find((column) => column?.taskIds.includes(task.id));

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
          columnId: taskColumn?.id ?? resolveDefaultColumnId(),
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
      },
      [board.columns, resolveDefaultColumnId]
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
      [editingTask, editTaskState, fetchGanttTasks, handleCloseEditModal, isSavingEdit]
    );

  const dateRange = useMemo((): GanttDateRange => {
    const start = new Date();
    const end = new Date();
    
    switch (selectedTimeRange) {
      case 'week':
        end.setDate(start.getDate() + 7);
        break;
      case 'month':
        end.setDate(start.getDate() + 30);
        break;
      case 'quarter':
        end.setDate(start.getDate() + 90);
        break;
    }
    
    return { start, end };
  }, [selectedTimeRange]);

  const organizedTasks = useMemo(() => {
    const result: Array<{ task: KanbanTask; isSubtask: boolean }> = [];
    const taskMap = new Map(tasks.map((task) => [task.id, task]));
    
    // Filter tasks based on completion status
    const filteredTasks = showCompletedTasks
      ? tasks
      : tasks.filter((task) => (task.progress || 0) < 100);
    
    // Find parent tasks
    const parentTasks = filteredTasks.filter((task) =>
      task.children && task.children.length > 0 && 
      !filteredTasks.some((otherTask) =>
        otherTask.children?.some((child) => child.id === task.id)
      )
    );

    const standaloneTasks = filteredTasks.filter((task) =>
      (!task.children || task.children.length === 0) &&
      !filteredTasks.some((otherTask) =>
        otherTask.children?.some((child) => child.id === task.id)
      )
    );
    
    // Add standalone tasks
    standaloneTasks.forEach((task) => {
      result.push({ task, isSubtask: false });
    });
    
    // Add parent tasks and their children
    parentTasks.forEach((parentTask) => {
      result.push({ task: parentTask, isSubtask: false });
      
      parentTask.children?.forEach((child) => {
        const childTask = taskMap.get(child.id.toString());
        if (childTask && (showCompletedTasks || (childTask.progress || 0) < 100)) {
          result.push({ task: childTask, isSubtask: true });
        }
      });
    });
    
    return result;
  }, [showCompletedTasks, tasks]);

  const hasOrganizedTasks = organizedTasks.length > 0;

  const handleTaskClick = useCallback((taskId: string) => {
    setSelectedTask(selectedTask === taskId ? null : taskId);
  }, [selectedTask]);

  const taskStats = useMemo(() => {
    const total = tasks.length;
    const completed = tasks.filter((task) => (task.progress || 0) >= 100).length;
    const inProgress = tasks.filter((task) => (task.progress || 0) > 0 && (task.progress || 0) < 100).length;
    const notStarted = tasks.filter((task) => (task.progress || 0) === 0).length;

    return { total, completed, inProgress, notStarted };
  }, [tasks]);

  return (
    <div className="space-y-6">
      <PageBreadcrumb pageTitle="Kanban Gantt Chart" />

      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Project Timeline</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Visualize task dependencies and progress in a timeline view for better project planning.
          </p>
        </div>
        
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex rounded-lg border border-gray-200 bg-white p-1 dark:border-gray-700 dark:bg-gray-900">
            {(['week', 'month', 'quarter'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setSelectedTimeRange(range)}
                className={clsx(
                  "px-3 py-1.5 text-sm font-medium rounded-md transition-all",
                  selectedTimeRange === range
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                )}
              >
                {range.charAt(0).toUpperCase() + range.slice(1)}
              </button>
            ))}
          </div>
          
          <div className="flex rounded-lg border border-gray-200 bg-white p-1 dark:border-gray-700 dark:bg-gray-900">
            {(['gantt', 'timeline'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={clsx(
                  "px-3 py-1.5 text-sm font-medium rounded-md transition-all",
                  viewMode === mode
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                )}
              >
                {mode.charAt(0).toUpperCase() + mode.slice(1)}
              </button>
            ))}
          </div>

          <label className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-500 shadow-sm dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300">
            <input
              type="checkbox"
              checked={showCompletedTasks}
              onChange={(e) => setShowCompletedTasks(e.target.checked)}
              className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <span>Show Completed</span>
          </label>
          
          <a 
            href="/kanban-board"
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M9 11H3m6 0V9m0 2v2m0-2h6m-6 0a3 3 0 003 3v-3m-3 0a3 3 0 00-3 3v-3" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Kanban View
          </a>
          
          <button className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Export
          </button>
          <button
            type="button"
            onClick={fetchGanttTasks}
            disabled={isLoading}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition disabled:cursor-not-allowed disabled:opacity-60 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M4 4v5h5" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
              <path d="M20 20v-5h-5" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
              <path d="M5.64 18.36A9 9 0 1018.36 5.64" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {isLoading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      {fetchError && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/40 dark:text-rose-100">
          {fetchError}
          {usingFallback && <span className="ml-2 font-semibold">Loaded fallback data.</span>}
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-800">
              <svg className="h-5 w-5 text-gray-600 dark:text-gray-400" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M9 11H3m6 0V9m0 2v2m0-2h6m-6 0a3 3 0 003 3v-3m-3 0a3 3 0 00-3 3v-3" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Total Tasks</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{taskStats.total}</p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100 dark:bg-emerald-500/10">
              <svg className="h-5 w-5 text-emerald-600 dark:text-emerald-400" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
                <path d="M21 12c0 4.97-4.03 9-9 9s-9-4.03-9-9 4.03-9 9-9 9 4.03 9 9z" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Completed</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{taskStats.completed}</p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-100 dark:bg-amber-500/10">
              <svg className="h-5 w-5 text-amber-600 dark:text-amber-400" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2l2 7h7l-5.5 4.5L17 21l-5-4-5 4 1.5-7.5L3 9h7l2-7z" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">In Progress</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{taskStats.inProgress}</p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-800">
              <svg className="h-5 w-5 text-gray-600 dark:text-gray-400" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 8v4l3 3" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
                <path d="M21 12c0 4.97-4.03 9-9 9s-9-4.03-9-9 4.03-9 9-9 9 4.03 9 9z" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Not Started</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{taskStats.notStarted}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Legend</h3>
        <div className="flex flex-wrap items-center gap-4 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-4 h-2 rounded bg-emerald-500"></div>
            <span className="text-gray-600 dark:text-gray-300">Low Priority</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-2 rounded bg-amber-500"></div>
            <span className="text-gray-600 dark:text-gray-300">Medium Priority</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-2 rounded bg-orange-500"></div>
            <span className="text-gray-600 dark:text-gray-300">High Priority</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-2 rounded bg-rose-500 ring-2 ring-orange-400 ring-opacity-50"></div>
            <span className="text-gray-600 dark:text-gray-300">Critical Priority</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-2 rounded bg-emerald-100 border-2 border-emerald-300 dark:bg-emerald-500/20 dark:border-emerald-500/40"></div>
            <span className="text-gray-600 dark:text-gray-300">Completed</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-2 rounded bg-rose-100 border-2 border-rose-300 dark:bg-rose-500/20 dark:border-rose-500/40"></div>
            <span className="text-gray-600 dark:text-gray-300">Overdue</span>
          </div>
        </div>
      </div>

      {/* Gantt Chart */}
      <div className="rounded-3xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
        <div className="border-b border-gray-200 px-6 py-4 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Project Timeline</h2>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Track progress and dependencies across all tasks
              </p>
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Showing {organizedTasks.length} tasks • {selectedTimeRange} view
            </div>
          </div>
        </div>

        <div className="flex">
          {/* Task List */}
          {/* <div className="w-96 flex-shrink-0 border-r border-gray-200 dark:border-gray-700">
            <div className="border-b border-gray-200 px-4 py-3 dark:border-gray-700">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Tasks</h3>
            </div>
            <div className="divide-y divide-gray-100 dark:divide-gray-800">
              {isLoading ? (
                <div className="px-4 py-6 text-sm text-gray-500 dark:text-gray-400">Loading tasks…</div>
              ) : !hasOrganizedTasks ? (
                <div className="px-4 py-6 text-sm text-gray-500 dark:text-gray-400">
                  {usingFallback ? "Sample tasks are unavailable." : "No tasks available yet."}
                </div>
              ) : (
                organizedTasks.map(({ task, isSubtask }) => (
                  <div
                    key={task.id}
                    onClick={() => handleTaskClick(task.id)}
                    className={clsx(
                      "cursor-pointer px-4 py-6 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50",
                      {
                        "bg-indigo-50 dark:bg-indigo-500/10": selectedTask === task.id,
                        "pl-8 py-4": isSubtask,
                      }
                    )}
                  >
                    <div className="flex items-start gap-3">
                      {isSubtask && (
                        <div className="mt-1 flex-shrink-0">
                          <div className="h-2 w-2 rounded-full bg-gray-300 dark:bg-gray-600" />
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-3">
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              if (!usingFallback) {
                                handleOpenEditModal(task);
                              }
                            }}
                            disabled={usingFallback}
                            className={clsx(
                              "font-semibold truncate leading-tight text-left transition hover:text-indigo-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/60 disabled:cursor-not-allowed",
                              isSubtask
                                ? "text-sm text-gray-600 dark:text-gray-400"
                                : "text-base text-gray-900 dark:text-white"
                            )}
                          >
                            {task.title}
                          </button>
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              handleOpenEditModal(task);
                            }}
                            disabled={usingFallback}
                            className="rounded-lg border border-gray-300 px-2 py-1 text-xs font-semibold text-gray-600 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                          >
                            Edit
                          </button>
                        </div>
                        <div className="mt-2 flex items-center gap-3">
                          <span className={clsx(
                            "inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold",
                            priorityBgColors[task.priority]
                          )}>
                            {task.priority.toUpperCase()}
                          </span>
                          <div className="flex items-center gap-1">
                            <div className="w-16 bg-gray-200 rounded-full h-1.5 dark:bg-gray-700">
                              <div
                                className={clsx("h-1.5 rounded-full transition-all", priorityColors[task.priority])}
                                style={{ width: `${task.progress || 0}%` }}
                              />
                            </div>
                            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                              {task.progress || 0}%
                            </span>
                          </div>
                        </div>
                        {task.assignee && (
                          <p className="mt-2 text-sm font-medium text-gray-600 dark:text-gray-300">
                            👤 {task.assignee}
                          </p>
                        )}
                        {task.dueDate && (
                          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                            📅 Due: {new Date(task.dueDate).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div> */}

          {/* Timeline */}
          <div className="flex-1 overflow-x-auto">
            <TimelineHeader dateRange={dateRange} />
            
            <div className="divide-y divide-gray-100 dark:divide-gray-800">
              {isLoading ? (
                <div className="flex h-40 items-center justify-center px-4 text-sm text-gray-500 dark:text-gray-400">
                  Loading timeline…
                </div>
              ) : !hasOrganizedTasks ? (
                <div className="flex h-40 items-center justify-center px-4 text-sm text-gray-500 dark:text-gray-400">
                  {usingFallback ? "No timeline data in sample set." : "Add tasks to view the timeline."}
                </div>
              ) : (
                organizedTasks.map(({ task, isSubtask }) => (
                  <div
                    key={task.id}
                    onClick={() => handleTaskClick(task.id)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        handleTaskClick(task.id);
                        handleOpenEditModal(task);
                      }
                    }}
                    role="button"
                    tabIndex={0}
                    className={clsx(
                      "relative h-20 flex items-center px-4 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/60",
                      {
                        "bg-indigo-50 dark:bg-indigo-500/10": selectedTask === task.id,
                        "h-16": isSubtask,
                      }
                    )}
                  >
                    <GanttBar
                      task={task}
                      dateRange={dateRange}
                      isSubtask={isSubtask}
                      onEdit={(clickedTask) => {
                        handleOpenEditModal(clickedTask);
                      }}
                    />
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Task Details Panel */}
      {selectedTask && (
        <div className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
          {(() => {
            const task = tasks.find((t) => t.id === selectedTask);
            if (!task) return null;
            
            return (
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <button
                      type="button"
                      onClick={() => {
                        if (!usingFallback) {
                          handleOpenEditModal(task);
                        }
                      }}
                      disabled={usingFallback}
                      className="text-left text-lg font-semibold text-gray-900 transition hover:text-indigo-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/60 disabled:cursor-not-allowed dark:text-white"
                    >
                      {task.title}
                    </button>
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{task.description}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleOpenEditModal(task)}
                      disabled={usingFallback}
                      className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                    >
                      Edit Task
                    </button>
                    <button
                      onClick={() => setSelectedTask(null)}
                      className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800"
                    >
                      <svg className="h-5 w-5" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M6 6l8 8M14 6l-8 8" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>
                  </div>
                </div>
                
                <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-3">
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">Progress</h4>
                    <div className="mt-2 flex items-center gap-3">
                      <div className="flex-1 bg-gray-200 rounded-full h-2 dark:bg-gray-700">
                        <div 
                          className={clsx("h-2 rounded-full transition-all", priorityColors[task.priority])}
                          style={{ width: `${task.progress || 0}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium text-gray-900 dark:text-white">
                        {task.progress || 0}%
                      </span>
                    </div>
                  </div>
                  
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">Assignee</h4>
                    <p className="mt-2 text-sm text-gray-900 dark:text-white">{task.assignee || 'Unassigned'}</p>
                  </div>
                  
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">Due Date</h4>
                    <p className="mt-2 text-sm text-gray-900 dark:text-white">
                      {task.dueDate ? new Date(task.dueDate).toLocaleDateString() : 'No due date'}
                    </p>
                  </div>
                </div>
                
                {task.tags && task.tags.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Tags</h4>
                    <div className="flex flex-wrap gap-2">
                      {task.tags.map((tag) => (
                        <span
                          key={tag}
                          className="inline-flex items-center rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600 dark:bg-gray-700/60 dark:text-gray-200"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      )}

      <KanbanTaskModal
        mode="edit"
        isOpen={isEditModalOpen && Boolean(editingTask)}
        title="Edit task"
        description="Update task details and move between columns."
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
          handleEditTranslationFieldChange(
            entryId,
            field as "language" | "title" | "description",
            value
          )
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

export default KanbanGanttPage;
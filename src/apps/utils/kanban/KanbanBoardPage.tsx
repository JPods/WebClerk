import { CSSProperties, ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import PageBreadcrumb from "../../../components/common/PageBreadCrumb";
import { KanbanColumn } from "../../../components/kanban/KanbanColumn";
import { KanbanDragLayer } from "../../../components/kanban/KanbanDragLayer";
import KanbanTaskModal from "../../../components/kanban/KanbanTaskModal";
import { ProjectContactManager } from "../../../components/kanban/ProjectContactManager";
import type { DragItem, DropResult } from "../../../components/kanban/dndTypes";
import { DRAG_TYPE_TASK } from "../../../components/kanban/dndTypes";
import type { TaskFormEditableField, TaskFormState, TranslationFormEntry } from "../../../components/kanban/taskFormTypes";
import type { BoardData, KanbanColumn as KanbanColumnType, KanbanTask, TaskPriority } from "../../../type/kanban";
import { Actions, patchAction } from "../../../api/userProfile";
import { getRecords } from "../../../api/wcapi";
import { createBoardDataFromApi, createEmptyBoardData, extractKanbanItems } from "./kanbanDataMapper";
import { Link } from "react-router";
import { PageRoutes } from "../../../routes/Routes";

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

const priorityOptions: TaskPriority[] = ["low", "medium", "high", "critical"];

const DEFAULT_LANGUAGE_ORDER = ["en", "ar", "bn", "es"];

const LANGUAGE_LABELS: Record<string, string> = {
  en: "English",
  ar: "Arabic",
  bn: "Bengali",
  es: "Spanish",
};

const getLanguageLabel = (code: string) => LANGUAGE_LABELS[code.toLowerCase()] ?? code;

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

const clampPercentageValue = (value: number | undefined): number => {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return 0;
  }
  return Math.max(0, Math.min(100, value));
};

const serializeBurndownValue = (value: number | undefined): string => clampPercentageValue(value).toString();

interface ProjectContact {
  id: number | string;
  attention?: string;
}

interface ProjectOption {
  id: string;
  slug?: string;
  name?: string;
  intent?: string;
  contacts?: ProjectContact[];
}

interface ContactOption {
  id: string;
  label: string;
  searchName: string;
  email?: string;
}

interface FetchActionsOptions {
  projectId?: string;
  contactId?: string;
}

const toBoolean = (value: unknown): boolean => {
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value === "number") {
    return value !== 0;
  }
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (!normalized) {
      return false;
    }
    return ["true", "1", "yes", "y", "t", "on"].includes(normalized);
  }
  return false;
};

const isRecordObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const findFirstObjectArray = (root: unknown): Record<string, unknown>[] => {
  if (!root) {
    return [];
  }

  const queue: unknown[] = [root];
  const visited = new Set<object>();

  while (queue.length) {
    const current = queue.shift();
    if (current === undefined || current === null) {
      continue;
    }

    if (typeof current === "object") {
      const asObject = current as object;
      if (visited.has(asObject)) {
        continue;
      }
      visited.add(asObject);
    }

    if (Array.isArray(current)) {
      const objects = current.filter(isRecordObject);
      if (objects.length) {
        return objects;
      }
      current.forEach((value) => {
        if (value && (isRecordObject(value) || Array.isArray(value))) {
          queue.push(value);
        }
      });
      continue;
    }

    if (isRecordObject(current)) {
      Object.values(current).forEach((value) => {
        if (value && (isRecordObject(value) || Array.isArray(value))) {
          queue.push(value);
        }
      });
    }
  }

  return [];
};

const preferString = (value: unknown): string | undefined => {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed ? trimmed : undefined;
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }
  return undefined;
};

const extractRecordArray = (payload: unknown): Record<string, unknown>[] => {
  if (Array.isArray(payload)) {
    return payload.filter(isRecordObject);
  }
  if (isRecordObject(payload)) {
    const firstLevelArrays: unknown[] = [];
    if (Array.isArray((payload as Record<string, unknown>).results)) {
      firstLevelArrays.push((payload as Record<string, unknown>).results);
    }
    if (Array.isArray((payload as Record<string, unknown>).items)) {
      firstLevelArrays.push((payload as Record<string, unknown>).items);
    }
    if (Array.isArray((payload as Record<string, unknown>).data)) {
      firstLevelArrays.push((payload as Record<string, unknown>).data);
    }
    for (const arrayCandidate of firstLevelArrays) {
      if (Array.isArray(arrayCandidate)) {
        const records = arrayCandidate.filter(isRecordObject);
        if (records.length) {
          return records;
        }
      }
    }
  }
  return findFirstObjectArray(payload);
};

const resolveProjectActivity = (record: Record<string, unknown>): boolean => {
  const candidates: unknown[] = [];
  candidates.push(record.active);
  candidates.push(record.is_active);
  candidates.push(record.status);
  candidates.push(record.state);
  candidates.push(record.enabled);
  candidates.push(record.active_flag);
  if ("project.active" in record) {
    candidates.push((record as Record<string, unknown>)["project.active"]);
  }
  if ("project_is_active" in record) {
    candidates.push((record as Record<string, unknown>)["project_is_active"]);
  }
  const nestedProject = record.project;
  if (nestedProject && typeof nestedProject === "object" && !Array.isArray(nestedProject)) {
    const nestedRecord = nestedProject as Record<string, unknown>;
    candidates.push(nestedRecord.active);
    candidates.push(nestedRecord.is_active);
    candidates.push(nestedRecord.status);
  }

  return candidates.some((value) => {
    if (typeof value === "string") {
      const normalized = value.trim().toLowerCase();
      if (!normalized) {
        return false;
      }
      if (["active", "enabled"].includes(normalized)) {
        return true;
      }
      if (["inactive", "archived", "disabled", "false", "0", "no"].includes(normalized)) {
        return false;
      }
    }
    return toBoolean(value);
  });
};

const createProjectOption = (record: Record<string, unknown>): ProjectOption | null => {
  const nestedProject = record.project && typeof record.project === "object" && !Array.isArray(record.project)
    ? (record.project as Record<string, unknown>)
    : undefined;

  const idCandidates: Array<unknown> = [
    record.id,
    record.pk,
    record.uuid,
    record.project_id,
    record.projectId,
    nestedProject?.id,
    nestedProject?.uuid,
  ];

  let parsedId: string | undefined;
  for (const candidate of idCandidates) {
    const value = preferString(candidate);
    if (value) {
      parsedId = value;
      break;
    }
  }

  if (!parsedId) {
    return null;
  }

  const slugCandidates: Array<unknown> = [
    record.slug,
    record.project_slug,
    record.code,
    record.project_code,
    record.identifier,
    nestedProject?.slug,
    nestedProject?.code,
  ];

  let slug: string | undefined;
  for (const candidate of slugCandidates) {
    const value = preferString(candidate);
    if (value) {
      slug = value;
      break;
    }
  }

  const nameCandidates: Array<unknown> = [
    record.name,
    record.project_name,
    record.title,
    record.label,
    nestedProject?.name,
    nestedProject?.title,
    nestedProject?.label,
  ];

  let resolvedName: string | undefined;
  for (const candidate of nameCandidates) {
    const value = preferString(candidate);
    if (value) {
      resolvedName = value;
      break;
    }
  }

  const intentCandidates: Array<unknown> = [
    record.intent,
    record.description,
    nestedProject?.intent,
    nestedProject?.description,
  ];

  let intent: string | undefined;
  for (const candidate of intentCandidates) {
    const value = preferString(candidate);
    if (value) {
      intent = value;
      break;
    }
  }

  // Extract contacts from refs.links.contact
  let contacts: ProjectContact[] | undefined;
  const refs = record.refs ?? nestedProject?.refs;
  if (refs && typeof refs === "object" && !Array.isArray(refs)) {
    const refsObj = refs as Record<string, unknown>;
    const links = refsObj.links;
    if (links && typeof links === "object" && !Array.isArray(links)) {
      const linksObj = links as Record<string, unknown>;
      const contactList = linksObj.contact;
      if (Array.isArray(contactList)) {
        contacts = contactList
          .filter((c): c is Record<string, unknown> => typeof c === "object" && c !== null)
          .map((c) => ({
            id: c.id as number | string,
            attention: typeof c.attention === "string" ? c.attention : undefined,
          }))
          .filter((c) => c.id !== undefined && c.id !== null);
      }
    }
  }

  return {
    id: parsedId,
    slug,
    name: resolvedName,
    intent,
    contacts,
  };
};

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

const FALLBACK_COLUMN_ID = "column-uncategorized";

const handleBoardMove = (prev: BoardData, { item, result }: OnDragEndArgs): BoardData => {
  if (!result) {
    return prev;
  }

  const sourceColumn = prev.columns[item.sourceColumnId];
  const destinationColumn = prev.columns[result.columnId];

  if (!sourceColumn || !destinationColumn) {
    return prev;
  }

  const sourceIndex = sourceColumn.taskIds.indexOf(item.taskId);
  if (sourceIndex === -1) {
    return prev;
  }

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

const updateTaskFormState = (prev: TaskFormState, field: TaskFormEditableField, value: string): TaskFormState => {
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
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [columnsPerRow, setColumnsPerRow] = useState<number>(4);

  const [projectOptions, setProjectOptions] = useState<ProjectOption[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [isLoadingProjects, setIsLoadingProjects] = useState<boolean>(false);
  const [projectFetchError, setProjectFetchError] = useState<string | null>(null);
  const selectedProject = useMemo(
    () => projectOptions.find((option) => option.id === selectedProjectId),
    [projectOptions, selectedProjectId]
  );
  const selectedProjectName = selectedProject?.name ?? selectedProject?.intent ?? "";

  const [contactOptions, setContactOptions] = useState<ContactOption[]>([]);
  const [selectedContactId, setSelectedContactId] = useState<string>("");
  const [isLoadingContacts, setIsLoadingContacts] = useState<boolean>(false);

  const handleProjectFilterChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setSelectedProjectId(event.target.value);
  };

  const handleContactFilterChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setSelectedContactId(event.target.value);
  };

  // Fetch all active contacts (used when "All projects" is selected)
  const fetchAllContacts = useCallback(async () => {
    setIsLoadingContacts(true);
    try {
      const response = await getRecords("contact", {
        is_active: true,
        limit: 500,
      });
      const records = extractRecordArray(response);
      const options: ContactOption[] = records
        .filter((r: Record<string, unknown>) => r.id !== undefined && r.id !== null)
        .map((r: Record<string, unknown>) => {
          const attention = typeof r.attention === "string" ? r.attention : "";
          const id = String(r.id);
          return {
            id,
            label: attention || `Contact #${id}`,
            searchName: (attention || id).toLowerCase(),
            email: typeof r.email === "string" ? r.email : undefined,
          };
        });

      const uniqueById = new Map<string, ContactOption>();
      options.forEach((option) => {
        if (!uniqueById.has(option.id)) {
          uniqueById.set(option.id, option);
        }
      });

      const sorted = Array.from(uniqueById.values()).sort((a, b) => a.label.localeCompare(b.label));
      console.log("All contacts fetched:", sorted.length);
      setContactOptions(sorted);
      setSelectedContactId((previous) => {
        if (previous && sorted.some((option) => option.id === previous)) {
          return previous;
        }
        return "";
      });
    } catch (error) {
      console.error("Failed to fetch all contacts:", error);
      setContactOptions([]);
    } finally {
      setIsLoadingContacts(false);
    }
  }, []);

  // Populate contacts from selected project's refs.links.contact
  const updateContactsFromProject = useCallback((project: ProjectOption | undefined) => {
    if (!project?.contacts?.length) {
      // No project selected or project has no contacts - fetch all contacts
      return;
    }

    const options: ContactOption[] = project.contacts
      .map((contact) => ({
        id: String(contact.id),
        label: contact.attention || String(contact.id),
        searchName: (contact.attention || String(contact.id)).toLowerCase(),
      }))
      .filter((option) => option.id);

    const uniqueById = new Map<string, ContactOption>();
    options.forEach((option) => {
      if (!uniqueById.has(option.id)) {
        uniqueById.set(option.id, option);
      }
    });

    const sorted = Array.from(uniqueById.values()).sort((a, b) => a.label.localeCompare(b.label));
    console.log("Contacts from project:", sorted);
    setContactOptions(sorted);
    setSelectedContactId((previous) => {
      if (previous && sorted.some((option) => option.id === previous)) {
        return previous;
      }
      return "";
    });
  }, []);

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<KanbanTask | null>(null);

  // Contact Manager Modal state
  const [isContactManagerOpen, setIsContactManagerOpen] = useState(false);

  // Auto-refresh state
  const [lastRefreshTime, setLastRefreshTime] = useState<Date | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const autoRefreshIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Track if any modal is open to pause auto-refresh
  const isAnyModalOpen = isCreateModalOpen || isEditModalOpen || isContactManagerOpen;

  const [createTaskState, setCreateTaskState] = useState<TaskFormState>(() => createInitialTaskFormState(FALLBACK_COLUMN_ID));
  const [editTaskState, setEditTaskState] = useState<TaskFormState>(() => createInitialTaskFormState(FALLBACK_COLUMN_ID));

  const [isSavingCreate, setIsSavingCreate] = useState<boolean>(false);
  const [isSavingEdit, setIsSavingEdit] = useState<boolean>(false);
  const [createModalError, setCreateModalError] = useState<string | null>(null);
  const [editModalError, setEditModalError] = useState<string | null>(null);

  const [createLanguagePickerOpen, setCreateLanguagePickerOpen] = useState(false);
  const [createLanguageSelection, setCreateLanguageSelection] = useState("");
  const [createCustomLanguage, setCreateCustomLanguage] = useState("");
  const [createLanguagePickerError, setCreateLanguagePickerError] = useState<string | null>(null);

  const [editLanguagePickerOpen, setEditLanguagePickerOpen] = useState(false);
  const [editLanguageSelection, setEditLanguageSelection] = useState("");
  const [editCustomLanguage, setEditCustomLanguage] = useState("");
  const [editLanguagePickerError, setEditLanguagePickerError] = useState<string | null>(null);

  //const navigate = useNavigate();

  const resolveDefaultColumnId = useCallback(
    () => board.columnOrder[0] ?? FALLBACK_COLUMN_ID,
    [board.columnOrder]
  );

  const persistTaskReorder = useCallback(
    async (boardSnapshot: BoardData, taskId: string, dropResult: DropResult | null) => {
      if (!dropResult) {
        return;
      }

      const targetColumn = boardSnapshot.columns[dropResult.columnId];
      const task = boardSnapshot.tasks[taskId];
      if (!targetColumn || !task) {
        return;
      }

      // Build full ordering payload for the target column so backend receives complete sequence.
      const wrap = (value: unknown) => ({ mode: "update", value });
      const payload = targetColumn.taskIds.map((id, index) => {
        const targetTask = boardSnapshot.tasks[id];
        const base: Record<string, unknown> = {
          model_name: "action",
          kanban_column: wrap(targetColumn.title),
          kanban_column_id: wrap(targetColumn.id),
          sequence: wrap(index),
          order: wrap(index),
          position: wrap(index),
        };
        if (targetTask?.id) {
          base.id = targetTask.id;
        }
        if (selectedProjectName) {
          base.project_name = wrap(selectedProjectName);
        }
        return base;
      });

      try {
        const projectPayload: Record<string, unknown> = {
          model_name: "project",
          ...(selectedProjectId ? { id: selectedProjectId } : {}),
          bulk: payload,
        };
        await patchAction(projectPayload);
      } catch (error) {
        console.error("Failed to persist kanban reorder", error);
      }
    },
    [selectedProjectId, selectedProjectName]
  );

  const handleDragEnd = useCallback(
    (item: DragItem, dropResult: DropResult | null) => {
      if (item.type !== DRAG_TYPE_TASK) {
        return;
      }
      setBoard((prev) => {
        const next = handleBoardMove(prev, { item, result: dropResult });
        if (next !== prev) {
          void persistTaskReorder(next, item.taskId, dropResult);
        }
        return next;
      });
    },
    [persistTaskReorder]
  );

  const fetchProjects = useCallback(async () => {
    setIsLoadingProjects(true);
    setProjectFetchError(null);
    try {
      const response = await getRecords("project", {
        active: true,
        is_active: true,
        status: "active",
        limit: 500,
      });
      const rawRecords = extractRecordArray(response);
      const activeRecords = rawRecords.filter((record) => resolveProjectActivity(record));
      const fallbackRecords = activeRecords.length ? activeRecords : rawRecords;

      const uniqueById = new Map<string, ProjectOption>();
      fallbackRecords.forEach((record) => {
        const option = createProjectOption(record);
        if (!option) {
          return;
        }
        if (!uniqueById.has(option.id)) {
          uniqueById.set(option.id, option);
        }
      });

      const nextOptions = Array.from(uniqueById.values()).sort((a, b) => {
        const aLabel = a.name ?? a.intent ?? a.id;
        const bLabel = b.name ?? b.intent ?? b.id;
        return aLabel.localeCompare(bLabel);
      });

      if (!nextOptions.length) {
        setProjectOptions([]);
        setSelectedProjectId("");
        setProjectFetchError("No active projects found.");
        return;
      }

      setProjectOptions(nextOptions);
      setProjectFetchError(null);
      setSelectedProjectId((previous) => {
        if (previous && nextOptions.some((option) => option.id === previous)) {
          return previous;
        }
        return "";
      });
    } catch (error) {
      console.error("Failed to fetch active projects", error);
      setProjectOptions([]);
      setProjectFetchError("Unable to load project list.");
      setSelectedProjectId("");
    } finally {
      setIsLoadingProjects(false);
    }
  }, []);

  const fetchActions = useCallback(async ({ projectId, contactId }: FetchActionsOptions = {}) => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const params: Record<string, string> = {};
      if (projectId) {
        params.project_id = projectId;
      }
      if (contactId) {
        // Use contact_id field which is indexed on the Action model
        params.contact_id = contactId;
      }

      const response = await Actions(Object.keys(params).length ? params : undefined);
      if (!response || response.status !== 200) {
        throw new Error("Request failed");
      }

      const items = extractKanbanItems(response);
      
      // Backend now filters by contact_id, so no client-side filtering needed
      if (items.length === 0) {
        setBoard(createEmptyBoardData());
      } else {
        setBoard(createBoardDataFromApi(items));
      }
    } catch (error) {
      console.error("Failed to fetch kanban actions", error);
      const parts: string[] = [];
      if (projectId) {
        parts.push(`project ${projectId}`);
      }
      if (contactId) {
        parts.push(`contact ${contactId}`);
      }
      const contextLabel = parts.length === 0 ? "" : parts.length === 1 ? parts[0] : `${parts[0]} and ${parts[1]}`;
      const message = contextLabel
        ? `Unable to load kanban data for ${contextLabel}. Displaying local state only.`
        : "Unable to load kanban data. Displaying local state only.";
      setFetchError(message);
      setBoard(createEmptyBoardData());
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchProjects();
  }, [fetchProjects]);

  // When project selection changes, update contacts from project's refs.links.contact
  // or fetch all contacts if "All projects" is selected
  useEffect(() => {
    if (selectedProjectId && selectedProject) {
      updateContactsFromProject(selectedProject);
    } else {
      // "All projects" selected - fetch all active contacts
      void fetchAllContacts();
    }
  }, [selectedProjectId, selectedProject, updateContactsFromProject, fetchAllContacts]);

  useEffect(() => {
    void fetchActions({
      projectId: selectedProjectId || undefined,
      contactId: selectedContactId || undefined,
    });
    setLastRefreshTime(new Date());
  }, [fetchActions, selectedProjectId, selectedContactId]);

  // Auto-refresh every 5 minutes (300000ms) - pauses when modal is open
  useEffect(() => {
    const AUTO_REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes

    // Clear any existing interval
    if (autoRefreshIntervalRef.current) {
      clearInterval(autoRefreshIntervalRef.current);
      autoRefreshIntervalRef.current = null;
    }

    // Don't start auto-refresh if a modal is open
    if (isAnyModalOpen) {
      return;
    }

    autoRefreshIntervalRef.current = setInterval(() => {
      console.log("Auto-refreshing kanban board...");
      void fetchActions({
        projectId: selectedProjectId || undefined,
        contactId: selectedContactId || undefined,
      });
      setLastRefreshTime(new Date());
    }, AUTO_REFRESH_INTERVAL);

    return () => {
      if (autoRefreshIntervalRef.current) {
        clearInterval(autoRefreshIntervalRef.current);
        autoRefreshIntervalRef.current = null;
      }
    };
  }, [fetchActions, selectedProjectId, selectedContactId, isAnyModalOpen]);

  // Manual refresh handler
  const handleManualRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await fetchActions({
        projectId: selectedProjectId || undefined,
        contactId: selectedContactId || undefined,
      });
      setLastRefreshTime(new Date());
    } finally {
      setIsRefreshing(false);
    }
  }, [fetchActions, selectedProjectId, selectedContactId]);

  // Format last refresh time for display
  const formatLastRefresh = (date: Date | null): string => {
    if (!date) return "Never";
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    
    if (diffSecs < 10) return "Just now";
    if (diffSecs < 60) return `${diffSecs}s ago`;
    if (diffMins < 60) return `${diffMins}m ago`;
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  useEffect(() => {
    if (board.columnOrder.length === 0) {
      return;
    }
    // Keep columnsPerRow at 4 by default, don't clamp based on available columns
    // This ensures the grid always shows 4 columns per row
  }, [board.columnOrder]);

  // Handler for when contacts are updated via the Contact Manager modal
  const handleContactsUpdated = useCallback((updatedContacts: ProjectContact[]) => {
    if (!selectedProjectId || !selectedProject) return;

    // Update the project option in our local state
    setProjectOptions((prevOptions) => 
      prevOptions.map((option) => {
        if (option.id === selectedProjectId) {
          return { ...option, contacts: updatedContacts };
        }
        return option;
      })
    );

    // Update the contact dropdown options
    updateContactsFromProject({
      ...selectedProject,
      id: selectedProject.id,
      contacts: updatedContacts,
    });
  }, [selectedProjectId, selectedProject, updateContactsFromProject]);

  useEffect(() => {
    const firstColumnId = resolveDefaultColumnId();
    setCreateTaskState((prev) => ({
      ...prev,
      columnId: board.columns[prev.columnId] ? prev.columnId : firstColumnId,
    }));
  }, [board.columns, resolveDefaultColumnId]);

  const columns = useMemo(
    () =>
      board.columnOrder
        .map((columnId) => board.columns[columnId])
        .filter((column): column is KanbanColumnType => Boolean(column)),
    [board]
  );

  const columnOptions = useMemo(
    () => columns.map((column) => ({ id: column.id, title: column.title })),
    [columns]
  );

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
    if (!options.includes(4)) {
      options.push(4);
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
    setCreateTaskState((prev) => updateTaskFormState(prev, field, value));
  };

  const handleEditTaskChange = (field: TaskFormEditableField, value: string) => {
    setEditTaskState((prev) => updateTaskFormState(prev, field, value));
  };

  const updateTranslations = (
    mode: "create" | "edit",
    updater: (current: TranslationFormEntry[]) => TranslationFormEntry[]
  ) => {
    if (mode === "create") {
      setCreateTaskState((prev) => ({
        ...prev,
        translations: updater(prev.translations),
      }));
    } else {
      setEditTaskState((prev) => ({
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
      targetState.translations.map((translation) => normalizeLanguageCode(translation.language)).filter(Boolean)
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

  const handleCreateLanguagePickerToggle = () => {
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
  };

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

  const handleCreateLanguageSelectionChange = (value: string) => {
    setCreateLanguageSelection(value);
    if (value !== "__custom") {
      setCreateCustomLanguage("");
    }
    setCreateLanguagePickerError(null);
  };

  const handleEditLanguageSelectionChange = (value: string) => {
    setEditLanguageSelection(value);
    if (value !== "__custom") {
      setEditCustomLanguage("");
    }
    setEditLanguagePickerError(null);
  };

  const handleCreateLanguageCustomChange = (value: string) => {
    setCreateCustomLanguage(value);
    setCreateLanguagePickerError(null);
  };

  const handleEditLanguageCustomChange = (value: string) => {
    setEditCustomLanguage(value);
    setEditLanguagePickerError(null);
  };

  const handleCreateLanguagePickerSubmit = () => {
    const selection = createLanguageSelection === "__custom" ? createCustomLanguage.trim() : createLanguageSelection;
    if (!selection) {
      setCreateLanguagePickerError("Choose a language before adding.");
      return;
    }
    const result = handleAddTranslation("create", selection);
    if (!result.success) {
      setCreateLanguagePickerError(result.error ?? "Unable to add language.");
      return;
    }
    setCreateLanguagePickerOpen(false);
    setCreateLanguageSelection("");
    setCreateCustomLanguage("");
  };

  const handleEditLanguagePickerSubmit = () => {
    const selection = editLanguageSelection === "__custom" ? editCustomLanguage.trim() : editLanguageSelection;
    if (!selection) {
      setEditLanguagePickerError("Choose a language before adding.");
      return;
    }
    const result = handleAddTranslation("edit", selection);
    if (!result.success) {
      setEditLanguagePickerError(result.error ?? "Unable to add language.");
      return;
    }
    setEditLanguagePickerOpen(false);
    setEditLanguageSelection("");
    setEditCustomLanguage("");
  };

  const handleCreateLanguagePickerCancel = () => {
    setCreateLanguagePickerOpen(false);
    setCreateLanguageSelection("");
    setCreateCustomLanguage("");
    setCreateLanguagePickerError(null);
  };

  const handleEditLanguagePickerCancel = () => {
    setEditLanguagePickerOpen(false);
    setEditLanguageSelection("");
    setEditCustomLanguage("");
    setEditLanguagePickerError(null);
  };

  const createLanguagePickerState = {
    isOpen: createLanguagePickerOpen,
    selection: createLanguageSelection,
    customValue: createCustomLanguage,
    error: createLanguagePickerError,
  };

  const editLanguagePickerState = {
    isOpen: editLanguagePickerOpen,
    selection: editLanguageSelection,
    customValue: editCustomLanguage,
    error: editLanguagePickerError,
  };

  const buildActionPayload = (
    mode: "create" | "edit",
    state: TaskFormState,
    baseTask?: KanbanTask | null
  ): { payload: Record<string, unknown> } | { error: string } => {
    const normalized = new Map<string, { title: string; description: string }>();

    state.translations.forEach((entry) => {
      const language = typeof entry.language === "string" ? normalizeLanguageCode(entry.language) : "";
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

    const translationFields: Record<string, string> = {};
    normalized.forEach((value, language) => {
      translationFields[`action_${language}`] = value.title || "";
      translationFields[`description_${language}`] = value.description || "";
    });

    const languages = Array.from(normalized.keys());

    const removalTokens: string[] = [];
    if (mode === "edit" && baseTask) {
      const originalLanguages = new Set<string>();
      baseTask.languageCodes?.forEach((code) => {
        if (typeof code === "string") {
          originalLanguages.add(normalizeLanguageCode(code));
        }
      });
      Object.keys(baseTask.titleTranslations ?? {}).forEach((code) => originalLanguages.add(normalizeLanguageCode(code)));
      Object.keys(baseTask.descriptionTranslations ?? {}).forEach((code) =>
        originalLanguages.add(normalizeLanguageCode(code))
      );

      originalLanguages.forEach((language) => {
        if (language && !normalized.has(language)) {
          removalTokens.push(`action_${language}`);
          removalTokens.push(`description_${language}`);
        }
      });
    }

    const column = board.columns[state.columnId] ?? board.columns[FALLBACK_COLUMN_ID];
    const columnTitle = column?.title ?? "Uncategorized";
    const assigneeValue = typeof state.assignee === "string" ? state.assignee.trim() : "";
    const assignedTo = assigneeValue
      ? [{ name: assigneeValue }]
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
    const resolvedProgress = clampPercentageValue(
      Number.isNaN(parsedProgress) || parsedProgress < 0 ? fallbackProgress : parsedProgress
    );
    const resolvedBurndown = clampPercentageValue(
      mode === "edit" && baseTask ? baseTask.progress ?? resolvedProgress : resolvedProgress
    );

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
      dt_due: dueTimestamp ?? null,
      dt_start: startTimestamp ?? null,
      dt_end: endTimestamp ?? null,
      progress: resolvedProgress,
      // Backend drops numeric 0 via truthy checks; keep as string to satisfy NOT NULL constraint.
      burndown: serializeBurndownValue(resolvedBurndown),
    };

    if (mode === "edit" && baseTask) {
      payloadItem.id = baseTask.id;
    }

    if (assignedTo.length > 0) {
      payloadItem.assigned_to = assignedTo;
      // If we have a selected contact, include contact_id for direct assignment
      if (selectedContactId) {
        const numericContactId = Number(selectedContactId);
        if (!Number.isNaN(numericContactId) && numericContactId > 0) {
          payloadItem.contact_id = numericContactId;
          // Also add id to assigned_to entry for backend reference
          if (assignedTo[0] && typeof assignedTo[0] === "object") {
            assignedTo[0].id = numericContactId;
          }
        }
      }
    }

    if (!removalTokens.length) {
      payloadItem.needtoremove = "";
    }

    const resolvedProjectName = (() => {
      const selected = selectedProjectName.trim();
      if (selected) {
        return selected;
      }
      if (mode === "edit" && baseTask?.projectName) {
        return baseTask.projectName;
      }
      return "";
    })();

    if (resolvedProjectName) {
      payloadItem.project_name = resolvedProjectName;
    }

    if (selectedProjectId) {
      const numericId = Number(selectedProjectId);
      payloadItem.project_id = Number.isNaN(numericId) ? selectedProjectId : numericId;
    }

    if (selectedProjectId) {
      const numericId = Number(selectedProjectId);
      const projectPayload: Record<string, unknown> = {
        model_name: "project",
        id: Number.isNaN(numericId) ? selectedProjectId : numericId,
        bulk: [payloadItem],
      };

      if (resolvedProjectName) {
        projectPayload.project_name = resolvedProjectName;
      }

      return { payload: projectPayload };
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
      await fetchActions({
        projectId: selectedProjectId || undefined,
        contactId: selectedContactId || undefined,
      });
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
      await fetchActions({
        projectId: selectedProjectId || undefined,
        contactId: selectedContactId || undefined,
      });
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

  const gridStyle = useMemo<CSSProperties>(
    () => ({
      gridTemplateColumns: `repeat(${Math.max(1, columnsPerRow)}, minmax(0, 1fr))`,
    }),
    [columnsPerRow]
  );

  const editModalExtraContent = editingTask ? (
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
  ) : null;

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
            <span>Project</span>
            <select
              value={selectedProjectId}
              onChange={handleProjectFilterChange}
              disabled={isLoadingProjects}
              className="rounded-md border border-gray-200 px-2 py-1 text-xs font-semibold text-gray-700 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 dark:border-gray-700 dark:bg-black dark:text-white"
            >
              <option value="">
                {isLoadingProjects ? "Loading..." : "All projects"}
              </option>
              {projectOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name ?? option.intent ?? option.id}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-500 shadow-sm dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300">
            <span>Contact</span>
            <select
              value={selectedContactId}
              onChange={handleContactFilterChange}
              disabled={isLoadingContacts}
              className="rounded-md border border-gray-200 px-2 py-1 text-xs font-semibold text-gray-700 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 dark:border-gray-700 dark:bg-black dark:text-white"
            >
              <option value="">
                {isLoadingContacts ? "Loading..." : "All contacts"}
              </option>
              {contactOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
            {selectedProjectId && (
              <button
                type="button"
                onClick={() => setIsContactManagerOpen(true)}
                className="ml-1 rounded p-1 text-gray-400 transition hover:bg-gray-100 hover:text-indigo-600 dark:hover:bg-gray-800 dark:hover:text-indigo-400"
                title="Manage project contacts"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </button>
            )}
          </label>
          <label className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-500 shadow-sm dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300">
            <span>Columns</span>
            <select
              value={columnsPerRow}
              onChange={(event) => setColumnsPerRow(Number(event.target.value))}
              className="rounded-md border border-gray-200 px-2 py-1 text-xs font-semibold text-gray-700 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 dark:border-gray-700 dark:bg-black dark:text-white"
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
          <Link
            to={PageRoutes.kanbanGantt}
            className="inline-flex items-center gap-2 rounded-lg border border-indigo-300 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-100 dark:border-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400 dark:hover:bg-indigo-500/20"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
              <path d="M9 22V12h6v10" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Gantt
          </Link>
          <Link
            to={PageRoutes.multiProjectGantt}
            className="inline-flex items-center gap-2 rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 hover:bg-emerald-100 dark:border-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 dark:hover:bg-emerald-500/20"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Multi-Project
          </Link>
          <button
            onClick={() => void handleManualRefresh()}
            disabled={isRefreshing || isLoading}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
            title={`Last refreshed: ${formatLastRefresh(lastRefreshTime)}. Auto-refresh every 5 minutes${isAnyModalOpen ? ' (paused while dialog open)' : ''}`}
          >
            <svg
              className={clsx("h-4 w-4", isRefreshing && "animate-spin")}
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
          <span className="text-xs text-gray-400 dark:text-gray-500" title="Auto-refresh every 5 minutes">
            {formatLastRefresh(lastRefreshTime)}
          </span>
        </div>
      </div>

      {projectFetchError && (
        <div className="flex items-center justify-between rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700 dark:border-amber-800 dark:bg-amber-900/30 dark:text-amber-200">
          <span>{projectFetchError}</span>
          <button
            type="button"
            onClick={() => void fetchProjects()}
            className="rounded-md border border-amber-300 px-3 py-1 text-xs font-semibold text-amber-700 transition hover:bg-amber-100 dark:border-amber-700 dark:text-amber-200 dark:hover:bg-amber-900/50"
          >
            Retry
          </button>
        </div>
      )}

      {fetchError && (
        <div className="flex items-center justify-between rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/30 dark:text-rose-200">
          <span>{fetchError}</span>
          <button
            type="button"
            onClick={() =>
              void fetchActions({
                projectId: selectedProjectId || undefined,
                contactId: selectedContactId || undefined,
              })
            }
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
        <KanbanDragLayer tasks={board.tasks} />
        {isLoading ? (
          <div className="flex h-56 items-center justify-center rounded-3xl border border-dashed border-gray-300 text-sm text-gray-400 dark:border-gray-700 dark:text-gray-500">
            Loading kanban board...
          </div>
        ) : columns.length === 0 ? (
          <div className="flex h-56 items-center justify-center rounded-3xl border border-dashed border-gray-300 text-sm text-gray-400 dark:border-gray-700 dark:text-gray-500">
            No columns configured yet. Start by creating your first task.
          </div>
        ) : (
          <div className="grid gap-4" style={gridStyle}>
            {columns.map((column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                tasks={column.taskIds.map((taskId) => board.tasks[taskId]).filter((task): task is KanbanTask => Boolean(task))}
                onDragEnd={handleDragEnd}
                onTaskClick={handleOpenEditModal}
              />
            ))}
          </div>
        )}
      </DndProvider>

      <KanbanTaskModal
        mode="create"
        isOpen={isCreateModalOpen}
        title="Create new task"
        description="Add the essentials and drop it in the right column."
        isSaving={isSavingCreate}
        submitLabel={isSavingCreate ? "Saving..." : "Create task"}
        onClose={handleCloseCreateModal}
        onSubmit={handleCreateTaskSubmit}
        modalError={createModalError}
        formState={createTaskState}
        onFieldChange={handleCreateTaskChange}
        columnOptions={columnOptions}
        priorityOptions={priorityOptions}
        difficultyOptions={createDifficultyOptions}
        progressOptions={createProgressOptions}
        assigneeOptions={contactOptions}
        translations={createTaskState.translations}
        onTranslationFieldChange={(entryId, field, value) =>
          handleTranslationFieldChange("create", entryId, field as "language" | "title" | "description", value)
        }
        onRemoveTranslation={(entryId) => handleRemoveTranslation("create", entryId)}
        languageOptions={languageOptions}
        languagePickerOptions={availableCreateLanguages}
        languagePickerState={createLanguagePickerState}
        onLanguagePickerToggle={handleCreateLanguagePickerToggle}
        onLanguageSelectionChange={handleCreateLanguageSelectionChange}
        onLanguageCustomChange={handleCreateLanguageCustomChange}
        onLanguagePickerSubmit={handleCreateLanguagePickerSubmit}
        onLanguagePickerCancel={handleCreateLanguagePickerCancel}
      />

      <KanbanTaskModal
        mode="edit"
        isOpen={isEditModalOpen}
        title="Update task"
        description="Fine-tune translations, ownership, or schedule without losing context."
        isSaving={isSavingEdit}
        submitLabel={isSavingEdit ? "Saving..." : "Update task"}
        onClose={handleCloseEditModal}
        onSubmit={handleEditTaskSubmit}
        modalError={editModalError}
        formState={editTaskState}
        onFieldChange={handleEditTaskChange}
        columnOptions={columnOptions}
        priorityOptions={priorityOptions}
        difficultyOptions={editDifficultyOptions}
        progressOptions={editProgressOptions}
        assigneeOptions={contactOptions}
        translations={editTaskState.translations}
        onTranslationFieldChange={(entryId, field, value) =>
          handleTranslationFieldChange("edit", entryId, field as "language" | "title" | "description", value)
        }
        onRemoveTranslation={(entryId) => handleRemoveTranslation("edit", entryId)}
        languageOptions={languageOptions}
        languagePickerOptions={availableEditLanguages}
        languagePickerState={editLanguagePickerState}
        onLanguagePickerToggle={handleEditLanguagePickerToggle}
        onLanguageSelectionChange={handleEditLanguageSelectionChange}
        onLanguageCustomChange={handleEditLanguageCustomChange}
        onLanguagePickerSubmit={handleEditLanguagePickerSubmit}
        onLanguagePickerCancel={handleEditLanguagePickerCancel}
        extraContent={editModalExtraContent}
        currentTask={editingTask}
      />

      {/* Contact Manager Modal */}
      <ProjectContactManager
        isOpen={isContactManagerOpen}
        onClose={() => setIsContactManagerOpen(false)}
        projectId={selectedProjectId}
        projectName={selectedProjectName}
        currentContacts={selectedProject?.contacts ?? []}
        onContactsUpdated={handleContactsUpdated}
      />
    </div>
  );
};

export default KanbanBoardPage;


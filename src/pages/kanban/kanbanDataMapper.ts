import type {
  BoardData,
  KanbanColumn as KanbanColumnType,
  KanbanTask,
  LocalizedTextMap,
  TaskPriority,
} from "../../type/kanban";

export interface ApiKanbanAssignment {
  id?: string | number;
  name?: string;
  [key: string]: unknown;
}

export interface ApiKanbanItem {
  id: string;
  action_en?: string | null;
  action_ar?: string | null;
  action_bn?: string | null;
  action_es?: string | null;
  description_en?: string | null;
  description_ar?: string | null;
  description_bn?: string | null;
  description_es?: string | null;
  languages?: string[];
  kanban_column?: string | null;
  priority?: number | null;
  difficulty?: number | null;
  status?: string | null;
  dt_created?: string | null;
  dt_updated?: string | null;
  dt_expected?: string | null;
  dt_due?: string | null;
  dt_completed?: string | null;
  dt_start?: string | null;
  dt_end?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  expected_by?: string | null;
  due_by?: string | null;
  completed_by?: string | null;
  start_by?: string | null;
  end_by?: string | null;
  assigned_to?: ApiKanbanAssignment[];
  linkage?: number | null;
  kanban_meta?: unknown;
  refs?: {
    tags?: string[];
    [key: string]: unknown;
  };
  comments?: {
    public?: string;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export const createEmptyBoardData = (): BoardData => ({
  tasks: {},
  columns: {
    "column-uncategorized": {
      id: "column-uncategorized",
      title: "Uncategorized",
      taskIds: [],
    },
  },
  columnOrder: ["column-uncategorized"],
});

const mapPriorityValue = (value?: number | null): TaskPriority => {
  if (typeof value !== "number") return "medium";
  if (value >= 4) return "critical";
  if (value >= 3) return "high";
  if (value >= 2) return "medium";
  return "low";
};

const slugifyColumn = (rawTitle: string): string => {
  const cleaned = rawTitle
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return `column-${cleaned || "uncategorized"}`;
};

const buildTranslations = (
  entries: Array<[string, string | null | undefined]>
): LocalizedTextMap | undefined => {
  const map: LocalizedTextMap = {};
  entries.forEach(([lang, value]) => {
    if (value) {
      map[lang] = value;
    }
  });
  return Object.keys(map).length > 0 ? map : undefined;
};

export const createBoardDataFromApi = (items: ApiKanbanItem[]): BoardData => {
  const tasks: Record<string, KanbanTask> = {};
  const columns: Record<string, KanbanColumnType> = {};
  const columnOrder: string[] = [];

  items.forEach((item) => {
    if (!item?.id) return;

    const rawColumnTitle = (item.kanban_column && String(item.kanban_column).trim()) || "Uncategorized";
    const columnId = slugifyColumn(rawColumnTitle);

    if (!columns[columnId]) {
      columns[columnId] = { id: columnId, title: rawColumnTitle, taskIds: [] };
      columnOrder.push(columnId);
    }

    columns[columnId].taskIds.push(item.id);

    const titleTranslations = buildTranslations([
      ["en", item.action_en],
      ["ar", item.action_ar],
      ["bn", item.action_bn],
      ["es", item.action_es],
    ]);

    const descriptionTranslations = buildTranslations([
      ["en", item.description_en],
      ["ar", item.description_ar],
      ["bn", item.description_bn],
      ["es", item.description_es],
    ]);

    const assignedToRecords =
      item.assigned_to?.map((person, index) => ({
        id: person?.id !== undefined ? String(person.id) : `${item.id}-assignee-${index}`,
        name: person?.name ?? `Assignee ${index + 1}`,
      })) ?? [];

    const tags = item.refs?.tags ?? [];

    tasks[item.id] = {
      id: item.id,
      title:
        item.action_en ||
        item.action_ar ||
        item.action_bn ||
        item.action_es ||
        `Task ${item.id}`,
      description:
        item.description_en ??
        item.description_ar ??
        item.description_bn ??
        item.description_es ??
        undefined,
      priority: mapPriorityValue(item.priority),
      priorityValue: item.priority ?? undefined,
      difficulty: item.difficulty ?? undefined,
      status: item.status ?? undefined,
      dueDate: item.dt_due ?? undefined,
      assignee: assignedToRecords[0]?.name,
      assignedTo: assignedToRecords.length ? assignedToRecords : undefined,
      languageCodes: item.languages && item.languages.length ? item.languages : undefined,
      titleTranslations,
      descriptionTranslations,
      tags: tags.length ? tags : undefined,
      linkage: item.linkage ?? undefined,
      remarks: item.comments?.public || undefined,
    };
  });

  return { tasks, columns, columnOrder };
};

export const extractKanbanItems = (raw: unknown): ApiKanbanItem[] => {
  if (!raw) return [];

  const drill = (candidate: any): ApiKanbanItem[] => {
    if (!candidate) return [];

    if (Array.isArray(candidate)) {
      return candidate as ApiKanbanItem[];
    }

    if (candidate?.results && Array.isArray(candidate.results)) {
      return candidate.results as ApiKanbanItem[];
    }

    if (candidate?.data?.results && Array.isArray(candidate.data.results)) {
      return candidate.data.results as ApiKanbanItem[];
    }

    if (candidate?.data && Array.isArray(candidate.data)) {
      return candidate.data as ApiKanbanItem[];
    }

    if (candidate?.data?.data?.results && Array.isArray(candidate.data.data.results)) {
      return candidate.data.data.results as ApiKanbanItem[];
    }

    if (candidate?.data?.data && Array.isArray(candidate.data.data)) {
      return candidate.data.data as ApiKanbanItem[];
    }

    return [];
  };

  const levels = [raw, (raw as any)?.data];
  for (const level of levels) {
    const extracted = drill(level);
    if (extracted.length) {
      return extracted;
    }
  }

  return [];
};

import type {
  BoardData,
  KanbanColumn as KanbanColumnType,
  KanbanTask,
  LocalizedTextMap,
  TaskPriority,
} from "./type/kanban";

export interface ApiKanbanAssignment {
  id?: string | number;
  name?: string;
  [key: string]: unknown;
}

export interface ApiKanbanItem {
  id: string;
  is_deleted?: boolean | string | number;
  is_archived?: boolean | string | number;
  is_active?: boolean | string | number;
  project_name?: string | null;
  project_id?: number | null;
  action?: Record<string, string> | null;
  description?: Record<string, string> | null;
  action_en?: string | null;
  action_ar?: string | null;
  action_bn?: string | null;
  action_es?: string | null;
  action_id?: string | null;
  description_en?: string | null;
  description_ar?: string | null;
  description_bn?: string | null;
  description_es?: string | null;
  description_id?: string | null;
  languages?: string[];
  kanban_column?: string | null;
  priority?: number | null;
  difficulty?: number | null;
  status?: string | null;
  dt_created?: string | null;
  dt_updated?: string | null;
  dt_expected?: string | null;
  dt_deadline?: string | null;
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
  project_metadata?: unknown;
  refs?: {
    tags?: string[];
    links?: {
      parent?: string;
      items?: unknown[];
      contacts?: unknown[];
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
  prefs?: {
    userdefined?: {
      progress?: number | string | null;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
  comments?: {
    public?: string;
    [key: string]: unknown;
  };
  progress?: number | string | null;
  progress_percent?: number | string | null;
  progress_percentage?: number | string | null;
  completion?: number | string | null;
  completion_percent?: number | string | null;
  completion_percentage?: number | string | null;
  sequence?: number | null;
  order?: number | null;
  position?: number | null;
  [key: string]: unknown;
}

const isTrue = (value: unknown): boolean => value === true || value === "true" || value === 1 || value === "1";
const isFalse = (value: unknown): boolean => value === false || value === "false" || value === 0 || value === "0";

export const createEmptyBoardData = (): BoardData => ({
  tasks: {},
  columns: {
    "column-uncategorized": {
      id: "column-uncategorized",
      title: "Uncategorized",
      task_ids: [],
    },
  },
  column_order: ["column-uncategorized"],
});

const PREFERRED_COLUMN_GROUPS: string[][] = [
  ["backlog"],
  ["progress", "inprogress", "in-process", "inprocess"],
  ["review"],
  ["complete", "completed", "done"],
];

const normalizeColumnKey = (input: string): string => input.trim().toLowerCase().replace(/[^a-z0-9]+/g, "");

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

const getColumnWeight = (column: KanbanColumnType): number => {
  const normalizedTitle = normalizeColumnKey(column.title);
  const normalizedId = normalizeColumnKey(column.id.replace(/^column-/, ""));

  for (let index = 0; index < PREFERRED_COLUMN_GROUPS.length; index += 1) {
    const group = PREFERRED_COLUMN_GROUPS[index];
    const matches = group.some((key) => {
      const normalizedKey = normalizeColumnKey(key);
      return normalizedTitle === normalizedKey || normalizedId === normalizedKey;
    });
    if (matches) {
      return index;
    }
  }

  return PREFERRED_COLUMN_GROUPS.length;
};

const PROGRESS_FIELD_CANDIDATES = [
  "percent_complete",
];

const SEQUENCE_FIELD_CANDIDATES = [
  "sequence",
  "order",
  "position",
];

const coerceNumericValue = (value: unknown): number | undefined => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const trimmed = value.trim().replace(/%$/, "");
    if (!trimmed) {
      return undefined;
    }
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : undefined;
  }
  return undefined;
};

const normalizeProgressInput = (value?: number): number | undefined => {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return undefined;
  }
  if (value >= 0 && value <= 1) {
    return Math.round(value * 100);
  }
  return Math.round(Math.max(0, Math.min(100, value)));
};

const extractProgressValue = (item: ApiKanbanItem): number | undefined => {
  // Only use percent_complete as canonical field
  const candidate = coerceNumericValue((item as Record<string, unknown>)["percent_complete"]);
  if (candidate !== undefined) {
    return normalizeProgressInput(candidate);
  }
  return undefined;
};

const extractSequenceValue = (item: ApiKanbanItem): number | undefined => {
  for (const key of SEQUENCE_FIELD_CANDIDATES) {
    const candidate = coerceNumericValue((item as Record<string, unknown>)[key]);
    if (candidate !== undefined) {
      return Math.round(candidate);
    }
  }

  const metaSources = [item.kanban_meta, item.refs];
  for (const source of metaSources) {
    if (!source || typeof source !== "object") {
      continue;
    }
    for (const key of SEQUENCE_FIELD_CANDIDATES) {
      const candidate = coerceNumericValue((source as Record<string, unknown>)[key]);
      if (candidate !== undefined) {
        return Math.round(candidate);
      }
    }
  }

  return undefined;
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

const normalizeLanguageKey = (key: string): string => key.trim().toLowerCase();

const coerceTranslationString = (input: unknown): string | undefined => {
  if (input === null || input === undefined) {
    return undefined;
  }
  if (typeof input === "string") {
    return input;
  }
  if (typeof input === "number" || typeof input === "boolean") {
    return String(input);
  }
  if (Array.isArray(input)) {
    for (const value of input) {
      const candidate = coerceTranslationString(value);
      if (candidate) {
        return candidate;
      }
    }
    return undefined;
  }
  if (typeof input === "object") {
    const candidateKeys = ["value", "text", "title", "description", "display_value"];    
    for (const key of candidateKeys) {
      if (Object.prototype.hasOwnProperty.call(input, key)) {
        const nested = coerceTranslationString((input as Record<string, unknown>)[key]);
        if (nested) {
          return nested;
        }
      }
    }
    // As a last resort, grab the first primitive child value
    for (const value of Object.values(input as Record<string, unknown>)) {
      const nested = coerceTranslationString(value);
      if (nested) {
        return nested;
      }
    }
  }
  return undefined;
};

const assignTranslationValue = (
  target: Map<string, string | null | undefined>,
  language: string,
  rawValue: unknown
) => {
  const normalized = normalizeLanguageKey(language);
  if (!normalized || target.has(normalized)) {
    return;
  }
  const coerced = coerceTranslationString(rawValue);
  if (coerced !== undefined) {
    target.set(normalized, coerced);
    return;
  }
  if (rawValue === null) {
    target.set(normalized, undefined);
  }
};

const collectLocalizedEntries = (
  item: ApiKanbanItem,
  fieldPrefix: string,
  fallbackEntries: Array<[string, string | null | undefined]> = []
): Array<[string, string | null | undefined]> => {
  const collected = new Map<string, string | null | undefined>();
  const record = item as Record<string, unknown>;
  const pattern = new RegExp(`^${fieldPrefix}(?:[._])([a-z0-9-]+)$`, "i");

  // Process nested objects FIRST (highest priority)
  const nestedField = record[fieldPrefix];
  if (nestedField && typeof nestedField === "object" && !Array.isArray(nestedField)) {
    Object.entries(nestedField as Record<string, unknown>).forEach(([language, rawValue]) => {
      assignTranslationValue(collected, language, rawValue);
    });
  }

  // Then process flat fields (medium priority)
  Object.entries(record).forEach(([key, raw]) => {
    const match = key.match(pattern);
    if (!match) return;
    assignTranslationValue(collected, match[1], raw);
  });

  // Finally process fallback entries (lowest priority)
  fallbackEntries.forEach(([language, value]) => {
    assignTranslationValue(collected, language, value);
  });

  return Array.from(collected.entries());
};

const getFirstTranslationValue = (map?: LocalizedTextMap): string | undefined => {
  if (!map) {
    return undefined;
  }
  const [firstKey] = Object.keys(map);
  return firstKey ? map[firstKey] : undefined;
};

export const createBoardDataFromApi = (items: ApiKanbanItem[]): BoardData => {
  const tasks: Record<string, KanbanTask> = {};
  const columns: Record<string, KanbanColumnType> = {};
  const columnOrder: string[] = [];

    const sortedItems = items
      .map((item, index) => ({ item, index, sequence: extractSequenceValue(item) }))
      .sort((a, b) => {
        const aSeq = a.sequence;
        const bSeq = b.sequence;
        if (typeof aSeq === "number" && typeof bSeq === "number") {
          if (aSeq !== bSeq) return aSeq - bSeq;
          return a.index - b.index;
        }
        if (typeof aSeq === "number") return -1;
        if (typeof bSeq === "number") return 1;
        return a.index - b.index;
      });

    sortedItems.forEach(({ item }) => {
    if (!item?.id) return;
    if (isTrue(item.is_deleted) || isTrue(item.is_archived) || isFalse(item.is_active)) return;

    const rawColumnTitle = (item.kanban_column && String(item.kanban_column).trim()) || "Uncategorized";
    const columnId = slugifyColumn(rawColumnTitle);

    if (!columns[columnId]) {
    columns[columnId] = { id: columnId, title: rawColumnTitle, task_ids: [] };
      columnOrder.push(columnId);
    }

    columns[columnId].task_ids.push(item.id);

    const actionEntries = collectLocalizedEntries(item, "action", [
      ["en", item.action_en],
      ["ar", item.action_ar],
      ["bn", item.action_bn],
      ["es", item.action_es],
      ["id", item.action_id],
    ]);

    const descriptionEntries = collectLocalizedEntries(item, "description", [
      ["en", item.description_en],
      ["ar", item.description_ar],
      ["bn", item.description_bn],
      ["es", item.description_es],
      ["id", item.description_id],
    ]);

    const titleTranslations = buildTranslations(actionEntries);
    const descriptionTranslations = buildTranslations(descriptionEntries);

    const translationLanguages = new Set<string>();
    actionEntries.forEach(([language]) => translationLanguages.add(language));
    descriptionEntries.forEach(([language]) => translationLanguages.add(language));
    item.languages?.forEach((language) => {
      if (typeof language === "string" && language.trim()) {
        translationLanguages.add(language.trim().toLowerCase());
      }
    });
    const languageCodes = translationLanguages.size ? Array.from(translationLanguages) : undefined;

    const assignedToRecords =
      item.assigned_to?.map((person, index) => ({
        id: person?.id !== undefined ? String(person.id) : `${item.id}-assignee-${index}`,
        name: person?.name ?? `Assignee ${index + 1}`,
      })) ?? [];

    const tags = item.refs?.tags ?? [];
    const progressValue = extractProgressValue(item);
    const sequenceValue = extractSequenceValue(item);

    tasks[item.id] = {
      id: item.id,
      title:
        titleTranslations?.en ||
        getFirstTranslationValue(titleTranslations) ||
        item.action_en ||
        item.action_ar ||
        item.action_bn ||
        item.action_es ||
        `Task ${item.id}`,
      description:
        descriptionTranslations?.en ??
        getFirstTranslationValue(descriptionTranslations) ??
        item.description_en ??
        item.description_ar ??
        item.description_bn ??
        item.description_es ??
        undefined,
      priority: mapPriorityValue(item.priority),
      project_name: item.project_name ?? undefined,
      project_id: item.project_id ?? undefined,
      priority_value: item.priority ?? undefined,
      difficulty: item.difficulty ?? undefined,
      status: typeof item.status === "string" ? item.status : undefined,
      dt_deadline: normalizeDate(item.dt_deadline),
      dt_start: normalizeDate(item.dt_start),
      dt_expected: normalizeDate(item.dt_expected),
      dt_completed: normalizeDate(item.dt_completed),
      dt_created: normalizeDate(item.dt_created) ?? undefined,
      dt_updated: normalizeDate(item.dt_updated),
      assignee: assignedToRecords[0]?.name,
      assigned_to: assignedToRecords.length ? assignedToRecords : undefined,
      language_codes: languageCodes,
      title_translations: titleTranslations,
      description_translations: descriptionTranslations,
      tags: tags.length ? tags : undefined,
      linkage: item.linkage ?? undefined,
      remarks: item.comments?.public || undefined,
      progress: progressValue,
      sequence: sequenceValue,
      refs: item.refs,
    };
  });

  const sortedColumnOrder = columnOrder
    .map((id, index) => {
      const column = columns[id];
      const weight = column ? getColumnWeight(column) : PREFERRED_COLUMN_GROUPS.length;
      return { id, weight, index };
    })
    .sort((a, b) => {
      if (a.weight !== b.weight) {
        return a.weight - b.weight;
      }
      return a.index - b.index;
    })
    .map(({ id }) => id);

  return { tasks, columns, column_order: sortedColumnOrder };
};

const normalizeDate = (value?: string | number | null): number | null | undefined => {
  if (value == null) return undefined;
  const dateObj = typeof value === "number" ? new Date(value) : new Date(value);
  const time = dateObj.getTime();
  return isNaN(time) ? undefined : time;
};

export const mapToApi = (task: KanbanTask): ApiKanbanItem => {
  return {
    id: task.id,
    dt_deadline: normalizeDate(task.dt_deadline),
    dt_start: normalizeDate(task.dt_start),
    dt_expected: normalizeDate(task.dt_expected),
    dt_completed: normalizeDate(task.dt_completed),
  } as ApiKanbanItem;
};

const isPlainObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const looksLikeKanbanEntry = (entry: Record<string, unknown>): boolean => {
  const keys = Object.keys(entry).map((key) => key.toLowerCase());
  if (keys.includes("id")) {
    return true;
  }
  const hints = ["action", "description", "kanban", "priority", "dt_", "status", "assigned"];
  return keys.some((key) => hints.some((hint) => key.includes(hint)));
};

const coerceKanbanArray = (value: unknown): ApiKanbanItem[] | null => {
  if (!Array.isArray(value) || value.length === 0) {
    return null;
  }
  const objects = value.filter((entry): entry is ApiKanbanItem => isPlainObject(entry));
  if (!objects.length) {
    return null;
  }
  if (!objects.some((entry) => looksLikeKanbanEntry(entry as Record<string, unknown>))) {
    return null;
  }
  return objects;
};

const drill = (candidate: any): ApiKanbanItem[] => {
  if (!candidate) return [];

  const direct = coerceKanbanArray(candidate);
  if (direct) {
    return direct;
  }

  const arrayKeys = [
    "results",
    "records",
    "items",
    "data",
    "payload",
    "value",
    "rows",
  ];

  if (isPlainObject(candidate)) {
    const record = candidate as Record<string, unknown>;

    for (const key of arrayKeys) {
      const nested = coerceKanbanArray(record[key]);
      if (nested) {
        return nested;
      }
    }

    const dataLayer = record.data as any;
    if (dataLayer?.results && Array.isArray(dataLayer.results)) {
      return dataLayer.results as ApiKanbanItem[];
    }

    if (dataLayer?.records && Array.isArray(dataLayer.records)) {
      return dataLayer.records as ApiKanbanItem[];
    }

    if (dataLayer?.payload?.results && Array.isArray(dataLayer.payload.results)) {
      return dataLayer.payload.results as ApiKanbanItem[];
    }

    const payloadLayer = record.payload as any;
    if (payloadLayer?.results && Array.isArray(payloadLayer.results)) {
      return payloadLayer.results as ApiKanbanItem[];
    }

    if (dataLayer?.payload && Array.isArray(dataLayer.payload)) {
      return dataLayer.payload as ApiKanbanItem[];
    }

    if (payloadLayer && Array.isArray(payloadLayer)) {
      return payloadLayer as ApiKanbanItem[];
    }

    if (dataLayer?.data?.results && Array.isArray(dataLayer.data.results)) {
      return dataLayer.data.results as ApiKanbanItem[];
    }

    if (dataLayer?.data && Array.isArray(dataLayer.data)) {
      return dataLayer.data as ApiKanbanItem[];
    }
  }

  return [];
};

const deepScanForItems = (root: unknown): ApiKanbanItem[] => {
  const queue: unknown[] = [root];
  const visited = new Set<unknown>();
  const MAX_NODES = 200;
  let processed = 0;

  while (queue.length && processed < MAX_NODES) {
    const current = queue.shift();
    processed += 1;

    const asArray = coerceKanbanArray(current);
    if (asArray) {
      return asArray;
    }

    if (!isPlainObject(current) && !Array.isArray(current)) {
      continue;
    }

    if (visited.has(current as object)) {
      continue;
    }
    visited.add(current as object);

    const values = Array.isArray(current)
      ? (current as unknown[])
      : Object.values(current as Record<string, unknown>);

    for (const value of values) {
      const nestedArray = coerceKanbanArray(value);
      if (nestedArray) {
        return nestedArray;
      }
      if (value && (isPlainObject(value) || Array.isArray(value))) {
        queue.push(value);
      }
    }
  }

  return [];
};

export const extractKanbanItems = (raw: unknown): ApiKanbanItem[] => {
  if (!raw) return [];

  const levels = [raw, (raw as any)?.data];
  for (const level of levels) {
    const extracted = drill(level);
    if (extracted.length) {
      return extracted;
    }
  }

  const fallback = deepScanForItems(raw);
  if (fallback.length) {
    return fallback;
  }

  return [];
};

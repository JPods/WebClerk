/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { CSSProperties, ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import { DndProvider, useDragLayer, useDrop } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import PageBreadcrumb from "../../../components/common/PageBreadCrumb";
import { KanbanColumn } from "./KanbanColumn";
import { KanbanDragLayer } from "./KanbanDragLayer";
import KanbanTaskModal from "./KanbanTaskModal";
import { ActionFloatingWindow } from "../../core/models/action/pages/ActionFloatingWindow";
import { ProjectContactManager } from "./ProjectContactManager";
import type { DragItem, DropResult } from "./dndTypes";
import { DRAG_TYPE_TASK } from "./dndTypes";
import type { TaskFormEditableField, TaskFormState, TranslationFormEntry, TaskAttachment, TaskFormFieldValue } from "./taskFormTypes";
import type { BoardData, KanbanColumn as KanbanColumnType, KanbanTask, TaskPriority } from "./type/kanban";
import { Actions, patchAction } from "../../../api/userProfile";
import { getRecords, manageAction, saveRecord, uploadDocument } from "../../../api/wcapi";
import { createBoardDataFromApi, createEmptyBoardData, extractKanbanItems } from "./kanbanDataMapper";
import { Link, useSearchParams } from "react-router";
import { PageRoutes } from "../../../routes/Routes";
import RippleLoader from "@/components/common/RippleLoader";
import { NetworkInfo } from "@/routes/network";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

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

const parseMaybeObject = (value: unknown): Record<string, unknown> | null => {
  if (isRecordObject(value)) {
    return value;
  }
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      return isRecordObject(parsed) ? parsed : null;
    } catch {
      return null;
    }
  }
  return null;
};

const toAbsoluteAssetUrl = (url?: string): string | undefined => {
  if (!url || typeof url !== "string") {
    return undefined;
  }

  const trimmed = url.trim();
  if (!trimmed) {
    return undefined;
  }

  if (/^https?:\/\//i.test(trimmed) || trimmed.startsWith("blob:")) {
    return trimmed;
  }

  const envBase = typeof import.meta.env.VITE_API_URL === "string" ? import.meta.env.VITE_API_URL : "";
  const configuredBase = (envBase || NetworkInfo.API_URL || "http://localhost:8000").trim();
  const base = configuredBase.replace(/\/$/, "");
  const path = trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
  return `${base}${path}`;
};

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

// Parse date from project name/slug using formats: title_YYYY-MM-DD or title-YYYY-MM-DD
const parseProjectDateFromLabel = (label?: string): Date | null => {
  if (!label) return null;
  const m = label.match(/(?:_|-)(\d{4}-\d{2}-\d{2})$/);
  if (!m) return null;
  const dateStr = m[1];
  const d = new Date(dateStr + "T00:00:00Z");
  return Number.isNaN(d.getTime()) ? null : d;
};

// Choose default project id: the project whose parsed date is the earliest date >= today
const findDefaultProjectId = (projects: ProjectOption[]): string | undefined => {
  if (!projects || projects.length === 0) return undefined;
  const today = new Date();
  // normalize to UTC date-only for comparison
  const todayUtc = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));

  let chosen: { id: string; date: Date } | undefined;
  for (const p of projects) {
    const label = p.name ?? p.slug ?? p.id;
    const d = parseProjectDateFromLabel(label);
    if (!d) continue;
    // zero-time UTC normalization
    const dUtc = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
    if (dUtc.getTime() < todayUtc.getTime()) continue; // skip past dates
    if (!chosen || dUtc.getTime() < chosen.date.getTime()) {
      chosen = { id: p.id, date: dUtc };
    }
  }

  return chosen?.id;
};

const parseAttachmentDocumentId = (attachment: TaskAttachment): number | null => {
  if (typeof attachment.documentId === "number" && Number.isFinite(attachment.documentId)) {
    return attachment.documentId;
  }
  const fallback = Number(attachment.id);
  return Number.isFinite(fallback) && fallback > 0 ? fallback : null;
};

const extractAttachmentChecksums = (attachments: TaskAttachment[] | undefined): string[] => {
  if (!Array.isArray(attachments)) return [];
  const checksums = attachments
    .map((attachment) => (typeof attachment.checksum === "string" ? attachment.checksum.trim() : ""))
    .filter((checksum): checksum is string => Boolean(checksum));
  return Array.from(new Set(checksums));
};

const extractTaskAttachmentHashes = (task: KanbanTask): string[] => {
  const refs = parseMaybeObject(task.refs);
  if (!refs) {
    return [];
  }
  const raw = refs.attachments_sha256;
  if (!Array.isArray(raw)) {
    return [];
  }
  return Array.from(
    new Set(
      raw
        .map((value) => (typeof value === "string" ? value.trim() : ""))
        .filter((value): value is string => Boolean(value))
    )
  );
};

const mapDocumentRecordToAttachment = (doc: Record<string, unknown>, index: number): TaskAttachment | null => {
  const idCandidate = Number(doc.id);
  if (!Number.isFinite(idCandidate) || idCandidate <= 0) {
    return null;
  }

  const name = typeof doc.name === "string" && doc.name ? doc.name : `Attachment ${index + 1}`;
  const type = (typeof doc.mime_type === "string" && doc.mime_type) || "application/octet-stream";
  const pathObj = parseMaybeObject(doc.path);
  const url = toAbsoluteAssetUrl(typeof pathObj?.url === "string" ? pathObj.url : undefined);
  const sizeRaw = Number(doc.size_bytes);
  const size = Number.isFinite(sizeRaw) ? sizeRaw : 0;
  const isImage = type.startsWith("image/") || /\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(name);

  return {
    id: `doc-${idCandidate}`,
    documentId: idCandidate,
    name,
    type,
    size,
    checksum: typeof doc.checksum === "string" ? doc.checksum : undefined,
    url,
    previewUrl: isImage ? url : undefined,
  };
};

const mergeAttachmentsByDocumentId = (primary: TaskAttachment[], secondary: TaskAttachment[]): TaskAttachment[] => {
  const merged = new Map<string, TaskAttachment>();
  [...primary, ...secondary].forEach((attachment, index) => {
    const id = parseAttachmentDocumentId(attachment);
    const key = id ? `doc-${id}` : `${attachment.id || "local"}-${index}`;
    if (!merged.has(key)) {
      merged.set(key, attachment);
    }
  });
  return Array.from(merged.values());
};

const createTranslationEntry = (language: string, title = "", description = ""): TranslationFormEntry => ({
  id: createLocalId(),
  language,
  title,
  description,
});

const normalizeLanguageCode = (code: string) => code.trim().toLowerCase();

const createInitialTaskFormState = (columnId: string): TaskFormState => {
  // Helper to format date as datetime-local string (YYYY-MM-DDTHH:MM)
  const pad = (n: number) => n.toString().padStart(2, "0");
  const formatDT = (d: Date) =>
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;

  const now = new Date();
  const sevenDaysLater = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);

  return {
    translations: [createTranslationEntry(DEFAULT_LANGUAGE_ORDER[0])],
    columnId,
    projectId: "",
    priority: "medium",
    dt_deadline: formatDT(sevenDaysLater),
    dt_start: formatDT(now),
    dt_completed: "",
    dt_expected: "",
    assigned_to: [],
    difficulty: DEFAULT_DIFFICULTY_STRING,
    percent_complete: DEFAULT_PROGRESS_STRING,
    is_active: "true",
    attachments: [],
  };
};

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
  task.language_codes?.forEach((code: string) => languages.add(normalizeLanguageCode(code)));
  Object.keys(task.title_translations ?? {}).forEach((code: string) => languages.add(normalizeLanguageCode(code)));
  Object.keys(task.description_translations ?? {}).forEach((code: string) => languages.add(normalizeLanguageCode(code)));

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
      task.title_translations?.[language] ?? fallbackTitle,
      task.description_translations?.[language] ?? fallbackDescription
    );
  });
};

const buildTranslationMapsFromEntries = (entries: TranslationFormEntry[]) => {
  const titleTranslations: Record<string, string> = {};
  const descriptionTranslations: Record<string, string> = {};
  const languageCodes = new Set<string>();

  entries.forEach((entry) => {
    const language = normalizeLanguageCode(entry.language);
    if (!language) {
      return;
    }

    const title = entry.title?.trim() ?? "";
    const description = entry.description?.trim() ?? "";

    if (title) {
      titleTranslations[language] = title;
      languageCodes.add(language);
    }
    if (description) {
      descriptionTranslations[language] = description;
      languageCodes.add(language);
    }
  });

  const firstTitle = Object.values(titleTranslations).find(Boolean);
  const firstDescription = Object.values(descriptionTranslations).find(Boolean);

  return {
    titleTranslations: Object.keys(titleTranslations).length ? titleTranslations : undefined,
    descriptionTranslations: Object.keys(descriptionTranslations).length ? descriptionTranslations : undefined,
    title: titleTranslations.en || firstTitle,
    description: descriptionTranslations.en || firstDescription,
    languageCodes: languageCodes.size ? Array.from(languageCodes) : undefined,
  };
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

  const sourceIndex = sourceColumn.task_ids.indexOf(item.taskId);
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
    const updated = [...sourceColumn.task_ids];
    updated.splice(sourceIndex, 1);
    nextColumns[sourceColumn.id] = { ...sourceColumn, task_ids: updated };
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

    if (sourceColumn.task_ids.join() === reordered.join()) {
      return prev;
    }

    nextColumns[sourceColumn.id] = { ...sourceColumn, task_ids: reordered };
    return { ...prev, columns: nextColumns };
  }

  removeFromSource();
  const destinationTaskIds = [...destinationColumn.task_ids];
  const clampedIndex = Math.max(0, Math.min(rawDestinationIndex, destinationTaskIds.length));
  destinationTaskIds.splice(clampedIndex, 0, item.taskId);

  nextColumns[destinationColumn.id] = { ...destinationColumn, task_ids: destinationTaskIds };

  return {
    ...prev,
    columns: nextColumns,
  };
};

const removeTaskFromBoardState = (prev: BoardData, taskId: string): BoardData => {
  let columnsChanged = false;

  const nextColumns = Object.entries(prev.columns).reduce<Record<string, KanbanColumnType>>((acc, [columnId, column]) => {
    const nextTaskIds = column.task_ids.filter((id) => id !== taskId);
    if (nextTaskIds.length !== column.task_ids.length) {
      columnsChanged = true;
      acc[columnId] = { ...column, task_ids: nextTaskIds };
    } else {
      acc[columnId] = column;
    }
    return acc;
  }, {});

  if (!columnsChanged) {
    return prev;
  }

  const { [taskId]: _removed, ...remainingTasks } = prev.tasks;

  return {
    ...prev,
    columns: nextColumns,
    tasks: remainingTasks,
  };
};

const TrashDropZone: React.FC<{ isDeleting?: boolean }> = ({ isDeleting = false }) => {
  const { isDragging, itemType } = useDragLayer((monitor) => ({
    isDragging: monitor.isDragging(),
    itemType: monitor.getItemType(),
  }));

  const [{ isOver, canDrop }, drop] = useDrop<DragItem, DropResult, { isOver: boolean; canDrop: boolean }>(
    () => ({
      accept: DRAG_TYPE_TASK,
      drop: () => ({ columnId: "trash", index: -1, dropType: "trash" }),
      collect: (monitor) => ({
        isOver: monitor.isOver(),
        canDrop: monitor.canDrop(),
      }),
    }),
    []
  );

  if (!isDragging || itemType !== DRAG_TYPE_TASK) {
    return null;
  }

  const isActive = isOver && canDrop;

  return (
    <div className="fixed bottom-6 left-1/2 z-40 -translate-x-1/2">
      <div
        ref={drop}
        className={clsx(
          "flex items-center gap-3 rounded-2xl border-2 border-dashed px-5 py-4 shadow-xl backdrop-blur transition",
          isActive
            ? "border-rose-400/80 bg-rose-50 text-rose-700 dark:border-rose-500/70 dark:bg-rose-500/20 dark:text-rose-100"
            : "border-gray-200 bg-white/90 text-gray-600 dark:border-gray-700 dark:bg-gray-900/80 dark:text-gray-200",
          isDeleting && "ring-2 ring-rose-300/60 dark:ring-rose-600/60"
        )}
      >
        <div
          className={clsx(
            "flex h-12 w-12 items-center justify-center rounded-xl border-2 text-xl font-semibold transition",
            isActive
              ? "border-rose-300 bg-rose-100 text-rose-700 dark:border-rose-500/80 dark:bg-rose-500/30 dark:text-rose-50"
              : "border-gray-200 bg-gray-50 text-gray-500 dark:border-gray-600 dark:bg-gray-800"
          )}
        >
          {isDeleting ? (
            <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth={2.4} strokeOpacity={0.2} />
              <path d="M21 12a9 9 0 00-9-9" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" />
            </svg>
          ) : (
            <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M9 5h6m-7 3h8" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" />
              <path d="M10 10v6m4-6v6" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" />
              <path d="M5 8h14l-1 12H6L5 8Zm4-3.5a1.5 1.5 0 0 1 1.5-1.5h3a1.5 1.5 0 0 1 1.5 1.5V8h-6V4.5Z" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          )}
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-semibold">Delete task</span>
          <span className="text-xs text-gray-400 dark:text-gray-500">Drop here to remove</span>
        </div>
      </div>
    </div>
  );
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
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(trimmed)) return null;
  const parsed = new Date(trimmed);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
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

const STATUS_COLUMN_KEYWORDS: Record<string, string[]> = {
  "0": ["backlog", "todo", "uncategorized", "icebox"],
  "5": ["hold", "paused", "waiting"],
  "30": ["progress", "inprogress", "doing", "in-process"],
  review: ["review", "qa", "verify", "quality"],
  "100": ["complete", "done", "completed"],
  "101": ["cancel", "canceled", "closed"],
};

const normalizeKey = (label: string) => label.trim().toLowerCase().replace(/[^a-z0-9]+/g, "");

const pickColumnForStatus = (
  statusValue: string,
  columns: Array<{ id: string; title: string }>,
  fallback: string
): string => {
  const keywords = STATUS_COLUMN_KEYWORDS[statusValue];
  if (!keywords?.length) {
    return fallback;
  }

  const normalizedColumns = columns.map((column) => ({
    id: column.id,
    titleKey: normalizeKey(column.title),
    idKey: normalizeKey(column.id.replace(/^column-/, "")),
  }));

  for (const keyword of keywords) {
    const key = normalizeKey(keyword);
    const match = normalizedColumns.find((column) => column.titleKey === key || column.idKey === key);
    if (match) {
      return match.id;
    }
  }

  return fallback;
};
















/* WC3 strict date implementation */
const updateTaskFormState = (
  prev: TaskFormState,
  field: TaskFormEditableField,
  value: TaskFormFieldValue,
  options?: { columns?: Array<{ id: string; title: string }>; fallbackColumnId?: string }
): TaskFormState => {
  if (field === "dt_start") {
    const next: TaskFormState = { ...prev, dt_start: value };

    // If dt_deadline exists and is earlier than new dt_start, shift dt_deadline up to dt_start
    if (value && prev.dt_deadline) {
      const start = parseDateTimeInputValue(value);
      const due = parseDateTimeInputValue(prev.dt_deadline);
      if (start && due && due.getTime() < start.getTime()) {
        next.dt_deadline = value;
      }
    }

    return next;
  }

  if (field === "dt_completed") {
    const next: TaskFormState = { ...prev, dt_completed: value };
    if (value) {
      if (!prev.dt_start) next.dt_start = value;
      if (!prev.dt_deadline) next.dt_deadline = value;
      const startDate = parseDateTimeInputValue(next.dt_start);
      const compDate = parseDateTimeInputValue(value);
      if (startDate && compDate && compDate.getTime() < startDate.getTime()) {
        next.dt_completed = formatDateTimeLocalString(startDate);
      }
    }
    return next;
  }

  if (field === "dt_deadline") {
    if (!value) {
      return { ...prev, dt_deadline: calculateDueDate(prev.dt_start, prev.dt_completed) };
    }

    const parsedDue = parseDateTimeInputValue(value);
    if (!parsedDue) {
      return prev;
    }

    const endDate = parseDateTimeInputValue(prev.dt_completed);
    if (endDate && parsedDue.getTime() < endDate.getTime()) {
      return { ...prev, dt_deadline: formatDateTimeLocalString(endDate) };
    }

    const startDate = parseDateTimeInputValue(prev.dt_start);
    if (!endDate && startDate && parsedDue.getTime() < startDate.getTime()) {
      return { ...prev, dt_deadline: formatDateTimeLocalString(startDate) };
    }

    return { ...prev, dt_deadline: formatDateTimeLocalString(parsedDue) };
  }

  if (field === "priority") {
    return { ...prev, priority: value as TaskPriority };
  }

  if (field === "columnId") {
    return { ...prev, columnId: value };
  }

  if (field === "projectId") {
    return { ...prev, projectId: value };
  }

  if (field === "assigned_to") {
    return { ...prev, assigned_to: value };
  }

  if (field === "difficulty") {
    return { ...prev, difficulty: value };
  }

  if (field === "is_active") {
    return { ...prev, is_active: value };
  }

  if (field === "percent_complete") {
    const next: TaskFormState = { ...prev, percent_complete: value };
    const numericProgress = Number(value);
    if (Number.isFinite(numericProgress)) {
      // Derive status for column selection
      let derivedStatus: string | null = null;
      if (numericProgress >= 100) {
        derivedStatus = "100";
      } else if (numericProgress >= 70) {
        derivedStatus = "review";
      } else if (numericProgress <= 0) {
        derivedStatus = "0";
      } else if (numericProgress <= 5) {
        derivedStatus = "5";
      } else {
        derivedStatus = "30";
      }

      if (options?.columns?.length && options.fallbackColumnId) {
        next.columnId = pickColumnForStatus(derivedStatus, options.columns, options.fallbackColumnId);
      }

      if (numericProgress >= 100 && !prev.dt_completed) {
        const now = formatDateTimeLocalString(new Date());
        next.dt_completed = ensureEndAfterStart(prev.dt_start, now);
      }
    }
    return next;
  }

  if (field === "attachments") {
    return { ...prev, attachments: value as TaskAttachment[] };
  }

  return prev;
};




















const KanbanBoardPage: React.FC = () => {
  const [board, setBoard] = useState<BoardData>(() => createEmptyBoardData());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [columnsPerRow, setColumnsPerRow] = useState<number>(4);

  const [searchParams] = useSearchParams();
  const [projectOptions, setProjectOptions] = useState<ProjectOption[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(
    () => searchParams.get("project") || ""
  );
  const [isLoadingProjects, setIsLoadingProjects] = useState<boolean>(true);
  const [projectFetchError, setProjectFetchError] = useState<string | null>(null);
  const selectedProject = useMemo(
    () => projectOptions.find((option) => option.id === selectedProjectId),
    [projectOptions, selectedProjectId]
  );
  const selectedProjectName = selectedProject?.name ?? selectedProject?.intent ?? "";

  useEffect(() => {
    console.log("selectedProjectId changed:", selectedProjectId, "projectOptions:", projectOptions.length);
  }, [selectedProjectId, projectOptions.length]);

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
  const [floatingActionId, setFloatingActionId] = useState<string | null>(null);

  // Contact Manager Modal state
  const [isContactManagerOpen, setIsContactManagerOpen] = useState(false);

  // Auto-refresh state
  const [lastRefreshTime, setLastRefreshTime] = useState<Date | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const autoRefreshIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Generate Projects dialog state
  const [isGenerateOpen, setIsGenerateOpen] = useState(false);

  // Track if any modal is open to pause auto-refresh
  const isAnyModalOpen = isCreateModalOpen || isEditModalOpen || isContactManagerOpen || isGenerateOpen || !!floatingActionId;

  const [createTaskState, setCreateTaskState] = useState<TaskFormState>(() => createInitialTaskFormState(FALLBACK_COLUMN_ID));
  const [editTaskState, setEditTaskState] = useState<TaskFormState>(() => createInitialTaskFormState(FALLBACK_COLUMN_ID));

  const [isSavingCreate, setIsSavingCreate] = useState<boolean>(false);
  const [isSavingEdit, setIsSavingEdit] = useState<boolean>(false);
  const [generateCount, setGenerateCount] = useState(1);
  const [generateName, setGenerateName] = useState("");
  const [generateCategory, setGenerateCategory] = useState("kanban");
  const [generateStartDate, setGenerateStartDate] = useState(() => {
    const d = new Date(); d.setDate(d.getDate() + 1);
    return d.toISOString().slice(0, 10);
  });
  const [generateEndDate, setGenerateEndDate] = useState(() => {
    const d = new Date(); d.setDate(d.getDate() + 8);
    return d.toISOString().slice(0, 10);
  });
  const [generateInterval, setGenerateInterval] = useState(7);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateResult, setGenerateResult] = useState<string | null>(null);

  const generatedProjectName = [generateCategory, generateName, generateStartDate].filter(Boolean).join("-");

  const handleGenerateProjects = useCallback(async () => {
    setIsGenerating(true);
    setGenerateResult(null);
    try {
      const result = await manageAction("generate_kanban_projects", {
        count: generateCount,
        name: generateName,
        category: generateCategory,
        start_date: generateStartDate,
        end_date: generateEndDate,
        interval_days: generateInterval,
      });
      setGenerateResult(`Created ${result.created} project(s)`);
      setTimeout(() => {
        setIsGenerateOpen(false);
        setGenerateResult(null);
      }, 1500);
    } catch (err: any) {
      const msg = err?.response?.data?.message || err?.message || "Failed to generate projects";
      setGenerateResult(`Error: ${msg}`);
    } finally {
      setIsGenerating(false);
    }
  }, [generateCount, generateName, generateCategory, generateStartDate, generateEndDate, generateInterval]);
  const [isRemovingTask, setIsRemovingTask] = useState<boolean>(false);
  const [isTrashDeleting, setIsTrashDeleting] = useState<boolean>(false);
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

  const loadPersistedActionAttachments = useCallback(async (actionId: string | number, hashes: string[]): Promise<TaskAttachment[]> => {
    if (!Array.isArray(hashes) || !hashes.length) {
      return [];
    }

    try {
      const hashSet = new Set(hashes);
      const docsByChecksum = new Map<string, Record<string, unknown>>();
      const targetActionId = String(actionId);

      const scoreDocForAction = (doc: Record<string, unknown>): number => {
        let score = 0;
        const modelName = typeof doc.model_name === "string" ? doc.model_name.toLowerCase() : "";
        if (modelName === "action") {
          score += 3;
        }
        const dataObj = parseMaybeObject(doc.data);
        const parentId = dataObj?.parent_id;
        if (String(parentId ?? "") === targetActionId) {
          score += 5;
        }
        const pathObj = parseMaybeObject(doc.path);
        const storage = typeof pathObj?.storage === "string" ? pathObj.storage.toLowerCase() : "";
        if (storage === "inline") {
          score += 3;
        }
        const url = typeof pathObj?.url === "string" ? pathObj.url : "";
        if (url.startsWith("/wcapi/document/")) {
          score += 2;
        } else if (url.startsWith("/static/")) {
          score += 1;
        }
        if (doc.is_deleted === true) {
          score -= 4;
        }
        if (doc.is_active === false) {
          score -= 2;
        }
        return score;
      };

      const pageSize = 500;
      let offset = 0;
      let hasMore = true;
      let guard = 0;

      while (hasMore && docsByChecksum.size < hashSet.size && guard < 50) {
        const pageResponse = await getRecords("document", { limit: pageSize, offset });
        const pageRecords = extractRecordArray(pageResponse);
        if (!pageRecords.length) {
          break;
        }

        for (const doc of pageRecords) {
          const checksum = typeof doc.checksum === "string" ? doc.checksum.trim() : "";
          if (!checksum || !hashSet.has(checksum)) {
            continue;
          }

          const current = docsByChecksum.get(checksum);
          if (!current || scoreDocForAction(doc) > scoreDocForAction(current)) {
            docsByChecksum.set(checksum, doc);
          }
        }

        hasMore = pageRecords.length >= pageSize;
        offset += pageRecords.length;
        guard += 1;
      }

      return hashes
        .map((hash, index) => {
          const doc = docsByChecksum.get(hash);
          if (!doc) {
            return null;
          }
          return mapDocumentRecordToAttachment(doc, index);
        })
        .filter((entry): entry is TaskAttachment => !!entry);
    } catch {
      return [];
    }
  }, []);

  const persistActionAttachmentHashes = useCallback(async (actionId: number, hashes: string[]) => {
    if (!Number.isFinite(actionId) || actionId <= 0) {
      return;
    }

    await patchAction({
      model_name: "action",
      id: actionId,
      "refs.attachments_sha256": {
        mode: "update",
        value: hashes,
      },
    });
  }, []);

  const collectActionDocumentChecksums = useCallback(async (actionId: number): Promise<string[]> => {
    if (!Number.isFinite(actionId) || actionId <= 0) {
      return [];
    }

    try {
      const pageSize = 500;
      let offset = 0;
      let hasMore = true;
      let guard = 0;
      const checksums = new Set<string>();

      while (hasMore && guard < 50) {
        const pageResponse = await getRecords("document", { limit: pageSize, offset });
        const pageRecords = extractRecordArray(pageResponse);
        if (!pageRecords.length) {
          break;
        }

        for (const doc of pageRecords) {
          const modelName = typeof doc.model_name === "string" ? doc.model_name.toLowerCase() : "";
          if (modelName && modelName !== "action") {
            continue;
          }
          const dataObj = parseMaybeObject(doc.data);
          const parentId = Number(dataObj?.parent_id);
          if (!Number.isFinite(parentId) || parentId !== actionId) {
            continue;
          }
          const checksum = typeof doc.checksum === "string" ? doc.checksum.trim() : "";
          if (checksum) {
            checksums.add(checksum);
          }
        }

        hasMore = pageRecords.length >= pageSize;
        offset += pageRecords.length;
        guard += 1;
      }

      return Array.from(checksums);
    } catch {
      return [];
    }
  }, []);

  //const navigate = useNavigate();

  const resolveDefaultColumnId = useCallback(
    () => board.column_order[0] ?? FALLBACK_COLUMN_ID,
    [board.column_order]
  );

  const persistTaskReorder = useCallback(
    async (
      previousBoard: BoardData,
      nextBoard: BoardData,
      item: DragItem,
      dropResult: DropResult | null
    ) => {
      if (!dropResult) {
        return;
      }

      const destinationColumn = nextBoard.columns[dropResult.columnId];
      if (!destinationColumn) return;

      const destinationTaskIds = destinationColumn.task_ids;
      const targetIndex = dropResult.index;
      const prevTaskId = destinationTaskIds[targetIndex - 1];
      const nextTaskId = destinationTaskIds[targetIndex + 1];

      const prevSeq = prevTaskId ? nextBoard.tasks[prevTaskId]?.sequence : undefined;
      const nextSeq = nextTaskId ? nextBoard.tasks[nextTaskId]?.sequence : undefined;

      const BASE_SPACING = 1000;
      const clampSequence = (value: number) => Math.max(1, Math.round(value));

      let newSequence: number;
      if (typeof prevSeq === "number" && typeof nextSeq === "number" && nextSeq > prevSeq + 1) {
        // There is room between neighbors; pick a midpoint integer.
        newSequence = clampSequence(prevSeq + Math.floor((nextSeq - prevSeq) / 2));
      } else if (typeof prevSeq === "number" && typeof nextSeq !== "number") {
        // Append to the end of the column with padded spacing.
        newSequence = clampSequence(prevSeq + BASE_SPACING);
      } else if (typeof prevSeq !== "number" && typeof nextSeq === "number") {
        // Insert at the start; keep spacing before the next item.
        newSequence = clampSequence(Math.max(nextSeq - BASE_SPACING, BASE_SPACING));
      } else {
        // Either no neighbors or neighbors are colliding; fall back to index-based spacing.
        newSequence = clampSequence((targetIndex + 1) * BASE_SPACING);
      }

      const targetTask = nextBoard.tasks[item.taskId];
      if (!targetTask?.id) return;

      // Build complete payload with all necessary fields
      const entry: Record<string, unknown> = {
        model_name: "action",
        id: targetTask.id,
        kanban_column: destinationColumn.title,
        kanban_column_id: destinationColumn.id,
        sequence: newSequence,
        order: newSequence,
        position: newSequence,
      };

      // Include action titles to ensure backend has them
      if (targetTask.title) {
        entry.action_en = targetTask.title;
      }

      // Include translations if available
      if (targetTask.title_translations) {
        Object.entries(targetTask.title_translations).forEach(([lang, text]) => {
          if (text) {
            entry[`action_${lang}`] = text;
          }
        });
      }

      if (selectedProjectName) {
        entry.project_name = selectedProjectName;
      }

      if (selectedProjectId) {
        const numericId = Number(selectedProjectId);
        entry.project_id = Number.isNaN(numericId) ? selectedProjectId : numericId;
      }

      console.log("Dragging task - payload:", entry);

      try {
        const response = await patchAction(entry);
        console.log("Drag persist response:", response);
      } catch (error) {
        console.error("Failed to persist kanban reorder", error);
        console.error("Error details:", error);
      }
    },
    [selectedProjectName, selectedProjectId]
  );

  const removeTaskInBackend = useCallback(async (taskId: string | number) => {
    const parsedId = typeof taskId === "number" ? taskId : Number(taskId);
    const payloadId = Number.isNaN(parsedId) ? taskId : parsedId;

    try {
      const response = await patchAction({
        model_name: "action",
        id: payloadId,
        is_deleted: { mode: "update", value: true },
        is_active: { mode: "update", value: false },
        status: { mode: "update", value: "Removed" },
        kanban_column: { mode: "update", value: "Removed" },
        kanban_column_id: { mode: "update", value: "column-removed" },
      });

      const body: any = (response as any)?.data ?? response;
      if ((response as any)?.status !== 200 && (response as any)?.status !== 201) {
        throw new Error("Failed to remove task.");
      }
      if (body?.status === "fail") {
        const details = Array.isArray(body?.error?.details) ? body.error.details.join("; ") : body?.message;
        throw new Error(details || "Backend rejected the remove request.");
      }

      return { success: true } as const;
    } catch (error) {
      console.error("Failed to remove kanban task", error);
      const message =
        (error as any)?.response?.data?.message ||
        (error as any)?.message ||
        "Unable to remove task. Please try again.";
      return { success: false, error: message } as const;
    }
  }, []);

  const handleDragEnd = useCallback(
    (item: DragItem, dropResult: DropResult | null) => {
      if (item.type !== DRAG_TYPE_TASK) {
        return;
      }

      if (dropResult?.dropType === "trash") {
        setBoard((prev) => removeTaskFromBoardState(prev, item.taskId));
        setIsTrashDeleting(true);
        void removeTaskInBackend(item.taskId).then((result) => {
          if (!result.success) {
            setFetchError((current) => current ?? result.error ?? null);
          }
        }).finally(() => {
          setIsTrashDeleting(false);
        });
        return;
      }

      setBoard((prev) => {
        const next = handleBoardMove(prev, { item, result: dropResult });
        if (next !== prev) {
          void persistTaskReorder(prev, next, item, dropResult);
        }
        return next;
      });
    },
    [persistTaskReorder, removeTaskInBackend]
  );

  const fetchProjects = useCallback(async () => {
    setIsLoadingProjects(true);
    setProjectFetchError(null);
    try {
      const response = await getRecords("project", {
        is_active: true,
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
          console.log("fetchProjects: keeping previous selectedProjectId:", previous);
          return previous;
        }
        // Try to find a sensible default project based on naming convention
        const defaultId = findDefaultProjectId(nextOptions);
        console.log("fetchProjects: previous selection not kept, defaultId:", defaultId);
        return defaultId ?? "";
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
      const params: Record<string, string | number> = {};
      if (projectId) {
        // Prefer numeric project_id when possible (backend expects numeric IDs)
        const numericId = Number(projectId);
        if (!Number.isNaN(numericId) && String(numericId) === String(projectId)) {
          params.project_id = numericId;
        } else {
          // If non-numeric (slug/uuid), also provide project_slug to increase match chance
          params.project_id = projectId;
          params.project_slug = projectId;
        }
      }
      if (contactId) {
        // Use contact_id field which is indexed on the Action model
        params.contact_id = contactId;
      }

      console.log("fetchActions - params:", params);
      const response = await Actions(Object.keys(params).length ? params : undefined);
      console.log("fetchActions - raw response:", response);
      if (!response || response.status !== 200) {
        throw new Error("Request failed");
      }

      let items = extractKanbanItems(response);
      console.log("fetchActions - items count:", Array.isArray(items) ? items.length : 0);
      items = items.filter((item: any) => String(item.status).toLowerCase() !== "on hold");

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
    if (isLoadingProjects) return;
    if (selectedProjectId && selectedProject) {
      updateContactsFromProject(selectedProject);
    } else {
      // "All projects" selected or project not yet resolved — fetch all contacts
      void fetchAllContacts();
    }
  }, [isLoadingProjects, selectedProjectId, selectedProject, updateContactsFromProject, fetchAllContacts]);

  useEffect(() => {
    // Avoid fetching actions until project list has been loaded to prevent
    // an initial unfiltered request returning all projects' actions.
    if (isLoadingProjects) return;

    void fetchActions({
      projectId: selectedProjectId || undefined,
      contactId: selectedContactId || undefined,
    });
    setLastRefreshTime(new Date());
  }, [fetchActions, isLoadingProjects, selectedProjectId, selectedContactId]);

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
    if (board.column_order.length === 0) {
      return;
    }
    // Keep columnsPerRow at 4 by default, don't clamp based on available columns
    // This ensures the grid always shows 4 columns per row
  }, [board.column_order]);

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
      board.column_order
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
    () => extendNumericOptionStrings(PROGRESS_OPTIONS, createTaskState.percent_complete),
    [createTaskState.percent_complete]
  );

  const editDifficultyOptions = useMemo(
    () => extendNumericOptionStrings(DIFFICULTY_OPTIONS, editTaskState.difficulty),
    [editTaskState.difficulty]
  );

  const editProgressOptions = useMemo(
    () => extendNumericOptionStrings(PROGRESS_OPTIONS, editTaskState.percent_complete),
    [editTaskState.percent_complete]
  );

  const languageOptions = useMemo(() => {
    const codes = new Set<string>(DEFAULT_LANGUAGE_ORDER);
    Object.values(board.tasks).forEach((task) => {
      task.language_codes?.forEach((code: string) => codes.add(normalizeLanguageCode(code)));
      Object.keys(task.title_translations ?? {}).forEach((code: string) => codes.add(normalizeLanguageCode(code)));
      Object.keys(task.description_translations ?? {}).forEach((code: string) => codes.add(normalizeLanguageCode(code)));
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
    setCreateTaskState((prev) => {
      const base = createInitialTaskFormState(firstColumn);
      return { ...base, projectId: selectedProjectId || base.projectId };
    });
    setCreateModalError(null);
    setCreateLanguagePickerOpen(false);
    setCreateLanguageSelection("");
    setCreateCustomLanguage("");
    setCreateLanguagePickerError(null);
  }, [resolveDefaultColumnId, selectedProjectId]);

  const handleOpenCreateModal = () => {
    resetCreateState();
    setIsCreateModalOpen(true);
  };

  const handleNewActionFloating = useCallback(async () => {
    try {
      const result = await saveRecord("action", {
        model_name: "action",
        action: { en: "" },
        status: "open",
        priority: 2,
        project_id: selectedProjectId || undefined,
      });
      const newId = result?.id || result?.record?.id;
      if (newId) setFloatingActionId(String(newId));
    } catch {}
  }, [selectedProjectId]);

  const handleCloseCreateModal = () => {
    setIsCreateModalOpen(false);
    resetCreateState();
  };

  const handleOpenEditModal = (task: KanbanTask) => {
    setEditingTask(task);

    const taskColumn = Object.values(board.columns).find((column) => column.task_ids.includes(task.id));

    const normalizedStart = normalizeIncomingDateValue(task.dt_start);
    const normalizedEnd = normalizeIncomingDateValue(task.dt_completed);
    const normalizedDue = normalizeIncomingDateValue(task.dt_deadline);
    const normalizedDifficulty = normalizeNumericSelectValue(
      task.difficulty ?? PRIORITY_TO_VALUE[task.priority],
      DEFAULT_DIFFICULTY
    );
    const normalizedProgress = normalizeNumericSelectValue(task.percent_complete ?? 0, DEFAULT_PROGRESS);
    const normalizedProjectId = task.project_id ?? selectedProjectId ?? "";
    const normalizedIsActive = task.is_active;

    const refsHashes = extractTaskAttachmentHashes(task);

    const taskAttachments: TaskAttachment[] = (task.attachments || []).map(att => ({
      id: `existing-${att.id}`,
      documentId: att.id,
      type: att.mime_type,
      name: att.name,
      size: att.size_bytes,
      previewUrl: att.url,
    }));

    setEditTaskState({
      translations: createTranslationEntriesFromTask(task),
      columnId: taskColumn?.id || resolveDefaultColumnId(),
      projectId: typeof normalizedProjectId === "string" || typeof normalizedProjectId === "number" ? String(normalizedProjectId) : "",
      priority: task.priority,
      dt_deadline: normalizedDue || calculateDueDate(normalizedStart, normalizedEnd),
      dt_start: normalizedStart,
      dt_completed: normalizedEnd,
      dt_expected: normalizeIncomingDateValue(task.dt_expected),
      assigned_to: Array.isArray(task.assigned_to) ? task.assigned_to.map(a => ({ id: a.id, name: a.name || a.id })) : [],
      difficulty: normalizedDifficulty,
      percent_complete: String(normalizedProgress),
      is_active: typeof normalizedIsActive === "boolean" ? String(normalizedIsActive) : "true",
      attachments: [],
      //attachments: taskAttachments,
    });
    setEditModalError(null);
    setEditLanguagePickerOpen(false);
    setEditLanguageSelection("");
    setEditCustomLanguage("");
    setEditLanguagePickerError(null);

    setIsEditModalOpen(true);

    void loadPersistedActionAttachments(task.id, refsHashes).then((persisted) => {
      if (!persisted.length) {
        return;
      }
      setEditTaskState((prev) => ({
        ...prev,
        attachments: mergeAttachmentsByDocumentId(prev.attachments || [], persisted),
      }));
    });
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

  const handleCreateTaskChange = (field: TaskFormEditableField, value: TaskFormFieldValue) => {
    setCreateTaskState((prev) =>
      updateTaskFormState(prev, field, value, {
        columns: columnOptions,
        fallbackColumnId: resolveDefaultColumnId(),
      })
    );
  };

  const handleEditTaskChange = (field: TaskFormEditableField, value: TaskFormFieldValue) => {
    setEditTaskState((prev) =>
      updateTaskFormState(prev, field, value, {
        columns: columnOptions,
        fallbackColumnId: resolveDefaultColumnId(),
      })
    );
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

  const cleanActionPayload = (payload: Record<string, unknown>): Record<string, unknown> => {
    const mutable = payload as Record<string, unknown>;

    if ("action_id" in mutable) {
      const value = mutable.action_id as unknown;
      if (value === "" || value === null || value === undefined) {
        delete mutable.action_id;
      }
    }

    if ("description_id" in mutable) {
      const value = mutable.description_id as unknown;
      if (value === "") {
        delete mutable.description_id;
      }
    }

    return mutable;
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

    const effectiveTranslations = new Map(
      Array.from(normalized.entries()).filter(
        ([, value]) => value.title.length > 0 || value.description.length > 0
      )
    );

    const hasTitle = Array.from(effectiveTranslations.values()).some(
      (value) => value.title.length > 0
    );
    if (!hasTitle) {
      return { error: "Add at least one language with a title." };
    }

    const translationFields: Record<string, string> = {};
    effectiveTranslations.forEach((value, language) => {
      if (value.title) {
        translationFields[`action_${language}`] = value.title;
      }
      if (value.description) {
        translationFields[`description_${language}`] = value.description;
      }
    });

    const languages = Array.from(effectiveTranslations.keys());
    const actionPayload: Record<string, string> = {};
    const descriptionPayload: Record<string, string> = {};
    effectiveTranslations.forEach((value, language) => {
      if (value.title) {
        actionPayload[language] = value.title;
      }
      if (value.description) {
        descriptionPayload[language] = value.description;
      }
    });

    const removalTokens: string[] = [];
    if (mode === "edit" && baseTask) {
      const originalLanguages = new Set<string>();
      baseTask.language_codes?.forEach((code: string) => {
        if (typeof code === "string") {
          originalLanguages.add(normalizeLanguageCode(code));
        }
      });
      Object.keys(baseTask.title_translations ?? {}).forEach((code: string) => originalLanguages.add(normalizeLanguageCode(code)));
      Object.keys(baseTask.description_translations ?? {}).forEach((code: string) =>
        originalLanguages.add(normalizeLanguageCode(code))
      );

      originalLanguages.forEach((language) => {
        if (language && !effectiveTranslations.has(language)) {
          removalTokens.push(`action_${language}`);
          removalTokens.push(`description_${language}`);
        }
      });
    }

    const column = board.columns[state.columnId] ?? board.columns[FALLBACK_COLUMN_ID];
    const columnTitle = column?.title ?? "Uncategorized";
    const assignedTo = Array.isArray(state.assigned_to) ? state.assigned_to : [];

    let startTimestamp = toTimestampMilliseconds(state.dt_start);
    let dueTimestamp = toTimestampMilliseconds(state.dt_deadline);
    let completedTimestamp = toTimestampMilliseconds(state.dt_completed);

    // WC3 minimal ordering: dt_start <= dt_deadline <= dt_completed
    if (startTimestamp && dueTimestamp && dueTimestamp < startTimestamp) {
      dueTimestamp = startTimestamp;
    }
    if (dueTimestamp && completedTimestamp && completedTimestamp < dueTimestamp) {
      completedTimestamp = dueTimestamp;
    }


    const fallbackDifficulty = baseTask?.difficulty ?? PRIORITY_TO_VALUE[state.priority];
    const parsedDifficulty = Number(state.difficulty);
    const resolvedDifficulty = Number.isNaN(parsedDifficulty) || parsedDifficulty <= 0 ? fallbackDifficulty : parsedDifficulty;

    const fallbackProgress = baseTask?.percent_complete ?? 0;
    const parsedProgress = Number(state.percent_complete);
    const resolvedProgress = clampPercentageValue(
      Number.isNaN(parsedProgress) || parsedProgress < 0 ? fallbackProgress : parsedProgress
    );
    const resolvedBurndown = clampPercentageValue(
      mode === "edit" && baseTask ? baseTask.percent_complete ?? resolvedProgress : resolvedProgress
    );

    const payloadItem: Record<string, unknown> = {
      model_name: "action",
      ...translationFields,
      languages,
      needtoremove: removalTokens.join(","),
      ...(Object.keys(actionPayload).length ? { action: actionPayload } : {}),
      ...(Object.keys(descriptionPayload).length ? { description: descriptionPayload } : {}),
      kanban_column: columnTitle,
      kanban_column_id: column?.id ?? FALLBACK_COLUMN_ID,
      priority: PRIORITY_TO_VALUE[state.priority],
      difficulty: resolvedDifficulty,
      status: baseTask?.status ?? "In progress",
      dt_deadline: dueTimestamp ?? null,
      dt_start: startTimestamp ?? null,
      dt_completed: completedTimestamp ?? null,
      dt_expected: toTimestampMilliseconds(state.dt_expected) ?? null,
      percent_complete: resolvedProgress,
      // Backend drops numeric 0 via truthy checks; keep as string to satisfy NOT NULL constraint.
      burndown: serializeBurndownValue(resolvedBurndown),
    };

    if (mode === "edit" && baseTask) {
      payloadItem.id = baseTask.id;
    }

    if (assignedTo.length > 0) {
      payloadItem.assigned_to = assignedTo.map(a => ({ id: a.id, name: a.name }));
      // Optionally, set contact_id if only one selected
      if (assignedTo.length === 1 && assignedTo[0].id) {
        payloadItem.contact_id = assignedTo[0].id;
      }
    }

    if (!removalTokens.length) {
      payloadItem.needtoremove = "";
    }

    const projectIdFromState = state.projectId?.trim();
    const resolvedProjectId = projectIdFromState || selectedProjectId || "";
    const resolvedProjectName = (() => {
      const selected = projectOptions.find((option) => option.id === resolvedProjectId);
      if (selected?.name) return selected.name;
      if (selected?.intent) return selected.intent;
      if (selectedProjectName.trim()) return selectedProjectName.trim();
      if (mode === "edit" && baseTask?.project_name) return baseTask.project_name;
      return "";
    })();

    if (resolvedProjectName) {
      payloadItem.project_name = resolvedProjectName;
    }

    if (resolvedProjectId) {
      const numericId = Number(resolvedProjectId);
      payloadItem.project_id = Number.isNaN(numericId) ? resolvedProjectId : numericId;
    }

    // Provide project_slug when available to help backend resolve non-numeric identifiers
    try {
      const selectedOpt = projectOptions.find((o) => String(o.id) === String(resolvedProjectId));
      if (selectedOpt && selectedOpt.slug) {
        payloadItem.project_slug = selectedOpt.slug;
      } else if (resolvedProjectId && isNaN(Number(resolvedProjectId))) {
        // If the provided project id looks non-numeric, include it as a slug too
        payloadItem.project_slug = resolvedProjectId;
      }
    } catch (e) {
      // defensive - ignore
    }

    payloadItem.is_active = state.is_active !== "false";

    // Add attachments if present
    if (state.attachments && state.attachments.length > 0) {
      const documentIds = state.attachments
        .map(att => att.documentId)
        .filter(id => id !== undefined);
      if (documentIds.length > 0) {
        payloadItem.attachments = documentIds;
      }
    }

    // Backend doesn't process 'bulk' arrays - always send action directly
    return { payload: cleanActionPayload(payloadItem) };
  };

  const handleCreateTaskSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSavingCreate) {
      return;
    }

    setCreateModalError(null);
    setIsSavingCreate(true);

    void (async () => {
      try {
        const result = buildActionPayload("create", createTaskState);
        if ("error" in result) {
          setCreateModalError(result.error);
          return;
        }

        const response = await patchAction(result.payload);
        console.log("Create task response:", response);
        const body: any = (response as any)?.data ?? response;

        if (body?.status === "fail") {
          const details = Array.isArray(body?.error?.details) ? body.error.details.join("; ") : body?.message;
          setCreateModalError(details || "Backend rejected the save request.");
          return;
        }

        if (body?.bulk && Array.isArray(body.bulk)) {
          const failedItems = body.bulk.filter((item: any) => item?.status === "fail");
          if (failedItems.length > 0) {
            const errors = failedItems.map((item: any) =>
              Array.isArray(item?.error?.details) ? item.error.details.join("; ") : item?.message || "Unknown error"
            );
            throw new Error(errors.join("; "));
          }
        }

        const bulkCreatedId = Array.isArray(body?.bulk)
          ? body.bulk
            .map((entry: any) => entry?.data?.id ?? entry?.id ?? entry?.record?.id ?? entry?.data?.record?.id)
            .find((value: unknown) => Number.isFinite(Number(value)))
          : undefined;

        const createdIdCandidate =
          bulkCreatedId ??
          body?.data?.id ??
          body?.id ??
          body?.data?.record?.id ??
          body?.record?.id;
        const createdTaskId = Number(createdIdCandidate);

        const pendingUploads = (createTaskState.attachments || []).filter((attachment) => attachment.file instanceof File);
        const uploadedAttachments: TaskAttachment[] = [];

        if (pendingUploads.length && Number.isFinite(createdTaskId) && createdTaskId > 0) {
          for (const attachment of pendingUploads) {
            const uploaded = await uploadDocument(
              attachment.file as File,
              "action",
              createdTaskId,
              "attachment"
            );

            const uploadedDoc = (uploaded.document || {}) as Record<string, any>;

            uploadedAttachments.push({
              id: `doc-${uploaded.document_id}`,
              documentId: uploaded.document_id,
              name: (uploadedDoc.name as string) || uploaded.name || attachment.name,
              type: (uploadedDoc.mime_type as string) || uploaded.mime_type || attachment.type,
              size: (uploadedDoc.size_bytes as number) || uploaded.size_bytes || attachment.size,
              checksum: (uploadedDoc.checksum as string) || uploaded.checksum,
              url: uploaded.url,
              previewUrl:
                ((uploaded.mime_type || attachment.type || "") as string).startsWith("image/")
                  ? uploaded.url
                  : undefined,
            });
          }
        }

        if (Number.isFinite(createdTaskId) && createdTaskId > 0) {
          const hashes = Array.from(
            new Set([
              ...extractAttachmentChecksums(uploadedAttachments),
              ...(await collectActionDocumentChecksums(createdTaskId)),
            ])
          );
          await persistActionAttachmentHashes(createdTaskId, hashes);
        }

        handleCloseCreateModal();
        setTimeout(() => {
          void fetchActions({
            projectId: selectedProjectId || undefined,
            contactId: selectedContactId || undefined,
          });
        }, 300);
      } catch (error) {
        console.error("Failed to create kanban task", error);
        const message =
          (error as any)?.response?.data?.message ||
          (error as any)?.message ||
          "Failed to create task. Please try again.";
        setCreateModalError(message);
      } finally {
        setIsSavingCreate(false);
      }
    })();
  };

  const handleEditTaskSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editingTask || isSavingEdit) {
      return;
    }

    setEditModalError(null);
    setIsSavingEdit(true);

    void (async () => {
      try {
        const result = buildActionPayload("edit", editTaskState, editingTask);
        if ("error" in result) {
          setEditModalError(result.error);
          return;
        }

        try {
          console.debug("[Kanban] Edit payload:", result.payload);
        } catch {
          // ignore
        }

        await patchAction(result.payload);

        const pendingUploads = (editTaskState.attachments || []).filter((attachment) => attachment.file instanceof File);
        const uploadedAttachments: TaskAttachment[] = [];
        const editingTaskId = Number(editingTask.id);

        const previousHashes = extractTaskAttachmentHashes(editingTask);
        const currentPersistedHashes = new Set(extractAttachmentChecksums(editTaskState.attachments));
        const removedHashes = previousHashes.filter((hash) => !currentPersistedHashes.has(hash));

        if (removedHashes.length) {
          // Attachment removal is checksum-list based; avoid deleting shared document records.
        }

        if (pendingUploads.length && Number.isFinite(editingTaskId) && editingTaskId > 0) {
          for (const attachment of pendingUploads) {
            const uploaded = await uploadDocument(
              attachment.file as File,
              "action",
              editingTaskId,
              "attachment"
            );

            const uploadedDoc = (uploaded.document || {}) as Record<string, any>;

            uploadedAttachments.push({
              id: `doc-${uploaded.document_id}`,
              documentId: uploaded.document_id,
              name: (uploadedDoc.name as string) || uploaded.name || attachment.name,
              type: (uploadedDoc.mime_type as string) || uploaded.mime_type || attachment.type,
              size: (uploadedDoc.size_bytes as number) || uploaded.size_bytes || attachment.size,
              checksum: (uploadedDoc.checksum as string) || uploaded.checksum,
              url: uploaded.url,
              previewUrl:
                ((uploaded.mime_type || attachment.type || "") as string).startsWith("image/")
                  ? uploaded.url
                  : undefined,
            });
          }
        }

        if (Number.isFinite(editingTaskId) && editingTaskId > 0) {
          const finalHashes = Array.from(
            new Set([
              ...Array.from(currentPersistedHashes),
              ...extractAttachmentChecksums(uploadedAttachments),
            ])
          );
          await persistActionAttachmentHashes(editingTaskId, finalHashes);
        }

        await fetchActions({
          projectId: selectedProjectId || undefined,
          contactId: selectedContactId || undefined,
        });
      } catch (error) {
        console.error("Failed to update kanban task", error);
        const message =
          (error as any)?.response?.data?.message ||
          (error as any)?.message ||
          "Failed to update task. Please try again.";
        setEditModalError(message);

        try {
          console.error("Update error response body:", (error as any)?.response?.data ?? (error as any)?.response ?? null);
        } catch {
          // ignore
        }
      } finally {
        setIsSavingEdit(false);
      }
    })();
  };

  const handleRemoveTaskFromKanban = async () => {
    if (!editingTask || isSavingEdit || isRemovingTask) {
      return;
    }

    setEditModalError(null);
    try {
      setIsRemovingTask(true);
      const result = await removeTaskInBackend(editingTask.id);
      if (!result.success) {
        setEditModalError(result.error ?? "Unable to remove task. Please try again.");
        return;
      }

      await fetchActions({
        projectId: selectedProjectId || undefined,
        contactId: selectedContactId || undefined,
      });
      handleCloseEditModal();
    } finally {
      setIsRemovingTask(false);
    }
  };

  const gridStyle = useMemo<CSSProperties>(
    () => ({
      gridTemplateColumns: `repeat(${Math.max(1, columnsPerRow)}, minmax(0, 1fr))`,
    }),
    [columnsPerRow]
  );

  const editModalExtraContent = null;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-1 px-2 py-1" style={{ fontSize: 12, color: '#9cdcfe' }}>
        <Link to={PageRoutes.multiProjectGantt}
          style={{ padding: '4px 8px', border: '1px solid transparent', borderRadius: 4, background: 'transparent', fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap', color: '#9cdcfe', textDecoration: 'none' }}
        >📋 Multi-Project</Link>
          <select value={selectedProjectId} onChange={handleProjectFilterChange} disabled={isLoadingProjects}
            className="rounded border border-slate-200 bg-white px-1 py-0.5 text-[10px] text-slate-600 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300"
          >
            <option value="">{isLoadingProjects ? "Loading..." : "Project: All"}</option>
            {projectOptions.map((option) => (
              <option key={option.id} value={option.id}>{option.name ?? option.intent ?? option.id}</option>
            ))}
          </select>
          <select value={selectedContactId} onChange={handleContactFilterChange} disabled={isLoadingContacts}
            className="rounded border border-slate-200 bg-white px-1 py-0.5 text-[10px] text-slate-600 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300"
          >
            <option value="">{isLoadingContacts ? "Loading..." : "Contact: All"}</option>
            {contactOptions.map((option) => (
              <option key={option.id} value={option.id}>{option.label}</option>
            ))}
          </select>
          <select value={columnsPerRow} onChange={(event) => setColumnsPerRow(Number(event.target.value))}
            className="rounded border border-slate-200 bg-white px-1 py-0.5 text-[10px] text-slate-600 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300"
          >
            {columnDensityOptions.map((option) => (
              <option key={option} value={option}>Cols: {option}</option>
            ))}
          </select>
          <button onClick={() => setIsGenerateOpen(true)} title="Generate kanban project records"
            style={{ padding: '4px 8px', border: '1px solid transparent', borderRadius: 4, background: 'transparent', cursor: 'pointer', fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap', color: '#9cdcfe' }}
          >📦 Gen Projects</button>
          <button onClick={() => void handleNewActionFloating()}
            style={{ padding: '4px 8px', border: '1px solid transparent', borderRadius: 4, background: 'transparent', cursor: 'pointer', fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap', color: '#4ec98c' }}
          >+ New Action</button>
          <button onClick={() => void handleManualRefresh()} disabled={isRefreshing || isLoading}
            title={`Last refreshed: ${formatLastRefresh(lastRefreshTime)}. Auto-refresh every 5 minutes${isAnyModalOpen ? ' (paused while dialog open)' : ''}`}
            style={{ padding: '4px 8px', border: '1px solid transparent', borderRadius: 4, background: 'transparent', cursor: isRefreshing ? 'default' : 'pointer', opacity: isRefreshing ? 0.4 : 1, fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap', color: '#9cdcfe' }}
          >🔄 {isRefreshing ? "Refreshing..." : "Refresh"}</button>
          <span style={{ fontSize: 10, color: '#888' }} title="Auto-refresh every 5 minutes">
            {formatLastRefresh(lastRefreshTime)}
          </span>
      </div>

      {projectFetchError && (
        <div className="flex items-center justify-between rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700 dark:border-amber-800 dark:bg-amber-900/30 dark:text-amber-200">
          <span>{projectFetchError}</span>
          <button type="button" onClick={() => void fetchProjects()}
            style={{ padding: '4px 8px', border: '1px solid transparent', borderRadius: 4, background: 'transparent', cursor: 'pointer', fontSize: 12, fontWeight: 600, color: '#e8c870' }}
          >↩ Retry</button>
        </div>
      )}

      {fetchError && (
        <div className="flex items-center justify-between rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/30 dark:text-rose-200">
          <span>{fetchError}</span>
          <button type="button"
            onClick={() => void fetchActions({ projectId: selectedProjectId || undefined, contactId: selectedContactId || undefined })}
            style={{ padding: '4px 8px', border: '1px solid transparent', borderRadius: 4, background: 'transparent', cursor: 'pointer', fontSize: 12, fontWeight: 600, color: '#e05252' }}
          >↩ Retry</button>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {(Object.keys(prioritySummary) as TaskPriority[]).map((priority) => (
          <div key={priority} className={clsx("flex gap-2 items-center justify-between rounded-full px-3 py-1 text-xs font-semibold", priorityPalette[priority])}>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-800 dark:text-gray-400">{priority}</p>
            <div className="flex items-center gap-2">
              <span className="text-3xl font-semibold text-gray-900 dark:text-white">{prioritySummary[priority]}</span>
              <span className="text-xs font-medium text-gray-400">/ {totalTasks} tasks</span>
            </div>
          </div>
        ))}
      </div>

      <DndProvider backend={HTML5Backend}>
        <KanbanDragLayer tasks={board.tasks} />
        <TrashDropZone isDeleting={isTrashDeleting} />
        {isLoading ? (
          <div className="flex justify-center items-center h-[50vh] rounded-3xl border border-dashed border-gray-300 text-sm text-gray-400 dark:border-gray-700 dark:text-gray-500">
            <RippleLoader />
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
                tasks={column.task_ids.map((taskId) => board.tasks[taskId]).filter((task): task is KanbanTask => Boolean(task))}
                onDragEnd={handleDragEnd}
                onTaskClick={(task) => setFloatingActionId(String(task.id))}
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
        projectOptions={projectOptions}
        priorityOptions={priorityOptions}
        difficultyOptions={createDifficultyOptions}
        progressOptions={createProgressOptions}
        assigneeOptions={contactOptions}
        translations={createTaskState.translations}
        onTranslationFieldChange={(entryId, field, value) =>
          handleTranslationFieldChange("create", entryId, field as "language" | "title" | "description", value)
        }
        onRemoveTranslation={(entryId) => handleRemoveTranslation("create", entryId)}
        languagePickerOptions={availableCreateLanguages}
        languagePickerState={createLanguagePickerState}
        onLanguagePickerToggle={handleCreateLanguagePickerToggle}
        onLanguageSelectionChange={handleCreateLanguageSelectionChange}
        onLanguageCustomChange={handleCreateLanguageCustomChange}
        onLanguagePickerSubmit={handleCreateLanguagePickerSubmit}
        onLanguagePickerCancel={handleCreateLanguagePickerCancel}
      />

      {/* Action Detail floating window — same as Gantt */}
      {floatingActionId && (
        <ActionFloatingWindow
          key={floatingActionId}
          actionId={floatingActionId}
          onClose={() => setFloatingActionId(null)}
          onSaved={() => void fetchActions({ projectId: selectedProjectId || undefined, contactId: selectedContactId || undefined })}
        />
      )}

      {/* Contact Manager Modal */}
      <ProjectContactManager
        isOpen={isContactManagerOpen}
        onClose={() => setIsContactManagerOpen(false)}
        projectId={selectedProjectId}
        projectName={selectedProjectName}
        currentContacts={selectedProject?.contacts ?? []}
        onContactsUpdated={handleContactsUpdated}
      />

      {/* Generate Kanban Projects Modal */}
      {isGenerateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="mx-4 w-full max-w-md rounded-xl bg-white p-6 shadow-2xl dark:bg-gray-900">
            <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
              Generate Kanban Projects
            </h3>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Category</span>
                  <input
                    type="text"
                    value={generateCategory}
                    onChange={(e) => setGenerateCategory(e.target.value)}
                    placeholder="kanban"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Name</span>
                  <input
                    type="text"
                    value={generateName}
                    onChange={(e) => setGenerateName(e.target.value)}
                    placeholder="optional"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                  />
                </label>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Start date</span>
                  <input
                    type="date"
                    value={generateStartDate}
                    onChange={(e) => setGenerateStartDate(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">End date</span>
                  <input
                    type="date"
                    value={generateEndDate}
                    onChange={(e) => setGenerateEndDate(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                  />
                </label>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Number of projects</span>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={generateCount}
                    onChange={(e) => setGenerateCount(Math.max(1, Math.min(100, Number(e.target.value))))}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Interval (days)</span>
                  <input
                    type="number"
                    min={1}
                    max={365}
                    value={generateInterval}
                    onChange={(e) => setGenerateInterval(Math.max(1, Number(e.target.value)))}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                  />
                </label>
              </div>
              <div className="rounded-lg bg-gray-50 p-3 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                Will create <strong>{generateCount}</strong> project(s) named{" "}
                <code className="text-indigo-600 dark:text-indigo-400">{generatedProjectName}</code>,
                starting <strong>{generateStartDate}</strong>, every <strong>{generateInterval}</strong> day(s).
              </div>
              {generateResult && (
                <div className={clsx(
                  "rounded-lg p-3 text-sm font-medium",
                  generateResult.startsWith("Error")
                    ? "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"
                    : "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400",
                )}>
                  {generateResult}
                </div>
              )}
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => { setIsGenerateOpen(false); setGenerateResult(null); }}
                disabled={isGenerating}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void handleGenerateProjects()}
                disabled={isGenerating || !generateStartDate}
                className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-amber-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isGenerating ? "Generating..." : "Generate"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default withDevIdentifier(KanbanBoardPage, 'KanbanBoardPage', 'rose', 'apps/utils/kanban/KanbanBoardPage.tsx');
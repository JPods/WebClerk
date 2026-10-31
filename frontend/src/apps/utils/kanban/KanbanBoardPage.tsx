/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { CSSProperties, ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import { DndProvider, useDragLayer, useDrop } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { KanbanColumn } from "./KanbanColumn";
import { KanbanDragLayer } from "./KanbanDragLayer";
import { ActionFloatingWindow } from "../../core/models/action/pages/ActionFloatingWindow";
import { ProjectContactManager } from "./ProjectContactManager";
import type { DragItem, DropResult } from "./dndTypes";
import { DRAG_TYPE_TASK } from "./dndTypes";
import type { BoardData, KanbanColumn as KanbanColumnType, KanbanTask, TaskPriority } from "./type/kanban";
import { getRecords, manageAction, saveRecord, createRecord, refusedFrom } from "@/api/wcapi";
import { createBoardDataFromApi, createEmptyBoardData, extractKanbanItems } from "./kanbanDataMapper";
import { Link, useSearchParams } from "react-router";
import { PageRoutes } from "../../../routes/Routes";
import LoadingSpinner from "@/components/common/LoadingSpinner";
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import { formatDt } from '@/utils/fieldFormatters';

const priorityPalette: Record<TaskPriority, string> = {
  low: "bg-emerald-500/10 text-emerald-600",
  medium: "bg-amber-500/10 text-amber-600",
  high: "bg-orange-500/10 text-orange-600",
  critical: "bg-rose-500/10 text-rose-600",
};




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
  dtKanban?: string | null;
  parent_id?: string | null;
  dt_start?: number | null;
  dt_end?: number | null;
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

  // Extract dt_kanban
  const dtKanbanRaw = record.dt_kanban ?? nestedProject?.dt_kanban;
  const dtKanban = typeof dtKanbanRaw === "string" && dtKanbanRaw ? dtKanbanRaw : null;

  // Extract parent_id, dt_start, dt_end for sprint hierarchy
  const parentIdRaw = record.parent_id ?? nestedProject?.parent_id;
  const parent_id = parentIdRaw != null ? String(parentIdRaw) : null;
  const dt_start = typeof record.dt_start === "number" ? record.dt_start : null;
  const dt_end = typeof record.dt_end === "number" ? record.dt_end : null;

  return {
    id: parsedId,
    slug,
    name: resolvedName,
    intent,
    contacts,
    dtKanban,
    parent_id,
    dt_start,
    dt_end,
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

// Choose default project id: the project whose dt_kanban is the earliest date >= today
const findDefaultProjectId = (projects: ProjectOption[]): string | undefined => {
  if (!projects || projects.length === 0) return undefined;
  const today = new Date();
  const todayUtc = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));

  let chosen: { id: string; date: Date } | undefined;
  for (const p of projects) {
    // Prefer dt_kanban, fall back to name-based parsing
    let d: Date | null = null;
    if (p.dtKanban) {
      const parsed = new Date(p.dtKanban);
      if (!Number.isNaN(parsed.getTime())) d = parsed;
    }
    if (!d) {
      const label = p.name ?? p.slug ?? p.id;
      d = parseProjectDateFromLabel(label);
    }
    if (!d) continue;
    const dUtc = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
    if (dUtc.getTime() < todayUtc.getTime()) continue;
    if (!chosen || dUtc.getTime() < chosen.date.getTime()) {
      chosen = { id: p.id, date: dUtc };
    }
  }

  return chosen?.id;
};

// ── Segmented Project Selector helpers ──

/** Get the Monday of the week containing a given date (UTC) */
const getWeekStart = (d: Date): Date => {
  const day = d.getUTCDay(); // 0=Sun
  const diff = day === 0 ? -6 : 1 - day;
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate() + diff));
};

interface ProjectSegments {
  permanent: ProjectOption[];
  thisWeek: ProjectOption[];
  next8: ProjectOption[];
  previous2: ProjectOption[];
  future: ProjectOption[];
  older: ProjectOption[];
}

const segmentProjects = (projects: ProjectOption[]): ProjectSegments => {
  const now = new Date();
  const thisWeekStart = getWeekStart(now);
  const WEEK = 7 * 86400000;
  const thisWeekEnd = new Date(thisWeekStart.getTime() + WEEK);
  const next8End = new Date(thisWeekEnd.getTime() + 8 * WEEK);
  const prev2Start = new Date(thisWeekStart.getTime() - 2 * WEEK);

  const segments: ProjectSegments = {
    permanent: [],
    thisWeek: [],
    next8: [],
    previous2: [],
    future: [],
    older: [],
  };

  for (const p of projects) {
    let d: Date | null = null;
    if (p.dtKanban) {
      const parsed = new Date(p.dtKanban);
      if (!Number.isNaN(parsed.getTime())) d = parsed;
    }
    if (!d) {
      const label = p.name ?? p.slug ?? p.id;
      d = parseProjectDateFromLabel(label);
    }
    if (!d) {
      segments.permanent.push(p);
      continue;
    }
    const t = d.getTime();
    if (t >= thisWeekStart.getTime() && t < thisWeekEnd.getTime()) {
      segments.thisWeek.push(p);
    } else if (t >= thisWeekEnd.getTime() && t < next8End.getTime()) {
      segments.next8.push(p);
    } else if (t >= prev2Start.getTime() && t < thisWeekStart.getTime()) {
      segments.previous2.push(p);
    } else if (t >= next8End.getTime()) {
      segments.future.push(p);
    } else {
      segments.older.push(p);
    }
  }

  const byDateDesc = (a: ProjectOption, b: ProjectOption) => {
    const da = a.dtKanban ? new Date(a.dtKanban).getTime() : 0;
    const db = b.dtKanban ? new Date(b.dtKanban).getTime() : 0;
    return db - da;
  };
  segments.thisWeek.sort(byDateDesc);
  segments.next8.sort(byDateDesc);
  segments.previous2.sort(byDateDesc);
  segments.future.sort(byDateDesc);
  segments.older.sort(byDateDesc);

  return segments;
};

interface OnDragEndArgs {
  item: DragItem;
  result: DropResult | null;
}

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

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
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
        ref={(el) => { drop(el); }}
        className={clsx(
          "flex items-center gap-3 rounded-2xl border-2 border-dashed px-5 py-4 shadow-xl backdrop-blur transition",
          isActive
            ? "border-rose-400/80 bg-rose-50 text-rose-700"
            : "",
          isDeleting && "ring-2 ring-rose-300/60"
        )}
        style={isActive ? undefined : { borderColor: 'var(--db-border)', background: 'var(--db-surface)', color: 'var(--db-text-muted)' }}
      >
        <div
          className={clsx(
            "flex h-12 w-12 items-center justify-center rounded-xl border-2 text-xl font-semibold transition",
            isActive
              ? "border-rose-300 bg-rose-100 text-rose-700"
              : ""
          )}
          style={isActive ? undefined : { borderColor: 'var(--db-border)', background: 'var(--db-surface-alt)', color: 'var(--db-text-muted)' }}
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
          <span className="db-font-sm font-semibold">Delete task</span>
          <span className="db-font-xs" style={{ color: 'var(--db-text-dim)' }}>Drop here to remove</span>
        </div>
      </div>
    </div>
  );
};

















// ── Segmented Project Selector ──

interface SegmentedProjectSelectorProps {
  options: ProjectOption[];
  selectedId: string;
  isLoading: boolean;
  onSelect: (id: string) => void;
}

const spsDropdownStyle: CSSProperties = {
  position: "absolute",
  top: "100%",
  left: 0,
  zIndex: 9999,
  minWidth: 280,
  maxHeight: 420,
  overflowY: "auto",
  background: "var(--color-gray-800, #1e293b)",
  border: "1px solid var(--color-gray-600, #475569)",
  borderRadius: 6,
  boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
  marginTop: 2,
  padding: "4px 0",
};

const spsItemStyle: CSSProperties = {
  padding: "4px 10px",
  fontSize: 'calc(var(--wc-font-size, 13px) - 2px)',
  cursor: "pointer",
  whiteSpace: "nowrap",
  overflow: "hidden",
  textOverflow: "ellipsis",
  color: "#d1d5db",
};

const spsItemSelectedStyle: CSSProperties = {
  ...spsItemStyle,
  background: "var(--color-blue-900, #1e3a5f)",
  color: "#93c5fd",
  fontWeight: 600,
};

const spsSectionHeaderStyle: CSSProperties = {
  padding: "6px 10px 3px",
  fontSize: 'calc(var(--wc-font-size, 13px) - 4px)',
  fontWeight: 700,
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  color: "#9ca3af",
  cursor: "pointer",
  userSelect: "none",
  display: "flex",
  alignItems: "center",
  gap: 4,
};

const spsSectionHeaderFixedStyle: CSSProperties = {
  ...spsSectionHeaderStyle,
  cursor: "default",
};

const spsDividerStyle: CSSProperties = {
  height: 1,
  background: "var(--color-gray-700, #374151)",
  margin: "3px 8px",
};

const SegmentedProjectSelector: React.FC<SegmentedProjectSelectorProps> = ({
  options,
  selectedId,
  isLoading,
  onSelect,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({
    previous: true,
    next: true,
    older: true,
  });
  const containerRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [isOpen]);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsOpen(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [isOpen]);

  const segments = useMemo(() => segmentProjects(options), [options]);

  const selectedLabel = useMemo(() => {
    if (!selectedId) return isLoading ? "Loading..." : "Project: All";
    const found = options.find((o) => o.id === selectedId);
    return found ? (found.name ?? found.intent ?? found.id) : selectedId;
  }, [selectedId, options, isLoading]);

  const toggleSection = (key: string) => {
    setCollapsedSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSelect = (id: string) => {
    onSelect(id);
    setIsOpen(false);
  };

  const renderItem = (p: ProjectOption) => {
    const label = p.name ?? p.intent ?? p.id;
    const isSelected = p.id === selectedId;
    return (
      <div
        key={p.id}
        style={isSelected ? spsItemSelectedStyle : spsItemStyle}
        title={label}
        onMouseEnter={(e) => { if (!isSelected) (e.currentTarget.style.background = "var(--color-gray-700, #334155)"); }}
        onMouseLeave={(e) => { if (!isSelected) (e.currentTarget.style.background = "transparent"); }}
        onClick={() => handleSelect(p.id)}
      >
        {label}
      </div>
    );
  };

  const renderSection = (
    key: string,
    label: string,
    items: ProjectOption[],
    collapsible: boolean,
  ) => {
    if (items.length === 0) return null;
    const isCollapsed = collapsible && collapsedSections[key];
    return (
      <div key={key}>
        <div style={spsDividerStyle} />
        <div
          style={collapsible ? spsSectionHeaderStyle : spsSectionHeaderFixedStyle}
          onClick={collapsible ? () => toggleSection(key) : undefined}
        >
          {collapsible && <span style={{ fontSize: 'calc(var(--wc-font-size, 13px) - 5px)' }}>{isCollapsed ? "▶" : "▼"}</span>}
          {label} ({items.length})
        </div>
        {!isCollapsed && items.map(renderItem)}
      </div>
    );
  };

  return (
    <div ref={containerRef} style={{ position: "relative", display: "inline-block" }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
        className="rounded px-1 py-0.5 db-font-xs"
        style={{
          border: '1px solid var(--db-border)',
          background: 'var(--db-surface)',
          color: 'var(--db-text-muted)',
          cursor: isLoading ? "default" : "pointer",
          minWidth: 120,
          textAlign: "left",
        }}
      >
        {selectedLabel} ▾
      </button>
      {isOpen && (
        <div style={spsDropdownStyle}>
          {/* All option */}
          <div
            style={selectedId === "" ? spsItemSelectedStyle : spsItemStyle}
            onMouseEnter={(e) => { if (selectedId !== "") (e.currentTarget.style.background = "var(--color-gray-700, #334155)"); }}
            onMouseLeave={(e) => { if (selectedId !== "") (e.currentTarget.style.background = "transparent"); }}
            onClick={() => handleSelect("")}
          >
            Project: All
          </div>
          {renderSection("permanent", "Permanent", segments.permanent, false)}
          {renderSection("thisWeek", "This Week", segments.thisWeek, false)}
          {renderSection("next8", "Next 8 Weeks", segments.next8, false)}
          {renderSection("previous2", "Previous 2 Weeks", segments.previous2, false)}
          {renderSection("future", "Future", segments.future, true)}
          {renderSection("older", "Older", segments.older, true)}
        </div>
      )}
    </div>
  );
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

  // Build move-to-project options for task cards
  const moveToProjectOptions = useMemo(() => {
    if (!selectedProjectId || projectOptions.length < 2) return [];
    const current = projectOptions.find((p) => p.id === selectedProjectId);
    if (!current) return [];

    // Parse dt_kanban for the current project to find nearby ones
    const currentDt = current.dtKanban ? new Date(current.dtKanban).getTime() : 0;
    const fourWeeksMs = 4 * 7 * 86400000;

    type MoveOpt = { id: string; name: string; group: string };
    const opts: MoveOpt[] = [];
    const seen = new Set<string>();
    seen.add(selectedProjectId); // exclude current

    for (const p of projectOptions) {
      if (seen.has(p.id)) continue;
      seen.add(p.id);
      const label = p.name ?? p.intent ?? p.id;
      const pDt = p.dtKanban ? new Date(p.dtKanban).getTime() : 0;

      if (currentDt && pDt && Math.abs(pDt - currentDt) <= fourWeeksMs) {
        opts.push({ id: p.id, name: label, group: "nearby" });
      } else {
        opts.push({ id: p.id, name: label, group: "other" });
      }
    }

    // Sort: nearby first (by date), then other (alpha)
    opts.sort((a, b) => {
      if (a.group !== b.group) return a.group === "nearby" ? -1 : 1;
      return a.name.localeCompare(b.name);
    });

    return opts;
  }, [projectOptions, selectedProjectId]);

  const [contactOptions, setContactOptions] = useState<ContactOption[]>([]);
  const [selectedContactId, setSelectedContactId] = useState<string>("");
  const [isLoadingContacts, setIsLoadingContacts] = useState<boolean>(false);

  useEffect(() => {
    console.log("selectedProjectId changed:", selectedProjectId, "projectOptions:", projectOptions.length);
  }, [selectedProjectId, projectOptions.length]);

  const handleContactFilterChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setSelectedContactId(event.target.value);
  };

  // Fetch staff contacts + project assigned_to (not all contacts)
  const fetchAllContacts = useCallback(async () => {
    setIsLoadingContacts(true);
    try {
      const uniqueById = new Map<string, ContactOption>();

      // Source 1: is_staff contacts
      const response = await getRecords("contact", {
        is_staff: true,
        is_active: true,
        limit: 200,
      });
      const records = extractRecordArray(response);
      records
        .filter((r: Record<string, unknown>) => r.id !== undefined && r.id !== null)
        .forEach((r: Record<string, unknown>) => {
          const attention = typeof r.attention === "string" ? r.attention : "";
          const id = String(r.id);
          if (!uniqueById.has(id)) {
            uniqueById.set(id, {
              id,
              label: attention || `Contact #${id}`,
              searchName: (attention || id).toLowerCase(),
              email: typeof r.email === "string" ? r.email : undefined,
            });
          }
        });

      // Source 2: active projects' prefs.assigned_to
      try {
        const projRes = await getRecords("project", {
          status__in: "open,in_progress",
          fields: "prefs",
          limit: 10,
        });
        const projRecords = extractRecordArray(projRes);
        for (const proj of projRecords) {
          const assignedTo = (proj as any)?.prefs?.assigned_to;
          if (Array.isArray(assignedTo)) {
            for (const a of assignedTo) {
              const id = a.id ? String(a.id) : null;
              if (id && !uniqueById.has(id)) {
                const label = a.name || a.label || `Contact #${id}`;
                uniqueById.set(id, { id, label, searchName: label.toLowerCase() });
              }
            }
          }
        }
      } catch { /* project fetch failed — staff list is enough */ }

      const sorted = Array.from(uniqueById.values()).sort((a, b) => a.label.localeCompare(b.label));
      console.log("Staff + project contacts fetched:", sorted.length);
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
  const isAnyModalOpen = isContactManagerOpen || isGenerateOpen || !!floatingActionId;

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
  const [isTrashDeleting, setIsTrashDeleting] = useState<boolean>(false);

  const persistTaskReorder = useCallback(
    async (
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

      // A drag changes the column and the order — only those fields go (kanban_column_id,
      // order, position and action_<lang> are not action fields; the door refuses them).
      const entry: Record<string, unknown> = {
        id: targetTask.id,
        kanban_column: destinationColumn.title,
        sequence: newSequence,
      };

      console.log("Dragging task - payload:", entry);

      try {
        const response = await saveRecord("action", entry);
        console.log("Drag persist response:", response);
      } catch (error) {
        console.error("Failed to persist kanban reorder", error);
        console.error("Error details:", error);
      }
    },
    []
  );

  const removeTaskInBackend = useCallback(async (taskId: string | number) => {
    const parsedId = typeof taskId === "number" ? taskId : Number(taskId);
    const payloadId = Number.isNaN(parsedId) ? taskId : parsedId;

    try {
      await saveRecord("action", {
        id: payloadId,
        is_active: { mode: "update", value: false },
        status: { mode: "update", value: "Removed" },
        kanban_column: { mode: "update", value: "Removed" },
      });

      return { success: true } as const;
    } catch (error) {
      console.error("Failed to remove kanban task", error);
      const message =
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
          void persistTaskReorder(next, item, dropResult);
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

      const uniqueById = new Map<string, ProjectOption>();
      activeRecords.forEach((record) => {
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
        const numericId = Number(projectId);
        if (!Number.isNaN(numericId) && String(numericId) === String(projectId)) {
          params.project_id = numericId;
        } else {
          params.project_id = projectId;
          params.project_slug = projectId;
        }
      }
      if (contactId) {
        params.contact_id = contactId;
      }

      console.log("fetchActions - params:", params);
      const response = await getRecords("action", Object.keys(params).length ? params : undefined);
      console.log("fetchActions - raw response:", response);

      let items = extractKanbanItems(response);

      // If this is a sprint (has parent_id + date range), also fetch parent project
      // actions whose dt_start falls within this sprint's window
      if (projectId) {
        const selectedProj = projectOptions.find((p) => p.id === projectId);
        if (selectedProj?.parent_id && selectedProj.dt_start && selectedProj.dt_end) {
          try {
            const parentParams: Record<string, string | number> = {
              project_id: Number(selectedProj.parent_id),
            };
            if (contactId) parentParams.contact_id = contactId;
            const parentResponse = await getRecords("action", parentParams);
            const parentItems = extractKanbanItems(parentResponse);
            // Filter parent items to those whose dt_start falls in this sprint's range
            const sprintStart = selectedProj.dt_start;
            const sprintEnd = selectedProj.dt_end;
            const existingIds = new Set(items.map((i: any) => i.id));
            const filtered = parentItems.filter((item: any) => {
              if (existingIds.has(item.id)) return false;
              const dtStart = item.dt_start || item.dtStart;
              if (typeof dtStart !== "number") return false;
              return dtStart >= sprintStart && dtStart < sprintEnd;
            });
            if (filtered.length > 0) {
              console.log(`fetchActions - added ${filtered.length} parent project actions within sprint range`);
              items = [...items, ...filtered];
            }
          } catch (e) {
            console.error("Failed to fetch parent project actions:", e);
          }
        }
      }

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
  }, [projectOptions]);

  // Handle moving a task to a different project
  const handleMoveToProject = useCallback(async (taskId: string | number, projectId: string, projectName: string) => {
    try {
      const numericProjectId = Number(projectId);
      await saveRecord("action", {
        id: Number(taskId),
        project_id: Number.isNaN(numericProjectId) ? 0 : numericProjectId,
        project_name: projectName,
      });
      // Refresh the board
      void fetchActions({ projectId: selectedProjectId || undefined, contactId: selectedContactId || undefined });
    } catch (error) {
      console.error("Failed to move task to project:", error);
    }
  }, [selectedProjectId, selectedContactId, fetchActions]);

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
    return formatDt(date, 'datetime');
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

  const columns = useMemo(
    () =>
      board.column_order
        .map((columnId) => board.columns[columnId])
        .filter((column): column is KanbanColumnType => Boolean(column)),
    [board]
  );

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
      if (typeof task.priority === 'string') base[task.priority] += 1;
    });

    return base;
  }, [board.tasks]);

  const totalTasks = useMemo(() => Object.keys(board.tasks).length, [board.tasks]);

  const handleNewActionFloating = useCallback(async () => {
    try {
      // new: the server's defaults populate it; the project is the context the board holds
      // (project_id is the FK — a project picked by slug in the URL is not an id).
      const projectId = Number(selectedProjectId);
      const result: any = await createRecord("action",
        selectedProjectId && Number.isFinite(projectId) ? { project_id: projectId } : {});
      const newId = result?.id;
      if (newId) setFloatingActionId(String(newId));
    } catch (err) {
      // Never silent (Axiom 6): the board said nothing when the door refused.
      console.error("[Kanban] New Action failed:", err);
      alert("New Action failed: " + refusedFrom(err).message);
    }
  }, [selectedProjectId]);

  const gridStyle = useMemo<CSSProperties>(
    () => ({
      gridTemplateColumns: `repeat(${Math.max(1, columnsPerRow)}, minmax(0, 1fr))`,
    }),
    [columnsPerRow]
  );

  return (
    <div className="space-y-6" style={{ fontSize: 'var(--wc-font-size, 13px)' }}>
      <div className="flex items-center gap-1 px-2 py-1" style={{ fontSize: 'calc(var(--wc-font-size, 13px) - 1px)', color: 'var(--db-accent, #2563eb)' }}>
        <Link to={PageRoutes.multiProjectGantt}
          style={{ padding: '4px 8px', border: '1px solid transparent', borderRadius: 4, background: 'transparent', fontSize: 'calc(var(--wc-font-size, 13px) - 1px)', fontWeight: 600, whiteSpace: 'nowrap', color: 'var(--db-accent, #2563eb)', textDecoration: 'none' }}
        >📋 Multi-Project</Link>
          <SegmentedProjectSelector
            options={projectOptions}
            selectedId={selectedProjectId}
            isLoading={isLoadingProjects}
            onSelect={(id) => {
              setSelectedProjectId(id);
              void fetchActions({ projectId: id || undefined, contactId: selectedContactId || undefined });
            }}
          />
          <select value={selectedContactId} onChange={handleContactFilterChange} disabled={isLoadingContacts}
            className="rounded px-1 py-0.5 db-font-xs"
            style={{ border: '1px solid var(--db-border)', background: 'var(--db-surface)', color: 'var(--db-text-muted)' }}
          >
            <option value="">{isLoadingContacts ? "Loading..." : "Contact: All"}</option>
            {contactOptions.map((option) => (
              <option key={option.id} value={option.id}>{option.label}</option>
            ))}
          </select>
          {selectedProjectId && (
            <button
              onClick={() => setIsContactManagerOpen(true)}
              title="Manage project contacts"
              style={{ padding: '2px 6px', border: '1px solid transparent', borderRadius: 4, background: 'transparent', cursor: 'pointer', fontSize: 'calc(var(--wc-font-size, 13px) - 1px)', fontWeight: 700, color: 'var(--db-accent-green, #16a34a)', lineHeight: 1 }}
            >+</button>
          )}
          <select value={columnsPerRow} onChange={(event) => setColumnsPerRow(Number(event.target.value))}
            className="rounded px-1 py-0.5 db-font-xs"
            style={{ border: '1px solid var(--db-border)', background: 'var(--db-surface)', color: 'var(--db-text-muted)' }}
          >
            {columnDensityOptions.map((option) => (
              <option key={option} value={option}>Cols: {option}</option>
            ))}
          </select>
          <button onClick={() => setIsGenerateOpen(true)} title="Generate kanban project records"
            style={{ padding: '4px 8px', border: '1px solid transparent', borderRadius: 4, background: 'transparent', cursor: 'pointer', fontSize: 'calc(var(--wc-font-size, 13px) - 1px)', fontWeight: 600, whiteSpace: 'nowrap', color: 'var(--db-accent, #2563eb)' }}
          >📦 Gen Projects</button>
          <button onClick={() => void handleNewActionFloating()}
            style={{ padding: '4px 8px', border: '1px solid transparent', borderRadius: 4, background: 'transparent', cursor: 'pointer', fontSize: 'calc(var(--wc-font-size, 13px) - 1px)', fontWeight: 600, whiteSpace: 'nowrap', color: 'var(--db-accent-green, #16a34a)' }}
          >+ New Action</button>
          <button onClick={() => void handleManualRefresh()} disabled={isRefreshing || isLoading}
            title={`Last refreshed: ${formatLastRefresh(lastRefreshTime)}. Auto-refresh every 5 minutes${isAnyModalOpen ? ' (paused while dialog open)' : ''}`}
            style={{ padding: '4px 8px', border: '1px solid transparent', borderRadius: 4, background: 'transparent', cursor: isRefreshing ? 'default' : 'pointer', opacity: isRefreshing ? 0.4 : 1, fontSize: 'calc(var(--wc-font-size, 13px) - 1px)', fontWeight: 600, whiteSpace: 'nowrap', color: 'var(--db-accent, #2563eb)' }}
          >🔄 {isRefreshing ? "Refreshing..." : "Refresh"}</button>
          <span style={{ fontSize: 'calc(var(--wc-font-size, 13px) - 3px)', color: 'var(--db-text-muted)' }} title="Auto-refresh every 5 minutes">
            {formatLastRefresh(lastRefreshTime)}
          </span>
      </div>

      {projectFetchError && (
        <div className="flex items-center justify-between rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 db-font-sm text-amber-700">
          <span>{projectFetchError}</span>
          <button type="button" onClick={() => void fetchProjects()}
            style={{ padding: '4px 8px', border: '1px solid transparent', borderRadius: 4, background: 'transparent', cursor: 'pointer', fontSize: 'calc(var(--wc-font-size, 13px) - 1px)', fontWeight: 600, color: '#e8c870' }}
          >↩ Retry</button>
        </div>
      )}

      {fetchError && (
        <div className="flex items-center justify-between rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 db-font-sm text-rose-700">
          <span>{fetchError}</span>
          <button type="button"
            onClick={() => void fetchActions({ projectId: selectedProjectId || undefined, contactId: selectedContactId || undefined })}
            style={{ padding: '4px 8px', border: '1px solid transparent', borderRadius: 4, background: 'transparent', cursor: 'pointer', fontSize: 'calc(var(--wc-font-size, 13px) - 1px)', fontWeight: 600, color: '#e05252' }}
          >↩ Retry</button>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {(Object.keys(prioritySummary) as TaskPriority[]).map((priority) => (
          <div key={priority} className={clsx("flex gap-2 items-center justify-between rounded-full px-3 py-1 db-font-xs font-semibold", priorityPalette[priority])}>
            <p className="db-font-xs font-medium uppercase tracking-wide" style={{ color: 'var(--db-text)' }}>{priority}</p>
            <div className="flex items-center gap-2">
              <span className="text-3xl font-semibold" style={{ color: 'var(--db-text)' }}>{prioritySummary[priority]}</span>
              <span className="db-font-xs font-medium" style={{ color: 'var(--db-text-dim)' }}>/ {totalTasks} tasks</span>
            </div>
          </div>
        ))}
      </div>

      <DndProvider backend={HTML5Backend}>
        <KanbanDragLayer tasks={board.tasks} />
        <TrashDropZone isDeleting={isTrashDeleting} />
        {isLoading ? (
          <div className="flex justify-center items-center h-[50vh] rounded-3xl border border-dashed db-font-sm" style={{ borderColor: 'var(--db-border)', color: 'var(--db-text-dim)' }}>
            <LoadingSpinner size="lg" label="Loading..." />
          </div>
        ) : columns.length === 0 ? (
          <div className="flex h-56 items-center justify-center rounded-3xl border border-dashed db-font-sm" style={{ borderColor: 'var(--db-border)', color: 'var(--db-text-dim)' }}>
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
                moveToOptions={moveToProjectOptions}
                onMoveToProject={handleMoveToProject}
              />
            ))}
          </div>
        )}
      </DndProvider>


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
          <div className="mx-4 w-full max-w-md rounded-xl p-6 shadow-2xl" style={{ background: 'var(--db-surface)' }}>
            <h3 className="mb-4 text-lg font-semibold" style={{ color: 'var(--db-text)' }}>
              Generate Kanban Projects
            </h3>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="mb-1 block db-font-sm font-medium" style={{ color: 'var(--db-text)' }}>Category</span>
                  <input
                    type="text"
                    value={generateCategory}
                    onChange={(e) => setGenerateCategory(e.target.value)}
                    placeholder="kanban"
                    className="w-full rounded-lg px-3 py-2 db-font-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 db-input"
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block db-font-sm font-medium" style={{ color: 'var(--db-text)' }}>Name</span>
                  <input
                    type="text"
                    value={generateName}
                    onChange={(e) => setGenerateName(e.target.value)}
                    placeholder="optional"
                    className="w-full rounded-lg px-3 py-2 db-font-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 db-input"
                  />
                </label>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="mb-1 block db-font-sm font-medium" style={{ color: 'var(--db-text)' }}>Start date</span>
                  <input
                    type="date"
                    value={generateStartDate}
                    onChange={(e) => setGenerateStartDate(e.target.value)}
                    className="w-full rounded-lg px-3 py-2 db-font-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 db-input"
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block db-font-sm font-medium" style={{ color: 'var(--db-text)' }}>End date</span>
                  <input
                    type="date"
                    value={generateEndDate}
                    onChange={(e) => setGenerateEndDate(e.target.value)}
                    className="w-full rounded-lg px-3 py-2 db-font-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 db-input"
                  />
                </label>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="mb-1 block db-font-sm font-medium" style={{ color: 'var(--db-text)' }}>Number of projects</span>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={generateCount}
                    onChange={(e) => setGenerateCount(Math.max(1, Math.min(100, Number(e.target.value))))}
                    className="w-full rounded-lg px-3 py-2 db-font-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 db-input"
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block db-font-sm font-medium" style={{ color: 'var(--db-text)' }}>Interval (days)</span>
                  <input
                    type="number"
                    min={1}
                    max={365}
                    value={generateInterval}
                    onChange={(e) => setGenerateInterval(Math.max(1, Number(e.target.value)))}
                    className="w-full rounded-lg px-3 py-2 db-font-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 db-input"
                  />
                </label>
              </div>
              <div className="rounded-lg p-3 db-font-xs" style={{ background: 'var(--db-surface-alt)', color: 'var(--db-text-muted)' }}>
                Will create <strong>{generateCount}</strong> project(s) named{" "}
                <code className="text-indigo-600">{generatedProjectName}</code>,
                starting <strong>{generateStartDate}</strong>, every <strong>{generateInterval}</strong> day(s).
              </div>
              {generateResult && (
                <div className={clsx(
                  "rounded-lg p-3 db-font-sm font-medium",
                  generateResult.startsWith("Error")
                    ? "bg-red-50 text-red-700"
                    : "bg-green-50 text-green-700",
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
                className="rounded-lg px-4 py-2 db-font-sm font-medium"
                style={{ border: '1px solid var(--db-border)', color: 'var(--db-text-muted)' }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void handleGenerateProjects()}
                disabled={isGenerating || !generateStartDate}
                className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-4 py-2 db-font-sm font-semibold text-white shadow-sm hover:bg-amber-500 disabled:cursor-not-allowed disabled:opacity-50"
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
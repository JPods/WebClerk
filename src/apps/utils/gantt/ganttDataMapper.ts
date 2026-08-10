/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import type { GanttTask, GanttLink } from "./gantt.types";
import type { ApiKanbanItem } from "../kanban/kanbanDataMapper";

// Default start offset: today - 5 days
const DEFAULT_START_OFFSET_DAYS = -5;

const DAY_IN_MS = 24 * 60 * 60 * 1000;

// Debug flag
let _mapperDebugLogged = false;

export interface BadgePrefs {
  bg_color?: string;     // hex color for badge background
  text_color?: string;   // hex color for badge text
  initials?: string;     // custom initials override
}

export interface AssignedUser {
  id: string | number;
  name?: string;
  is_staff?: boolean;
  prefs?: {
    badge?: BadgePrefs;
  };
}

export interface GanttMappedTask extends GanttTask {
  projectId: string;
  projectName: string;
  projectIda?: string;
  taskIda?: string;
  percentComplete?: number;
  columnId?: string;
  columnTitle?: string;
  priority?: string;
  priorityValue?: number;
  assignee?: string;
  assignedTo?: AssignedUser[];
  apiId: string;
  details?: string;
  /** Parent task IDs from refs.parents - used for dependency links */
  refParents?: string[];
  /** True if this task is on the critical path */
  isCritical?: boolean;
  /** Slack/float in days - how much buffer before becoming critical */
  slack?: number;
  /** Original planned start date for baseline comparison */
  dtStartOriginal?: Date;
  /** Original planned end date for baseline comparison */
  dtEndOriginal?: Date;
}

export interface ProjectActionData {
  projectId: string;
  projectName: string;
  projectIda?: string;
  actions: ApiKanbanItem[];
}

export interface GanttDataset {
  tasks: GanttMappedTask[];
  links: GanttLink[];
}

// Priority mapping
const PRIORITY_LABELS: Record<number, string> = {
  1: "low",
  2: "medium",
  3: "high",
  4: "critical",
};

const mapPriorityLabel = (value?: number | null): string => {
  if (typeof value !== "number") return "medium";
  return PRIORITY_LABELS[value] ?? "medium";
};

// Date parsing utilities
// Normalizes dates to midday to prevent timezone-related day shifts
const parseDateValue = (value?: string | number | null): Date | null => {
  if (!value) return null;
  
  if (typeof value === "number") {
    // Handle Unix timestamps (seconds or milliseconds)
    const timestamp = value > 1e12 ? value : value * 1000;
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return null;
    
    // Normalize to midday of the UTC date to avoid timezone boundary issues
    // Extract UTC date components and create a new date at local noon
    const utcYear = date.getUTCFullYear();
    const utcMonth = date.getUTCMonth();
    const utcDay = date.getUTCDate();
    return new Date(utcYear, utcMonth, utcDay, 12, 0, 0, 0);
  }
  
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) return null;
    
    // Try parsing as ISO string or common formats
    const parsed = new Date(trimmed);
    if (Number.isNaN(parsed.getTime())) return null;
    
    // Normalize to midday to avoid timezone issues
    const utcYear = parsed.getUTCFullYear();
    const utcMonth = parsed.getUTCMonth();
    const utcDay = parsed.getUTCDate();
    return new Date(utcYear, utcMonth, utcDay, 12, 0, 0, 0);
  }
  
  return null;
};

/**
 * Resolve the start date for a task with fallback to today - 5 days
 * Priority: dt_start → dt_expected → dt_deadline → (today - 5 days)
 */
export const resolveTaskStartDate = (action: ApiKanbanItem): Date => {
  const candidates = [
    action.dt_start,
    action.dt_expected,
    action.dt_deadline,
  ];
  
  for (const candidate of candidates) {
    const parsed = parseDateValue(candidate);
    if (parsed) {
      return parsed;
    }
  }
  
  // Fallback: today - 5 days
  const fallback = new Date();
  fallback.setDate(fallback.getDate() + DEFAULT_START_OFFSET_DAYS);
  fallback.setHours(9, 0, 0, 0); // Set to 9 AM for cleaner display
  return fallback;
};

/**
 * Resolve the end date for a task
 * Priority: dt_end → dt_deadline → (start + 1 day)
 */
export const resolveTaskEndDate = (action: ApiKanbanItem, start: Date): Date => {
  const candidates = [
    action.dt_end,
    action.dt_deadline,
  ];
  
  for (const candidate of candidates) {
    const parsed = parseDateValue(candidate);
    if (parsed && parsed.getTime() > start.getTime()) {
      return parsed;
    }
  }
  
  // Fallback: start + 1 day
  const fallback = new Date(start.getTime());
  fallback.setDate(fallback.getDate() + 1);
  return fallback;
};

/**
 * Calculate duration in days between two dates
 */
export const calculateDurationDays = (start: Date, end: Date): number => {
  const diffMs = end.getTime() - start.getTime();
  if (diffMs <= 0) return 1;
  return Math.max(1, Math.ceil(diffMs / DAY_IN_MS));
};

/**
 * Normalize progress value to 0-100 range (SVAR Gantt expects 0-100)
 */
export const normalizeProgress = (value?: number | string | null): number | undefined => {
  if (value === null || value === undefined) return undefined;
  
  const numValue = typeof value === "string" ? parseFloat(value.replace(/%$/, "")) : value;
  if (Number.isNaN(numValue)) return undefined;
  
  // If value is a decimal (0-1 range), convert to percentage
  if (numValue > 0 && numValue <= 1) {
    return Math.max(0, Math.min(100, numValue * 100));
  }
  
  // Assume it's already in 0-100 range
  return Math.max(0, Math.min(100, numValue));
};

/**
 * Extract progress from various possible locations in the API response
 */
const extractProgress = (action: ApiKanbanItem): number | undefined => {
  const actionRecord = action as Record<string, unknown>;
  
  const candidates = [
    // Canonical field used by kanbanDataMapper
    actionRecord["percent_complete"],
    // Common progress fields
    action.progress,
    actionRecord["progress_percent"],
    actionRecord["progress_percentage"],
    // Completion fields
    actionRecord["completion"],
    actionRecord["completion_percent"],
    actionRecord["completion_percentage"],
    // Nested in prefs
    action.prefs?.userdefined?.progress,
  ];
  
  for (const candidate of candidates) {
    const normalized = normalizeProgress(candidate as number | string | null | undefined);
    if (normalized !== undefined) {
      return normalized;
    }
  }
  
  return undefined;
};

/**
 * Extract the action text from an API item
 * Checks both nested action object (action.en) and flat properties (action_en)
 */
const extractActionText = (action: ApiKanbanItem): string => {
  // Check nested action object first (highest priority)
  const nestedAction = action.action;
  if (nestedAction && typeof nestedAction === "object") {
    const nestedEn = nestedAction.en;
    if (typeof nestedEn === "string" && nestedEn.trim()) {
      return nestedEn;
    }
    // Try any other language in the nested object
    const firstValue = Object.values(nestedAction).find(
      (v) => typeof v === "string" && v.trim()
    );
    if (firstValue) {
      return firstValue;
    }
  }
  
  // Fall back to flat properties
  if (action.action_en && typeof action.action_en === "string" && action.action_en.trim()) {
    return action.action_en;
  }
  if (action.action_ar && typeof action.action_ar === "string" && action.action_ar.trim()) {
    return action.action_ar;
  }
  if (action.action_bn && typeof action.action_bn === "string" && action.action_bn.trim()) {
    return action.action_bn;
  }
  if (action.action_es && typeof action.action_es === "string" && action.action_es.trim()) {
    return action.action_es;
  }
  
  return "Untitled Action";
};



/**
 * Map a single API action to SVAR Gantt task format
 */
export const mapApiActionToGanttTask = (
  action: ApiKanbanItem,
  projectId: string,
  projectName: string,
  projectColor?: string,
  projectIda?: string
): GanttMappedTask => {
  const start = resolveTaskStartDate(action);
  const end = resolveTaskEndDate(action, start);
  
  // Extract duration - prefer explicit duration field, otherwise calculate from dates
  // Default to 7 days if duration is null, 0, or invalid
  const actionRecord = action as Record<string, unknown>;
  
  // DEBUG: Log first record to see what fields are coming from API
  if (!_mapperDebugLogged) {
    console.log("[GanttMapper] API action record keys:", Object.keys(actionRecord));
    console.log("[GanttMapper] action.id:", action.id);
    console.log("[GanttMapper] actionRecord.ida:", actionRecord.ida, "type:", typeof actionRecord.ida);
    console.log("[GanttMapper] actionRecord.project_ida:", actionRecord.project_ida, "type:", typeof actionRecord.project_ida);
    console.log("[GanttMapper] actionRecord.duration:", actionRecord.duration);
    console.log("[GanttMapper] actionRecord.percent_complete:", actionRecord.percent_complete);
    console.log("[GanttMapper] Full record (first 2000 chars):", JSON.stringify(actionRecord, null, 2).slice(0, 2000));
    _mapperDebugLogged = true;
  }
  
  const DEFAULT_DURATION = 7;
  let duration: number;
  if (typeof actionRecord.duration === "number" && actionRecord.duration > 0) {
    duration = actionRecord.duration;
  } else {
    const calculatedDuration = calculateDurationDays(start, end);
    duration = calculatedDuration > 0 ? calculatedDuration : DEFAULT_DURATION;
  }
  
  // Extract percent_complete directly
  let percentComplete = 0;
  if (typeof actionRecord.percent_complete === "number") {
    percentComplete = actionRecord.percent_complete;
  } else {
    const extracted = extractProgress(action);
    percentComplete = extracted ?? 0;
  }
  
  // Extract task ida from the action record
  const taskIda = typeof actionRecord.ida === "string" ? actionRecord.ida : undefined;
  
  // Extract project_ida from the action record (overrides project-level if present)
  const actionProjectIda = typeof actionRecord.project_ida === "string" && actionRecord.project_ida 
    ? actionRecord.project_ida 
    : projectIda;
  
  const task: GanttMappedTask = {
    id: action.id,
    apiId: action.id,
    text: extractActionText(action),
    taskIda,
    projectIda: actionProjectIda,
    percentComplete,
    start,
    end,
    duration,
    progress: percentComplete, // SVAR expects 0-100 for progress bar
    type: duration === 0 || !duration ? "milestone" : "task", // 0-duration shows as diamond
    parent: action.refs?.links?.parent,
    projectId,
    projectName,
    columnId: action.kanban_column || undefined,
    columnTitle: action.kanban_column || undefined,
    priority: mapPriorityLabel(action.priority),
    priorityValue: typeof action.priority === "number" ? action.priority : undefined,
    assignee: action.assigned_to?.[0]?.name,
    assignedTo: Array.isArray(action.assigned_to) ? action.assigned_to.map((a: any) => ({
      id: a.id ?? a.contact_id,
      name: a.name ?? a.attention,
      is_staff: a.is_staff,
      prefs: a.prefs?.badge ? { badge: a.prefs.badge } : undefined,
    })) : undefined,
    details: action.description_en || action.comments?.public || undefined,
    // Store refs.parents for link manipulation
    refParents: extractRefParents(action),
    // Original planned dates for baseline comparison
    dtStartOriginal: parseDateValue(actionRecord.dt_start_original as number | undefined),
    dtEndOriginal: parseDateValue(actionRecord.dt_end_original as number | undefined),
  };
  
  // Add color if provided
  if (projectColor) {
    (task as unknown as { color?: string; progressColor?: string }).color = projectColor;
    (task as unknown as { color?: string; progressColor?: string }).progressColor = projectColor;
  }
  
  return task;
};

/**
 * Extract refs.parents array from action as string[]
 */
const extractRefParents = (action: ApiKanbanItem): string[] => {
  const refs = action.refs as Record<string, unknown> | undefined;
  const parents = refs?.parents;
  if (!Array.isArray(parents)) return [];
  return parents.map((p) => String(p));
};

/**
 * Create links between tasks based on refs.parents[] dependencies
 * Each parent ID in refs.parents[] creates a finish-to-start link
 */
const createDependencyLinks = (
  tasks: GanttMappedTask[],
  actions: ApiKanbanItem[]
): GanttLink[] => {
  const links: GanttLink[] = [];
  const taskIdSet = new Set(tasks.map((t) => String(t.id)));
  
  for (const action of actions) {
    const targetId = action.id;
    if (!targetId) continue;
    
    // Get parent IDs from refs.parents[]
    const refs = action.refs as Record<string, unknown> | undefined;
    const parents = refs?.parents;
    
    if (!Array.isArray(parents) || parents.length === 0) continue;
    
    for (const parentId of parents) {
      const sourceId = String(parentId);
      
      // Only create link if both source and target exist in our task set
      if (taskIdSet.has(sourceId) && taskIdSet.has(String(targetId))) {
        links.push({
          id: `dep-${sourceId}-${targetId}`,
          source: Number(sourceId) || sourceId, // SVAR prefers numeric IDs
          target: Number(targetId) || targetId,
          type: "e2s", // end-to-start (finish-to-start)
        });
      }
    }
  }
  
  return links;
};

/**
 * Sort tasks so that children appear immediately after their last parent is placed.
 * 
 * This ensures that when viewing the task list:
 * 1. Root tasks (no parents) are sorted by start date (earliest first)
 * 2. A child task waits until ALL its parents are placed
 * 3. Once ready, the child is inserted immediately after its last placed parent
 * 
 * Example: If Task C depends on A and B, and root order is A, B, X, Y
 *          Then C appears right after B: A, B, C, X, Y
 */
const topologicalSortByDependencies = (tasks: GanttMappedTask[]): GanttMappedTask[] => {
  if (tasks.length === 0) return [];
  
  // Build lookup maps
  const taskById = new Map<string, GanttMappedTask>();
  const taskParents = new Map<string, Set<string>>(); // taskId -> Set of valid parentIds
  const taskChildren = new Map<string, string[]>();   // taskId -> [childIds]
  
  for (const task of tasks) {
    const taskId = String(task.id);
    taskById.set(taskId, task);
    
    const parents = (task as any).refParents || [];
    taskParents.set(taskId, new Set(parents.map(String)));
    
    for (const parentId of parents) {
      const parentIdStr = String(parentId);
      if (!taskChildren.has(parentIdStr)) {
        taskChildren.set(parentIdStr, []);
      }
      taskChildren.get(parentIdStr)!.push(taskId);
    }
  }
  
  // Filter parent sets to only include tasks that exist in our set
  for (const [taskId, parents] of taskParents) {
    const validParents = new Set<string>();
    for (const parentId of parents) {
      if (taskById.has(parentId)) {
        validParents.add(parentId);
      }
    }
    taskParents.set(taskId, validParents);
  }
  
  // Separate tasks: root tasks (no valid parents) vs dependent tasks
  const rootTasks: GanttMappedTask[] = [];
  
  for (const task of tasks) {
    const taskId = String(task.id);
    const parents = taskParents.get(taskId) || new Set();
    if (parents.size === 0) {
      rootTasks.push(task);
    }
  }
  
  // Sort root tasks by start date (earliest first)
  rootTasks.sort((a, b) => {
    const aTime = a.start instanceof Date ? a.start.getTime() : 0;
    const bTime = b.start instanceof Date ? b.start.getTime() : 0;
    return aTime - bTime;
  });
  
  // Build result with topological ordering
  const result: GanttMappedTask[] = [];
  const placed = new Set<string>();
  const unplacedParentCount = new Map<string, number>(); // Track how many parents still need placing
  
  // Initialize unplaced parent counts
  for (const [taskId, parents] of taskParents) {
    unplacedParentCount.set(taskId, parents.size);
  }
  
  // Helper to get and mark ready children (all parents placed), sorted by start date
  const getReadyChildren = (placedParentId: string): GanttMappedTask[] => {
    const children = taskChildren.get(placedParentId) || [];
    const ready: GanttMappedTask[] = [];
    
    for (const childId of children) {
      if (placed.has(childId)) continue;
      
      // Decrement unplaced parent count
      const remaining = (unplacedParentCount.get(childId) || 1) - 1;
      unplacedParentCount.set(childId, remaining);
      
      // Child is ready only if ALL parents are placed (remaining = 0)
      if (remaining <= 0) {
        const child = taskById.get(childId);
        if (child) {
          ready.push(child);
        }
      }
    }
    
    // Sort ready children by start date (earliest first)
    ready.sort((a, b) => {
      const aTime = a.start instanceof Date ? a.start.getTime() : 0;
      const bTime = b.start instanceof Date ? b.start.getTime() : 0;
      return aTime - bTime;
    });
    
    return ready;
  };
  
  // Place a task and immediately cascade to any children that become ready
  const placeTask = (task: GanttMappedTask) => {
    const taskId = String(task.id);
    if (placed.has(taskId)) return;
    
    result.push(task);
    placed.add(taskId);
    
    // Get children that are now ready (all their parents placed)
    const readyChildren = getReadyChildren(taskId);
    
    // Recursively place ready children (they'll cascade to their children)
    for (const child of readyChildren) {
      placeTask(child);
    }
  };
  
  // Place all root tasks (this cascades to children as they become ready)
  for (const rootTask of rootTasks) {
    placeTask(rootTask);
  }
  
  // Handle any orphaned tasks (parents don't exist in our set)
  for (const task of tasks) {
    const taskId = String(task.id);
    if (!placed.has(taskId)) {
      placeTask(task);
    }
  }
  
  return result;
};

/**
 * Calculate and mark critical path tasks.
 * The critical path is the longest path through the project that determines
 * the minimum project duration. Tasks on this path have zero float/slack.
 * 
 * Uses forward pass (earliest start/finish) and backward pass (latest start/finish)
 * to identify tasks where ES == LS (zero float = critical).
 */
const markCriticalPath = (tasks: GanttMappedTask[]): void => {
  if (tasks.length === 0) return;
  
  // Build dependency maps
  const taskById = new Map<string, GanttMappedTask>();
  const taskParents = new Map<string, string[]>();
  const taskChildren = new Map<string, string[]>();
  
  for (const task of tasks) {
    const taskId = String(task.id);
    taskById.set(taskId, task);
    
    const parents = (task as any).refParents || [];
    const validParents = parents.map(String).filter((p: string) => {
      // Parent must exist in our task set
      return tasks.some((t) => String(t.id) === p);
    });
    taskParents.set(taskId, validParents);
    
    for (const parentId of validParents) {
      if (!taskChildren.has(parentId)) {
        taskChildren.set(parentId, []);
      }
      taskChildren.get(parentId)!.push(taskId);
    }
  }
  
  // Get task end time in ms 
  const getTaskEnd = (task: GanttMappedTask): number => {
    if (task.end instanceof Date) return task.end.getTime();
    if (task.start instanceof Date && task.duration) {
      return task.start.getTime() + task.duration * DAY_IN_MS;
    }
    return task.start instanceof Date ? task.start.getTime() : 0;
  };
  
  // Get task duration in ms
  const getTaskDuration = (task: GanttMappedTask): number => {
    if (task.duration) return task.duration * DAY_IN_MS;
    if (task.start instanceof Date && task.end instanceof Date) {
      return Math.max(0, task.end.getTime() - task.start.getTime());
    }
    return DAY_IN_MS; // Default 1 day
  };
  
  // Forward pass: calculate earliest start (ES) and earliest finish (EF)
  const earliestStart = new Map<string, number>();
  const earliestFinish = new Map<string, number>();
  
  // Process in topological order (tasks sorted so parents come before children)
  for (const task of tasks) {
    const taskId = String(task.id);
    const parents = taskParents.get(taskId) || [];
    
    // ES = max of all parent EFs, or task's own start if no parents
    let es = task.start instanceof Date ? task.start.getTime() : 0;
    for (const parentId of parents) {
      const parentEF = earliestFinish.get(parentId);
      if (parentEF !== undefined && parentEF > es) {
        es = parentEF;
      }
    }
    
    earliestStart.set(taskId, es);
    earliestFinish.set(taskId, es + getTaskDuration(task));
  }
  
  // Find project end (latest EF)
  let projectEnd = 0;
  for (const ef of earliestFinish.values()) {
    if (ef > projectEnd) projectEnd = ef;
  }
  
  // Backward pass: calculate latest start (LS) and latest finish (LF)
  const latestStart = new Map<string, number>();
  const latestFinish = new Map<string, number>();
  
  // Process in reverse topological order
  for (let i = tasks.length - 1; i >= 0; i--) {
    const task = tasks[i];
    const taskId = String(task.id);
    const children = taskChildren.get(taskId) || [];
    
    // LF = min of all children's LS, or project end if no children
    let lf = projectEnd;
    for (const childId of children) {
      const childLS = latestStart.get(childId);
      if (childLS !== undefined && childLS < lf) {
        lf = childLS;
      }
    }
    
    latestFinish.set(taskId, lf);
    latestStart.set(taskId, lf - getTaskDuration(task));
  }
  
  // Mark critical path: tasks where ES == LS (zero float)
  // Also calculate slack (LS - ES) in days
  const tolerance = DAY_IN_MS / 24; // 1 hour tolerance for floating point
  for (const task of tasks) {
    const taskId = String(task.id);
    const es = earliestStart.get(taskId) || 0;
    const ls = latestStart.get(taskId) || 0;
    
    // Calculate slack in days (LS - ES)
    const slackMs = ls - es;
    task.slack = Math.max(0, Math.round(slackMs / DAY_IN_MS * 10) / 10); // Round to 1 decimal
    
    // Critical if start times match (zero slack)
    task.isCritical = Math.abs(slackMs) < tolerance;
  }
};

/**
 * Options for mapping project actions to Gantt format
 */
export interface GanttMapOptions {
  /** Whether to automatically sort tasks by start date (default: true) */
  sortByDate?: boolean;
  /** Custom task order (task IDs) to use instead of auto-sorting when sortByDate is false */
  customOrder?: string[];
}

/**
 * Map multiple projects' actions to SVAR Gantt format
 */
export const mapProjectActionsToGantt = (
  projectsData: ProjectActionData[],
  projectColors: Map<string, string>,
  options: GanttMapOptions = {}
): GanttDataset => {
  const { sortByDate = true, customOrder } = options;
  const allTasks: GanttMappedTask[] = [];
  const allActions: ApiKanbanItem[] = [];
  const seenTaskIds = new Set<string>();
  
  for (const { projectId, projectName, projectIda, actions } of projectsData) {
    const projectColor = projectColors.get(projectId);
    
    const projectTasks = actions
      .filter((action) => action.id) // Ensure action has an ID
      .map((action) =>
        mapApiActionToGanttTask(action, projectId, projectName, projectColor, projectIda)
      )
      // Deduplicate tasks by ID to prevent React key warnings
      .filter((task) => {
        const taskIdStr = String(task.id);
        if (seenTaskIds.has(taskIdStr)) {
          return false;
        }
        seenTaskIds.add(taskIdStr);
        return true;
      });
    
    allTasks.push(...projectTasks);
    allActions.push(...actions);
  }
  
  // Create dependency links from refs.parents[]
  const allLinks = createDependencyLinks(allTasks, allActions);
  
  // Determine task ordering based on options
  let orderedTasks: GanttMappedTask[];
  
  if (!sortByDate && customOrder && customOrder.length > 0) {
    // Use custom order: place tasks in the order specified, with any remaining tasks at the end
    const orderMap = new Map<string, number>();
    customOrder.forEach((id, index) => orderMap.set(id, index));
    
    orderedTasks = [...allTasks].sort((a, b) => {
      const aOrder = orderMap.get(String(a.id));
      const bOrder = orderMap.get(String(b.id));
      
      // Tasks in customOrder come first, sorted by their order
      if (aOrder !== undefined && bOrder !== undefined) {
        return aOrder - bOrder;
      }
      // Tasks in customOrder come before tasks not in it
      if (aOrder !== undefined) return -1;
      if (bOrder !== undefined) return 1;
      // Tasks not in customOrder keep original order
      return 0;
    });
  } else if (sortByDate) {
    // Topological sort: place children after their parents while maintaining chronological order
    orderedTasks = topologicalSortByDependencies(allTasks);
  } else {
    // No sorting - keep order as received from API (natural order)
    orderedTasks = allTasks;
  }
  
  // Calculate and mark critical path
  markCriticalPath(orderedTasks);
  
  return { tasks: orderedTasks, links: allLinks };
};

/**
 * Filter tasks by project IDs
 */
export const filterTasksByProjects = (
  dataset: GanttDataset,
  projectIds: string[]
): GanttDataset => {
  if (projectIds.length === 0) {
    return { tasks: [], links: [] };
  }
  
  const projectIdSet = new Set(projectIds);
  const filteredTasks = dataset.tasks.filter((task) =>
    projectIdSet.has(task.projectId)
  );
  
  const taskIdSet = new Set(filteredTasks.map((t) => String(t.id)));
  const filteredLinks = dataset.links.filter(
    (link) =>
      taskIdSet.has(String(link.source)) && taskIdSet.has(String(link.target))
  );
  
  return { tasks: filteredTasks, links: filteredLinks };
};

/**
 * Get date range for the Gantt chart based on tasks
 */
export const getGanttDateRange = (
  tasks: GanttMappedTask[]
): { start: Date; end: Date } => {
  const now = new Date();
  
  if (tasks.length === 0) {
    // Default to 2 weeks around today
    const start = new Date(now);
    start.setDate(start.getDate() - 7);
    const end = new Date(now);
    end.setDate(end.getDate() + 7);
    return { start, end };
  }
  
  let minDate = new Date(tasks[0].start || now);
  let maxDate = new Date(tasks[0].end || now);
  
  for (const task of tasks) {
    const taskStart = task.start instanceof Date ? task.start : new Date(task.start || now);
    const taskEnd = task.end instanceof Date ? task.end : new Date(task.end || now);
    
    if (taskStart < minDate) minDate = taskStart;
    if (taskEnd > maxDate) maxDate = taskEnd;
  }
  
  // Add some padding
  const start = new Date(minDate);
  start.setDate(start.getDate() - 3);
  const end = new Date(maxDate);
  end.setDate(end.getDate() + 7);
  
  return { start, end };
};

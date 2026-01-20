import type { ILink, ITask } from "@svar-ui/react-gantt";
import type { ApiKanbanItem } from "../kanban/kanbanDataMapper";

// Default start offset: today - 5 days
const DEFAULT_START_OFFSET_DAYS = -5;

const DAY_IN_MS = 24 * 60 * 60 * 1000;

export interface GanttMappedTask extends ITask {
  projectId: string;
  projectName: string;
  columnId?: string;
  columnTitle?: string;
  priority?: string;
  assignee?: string;
  apiId: string;
}

export interface ProjectActionData {
  projectId: string;
  projectName: string;
  actions: ApiKanbanItem[];
}

export interface GanttDataset {
  tasks: GanttMappedTask[];
  links: ILink[];
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
const parseDateValue = (value?: string | number | null): Date | null => {
  if (!value) return null;
  
  if (typeof value === "number") {
    // Handle Unix timestamps (seconds or milliseconds)
    const timestamp = value > 1e12 ? value : value * 1000;
    const date = new Date(timestamp);
    return Number.isNaN(date.getTime()) ? null : date;
  }
  
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) return null;
    
    // Try parsing as ISO string or common formats
    const parsed = new Date(trimmed);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
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
 * Normalize progress value to 0-1 ratio
 */
export const normalizeProgress = (value?: number | string | null): number | undefined => {
  if (value === null || value === undefined) return undefined;
  
  const numValue = typeof value === "string" ? parseFloat(value) : value;
  if (Number.isNaN(numValue)) return undefined;
  
  // If value > 1, assume it's a percentage
  if (numValue > 1) {
    return Math.max(0, Math.min(1, numValue / 100));
  }
  
  return Math.max(0, Math.min(1, numValue));
};

/**
 * Extract progress from various possible locations in the API response
 */
const extractProgress = (action: ApiKanbanItem): number | undefined => {
  const candidates = [
    action.progress,
    action.progress_percent,
    action.progress_percentage,
    action.completion,
    action.completion_percent,
    action.completion_percentage,
    action.prefs?.userdefined?.progress,
  ];
  
  for (const candidate of candidates) {
    const normalized = normalizeProgress(candidate);
    if (normalized !== undefined) {
      return normalized;
    }
  }
  
  return undefined;
};

/**
 * Map a single API action to SVAR Gantt task format
 */
export const mapApiActionToGanttTask = (
  action: ApiKanbanItem,
  projectId: string,
  projectName: string,
  projectColor?: string
): GanttMappedTask => {
  const start = resolveTaskStartDate(action);
  const end = resolveTaskEndDate(action, start);
  const duration = calculateDurationDays(start, end);
  const progress = extractProgress(action);
  
  const task: GanttMappedTask = {
    id: action.id,
    apiId: action.id,
    text: action.action_en || action.project_name || "Untitled Action",
    start,
    end,
    duration,
    progress,
    type: "task",
    parent: action.refs?.links?.parent,
    projectId,
    projectName,
    columnId: action.kanban_column || undefined,
    columnTitle: action.kanban_column || undefined,
    priority: mapPriorityLabel(action.priority),
    assignee: action.assigned_to?.[0]?.name,
    details: action.description_en || action.comments?.public || undefined,
  };
  
  // Add color if provided
  if (projectColor) {
    (task as unknown as { color?: string; progressColor?: string }).color = projectColor;
    (task as unknown as { color?: string; progressColor?: string }).progressColor = projectColor;
  }
  
  return task;
};

/**
 * Create links between tasks based on sequence/order within a project
 */
const createProjectLinks = (tasks: GanttMappedTask[], projectId: string): ILink[] => {
  const projectTasks = tasks.filter((t) => t.projectId === projectId);
  
  if (projectTasks.length < 2) return [];
  
  // Sort by start date, then by id
  const sorted = [...projectTasks].sort((a, b) => {
    const aTime = a.start instanceof Date ? a.start.getTime() : 0;
    const bTime = b.start instanceof Date ? b.start.getTime() : 0;
    if (aTime === bTime) {
      return String(a.id ?? "").localeCompare(String(b.id ?? ""));
    }
    return aTime - bTime;
  });
  
  const links: ILink[] = [];
  for (let i = 1; i < sorted.length; i++) {
    const prev = sorted[i - 1];
    const curr = sorted[i];
    if (prev.id && curr.id) {
      links.push({
        id: `link-${projectId}-${i}`,
        source: prev.id,
        target: curr.id,
        type: "e2s", // end-to-start
      });
    }
  }
  
  return links;
};

/**
 * Map multiple projects' actions to SVAR Gantt format
 */
export const mapProjectActionsToGantt = (
  projectsData: ProjectActionData[],
  projectColors: Map<string, string>
): GanttDataset => {
  const allTasks: GanttMappedTask[] = [];
  const allLinks: ILink[] = [];
  
  for (const { projectId, projectName, actions } of projectsData) {
    const projectColor = projectColors.get(projectId);
    
    const projectTasks = actions
      .filter((action) => action.id) // Ensure action has an ID
      .map((action) =>
        mapApiActionToGanttTask(action, projectId, projectName, projectColor)
      );
    
    allTasks.push(...projectTasks);
    
    // Create links for this project's tasks
    const projectLinks = createProjectLinks(projectTasks, projectId);
    allLinks.push(...projectLinks);
  }
  
  // Sort all tasks by start date for consistent display
  allTasks.sort((a, b) => {
    const aTime = a.start instanceof Date ? a.start.getTime() : 0;
    const bTime = b.start instanceof Date ? b.start.getTime() : 0;
    return aTime - bTime;
  });
  
  return { tasks: allTasks, links: allLinks };
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

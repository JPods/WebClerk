/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useCallback, useEffect, useRef, useState } from "react";
import { Actions, Projects } from "../../../api/userProfile";
import type { ApiKanbanItem } from "../kanban/kanbanDataMapper";
import type { ProjectOption, ProjectPrefs } from "./GanttProjectSelector";
import { getProjectColor } from "./GanttProjectSelector";
import {
  GanttDataset,
  GanttMapOptions,
  GanttMappedTask,
  ProjectActionData,
  mapProjectActionsToGantt,
} from "./ganttDataMapper";

// Batch size for concurrent API requests
const MAX_CONCURRENT_REQUESTS = 3;

// Auto-refresh interval: 5 minutes
export const AUTO_REFRESH_INTERVAL_MS = 5 * 60 * 1000;

export interface UseGanttDataOptions {
  selectedProjectIds: string[];
  enabled?: boolean;
  autoRefresh?: boolean;
  isModalOpen?: boolean;
  /** Whether to auto-sort tasks by start date (default: true) */
  sortByDate?: boolean;
  /** Custom task order (task IDs) - used when sortByDate is false */
  customTaskOrder?: string[];
}

export interface UseGanttDataResult {
  // Project data
  projects: ProjectOption[];
  isLoadingProjects: boolean;
  projectsError: string | null;
  
  // Actions/Tasks data
  ganttData: GanttDataset;
  isLoadingActions: boolean;
  actionsError: string | null;
  
  // Refresh controls
  lastRefreshTime: Date | null;
  isRefreshing: boolean;
  refetchProjects: () => Promise<void>;
  refetchActions: () => Promise<void>;
  refetchAll: () => Promise<void>;
  
  // Optimistic updates
  updateTaskLocally: (taskId: string | number, updates: { start?: Date; end?: Date; progress?: number }) => void;
  
  // Task reordering
  reorderTaskLocally: (fromIndex: number, toIndex: number) => void;
  getTaskOrder: () => string[];
}

// Type guard for checking if response is valid
const isValidResponse = (response: unknown): response is { data: unknown } => {
  return (
    response !== null &&
    typeof response === "object" &&
    "data" in response
  );
};

// Extract records array from API response
// Handles axios response: { data: { status, data: { results: [...] } } }
// Or direct API response: { status, data: { results: [...] } }
const extractRecordsFromResponse = (response: unknown): Record<string, unknown>[] => {
  console.log('[useGanttData] extractRecordsFromResponse input:', response);
  
  if (!isValidResponse(response)) {
    console.log('[useGanttData] Response is not valid (no data property)');
    return [];
  }
  
  let payload = response.data;
  console.log('[useGanttData] Initial payload:', payload);
  
  // Handle axios wrapper: response.data is the API response body
  // API response body has shape: { status, data: { results: [...] } }
  if (payload && typeof payload === "object" && "data" in payload) {
    const apiBody = payload as Record<string, unknown>;
    // Check if this is the API response wrapper with status field
    if ("status" in apiBody && apiBody.data) {
      payload = apiBody.data;
      console.log('[useGanttData] Unwrapped API body, payload now:', payload);
    }
  }
  
  if (Array.isArray(payload)) {
    return payload.filter(
      (item): item is Record<string, unknown> =>
        item !== null && typeof item === "object"
    );
  }
  
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    
    // Check common nested array keys
    for (const key of ["results", "items", "data", "records"]) {
      if (Array.isArray(obj[key])) {
        return (obj[key] as unknown[]).filter(
          (item): item is Record<string, unknown> =>
            item !== null && typeof item === "object"
        );
      }
    }
  }
  
  return [];
};

// Parse project from API record
const parseProjectOption = (record: Record<string, unknown>): ProjectOption | null => {
  const id = record.id ?? record.pk ?? record.uuid;
  if (id === null || id === undefined) return null;
  
  const idStr = String(id);
  const name = typeof record.name === "string" ? record.name : undefined;
  const slug = typeof record.slug === "string" ? record.slug : undefined;
  const intent = typeof record.intent === "string" ? record.intent : undefined;
  const ida = typeof record.ida === "string" ? record.ida : undefined;
  
  // Parse prefs.action.color for project-specific task colors
  let prefs: ProjectPrefs | undefined;
  if (record.prefs && typeof record.prefs === "object") {
    const prefsObj = record.prefs as Record<string, unknown>;
    if (prefsObj.action && typeof prefsObj.action === "object") {
      const actionPrefs = prefsObj.action as Record<string, unknown>;
      if (typeof actionPrefs.color === "string") {
        prefs = { action: { color: actionPrefs.color } };
      }
    }
  }
  
  // Since we already filter by is_active in the API call, accept all returned projects
  // Only filter out if explicitly marked as inactive
  const isExplicitlyInactive =
    record.is_active === false ||
    record.is_active === "false" ||
    record.is_active === 0 ||
    record.active === false;
  
  if (isExplicitlyInactive) return null;

  // Parse id_parent for parent-child project hierarchy
  const rawParent = record.id_parent ?? record.parent_id ?? record.parent;
  const id_parent = rawParent != null ? rawParent : null;

  const category = typeof record.category === 'string' ? record.category : undefined;
  const dt_start = typeof record.dt_start === 'number' ? record.dt_start : undefined;
  const dt_end = typeof record.dt_end === 'number' ? record.dt_end : undefined;

  return {
    id: idStr,
    name: name || intent || `Project ${idStr}`,
    slug,
    intent,
    ida,
    prefs,
    id_parent: id_parent as string | number | null,
    category,
    dt_start,
    dt_end,
  };
};

// Batch array into chunks
const batchArray = <T,>(array: T[], size: number): T[][] => {
  const batches: T[][] = [];
  for (let i = 0; i < array.length; i += size) {
    batches.push(array.slice(i, i + size));
  }
  return batches;
};

export const useGanttData = ({
  selectedProjectIds,
  enabled = true,
  autoRefresh = true,
  isModalOpen = false,
  sortByDate = true,
  customTaskOrder,
}: UseGanttDataOptions): UseGanttDataResult => {
  // Project state
  const [projects, setProjects] = useState<ProjectOption[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  
  // Actions state
  const [ganttData, setGanttData] = useState<GanttDataset>({ tasks: [], links: [] });
  const [isLoadingActions, setIsLoadingActions] = useState(false);
  const [actionsError, setActionsError] = useState<string | null>(null);
  
  // Refresh state
  const [lastRefreshTime, setLastRefreshTime] = useState<Date | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  
  // Refs for cleanup and stable references
  const autoRefreshTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isMountedRef = useRef(true);
  const projectsRef = useRef<ProjectOption[]>([]);
  const sortByDateRef = useRef(sortByDate);
  const customTaskOrderRef = useRef(customTaskOrder);
  
  // Keep refs in sync with props
  projectsRef.current = projects;
  sortByDateRef.current = sortByDate;
  customTaskOrderRef.current = customTaskOrder;
  
  // Fetch projects
  const refetchProjects = useCallback(async () => {
    console.log('[useGanttData] refetchProjects called, enabled:', enabled);
    if (!enabled) return;
    
    setIsLoadingProjects(true);
    setProjectsError(null);
    
    try {
      console.log('[useGanttData] Calling Projects API with is_active:true, limit:500');
      const response = await Projects({ is_active: true, limit: 500 });
      console.log('[useGanttData] Projects API response:', response);
      
      if (!isMountedRef.current) return;
      
      const records = extractRecordsFromResponse(response);
      console.log(`[useGanttData] Fetched ${records.length} projects from API`, 
        records.map(r => ({ id: r.id, name: r.name, is_active: r.is_active })));
      
      const projectOptions = records
        .map(parseProjectOption)
        .filter((p): p is ProjectOption => p !== null)
        .sort((a, b) => (a.name || "").localeCompare(b.name || ""));
      
      console.log(`[useGanttData] Parsed ${projectOptions.length} project options`);
      setProjects(projectOptions);
    } catch (error) {
      if (!isMountedRef.current) return;
      
      const message =
        error instanceof Error ? error.message : "Failed to fetch projects";
      setProjectsError(message);
      console.error("Failed to fetch projects:", error);
    } finally {
      if (isMountedRef.current) {
        setIsLoadingProjects(false);
      }
    }
  }, [enabled]);
  
  // Fetch actions for selected projects
  const refetchActions = useCallback(async () => {
    if (!enabled || selectedProjectIds.length === 0) {
      setGanttData({ tasks: [], links: [] });
      return;
    }
    
    setIsLoadingActions(true);
    setActionsError(null);
    
    try {
      const projectsDataArray: ProjectActionData[] = [];
      const projectBatches = batchArray(selectedProjectIds, MAX_CONCURRENT_REQUESTS);
      
      for (const batch of projectBatches) {
        const batchResults = await Promise.all(
          batch.map(async (projectId) => {
            try {
              console.log(`[useGanttData] Fetching actions for project_id=${projectId} (type: ${typeof projectId})`);
              const response = await Actions({
                project_id: projectId,
                is_active: true,
                limit: 500,
              });
              
              const records = extractRecordsFromResponse(response);
              console.log(`[useGanttData] Received ${records.length} actions for project_id=${projectId}`, 
                records.slice(0, 3).map(r => ({ id: r.id, project_id: r.project_id })));
              
              const actions = records as unknown as ApiKanbanItem[];
              
              // Find project name using ref to avoid dependency on projects state
              const project = projectsRef.current.find((p) => p.id === projectId);
              const projectName = project?.name || project?.intent || `Project ${projectId}`;
              const projectIda = project?.ida;
              
              return {
                projectId,
                projectName,
                projectIda,
                actions,
              };
            } catch (error) {
              console.error(`Failed to fetch actions for project ${projectId}:`, error);
              return {
                projectId,
                projectName: `Project ${projectId}`,
                actions: [],
              };
            }
          })
        );
        
        projectsDataArray.push(...batchResults);
      }
      
      if (!isMountedRef.current) return;
      
      // Build color map based on selection order, preferring project.prefs.action.color
      const colorMap = new Map<string, string>();
      selectedProjectIds.forEach((id) => {
        const project = projectsRef.current.find((p) => p.id === id);
        const prefsColor = project?.prefs?.action?.color;
        colorMap.set(id, getProjectColor(id, selectedProjectIds, prefsColor));
      });
      
      // Map to Gantt format with sorting options
      const mapOptions: GanttMapOptions = {
        sortByDate: sortByDateRef.current,
        customOrder: customTaskOrderRef.current,
      };
      const mappedData = mapProjectActionsToGantt(projectsDataArray, colorMap, mapOptions);
      
      setGanttData(mappedData);
      setLastRefreshTime(new Date());
      
      // Update project action counts
      setProjects((prev) =>
        prev.map((project) => {
          const projectData = projectsDataArray.find((p) => p.projectId === project.id);
          return projectData
            ? { ...project, actionCount: projectData.actions.length }
            : project;
        })
      );
    } catch (error) {
      if (!isMountedRef.current) return;
      
      const message =
        error instanceof Error ? error.message : "Failed to fetch actions";
      setActionsError(message);
      console.error("Failed to fetch actions:", error);
    } finally {
      if (isMountedRef.current) {
        setIsLoadingActions(false);
        setIsRefreshing(false);
      }
    }
  }, [enabled, selectedProjectIds]);
  
  // Refetch all data
  const refetchAll = useCallback(async () => {
    setIsRefreshing(true);
    await refetchProjects();
    await refetchActions();
  }, [refetchProjects, refetchActions]);
  
  // Initial fetch of projects
  useEffect(() => {
    isMountedRef.current = true;
    refetchProjects();
    
    return () => {
      isMountedRef.current = false;
    };
  }, [refetchProjects]);
  
  // Fetch actions when selection changes
  useEffect(() => {
    if (selectedProjectIds.length > 0) {
      refetchActions();
    }
  }, [selectedProjectIds, refetchActions]);
  
  // Auto-refresh timer
  useEffect(() => {
    // Clear existing timer
    if (autoRefreshTimerRef.current) {
      clearInterval(autoRefreshTimerRef.current);
      autoRefreshTimerRef.current = null;
    }
    
    // Don't start auto-refresh if disabled or modal is open
    if (!autoRefresh || isModalOpen || selectedProjectIds.length === 0) {
      return;
    }
    
    autoRefreshTimerRef.current = setInterval(() => {
      console.log("Auto-refreshing Gantt data...");
      refetchActions();
    }, AUTO_REFRESH_INTERVAL_MS);
    
    return () => {
      if (autoRefreshTimerRef.current) {
        clearInterval(autoRefreshTimerRef.current);
        autoRefreshTimerRef.current = null;
      }
    };
  }, [autoRefresh, isModalOpen, selectedProjectIds.length, refetchActions]);
  
  // Optimistically update a task's dates in local state (for drag-and-drop)
  const updateTaskLocally = useCallback((
    taskId: string | number,
    updates: { start?: Date; end?: Date; progress?: number }
  ) => {
    setGanttData((prev) => ({
      ...prev,
      tasks: prev.tasks.map((task) => {
        if (String(task.id) === String(taskId)) {
          const updatedTask = { ...task };
          if (updates.start !== undefined) {
            updatedTask.start = updates.start;
          }
          if (updates.end !== undefined) {
            updatedTask.end = updates.end;
          }
          if (updates.progress !== undefined) {
            updatedTask.progress = updates.progress;
          }
          return updatedTask;
        }
        return task;
      }),
    }));
  }, []);
  
  // Reorder task in the local task list (drag-and-drop support)
  const reorderTaskLocally = useCallback((fromIndex: number, toIndex: number) => {
    setGanttData((prev) => {
      if (fromIndex < 0 || fromIndex >= prev.tasks.length ||
          toIndex < 0 || toIndex >= prev.tasks.length ||
          fromIndex === toIndex) {
        return prev;
      }
      
      const newTasks = [...prev.tasks];
      const [movedTask] = newTasks.splice(fromIndex, 1);
      newTasks.splice(toIndex, 0, movedTask);
      
      return { ...prev, tasks: newTasks };
    });
  }, []);
  
  // Get current task order as array of IDs
  const getTaskOrder = useCallback((): string[] => {
    return ganttData.tasks.map((task) => String(task.id));
  }, [ganttData.tasks]);
  
  return {
    projects,
    isLoadingProjects,
    projectsError,
    ganttData,
    isLoadingActions,
    actionsError,
    lastRefreshTime,
    isRefreshing,
    refetchProjects,
    refetchActions,
    refetchAll,
    updateTaskLocally,
    reorderTaskLocally,
    getTaskOrder,
  };
};

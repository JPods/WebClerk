import { useCallback, useEffect, useRef, useState } from "react";
import { Actions, Projects } from "../../../api/userProfile";
import type { ApiKanbanItem } from "../kanban/kanbanDataMapper";
import type { ProjectOption } from "./GanttProjectSelector";
import { getProjectColor } from "./GanttProjectSelector";
import {
  GanttDataset,
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
const extractRecordsFromResponse = (response: unknown): Record<string, unknown>[] => {
  if (!isValidResponse(response)) return [];
  
  const payload = response.data;
  
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
  
  // Check if project is active
  const isActive =
    record.is_active === true ||
    record.is_active === "true" ||
    record.is_active === 1 ||
    record.active === true;
  
  if (!isActive) return null;
  
  return {
    id: idStr,
    name: name || intent || `Project ${idStr}`,
    slug,
    intent,
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
  
  // Refs for cleanup
  const autoRefreshTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isMountedRef = useRef(true);
  
  // Fetch projects
  const refetchProjects = useCallback(async () => {
    if (!enabled) return;
    
    setIsLoadingProjects(true);
    setProjectsError(null);
    
    try {
      const response = await Projects({ is_active: true, limit: 500 });
      
      if (!isMountedRef.current) return;
      
      const records = extractRecordsFromResponse(response);
      const projectOptions = records
        .map(parseProjectOption)
        .filter((p): p is ProjectOption => p !== null)
        .sort((a, b) => (a.name || "").localeCompare(b.name || ""));
      
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
              const response = await Actions({
                project_id: projectId,
                is_active: true,
                limit: 500,
              });
              
              const records = extractRecordsFromResponse(response);
              const actions = records as unknown as ApiKanbanItem[];
              
              // Find project name
              const project = projects.find((p) => p.id === projectId);
              const projectName = project?.name || project?.intent || `Project ${projectId}`;
              
              return {
                projectId,
                projectName,
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
      
      // Build color map based on selection order
      const colorMap = new Map<string, string>();
      selectedProjectIds.forEach((id) => {
        colorMap.set(id, getProjectColor(id, selectedProjectIds));
      });
      
      // Map to Gantt format
      const mappedData = mapProjectActionsToGantt(projectsDataArray, colorMap);
      
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
  }, [enabled, selectedProjectIds, projects]);
  
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
    refetchActions();
  }, [refetchActions]);
  
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
  };
};

export default useGanttData;

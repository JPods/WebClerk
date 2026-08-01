/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * UnifiedGantt - Core Gantt chart component
 * 
 * Supports both single-project and multi-project modes.
 * Can be embedded in other pages or used standalone.
 * 
 * TODO: Type cleanup needed - this file uses patterns from the legacy
 * MultiProjectGanttPage that have evolved out of sync with current type
 * definitions. See kanban/type/kanban.ts and kanban/taskFormTypes.ts.
 */
// @ts-nocheck - Temporary: types need alignment with current definitions

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { format as dateFnsFormat } from "date-fns";
import { Gantt, Willow } from "@svar-ui/react-gantt";
import type { IApi, IColumnConfig, ITask } from "@svar-ui/react-gantt";
import "@svar-ui/react-gantt/all.css";
import KanbanTaskModal from "../kanban/KanbanTaskModal";
import type { TaskFormEditableField, TaskFormState } from "../kanban/taskFormTypes";
import { patchAction } from "../../../api/userProfile";
import { saveRecord, getRecord } from "../../../api/wcapi";
import { createEmptyBoardData } from "../kanban/kanbanDataMapper";
import type { BoardData, KanbanTask, TaskPriority } from "../kanban/type/kanban";
import {
  DEFAULT_LANGUAGE_ORDER,
  DEFAULT_DIFFICULTY,
  DEFAULT_PROGRESS,
  DIFFICULTY_OPTIONS,
  FALLBACK_COLUMN_ID,
  PRIORITY_TO_VALUE,
  PROGRESS_OPTIONS,
  createInitialTaskFormState,
  createTranslationEntry,
  createTranslationEntriesFromTask,
  extendNumericOptionStrings,
  getLanguageLabel,
  normalizeIncomingDateValue,
  normalizeLanguageCode,
  normalizeNumericSelectValue,
  priorityOptions,
  toTimestampMilliseconds,
  updateTaskFormState,
} from "../shared/taskFormUtils";

import { GanttProjectSelector, getProjectColor } from "./GanttProjectSelector";
import { useGanttData, AUTO_REFRESH_INTERVAL_MS } from "./useGanttData";
import type { GanttMappedTask } from "./ganttDataMapper";
import { getGanttDateRange } from "./ganttDataMapper";
import { GanttTaskTemplate, setGanttCriticalPathHighlight, setGanttAssigneeFilter, setGanttOnOpenDetail } from "./GanttTaskTemplate";
import { ActionFloatingWindow } from "../../core/models/action/pages/ActionFloatingWindow";
import { DualScrollbar } from "../../../components/common/DualScrollbar";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

// =============================================================================
// Types
// =============================================================================

export interface UnifiedGanttProps {
  /** Single project mode - provide ID to show only this project */
  projectId?: string;
  
  /** Multi-project mode - initial selection of project IDs */
  initialProjectIds?: string[];
  
  /** Show the project selector sidebar (default: true, false if projectId provided) */
  showSelector?: boolean;
  
  /** Compact mode with reduced padding */
  compact?: boolean;
  
  /** Additional CSS classes */
  className?: string;
  
  /** Enable auto-refresh (default: true) */
  autoRefresh?: boolean;
  
  /** Callback when a task is clicked */
  onTaskClick?: (task: GanttMappedTask) => void;
}

// =============================================================================
// Constants
// =============================================================================

const ganttDateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
});

const formatDate = (value?: Date) => (value ? ganttDateFormatter.format(value) : "-");

// SVAR template signature: (value: string, task: ITask, column: IColumnConfig)
// The task with all custom properties is in the 2nd argument

// =============================================================================
// Project-level Gantt settings — stored in project.metadata.kanban.settings[]
// =============================================================================

interface GanttSettingsSnapshot {
  color: string;
  font_scale: number;
  cp_highlight: boolean;
  period: string;
  text_overflow: boolean;
  list_collapsed: boolean;
  assignee_filter: string | null;
  use_count: number;
  dt_last_used: number;
}

/** Load settings: admin default_view first, then most-used from settings[], then system defaults */
function loadProjectGanttSettings(projectMetadata: any): GanttSettingsSnapshot | null {
  try {
    // Admin-pinned default view takes priority
    const defaultView = projectMetadata?.kanban?.default_view;
    if (defaultView && typeof defaultView === 'object') {
      return { ...defaultView, use_count: 0, dt_last_used: 0 } as GanttSettingsSnapshot;
    }
    // Fall back to most frequently used
    const settings = projectMetadata?.kanban?.settings;
    if (Array.isArray(settings) && settings.length > 0) {
      return [...settings].sort((a, b) => (b.use_count || 0) - (a.use_count || 0))[0];
    }
  } catch {}
  return null;
}

/** Save current settings to project metadata. Dedup, cap at 5, track frequency. */
async function saveProjectGanttSettings(
  projectId: string,
  current: Omit<GanttSettingsSnapshot, 'use_count' | 'dt_last_used'>,
  existingMetadata: any,
): Promise<void> {
  const meta = { ...(existingMetadata || {}) };
  if (!meta.kanban) meta.kanban = {};
  if (!Array.isArray(meta.kanban.settings)) meta.kanban.settings = [];

  const settings: GanttSettingsSnapshot[] = meta.kanban.settings;
  const now = Date.now();

  // Check if this exact config already exists
  const match = settings.findIndex(s =>
    s.color === current.color &&
    s.font_scale === current.font_scale &&
    s.cp_highlight === current.cp_highlight &&
    s.period === current.period &&
    s.text_overflow === current.text_overflow &&
    s.list_collapsed === current.list_collapsed &&
    s.assignee_filter === current.assignee_filter
  );

  if (match >= 0) {
    settings[match].use_count = (settings[match].use_count || 0) + 1;
    settings[match].dt_last_used = now;
  } else {
    settings.push({ ...current, use_count: 1, dt_last_used: now });
    // Cap at 5 — drop least used
    if (settings.length > 5) {
      settings.sort((a, b) => (b.use_count || 0) - (a.use_count || 0));
      settings.length = 5;
    }
  }

  meta.kanban.settings = settings;

  try {
    const wcapi = await import("../../../api/wcapi");
    await wcapi.saveRecord("project", {
      model_name: "project",
      id: projectId,
      metadata: { mode: "update", value: meta },
    });
  } catch (e) {
    console.warn("[Gantt] Failed to save project settings:", e);
  }
}

// Reorder column for manual task ordering (shown when auto-sort is disabled)
// Uses a global event emitter pattern since SVAR templates can't directly call React state setters
let _reorderCallback: ((taskId: string, direction: 'up' | 'down') => void) | null = null;

const createReorderColumn = (): IColumnConfig => ({
  id: "reorder",
  header: "#",
  width: 55,
  align: "center",
  template: (_value: unknown, task: GanttMappedTask, _column: IColumnConfig) => {
    const taskId = String(task?.id || "");
    // Render up/down arrow buttons as HTML
    return `
      <div style="display:flex;align-items:center;justify-content:center;gap:2px;">
        <button 
          onclick="window.__ganttMoveTask?.('${taskId}', 'up')"
          style="border:none;background:transparent;cursor:pointer;padding:2px;color:#6b7280;line-height:1;"
          title="Move up"
        >▲</button>
        <button 
          onclick="window.__ganttMoveTask?.('${taskId}', 'down')"
          style="border:none;background:transparent;cursor:pointer;padding:2px;color:#6b7280;line-height:1;"
          title="Move down"
        >▼</button>
      </div>
    `;
  },
});

// Factory function to create columns (taskLookup no longer needed since task is in arg[1])
const createGanttColumns = (_taskLookup: Map<string, GanttMappedTask>, includeReorder: boolean = false): IColumnConfig[] => {
  const columns: IColumnConfig[] = [];
  
  // Add reorder column first if enabled
  if (includeReorder) {
    columns.push(createReorderColumn());
  }
  
  columns.push(
  {
    id: "taskIda",
    header: "ida",
    width: 60,
    align: "center",
    template: (_value: unknown, task: GanttMappedTask) => task?.taskIda || "-",
  },
  {
    id: "projectIda",
    header: "project_ida",
    width: 75,
    align: "center",
    template: (_value: unknown, task: GanttMappedTask) => task?.projectIda || "-",
  },
  {
    id: "start",
    header: "dt_start",
    width: 85,
    align: "center",
    template: (_value: unknown, task: GanttMappedTask) => {
      const startDate = task?.start;
      if (startDate instanceof Date) {
        return formatDate(startDate);
      }
      if (typeof startDate === "string") {
        return formatDate(new Date(startDate));
      }
      return "-";
    },
  },
  {
    id: "duration",
    header: "duration",
    width: 50,
    align: "center",
    template: (_value: unknown, task: GanttMappedTask) => {
      const d = task?.duration;
      if (typeof d === "number" && d > 0) {
        return `${d}d`;
      }
      return "-";
    },
  },
  {
    id: "progress",
    header: "percent_complete",
    width: 95,
    align: "center",
    template: (_value: unknown, task: GanttMappedTask) => {
      const pct = task?.percentComplete ?? task?.progress ?? 0;
      return `${pct}%`;
    },
  },
  {
    id: "slack",
    header: "slack",
    width: 55,
    align: "center",
    template: (_value: unknown, task: GanttMappedTask) => {
      const slack = task?.slack;
      if (typeof slack !== "number") return "-";
      if (slack === 0) return `<span style="color:#dc2626;font-weight:600">0d</span>`;
      return `${slack}d`;
    },
  },
  {
    id: "baseline",
    header: "dt_start_original",
    width: 100,
    align: "center",
    template: (_value: unknown, task: GanttMappedTask) => {
      // Show variance from original (positive = delayed, negative = ahead)
      if (!task?.dtStartOriginal || !task?.start) return "-";
      const originalMs = task.dtStartOriginal instanceof Date ? task.dtStartOriginal.getTime() : 0;
      const actualMs = task.start instanceof Date ? task.start.getTime() : 0;
      if (!originalMs || !actualMs) return "-";
      const varianceDays = Math.round((actualMs - originalMs) / (1000 * 60 * 60 * 24));
      if (varianceDays === 0) return `<span style="color:#059669">±0</span>`;
      if (varianceDays > 0) return `<span style="color:#dc2626;font-weight:600">+${varianceDays}d</span>`;
      return `<span style="color:#059669">${varianceDays}d</span>`;
    },
  });
  
  return columns;
};

// Factory for single-project mode (hides project column)
const createGanttColumnsSingleProject = (taskLookup: Map<string, GanttMappedTask>, includeReorder: boolean = false): IColumnConfig[] => 
  createGanttColumns(taskLookup, includeReorder).filter((col) => col.id !== "projectIda");

type ScalePresetKey = "day" | "week" | "month" | "quarter";
type ScaleConfig = { unit: string; step: number; format: (date: Date) => string };

const scalePresets: Record<ScalePresetKey, ScaleConfig[]> = {
  day: [
    { unit: "month", step: 1, format: (d: Date) => dateFnsFormat(d, "MMMM yyyy") },
    { unit: "day", step: 1, format: (d: Date) => dateFnsFormat(d, "EEE d") },
  ],
  week: [
    { unit: "month", step: 1, format: (d: Date) => dateFnsFormat(d, "MMMM yyyy") },
    { unit: "day", step: 1, format: (d: Date) => dateFnsFormat(d, "d") },
  ],
  month: [
    { unit: "month", step: 1, format: (d: Date) => dateFnsFormat(d, "MMMM yyyy") },
    { unit: "week", step: 1, format: (d: Date) => dateFnsFormat(d, "d") },
  ],
  quarter: [
    { unit: "month", step: 12, format: (d: Date) => dateFnsFormat(d, "yyyy") },
    { unit: "month", step: 1, format: (d: Date) => dateFnsFormat(d, "MMM") },
  ],
};

const scaleButtons: Array<{ id: ScalePresetKey; label: string }> = [
  { id: "day", label: "Day" },
  { id: "week", label: "Week" },
  { id: "month", label: "Month" },
  { id: "quarter", label: "Quarter" },
];

const GANTT_COLOR_EVENT_TAG = "gantt-project-colors";

// =============================================================================
// Utilities
// =============================================================================

const parseHexColor = (color: string) => {
  const hex = color.startsWith("#") ? color.slice(1) : color;
  if (!/^[0-9a-fA-F]{6}$/.test(hex)) return null;
  return {
    r: parseInt(hex.slice(0, 2), 16),
    g: parseInt(hex.slice(2, 4), 16),
    b: parseInt(hex.slice(4, 6), 16),
  };
};

const getRelativeLuminance = ({ r, g, b }: { r: number; g: number; b: number }): number => {
  const normalizeChannel = (value: number) => {
    const channel = value / 255;
    return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * normalizeChannel(r) + 0.7152 * normalizeChannel(g) + 0.0722 * normalizeChannel(b);
};

const pickReadableTextColor = (background: string): string => {
  const channels = parseHexColor(background);
  if (!channels) return "#0f172a";
  return getRelativeLuminance(channels) > 0.45 ? "#0f172a" : "#ffffff";
};

const combineClassNames = (...classes: Array<string | false | null | undefined>) =>
  classes.filter(Boolean).join(" ");

const toProgressPercentage = (value?: number | null): number => {
  if (typeof value !== "number" || Number.isNaN(value)) return 0;
  if (value >= 0 && value <= 1) return Math.round(value * 100);
  return Math.round(Math.max(0, Math.min(100, value)));
};

const padTwoDigits = (value: number) => value.toString().padStart(2, "0");

const formatDateTimeLocal = (date: Date): string => {
  const year = date.getFullYear();
  const month = padTwoDigits(date.getMonth() + 1);
  const day = padTwoDigits(date.getDate());
  const hours = padTwoDigits(date.getHours());
  const minutes = padTwoDigits(date.getMinutes());
  return `${year}-${month}-${day}T${hours}:${minutes}`;
};

const formatLastRefresh = (date: Date | null): string => {
  if (!date) return "Never";
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  
  if (diffSecs < 10) return "Just now";
  if (diffSecs < 60) return `${diffSecs}s ago`;
  if (diffMins < 60) return `${diffMins}m ago`;
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
};

type TaskColorInfo = {
  color: string;
  textColor: string;
  type?: ITask["type"];
};

// =============================================================================
// Component
// =============================================================================

export const UnifiedGantt: React.FC<UnifiedGanttProps> = ({
  projectId,
  initialProjectIds = [],
  showSelector: showSelectorProp,
  compact = false,
  className,
  autoRefresh = true,
  onTaskClick,
}) => {
  const navigate = useNavigate();

  // Determine if we should show selector
  const isSingleProjectMode = Boolean(projectId);
  const showSelector = showSelectorProp ?? !isSingleProjectMode;

  // Project metadata — loaded once for project-level settings
  const [projectMetadata, setProjectMetadata] = useState<any>(null);
  const projectSettingsApplied = useRef(false);

  // Load project metadata for settings
  useEffect(() => {
    if (!projectId) return;
    projectSettingsApplied.current = false;
    getRecord("project", projectId).then((resp: any) => {
      const meta = resp?.data?.metadata || resp?.metadata || null;
      setProjectMetadata(meta);
    }).catch(() => {});
  }, [projectId]);

  // Sidebar collapsed state (collapsed by default)
  const [selectorCollapsed, setSelectorCollapsed] = useState(true);
  
  // Task list (grid) collapsed state - shows only minimal columns when collapsed
  // Default collapsed: the bars carry the value; grid expands on demand
  const [taskListCollapsed, setTaskListCollapsed] = useState(() => {
    try {
      const stored = localStorage.getItem('wc3_wcui_prefs');
      if (stored) {
        const prefs = JSON.parse(stored);
        if (typeof prefs.gantt_list_collapsed === 'boolean') return prefs.gantt_list_collapsed;
      }
    } catch {}
    return true;
  });
  
  // Sorting state - auto-sort by start date toggle
  const [autoSortByDate, setAutoSortByDate] = useState(true);
  
  // Custom task order (used when autoSortByDate is false)
  const [customTaskOrder, setCustomTaskOrder] = useState<string[]>([]);
  
  // Project selection state
  const [selectedProjectIds, setSelectedProjectIds] = useState<string[]>(() => {
    if (projectId) return [projectId];
    return initialProjectIds;
  });
  
  // Sync with projectId prop changes
  useEffect(() => {
    if (projectId) {
      setSelectedProjectIds([projectId]);
    }
  }, [projectId]);
  
  // Refs for task order saving (placed before useGanttData since they don't depend on it)
  const saveOrderTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isSavingOrderRef = useRef(false);
  const hasLoadedOrderRef = useRef<string | null>(null); // Track which project's order we've loaded
  
  // Modal state (placed here to be available for useGanttData)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editAssigneeUIMode, setEditAssigneeUIMode] = useState<'dropdown' | 'chips'>('dropdown');
  
  // Data fetching
  const {
    projects,
    isLoadingProjects,
    projectsError,
    ganttData,
    isLoadingActions,
    actionsError,
    lastRefreshTime,
    isRefreshing,
    refetchActions,
    refetchAll,
    updateTaskLocally,
    reorderTaskLocally,
    getTaskOrder,
  } = useGanttData({
    selectedProjectIds,
    enabled: true,
    autoRefresh: autoRefresh,
    isModalOpen: isEditModalOpen,
    sortByDate: autoSortByDate,
    customTaskOrder: autoSortByDate ? undefined : customTaskOrder,
  });
  
  // Save task order to project.refs.links.actions
  // Uses debouncing to avoid excessive API calls during rapid reordering
  const saveTaskOrderToProject = useCallback(async (tasks: GanttMappedTask[]) => {
    // Only save in single-project mode
    if (!projectId || selectedProjectIds.length !== 1) {
      console.log('[UnifiedGantt] Skipping save: not in single-project mode');
      return;
    }
    
    // Build the action order array in the required format
    const actionOrder = tasks.map((task) => ({
      id: Number(task.id),
      "action.en": task.text || task.title || "",
    }));
    
    try {
      isSavingOrderRef.current = true;
      const payload = {
        id: Number(projectId),
        refs: {
          links: {
            actions: actionOrder,
          },
        },
      };
      
      console.log('[UnifiedGantt] Saving task order to project:', payload);
      await saveRecord("project", payload);
      console.log('[UnifiedGantt] Task order saved successfully');
    } catch (error) {
      console.error('[UnifiedGantt] Failed to save task order:', error);
    } finally {
      isSavingOrderRef.current = false;
    }
  }, [projectId, selectedProjectIds]);
  
  // Debounced save function
  const debouncedSaveOrder = useCallback((tasks: GanttMappedTask[]) => {
    // Clear any pending save
    if (saveOrderTimeoutRef.current) {
      clearTimeout(saveOrderTimeoutRef.current);
    }
    
    // Schedule new save after 500ms delay
    saveOrderTimeoutRef.current = setTimeout(() => {
      saveTaskOrderToProject(tasks);
    }, 500);
  }, [saveTaskOrderToProject]);
  
  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (saveOrderTimeoutRef.current) {
        clearTimeout(saveOrderTimeoutRef.current);
      }
    };
  }, []);
  
  // Setup global handler for task reorder buttons
  // This is needed because SVAR templates render HTML strings, not React components
  useEffect(() => {
    const handleMoveTask = (taskId: string, direction: 'up' | 'down') => {
      const currentTasks = ganttData.tasks;
      const taskIndex = currentTasks.findIndex((t) => String(t.id) === taskId);
      if (taskIndex === -1) return;
      
      const newIndex = direction === 'up' 
        ? Math.max(0, taskIndex - 1)
        : Math.min(currentTasks.length - 1, taskIndex + 1);
      
      if (newIndex !== taskIndex) {
        reorderTaskLocally(taskIndex, newIndex);
        // Update custom order state
        setCustomTaskOrder(getTaskOrder());
        
        // Save order to project (debounced)
        // Calculate the new tasks array for saving
        const newTasks = [...currentTasks];
        const [movedTask] = newTasks.splice(taskIndex, 1);
        newTasks.splice(newIndex, 0, movedTask);
        debouncedSaveOrder(newTasks);
      }
    };
    
    // Attach to window for HTML button onclick access
    (window as any).__ganttMoveTask = handleMoveTask;
    
    return () => {
      delete (window as any).__ganttMoveTask;
    };
  }, [ganttData.tasks, reorderTaskLocally, getTaskOrder, debouncedSaveOrder]);
  
  // Load saved task order from project.refs.links.actions on mount / project change
  useEffect(() => {
    // Only load in single-project mode
    if (!projectId || selectedProjectIds.length !== 1) {
      return;
    }
    
    // Avoid re-loading for the same project
    if (hasLoadedOrderRef.current === projectId) {
      return;
    }
    
    const loadSavedTaskOrder = async () => {
      try {
        console.log('[UnifiedGantt] Loading saved task order for project:', projectId);
        const project = await getRecord("project", Number(projectId));
        
        if (!project) {
          console.log('[UnifiedGantt] Project not found');
          return;
        }
        
        const savedActions = project?.refs?.links?.actions;
        if (Array.isArray(savedActions) && savedActions.length > 0) {
          // Extract IDs in order from saved actions
          const savedOrder = savedActions
            .filter((a: any) => a && typeof a.id === 'number')
            .map((a: any) => String(a.id));
          
          if (savedOrder.length > 0) {
            console.log('[UnifiedGantt] Found saved task order:', savedOrder);
            setCustomTaskOrder(savedOrder);
            setAutoSortByDate(false); // Disable auto-sort to use custom order
            hasLoadedOrderRef.current = projectId;
          }
        } else {
          console.log('[UnifiedGantt] No saved task order found');
          hasLoadedOrderRef.current = projectId;
        }
      } catch (error) {
        console.error('[UnifiedGantt] Failed to load saved task order:', error);
        hasLoadedOrderRef.current = projectId; // Mark as loaded to avoid retries
      }
    };
    
    loadSavedTaskOrder();
  }, [projectId, selectedProjectIds]);
  
  // Gantt display state
  const [scalePreset, setScalePreset] = useState<ScalePresetKey>(() => {
    try {
      const stored = localStorage.getItem('wc3_wcui_prefs');
      if (stored) {
        const prefs = JSON.parse(stored);
        if (prefs.gantt_scale) return prefs.gantt_scale as ScalePresetKey;
      }
    } catch {}
    return "month";
  });
  const [colorMode, setColorMode] = useState<'project' | 'priority' | 'status' | 'assigned' | 'difficulty'>('priority');
  const [ganttKey, setGanttKey] = useState(0);
  const [ganttFontScale, setGanttFontScale] = useState(() => {
    try {
      const stored = localStorage.getItem('wc3_wcui_prefs');
      if (stored) {
        const prefs = JSON.parse(stored);
        if (typeof prefs.gantt_font_scale === 'number') return prefs.gantt_font_scale;
      }
    } catch {}
    return 0;
  });
  const [textOverflow, setTextOverflow] = useState(() => {
    try {
      const stored = localStorage.getItem('wc3_wcui_prefs');
      if (stored) {
        const prefs = JSON.parse(stored);
        if (typeof prefs.gantt_show_full_text === 'boolean') return prefs.gantt_show_full_text;
      }
    } catch {}
    return false;
  });
  const [criticalPathHighlight, setCriticalPathHighlight] = useState(false);
  const [assigneeFilter, setAssigneeFilter] = useState<string | null>(null);
  const [showAdminTools, setShowAdminTools] = useState(false);
  const [detailActionId, setDetailActionId] = useState<string | null>(null);

  // Unique assignees from current tasks for filter dropdown
  const uniqueAssignees = useMemo(() => {
    const seen = new Map<string, string>(); // id -> name
    ganttData.tasks.forEach(task => {
      const mapped = task as GanttMappedTask;
      (mapped.assignedTo || []).forEach(a => {
        const id = String(a.id);
        if (!seen.has(id)) seen.set(id, a.name || `User ${id}`);
      });
    });
    return Array.from(seen.entries())
      .map(([id, name]) => ({ id, name }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [ganttData.tasks]);

  // Precompute sprint end dates for vertical boundary lines
  const sprintEndDates = useMemo(() => {
    const dates = new Set<string>();
    // Child projects (id_parent set) are sprints — use their deadlines
    const childProjectIds = new Set(
      projects.filter(p => p.id_parent != null).map(p => p.id)
    );
    // Also match any task with "sprint" in the name
    for (const task of ganttData.tasks) {
      const mapped = task as GanttMappedTask;
      const isSprint = childProjectIds.has(mapped.projectId) ||
        (mapped.text?.toLowerCase().includes('sprint') && task.end instanceof Date);
      if (isSprint && task.end instanceof Date) {
        dates.add(`${task.end.getFullYear()}-${String(task.end.getMonth()+1).padStart(2,'0')}-${String(task.end.getDate()).padStart(2,'0')}`);
      }
    }
    return dates;
  }, [ganttData.tasks, projects]);

  // Apply project-level settings once metadata loads
  useEffect(() => {
    if (!projectMetadata || projectSettingsApplied.current) return;
    const ps = loadProjectGanttSettings(projectMetadata);
    if (!ps) return;
    projectSettingsApplied.current = true;
    if (ps.color) setColorMode(ps.color as any);
    if (typeof ps.font_scale === 'number') setGanttFontScale(ps.font_scale);
    if (typeof ps.cp_highlight === 'boolean') setCriticalPathHighlight(ps.cp_highlight);
    if (ps.period) setScalePreset(ps.period as ScalePresetKey);
    if (typeof ps.text_overflow === 'boolean') setTextOverflow(ps.text_overflow);
    if (typeof ps.list_collapsed === 'boolean') setTaskListCollapsed(ps.list_collapsed);
    if (ps.assignee_filter !== undefined) setAssigneeFilter(ps.assignee_filter);
  }, [projectMetadata]);

  // Auto-save settings to project when they change (debounced)
  const saveSettingsTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (!projectId || !projectSettingsApplied.current) return;
    if (saveSettingsTimeoutRef.current) clearTimeout(saveSettingsTimeoutRef.current);
    saveSettingsTimeoutRef.current = setTimeout(() => {
      saveProjectGanttSettings(projectId, {
        color: colorMode,
        font_scale: ganttFontScale,
        cp_highlight: criticalPathHighlight,
        period: scalePreset,
        text_overflow: textOverflow,
        list_collapsed: taskListCollapsed,
        assignee_filter: assigneeFilter,
      }, projectMetadata);
    }, 2000);
    return () => { if (saveSettingsTimeoutRef.current) clearTimeout(saveSettingsTimeoutRef.current); };
  }, [projectId, colorMode, ganttFontScale, criticalPathHighlight, scalePreset, textOverflow, taskListCollapsed, assigneeFilter, projectMetadata]);

  // Sync module-level flags for task template and force SVAR re-render
  useEffect(() => {
    setGanttCriticalPathHighlight(criticalPathHighlight);
    setGanttAssigneeFilter(assigneeFilter);
    setGanttOnOpenDetail((id: string) => setDetailActionId(id));
    setGanttKey(k => k + 1);
    return () => { setGanttOnOpenDetail(null); };
  }, [criticalPathHighlight, assigneeFilter]);

  const activeScales = scalePresets[scalePreset];

  // Calculate date range
  const dateRange = useMemo(() => {
    return getGanttDateRange(ganttData.tasks);
  }, [ganttData.tasks]);
  
  // Board state for task editing
  const [board] = useState<BoardData>(() => createEmptyBoardData());
  
  // Edit modal state
  const [editingTask, setEditingTask] = useState<KanbanTask | null>(null);
  const [editTaskState, setEditTaskState] = useState<TaskFormState>(() =>
    createInitialTaskFormState(FALLBACK_COLUMN_ID)
  );
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [editModalError, setEditModalError] = useState<string | null>(null);
  const [editLanguagePickerOpen, setEditLanguagePickerOpen] = useState(false);
  const [editLanguageSelection, setEditLanguageSelection] = useState("");
  const [editCustomLanguage, setEditCustomLanguage] = useState("");
  const [editLanguagePickerError, setEditLanguagePickerError] = useState<string | null>(null);

  // Link context menu state
  const [linkContextMenu, setLinkContextMenu] = useState<{
    x: number;
    y: number;
    linkId: string;
  } | null>(null);

  // Undo/Redo history stacks
  type HistoryEntry = { taskId: string; field: string; oldValue: unknown; newValue: unknown };
  const [undoStack, setUndoStack] = useState<HistoryEntry[]>([]);
  const [redoStack, setRedoStack] = useState<HistoryEntry[]>([]);
  
  // Helper to push to undo stack (called from task update handlers)
  const pushToUndoStack = useCallback((entry: HistoryEntry) => {
    setUndoStack((stack) => [...stack.slice(-49), entry]); // Keep last 50 entries
    setRedoStack([]); // Clear redo stack on new action
  }, []);
  
  // Refs
  const ganttContainerRef = useRef<HTMLDivElement | null>(null);
  const ganttApiRef = useRef<IApi | null>(null);
  const taskColorMapRef = useRef<Map<string, TaskColorInfo>>(new Map());
  // Ref to hold latest update handler for use in init callback
  const handleSvarUpdateTaskRef = useRef<((ev: { id: string | number; task: Partial<ITask> }) => Promise<boolean>) | null>(null);

  // Column options for KanbanTaskModal
  const columnOptions = useMemo(() => {
    return (board.column_order || [])
      .map((colId) => board.columns[colId])
      .filter((col): col is NonNullable<typeof col> => Boolean(col))
      .map((col) => ({ id: col.id, title: col.title }));
  }, [board.column_order, board.columns]);

  // Difficulty and progress options
  const editDifficultyOptions = useMemo(
    () => extendNumericOptionStrings(DIFFICULTY_OPTIONS, editTaskState.difficulty),
    [editTaskState.difficulty]
  );
  const editProgressOptions = useMemo(
    () => extendNumericOptionStrings(PROGRESS_OPTIONS, editTaskState.progress),
    [editTaskState.progress]
  );

  // Language options
  const languageOptions = useMemo(() => {
    return DEFAULT_LANGUAGE_ORDER.map((code) => ({
      value: code,
      label: getLanguageLabel(code),
    }));
  }, []);

  const availableEditLanguages = useMemo(() => {
    const usedCodes = new Set(editTaskState.translations.map((t) => normalizeLanguageCode(t.language)));
    return languageOptions.filter((opt) => !usedCodes.has(normalizeLanguageCode(opt.value)));
  }, [editTaskState.translations, languageOptions]);

  const editLanguagePickerState = useMemo(() => {
    return {
      isOpen: editLanguagePickerOpen,
      selection: editLanguageSelection,
      selectedValue: editLanguageSelection,
      customValue: editCustomLanguage,
      error: editLanguagePickerError,
    };
  }, [editLanguagePickerOpen, editLanguageSelection, editCustomLanguage, editLanguagePickerError]);

  // Color refresh logic
  const refreshTaskColorCache = useCallback(() => {
    const container = ganttContainerRef.current;
    if (!container) return;

    // SVAR Gantt uses CSS variables for colors, not direct style properties
    // We need to find task bar elements and set CSS custom properties on them
    const bars = container.querySelectorAll<HTMLElement>(".wx-bar");
    const newMap = new Map<string, TaskColorInfo>();

    bars.forEach((bar) => {
      // Try multiple ways to find task ID:
      // 1. Check the bar itself for data-id
      let taskId = bar.getAttribute("data-id");
      
      // 2. Check closest parent with data-id
      if (!taskId) {
        const closestWithId = bar.closest("[data-id]");
        if (closestWithId) {
          taskId = closestWithId.getAttribute("data-id");
        }
      }
      
      // 3. Walk up the DOM as fallback
      if (!taskId) {
        let parent = bar.parentElement;
        while (parent && parent !== container) {
          if (parent.hasAttribute("data-id")) {
            taskId = parent.getAttribute("data-id");
            break;
          }
          parent = parent.parentElement;
        }
      }
      
      if (!taskId) return;

      const task = ganttData.tasks.find((t) => String(t.id) === taskId);
      if (!task) return;

      // Color based on selected mode
      let color: string;
      const priorityColors: Record<string, string> = {
        low: '#e2e8f0', medium: '#93c5fd', high: '#f97316', critical: '#ef4444',
      };
      const statusColors: Record<string, string> = {
        open: '#94a3b8', in_progress: '#3b82f6', active: '#3b82f6',
        complete: '#22c55e', done: '#22c55e', on_hold: '#9ca3af',
        blocked: '#ef4444', cancelled: '#6b7280', draft: '#d1d5db',
      };
      const difficultyColors: Record<number, string> = {
        1: '#10b981', 2: '#a3e635', 3: '#f59e0b', 4: '#f97316', 5: '#ef4444',
      };
      const assignedColors = ['#3b82f6','#8b5cf6','#06b6d4','#d946ef','#84cc16','#eab308','#ec4899','#6366f1'];

      if (colorMode === 'priority') {
        const p = (task as GanttMappedTask).priority || 'medium';
        color = priorityColors[p] || priorityColors.medium;
      } else if (colorMode === 'status') {
        const s = ((task as GanttMappedTask).columnId || 'open').toLowerCase().replace(/\s+/g, '_');
        color = statusColors[s] || statusColors.open;
      } else if (colorMode === 'assigned') {
        const assigned = (task as GanttMappedTask).assignedTo?.[0];
        if (assigned) {
          const key = typeof assigned.id === 'string' ? parseInt(assigned.id, 10) : assigned.id;
          color = assignedColors[key % assignedColors.length];
        } else {
          color = '#94a3b8';
        }
      } else if (colorMode === 'difficulty') {
        const d = (task as any).difficulty || 3;
        color = difficultyColors[Math.min(5, Math.max(1, d))] || difficultyColors[3];
      } else {
        // project mode (original behavior)
        const project = projects.find((p) => String(p.id) === String(task.projectId));
        const prefsColor = project?.prefs?.action?.color;
        color = getProjectColor(String(task.projectId), selectedProjectIds, prefsColor);
      }
      const textColor = pickReadableTextColor(color);

      newMap.set(taskId, { color, textColor, type: task.type });

      // Apply SVAR CSS variables on the bar element
      bar.style.setProperty("--wx-gantt-task-color", color);
      bar.style.setProperty("--wx-gantt-task-fill-color", color);
      bar.style.setProperty("--wx-gantt-task-border-color", color);
      bar.style.setProperty("--wx-gantt-task-font-color", textColor);
      
      // Apply direct styles with !important to override SVAR defaults
      bar.style.setProperty("background-color", color, "important");
      bar.style.setProperty("border-color", color, "important");
      bar.style.setProperty("background", color, "important");
      
      // Also set as data attribute for CSS targeting
      bar.setAttribute("data-project-color", color);
      
      // Find and style progress bar elements (SVAR uses multiple class names)
      const progressSelectors = [".wx-progress", ".wx-progress-percent", ".wx-progress-wrapper .wx-progress-percent"];
      for (const selector of progressSelectors) {
        const progress = bar.querySelector<HTMLElement>(selector);
        if (progress) {
          progress.style.setProperty("background-color", color, "important");
          progress.style.opacity = "0.7";
        }
      }
      
      // Find and style text content elements
      const textSelectors = [".wx-content", ".wx-text"];
      for (const selector of textSelectors) {
        const textEl = bar.querySelector<HTMLElement>(selector);
        if (textEl) {
          textEl.style.setProperty("color", textColor, "important");
        }
      }
    });

    taskColorMapRef.current = newMap;
  }, [ganttData.tasks, selectedProjectIds, projects, colorMode]);

  const scheduleColorRefresh = useCallback(() => {
    // Multiple refresh attempts to catch SVAR's async rendering
    // Immediate refresh
    requestAnimationFrame(() => {
      refreshTaskColorCache();
    });
    // Quick follow-up
    setTimeout(() => {
      refreshTaskColorCache();
    }, 50);
    // Delayed refresh to catch any late renders
    setTimeout(() => {
      refreshTaskColorCache();
    }, 150);
    // Final catch-all
    setTimeout(() => {
      refreshTaskColorCache();
    }, 300);
  }, [refreshTaskColorCache]);

  // Derive form state from a task
  const deriveFormStateFromTask = useCallback(
    (task: KanbanTask): TaskFormState => {
      const taskColumn = Object.values(board.columns).find((column) => column?.task_ids?.includes(task.id));
      const normalizedStart = normalizeIncomingDateValue((task as any).dt_start);
      const normalizedDue = normalizeIncomingDateValue((task as any).dt_deadline);
      const shouldFallbackStart = !normalizedStart && !normalizedDue;
      const resolvedStartDate = shouldFallbackStart ? formatDateTimeLocal(new Date()) : normalizedStart;
      const resolvedDueDate = normalizedDue || "";
      const normalizedDifficulty = normalizeNumericSelectValue(
        task.difficulty ?? PRIORITY_TO_VALUE[task.priority],
        DEFAULT_DIFFICULTY
      );
      const normalizedProgressValue = toProgressPercentage(task.progress);
      const normalizedProgress = normalizeNumericSelectValue(normalizedProgressValue, DEFAULT_PROGRESS);

      return {
        translations: createTranslationEntriesFromTask(task),
        columnId: taskColumn?.id ?? task.status ?? FALLBACK_COLUMN_ID,
        priority: task.priority,
        dt_deadline: resolvedDueDate,
        dt_start: resolvedStartDate,
        dt_completed: "",
        dt_expected: resolvedDueDate,
        assignee: task.assignee || task.assigned_to?.[0]?.name || "",
        difficulty: String(normalizedDifficulty),
        progress: String(normalizedProgress),
        percent_complete: String(normalizedProgress),
      };
    },
    [board.columns]
  );

  // Task editing handlers
  const handleShowEditor = useCallback(
    ({ id }: { id: string | number }) => {
      const ganttTask = ganttData.tasks.find((t) => String(t.id) === String(id));
      if (!ganttTask) return;

      // Optional callback
      if (onTaskClick) {
        onTaskClick(ganttTask);
      }

      // Create a KanbanTask-like object
      const kanbanTask: KanbanTask = {
        id: String(ganttTask.id),
        title: ganttTask.text || "",
        description: ganttTask.details || "",
        priority: (ganttTask.priority as TaskPriority) || "medium",
        status: ganttTask.columnTitle || "Uncategorized",
        dt_deadline: ganttTask.end instanceof Date ? ganttTask.end.toISOString() : undefined,
        dt_start: ganttTask.start instanceof Date ? ganttTask.start.toISOString() : undefined,
        progress: toProgressPercentage(ganttTask.progress),
        assignee: ganttTask.assignee,
        tags: [],
        title_translations: { en: ganttTask.text || "" },
        description_translations: { en: ganttTask.details || "" },
        language_codes: ["en"],
      };

      setEditingTask(kanbanTask);
      setEditTaskState(deriveFormStateFromTask(kanbanTask));
      setEditModalError(null);
      setIsEditModalOpen(true);
    },
    [ganttData.tasks, deriveFormStateFromTask, onTaskClick]
  );

  // Double-click on grid row → open in side panel
  const handleOpenDetailPanel = useCallback(
    ({ id }: { id: string | number }) => {
      if (id) setDetailActionId(String(id));
    },
    []
  );

  const handleCloseEditModal = useCallback(() => {
    setIsEditModalOpen(false);
    setEditingTask(null);
    setEditModalError(null);
    setEditLanguagePickerOpen(false);
  }, []);

  const handleEditTaskChange = useCallback(
    (field: TaskFormEditableField, value: string) => {
      setEditTaskState((prev) => updateTaskFormState(prev, field, value));
    },
    []
  );

  const handleEditTranslationFieldChange = useCallback(
    (entryId: string, field: "language" | "title" | "description", value: string) => {
      setEditTaskState((prev) => ({
        ...prev,
        translations: prev.translations.map((entry) =>
          entry.id === entryId ? { ...entry, [field]: value } : entry
        ),
      }));
    },
    []
  );

  const handleRemoveEditTranslation = useCallback((entryId: string) => {
    setEditTaskState((prev) => ({
      ...prev,
      translations: prev.translations.filter((entry) => entry.id !== entryId),
    }));
  }, []);

  const handleEditLanguagePickerToggle = useCallback(() => {
    setEditLanguagePickerOpen((prev) => !prev);
    if (!editLanguagePickerOpen) {
      setEditLanguageSelection("");
      setEditCustomLanguage("");
      setEditLanguagePickerError(null);
    }
  }, [editLanguagePickerOpen]);

  const handleEditLanguageSelectionChange = useCallback((value: string) => {
    setEditLanguageSelection(value);
    setEditLanguagePickerError(null);
  }, []);

  const handleEditLanguageCustomChange = useCallback((value: string) => {
    setEditCustomLanguage(value);
    setEditLanguagePickerError(null);
  }, []);

  const handleEditLanguagePickerSubmit = useCallback(() => {
    const code = editLanguageSelection === "custom" ? editCustomLanguage.trim() : editLanguageSelection;
    if (!code) {
      setEditLanguagePickerError("Please select or enter a language code.");
      return;
    }
    const normalized = normalizeLanguageCode(code);
    const alreadyUsed = editTaskState.translations.some(
      (t) => normalizeLanguageCode(t.language) === normalized
    );
    if (alreadyUsed) {
      setEditLanguagePickerError("This language is already added.");
      return;
    }
    const newEntry = createTranslationEntry(code);
    setEditTaskState((prev) => ({
      ...prev,
      translations: [...prev.translations, newEntry],
    }));
    setEditLanguagePickerOpen(false);
    setEditLanguageSelection("");
    setEditCustomLanguage("");
    setEditLanguagePickerError(null);
  }, [editLanguageSelection, editCustomLanguage, editTaskState.translations]);

  const handleEditLanguagePickerCancel = useCallback(() => {
    setEditLanguagePickerOpen(false);
    setEditLanguageSelection("");
    setEditCustomLanguage("");
    setEditLanguagePickerError(null);
  }, []);

  const buildEditActionPayload = useCallback(
    (state: TaskFormState, baseTask: KanbanTask | null): { payload: Record<string, unknown> } | { error: string } => {
      if (!baseTask) {
        return { error: "No task selected for editing." };
      }

      const normalized = new Map<string, { title: string; description: string }>();

      state.translations.forEach((entry) => {
        const language = normalizeLanguageCode(entry.language);
        if (!language) return;
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

      const translationFields: Record<string, { mode: string; value: string | string[] }> = {};

      normalized.forEach((value, language) => {
        translationFields[`action.${language}`] = {
          mode: "update",
          value: value.title || "",
        };
        translationFields[`description.${language}`] = {
          mode: "update",
          value: value.description || "",
        };
      });

      translationFields.languages = {
        mode: "update",
        value: Array.from(normalized.keys()),
      };

      const column = board.columns[state.columnId] ?? board.columns[FALLBACK_COLUMN_ID];
      const assignedTo = state.assignee
        ? [{ name: state.assignee }]
        : baseTask.assigned_to?.map((assignment: any) => ({ name: assignment.name })) ?? [];

      const dueTimestamp = toTimestampMilliseconds(state.dt_deadline);
      const startTimestamp = toTimestampMilliseconds(state.dt_start);
      const resolvedProgress = Number(state.progress) || 0;

      const payloadItem: Record<string, unknown> = {
        model_name: "action",
        ...translationFields,
        kanban_column: {
          mode: "update",
          value: column?.title ?? "Uncategorized",
        },
        kanban_column_id: {
          mode: "update",
          value: column?.id ?? FALLBACK_COLUMN_ID,
        },
        priority: {
          mode: "update",
          value: PRIORITY_TO_VALUE[state.priority],
        },
        difficulty: {
          mode: "update",
          value: Number(state.difficulty) || PRIORITY_TO_VALUE[state.priority],
        },
        status: {
          mode: "update",
          value: baseTask.status ?? "In progress",
        },
        dt_deadline: {
          mode: "update",
          value: dueTimestamp,
        },
        dt_start: {
          mode: "update",
          value: startTimestamp,
        },
        assigned_to: {
          mode: "update",
          value: assignedTo,
        },
        progress: {
          mode: "update",
          value: resolvedProgress,
        },
        id: baseTask.id,
      };

      if (!state.assignee && assignedTo.length === 0) {
        delete payloadItem.assigned_to;
      }

      return { payload: payloadItem };
    },
    [board.columns]
  );

  const handleEditTaskSubmit = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      if (isSavingEdit || !editingTask) return;

      setIsSavingEdit(true);
      setEditModalError(null);

      const result = buildEditActionPayload(editTaskState, editingTask);
      if ("error" in result) {
        setEditModalError(result.error);
        setIsSavingEdit(false);
        return;
      }

      try {
        await patchAction(result.payload);
        await refetchActions();
        handleCloseEditModal();
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to save changes";
        setEditModalError(message);
        console.error("Failed to update task:", error);
      } finally {
        setIsSavingEdit(false);
      }
    },
    [isSavingEdit, editingTask, editTaskState, buildEditActionPayload, refetchActions, handleCloseEditModal]
  );

  const handleSvarUpdateTask = useCallback(
    async ({ id, task }: { id: string | number; task: Partial<ITask> }) => {
      console.log("[Gantt] handleSvarUpdateTask called (before checks)", { id, task });
      if (!id) return false;

      console.log("[Gantt] handleSvarUpdateTask proceeding", { id, task });

      try {
        // Find the original task to record old values for undo
        const originalTask = ganttData.tasks.find((t) => String(t.id) === String(id));
        
        const payload: Record<string, unknown> = {
          model_name: "action",
          id: String(id),
        };

        if (task.start instanceof Date) {
          const oldValue = originalTask?.start instanceof Date ? originalTask.start.getTime() : null;
          const newValue = task.start.getTime();
          payload["dt_start"] = { mode: "update", value: newValue };
          console.log("[Gantt] dt_start changed:", { oldValue, newValue });
          // Record for undo
          if (oldValue !== newValue) {
            pushToUndoStack({ taskId: String(id), field: "dt_start", oldValue, newValue });
          }
        }
        if (task.end instanceof Date) {
          const oldValue = originalTask?.end instanceof Date ? originalTask.end.getTime() : null;
          const newValue = task.end.getTime();
          payload["dt_deadline"] = { mode: "update", value: newValue };
          console.log("[Gantt] dt_deadline changed:", { oldValue, newValue });
          if (oldValue !== newValue) {
            pushToUndoStack({ taskId: String(id), field: "dt_deadline", oldValue, newValue });
          }
        }
        
        // Calculate and save duration when both start and end are available
        const startDate = task.start instanceof Date ? task.start : (originalTask?.start instanceof Date ? originalTask.start : null);
        const endDate = task.end instanceof Date ? task.end : (originalTask?.end instanceof Date ? originalTask.end : null);
        if (startDate && endDate) {
          const durationDays = Math.max(1, Math.round((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)));
          payload["duration"] = { mode: "update", value: durationDays };
          console.log("[Gantt] duration calculated:", durationDays, "days");
        }
        
        if (typeof task.progress === "number") {
          payload["percent_complete"] = {
            mode: "update",
            value: Math.round(task.progress * 100),
          };
        }

        console.log("[Gantt] Saving payload:", payload);
        await patchAction(payload);
        console.log("[Gantt] Save completed for task", id);
        
        // Update local React state to keep ganttData in sync with the new values
        const localUpdates: { start?: Date; end?: Date; progress?: number } = {};
        if (task.start instanceof Date) localUpdates.start = task.start;
        if (task.end instanceof Date) localUpdates.end = task.end;
        if (typeof task.progress === "number") localUpdates.progress = task.progress;
        
        updateTaskLocally(id, localUpdates);
        console.log("[Gantt] Local state updated for task", id);
        
        return true;
      } catch (error) {
        console.error("Failed to update task:", error);
        return false;
      }
    },
    [ganttData.tasks, pushToUndoStack, updateTaskLocally]
  );

  // Keep ref updated for use in init callback
  handleSvarUpdateTaskRef.current = handleSvarUpdateTask;

  /**
   * Check if adding a link from source → target would create a circular dependency.
   * A cycle exists if target is already an ancestor of source.
   */
  const wouldCreateCircularDependency = useCallback(
    (sourceId: string, targetId: string): { wouldCreateCycle: boolean; cyclePath: string[] } => {
      // Self-reference check
      if (sourceId === targetId) {
        return { wouldCreateCycle: true, cyclePath: [sourceId] };
      }

      // Build a quick lookup of task parents
      const taskParentsMap = new Map<string, string[]>();
      for (const task of ganttData.tasks) {
        const parents = (task as any).refParents || [];
        taskParentsMap.set(String(task.id), parents.map(String));
      }

      // Check if targetId is an ancestor of sourceId by traversing up from source
      const visited = new Set<string>();
      const path: string[] = [sourceId];

      const hasAncestor = (currentId: string, lookingFor: string): boolean => {
        if (visited.has(currentId)) return false;
        visited.add(currentId);

        const parents = taskParentsMap.get(currentId) || [];
        for (const parentId of parents) {
          if (parentId === lookingFor) {
            path.push(parentId);
            return true;
          }
          path.push(parentId);
          if (hasAncestor(parentId, lookingFor)) {
            return true;
          }
          path.pop();
        }
        return false;
      };

      if (hasAncestor(sourceId, targetId)) {
        return { wouldCreateCycle: true, cyclePath: path };
      }

      return { wouldCreateCycle: false, cyclePath: [] };
    },
    [ganttData.tasks]
  );

  /**
   * Handle adding a new dependency link between tasks
   * Links are stored in refs.parents[] on the target action
   * 
   * SVAR link types:
   * - e2s: End-to-Start (finish-to-start) - most common
   * - s2s: Start-to-Start
   * - e2e: End-to-End
   * - s2e: Start-to-End
   */
  const handleAddLink = useCallback(
    async ({ link }: { id?: string | number; link: { source: string | number; target: string | number; type: string } }) => {
      const sourceId = String(link.source);
      const targetId = String(link.target);
      const linkType = link.type || "e2s";
      
      console.log(`[Gantt] Adding link: ${sourceId} → ${targetId} (${linkType})`);
      
      // Check for circular dependency BEFORE creating the link
      const circularCheck = wouldCreateCircularDependency(sourceId, targetId);
      if (circularCheck.wouldCreateCycle) {
        console.warn(
          `[Gantt] Cannot add link: would create circular dependency. Path: ${circularCheck.cyclePath.join(' → ')}`
        );
        // You could show a toast/alert here
        alert(`Cannot create this dependency: it would create a circular reference.\n\nCycle: ${circularCheck.cyclePath.join(' → ')}`);
        return false;
      }
      
      // Find the target task to get its current refs.parents
      const targetTask = ganttData.tasks.find((t) => String(t.id) === targetId);
      if (!targetTask) {
        console.warn(`[Gantt] Cannot add link: target task ${targetId} not found`);
        return false;
      }
      
      try {
        // Get existing parents from the target task's original action data
        // The parents array should already include existing dependencies
        const existingParents: string[] = (targetTask as any).refParents || [];
        
        // Add the new parent if not already present
        if (!existingParents.includes(sourceId)) {
          const updatedParents = [...existingParents, sourceId];
          
          const payload: Record<string, unknown> = {
            model_name: "action",
            id: targetId,
            "refs.parents": { mode: "update", value: updatedParents },
          };
          
          await patchAction(payload);
          console.log(`[Gantt] Link added successfully: ${sourceId} → ${targetId}`);
          
          // Refresh to show the new link and auto-scheduled dates
          await refetchActions();
          
          // Force Gantt re-render to reflect backend auto-scheduling changes
          setGanttKey((k) => k + 1);
        } else {
          console.log(`[Gantt] Link already exists: ${sourceId} → ${targetId}`);
        }
        
        return true;
      } catch (error) {
        console.error("[Gantt] Failed to add link:", error);
        return false;
      }
    },
    [ganttData.tasks, refetchActions, setGanttKey, wouldCreateCircularDependency]
  );

  /**
   * Handle deleting a dependency link between tasks
   */
  const handleDeleteLink = useCallback(
    async ({ id }: { id: string | number }) => {
      // The link ID format from our mapper is: "dep-{sourceId}-{targetId}"
      const linkIdStr = String(id);
      console.log(`[Gantt] Deleting link: ${linkIdStr}`);
      
      // Parse the link ID to get source and target
      const match = linkIdStr.match(/^dep-(.+)-(.+)$/);
      if (!match) {
        console.warn(`[Gantt] Cannot parse link ID: ${linkIdStr}`);
        return false;
      }
      
      const [, sourceId, targetId] = match;
      
      // Find the target task
      const targetTask = ganttData.tasks.find((t) => String(t.id) === targetId);
      if (!targetTask) {
        console.warn(`[Gantt] Cannot delete link: target task ${targetId} not found`);
        return false;
      }
      
      try {
        // Get existing parents and remove the source
        const existingParents: string[] = (targetTask as any).refParents || [];
        const updatedParents = existingParents.filter((p) => String(p) !== sourceId);
        
        const payload: Record<string, unknown> = {
          model_name: "action",
          id: targetId,
          "refs.parents": { mode: "update", value: updatedParents },
        };
        
        await patchAction(payload);
        console.log(`[Gantt] Link deleted successfully: ${sourceId} → ${targetId}`);
        
        // Refresh to update the display
        await refetchActions();
        
        // Force Gantt re-render
        setGanttKey((k) => k + 1);
        return true;
      } catch (error) {
        console.error("[Gantt] Failed to delete link:", error);
        return false;
      }
    },
    [ganttData.tasks, refetchActions, setGanttKey]
  );

  /**
   * Handle updating an existing link (e.g., changing link type)
   * Note: Our backend currently only stores parent references, not link types
   */
  const handleUpdateLink = useCallback(
    async ({ id, link }: { id: string | number; link: { type?: string } }) => {
      console.log(`[Gantt] Update link requested: ${id}`, link);
      // For now, we don't persist link types - just log the change
      // Link types would require extending the backend model
      return true;
    },
    []
  );

  // Force re-render when selection changes
  useEffect(() => {
    setGanttKey((prev) => prev + 1);
  }, [selectedProjectIds]);
  
  // Refresh task bar colors when tasks, projects (with prefs), or selection changes
  useEffect(() => {
    refreshTaskColorCache();
    scheduleColorRefresh();
  }, [ganttData.tasks, projects, refreshTaskColorCache, scheduleColorRefresh, colorMode]);
  
  // MutationObserver to apply colors when SVAR adds new bar elements
  useEffect(() => {
    const container = ganttContainerRef.current;
    if (!container) return;
    
    const observer = new MutationObserver((mutations) => {
      let hasNewBars = false;
      for (const mutation of mutations) {
        if (mutation.type === "childList") {
          for (const node of mutation.addedNodes) {
            if (node instanceof HTMLElement) {
              // Check if it's a bar or contains bars
              if (node.classList.contains("wx-bar") || node.querySelector(".wx-bar")) {
                hasNewBars = true;
                break;
              }
            }
          }
        }
        if (hasNewBars) break;
      }
      
      if (hasNewBars) {
        // Debounce to avoid excessive calls
        requestAnimationFrame(() => {
          refreshTaskColorCache();
        });
      }
    });
    
    observer.observe(container, {
      childList: true,
      subtree: true,
    });
    
    return () => observer.disconnect();
  }, [refreshTaskColorCache]);
  
  // Link context menu handler
  useEffect(() => {
    const container = ganttContainerRef.current;
    if (!container) return;

    const handleContextMenu = (e: MouseEvent) => {
      // Check if clicked on a link element (SVG path within the chart area)
      const target = e.target as Element;
      
      // SVAR renders links as SVG paths with specific classes
      // Look for parent with data-link-id or similar, or check if it's a path in the chart
      let linkElement: Element | null = target;
      let linkId: string | null = null;
      
      // Walk up the DOM to find a link element
      while (linkElement && linkElement !== container) {
        // Check for data-id attribute on link-related elements
        const dataId = linkElement.getAttribute("data-id");
        if (dataId && dataId.startsWith("dep-")) {
          linkId = dataId;
          break;
        }
        
        // Check if it's an SVG path (links are rendered as paths)
        if (linkElement.tagName.toLowerCase() === "path") {
          // Look for the closest g element with data-id
          const parentG = linkElement.closest("g[data-id]");
          if (parentG) {
            const gDataId = parentG.getAttribute("data-id");
            if (gDataId && gDataId.startsWith("dep-")) {
              linkId = gDataId;
              break;
            }
          }
        }
        
        linkElement = linkElement.parentElement;
      }
      
      if (linkId) {
        e.preventDefault();
        e.stopPropagation();
        setLinkContextMenu({
          x: e.clientX,
          y: e.clientY,
          linkId,
        });
      }
    };

    const handleClick = () => {
      // Close context menu on any click
      setLinkContextMenu(null);
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setLinkContextMenu(null);
      }
    };

    container.addEventListener("contextmenu", handleContextMenu);
    document.addEventListener("click", handleClick);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      container.removeEventListener("contextmenu", handleContextMenu);
      document.removeEventListener("click", handleClick);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);
  
  const handleManualRefresh = useCallback(async () => {
    await refetchActions();
  }, [refetchActions]);
  
  // Helper to format date for display
  const formatDateShort = (date: Date | null | undefined): string => {
    if (!date) return '—';
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' });
  };
  
  // Project legend for print — colored dots with project names
  const renderPrintProjectLegend = (selectedIds: string[], allProjects: typeof projects) => {
    const items = selectedIds.map(id => {
      const proj = allProjects.find(p => String(p.id) === String(id));
      if (!proj) return '';
      const color = getProjectColor(id, selectedIds, proj.prefs?.action?.color);
      const name = proj.name || proj.intent || `Project ${id}`;
      const isChild = proj.id_parent != null;
      const pca = '-webkit-print-color-adjust:exact;print-color-adjust:exact;color-adjust:exact';
      return `<span style="display:inline-flex;align-items:center;gap:3px;margin-right:12px;${isChild ? 'margin-left:12px;' : ''}">
        <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color};${pca};"></span>
        <span style="font-size:9px;color:${isChild ? '#6b7280' : '#374151'};font-weight:${isChild ? '400' : '600'};">${name}</span>
      </span>`;
    }).filter(Boolean).join('');
    return `<div style="display:flex;flex-wrap:wrap;gap:2px 0;margin-top:6px;">${items}</div>`;
  };

  // Today line for print — returns HTML string for a red vertical line at today's position
  const renderPrintTodayLine = (minDate: Date, totalDays: number) => {
    const now = new Date();
    const todayOffset = (now.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24);
    const todayLeft = (todayOffset / totalDays) * 100;
    if (todayLeft < 0 || todayLeft > 100) return '';
    const pca = '-webkit-print-color-adjust:exact;print-color-adjust:exact;color-adjust:exact';
    return `<div style="position:absolute;left:${todayLeft}%;top:0;bottom:0;width:2px;background:rgb(239,68,68);z-index:5;${pca};"></div>
      <div style="position:absolute;left:${todayLeft}%;top:-14px;transform:translateX(-50%);font-size:7px;color:rgb(239,68,68);font-weight:600;white-space:nowrap;">Today</div>`;
  };

  // Shared print bar renderer — matches on-screen GanttTaskTemplate encoding
  const printBarColors = {
    priority: { low: '#e2e8f0', medium: '#93c5fd', high: '#f97316', critical: '#ef4444' } as Record<string, string>,
    status: { open: '#94a3b8', in_progress: '#3b82f6', active: '#3b82f6', complete: '#22c55e', done: '#22c55e', on_hold: '#9ca3af', onhold: '#9ca3af', blocked: '#ef4444', cancelled: '#6b7280', canceled: '#6b7280', draft: '#d1d5db' } as Record<string, string>,
    priorityLabel: { low: 'L', medium: 'M', high: 'H', critical: '!' } as Record<string, string>,
  };

  const renderPrintBar = (task: GanttMappedTask, barLeft: number, barWidth: number, height: number) => {
    const priority = task.priority || 'medium';
    const status = (task.columnId || 'open').toLowerCase().replace(/\s+/g, '_');
    const progress = typeof task.progress === 'number' ? Math.round(task.progress * 100) : (task.percentComplete || 0);
    const priorityColor = printBarColors.priority[priority] || printBarColors.priority.medium;
    const statusColor = printBarColors.status[status] || printBarColors.status.open;
    const pLabel = printBarColors.priorityLabel[priority] || 'M';
    const assignee = task.assignedTo?.[0];
    const initials = assignee?.name ? (assignee.name.trim().split(/\s+/).length > 1
      ? assignee.name.trim().split(/\s+/).map((w: string) => w[0]).join('').toUpperCase().slice(0, 2)
      : assignee.name.slice(0, 2).toUpperCase()) : '';
    const pca = '-webkit-print-color-adjust:exact;print-color-adjust:exact;color-adjust:exact';

    // Slippage from baseline
    const slippageDays = (() => {
      if (!task.dtStartOriginal || !(task.dtStartOriginal instanceof Date)) return 0;
      if (!task.start || !(task.start instanceof Date)) return 0;
      return Math.round((task.start.getTime() - task.dtStartOriginal.getTime()) / 86400000);
    })();
    const slippageHtml = slippageDays !== 0
      ? `<span style="display:inline-flex;align-items:center;justify-content:center;min-width:14px;height:14px;padding:0 2px;border-radius:2px;font-size:6px;font-weight:600;background:${slippageDays > 0 ? '#fef2f2' : '#f0fdf4'};color:${slippageDays > 0 ? '#dc2626' : '#16a34a'};flex-shrink:0;${pca};">${slippageDays > 0 ? '+' : ''}${slippageDays}d</span>`
      : '';

    // Milestone: diamond marker
    const isMilestone = task.start instanceof Date && task.end instanceof Date &&
      (task.end.getTime() - task.start.getTime()) <= 86400000;
    if (isMilestone) {
      return `<div style="position:absolute;left:${barLeft}%;top:50%;transform:translateY(-50%);display:flex;align-items:center;gap:4px;overflow:visible;">
        <div style="width:12px;height:12px;background:${priorityColor};transform:rotate(45deg);flex-shrink:0;border:${task.isCritical ? '2px solid #dc2626' : '1px solid rgba(0,0,0,0.2)'};${pca};"></div>
        <span style="white-space:nowrap;font-size:8px;color:#111827;">${task.text || '—'}</span>
        ${initials ? `<span style="display:inline-flex;align-items:center;justify-content:center;min-width:16px;height:14px;padding:0 3px;border-radius:2px;font-size:7px;font-weight:600;background:#dbeafe;color:#1d4ed8;flex-shrink:0;${pca};">${initials}</span>` : ''}
      </div>`;
    }

    return `<div style="position:absolute;left:${barLeft}%;width:${barWidth}%;height:${height}px;border-radius:3px;overflow:visible;min-width:6px;background:#f1f5f9;${pca};">
      <!-- Top stripe: priority -->
      <div style="position:absolute;top:0;left:0;right:0;height:3px;background:${priorityColor};border-radius:3px 3px 0 0;${pca};"></div>
      <!-- Left stripe: status -->
      <div style="position:absolute;top:0;left:0;bottom:0;width:4px;background:${statusColor};border-radius:3px 0 0 3px;${pca};"></div>
      <!-- Bottom bar: % complete -->
      <div style="position:absolute;bottom:0;left:0;right:0;height:3px;background:rgba(0,0,0,0.12);${pca};">
        <div style="height:100%;width:${Math.min(100, progress)}%;background:${progress >= 100 ? '#22c55e' : '#3b82f6'};border-radius:0 0 0 3px;${pca};"></div>
      </div>
      <!-- Content -->
      <div style="display:flex;align-items:center;gap:3px;padding:3px 6px 3px 8px;height:100%;overflow:visible;">
        ${task.isCritical ? `<span style="display:inline-flex;align-items:center;justify-content:center;min-width:14px;height:14px;padding:0 2px;border-radius:2px;font-size:7px;font-weight:700;background:#dc2626;color:#fff;${pca};">CP</span>` : ''}
        <span style="display:inline-flex;align-items:center;justify-content:center;min-width:14px;height:14px;padding:0 2px;border-radius:2px;font-size:7px;font-weight:700;background:${priorityColor};color:#fff;text-shadow:0 1px 1px rgba(0,0,0,0.3);${pca};">${pLabel}</span>
        <span style="white-space:nowrap;font-size:8px;color:#111827;overflow:visible;">${task.text || '—'}</span>
        ${progress > 0 && progress < 100 ? `<span style="font-size:7px;color:#374151;flex-shrink:0;">${progress}%</span>` : ''}
        ${slippageHtml}
        ${initials ? `<span style="display:inline-flex;align-items:center;justify-content:center;min-width:16px;height:14px;padding:0 3px;border-radius:2px;font-size:7px;font-weight:600;background:#dbeafe;color:#1d4ed8;flex-shrink:0;${pca};">${initials}</span>` : ''}
      </div>
    </div>`;
  };

  // Print handler - opens a new window with task list table + timeline visualization
  const handlePrint = useCallback(async () => {
    const container = ganttContainerRef.current;
    if (!container) {
      alert("Unable to print: Gantt container not found");
      return;
    }
    
    // Build project names header — top-level projects only
    const topLevelIds = selectedProjectIds.filter(id => {
      const proj = projects.find(p => String(p.id) === String(id));
      return !proj?.id_parent;
    });
    const projectNames = (topLevelIds.length > 0 ? topLevelIds : selectedProjectIds).map(id => {
      const proj = projects.find(p => String(p.id) === String(id));
      return proj?.name || proj?.intent || `Project ${id}`;
    }).join(', ');

    // Calculate date range for the timeline
    let minDate = new Date();
    let maxDate = new Date();
    ganttData.tasks.forEach(task => {
      if (task.start instanceof Date) {
        if (task.start < minDate) minDate = new Date(task.start);
        if (task.start > maxDate) maxDate = new Date(task.start);
      }
      if (task.end instanceof Date) {
        if (task.end < minDate) minDate = new Date(task.end);
        if (task.end > maxDate) maxDate = new Date(task.end);
      }
    });
    
    // Add padding to date range
    minDate.setDate(minDate.getDate() - 2);
    maxDate.setDate(maxDate.getDate() + 2);
    const totalDays = Math.max(1, Math.ceil((maxDate.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24)));
    
    // Today line for timeline cells
    const todayLineHtml = renderPrintTodayLine(minDate, totalDays);

    // Build task list table rows with visual timeline bars (using inline styles for print compatibility)
    const taskRows = ganttData.tasks.map(task => {
      const mapped = task as GanttMappedTask;
      const startDate = task.start instanceof Date ? formatDateShort(task.start) : '—';
      const endDate = task.end instanceof Date ? formatDateShort(task.end) : '—';
      const progress = typeof task.progress === 'number' ? Math.round(task.progress * 100) : 0;
      const slack = typeof mapped.slack === 'number' ? `${mapped.slack}d` : '—';
      const critical = mapped.critical ? '●' : '';
      
      // Calculate bar position and width for timeline visualization
      let barLeft = 0;
      let barWidth = 0;
      if (task.start instanceof Date && task.end instanceof Date) {
        const startOffset = (task.start.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24);
        const duration = Math.max(1, (task.end.getTime() - task.start.getTime()) / (1000 * 60 * 60 * 24));
        barLeft = (startOffset / totalDays) * 100;
        barWidth = Math.max((duration / totalDays) * 100, 1);
      }
      
      // Use fully inline styles for maximum print compatibility
      return `<tr>
        <td>${task.text || '—'}</td>
        <td style="text-align:center">${startDate}</td>
        <td style="text-align:center">${endDate}</td>
        <td style="text-align:center">${progress}%</td>
        <td style="text-align:center">${slack}</td>
        <td style="text-align:center;color:${mapped.critical ? '#dc2626' : '#9ca3af'}">${critical}</td>
        <td style="padding:2px 4px;min-width:300px;-webkit-print-color-adjust:exact;print-color-adjust:exact;color-adjust:exact;">
          <div style="position:relative;height:22px;background:#e5e7eb;border-radius:2px;-webkit-print-color-adjust:exact;print-color-adjust:exact;color-adjust:exact;">
            ${todayLineHtml}
            ${renderPrintBar(mapped, barLeft, barWidth, 22)}
          </div>
        </td>
      </tr>`;
    }).join('');
    
    // Generate week labels for timeline header
    const weekPositions: { label: string; left: number; isMonth: boolean }[] = [];
    const tempDate = new Date(minDate);
    while (tempDate <= maxDate) {
      const dayOffset = (tempDate.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24);
      const leftPos = (dayOffset / totalDays) * 100;
      const isMonthStart = tempDate.getDate() <= 7 && weekPositions.length > 0;
      weekPositions.push({
        label: tempDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        left: leftPos,
        isMonth: isMonthStart,
      });
      tempDate.setDate(tempDate.getDate() + 7);
    }

    const timelineHeader = weekPositions.map(m =>
      `<span style="position:absolute;left:${m.left}%;font-size:7px;color:${m.isMonth ? '#111827' : '#6b7280'};font-weight:${m.isMonth ? '700' : '400'};white-space:nowrap;">${m.label}</span>`
    ).join('');

    // Create a new window for printing
    const printWindow = window.open('', '_blank', 'width=1200,height=800');
    if (!printWindow) {
      alert("Please allow popups to print the Gantt chart");
      return;
    }
    
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Gantt Chart - ${projectNames}</title>
          <style>
            * { 
              box-sizing: border-box;
              -webkit-print-color-adjust: exact !important;
              print-color-adjust: exact !important;
              color-adjust: exact !important;
            }
            body { 
              margin: 0; 
              padding: 20px; 
              background: white;
              font-family: system-ui, -apple-system, sans-serif;
              font-size: 11px;
            }
            .print-header {
              margin-bottom: 15px;
              padding-bottom: 10px;
              border-bottom: 2px solid #e5e7eb;
            }
            .print-header h1 {
              margin: 0 0 4px 0;
              font-size: 16px;
              font-weight: 600;
              color: #111827;
            }
            .print-header p {
              margin: 0;
              font-size: 10px;
              color: #6b7280;
            }
            
            /* Task List Section */
            .task-list-section {
              margin-bottom: 20px;
            }
            .task-list-section h2 {
              font-size: 14px;
              font-weight: 600;
              margin: 0 0 10px 0;
              color: #374151;
            }
            .task-table {
              width: 100%;
              border-collapse: collapse;
              font-size: 9px;
            }
            .task-table th {
              background: #f3f4f6;
              border: 1px solid #d1d5db;
              padding: 4px 6px;
              text-align: left;
              font-weight: 600;
              color: #374151;
              white-space: nowrap;
            }
            .task-table td {
              border: 1px solid #e5e7eb;
              padding: 3px 6px;
              color: #4b5563;
            }
            .task-table tr:nth-child(even) {
              background: #f9fafb;
            }
            
            /* Timeline visualization */
            .timeline-header {
              position: relative;
              height: 16px;
              background: #f9fafb;
              border-bottom: 1px solid #e5e7eb;
            }
            .timeline-cell {
              padding: 2px 4px !important;
              min-width: 300px;
            }
            .timeline-bar-container {
              position: relative;
              height: 14px;
              background: #e5e7eb;
              border-radius: 2px;
              -webkit-print-color-adjust: exact !important;
              print-color-adjust: exact !important;
              color-adjust: exact !important;
            }
            .timeline-bar {
              position: absolute;
              height: 100%;
              border-radius: 2px;
              min-width: 4px;
              -webkit-print-color-adjust: exact !important;
              print-color-adjust: exact !important;
              color-adjust: exact !important;
            }
            .timeline-progress {
              height: 100%;
              background: rgba(0,0,0,0.25);
              border-radius: 2px 0 0 2px;
              -webkit-print-color-adjust: exact !important;
              print-color-adjust: exact !important;
              color-adjust: exact !important;
            }
            
            @media print {
              @page { 
                size: landscape; 
                margin: 0.3in; 
              }
              * {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                color-adjust: exact !important;
              }
              body { padding: 0; font-size: 8px; }
              .print-header { margin-bottom: 8px; }
              .task-table { font-size: 7px; }
              .task-table th, .task-table td { padding: 2px 4px; }
              .timeline-cell { min-width: 250px; }
              .timeline-bar-container {
                background: #e5e7eb !important;
              }
              .timeline-bar {
                background-color: inherit !important;
              }
            }
          </style>
        </head>
        <body>
          <div class="print-header">
            <h1>Project Gantt Chart</h1>
            <p>${projectNames} | Generated: ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString()} | ${ganttData.tasks.length} tasks</p>
            ${renderPrintProjectLegend(selectedProjectIds, projects)}
          </div>

          <!-- Task List with Timeline -->
          <div class="task-list-section">
            <table class="task-table">
              <thead>
                <tr>
                  <th style="width:22%">action.en</th>
                  <th style="width:8%;text-align:center">dt_start</th>
                  <th style="width:8%;text-align:center">dt_deadline</th>
                  <th style="width:6%;text-align:center">percent_complete</th>
                  <th style="width:6%;text-align:center">slack</th>
                  <th style="width:5%;text-align:center">isCritical</th>
                  <th style="width:45%">
                    <div style="position:relative;height:16px;background:#f9fafb;border-bottom:1px solid #e5e7eb;-webkit-print-color-adjust:exact;print-color-adjust:exact;color-adjust:exact;">${timelineHeader}</div>
                  </th>
                </tr>
              </thead>
              <tbody>
                ${taskRows}
              </tbody>
            </table>
          </div>
          
          <script>
            window.onload = function() {
              setTimeout(function() {
                window.print();
              }, 200);
            };
          </script>
        </body>
      </html>
    `);
    
    printWindow.document.close();
  }, [projects, selectedProjectIds, ganttData.tasks]);

  // Print handler - bars only, task text overruns the bar (no table columns)
  const handlePrintBars = useCallback(async () => {
    const container = ganttContainerRef.current;
    if (!container) {
      alert("Unable to print: Gantt container not found");
      return;
    }

    const topLevelIds = selectedProjectIds.filter(id => {
      const proj = projects.find(p => String(p.id) === String(id));
      return !proj?.id_parent;
    });
    const projectNames = (topLevelIds.length > 0 ? topLevelIds : selectedProjectIds).map(id => {
      const proj = projects.find(p => String(p.id) === String(id));
      return proj?.name || proj?.intent || `Project ${id}`;
    }).join(', ');

    // Calculate date range
    let minDate = new Date();
    let maxDate = new Date();
    ganttData.tasks.forEach(task => {
      if (task.start instanceof Date) {
        if (task.start < minDate) minDate = new Date(task.start);
        if (task.start > maxDate) maxDate = new Date(task.start);
      }
      if (task.end instanceof Date) {
        if (task.end < minDate) minDate = new Date(task.end);
        if (task.end > maxDate) maxDate = new Date(task.end);
      }
    });
    minDate.setDate(minDate.getDate() - 2);
    maxDate.setDate(maxDate.getDate() + 2);
    const totalDays = Math.max(1, Math.ceil((maxDate.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24)));

    // Build bar rows grouped by week
    const getWeekKey = (d: Date) => {
      const mon = new Date(d);
      mon.setDate(mon.getDate() - ((mon.getDay() + 6) % 7)); // Monday
      return mon.toISOString().slice(0, 10);
    };
    const getWeekLabel = (d: Date) => {
      const mon = new Date(d);
      mon.setDate(mon.getDate() - ((mon.getDay() + 6) % 7));
      const sun = new Date(mon);
      sun.setDate(sun.getDate() + 6);
      return `${mon.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} – ${sun.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
    };

    // Group tasks by start week
    const weekGroups = new Map<string, { label: string; rows: string[] }>();
    ganttData.tasks.forEach(task => {
      const mapped = task as GanttMappedTask;
      let barLeft = 0;
      let barWidth = 0;
      if (task.start instanceof Date && task.end instanceof Date) {
        const startOffset = (task.start.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24);
        const duration = Math.max(1, (task.end.getTime() - task.start.getTime()) / (1000 * 60 * 60 * 24));
        barLeft = (startOffset / totalDays) * 100;
        barWidth = Math.max((duration / totalDays) * 100, 1);
      }
      const weekKey = task.start instanceof Date ? getWeekKey(task.start) : '9999';
      const weekLabel = task.start instanceof Date ? getWeekLabel(task.start) : 'Unscheduled';
      if (!weekGroups.has(weekKey)) {
        weekGroups.set(weekKey, { label: weekLabel, rows: [] });
      }
      weekGroups.get(weekKey)!.rows.push(
        `<div style="position:relative;height:24px;margin-bottom:2px;">${renderPrintBar(mapped, barLeft, barWidth, 24)}</div>`
      );
    });

    // Render grouped with week dividers
    const barRows = Array.from(weekGroups.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([, group]) =>
        `<div style="margin-top:8px;margin-bottom:4px;border-top:1px solid #d1d5db;padding-top:4px;">
          <div style="font-size:8px;font-weight:600;color:#6b7280;margin-bottom:2px;">${group.label}</div>
          ${group.rows.join('')}
        </div>`
      ).join('');

    // Week labels for timeline header
    const weekPositions: { label: string; left: number; isMonth: boolean }[] = [];
    const tempDate = new Date(minDate);
    while (tempDate <= maxDate) {
      const dayOffset = (tempDate.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24);
      const leftPos = (dayOffset / totalDays) * 100;
      const isMonthStart = tempDate.getDate() <= 7 && weekPositions.length > 0;
      weekPositions.push({
        label: tempDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        left: leftPos,
        isMonth: isMonthStart,
      });
      tempDate.setDate(tempDate.getDate() + 7);
    }
    const timelineHeader = weekPositions.map(m =>
      `<span style="position:absolute;left:${m.left}%;font-size:8px;color:${m.isMonth ? '#111827' : '#6b7280'};font-weight:${m.isMonth ? '700' : '400'};white-space:nowrap;">${m.label}</span>`
    ).join('');

    // Week grid lines
    const gridLines: string[] = [];
    const gridDate = new Date(minDate);
    while (gridDate <= maxDate) {
      const dayOffset = (gridDate.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24);
      const leftPos = (dayOffset / totalDays) * 100;
      gridLines.push(`<div style="position:absolute;left:${leftPos}%;top:0;bottom:0;width:1px;background:#e5e7eb;-webkit-print-color-adjust:exact;print-color-adjust:exact;"></div>`);
      gridDate.setDate(gridDate.getDate() + 7);
    }

    const printWindow = window.open('', '_blank', 'width=1200,height=800');
    if (!printWindow) {
      alert("Please allow popups to print the Gantt chart");
      return;
    }

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Gantt Chart - ${projectNames}</title>
          <style>
            * {
              box-sizing: border-box;
              -webkit-print-color-adjust: exact !important;
              print-color-adjust: exact !important;
              color-adjust: exact !important;
            }
            body {
              margin: 0;
              padding: 20px;
              background: white;
              font-family: system-ui, -apple-system, sans-serif;
              font-size: 11px;
            }
            .print-header {
              margin-bottom: 15px;
              padding-bottom: 10px;
              border-bottom: 2px solid #e5e7eb;
            }
            .print-header h1 {
              margin: 0 0 4px 0;
              font-size: 16px;
              font-weight: 600;
              color: #111827;
            }
            .print-header p {
              margin: 0;
              font-size: 10px;
              color: #6b7280;
            }
            @media print {
              @page { size: landscape; margin: 0.3in; }
              * {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                color-adjust: exact !important;
              }
              body { padding: 0; }
              .print-header { margin-bottom: 8px; }
            }
          </style>
        </head>
        <body>
          <div class="print-header">
            <h1>Project Gantt Chart</h1>
            <p>${projectNames} | Generated: ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString()} | ${ganttData.tasks.length} tasks</p>
            ${renderPrintProjectLegend(selectedProjectIds, projects)}
          </div>

          <!-- Timeline header -->
          <div style="position:relative;height:20px;border-bottom:2px solid #d1d5db;margin-bottom:4px;">
            ${timelineHeader}
          </div>

          <!-- Bar chart -->
          <div style="position:relative;">
            ${renderPrintTodayLine(minDate, totalDays)}
            ${gridLines.join('')}
            ${barRows}
          </div>

          <script>
            window.onload = function() {
              setTimeout(function() { window.print(); }, 200);
            };
          </script>
        </body>
      </html>
    `);

    printWindow.document.close();
  }, [projects, selectedProjectIds, ganttData.tasks]);

  // Export to SVG handler - creates a true vector graphic
  const handleExportSVG = useCallback(() => {
    if (ganttData.tasks.length === 0) {
      alert("No tasks to export");
      return;
    }
    
    // Helper to escape XML special characters
    const escapeXml = (str: string): string => {
      return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    };
    
    // Configuration
    const leftPanelWidth = 200;
    const rowHeight = 28;
    const headerHeight = 50;
    const padding = 10;
    const chartWidth = 800;
    const totalWidth = leftPanelWidth + chartWidth + padding * 2;
    const totalHeight = headerHeight + ganttData.tasks.length * rowHeight + padding * 2;
    
    // Calculate date range
    let minDate = new Date();
    let maxDate = new Date();
    ganttData.tasks.forEach(task => {
      if (task.start instanceof Date) {
        if (task.start < minDate) minDate = new Date(task.start);
        if (task.start > maxDate) maxDate = new Date(task.start);
      }
      if (task.end instanceof Date) {
        if (task.end < minDate) minDate = new Date(task.end);
        if (task.end > maxDate) maxDate = new Date(task.end);
      }
    });
    minDate.setDate(minDate.getDate() - 3);
    maxDate.setDate(maxDate.getDate() + 3);
    const totalDays = Math.max(1, Math.ceil((maxDate.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24)));
    
    // Build project names
    const topLevelIds = selectedProjectIds.filter(id => {
      const proj = projects.find(p => String(p.id) === String(id));
      return !proj?.id_parent;
    });
    const projectNames = (topLevelIds.length > 0 ? topLevelIds : selectedProjectIds).map(id => {
      const proj = projects.find(p => String(p.id) === String(id));
      return proj?.name || proj?.intent || `Project ${id}`;
    }).join(', ');
    
    // Generate month/week markers
    const dateMarkers: { label: string; x: number }[] = [];
    const tempDate = new Date(minDate);
    let lastMonth = -1;
    while (tempDate <= maxDate) {
      const dayOffset = (tempDate.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24);
      const xPos = leftPanelWidth + padding + (dayOffset / totalDays) * chartWidth;
      
      if (tempDate.getMonth() !== lastMonth) {
        dateMarkers.push({
          label: tempDate.toLocaleDateString('en-US', { month: 'short', year: '2-digit' }),
          x: xPos
        });
        lastMonth = tempDate.getMonth();
      }
      tempDate.setDate(tempDate.getDate() + 7);
    }
    
    // Color maps matching GanttTaskTemplate
    const svgPriorityColors: Record<string, string> = {
      low: '#e2e8f0', medium: '#93c5fd', high: '#f97316', critical: '#ef4444',
    };
    const svgStatusColors: Record<string, string> = {
      open: '#94a3b8', in_progress: '#3b82f6', active: '#3b82f6',
      complete: '#22c55e', done: '#22c55e', on_hold: '#9ca3af', onhold: '#9ca3af',
      blocked: '#ef4444', cancelled: '#6b7280', canceled: '#6b7280', draft: '#d1d5db',
    };
    const svgPriorityLabel: Record<string, string> = { low: 'L', medium: 'M', high: 'H', critical: '!' };

    // Generate SVG content
    let svgContent = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${totalWidth} ${totalHeight}" width="${totalWidth}" height="${totalHeight}">
  <defs>
    <style>
      .title { font: bold 14px system-ui, -apple-system, sans-serif; fill: #111827; }
      .subtitle { font: 9px system-ui, sans-serif; fill: #6b7280; }
      .date-label { font: 8px system-ui, sans-serif; fill: #9ca3af; }
      .date-label-bold { font: bold 8px system-ui, sans-serif; fill: #111827; }
      .header-bg { fill: #f9fafb; }
      .grid-line { stroke: #e5e7eb; stroke-width: 0.5; }
      .task-text { font: 9px system-ui, sans-serif; fill: #111827; }
      .badge-text { font: bold 7px system-ui, sans-serif; fill: white; }
      .percent-text { font: 7px system-ui, sans-serif; fill: #374151; }
      .slip-text-pos { font: bold 6px system-ui, sans-serif; fill: #dc2626; }
      .slip-text-neg { font: bold 6px system-ui, sans-serif; fill: #16a34a; }
    </style>
  </defs>

  <!-- Background -->
  <rect width="${totalWidth}" height="${totalHeight}" fill="white"/>

  <!-- Header -->
  <rect x="0" y="0" width="${totalWidth}" height="${headerHeight}" class="header-bg"/>
  <text x="${padding}" y="20" class="title">Project Gantt Chart</text>
  <text x="${padding}" y="35" class="subtitle">${escapeXml(projectNames)} | ${ganttData.tasks.length} tasks | ${new Date().toLocaleDateString()}</text>

  <!-- Date markers -->
  ${dateMarkers.map(m => `<text x="${m.x}" y="45" class="date-label">${m.label}</text>`).join('\n  ')}

  <!-- Separator line -->
  <line x1="0" y1="${headerHeight}" x2="${totalWidth}" y2="${headerHeight}" class="grid-line"/>
`;

    // Today line
    const todayOffset = (new Date().getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24);
    const todayX = padding + (todayOffset / totalDays) * chartWidth;
    if (todayX >= 0 && todayX <= chartWidth) {
      svgContent += `  <line x1="${todayX}" y1="${headerHeight}" x2="${todayX}" y2="${totalHeight}" stroke="#ef4444" stroke-width="2"/>\n`;
      svgContent += `  <text x="${todayX}" y="${headerHeight - 2}" class="slip-text-pos" text-anchor="middle">Today</text>\n`;
    }

    // Add task rows with rich bars
    ganttData.tasks.forEach((task, index) => {
      const mapped = task as GanttMappedTask;
      const y = headerHeight + index * rowHeight;
      const priority = mapped.priority || 'medium';
      const status = (mapped.columnId || 'open').toLowerCase().replace(/\s+/g, '_');
      const progress = typeof task.progress === 'number' ? Math.round(task.progress * 100) : 0;
      const priorityColor = svgPriorityColors[priority] || svgPriorityColors.medium;
      const statusColor = svgStatusColors[status] || svgStatusColors.open;
      const pLabel = svgPriorityLabel[priority] || 'M';
      const isMilestone = task.start instanceof Date && task.end instanceof Date &&
        (task.end.getTime() - task.start.getTime()) <= 86400000;

      // Slippage
      const slippageDays = (mapped.dtStartOriginal instanceof Date && task.start instanceof Date)
        ? Math.round((task.start.getTime() - mapped.dtStartOriginal.getTime()) / 86400000) : 0;

      // Calculate bar position
      let barX = padding;
      let barWidth = 0;
      if (task.start instanceof Date && task.end instanceof Date) {
        const startOffset = (task.start.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24);
        const duration = Math.max(1, (task.end.getTime() - task.start.getTime()) / (1000 * 60 * 60 * 24));
        barX = padding + (startOffset / totalDays) * chartWidth;
        barWidth = Math.max((duration / totalDays) * chartWidth, 6);
      }

      // Row background (alternating)
      if (index % 2 === 0) {
        svgContent += `  <rect x="0" y="${y}" width="${totalWidth}" height="${rowHeight}" fill="#fafafa"/>\n`;
      }
      svgContent += `  <line x1="0" y1="${y + rowHeight}" x2="${totalWidth}" y2="${y + rowHeight}" class="grid-line"/>\n`;

      const barY = y + 4;
      const barHeight = rowHeight - 8;

      if (isMilestone) {
        // Diamond
        const cx = barX;
        const cy = barY + barHeight / 2;
        svgContent += `  <rect x="${cx - 7}" y="${cy - 7}" width="14" height="14" fill="${priorityColor}" transform="rotate(45 ${cx} ${cy})"/>\n`;
        svgContent += `  <text x="${cx + 12}" y="${cy + 4}" class="task-text">${escapeXml(task.text || '—')}</text>\n`;
      } else if (barWidth > 0) {
        // Bar background
        svgContent += `  <rect x="${barX}" y="${barY}" width="${barWidth}" height="${barHeight}" rx="3" fill="#f1f5f9"/>\n`;
        // Top stripe (priority)
        svgContent += `  <rect x="${barX}" y="${barY}" width="${barWidth}" height="3" rx="3" fill="${priorityColor}"/>\n`;
        // Left stripe (status)
        svgContent += `  <rect x="${barX}" y="${barY}" width="4" height="${barHeight}" rx="2" fill="${statusColor}"/>\n`;
        // Bottom bar (% complete)
        if (progress > 0) {
          const progW = (progress / 100) * barWidth;
          const progColor = progress >= 100 ? '#22c55e' : '#3b82f6';
          svgContent += `  <rect x="${barX}" y="${barY + barHeight - 3}" width="${progW}" height="3" fill="${progColor}"/>\n`;
        }
        // Priority badge
        svgContent += `  <rect x="${barX + 8}" y="${barY + barHeight / 2 - 7}" width="14" height="14" rx="2" fill="${priorityColor}"/>\n`;
        svgContent += `  <text x="${barX + 15}" y="${barY + barHeight / 2 + 3}" class="badge-text" text-anchor="middle">${pLabel}</text>\n`;
        // CP badge
        if (mapped.isCritical) {
          svgContent += `  <rect x="${barX + 24}" y="${barY + barHeight / 2 - 7}" width="16" height="14" rx="2" fill="#dc2626"/>\n`;
          svgContent += `  <text x="${barX + 32}" y="${barY + barHeight / 2 + 3}" class="badge-text" text-anchor="middle">CP</text>\n`;
        }
        // Task text (overruns bar)
        const textX = barX + (mapped.isCritical ? 44 : 26);
        svgContent += `  <text x="${textX}" y="${barY + barHeight / 2 + 3}" class="task-text">${escapeXml(task.text || '—')}</text>\n`;
        // Percent text
        if (progress > 0 && progress < 100) {
          svgContent += `  <text x="${barX + barWidth + 4}" y="${barY + barHeight / 2 + 3}" class="percent-text">${progress}%</text>\n`;
        }
        // Slippage
        if (slippageDays !== 0) {
          const slipClass = slippageDays > 0 ? 'slip-text-pos' : 'slip-text-neg';
          const slipLabel = `${slippageDays > 0 ? '+' : ''}${slippageDays}d`;
          svgContent += `  <text x="${barX + barWidth + (progress > 0 && progress < 100 ? 30 : 4)}" y="${barY + barHeight / 2 + 3}" class="${slipClass}">${slipLabel}</text>\n`;
        }
      }
    });
    
    svgContent += `</svg>`;
    
    // Download the SVG
    const blob = new Blob([svgContent], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    
    const fileProjectNames = selectedProjectIds.map(id => {
      const proj = projects.find(p => String(p.id) === String(id));
      return proj?.name || proj?.intent || id;
    }).join('-').replace(/[^a-zA-Z0-9-]/g, '').slice(0, 50);
    
    link.download = `gantt-${fileProjectNames || 'chart'}-${new Date().toISOString().split("T")[0]}.svg`;
    link.href = url;
    link.click();
    
    URL.revokeObjectURL(url);
  }, [projects, selectedProjectIds, ganttData.tasks]);
  
  // Export JSON — full task data for import, analysis, or archival
  const handleExportJSON = useCallback(() => {
    if (ganttData.tasks.length === 0) return;

    const topLevelIds = selectedProjectIds.filter(id => {
      const proj = projects.find(p => String(p.id) === String(id));
      return !proj?.id_parent;
    });
    const projectNames = (topLevelIds.length > 0 ? topLevelIds : selectedProjectIds).map(id => {
      const proj = projects.find(p => String(p.id) === String(id));
      return proj?.name || proj?.intent || `Project ${id}`;
    });

    const exported = {
      exported_at: new Date().toISOString(),
      projects: projectNames,
      task_count: ganttData.tasks.length,
      link_count: ganttData.links.length,
      tasks: ganttData.tasks.map(task => {
        const mapped = task as GanttMappedTask;
        return {
          id: task.id,
          ida: mapped.taskIda,
          text: task.text,
          project: mapped.projectName,
          project_ida: mapped.projectIda,
          status: mapped.columnId,
          priority: mapped.priority,
          percent_complete: typeof task.progress === 'number' ? Math.round(task.progress * 100) : 0,
          dt_start: task.start instanceof Date ? task.start.toISOString() : null,
          dt_deadline: task.end instanceof Date ? task.end.toISOString() : null,
          dt_start_original: mapped.dtStartOriginal instanceof Date ? mapped.dtStartOriginal.toISOString() : null,
          dt_end_original: mapped.dtEndOriginal instanceof Date ? mapped.dtEndOriginal.toISOString() : null,
          is_critical: mapped.isCritical || false,
          slack_days: mapped.slack ?? null,
          assigned_to: (mapped.assignedTo || []).map(a => ({ id: a.id, name: a.name })),
          dependencies: mapped.refParents || [],
        };
      }),
      links: ganttData.links,
    };

    const blob = new Blob([JSON.stringify(exported, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const fileLabel = projectNames.join('-').replace(/[^a-zA-Z0-9-]/g, '').slice(0, 50);
    link.download = `gantt-${fileLabel || 'chart'}-${new Date().toISOString().split('T')[0]}.json`;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  }, [projects, selectedProjectIds, ganttData]);

  // Set baseline handler - saves current dates as original planned dates
  const handleSetBaseline = useCallback(async () => {
    if (ganttData.tasks.length === 0) return;
    
    const confirmed = window.confirm(
      "This will save the current start dates as the original planned dates for all tasks. Continue?"
    );
    if (!confirmed) return;
    
    try {
      // Update each task's original planned dates
      const updates = ganttData.tasks.map(async (task) => {
        const startMs = task.start instanceof Date ? task.start.getTime() : null;
        const endMs = task.end instanceof Date ? task.end.getTime() : null;
        
        if (!startMs) return;
        
        const payload: Record<string, unknown> = {
          model_name: "action",
          id: task.id,
          dt_start_original: { mode: "update", value: startMs },
          dt_end_original: { mode: "update", value: endMs },
        };
        
        return patchAction(payload);
      });
      
      await Promise.all(updates);
      await refetchActions();
      alert("Baseline dates saved successfully!");
    } catch (error) {
      console.error("Failed to set baseline:", error);
      alert("Failed to save baseline dates. Please try again.");
    }
  }, [ganttData.tasks, refetchActions]);
  
  // Undo handler
  const handleUndo = useCallback(async () => {
    if (undoStack.length === 0) return;
    
    const entry = undoStack[undoStack.length - 1];
    setUndoStack((stack) => stack.slice(0, -1));
    
    try {
      const payload: Record<string, unknown> = {
        model_name: "action",
        id: entry.taskId,
        [entry.field]: { mode: "update", value: entry.oldValue },
      };
      
      await patchAction(payload);
      await refetchActions();
      
      // Add to redo stack
      setRedoStack((stack) => [...stack, entry]);
    } catch (error) {
      console.error("Undo failed:", error);
      // Restore the entry to undo stack on failure
      setUndoStack((stack) => [...stack, entry]);
    }
  }, [undoStack, refetchActions]);
  
  // Redo handler
  const handleRedo = useCallback(async () => {
    if (redoStack.length === 0) return;
    
    const entry = redoStack[redoStack.length - 1];
    setRedoStack((stack) => stack.slice(0, -1));
    
    try {
      const payload: Record<string, unknown> = {
        model_name: "action",
        id: entry.taskId,
        [entry.field]: { mode: "update", value: entry.newValue },
      };
      
      await patchAction(payload);
      await refetchActions();
      
      // Add to undo stack
      setUndoStack((stack) => [...stack, entry]);
    } catch (error) {
      console.error("Redo failed:", error);
      // Restore the entry to redo stack on failure
      setRedoStack((stack) => [...stack, entry]);
    }
  }, [redoStack, refetchActions]);
  
  // Keyboard shortcut for undo/redo
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "z") {
        e.preventDefault();
        if (e.shiftKey) {
          handleRedo();
        } else {
          handleUndo();
        }
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "y") {
        e.preventDefault();
        handleRedo();
      }
    };
    
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleUndo, handleRedo]);
  
  const isLoading = isLoadingProjects || isLoadingActions;
  const error = projectsError || actionsError;
  
  // Create task lookup map for column templates (SVAR strips custom properties)
  const taskLookup = useMemo(() => {
    const lookup = new Map<string, GanttMappedTask>();
    for (const task of ganttData.tasks) {
      lookup.set(String(task.id), task as GanttMappedTask);
    }
    return lookup;
  }, [ganttData.tasks]);
  
  // Minimal column configuration when task list is collapsed
  const collapsedColumns: IColumnConfig[] = useMemo(() => [
    {
      id: "taskIda",
      header: "#",
      width: 50,
      align: "center",
      template: (_value: unknown, task: GanttMappedTask) => task?.taskIda || "-",
    },
  ], []);
  
  // Choose columns based on mode - create dynamically with task lookup
  // Include reorder column when auto-sort is disabled
  const activeColumns = useMemo(() => {
    const includeReorder = !autoSortByDate;
    if (taskListCollapsed) {
      return collapsedColumns;
    }
    return isSingleProjectMode 
      ? createGanttColumnsSingleProject(taskLookup, includeReorder) 
      : createGanttColumns(taskLookup, includeReorder);
  }, [isSingleProjectMode, taskLookup, taskListCollapsed, collapsedColumns, autoSortByDate]);

  // Get the project name for single-project mode header
  const singleProjectName = useMemo(() => {
    if (!isSingleProjectMode) return null;
    const project = projects.find((p) => p.id === projectId);
    return project?.name || project?.slug || `Project ${projectId}`;
  }, [isSingleProjectMode, projects, projectId]);
  
  return (
    <>
      {/* Gantt today indicator styles */}
      <style>{`
        .today-highlight {
          background-color: rgba(239, 68, 68, 0.15) !important;
          position: relative;
        }
        .today-highlight::after {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          border-left: 3px solid rgb(239, 68, 68);
          pointer-events: none;
          z-index: 5;
        }
        .dark .today-highlight {
          background-color: rgba(239, 68, 68, 0.18) !important;
        }
        .sprint-boundary {
          border-right: 3px dashed rgba(156, 163, 175, 0.5) !important;
        }
        .dark .sprint-boundary {
          border-right-color: rgba(156, 163, 175, 0.4) !important;
        }
        /* Fix scale header — sticky on vertical scroll */
        .wx-gantt .wx-scale {
          position: sticky !important;
          top: 0 !important;
          z-index: 10 !important;
          background: white !important;
        }
        .dark .wx-gantt .wx-scale {
          background: rgb(17, 24, 39) !important;
        }
        /* Ensure the chart area scrolls independently */
        .wx-gantt .wx-chart {
          overflow-y: auto !important;
        }
        /* Add resize cursor zones on task bar edges */
        .wx-bar:not(.wx-milestone) {
          cursor: move;
        }
        /* Left justify header date cells */
        .wx-scale .wx-cell {
          justify-content: flex-start !important;
          padding-left: 8px !important;
        }
        .wx-bar:not(.wx-milestone)::before,
        .wx-bar:not(.wx-milestone)::after {
          content: '';
          position: absolute;
          top: 0;
          width: 8px;
          height: 100%;
          cursor: ew-resize;
          z-index: 10;
        }
        .wx-bar:not(.wx-milestone)::before {
          left: 0;
        }
        .wx-bar:not(.wx-milestone)::after {
          right: 0;
        }
      `}</style>
      <div className={combineClassNames("flex h-[calc(100vh-4rem)]", className)}>
      {/* Project Selector Sidebar - Collapsible */}
      {showSelector && (
        <div className={combineClassNames(
          "shrink-0 transition-all duration-300 ease-in-out",
          selectorCollapsed ? "w-10" : (compact ? "w-56" : "w-72")
        )}>
          <div className="sticky top-0 h-full">
            {selectorCollapsed ? (
              // Collapsed state - just a toggle button
              <div className="flex h-full flex-col items-center rounded-l-2xl border border-gray-200 bg-white py-3 dark:border-gray-700 dark:bg-gray-900">
                <button
                  type="button"
                  onClick={() => setSelectorCollapsed(false)}
                  className="rounded-lg p-2 text-gray-500 transition hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
                  title="Expand project list"
                >
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                <span className="mt-2 text-xs font-medium text-gray-500 dark:text-gray-400 [writing-mode:vertical-lr]">
                  Projects ({selectedProjectIds.length})
                </span>
              </div>
            ) : (
              // Expanded state - full selector with collapse button
              <div className="relative h-full">
                <button
                  type="button"
                  onClick={() => setSelectorCollapsed(true)}
                  className="absolute -right-3 top-3 z-10 rounded-full border border-gray-200 bg-white p-1 text-gray-500 shadow-sm transition hover:bg-gray-100 hover:text-gray-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-200"
                  title="Collapse project list"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
                <GanttProjectSelector
                  projects={projects}
                  selectedIds={selectedProjectIds}
                  onSelectionChange={setSelectedProjectIds}
                  isLoading={isLoadingProjects}
                  disabled={isRefreshing}
                />
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Gantt Chart Area */}
      <div className="min-w-0 flex-1 flex flex-col">
        <section className={combineClassNames(
          "flex flex-1 min-h-0 flex-col rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-900",
        )}>
          {/* Header */}
          <div className={combineClassNames(
            "flex shrink-0 flex-wrap items-center justify-between gap-4 border-b border-gray-200 dark:border-gray-700",
            compact ? "px-4 py-3" : "px-6 py-4"
          )}>
            <div>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {ganttData.tasks.length > 0
                  ? `${ganttData.tasks.length} task${ganttData.tasks.length !== 1 ? "s" : ""}${
                      !isSingleProjectMode && selectedProjectIds.length > 1 ? ` · ${selectedProjectIds.length} projects` : ""
                    }`
                  : ""}
              </span>
            </div>
            
            <div className="flex items-center gap-3">
              {/* Project settings presets */}
              {isSingleProjectMode && projectMetadata?.kanban?.settings?.length > 1 && (
                <select
                  value=""
                  onChange={(e) => {
                    const idx = parseInt(e.target.value, 10);
                    const settings = projectMetadata?.kanban?.settings;
                    if (!settings?.[idx]) return;
                    const ps = settings[idx];
                    if (ps.color) setColorMode(ps.color);
                    if (typeof ps.font_scale === 'number') setGanttFontScale(ps.font_scale);
                    if (typeof ps.cp_highlight === 'boolean') setCriticalPathHighlight(ps.cp_highlight);
                    if (ps.period) setScalePreset(ps.period as ScalePresetKey);
                    if (typeof ps.text_overflow === 'boolean') setTextOverflow(ps.text_overflow);
                    if (typeof ps.list_collapsed === 'boolean') setTaskListCollapsed(ps.list_collapsed);
                    if (ps.assignee_filter !== undefined) setAssigneeFilter(ps.assignee_filter);
                  }}
                  className="rounded-md border border-gray-300 bg-white px-2 py-1 text-xs text-gray-700 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
                  title="Load a saved view configuration"
                >
                  <option value="">Views</option>
                  {(projectMetadata?.kanban?.settings || [])
                    .sort((a: GanttSettingsSnapshot, b: GanttSettingsSnapshot) => (b.use_count || 0) - (a.use_count || 0))
                    .map((s: GanttSettingsSnapshot, i: number) => (
                      <option key={i} value={i}>
                        {s.color} · {s.period}{s.cp_highlight ? ' · CP' : ''}{s.assignee_filter ? ' · filtered' : ''} ({s.use_count}×)
                      </option>
                    ))
                  }
                </select>
              )}

              {/* Color mode */}
              <select
                value={colorMode}
                onChange={(e) => setColorMode(e.target.value as any)}
                className="rounded-md border border-gray-300 bg-white px-2 py-1 text-xs text-gray-700 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
              >
                <option value="priority">Color: Priority</option>
                <option value="status">Color: Status</option>
                <option value="assigned">Color: Who</option>
                <option value="project">Color: Project</option>
              </select>

              {/* Scale */}
              <select
                value={scalePreset}
                onChange={(e) => {
                  const v = e.target.value as ScalePresetKey;
                  setScalePreset(v);
                  import('@/utils/wcuiPrefs').then(m => m.setWcuiPref('gantt_scale', v));
                }}
                className="rounded-md border border-gray-300 bg-white px-2 py-1 text-xs text-gray-700 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
              >
                {scaleButtons.map((b) => (
                  <option key={b.id} value={b.id}>{b.label}</option>
                ))}
              </select>

              {/* View options */}
              <select
                value=""
                onChange={(e) => {
                  const v = e.target.value;
                  if (v === 'text') {
                    const next = !textOverflow;
                    setTextOverflow(next);
                    import('@/utils/wcuiPrefs').then(m => m.setWcuiPref('gantt_show_full_text', next));
                  } else if (v === 'cp') {
                    setCriticalPathHighlight(!criticalPathHighlight);
                  } else if (v === 'font+') {
                    setGanttFontScale(s => { const n = s + 2; import('@/utils/wcuiPrefs').then(m => m.setWcuiPref('gantt_font_scale', n)); return n; });
                  } else if (v === 'font-') {
                    setGanttFontScale(s => { const n = s - 2; import('@/utils/wcuiPrefs').then(m => m.setWcuiPref('gantt_font_scale', n)); return n; });
                  }
                  e.target.value = '';
                }}
                className="rounded-md border border-gray-300 bg-white px-2 py-1 text-xs text-gray-700 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
              >
                <option value="">View</option>
                <option value="text">{textOverflow ? '✓' : '○'} Full Text</option>
                <option value="cp">{criticalPathHighlight ? '✓' : '○'} Critical Path</option>
                <option value="font+">A+ Larger</option>
                <option value="font-">A- Smaller</option>
              </select>

              {/* Assignee filter */}
              {uniqueAssignees.length > 0 && (
                <select
                  value={assigneeFilter || ''}
                  onChange={(e) => setAssigneeFilter(e.target.value || null)}
                  className="rounded-md border border-gray-300 bg-white px-2 py-1 text-xs text-gray-700 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
                >
                  <option value="">All</option>
                  {uniqueAssignees.map(a => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
              )}
              
              {/* Task list collapse toggle */}
              <button
                type="button"
                onClick={() => {
                  const next = !taskListCollapsed;
                  setTaskListCollapsed(next);
                  import('@/utils/wcuiPrefs').then(m => m.setWcuiPref('gantt_list_collapsed', next));
                }}
                className={combineClassNames(
                  "inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-medium transition",
                  taskListCollapsed
                    ? "border-indigo-300 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:border-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-200 dark:hover:bg-indigo-900/50"
                    : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
                )}
                title={taskListCollapsed ? "Expand task list columns" : "Collapse task list columns"}
              >
                <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  {taskListCollapsed ? (
                    <path d="M9 4h11M9 8h7M9 12h4M9 16h7M9 20h11M4 12l3-3v6l-3-3z" strokeLinecap="round" strokeLinejoin="round"/>
                  ) : (
                    <path d="M4 4h11M4 8h7M4 12h4M4 16h7M4 20h11M21 12l-3-3v6l3-3z" strokeLinecap="round" strokeLinejoin="round"/>
                  )}
                </svg>
                List
              </button>
              
              {/* Refresh button */}
              <button
                type="button"
                onClick={handleManualRefresh}
                disabled={isRefreshing || isLoading}
                className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-2 py-1 text-xs font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
                title={`Auto-refresh every ${AUTO_REFRESH_INTERVAL_MS / 60000} minutes${isEditModalOpen ? " (paused while editing)" : ""}`}
              >
                <svg
                  className={combineClassNames("h-3.5 w-3.5", isRefreshing && "animate-spin")}
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
              
              {/* Export dropdown */}
              <select
                value=""
                onChange={(e) => {
                  const action = e.target.value;
                  if (action === 'print-table') handlePrint();
                  else if (action === 'print-bars') handlePrintBars();
                  else if (action === 'svg') handleExportSVG();
                  else if (action === 'json') handleExportJSON();
                  e.target.value = '';
                }}
                disabled={ganttData.tasks.length === 0}
                className="rounded-md border border-gray-300 bg-white px-2 py-1 text-xs font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
                title="Print or export"
              >
                <option value="">Export</option>
                <option value="print-table">Print — Table + Bars</option>
                <option value="print-bars">Print — Bars Only</option>
                <option value="svg">Download SVG</option>
                <option value="json">Download JSON</option>
              </select>
              
              {/* Undo/Redo buttons */}
              <div className="flex gap-1 rounded-lg bg-gray-100 p-1 dark:bg-gray-800">
                <button
                  type="button"
                  onClick={handleUndo}
                  disabled={undoStack.length === 0}
                  className="rounded-md p-1.5 text-gray-600 transition hover:bg-white hover:text-gray-900 hover:shadow-sm disabled:cursor-not-allowed disabled:opacity-40 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
                  title={`Undo (${undoStack.length}) - Ctrl+Z`}
                >
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 7v6h6M21 17a9 9 0 00-9-9 9 9 0 00-6.36 2.64L3 13" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>
                <button
                  type="button"
                  onClick={handleRedo}
                  disabled={redoStack.length === 0}
                  className="rounded-md p-1.5 text-gray-600 transition hover:bg-white hover:text-gray-900 hover:shadow-sm disabled:cursor-not-allowed disabled:opacity-40 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
                  title={`Redo (${redoStack.length}) - Ctrl+Shift+Z`}
                >
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 7v6h-6M3 17a9 9 0 019-9 9 9 0 016.36 2.64L21 13" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>
              </div>
              
              {/* Admin toolbox — Shift-click to toggle */}
              <button
                type="button"
                onClick={(e) => {
                  if (e.shiftKey) setShowAdminTools(!showAdminTools);
                }}
                className={combineClassNames(
                  "rounded-md p-1.5 transition",
                  showAdminTools
                    ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
                    : "text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
                )}
                title="Shift-click for admin tools"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 15a3 3 0 100-6 3 3 0 000 6z" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>

              <span className="text-xs text-gray-400 dark:text-gray-500">
                {formatLastRefresh(lastRefreshTime)}
              </span>
            </div>

            {/* Admin toolbox — visible only when toggled via Shift-click */}
            {showAdminTools && (
              <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 dark:border-amber-800 dark:bg-amber-900/20">
                <span className="text-xs font-medium text-amber-700 dark:text-amber-300">Admin:</span>
                <button
                  type="button"
                  onClick={handleSetBaseline}
                  disabled={ganttData.tasks.length === 0}
                  className="rounded-md bg-amber-100 px-2 py-1 text-xs font-medium text-amber-800 transition hover:bg-amber-200 disabled:opacity-50 dark:bg-amber-900/40 dark:text-amber-200 dark:hover:bg-amber-900/60"
                  title="Save current start dates as baseline for slippage comparison"
                >
                  Set Baseline
                </button>
                {isSingleProjectMode && (
                  <>
                    <button
                      type="button"
                      onClick={() => {
                        if (!projectId) return;
                        const current = {
                          color: colorMode,
                          font_scale: ganttFontScale,
                          cp_highlight: criticalPathHighlight,
                          period: scalePreset,
                          text_overflow: textOverflow,
                          list_collapsed: taskListCollapsed,
                          assignee_filter: assigneeFilter,
                        };
                        const meta = { ...(projectMetadata || {}) };
                        if (!meta.kanban) meta.kanban = {};
                        meta.kanban.default_view = current;
                        saveRecord("project", {
                          model_name: "project",
                          id: projectId,
                          metadata: { mode: "update", value: meta },
                        }).then(() => {
                          setProjectMetadata({ ...meta });
                          alert("Default view saved for this project");
                        }).catch((e: any) => {
                          console.warn("[Gantt] Failed to save default view:", e);
                          alert("Failed to save: " + (e?.message || e));
                        });
                      }}
                      className="rounded-md bg-amber-100 px-2 py-1 text-xs font-medium text-amber-800 transition hover:bg-amber-200 dark:bg-amber-900/40 dark:text-amber-200 dark:hover:bg-amber-900/60"
                      title="Pin current settings as this project's default view"
                    >
                      Set Default View
                    </button>
                    {/* Sprint boundary config */}
                    <select
                      value={projectMetadata?.kanban?.sprint?.day ?? ''}
                      onChange={(e) => {
                        if (!projectId) return;
                        const day = e.target.value === '' ? null : parseInt(e.target.value, 10);
                        const meta = { ...(projectMetadata || {}) };
                        if (!meta.kanban) meta.kanban = {};
                        if (day === null) {
                          delete meta.kanban.sprint;
                        } else {
                          meta.kanban.sprint = { day, hour: 15, minute: 1 };
                        }
                        saveRecord("project", {
                          model_name: "project",
                          id: projectId,
                          metadata: { mode: "update", value: meta },
                        }).then(() => {
                          setProjectMetadata({ ...meta });
                        }).catch((e: any) => console.warn("[Gantt] Failed to save sprint config:", e));
                      }}
                      className="rounded-md border border-amber-300 bg-amber-50 px-2 py-1 text-xs text-amber-800 dark:border-amber-700 dark:bg-amber-900/30 dark:text-amber-200"
                      title="Set sprint boundary day — shows dashed vertical lines"
                    >
                      <option value="">No Sprints</option>
                      <option value="0">Sprint: Sun</option>
                      <option value="1">Sprint: Mon</option>
                      <option value="2">Sprint: Tue</option>
                      <option value="3">Sprint: Wed</option>
                      <option value="4">Sprint: Thu</option>
                      <option value="5">Sprint: Fri</option>
                      <option value="6">Sprint: Sat</option>
                    </select>
                  </>
                )}
              </div>
            )}
          </div>
          
          {/* Error display */}
          {error && (
            <div className="mx-6 mt-4 flex shrink-0 items-center justify-between rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/30 dark:text-rose-200">
              <span>{error}</span>
              <button
                type="button"
                onClick={() => refetchAll()}
                className="rounded-md border border-rose-300 px-3 py-1 text-xs font-semibold transition hover:bg-rose-100 dark:border-rose-700 dark:hover:bg-rose-900/50"
              >
                Retry
              </button>
            </div>
          )}
          
          {/* Gantt Chart */}
          <DualScrollbar className="min-w-0 min-h-0 flex-1 rounded-b-2xl" scrollSelector=".wx-chart">
            {selectedProjectIds.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <svg
                  className="mb-4 h-16 w-16 text-gray-300 dark:text-gray-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1}
                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                  />
                </svg>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                  No projects selected
                </h3>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  {showSelector 
                    ? "Select one or more projects from the sidebar to view their tasks"
                    : "No project configured for this view"}
                </p>
              </div>
            ) : isLoading && ganttData.tasks.length === 0 ? (
              <div className="flex h-full items-center justify-center">
                <div className="text-center">
                  <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600 mx-auto" />
                  <p className="text-sm text-gray-500 dark:text-gray-400">Loading tasks...</p>
                </div>
              </div>
            ) : ganttData.tasks.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <svg
                  className="mb-4 h-16 w-16 text-gray-300 dark:text-gray-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1}
                    d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
                  />
                </svg>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                  No tasks found
                </h3>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  {isSingleProjectMode
                    ? "This project has no active actions"
                    : "The selected projects have no active actions"}
                </p>
              </div>
            ) : (
              <div ref={ganttContainerRef} className="h-full w-full [&_.wx-gantt]:!h-full [&_.wx-gantt]:!w-full [&_.wx-scale]:!sticky [&_.wx-scale]:!top-0 [&_.wx-scale]:!z-10 [&_.wx-scale]:!bg-white [&_.wx-scale]:dark:!bg-gray-900" style={{ fontSize: `${12 + ganttFontScale}px`, '--gantt-font-scale': ganttFontScale, '--gantt-text-overflow': textOverflow ? 'visible' : 'hidden', '--gantt-cp-highlight': criticalPathHighlight ? '1' : '0' } as React.CSSProperties}>
                {/* Frozen top 2 rows — project header rows stay pinned while scrolling */}
                <style>{`
                  .wx-content .wx-row:nth-child(1),
                  .wx-content .wx-row:nth-child(2) {
                    position: sticky !important;
                    top: 0 !important;
                    z-index: 5 !important;
                    background: var(--wx-background, #fff) !important;
                    box-shadow: 0 1px 0 rgba(0,0,0,0.08);
                  }
                  .wx-content .wx-row:nth-child(2) {
                    top: ${38 + ganttFontScale}px !important;
                  }
                `}</style>
                <Willow>
                  <Gantt
                    key={`${ganttKey}-fs${ganttFontScale}`}
                    tasks={ganttData.tasks}
                    links={ganttData.links}
                    columns={activeColumns}
                    scales={activeScales}
                    start={dateRange.start}
                    end={dateRange.end}
                    onItemDoubleClick={handleOpenDetailPanel}
                    onUpdateTask={handleSvarUpdateTask}
                    onAddLink={handleAddLink}
                    onDeleteLink={handleDeleteLink}
                    onUpdateLink={handleUpdateLink}
                    cellHeight={38 + ganttFontScale}
                    taskTemplate={GanttTaskTemplate}
                    highlightTime={(date: Date, unit: string) => {
                      const classes: string[] = [];
                      const dateStr = `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
                      const todayStr = (() => { const t = new Date(); return `${t.getFullYear()}-${String(t.getMonth()+1).padStart(2,'0')}-${String(t.getDate()).padStart(2,'0')}`; })();

                      // Highlight today
                      if (dateStr === todayStr) {
                        classes.push('today-highlight');
                      }
                      // Sprint end lines
                      if (sprintEndDates.has(dateStr)) {
                        classes.push('sprint-boundary');
                      }
                      return classes.join(' ');
                    }}
                    init={(api) => {
                      console.log("[Gantt] init callback called, api:", api);
                      ganttApiRef.current = api;
                      api.detach(GANTT_COLOR_EVENT_TAG);
                      const rerender = () => scheduleColorRefresh();
                      api.on("render-data", rerender, { tag: GANTT_COLOR_EVENT_TAG });
                      // Intercept update-task to catch the event before it's processed
                      api.intercept("update-task", (ev: { id: string | number; task: Partial<ITask>; diff?: number; inProgress?: boolean; eventSource?: string }) => {
                        console.log("[Gantt API INTERCEPT] update-task event", {
                          id: ev.id,
                          task: ev.task,
                          diff: ev.diff,
                          inProgress: ev.inProgress,
                          eventSource: ev.eventSource,
                          hasStart: ev.task?.start !== undefined,
                          hasEnd: ev.task?.end !== undefined,
                        });
                        return ev; // Must return the event to continue processing
                      }, { tag: GANTT_COLOR_EVENT_TAG });
                      // Handle task updates from drag-and-drop via API event
                      api.on("update-task", (ev: { id: string | number; task: Partial<ITask> }) => {
                        console.log("[Gantt API] update-task event fired", ev);
                        if (handleSvarUpdateTaskRef.current) {
                          handleSvarUpdateTaskRef.current(ev);
                        }
                        rerender();
                      }, { tag: GANTT_COLOR_EVENT_TAG });
                      // Intercept drag-task to see what happens during drag
                      api.intercept("drag-task", (ev: { id?: string | number; width?: number; left?: number; top?: number; inProgress?: boolean }) => {
                        console.log("[Gantt API INTERCEPT] drag-task event", {
                          id: ev.id,
                          width: ev.width,
                          left: ev.left,
                          top: ev.top,
                          inProgress: ev.inProgress,
                          eventType: ev.width !== undefined ? "RESIZE (edge drag)" : "MOVE (center drag)"
                        });
                        return ev;
                      }, { tag: GANTT_COLOR_EVENT_TAG });
                      // Listen for drag-task events (might fire during drag)
                      api.on("drag-task", (ev: { id?: string | number; width?: number; left?: number; inProgress?: boolean }) => {
                        console.log("[Gantt API] drag-task event fired", {
                          id: ev.id,
                          width: ev.width,
                          left: ev.left,
                          inProgress: ev.inProgress
                        });
                      }, { tag: GANTT_COLOR_EVENT_TAG });
                      // Allow vertical row reordering (drag up/down)
                      api.intercept("move-task", (ev: unknown) => {
                        return ev;
                      }, { tag: GANTT_COLOR_EVENT_TAG });
                      // Listen for move-task events (for logging only)
                      api.on("move-task", (ev: unknown) => {
                        console.log("[Gantt API] move-task event fired", ev);
                      }, { tag: GANTT_COLOR_EVENT_TAG });
                      // Also rerender when links change
                      api.on("add-link", rerender, { tag: GANTT_COLOR_EVENT_TAG });
                      api.on("delete-link", rerender, { tag: GANTT_COLOR_EVENT_TAG });
                      scheduleColorRefresh();
                    }}
                  />
                </Willow>
              </div>
            )}
          </DualScrollbar>
        </section>
      </div>
      
      {/* Edit Modal */}
      <KanbanTaskModal
        mode="edit"
        isOpen={isEditModalOpen && Boolean(editingTask)}
        title="Edit task"
        description="Update task details."
        isSaving={isSavingEdit}
        submitLabel={isSavingEdit ? "Saving..." : "Save changes"}
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
          handleEditTranslationFieldChange(entryId, field as "language" | "title" | "description", value)
        }
        onRemoveTranslation={handleRemoveEditTranslation}
        languagePickerOptions={availableEditLanguages}
        languagePickerState={editLanguagePickerState}
        onLanguagePickerToggle={handleEditLanguagePickerToggle}
        onLanguageSelectionChange={handleEditLanguageSelectionChange}
        onLanguageCustomChange={handleEditLanguageCustomChange}
        onLanguagePickerSubmit={handleEditLanguagePickerSubmit}
        onLanguagePickerCancel={handleEditLanguagePickerCancel}
        currentTask={editingTask}
        assigneeUIMode={editAssigneeUIMode}
        onAssigneeUIModeChange={setEditAssigneeUIMode}
      />
      
      {/* Link Context Menu */}
      {linkContextMenu && (
        <div
          style={{
            position: "fixed",
            top: linkContextMenu.y,
            left: linkContextMenu.x,
            zIndex: 9999,
            backgroundColor: "white",
            borderRadius: "6px",
            boxShadow: "0 4px 12px rgba(0, 0, 0, 0.15)",
            border: "1px solid #e5e7eb",
            padding: "4px 0",
            minWidth: "140px",
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={async () => {
              const linkId = linkContextMenu.linkId;
              setLinkContextMenu(null);
              await handleDeleteLink({ id: linkId });
            }}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              width: "100%",
              padding: "8px 12px",
              textAlign: "left",
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: "14px",
              color: "#dc2626",
            }}
            onMouseEnter={(e) => {
              (e.target as HTMLElement).style.backgroundColor = "#fef2f2";
            }}
            onMouseLeave={(e) => {
              (e.target as HTMLElement).style.backgroundColor = "transparent";
            }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 6h18" />
              <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
              <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
            </svg>
            Delete Link
          </button>
        </div>
      )}
    </div>

    {/* Action Detail floating window — opens on double-click, draggable + resizable */}
    {detailActionId && (
      <ActionFloatingWindow
        key={detailActionId}
        actionId={detailActionId}
        onClose={() => setDetailActionId(null)}
        onSaved={() => refetchActions()}
      />
    )}
    </>
  );
};

export default withDevIdentifier(UnifiedGantt, 'UnifiedGantt');
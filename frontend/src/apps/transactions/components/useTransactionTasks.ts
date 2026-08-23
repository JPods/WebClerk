/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * useTransactionTasks - Hook for managing tasks linked to transactions
 *
 * Provides CRUD operations for tasks/actions within a transaction context.
 */
import { useState, useCallback, useEffect, useRef } from "react";
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  TransactionTaskFormState,
  ContactOption,
  ProjectOption,
  PRIORITY_VALUES,
} from "./TransactionTaskModal.types";
import { VALUE_TO_PRIORITY } from "./TransactionTaskModal.types";

// API Action item structure
interface ActionItem {
  id: number;
  action?: string | Record<string, string>;
  description?: string | Record<string, string>;
  kind?: string;
  priority?: number;
  status?: string;
  dt_start?: number;
  dt_deadline?: number;
  dt_completed?: number;
  progress?: number;
  difficulty?: number;
  assigned_to?: Array<{ id: number | string; name: string }>;
  project_id?: number;
  project_name?: string;
  contact_id?: number;
  parent_model?: string;
  parent_id?: number;
  // Flattened fields from backend
  who_name?: string;
  who?: number | string;
  when?: number;
  what?: string;
}

interface UseTransactionTasksOptions {
  parent_model: string;
  parentId?: number;
  actionIds?: number[];
  useActionIds?: boolean; // When true, only fetch by actionIds, never by parent
  autoFetch?: boolean;
}

interface UseTransactionTasksReturn {
  tasks: TransactionTaskFormState[];
  isLoading: boolean;
  isSaving: boolean;
  isDeleting: boolean;
  error: string | null;
  fetchTasks: () => Promise<void>;
  fetchTasksByIds: (ids: number[]) => Promise<void>;
  createTask: (task: TransactionTaskFormState) => Promise<number | null>;
  updateTask: (task: TransactionTaskFormState) => Promise<boolean>;
  deleteTask: (taskId: number) => Promise<boolean>;
  contacts: ContactOption[];
  projects: ProjectOption[];
  fetchContacts: () => Promise<void>;
  fetchProjects: () => Promise<void>;
}

// Convert API action to form state
const apiToFormState = (action: ActionItem): TransactionTaskFormState => {
  // Extract title from action field
  let title = "";
  if (typeof action.action === "string") {
    title = action.action;
  } else if (action.action && typeof action.action === "object") {
    title = action.action.en || Object.values(action.action)[0] || "";
  } else if (action.what) {
    title = action.what;
  }

  // Extract description
  let description = "";
  if (typeof action.description === "string") {
    description = action.description;
  } else if (action.description && typeof action.description === "object") {
    description =
      action.description.en || Object.values(action.description)[0] || "";
  }

  // Convert assigned_to
  const assignedTo = action.assigned_to || [];
  if (action.who_name && !assignedTo.length) {
    assignedTo.push({ id: action.who || 0, name: action.who_name });
  }

  return {
    id: action.id,
    title,
    description,
    kind: (action.kind as any) || "task",
    priority: VALUE_TO_PRIORITY[action.priority || 2] || "medium",
    status: (action.status as any) || "pending",
    dt_start: action.dt_start
      ? new Date(
          action.dt_start > 1e12 ? action.dt_start : action.dt_start * 1000,
        )
          .toISOString()
          .slice(0, 16)
      : "",
    dt_deadline: action.dt_deadline
      ? new Date(
          action.dt_deadline > 1e12
            ? action.dt_deadline
            : action.dt_deadline * 1000,
        )
          .toISOString()
          .slice(0, 16)
      : "",
    dt_completed: action.dt_completed
      ? new Date(
          action.dt_completed > 1e12
            ? action.dt_completed
            : action.dt_completed * 1000,
        )
          .toISOString()
          .slice(0, 16)
      : "",
    progress: action.progress || 0,
    difficulty: action.difficulty,
    assigned_to: assignedTo.map((a) => ({ id: a.id, name: a.name })),
    project_id: action.project_id,
    project_name: action.project_name,
    kanban_column: action.kanban_column,
    parent_model: action.parent_model,
    parent_id: action.parent_id,
  };
};

// Convert form state to API payload (matches KanbanBoardPage.buildActionPayload)
const formStateToApi = (
  task: TransactionTaskFormState,
): Record<string, unknown> => {
  // Build flattened translation fields (action_en, description_en) + nested objects
  // This matches how KanbanBoardPage saves actions successfully
  const translationFields: Record<string, string> = {};
  const actionPayload: Record<string, string> = {};
  const descriptionPayload: Record<string, string> = {};

  // For now, use 'en' as default language
  const lang = "en";
  if (task.title) {
    translationFields[`action_${lang}`] = task.title;
    actionPayload[lang] = task.title;
  }
  if (task.description) {
    translationFields[`description_${lang}`] = task.description;
    descriptionPayload[lang] = task.description;
  }

  const payload: Record<string, unknown> = {
    // Flattened translation fields (required by backend)
    ...translationFields,
    // Nested objects (also included for compatibility)
    ...(Object.keys(actionPayload).length ? { action: actionPayload } : {}),
    ...(Object.keys(descriptionPayload).length
      ? { description: descriptionPayload }
      : {}),
    // Languages array
    languages: Object.keys(actionPayload).length > 0 ? [lang] : [],
    kind: task.kind,
    priority: { low: 1, medium: 2, high: 3, critical: 4 }[task.priority] || 2,
    // Map status values to backend-expected format
    status: (() => {
      switch (task.status) {
        case "done":
          return "done";
        case "in_progress":
          return "In progress";
        case "blocked":
          return "On hold";
        case "review":
          return "review";
        case "pending":
          return "pending";
        case "canceled":
          return "canceled";
        default:
          return task.status;
      }
    })(),
    progress: task.progress,
    difficulty: task.difficulty,
  };

  // Handle dates - convert to timestamp milliseconds
  if (task.dt_start) {
    const dt = new Date(task.dt_start);
    if (!isNaN(dt.getTime())) {
      payload.dt_start = dt.getTime();
    }
  }
  if (task.dt_deadline) {
    const dt = new Date(task.dt_deadline);
    if (!isNaN(dt.getTime())) {
      payload.dt_deadline = dt.getTime();
    }
  }
  if (task.dt_completed) {
    const dt = new Date(task.dt_completed);
    if (!isNaN(dt.getTime())) {
      payload.dt_completed = dt.getTime();
    }
  }

  // Handle assignees
  if (task.assigned_to.length > 0) {
    payload.assigned_to = task.assigned_to.map((a) => ({
      id: a.id,
      name: a.name,
    }));
    if (task.assigned_to.length === 1) {
      payload.contact_id = task.assigned_to[0].id;
    }
  }

  // Handle project (matching KanbanBoardPage pattern)
  if (task.project_id) {
    const numericId = Number(task.project_id);
    payload.project_id = Number.isNaN(numericId) ? task.project_id : numericId;
  }
  if (task.project_name) {
    payload.project_name = task.project_name;
  }

  // Handle kanban column (matching KanbanBoardPage pattern)
  if (task.kanban_column) {
    payload.kanban_column = task.kanban_column;
  }

  // Handle parent transaction link
  if (task.parent_model) {
    payload.parent_model = task.parent_model;
  }
  if (task.parent_id) {
    payload.parent_id = task.parent_id;
  }

  // Add ID for updates
  if (task.id) {
    payload.id = task.id;
  }

  return payload;
};

export function useTransactionTasks({
  parent_model,
  parentId,
  actionIds = [],
  useActionIds = false,
  autoFetch = true,
}: UseTransactionTasksOptions): UseTransactionTasksReturn {
  const [tasks, setTasks] = useState<TransactionTaskFormState[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [contacts, setContacts] = useState<ContactOption[]>([]);
  const [projects, setProjects] = useState<ProjectOption[]>([]);

  // Fetch tasks for the parent transaction
  const fetchTasks = useCallback(async () => {
    if (!parentId) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await getRecords("action", {
        parent_model: parent_model,
        parent_id: parentId,
        limit: 100,
      });

      const items = Array.isArray(response)
        ? response
        : (response as any)?.results || (response as any)?.data || [];

      setTasks(items.map(apiToFormState));
    } catch (err) {
      console.error("Failed to fetch tasks:", err);
      setError("Failed to load tasks");
    } finally {
      setIsLoading(false);
    }
  }, [parent_model, parentId]);

  // Fetch tasks by specific IDs (for when order has actions.ids array)
  // Backend doesn't support id__in filter, so we fetch each action individually
  const fetchTasksByIds = useCallback(async (ids: number[]) => {
    if (!ids || ids.length === 0) return;

    setIsLoading(true);
    setError(null);

    try {
      // Use Promise.all for parallel fetching
      const fetchPromises = ids.map(async (id) => {
        try {
          const response = await getRecords("action", { id, limit: 1 });

          if ((response as any)?.record) {
            return (response as any).record;
          }

          const recordItems = Array.isArray(response)
            ? response
            : (response as any)?.results || (response as any)?.data || [];
          if (recordItems.length > 0) {
            return recordItems[0];
          }
          return null;
        } catch (e) {
          console.warn(
            `[useTransactionTasks] Failed to fetch action ${id}:`,
            e,
          );
          return null;
        }
      });

      const results = await Promise.all(fetchPromises);
      const validResults = results.filter((r): r is ActionItem => r !== null);
      setTasks(validResults.map(apiToFormState));
    } catch (err) {
      console.error("Failed to fetch tasks by IDs:", err);
      setError("Failed to load tasks");
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch contacts for assignee dropdown
  const fetchContacts = useCallback(async () => {
    try {
      const response = await getRecords("contact", {
        is_active: true,
        limit: 500,
      });
      const items = Array.isArray(response)
        ? response
        : (response as any)?.results || (response as any)?.data || [];

      const options: ContactOption[] = items
        .filter((c: any) => c.id)
        .map((c: any) => ({
          id: c.id,
          label:
            c.attention ||
            c.display_name ||
            `${c.name_first || ""} ${c.name_last || ""}`.trim() ||
            `Contact #${c.id}`,
          email: c.email,
        }));

      setContacts(options);
    } catch (err) {
      console.error("Failed to fetch contacts:", err);
    }
  }, []);

  // Fetch projects for project dropdown
  const fetchProjects = useCallback(async () => {
    try {
      const response = await getRecords("project", {
        is_active: true,
        limit: 100,
      });
      const items = Array.isArray(response)
        ? response
        : (response as any)?.results || (response as any)?.data || [];

      const options: ProjectOption[] = items
        .filter((p: any) => p.id)
        .map((p: any) => ({
          id: p.id,
          name: p.name,
          slug: p.slug,
          intent: p.intent,
        }));

      setProjects(options);
    } catch (err) {
      console.error("Failed to fetch projects:", err);
    }
  }, []);

  // Create a new task - returns the created action ID on success, or null on failure
  const createTask = useCallback(
    async (task: TransactionTaskFormState): Promise<number | null> => {
      setIsSaving(true);
      setError(null);

      try {
        const payload = formStateToApi({
          ...task,
          parent_model: parent_model,
          parent_id: parentId,
        });

        const response = await saveRecord("action", payload);

        // Extract the created action ID from response
        const createdId =
          response?.id || response?.record?.id || response?.data?.id;

        if (createdId) {
          // Refresh tasks list - include the new ID when fetching by IDs
          if (useActionIds) {
            const newIds = [...actionIds, createdId];
            await fetchTasksByIds(newIds);
          } else {
            await fetchTasks();
          }
        }

        return createdId || null;
      } catch (err) {
        console.error("Failed to create task:", err);
        setError("Failed to create task");
        return null;
      } finally {
        setIsSaving(false);
      }
    },
    [
      parent_model,
      parentId,
      fetchTasks,
      fetchTasksByIds,
      useActionIds,
      actionIds,
    ],
  );

  // Update an existing task
  const updateTask = useCallback(
    async (task: TransactionTaskFormState): Promise<boolean> => {
      if (!task.id) return false;

      setIsSaving(true);
      setError(null);

      try {
        const payload = formStateToApi(task);

        // saveRecord handles both create and update when id is included
        await saveRecord("action", payload);

        // Refresh tasks list - use fetchTasksByIds if we have specific IDs
        if (useActionIds && actionIds.length > 0) {
          await fetchTasksByIds(actionIds);
        } else {
          await fetchTasks();
        }

        return true;
      } catch (err) {
        console.error("Failed to update task:", err);
        setError("Failed to update task");
        return false;
      } finally {
        setIsSaving(false);
      }
    },
    [fetchTasks, fetchTasksByIds, useActionIds, actionIds],
  );

  // Delete a task
  const deleteTaskFn = useCallback(async (taskId: number): Promise<boolean> => {
    setIsDeleting(true);
    setError(null);

    try {
      await deleteRecord("action", taskId);

      // Remove from local state
      setTasks((prev) => prev.filter((t) => t.id !== taskId));

      return true;
    } catch (err) {
      console.error("Failed to delete task:", err);
      setError("Failed to delete task");
      return false;
    } finally {
      setIsDeleting(false);
    }
  }, []);

  // Serialize actionIds to string for stable dependency comparison
  const actionIdsKey = actionIds.join(",");

  // Fetch contacts & projects once on mount (separate from task fetching)
  const didFetchLookups = useRef(false);
  useEffect(() => {
    if (autoFetch && !didFetchLookups.current) {
      didFetchLookups.current = true;
      fetchContacts();
      fetchProjects();
    }
  }, [autoFetch, fetchContacts, fetchProjects]);

  // Auto-fetch tasks when parentId or actionIds change
  useEffect(() => {
    if (!autoFetch) return;

    if (useActionIds) {
      if (actionIds && actionIds.length > 0) {
        fetchTasksByIds(actionIds);
      }
      // Don't fetch by parent when useActionIds is true - wait for IDs
    } else if (actionIds && actionIds.length > 0) {
      fetchTasksByIds(actionIds);
    } else if (parentId) {
      fetchTasks();
    }
  }, [
    autoFetch,
    parentId,
    actionIdsKey,
    useActionIds,
    fetchTasks,
    fetchTasksByIds,
  ]);

  return {
    tasks,
    isLoading,
    isSaving,
    isDeleting,
    error,
    fetchTasks,
    fetchTasksByIds,
    createTask,
    updateTask,
    deleteTask: deleteTaskFn,
    contacts,
    projects,
    fetchContacts,
    fetchProjects,
  };
}

export default useTransactionTasks;

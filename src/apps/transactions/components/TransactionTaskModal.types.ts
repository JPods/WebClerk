/**
 * TransactionTaskModal Types
 * Type definitions for the generic task modal used in transaction contexts
 */

// Task kind/type options
export type TaskKind =
  | "task"
  | "followup"
  | "call"
  | "email"
  | "review"
  | "approve"
  | "ship"
  | "receive"
  | "inspect"
  | "other";

// Priority levels (aligned with Kanban)
export type TaskPriority = "low" | "medium" | "high" | "critical";

// Priority numeric values (for API)
export const PRIORITY_VALUES: Record<TaskPriority, number> = {
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
};

export const VALUE_TO_PRIORITY: Record<number, TaskPriority> = {
  1: "low",
  2: "medium",
  3: "high",
  4: "critical",
};

// Status options
export type TaskStatus =
  | "pending"
  | "in_progress"
  | "review"
  | "done"
  | "blocked"
  | "canceled";

// Status display configuration
export const STATUS_CONFIG: Record<
  TaskStatus,
  { label: string; color: string }
> = {
  pending: {
    label: "Pending",
    color:
      "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
  },
  in_progress: {
    label: "In Progress",
    color: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  },
  review: {
    label: "Review",
    color:
      "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400",
  },
  done: {
    label: "Done",
    color:
      "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  },
  blocked: {
    label: "Blocked",
    color: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  },
  canceled: {
    label: "Canceled",
    color: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400",
  },
};

// Assignee information
export interface AssigneeInfo {
  id: string | number;
  name: string;
  email?: string;
}

// Task form state
export interface TransactionTaskFormState {
  id?: number;
  title: string;
  description: string;
  kind: TaskKind;
  priority: TaskPriority;
  status: TaskStatus;
  dt_start?: string;
  dt_deadline?: string;
  dt_completed?: string;
  progress: number;
  difficulty?: number;
  assigned_to: AssigneeInfo[];
  project_id?: number;
  project_name?: string;
  kanban_column?: string;
  // Transaction context
  parent_type?: string; // 'order', 'invoice', etc.
  parent_id?: number;
}

// Project option for dropdown
export interface ProjectOption {
  id: number | string;
  name?: string;
  slug?: string;
  intent?: string;
}

// Contact option for assignee dropdown
export interface ContactOption {
  id: number | string;
  label: string;
  email?: string;
}

// Modal props
export interface TransactionTaskModalProps {
  /** Modal mode */
  mode: "create" | "edit";
  /** Whether modal is open */
  isOpen: boolean;
  /** Close handler */
  onClose: () => void;
  /** Submit handler */
  onSubmit: (task: TransactionTaskFormState) => Promise<void> | void;
  /** Delete handler (edit mode only) */
  onDelete?: () => Promise<void> | void;
  /** Initial task data (for edit mode) */
  initialData?: Partial<TransactionTaskFormState>;
  /** Whether currently saving */
  isSaving?: boolean;
  /** Whether currently deleting */
  isDeleting?: boolean;
  /** Error message */
  error?: string | null;
  /** Transaction context */
  transactionType?: string;
  transactionId?: number;
  /** Available projects for dropdown */
  projectOptions?: ProjectOption[];
  /** Available contacts for assignee dropdown */
  contactOptions?: ContactOption[];
  /** Custom title override */
  title?: string;
}

// Default form state
export const createDefaultTaskState = (
  transactionType?: string,
  transactionId?: number,
): TransactionTaskFormState => ({
  title: "",
  description: "",
  kind: "task",
  priority: "medium",
  status: "pending",
  dt_start: "",
  dt_deadline: "",
  dt_completed: "",
  progress: 0,
  assigned_to: [],
  parent_type: transactionType,
  parent_id: transactionId,
});

// Task kind options for dropdown
export const TASK_KIND_OPTIONS: { value: TaskKind; label: string }[] = [
  { value: "task", label: "Task" },
  { value: "followup", label: "Follow Up" },
  { value: "call", label: "Call" },
  { value: "email", label: "Email" },
  { value: "review", label: "Review" },
  { value: "approve", label: "Approve" },
  { value: "ship", label: "Ship" },
  { value: "receive", label: "Receive" },
  { value: "inspect", label: "Inspect" },
  { value: "other", label: "Other" },
];

// Priority options for dropdown
export const PRIORITY_OPTIONS: { value: TaskPriority; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];

// Status options for dropdown
export const STATUS_OPTIONS: { value: TaskStatus; label: string }[] = [
  { value: "pending", label: "Pending" },
  { value: "in_progress", label: "In Progress" },
  { value: "review", label: "Review" },
  { value: "done", label: "Done" },
  { value: "blocked", label: "Blocked" },
  { value: "canceled", label: "Canceled" },
];

// Progress options (percentage steps)
export const PROGRESS_OPTIONS = [0, 10, 25, 50, 75, 90, 100];

// Difficulty options (Fibonacci scale)
export const DIFFICULTY_OPTIONS = [1, 2, 3, 5, 8, 13, 21];

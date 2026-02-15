/**
 * ActionsPanel - Display and manage entity .actions (next steps / tasks)
 *
 * Supports two data modes:
 * 1. Embedded: data={actionEntries} - pass ActionEntry[] directly
 * 2. By IDs: actionIds={[257, 258]} - fetch Action records from API
 *
 * Based on Django ActionsMixin schema:
 * {
 *   required: boolean,
 *   status: "pending" | "done" | "blocked",
 *   who: number | string,
 *   when: number (ms epoch),
 *   what: string,
 *   kind: "followup" | "review" | "ship" | "approve" | etc.,
 *   extra: { ... }
 * }
 *
 * Role-based access:
 * - View: All roles (default)
 * - Edit: User+ roles (default)
 *
 * @example
 * // Embedded data mode
 * <ActionsPanel
 *   entityType="contact"
 *   entityId={123}
 *   data={contact.actions}
 *   isEditing={true}
 *   onChange={(actions) => setContact({ ...contact, actions })}
 *   onSave={async (actions) => await updateContact({ id, actions })}
 * />
 *
 * @example
 * // Load by IDs mode
 * <ActionsPanel
 *   entityType="contact"
 *   entityId={123}
 *   actionIds={contact.actions?.ids}
 *   isEditing={true}
 *   onActionIdsChange={(ids) => setContact({ ...contact, actions: { ids } })}
 * />
 */
import React, { useState, useEffect } from "react";
import {
  FaTasks,
  FaChevronDown,
  FaChevronUp,
  FaPlus,
  FaEdit,
  FaTrash,
  FaCheck,
  FaClock,
  FaBan,
  FaExclamationTriangle,
  FaPhone,
  FaEnvelope,
  FaClipboardCheck,
  FaTruck,
  FaThumbsUp,
} from "react-icons/fa";
import { usePermissions } from "./usePermissions";
import { getRecords } from "../../../../api/wcapi";
import { SearchableSelect } from "../../../../components/ui/dropdown/SearchableSelect";
import type {
  BasePanelProps,
  ActionEntry,
  ActionStatus,
  ActionKind,
} from "./types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** API Action item structure (from Action model) */
interface ApiActionItem {
  id: number;
  ida?: string;
  action?: string | Record<string, string>;
  description?: string | Record<string, string>;
  kind?: string;
  priority?: number | string;
  status?: string;
  dt_start?: number;
  dt_deadline?: number;
  dt_completed?: number;
  progress?: number;
  percent_complete?: number;
  difficulty?: number;
  assigned_to?: Array<{ id: number | string; name: string }>;
  project_id?: number;
  project_name?: string;
  contact_id?: number;
  parent_model?: string;
  parent_id?: number;
  who_name?: string;
  who?: number | string;
  when?: number;
  what?: string;
}

interface ActionsPanelProps
  extends Omit<
    BasePanelProps<ActionEntry | ActionEntry[]>,
    "data" | "onChange"
  > {
  /** Actions data - single action or array (embedded mode) */
  data?: ActionEntry | ActionEntry[] | { ids?: number[] };
  /** Action IDs to load from API (ID-based mode) */
  actionIds?: number[];
  /** Whether editing is enabled */
  isEditing?: boolean;
  /** Callback when actions change (local state update, embedded mode) */
  onChange?: (actions: ActionEntry[]) => void;
  /** Callback to persist actions to the database (auto-save, embedded mode) */
  onSave?: (actions: ActionEntry[]) => Promise<void>;
  /** Callback when action IDs change (ID-based mode) */
  onActionIdsChange?: (ids: number[]) => void;
  /** View mode: 'cards' or 'table' */
  viewMode?: "cards" | "table";
  /** Assignee options for the searchable dropdown */
  assigneeOptions?: Array<{ id: string; label: string }>;
  /** Project options for the searchable dropdown */
  projectOptions?: Array<{ id: string; name?: string; intent?: string }>;
}

// ---------------------------------------------------------------------------
// Status & Kind Helpers
// ---------------------------------------------------------------------------

const STATUS_CONFIG: Record<
  ActionStatus,
  { icon: React.ReactNode; color: string; bg: string; label: string }
> = {
  pending: {
    icon: <FaClock size={12} />,
    color: "text-amber-600",
    bg: "bg-amber-100 dark:bg-amber-900/30",
    label: "Pending",
  },
  in_progress: {
    icon: <FaTasks size={12} />,
    color: "text-blue-600",
    bg: "bg-blue-100 dark:bg-blue-900/30",
    label: "In Progress",
  },
  completed: {
    icon: <FaCheck size={12} />,
    color: "text-green-600",
    bg: "bg-green-100 dark:bg-green-900/30",
    label: "Completed",
  },
  cancelled: {
    icon: <FaBan size={12} />,
    color: "text-slate-500",
    bg: "bg-slate-100 dark:bg-slate-700",
    label: "Cancelled",
  },
  on_hold: {
    icon: <FaExclamationTriangle size={12} />,
    color: "text-orange-600",
    bg: "bg-orange-100 dark:bg-orange-900/30",
    label: "On Hold",
  },
};

const KIND_ICONS: Record<ActionKind, React.ReactNode> = {
  task: <FaTasks size={12} />,
  followup: <FaClock size={12} />,
  call: <FaPhone size={12} />,
  email: <FaEnvelope size={12} />,
  review: <FaClipboardCheck size={12} />,
  approve: <FaThumbsUp size={12} />,
  ship: <FaTruck size={12} />,
  other: <FaTasks size={12} />,
};

const formatDate = (ts: number | string | undefined): string => {
  if (!ts) return "--";
  const date = typeof ts === "number" ? new Date(ts) : new Date(ts);
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

// ---------------------------------------------------------------------------
// API Helpers
// ---------------------------------------------------------------------------

/** Convert API Action item to ActionEntry */
const apiToActionEntry = (action: ApiActionItem): ActionEntry => {
  // Extract title/what
  let what = "";
  if (typeof action.action === "string") {
    what = action.action;
  } else if (action.action && typeof action.action === "object") {
    what = action.action.en || Object.values(action.action)[0] || "";
  } else if (action.what) {
    what = action.what;
  }

  // Map status
  let status: ActionStatus = "pending";
  const s = action.status?.toLowerCase();
  if (s === "done" || s === "completed") status = "completed";
  else if (s === "in_progress" || s === "in progress") status = "in_progress";
  else if (s === "blocked" || s === "on hold" || s === "on_hold")
    status = "on_hold";
  else if (s === "cancelled" || s === "canceled") status = "cancelled";

  // Map priority
  let priority: ActionEntry["priority"] = "normal";
  const p =
    typeof action.priority === "number"
      ? action.priority
      : parseInt(String(action.priority) || "2", 10);
  if (p === 1) priority = "low";
  else if (p === 3) priority = "high";
  else if (p === 4) priority = "urgent";

  return {
    id: action.id,
    ida: action.ida,
    kind: (action.kind as ActionKind) || "task",
    what,
    who:
      action.who_name ||
      (typeof action.who === "string" ? action.who : undefined),
    when: action.dt_deadline || action.when,
    status,
    priority,
    notes:
      typeof action.description === "string"
        ? action.description
        : action.description?.en ||
          Object.values(action.description || {})[0] ||
          "",
    created_at: undefined,
    completed_at: action.dt_completed
      ? new Date(
          action.dt_completed > 1e12
            ? action.dt_completed
            : action.dt_completed * 1000,
        ).toISOString()
      : undefined,
    // Extended fields for table view
    progress: action.progress || action.percent_complete || 0,
    difficulty: action.difficulty,
    project_name: action.project_name,
    assigned_to: action.assigned_to,
  } as ActionEntry & {
    progress?: number;
    difficulty?: number;
    project_name?: string;
    ida?: string;
    assigned_to?: Array<{ id: number | string; name: string }>;
  };
};

// ---------------------------------------------------------------------------
// Action Card Component
// ---------------------------------------------------------------------------

interface ActionCardProps {
  action: ActionEntry;
  canEdit: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
  onStatusChange?: (status: ActionStatus) => void;
  compact?: boolean;
}

const ActionCard: React.FC<ActionCardProps> = ({
  action,
  canEdit,
  onEdit,
  onDelete,
  onStatusChange,
  compact = false,
}) => {
  const status = action.status || "pending";
  const kind = action.kind || "task";
  const statusConfig = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  const kindIcon = KIND_ICONS[kind] || KIND_ICONS.task;

  const isOverdue =
    action.when && new Date(action.when) < new Date() && status !== "completed";

  return (
    <div
      className={`border rounded-lg ${
        statusConfig.bg
      } border-slate-200 dark:border-slate-600 ${compact ? "p-2" : "p-3"}`}
    >
      <div className="flex items-start gap-3">
        {/* Kind icon */}
        <div className={`p-2 rounded ${statusConfig.color}`}>{kindIcon}</div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Header row */}
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`px-2 py-0.5 text-xs rounded font-medium ${statusConfig.color} ${statusConfig.bg}`}
            >
              {statusConfig.icon}
              <span className="ml-1 capitalize">
                {status.replace("_", " ")}
              </span>
            </span>
            <span className="text-xs text-slate-500 capitalize">{kind}</span>
            {action.priority && action.priority !== "normal" && (
              <span
                className={`px-1.5 py-0.5 text-xs rounded ${
                  action.priority === "urgent"
                    ? "bg-red-100 text-red-700"
                    : action.priority === "high"
                    ? "bg-orange-100 text-orange-700"
                    : "bg-slate-100 text-slate-600"
                }`}
              >
                {action.priority}
              </span>
            )}
          </div>

          {/* Description */}
          <p
            className={`text-sm text-slate-700 dark:text-slate-300 mt-1 ${
              compact ? "line-clamp-1" : ""
            }`}
          >
            {action.what || "No description"}
          </p>

          {/* Meta row */}
          <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
            {action.who && <span>Assigned: {action.who}</span>}
            {action.when && (
              <span className={isOverdue ? "text-red-600 font-medium" : ""}>
                Due: {formatDate(action.when)}
                {isOverdue && " (overdue)"}
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        {canEdit && (
          <div className="flex items-center gap-1">
            {status !== "completed" && onStatusChange && (
              <button
                onClick={() => onStatusChange("completed")}
                className="p-1.5 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded"
                title="Mark complete"
              >
                <FaCheck size={12} />
              </button>
            )}
            {onEdit && (
              <button
                onClick={onEdit}
                className="p-1.5 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
                title="Edit"
              >
                <FaEdit size={12} />
              </button>
            )}
            {onDelete && (
              <button
                onClick={onDelete}
                className="p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                title="Delete"
              >
                <FaTrash size={12} />
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Actions Table Component (for viewMode="table")
// ---------------------------------------------------------------------------

interface ActionsTableProps {
  actions: Array<
    ActionEntry & {
      progress?: number;
      difficulty?: number;
      project_name?: string;
      ida?: string;
      assigned_to?: Array<{ id: number | string; name: string }>;
    }
  >;
  isEditing?: boolean;
  onEdit?: (action: ActionEntry) => void;
  onDelete?: (action: ActionEntry) => void;
  onComplete?: (action: ActionEntry) => void;
}

const ActionsTable: React.FC<ActionsTableProps> = ({
  actions,
  isEditing,
  onEdit,
  onDelete,
  onComplete,
}) => {
  if (actions.length === 0) {
    return (
      <div className="text-center py-6 text-slate-500 dark:text-slate-400 text-sm">
        No actions found
      </div>
    );
  }

  const getPriorityColor = (priority?: string) => {
    switch (priority) {
      case "urgent":
        return "text-red-600 bg-red-50 dark:bg-red-900/20";
      case "high":
        return "text-orange-600 bg-orange-50 dark:bg-orange-900/20";
      case "normal":
        return "text-blue-600 bg-blue-50 dark:bg-blue-900/20";
      case "low":
        return "text-slate-500 bg-slate-50 dark:bg-slate-700";
      default:
        return "text-slate-500";
    }
  };

  const getStatusBadge = (status?: ActionStatus) => {
    const config = STATUS_CONFIG[status || "pending"];
    return (
      <span
        className={`inline-flex items-center gap-1 px-1.5 py-0.5 text-xs rounded ${config.bg} ${config.color}`}
      >
        {config.icon}
        <span className="hidden sm:inline">{config.label}</span>
      </span>
    );
  };

  return (
    <div className="overflow-auto max-h-80">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-white dark:bg-slate-800 z-10">
          <tr className="border-b dark:border-slate-600 text-left text-slate-600 dark:text-slate-400">
            <th className="py-2 px-2 font-medium">IDA</th>
            <th className="py-2 px-2 font-medium">Action</th>
            <th className="py-2 px-2 font-medium">Project</th>
            <th className="py-2 px-2 font-medium">Status</th>
            <th className="py-2 px-2 font-medium">Progress</th>
            <th className="py-2 px-2 font-medium">Priority</th>
            <th className="py-2 px-2 font-medium">Difficulty</th>
            <th className="py-2 px-2 font-medium">Assigned</th>
            {isEditing && <th className="py-2 px-2 font-medium">Actions</th>}
          </tr>
        </thead>
        <tbody>
          {actions.map((action, idx) => (
            <tr
              key={action.id || idx}
              className="border-b dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50"
            >
              <td className="py-2 px-2 text-slate-600 dark:text-slate-400 font-mono">
                {action.ida || action.id || "--"}
              </td>
              <td className="py-2 px-2 max-w-xs">
                <div className="flex items-center gap-2">
                  <span className="text-lg">
                    {KIND_ICONS[action.kind || "task"]}
                  </span>
                  <span className="truncate text-slate-800 dark:text-slate-200">
                    {action.what || "--"}
                  </span>
                </div>
              </td>
              <td className="py-2 px-2 text-slate-600 dark:text-slate-300">
                {action.project_name || "--"}
              </td>
              <td className="py-2 px-2">{getStatusBadge(action.status)}</td>
              <td className="py-2 px-2">
                <div className="flex items-center gap-1">
                  <div className="w-12 h-1.5 bg-slate-200 dark:bg-slate-600 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-500 rounded-full"
                      style={{ width: `${action.progress || 0}%` }}
                    />
                  </div>
                  <span className="text-slate-500 dark:text-slate-400">
                    {action.progress || 0}%
                  </span>
                </div>
              </td>
              <td className="py-2 px-2">
                <span
                  className={`px-1.5 py-0.5 rounded text-xs ${getPriorityColor(
                    action.priority,
                  )}`}
                >
                  {action.priority || "normal"}
                </span>
              </td>
              <td className="py-2 px-2 text-center text-slate-600 dark:text-slate-300">
                {action.difficulty ?? "--"}
              </td>
              <td className="py-2 px-2">
                {action.assigned_to?.length ? (
                  <div className="flex flex-wrap gap-1">
                    {action.assigned_to.map((a) => (
                      <span
                        key={a.id}
                        className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-slate-600 dark:text-slate-300"
                      >
                        {a.name}
                      </span>
                    ))}
                  </div>
                ) : action.who ? (
                  <span>{action.who}</span>
                ) : (
                  "--"
                )}
              </td>
              {isEditing && (
                <td className="py-2 px-2">
                  <div className="flex items-center gap-1">
                    {onEdit && (
                      <button
                        onClick={() => onEdit(action)}
                        className="p-1 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
                        title="Edit"
                      >
                        <FaEdit size={10} />
                      </button>
                    )}
                    {onDelete && (
                      <button
                        onClick={() => onDelete(action)}
                        className="p-1 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                        title="Delete"
                      >
                        <FaTrash size={10} />
                      </button>
                    )}
                  </div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Action Edit Modal (Enhanced - matches transactions ActionsModal)
// ---------------------------------------------------------------------------

interface AssigneeOption {
  id: string;
  label: string;
}

interface ProjectOption {
  id: string;
  name?: string;
  intent?: string;
}

interface ActionEditModalProps {
  isOpen: boolean;
  action?: ActionEntry;
  onClose: () => void;
  onSave: (action: ActionEntry) => void;
  assigneeOptions?: AssigneeOption[];
  projectOptions?: ProjectOption[];
}

interface ExtendedActionEntry extends ActionEntry {
  progress?: number;
  difficulty?: number;
  project_name?: string;
  project_id?: number | string;
  dt_start?: number | string;
  dt_deadline?: number | string;
  dt_completed?: number | string;
  assigned_to?: Array<{ id: string; name: string }>;
}

const ActionEditModal: React.FC<ActionEditModalProps> = ({
  isOpen,
  action,
  onClose,
  onSave,
  assigneeOptions = [],
  projectOptions = [],
}) => {
  console.log("[ActionEditModal] assigneeOptions:", assigneeOptions);
  console.log("[ActionEditModal] projectOptions:", projectOptions);

  const [assigneeSelection, setAssigneeSelection] = useState<string>("");
  const [formData, setFormData] = useState<ExtendedActionEntry>(
    action || {
      kind: "task",
      status: "pending",
      priority: "normal",
      what: "",
      who: "",
      progress: 0,
      difficulty: 30,
    },
  );

  React.useEffect(() => {
    if (action) {
      const extAction = action as ExtendedActionEntry;
      setFormData({
        ...action,
        progress: extAction.progress || 0,
        difficulty: extAction.difficulty || 30,
      });
    } else {
      setFormData({
        kind: "task",
        status: "pending",
        priority: "normal",
        what: "",
        who: "",
        progress: 0,
        difficulty: 30,
      });
    }
  }, [action, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
    onClose();
  };

  // Priority mapping
  const priorityToNumeric: Record<string, number> = {
    low: 1,
    normal: 2,
    high: 3,
    urgent: 4,
  };
  const numericToPriority: Record<number, ActionEntry["priority"]> = {
    1: "low",
    2: "normal",
    3: "high",
    4: "urgent",
  };
  const currentPriorityNumeric =
    priorityToNumeric[formData.priority || "normal"] || 2;

  // Status options matching transactions
  const statusOptions: Array<{ value: ActionStatus; label: string }> = [
    { value: "pending", label: "Pending" },
    { value: "in_progress", label: "In Progress" },
    { value: "on_hold", label: "On Hold" },
    { value: "completed", label: "Completed" },
    { value: "cancelled", label: "Cancelled" },
  ];

  // Format datetime for input
  const formatDateTimeLocal = (val?: number | string): string => {
    if (!val) return "";
    const d = typeof val === "number" ? new Date(val) : new Date(val);
    if (isNaN(d.getTime())) return "";
    return d.toISOString().slice(0, 16);
  };

  const controlClass =
    "w-full h-10 rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white";

  return (
    <div className="pointer-events-none fixed inset-0 z-[200000] flex items-stretch justify-end">
      {/* Backdrop */}
      <div
        className="pointer-events-auto absolute inset-0 bg-black/30"
        onClick={onClose}
      />
      {/* Right Panel */}
      <div className="pointer-events-auto relative z-10 ml-auto flex h-full w-full max-h-screen flex-col overflow-hidden border-l border-gray-200 bg-white shadow-2xl dark:border-gray-800 dark:bg-gray-900 sm:w-[480px] lg:w-[33vw] lg:min-w-[360px]">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-gray-200 px-5 py-4 dark:border-gray-800">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {action ? "Edit Action" : "Create Action"}
            </h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Fill in the action details below
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800"
            aria-label="Close modal"
          >
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="none">
              <path
                d="M6 6l8 8M14 6l-8 8"
                stroke="currentColor"
                strokeWidth={1.6}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          className="flex-1 space-y-3 overflow-y-auto px-5 py-4"
        >
          {/* Action Title */}
          <div>
            <label className="text-xs font-medium tracking-wide text-gray-500 dark:text-gray-400">
              action
            </label>
            <input
              type="text"
              value={formData.what || ""}
              onChange={(e) =>
                setFormData({ ...formData, what: e.target.value })
              }
              className={`mt-1 ${controlClass}`}
              placeholder="Task title or action description"
              required
            />
          </div>

          {/* Description */}
          <div>
            <label className="text-xs font-medium tracking-wide text-gray-500 dark:text-gray-400">
              description
            </label>
            <textarea
              value={formData.notes || ""}
              onChange={(e) =>
                setFormData({ ...formData, notes: e.target.value })
              }
              className={`mt-1 ${controlClass} h-auto min-h-16 resize-y`}
              rows={2}
              placeholder="Context, acceptance criteria, or notes"
            />
          </div>

          {/* Assigned To with Chips */}
          <div className="space-y-2">
            <label className="text-xs font-medium tracking-wide text-gray-500 dark:text-gray-400">
              assigned to
            </label>
            <div className="flex flex-wrap gap-2">
              {(formData.assigned_to || []).map((a) => (
                <span
                  key={a.id}
                  className="inline-flex items-center rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700 ring-1 ring-indigo-200 dark:bg-indigo-500/10 dark:text-indigo-100 dark:ring-indigo-500/40"
                >
                  {a.name}
                  <button
                    type="button"
                    className="ml-2 text-indigo-500 hover:text-rose-500"
                    onClick={() => {
                      const next = (formData.assigned_to || []).filter(
                        (x) => x.id !== a.id,
                      );
                      setFormData({ ...formData, assigned_to: next });
                    }}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
            <div className="relative z-[200001]">
              <SearchableSelect
                options={assigneeOptions.map((opt) => ({
                  value: opt.id,
                  label: opt.label,
                }))}
                value={assigneeSelection || null}
                onChange={(val) => {
                  if (!val) return;
                  const selectedId = String(val);
                  const option = assigneeOptions.find(
                    (opt) => opt.id === selectedId,
                  );
                  const label = option?.label ?? selectedId;
                  const existing = (formData.assigned_to || []).some(
                    (a) => a.id === selectedId,
                  );
                  if (!existing) {
                    setFormData({
                      ...formData,
                      assigned_to: [
                        ...(formData.assigned_to || []),
                        { id: selectedId, name: label },
                      ],
                    });
                  }
                  setAssigneeSelection("");
                }}
                placeholder="Select assignee..."
                searchPlaceholder="Search assignees..."
                clearable={false}
                noResultsMessage={
                  assigneeOptions.length === 0
                    ? "No assignees available"
                    : "No results found"
                }
              />
            </div>
          </div>

          {/* Type */}
          <div>
            <label className="text-xs font-medium tracking-wide text-gray-500 dark:text-gray-400">
              type
            </label>
            <select
              value={formData.kind || "task"}
              onChange={(e) =>
                setFormData({ ...formData, kind: e.target.value as ActionKind })
              }
              className={`mt-1 ${controlClass}`}
            >
              <option value="task">Task</option>
              <option value="followup">Follow Up</option>
              <option value="call">Call</option>
              <option value="email">Email</option>
              <option value="review">Review</option>
              <option value="approve">Approve</option>
              <option value="ship">Ship</option>
              <option value="other">Other</option>
            </select>
          </div>

          {/* Project */}
          <div className="space-y-2">
            <label className="text-xs font-medium tracking-wide text-gray-500 dark:text-gray-400">
              project
            </label>
            <div className="relative z-[200001]">
              <SearchableSelect
                options={projectOptions.map((opt) => ({
                  value: opt.id,
                  label: opt.name || opt.intent || `Project #${opt.id}`,
                }))}
                value={formData.project_id ? String(formData.project_id) : null}
                onChange={(val) => {
                  if (!val) {
                    setFormData({
                      ...formData,
                      project_id: undefined,
                      project_name: undefined,
                    });
                  } else {
                    const selectedId = String(val);
                    const option = projectOptions.find(
                      (opt) => opt.id === selectedId,
                    );
                    setFormData({
                      ...formData,
                      project_id: selectedId,
                      project_name:
                        option?.name || option?.intent || selectedId,
                    });
                  }
                }}
                placeholder="Select project..."
                searchPlaceholder="Search projects..."
                clearable={true}
                noResultsMessage={
                  projectOptions.length === 0
                    ? "No projects available"
                    : "No results found"
                }
              />
            </div>
          </div>

          {/* Priority & Difficulty Sliders */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-gray-300">
                <span>priority</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {formData.priority}
                </span>
              </div>
              <input
                type="range"
                min={1}
                max={4}
                step={1}
                value={currentPriorityNumeric}
                onChange={(e) => {
                  const next = Number(e.target.value) || 2;
                  setFormData({
                    ...formData,
                    priority: numericToPriority[next] || "normal",
                  });
                }}
                className="w-full accent-indigo-600"
              />
              <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                <span>Low</span>
                <span>Normal</span>
                <span>High</span>
                <span>Urgent</span>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-gray-300">
                <span>difficulty</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {formData.difficulty || 30}
                </span>
              </div>
              <input
                type="range"
                min={10}
                max={100}
                step={5}
                value={formData.difficulty || 30}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    difficulty: Number(e.target.value),
                  })
                }
                className="w-full accent-indigo-600"
              />
              <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                <span>Easy</span>
                <span>Hard</span>
              </div>
            </div>
          </div>

          {/* Progress Slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-gray-300">
              <span>progress</span>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {formData.progress || 0}%
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={formData.progress || 0}
              onChange={(e) => {
                const progress = Number(e.target.value);
                // Sync status based on progress
                let newStatus: ActionStatus = formData.status || "pending";
                if (progress === 0) {
                  newStatus = "pending";
                } else if (progress < 30) {
                  newStatus = "on_hold";
                } else if (progress < 100) {
                  newStatus = "in_progress";
                } else {
                  newStatus = "completed";
                }
                const updates: Partial<ExtendedActionEntry> = {
                  progress,
                  status: newStatus,
                };
                if (newStatus === "completed") {
                  updates.completed_at = new Date().toISOString();
                }
                setFormData({ ...formData, ...updates });
              }}
              className="w-full accent-indigo-600"
            />
            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>0%</span>
              <span>50%</span>
              <span>100%</span>
            </div>
          </div>

          {/* Date Pickers */}
          <div className="space-y-2">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  dt_start
                </label>
                <input
                  type="datetime-local"
                  step={60}
                  value={formatDateTimeLocal(formData.dt_start)}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      dt_start: e.target.value
                        ? new Date(e.target.value).getTime()
                        : undefined,
                    })
                  }
                  className={`mt-1 ${controlClass}`}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  dt_deadline
                </label>
                <input
                  type="datetime-local"
                  step={60}
                  value={formatDateTimeLocal(
                    formData.dt_deadline || formData.when,
                  )}
                  onChange={(e) => {
                    const ts = e.target.value
                      ? new Date(e.target.value).getTime()
                      : undefined;
                    setFormData({ ...formData, dt_deadline: ts, when: ts });
                  }}
                  className={`mt-1 ${controlClass}`}
                />
              </div>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  dt_completed
                </label>
                <input
                  type="datetime-local"
                  step={60}
                  value={formatDateTimeLocal(
                    formData.completed_at || formData.dt_completed,
                  )}
                  onChange={(e) => {
                    const ts = e.target.value
                      ? new Date(e.target.value).getTime()
                      : undefined;
                    setFormData({
                      ...formData,
                      dt_completed: ts,
                      completed_at: e.target.value || undefined,
                    });
                  }}
                  className={`mt-1 ${controlClass}`}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  dt_expected
                </label>
                <input
                  type="datetime-local"
                  step={60}
                  value={formatDateTimeLocal(
                    (
                      formData as ExtendedActionEntry & {
                        dt_expected?: number | string;
                      }
                    ).dt_expected,
                  )}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      dt_expected: e.target.value
                        ? new Date(e.target.value).getTime()
                        : undefined,
                    } as ExtendedActionEntry)
                  }
                  className={`mt-1 ${controlClass}`}
                />
              </div>
            </div>
          </div>

          {/* Status Button Group */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              status
            </label>
            <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
              {statusOptions.map((opt) => {
                const active = formData.status === opt.value;
                const base =
                  "flex-1 min-w-24 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition sm:flex-none";
                const activeClass =
                  "border-indigo-500 bg-indigo-600 text-white shadow";
                const inactiveClass =
                  "border-gray-300 text-gray-700 hover:border-indigo-400 hover:text-indigo-600 dark:border-gray-700 dark:text-gray-200";
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => {
                      // Map status to progress values
                      const statusToProgress: Record<ActionStatus, number> = {
                        pending: 0,
                        on_hold: 5,
                        in_progress: 30,
                        completed: 100,
                        cancelled: 0,
                      };
                      const updates: Partial<ExtendedActionEntry> = {
                        status: opt.value,
                        progress:
                          statusToProgress[opt.value] ?? formData.progress,
                      };
                      if (opt.value === "completed") {
                        updates.completed_at = new Date().toISOString();
                      }
                      setFormData({ ...formData, ...updates });
                    }}
                    className={`${base} ${
                      active ? activeClass : inactiveClass
                    }`}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* is_active Toggle */}
          <div className="flex items-center justify-between rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 dark:border-gray-700 dark:bg-gray-800/50">
            <div>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                is_active
              </span>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Action is active and visible
              </p>
            </div>
            <button
              type="button"
              onClick={() =>
                setFormData({
                  ...formData,
                  is_active: !(
                    formData as ExtendedActionEntry & { is_active?: boolean }
                  ).is_active,
                } as ExtendedActionEntry)
              }
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
                (formData as ExtendedActionEntry & { is_active?: boolean })
                  .is_active !== false
                  ? "bg-indigo-600"
                  : "bg-gray-300 dark:bg-gray-600"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition ${
                  (formData as ExtendedActionEntry & { is_active?: boolean })
                    .is_active !== false
                    ? "translate-x-6"
                    : "translate-x-1"
                }`}
              />
            </button>
          </div>
        </form>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-gray-200 px-5 py-4 dark:border-gray-800">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => {
              onSave(formData);
              onClose();
            }}
            className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow transition hover:bg-indigo-700"
          >
            {action ? "Save" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main ActionsPanel Component
// ---------------------------------------------------------------------------

const ActionsPanel: React.FC<ActionsPanelProps> = ({
  entityType: _entityType,
  entityId: _entityId,
  data,
  actionIds,
  onActionIdsChange,
  viewMode = "cards",
  isEditing: isEditingProp = false,
  onChange,
  onSave,
  readOnly = false,
  viewRoles,
  editRoles,
  className = "",
  compact = false,
  title = "Actions",
  defaultCollapsed = false,
  assigneeOptions = [],
  projectOptions = [],
}) => {
  console.log("[ActionsPanel] assigneeOptions:", assigneeOptions);
  console.log("[ActionsPanel] projectOptions:", projectOptions);
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [showModal, setShowModal] = useState(false);
  const [editingAction, setEditingAction] = useState<ActionEntry | undefined>();
  const [isSaving, setIsSaving] = useState(false);

  // API-loaded actions state (for actionIds mode)
  const [apiActions, setApiActions] = useState<ActionEntry[]>([]);
  const [isLoadingApi, setIsLoadingApi] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // Load actions from API when actionIds is provided
  useEffect(() => {
    if (!actionIds || actionIds.length === 0) {
      setApiActions([]);
      setApiError(null);
      return;
    }

    const loadActions = async () => {
      setIsLoadingApi(true);
      setApiError(null);
      try {
        const response = await getRecords("action", { ids: actionIds });
        // Handle various response formats
        const resp = response as
          | { results?: unknown[]; data?: unknown[] }
          | unknown[];
        const records = Array.isArray(resp)
          ? resp
          : resp?.results || resp?.data || [];
        if (Array.isArray(records)) {
          const converted = records.map((r: unknown) =>
            apiToActionEntry(r as ApiActionItem),
          );
          setApiActions(converted);
        } else {
          console.warn(
            "[ActionsPanel] Unexpected API response format:",
            response,
          );
          setApiActions([]);
        }
      } catch (error) {
        console.error("[ActionsPanel] Failed to load actions:", error);
        setApiError("Failed to load actions");
        setApiActions([]);
      } finally {
        setIsLoadingApi(false);
      }
    };

    loadActions();
  }, [actionIds]);

  // Check permissions
  const { canView, canEdit: permCanEdit } = usePermissions({
    panelType: "actions",
    viewRoles,
    editRoles,
    forceReadOnly: readOnly,
  });

  // Can edit if: has permission, is in editing mode, and has onChange handler (or onActionIdsChange for ID mode)
  const canEdit =
    permCanEdit && isEditingProp && !!(onChange || onActionIdsChange);
  const isActionIdsMode = !!actionIds && actionIds.length > 0;

  if (!canView) return null;

  // Normalize to array - use API-loaded actions if in actionIds mode
  const embeddedActions: ActionEntry[] = Array.isArray(data)
    ? data
    : data && Object.keys(data).length > 0 && !("ids" in data)
    ? [data as ActionEntry]
    : [];

  const actions = isActionIdsMode ? apiActions : embeddedActions;

  const pendingCount = actions.filter(
    (a) => a.status === "pending" || !a.status,
  ).length;
  const hasRequired = actions.some(
    (a) => (a as ActionEntry & { required?: boolean }).required,
  );

  const handleAdd = () => {
    setEditingAction(undefined);
    setShowModal(true);
  };

  const handleEdit = (action: ActionEntry, index: number) => {
    setEditingAction({ ...action, id: action.id || index });
    setShowModal(true);
  };

  const handleDelete = async (index: number) => {
    if (!onChange) return;
    const newActions = actions.filter((_, i) => i !== index);

    // Update local state first
    onChange(newActions);

    // Auto-save to database
    if (onSave) {
      setIsSaving(true);
      try {
        await onSave(newActions);
      } catch (error) {
        console.error("[ActionsPanel] Auto-save failed:", error);
      } finally {
        setIsSaving(false);
      }
    }
  };

  const handleStatusChange = async (index: number, status: ActionStatus) => {
    if (!onChange) return;
    const newActions = [...actions];
    newActions[index] = { ...newActions[index], status };
    if (status === "completed") {
      newActions[index].completed_at = new Date().toISOString();
    }

    // Update local state first
    onChange(newActions);

    // Auto-save to database
    if (onSave) {
      setIsSaving(true);
      try {
        await onSave(newActions);
      } catch (error) {
        console.error("[ActionsPanel] Auto-save failed:", error);
      } finally {
        setIsSaving(false);
      }
    }
  };

  const handleSave = async (action: ActionEntry) => {
    if (!onChange) return;

    let newActions: ActionEntry[];

    if (editingAction?.id !== undefined) {
      // Update existing - always use findIndex to locate by id
      const index = actions.findIndex((a) => a.id === editingAction.id);
      if (index !== -1) {
        newActions = [...actions];
        newActions[index] = { ...action, id: editingAction.id };
      } else {
        // Fallback: append if not found
        newActions = [...actions, { ...action, id: editingAction.id }];
      }
    } else {
      // Add new
      const newAction = {
        ...action,
        id: Date.now(),
        created_at: new Date().toISOString(),
      };
      newActions = [...actions, newAction];
    }

    // Update local state first
    onChange(newActions);

    // Auto-save to database
    if (onSave) {
      setIsSaving(true);
      try {
        await onSave(newActions);
      } catch (error) {
        console.error("[ActionsPanel] Auto-save failed:", error);
      } finally {
        setIsSaving(false);
      }
    }
  };

  return (
    <div
      className={`bg-white dark:bg-slate-800 rounded-lg border border-emerald-200 dark:border-emerald-800 ${className}`}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-emerald-50 dark:bg-emerald-900/20 border-b border-emerald-200 dark:border-emerald-800 cursor-pointer rounded-t-lg"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaTasks className="text-emerald-500" size={14} />
          <h3 className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">
            {title}
          </h3>
          {pendingCount > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 rounded-full">
              {pendingCount} pending
            </span>
          )}
          {hasRequired && (
            <span className="px-1.5 py-0.5 text-xs bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded">
              Required
            </span>
          )}
          {isSaving && (
            <span className="flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400">
              <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-500" />
              Saving...
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isCollapsed ? (
            <FaChevronDown size={12} />
          ) : (
            <FaChevronUp size={12} />
          )}
        </div>
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className={`${compact ? "p-2" : "p-4"} space-y-2`}>
          {/* Loading state for API mode */}
          {isLoadingApi && (
            <div className="text-center py-6 text-slate-500 dark:text-slate-400 text-sm">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-emerald-500 mx-auto mb-2" />
              Loading actions...
            </div>
          )}

          {/* Error state */}
          {apiError && !isLoadingApi && (
            <div className="text-center py-4 text-red-500 text-sm">
              <p>{apiError}</p>
            </div>
          )}

          {/* Empty state */}
          {!isLoadingApi && !apiError && actions.length === 0 ? (
            <div className="text-center py-4 text-slate-400 text-sm">
              <FaTasks size={24} className="mx-auto mb-2 opacity-50" />
              <p>No actions defined</p>
              {canEdit && (
                <button
                  onClick={handleAdd}
                  className="mt-2 text-emerald-600 hover:underline text-xs"
                >
                  + Add first action
                </button>
              )}
            </div>
          ) : !isLoadingApi && !apiError ? (
            // Render based on viewMode
            viewMode === "table" ? (
              <>
                <ActionsTable
                  actions={actions as any}
                  isEditing={canEdit}
                  onEdit={(action) =>
                    handleEdit(
                      action,
                      actions.findIndex((a) => a.id === action.id),
                    )
                  }
                  onDelete={(action) =>
                    handleDelete(actions.findIndex((a) => a.id === action.id))
                  }
                  onComplete={(action) => {
                    const idx = actions.findIndex((a) => a.id === action.id);
                    if (idx >= 0) handleStatusChange(idx, "completed");
                  }}
                />
                {canEdit && (
                  <button
                    onClick={handleAdd}
                    className="mt-3 flex items-center gap-1 text-sm text-emerald-600 hover:text-emerald-700 dark:text-emerald-400 dark:hover:text-emerald-300"
                  >
                    <FaPlus size={10} />
                    Add Action
                  </button>
                )}
              </>
            ) : (
              <>
                {actions.map((action, index) => (
                  <ActionCard
                    key={action.id || index}
                    action={action}
                    canEdit={canEdit}
                    compact={compact}
                    onEdit={() => handleEdit(action, index)}
                    onDelete={() => handleDelete(index)}
                    onStatusChange={(status) =>
                      handleStatusChange(index, status)
                    }
                  />
                ))}
                {canEdit && (
                  <button
                    onClick={handleAdd}
                    className="mt-2 flex items-center gap-1 text-sm text-emerald-600 hover:text-emerald-700 dark:text-emerald-400 dark:hover:text-emerald-300"
                  >
                    <FaPlus size={10} />
                    Add Action
                  </button>
                )}
              </>
            )
          ) : null}
        </div>
      )}

      {/* Edit Modal */}
      <ActionEditModal
        isOpen={showModal}
        action={editingAction}
        onClose={() => setShowModal(false)}
        onSave={handleSave}
        assigneeOptions={assigneeOptions}
        projectOptions={projectOptions}
      />
    </div>
  );
};

export default ActionsPanel;

/**
 * OrderDetail - Refactored to use TransactionDetailBase
 * Extends base with order-specific fields and functionality
 * Keeps item search and lines management capabilities
 */
import React, { useCallback, useState, useEffect } from "react";
import { FaTruck, FaCheck } from "react-icons/fa";

// Import base component and shared types
import TransactionDetailBase, {
  TransactionTab,
} from "../../../components/TransactionDetailBase";
import FieldLabel from "../../../components/FieldLabel";
import AddPaymentModal from "../../../components/AddPaymentModal";

// Import existing components
import ActionsModal from "../../../components/ActionsModal";
import TransactionTaskModal from "../../../components/TransactionTaskModal";
import useTransactionTasks from "../../../components/useTransactionTasks";
import type { TransactionTaskFormState } from "../../../components/TransactionTaskModal.types";
import type { ItemSearchResult } from "../types/itemSearchType";

// Import types
import type {
  Transaction,
  TransactionLine,
  ActionItem,
} from "../../../types/transactionTypes";
import SummaryCard from "@/apps/transactions/components/SummaryCard";
import LinesCard from "@/apps/transactions/components/LinesCard";
import { saveRecord, getRecord } from "@/api/wcapi";
import { ShippingPanel } from "@/apps/common/components/panels";
// import { Dropdown } from "@/components/ui/dropdown/Dropdown";

// Order specific fields that extend base Transaction
interface Order extends Transaction {
  ida?: string;
  order_no?: string;
  sales_order_no?: string; // Backwards compatibility
  po_number?: string;
  reference?: string;
  dt?: string;
  terms?: string;
  due_date?: string;
  ship_date?: string;
  ship_via?: string;
  fob?: string;
  weight?: number;
  price_level?: string;
  priority?: string;
  // Computed from base totals
  subtotal?: number;
  tax?: number;
  total?: number;
  balance?: number;
}

// Order specific tabs
const SALES_ORDER_TABS_BEFORE: TransactionTab[] = [];

// Dynamic tabs generator with badges based on data
const getOrderTabsAfter = (_data: Transaction): TransactionTab[] => {
  return [
    { id: "shipping", label: "Shipping", icon: <FaTruck size={14} /> },
  ];
};

// Custom Order Header Component
const OrderHeader: React.FC<{
  data: Order;
  isEditing: boolean;
  onChange?: (field: keyof Order, value: unknown) => void;
  onStatusChange?: (status: string) => void;
  onPaymentAdded?: () => void;
}> = ({ data, isEditing, onChange, onPaymentAdded }) => {
  // State for Add Payment modal
  const [showAddPaymentModal, setShowAddPaymentModal] = useState(false);

  // Extract customer info from refs.links
  const customerInfo = data.refs?.links?.customer?.[0];
  const billingContact = data.refs?.links?.contact?.find(
    (c) => c.purpose === "billto",
  );
  const shippingContact = data.refs?.links?.contact?.find(
    (c) => c.purpose === "shipto",
  );

  // Get contact ID for payment - prefer billing contact, fall back to any contact
  const paymentContactId = billingContact?.id || 
    data.refs?.links?.contact?.[0]?.id ||
    null;

  const priceLable = [
    { value: "A", label: "A - Retail" },
    { value: "B", label: "B - Wholesale" },
    { value: "C", label: "C - Distributor" },
    { value: "D", label: "D - Volume" },
    { value: "E", label: "E - Special" },
  ];

  return (
    <div className="space-y-4">
      <SummaryCard
        data={data}
        isEditing={isEditing}
        onChange={onChange}
        priceLable={priceLable}
        customerInfo={customerInfo}
        billingContact={billingContact}
        shippingContact={shippingContact}
        showPayments={true}
        onAddPayment={() => setShowAddPaymentModal(true)}
      />

      {/* Add Payment Modal */}
      <AddPaymentModal
        isOpen={showAddPaymentModal}
        onClose={() => setShowAddPaymentModal(false)}
        order_id={data.id || 0}
        contact_id={paymentContactId ? Number(paymentContactId) : null}
        customer_name={customerInfo?.display_name}
        orderTotal={data.totals?.total ?? data.total}
        onPaymentAdded={() => {
          setShowAddPaymentModal(false);
          onPaymentAdded?.();
        }}
      />
    </div>
  );
};

// Actions Table Component
const ActionsTable: React.FC<{
  actions: ActionItem[];
  actionIds?: number[];
  isEditing: boolean;
  isLocked?: boolean;
  onAddAction?: (action: ActionItem) => void;
  onUpdateAction?: (index: number, action: ActionItem) => void;
  onDeleteAction?: (index: number) => void;
  onCreateTask?: (task: TransactionTaskFormState) => Promise<number | null>;
  onUpdateTask?: (task: TransactionTaskFormState) => Promise<boolean>;
  onActionIdsChange?: (ids: number[]) => void;
  onAutoSaveOrderActions?: (ids: number[]) => Promise<void>;
  contacts?: Array<{ id: string | number; label: string; email?: string }>;
  projects?: Array<{ id: string | number; name?: string; intent?: string }>;
}> = ({
  actions,
  actionIds = [],
  isEditing,
  isLocked = false,
  onAddAction,
  onUpdateAction,
  onDeleteAction,
  onCreateTask,
  onUpdateTask,
  onActionIdsChange,
  onAutoSaveOrderActions,
  contacts = [],
  projects = [],
}) => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [editingAction, setEditingAction] = useState<ActionItem | null>(null);

  const getStatusColor = (status?: string) => {
    switch (status) {
      case "done":
        return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400";
      case "blocked":
        return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400";
      case "canceled":
        return "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400";
      default:
        return "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400";
    }
  };

  const getPriorityColor = (priority?: string) => {
    switch (priority) {
      case "urgent":
        return "text-red-600 dark:text-red-400";
      case "high":
        return "text-orange-600 dark:text-orange-400";
      case "low":
        return "text-slate-400 dark:text-slate-500";
      default:
        return "text-slate-600 dark:text-slate-300";
    }
  };

  const canEdit = isEditing && !isLocked;

  // Convert ActionItem to ActionFormState for edit modal
  const actionToFormState = (
    action: ActionItem,
  ): import("../../../components/ActionsModal").ActionFormState => {
    // Convert numeric priority back to string
    const priorityMap: Record<number, "low" | "medium" | "high" | "critical"> =
      {
        1: "low",
        2: "medium",
        3: "high",
        4: "critical",
      };
    const priority =
      typeof action.priority === "number"
        ? priorityMap[action.priority] ?? "medium"
        : (action.priority === "urgent"
            ? "critical"
            : action.priority === "normal"
            ? "medium"
            : (action.priority as "low" | "medium" | "high" | "critical")) ??
          "medium";

    // Get title from action object or what field
    const title =
      typeof action.action === "object"
        ? action.action?.en ?? action.what ?? ""
        : action.action ?? action.what ?? "";

    // Get description from description object or notes field
    const description =
      typeof action.description === "object"
        ? action.description?.en ?? action.notes ?? ""
        : action.description ?? action.notes ?? "";

    return {
      translations: [
        {
          id: "en",
          language: "en",
          title,
          description,
        },
      ],
      columnId: action.kanban_column ?? "",
      projectId: action.project_id?.toString() ?? "",
      priority,
      dt_deadline: action.when
        ? new Date(typeof action.when === "number" ? action.when : action.when)
            .toISOString()
            .slice(0, 16)
        : "",
      dt_start: "",
      dt_completed: action.completed_at
        ? new Date(
            typeof action.completed_at === "number"
              ? action.completed_at
              : action.completed_at,
          )
            .toISOString()
            .slice(0, 16)
        : "",
      dt_expected: "",
      assigned_to:
        action.assigned_to?.map((a) => ({ id: String(a.id), name: a.name })) ??
        [],
      difficulty: action.difficulty?.toString() ?? "10",
      progress: (action.percent_complete ?? action.progress ?? 0).toString(),
      // Map status to the status option values used by ActionsModal
      // Status options: "0" (Backlog), "5" (On hold), "30" (In progress), "review" (Review), "100" (Completed)
      percent_complete: (() => {
        const status = action.status?.toString().toLowerCase();
        if (status === "done" || status === "completed") return "100";
        if (status === "in progress" || status === "in_progress") return "30";
        if (
          status === "on hold" ||
          status === "on_hold" ||
          status === "blocked"
        )
          return "5";
        if (status === "review") return "review";
        if (status === "pending" || status === "backlog") return "0";
        // Fallback: if percent_complete is 100, mark as completed
        const progress = action.percent_complete ?? action.progress ?? 0;
        if (progress === 100) return "100";
        if (progress >= 30) return "30";
        return "0";
      })(),
      is_active: "true",
    };
  };

  // Handle IDA click to open edit modal
  const handleEditClick = (action: ActionItem) => {
    setEditingAction(action);
    setShowEditForm(true);
  };

  return (
    <div className="space-y-4">
      {/* Add Action Button */}
      {canEdit && (onAddAction || onCreateTask) && !showAddForm && (
        <div className="flex justify-end mb-1 px-2">
          <button
            type="button"
            onClick={() => setShowAddForm(true)}
            className="flex px-3 py-2 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700 transition-colors"
          >
            + Add New Action
          </button>
        </div>
      )}

      {/* Add Action Modal */}
      <ActionsModal
        isOpen={showAddForm}
        onClose={() => setShowAddForm(false)}
        onSave={async (formData) => {
          // Convert ActionFormState to TransactionTaskFormState and save via API
          if (onCreateTask) {
            // Resolve project_id and project_name (matching KanbanBoardPage pattern)
            const projectIdFromForm = formData.projectId?.trim() || "";
            const resolvedProjectId = projectIdFromForm
              ? parseInt(projectIdFromForm, 10)
              : undefined;
            const resolvedProjectName = (() => {
              const selected = projects.find(
                (p) => String(p.id) === projectIdFromForm,
              );
              if (selected?.name) return selected.name;
              if (selected?.intent) return selected.intent;
              return "";
            })();

            const taskFormState: TransactionTaskFormState = {
              title: formData.translations[0]?.title || "",
              description: formData.translations[0]?.description || "",
              kind: "task",
              priority: formData.priority,
              // Map percent_complete to status: "0"=pending, "5"=blocked, "30"=in_progress, "review"=review, "100"=done
              status: (() => {
                switch (formData.percent_complete) {
                  case "100":
                    return "done";
                  case "30":
                    return "in_progress";
                  case "5":
                    return "blocked";
                  case "review":
                    return "review";
                  default:
                    return "pending";
                }
              })(),
              dt_start: formData.dt_start || undefined,
              dt_deadline: formData.dt_deadline || undefined,
              dt_completed:
                formData.percent_complete === "100"
                  ? new Date().toISOString().slice(0, 16)
                  : undefined,
              progress: parseInt(formData.percent_complete, 10) || 0,
              difficulty: formData.difficulty
                ? parseInt(formData.difficulty, 10)
                : undefined,
              assigned_to: formData.assigned_to.map((a) => ({
                id: a.id,
                name: a.name,
              })),
              project_id: resolvedProjectId,
              project_name: resolvedProjectName || undefined,
              kanban_column: formData.columnId || undefined,
            };
            const createdId = await onCreateTask(taskFormState);
            console.log(
              "[ActionsTable] onCreateTask returned createdId:",
              createdId,
            );
            if (createdId) {
              // Add the new action ID to the order's actions.ids array
              const newIds = [...actionIds, createdId];
              if (onActionIdsChange) {
                console.log(
                  "[ActionsTable] Calling onActionIdsChange with newIds:",
                  newIds,
                );
                onActionIdsChange(newIds);
              }
              // Auto-save the order with the new action IDs
              if (onAutoSaveOrderActions) {
                console.log(
                  "[ActionsTable] Auto-saving order.actions.ids:",
                  newIds,
                );
                await onAutoSaveOrderActions(newIds);
              }
              setShowAddForm(false);
            }
          } else if (onAddAction) {
            // Fallback to local state update
            const actionItem: ActionItem = {
              what: formData.translations[0]?.title || "",
              notes: formData.translations[0]?.description || "",
              kind: "task",
              priority:
                formData.priority === "critical"
                  ? "urgent"
                  : formData.priority === "low"
                  ? "low"
                  : formData.priority === "high"
                  ? "high"
                  : "normal",
              status: formData.percent_complete === "100" ? "done" : "pending",
              who: formData.assigned_to[0]?.id
                ? Number(formData.assigned_to[0].id)
                : undefined,
              who_name: formData.assigned_to[0]?.name,
              when: formData.dt_deadline
                ? new Date(formData.dt_deadline).getTime()
                : undefined,
            };
            onAddAction(actionItem);
            setShowAddForm(false);
          }
        }}
        mode="create"
        assigneeOptions={contacts.map((c) => ({
          id: String(c.id),
          label: c.label,
        }))}
        projectOptions={projects.map((p) => ({
          id: String(p.id),
          name: p.name,
          intent: p.intent,
        }))}
      />

      {/* Edit Action Modal */}
      <ActionsModal
        isOpen={showEditForm && editingAction !== null}
        onClose={() => {
          setShowEditForm(false);
          setEditingAction(null);
        }}
        onSave={async (formData) => {
          if (!editingAction?.id) return;

          if (onUpdateTask) {
            // Convert ActionFormState to TransactionTaskFormState and update via API
            const projectIdFromForm = formData.projectId?.trim() || "";
            const resolvedProjectId = projectIdFromForm
              ? parseInt(projectIdFromForm, 10)
              : undefined;
            const resolvedProjectName = (() => {
              const selected = projects.find(
                (p) => String(p.id) === projectIdFromForm,
              );
              if (selected?.name) return selected.name;
              if (selected?.intent) return selected.intent;
              return "";
            })();

            const taskFormState: TransactionTaskFormState = {
              id: editingAction.id,
              title: formData.translations[0]?.title || "",
              description: formData.translations[0]?.description || "",
              kind:
                (editingAction.kind as TransactionTaskFormState["kind"]) ||
                "task",
              priority: formData.priority,
              // Map percent_complete to status: "0"=pending, "5"=blocked (on hold), "30"=in_progress, "review"=review, "100"=done
              status: (() => {
                switch (formData.percent_complete) {
                  case "100":
                    return "done";
                  case "30":
                    return "in_progress";
                  case "5":
                    return "blocked"; // On hold maps to blocked
                  case "review":
                    return "review";
                  default:
                    return "pending";
                }
              })() as TransactionTaskFormState["status"],
              dt_start: formData.dt_start || undefined,
              dt_deadline: formData.dt_deadline || undefined,
              dt_completed:
                formData.percent_complete === "100"
                  ? formData.dt_completed ||
                    new Date().toISOString().slice(0, 16)
                  : undefined,
              // Map percent_complete to actual progress value
              progress: (() => {
                switch (formData.percent_complete) {
                  case "100":
                    return 100;
                  case "review":
                    return 90;
                  case "30":
                    return 30;
                  case "5":
                    return 5;
                  default:
                    return 0;
                }
              })(),
              difficulty: formData.difficulty
                ? parseInt(formData.difficulty, 10)
                : undefined,
              assigned_to: formData.assigned_to.map((a) => ({
                id: a.id,
                name: a.name,
              })),
              project_id: resolvedProjectId,
              project_name: resolvedProjectName || undefined,
              kanban_column: formData.columnId || undefined,
            };

            const success = await onUpdateTask(taskFormState);
            if (success) {
              setShowEditForm(false);
              setEditingAction(null);
            }
          }
        }}
        mode="edit"
        formState={editingAction ? actionToFormState(editingAction) : undefined}
        assigneeOptions={contacts.map((c) => ({
          id: String(c.id),
          label: c.label,
        }))}
        projectOptions={projects.map((p) => ({
          id: String(p.id),
          name: p.name,
          intent: p.intent,
        }))}
      />

      {/* Actions Table */}
      {!actions.length ? (
        <div className="text-center py-12 text-slate-400">
          <FaCheck size={32} className="mx-auto mb-3 opacity-50" />
          <p>No actions on this order</p>
          {canEdit && (
            <p className="mt-2 text-xs">
              Click "Add Action" to create a task or follow-up
            </p>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto cus-bg-purple-light">
          <table className="w-full my-0">
            <thead className="bg-success-600 text-white text-sm">
              <tr>
                <th className="px-2 py-2 text-left text-xs font-semibold uppercase tracking-wide w-16">
                  IDA
                </th>
                <th className="px-2 py-2 text-left text-xs font-semibold uppercase tracking-wide">
                  Action / Description
                </th>
                <th className="px-2 py-2 text-left text-xs font-semibold uppercase tracking-wide w-28">
                  Project
                </th>
                <th className="px-2 py-2 text-left text-xs font-semibold uppercase tracking-wide w-15">
                  Status
                </th>
                <th className="px-2 py-2 text-left text-xs font-semibold uppercase tracking-wide w-16">
                  Progress
                </th>
                <th className="px-2 py-2 text-left text-xs font-semibold uppercase tracking-wide w-20">
                  Priority
                </th>
                <th className="px-2 py-2 text-left text-xs font-semibold uppercase tracking-wide w-16">
                  Difficulty
                </th>
                <th className="px-2 py-2 text-left text-xs font-semibold uppercase tracking-wide w-28">
                  Assigned
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700 text-xs">
              {actions.map((action, idx) => {
                const stripeClass =
                  idx % 2 === 1 ? "bg-slate-50 dark:bg-slate-800/30" : "";
                return (
                  <tr
                    key={action.id ?? idx}
                    className={`hover:bg-blue-50 dark:hover:bg-blue-900/20 ${stripeClass} ${
                      action.status === "done" ? "opacity-60" : ""
                    }`}
                  >
                    {/* IDA - Clickable to edit */}
                    <td className="px-2 py-1 text-xs">
                      <button
                        type="button"
                        onClick={() => handleEditClick(action)}
                        className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline font-medium cursor-pointer"
                        title="Click to edit action"
                      >
                        {action.ida ?? action.id ?? "--"}
                      </button>
                    </td>
                    {/* Action/Description */}
                    <td
                      className={`px-2 py-1 text-xs text-slate-900 dark:text-white ${
                        action.status === "done" ? "line-through" : ""
                      }`}
                    >
                      <div className="flex flex-col">
                        <span className="font-medium">
                          {typeof action.action === "object"
                            ? action.action?.en ?? action.what ?? "--"
                            : action.action ?? action.what ?? "--"}
                        </span>
                        {(action.description || action.notes) && (
                          <span className="text-slate-500 dark:text-slate-400 text-[10px] truncate max-w-200">
                            {typeof action.description === "object"
                              ? action.description?.en ?? action.notes ?? ""
                              : action.description ?? action.notes ?? ""}
                          </span>
                        )}
                      </div>
                    </td>
                    {/* Project */}
                    <td className="px-2 py-1 text-xs text-slate-600 dark:text-slate-300">
                      {action.project_name ?? "--"}
                    </td>

                    {/* Status */}
                    <td className="px-2 py-1">
                      <span
                        className={`inline-flex px-2 py-1 text-xs whitespace-nowrap rounded-full capitalize ${getStatusColor(
                          action.status,
                        )}`}
                      >
                        {action.status ?? "pending"}
                      </span>
                    </td>
                    {/* Progress */}
                    <td className="px-2 py-1 text-xs text-slate-600 dark:text-slate-300">
                      {action.percent_complete ?? action.progress ?? 0}%
                    </td>
                    {/* Priority */}
                    <td
                      className={`px-2 py-1 text-xs font-medium capitalize ${getPriorityColor(
                        typeof action.priority === "number"
                          ? ["", "low", "normal", "high", "urgent"][
                              action.priority
                            ]
                          : action.priority,
                      )}`}
                    >
                      {typeof action.priority === "number"
                        ? ["", "Low", "Normal", "High", "Critical"][
                            action.priority
                          ] ?? action.priority
                        : action.priority ?? "normal"}
                    </td>
                    {/* Difficulty */}
                    <td className="px-2 py-1 text-xs text-slate-600 dark:text-slate-300">
                      {action.difficulty ?? "--"}
                    </td>
                    {/* Assigned To */}
                    <td className="px-2 py-1 text-xs text-slate-600 dark:text-slate-300">
                      {action.assigned_to?.[0]?.name ?? action.who_name ?? "--"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot className="bg-success-600 text-white border-t-2 border-slate-300 dark:border-slate-600">
              <tr>
                <td colSpan={9} className="px-4 py-2 text-xs font-medium">
                  <span className="me-4">
                    {actions.length}{" "}
                    {actions.length === 1 ? "action" : "actions"}
                  </span>
                  <span>
                    {actions.filter((a) => a.status === "pending").length}{" "}
                    pending
                  </span>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  );
};

// Main OrderDetail Component
interface OrderDetailProps {
  isAdmin?: boolean;
  /** When true, render inline without full page layout (for use in split-view list) */
  inline?: boolean;
  /** External mode control when used inline */
  modeProp?: "view" | "edit" | "add" | null;
  /** Pre-loaded data when used inline (skips fetch) */
  dataProp?: Transaction | null;
  /** Callback after successful save */
  onSaved?: (data: Transaction) => void;
  /** Callback for cancel action in inline mode */
  // onCancelInline?: () => void;
}

// Backwards compatibility alias
// type SalesOrderDetailProps = OrderDetailProps;

const OrderDetail: React.FC<OrderDetailProps> = ({
  isAdmin = false,
  inline = false,
  modeProp,
  dataProp,
  onSaved,
}) => {
  // Task modal state
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [taskModalMode, setTaskModalMode] = useState<"create" | "edit">(
    "create",
  );
  const [editingTask, setEditingTask] =
    useState<TransactionTaskFormState | null>(null);
  const [currentOrderId, setCurrentOrderId] = useState<number | undefined>(
    dataProp?.id,
  );

  // Track action IDs from order data
  const [currentActionIds, setCurrentActionIds] = useState<number[]>(
    (dataProp as Order)?.actions?.ids ?? [],
  );

  // Update action IDs when dataProp changes
  // Merge server IDs with local state to avoid losing newly created IDs
  useEffect(() => {
    const orderData = dataProp as Order;
    console.log("[OrderDetail] dataProp changed, actions:", orderData?.actions);
    const serverActionIds = orderData?.actions?.ids ?? [];
    if (serverActionIds.length > 0) {
      // Merge server IDs with any local IDs that aren't on the server yet
      setCurrentActionIds((prevIds) => {
        const merged = [...new Set([...serverActionIds, ...prevIds])];
        console.log("[OrderDetail] Merged actionIds:", merged);
        return merged;
      });
    }
  }, [dataProp]);

  // Also update currentOrderId when dataProp changes
  useEffect(() => {
    if (dataProp?.id && dataProp.id !== currentOrderId) {
      console.log("[OrderDetail] Setting currentOrderId to:", dataProp.id);
      setCurrentOrderId(dataProp.id);
    }
  }, [dataProp?.id, currentOrderId]);

  // Task management hook - pass actionIds for fetching
  // Use useActionIds=true to prevent fetching by parent_id (which returns ALL actions)
  const hasActionIds = currentActionIds.length > 0;
  console.log("[OrderDetail] Hook params:", {
    currentOrderId,
    currentActionIds,
    hasActionIds,
  });
  const {
    tasks,
    isSaving: isTaskSaving,
    isDeleting: isTaskDeleting,
    error: taskError,
    createTask,
    updateTask,
    deleteTask,
    contacts,
    projects,
  } = useTransactionTasks({
    parent_model: "order",
    parentId: currentOrderId,
    actionIds: currentActionIds,
    useActionIds: hasActionIds, // Only use IDs-based fetching when IDs exist
    autoFetch: !!currentOrderId || hasActionIds,
  });

  const fetchOrderData = useCallback(async (id: string) => {
    const apiResult = await getRecord("order", Number(id));
    const record = (apiResult as { record?: Transaction }).record ?? apiResult;

    try {
      const totalsRes = await apiClient.get(
        `/api/transactions/orders/${id}/totals/`,
        { cache: false } as any,
      );
      const totalsPayload = totalsRes.data?.data ?? totalsRes.data;
      if (totalsPayload?.totals) {
        record.totals = totalsPayload.totals;
      }
      if (totalsPayload?.cost) {
        record.cost = totalsPayload.cost;
      }
      if (totalsPayload?.sell) {
        record.sell = totalsPayload.sell;
      }
    } catch (err) {
      console.warn("[OrderDetail] totals fetch failed, using record totals", err);
    }

    return record;
  }, []);

  // Open create task modal
  const handleOpenCreateTask = useCallback(() => {
    setEditingTask(null);
    setTaskModalMode("create");
    setIsTaskModalOpen(true);
  }, []);

  // Handle task submit
  const handleTaskSubmit = useCallback(
    async (task: TransactionTaskFormState) => {
      let success = false;
      if (taskModalMode === "create") {
        const result = await createTask(task);
        success = result !== null;
      } else {
        success = await updateTask(task);
      }
      if (success) {
        setIsTaskModalOpen(false);
        setEditingTask(null);
      }
    },
    [taskModalMode, createTask, updateTask],
  );

  // Handle task delete
  const handleTaskDelete = useCallback(async () => {
    if (editingTask?.id) {
      const success = await deleteTask(editingTask.id);
      if (success) {
        setIsTaskModalOpen(false);
        setEditingTask(null);
      }
    }
  }, [editingTask, deleteTask]);

  // Handle adding item from search (with quantity)
  const handleAddItem = useCallback(
    (item: ItemSearchResult, quantity: number) => {
      // TODO: Convert item to line and add to transaction with the specified quantity
      console.log("Add item to order:", item, "Qty:", quantity);
    },
    [],
  );

  // Handle status change
  const handleStatusChange = useCallback((newStatus: string) => {
    // TODO: Implement status update API call
    console.log("Status changed to:", newStatus);
  }, []);

  // Custom tab content renderer - receives onFieldChange from TransactionDetailBase
  // Needs to be declared after renderHeader, so move renderHeader above this

  // Custom header renderer (moved above for ActionsCard summary tab logic)
  const renderHeaderFn = useCallback(
    (
      data: Transaction,
      isEditing: boolean,
      onChange?: (field: string, value: unknown) => void,
    ) => (
      <OrderHeader
        data={data as Order}
        isEditing={isEditing}
        onChange={
          onChange as ((field: keyof Order, value: unknown) => void) | undefined
        }
        onStatusChange={handleStatusChange}
        onPaymentAdded={() => {
          // Reload to refresh order data after payment added
          window.location.reload();
        }}
      />
    ),
    [handleStatusChange],
  );

  const renderCustomTab = useCallback(
    (
      tabId: string,
      data: Transaction,
      isEditing: boolean,
      onFieldChange?: (field: string, value: unknown) => void,
    ) => {
      const orderData = data as Order;

      console.log("[renderCustomTab] tasks from hook:", tasks);
      console.log("[renderCustomTab] orderData.actions:", orderData.actions);

      // Convert tasks from hook to ActionItem format
      const tasksAsActions: ActionItem[] = tasks.map((task) => ({
        id: task.id,
        ida: task.id?.toString(),
        what: task.title,
        action: { en: task.title },
        description: { en: task.description || "" },
        notes: task.description,
        kind: task.kind || "task",
        priority:
          { low: 1, medium: 2, high: 3, critical: 4 }[task.priority] || 2,
        status: task.status === "in_progress" ? "In progress" : task.status,
        percent_complete: task.progress,
        progress: task.progress,
        difficulty: task.difficulty,
        project_id: task.project_id,
        project_name: task.project_name,
        kanban_column: task.kanban_column,
        assigned_to: task.assigned_to?.map((a) => ({ id: a.id, name: a.name })),
        who: task.assigned_to?.[0]?.id
          ? Number(task.assigned_to[0].id)
          : undefined,
        who_name: task.assigned_to?.[0]?.name,
        when: task.dt_deadline
          ? new Date(task.dt_deadline).getTime()
          : undefined,
      }));

      // Use tasks from hook if available, otherwise fall back to items in data
      const currentActions =
        tasksAsActions.length > 0
          ? tasksAsActions
          : orderData.actions?.items ?? [];

      // Action handlers that use onFieldChange to update the data
      const handleAddAction = (action: ActionItem) => {
        if (onFieldChange) {
          const newActions = [...currentActions, { ...action, id: Date.now() }];
          onFieldChange("actions", {
            ...orderData.actions,
            items: newActions,
          });
        }
      };

      const handleUpdateAction = (index: number, action: ActionItem) => {
        if (onFieldChange) {
          const newActions = [...currentActions];
          newActions[index] = action;
          onFieldChange("actions", {
            ...orderData.actions,
            items: newActions,
          });
        }
      };

      const handleDeleteAction = (index: number) => {
        if (onFieldChange) {
          const newActions = currentActions.filter((_, i) => i !== index);
          onFieldChange("actions", {
            ...orderData.actions,
            items: newActions,
          });
        }
      };

      // Handler to update the action IDs in the order
      const handleActionIdsChange = (ids: number[]) => {
        console.log("[OrderDetail] handleActionIdsChange called with:", ids);
        // Update local state for useTransactionTasks hook
        setCurrentActionIds(ids);
        if (onFieldChange) {
          console.log(
            "[OrderDetail] Updating order.actions.ids via onFieldChange",
          );
          onFieldChange("actions", {
            ...orderData.actions,
            ids: ids,
          });
        }
      };

      // Handler to auto-save the order with updated action IDs
      const handleAutoSaveOrderActions = async (ids: number[]) => {
        console.log("[OrderDetail] Auto-saving order.actions.ids:", ids);
        if (orderData.id) {
          try {
            await saveRecord("order", {
              id: orderData.id,
              actions: {
                mode: "update",
                value: {
                  ...orderData.actions,
                  ids: ids,
                },
              },
            });
            console.log("[OrderDetail] Order.actions.ids saved successfully");
          } catch (error) {
            console.error(
              "[OrderDetail] Failed to save order.actions.ids:",
              error,
            );
          }
        }
      };

      // Get current action IDs - use state which includes newly created task IDs
      // that may not be in orderData yet
      const actionIdsForTable: number[] =
        currentActionIds.length > 0
          ? currentActionIds
          : orderData.actions?.ids ?? [];

      switch (tabId) {
        case "actions":
          return (
            <ActionsTable
              actions={currentActions}
              actionIds={actionIdsForTable}
              isEditing={isEditing}
              isLocked={orderData.is_locked}
              onAddAction={handleAddAction}
              onCreateTask={createTask}
              onUpdateTask={updateTask}
              onActionIdsChange={handleActionIdsChange}
              onAutoSaveOrderActions={handleAutoSaveOrderActions}
              onUpdateAction={handleUpdateAction}
              onDeleteAction={handleDeleteAction}
              contacts={contacts}
              projects={projects}
            />
          );
        case "shipping":
          return <ShippingPanel data={orderData} />;
        default:
          return null;
      }
    },
    [
      renderHeaderFn,
      contacts,
      projects,
      createTask,
      updateTask,
      tasks,
      currentActionIds,
    ],
  );

  // Custom header renderer

  // Custom lines renderer - includes item search when editing
  const renderLines = useCallback(
    (
      lines: TransactionLine[],
      isEditing: boolean,
      data?: Transaction,
      onLinesChange?: (lines: TransactionLine[]) => void,
    ) => {
      // Get price level from transaction, default to "base" if null/undefined
      const orderData = data as Order | undefined;
      const priceLevel = orderData?.price_level || "base";

      return (
        <LinesCard
          lines={lines}
          isEditing={isEditing}
          isLocked={data?.is_locked}
          priceLevel={priceLevel}
          onDeleteLine={(lineId) => {
            // Delete line from array
            if (onLinesChange) {
              onLinesChange(lines.filter((l) => l.id !== lineId));
            }
          }}
          onUpdateLine={(lineId, field, value) => {
            // Update line field - handle nested structure
            if (onLinesChange) {
              onLinesChange(
                lines.map((l) => {
                  if (l.id !== lineId) return l;

                  // Mark line as dirty when modified
                  const baseUpdate = { ...l, _dirty: true };

                  // Map field names to nested structure
                  switch (field) {
                    case "qty":
                      return {
                        ...baseUpdate,
                        quantity: { ...l.quantity, ordered: Number(value) },
                      };
                    case "description":
                      return {
                        ...baseUpdate,
                        item: { ...l.item, description: String(value) },
                      };
                    case "unit_price":
                      const newPrice = Number(value);
                      const qty = l.quantity?.ordered ?? 0;
                      return {
                        ...baseUpdate,
                        price: {
                          ...l.price,
                          unit: newPrice,
                          extended: newPrice * qty,
                        },
                      };
                    default:
                      // For flat fields or unknown fields, try top-level
                      return { ...baseUpdate, [field]: value };
                  }
                }),
              );
            }
          }}
          onDuplicateLine={(lineId) => {
            // Duplicate line - mark as dirty since it's new
            if (onLinesChange) {
              const lineToDup = lines.find((l) => l.id === lineId);
              if (lineToDup) {
                // Omit 'id' property so the new line does not have an 'id' field at all
                const { id, ...rest } = lineToDup;
                const newLine: TransactionLine = {
                  ...rest,
                  id: Date.now(), // Assign a new unique id
                };
                onLinesChange([...lines, newLine]);
              }
            }
          }}
          onLinesChange={onLinesChange}
          onAddItem={handleAddItem}
        />
      );
    },
    [handleAddItem],
  );

  // Check if order can be edited
  const canEdit = useCallback((data: Transaction) => {
    const status = data.status?.toLowerCase();
    return status !== "complete" && status !== "canceled";
  }, []);

  // Update currentOrderId when data changes
  const handleDataLoaded = useCallback((data: Transaction) => {
    if (data?.id) {
      setCurrentOrderId(data.id);
    }
  }, []);

  // Count pending tasks for badge
  const pendingTaskCount = tasks.filter(
    (t) => t.status !== "done" && t.status !== "canceled",
  ).length;

  return (
    <>
      <TransactionDetailBase
        transactionType="order"
        typeLabel="Order"
        modelName="order"
        fetchData={fetchOrderData}
        customTabsBefore={SALES_ORDER_TABS_BEFORE}
        getCustomTabsAfter={getOrderTabsAfter}
        renderCustomTab={renderCustomTab}
        renderHeader={renderHeaderFn}
        renderLines={renderLines}
        isAdmin={isAdmin}
        canEdit={canEdit}
        inline={inline}
        modeProp={modeProp}
        dataProp={dataProp}
        onSaved={(data) => {
          handleDataLoaded(data);
          onSaved?.(data);
        }}
        onAddTask={handleOpenCreateTask}
        showTaskButton={true}
        taskCount={pendingTaskCount}
      />

      {/* Task Modal */}
      <TransactionTaskModal
        mode={taskModalMode}
        isOpen={isTaskModalOpen}
        onClose={() => {
          setIsTaskModalOpen(false);
          setEditingTask(null);
        }}
        onSubmit={handleTaskSubmit}
        onDelete={taskModalMode === "edit" ? handleTaskDelete : undefined}
        initialData={editingTask || undefined}
        isSaving={isTaskSaving}
        isDeleting={isTaskDeleting}
        error={taskError}
        transactionType="order"
        transactionId={currentOrderId}
        contactOptions={contacts}
        projectOptions={projects}
      />
    </>
  );
};

// Backwards compatibility alias
export const SalesOrderDetail = OrderDetail;

export default OrderDetail;

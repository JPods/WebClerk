/**
 * OrderDetail - Refactored to use TransactionDetailBase
 * Extends base with order-specific fields and functionality
 * Keeps item search and lines management capabilities
 */
import React, { useCallback, useState } from "react";
import { FaTruck, FaTrash, FaCheck, FaTimes, FaTasks } from "react-icons/fa";

// Import base component and shared types
import TransactionDetailBase, {
  TransactionTab,
} from "../../../components/TransactionDetailBase";
import FieldLabel from "../../../components/FieldLabel";

// Import existing components
import ActionsModal from "../../../components/ActionsModal";
import type { ItemSearchResult } from "../types/itemSearchType";

// Import types
import type {
  Transaction,
  TransactionLine,
  ActionItem,
} from "../../../types/transactionTypes";
import SummaryCard from "@/apps/transactions/components/SummaryCard";
import LinesCard from "@/apps/transactions/components/LinesCard";
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
const getOrderTabsAfter = (data: Transaction): TransactionTab[] => {
  const orderData = data as Order;
  const pendingActions =
    orderData.actions?.items?.filter((a) => a.status === "pending").length ?? 0;

  return [
    {
      id: "actions",
      label: "Actions",
      icon: <FaTasks size={14} />,
      badge: pendingActions || undefined,
    },
    { id: "shipping", label: "Shipping", icon: <FaTruck size={14} /> },
  ];
};

// Custom Order Header Component
const OrderHeader: React.FC<{
  data: Order;
  isEditing: boolean;
  onChange?: (field: keyof Order, value: unknown) => void;
  onStatusChange?: (status: string) => void;
}> = ({ data, isEditing, onChange, onStatusChange }) => {
  // Extract customer info from refs.links
  const customerInfo = data.refs?.links?.customer?.[0];
  const billingContact = data.refs?.links?.contact?.find(
    (c) => c.purpose === "billto",
  );
  const shippingContact = data.refs?.links?.contact?.find(
    (c) => c.purpose === "shipto",
  );

  const priceLable = [
    { value: "A", label: "A - Retail" },
    { value: "B", label: "B - Wholesale" },
    { value: "C", label: "C - Distributor" },
    { value: "D", label: "D - Volume" },
    { value: "E", label: "E - Special" },
  ];

  // const handlePurposeChange = (value: string) => {
  //   setValue("purpose", value);
  // };
  return (
    <SummaryCard
      data={data}
      isEditing={isEditing}
      onChange={onChange}
      priceLable={priceLable}
      customerInfo={customerInfo}
      billingContact={billingContact}
      shippingContact={shippingContact}
    />
  );
};

// Actions Table Component
const ActionsTable: React.FC<{
  actions: ActionItem[];
  isEditing: boolean;
  isLocked?: boolean;
  onAddAction?: (action: ActionItem) => void;
  onUpdateAction?: (index: number, action: ActionItem) => void;
  onDeleteAction?: (index: number) => void;
}> = ({
  actions,
  isEditing,
  isLocked = false,
  onAddAction,
  onUpdateAction,
  onDeleteAction,
}) => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [pendingDeleteIdx, setPendingDeleteIdx] = useState<number | null>(null);

  const handleDeleteClick = (idx: number) => {
    if (pendingDeleteIdx === idx) {
      onDeleteAction?.(idx);
      setPendingDeleteIdx(null);
    } else {
      setPendingDeleteIdx(idx);
    }
  };

  const handleToggleComplete = (idx: number, action: ActionItem) => {
    if (onUpdateAction) {
      const newStatus = action.status === "done" ? "pending" : "done";
      onUpdateAction(idx, {
        ...action,
        status: newStatus,
        completed_at:
          newStatus === "done" ? new Date().toISOString() : undefined,
      });
    }
  };

  const formatDate = (dateVal?: number | string) => {
    if (!dateVal) return "--";
    const date =
      typeof dateVal === "number"
        ? new Date(dateVal * 1000)
        : new Date(dateVal);
    return date.toLocaleDateString();
  };

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

  return (
    <div className="space-y-4">
      {/* Add Action Button */}
      {canEdit && onAddAction && !showAddForm && (
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
        onSubmit={(action) => {
          onAddAction?.(action);
          setShowAddForm(false);
        }}
        mode="add"
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
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50 dark:bg-slate-900/50">
              <tr>
                {canEdit && <th className="px-3 py-3 w-10"></th>}
                <th className="px-2 py-1 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                  Status
                </th>
                <th className="px-2 py-1 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                  Type
                </th>
                <th className="px-2 py-1 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                  Description
                </th>
                <th className="px-2 py-1 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide w-28">
                  Due
                </th>
                <th className="px-2 py-1 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide w-32">
                  Assigned
                </th>
                <th className="px-2 py-1 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide w-24">
                  Priority
                </th>
                {canEdit && <th className="px-3 py-3 w-24"></th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {actions.map((action, idx) => (
                <tr
                  key={action.id ?? idx}
                  className={`hover:bg-slate-50 dark:hover:bg-slate-800/50 ${
                    action.status === "done" ? "opacity-60" : ""
                  }`}
                >
                  {canEdit && (
                    <td className="px-3 py-3">
                      <button
                        type="button"
                        onClick={() => handleToggleComplete(idx, action)}
                        className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                          action.status === "done"
                            ? "bg-green-500 border-green-500 text-white"
                            : "border-slate-300 dark:border-slate-600 hover:border-green-500"
                        }`}
                        title={
                          action.status === "done"
                            ? "Mark as pending"
                            : "Mark as complete"
                        }
                      >
                        {action.status === "done" && <FaCheck size={10} />}
                      </button>
                    </td>
                  )}
                  <td className="px-4 py-1">
                    <span
                      className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(
                        action.status,
                      )}`}
                    >
                      {action.status ?? "pending"}
                    </span>
                  </td>
                  <td className="px-2 py-1 text-xs text-slate-600 dark:text-slate-300 capitalize">
                    {action.kind ?? "task"}
                  </td>
                  <td
                    className={`px-2 py-1 text-xs text-slate-900 dark:text-white ${
                      action.status === "done" ? "line-through" : ""
                    }`}
                  >
                    {action.what ?? "--"}
                  </td>
                  <td className="px-2 py-1 text-xs text-slate-600 dark:text-slate-300">
                    {formatDate(action.when)}
                  </td>
                  <td className="px-2 py-1 text-xs text-slate-600 dark:text-slate-300">
                    {action.who_name ?? "--"}
                  </td>
                  <td
                    className={`px-2 py-1 text-xs font-medium capitalize ${getPriorityColor(
                      action.priority,
                    )}`}
                  >
                    {action.priority ?? "normal"}
                  </td>
                  {canEdit && (
                    <td className="px-3 py-3 text-center">
                      {pendingDeleteIdx === idx ? (
                        <div className="flex items-center gap-1 justify-center">
                          <button
                            type="button"
                            onClick={() => handleDeleteClick(idx)}
                            className="px-2 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
                            title="Confirm delete"
                          >
                            Confirm
                          </button>
                          <button
                            type="button"
                            onClick={() => setPendingDeleteIdx(null)}
                            className="px-2 py-1 text-xs bg-slate-300 dark:bg-slate-600 text-slate-700 dark:text-slate-200 rounded hover:bg-slate-400 dark:hover:bg-slate-500 transition-colors"
                            title="Cancel"
                          >
                            <FaTimes size={10} />
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleDeleteClick(idx)}
                          className="p-1 text-slate-400 hover:text-red-500 transition-colors"
                          title="Delete action"
                        >
                          <FaTrash size={14} />
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-slate-50 dark:bg-slate-900/50 border-t-2 border-slate-300 dark:border-slate-600">
              <tr>
                <td
                  colSpan={canEdit ? 8 : 6}
                  className="px-4 py-2 text-xs text-slate-600 dark:text-slate-300"
                >
                  {actions.length} {actions.length === 1 ? "action" : "actions"}{" "}
                  • {actions.filter((a) => a.status === "pending").length}{" "}
                  pending
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  );
};

// Shipping Tab Content
const ShippingTab: React.FC<{
  data: Order;
  isEditing: boolean;
}> = ({ data }) => {
  const shippingContact = data.refs?.links?.contact?.find(
    (c) => c.purpose === "shipto",
  );
  const shippingLocation = data.refs?.links?.location?.find(
    (l) => l.type === "shipto",
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
        <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
          Shipping Details
        </h3>
        <dl className="space-y-3 text-xs">
          <div className="flex justify-between">
            <FieldLabel
              label="Ship Date"
              className="text-slate-500 dark:text-slate-400"
            />
            <dd className="text-slate-900 dark:text-white">
              {data.ship_date
                ? new Date(data.ship_date).toLocaleDateString()
                : "--"}
            </dd>
          </div>
          <div className="flex justify-between">
            <FieldLabel
              label="Ship Via"
              className="text-slate-500 dark:text-slate-400"
            />
            <dd className="text-slate-900 dark:text-white">
              {data.ship_via ?? "--"}
            </dd>
          </div>
          <div className="flex justify-between">
            <FieldLabel
              label="FOB"
              className="text-slate-500 dark:text-slate-400"
            />
            <dd className="text-slate-900 dark:text-white">
              {data.fob ?? "--"}
            </dd>
          </div>
          <div className="flex justify-between">
            <FieldLabel
              label="Weight"
              className="text-slate-500 dark:text-slate-400"
            />
            <dd className="text-slate-900 dark:text-white">
              {data.weight ? `${data.weight} kg` : "--"}
            </dd>
          </div>
        </dl>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
        <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
          Ship To Address
        </h3>
        {shippingContact ? (
          <div className="text-xs text-slate-700 dark:text-slate-300 space-y-1">
            <p className="font-medium">{shippingContact.display_name}</p>
            {shippingContact.company && <p>{shippingContact.company}</p>}
            {shippingLocation?.address && (
              <>
                <p>
                  {(shippingLocation.address as Record<string, string>).street}
                </p>
                <p>
                  {(shippingLocation.address as Record<string, string>).city},{" "}
                  {(shippingLocation.address as Record<string, string>).state}{" "}
                  {(shippingLocation.address as Record<string, string>).zip}
                </p>
                {(shippingLocation.address as Record<string, string>)
                  .country && (
                  <p>
                    {
                      (shippingLocation.address as Record<string, string>)
                        .country
                    }
                  </p>
                )}
              </>
            )}
            {shippingContact.phone && (
              <p className="mt-2">Tel: {shippingContact.phone}</p>
            )}
          </div>
        ) : (
          <p className="text-slate-400 text-xs">
            No shipping address specified
          </p>
        )}
      </div>
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
      const currentActions = orderData.actions?.items ?? [];

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

      switch (tabId) {
        case "actions":
          return (
            <ActionsTable
              actions={currentActions}
              isEditing={isEditing}
              isLocked={orderData.is_locked}
              onAddAction={handleAddAction}
              onUpdateAction={handleUpdateAction}
              onDeleteAction={handleDeleteAction}
            />
          );
        case "shipping":
          return <ShippingTab data={orderData} isEditing={isEditing} />;
        default:
          return null;
      }
    },
    [renderHeaderFn],
  );

  // Custom header renderer

  // Custom lines renderer - includes item search when editing
  const renderLines = useCallback(
    (
      lines: TransactionLine[],
      isEditing: boolean,
      data?: Transaction,
      onLinesChange?: (lines: TransactionLine[]) => void,
    ) => (
      <LinesCard
        lines={lines}
        isEditing={isEditing}
        isLocked={data?.is_locked}
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
    ),
    [handleAddItem],
  );

  // Check if order can be edited
  const canEdit = useCallback((data: Transaction) => {
    const status = data.status?.toLowerCase();
    return status !== "complete" && status !== "canceled";
  }, []);

  return (
    <TransactionDetailBase
      transactionType="order"
      typeLabel="Order"
      modelName="order"
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
      onSaved={onSaved}
    />
  );
};

// Backwards compatibility alias
export const SalesOrderDetail = OrderDetail;

export default OrderDetail;

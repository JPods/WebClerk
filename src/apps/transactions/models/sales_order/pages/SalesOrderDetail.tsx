/**
 * SalesOrderDetail - Refactored to use TransactionDetailBase
 * Extends base with sales order-specific fields and functionality
 * Keeps item search and lines management capabilities
 */
import React, { useCallback, useState } from "react";
import {
  FaShoppingCart,
  FaTruck,
  FaPrint,
  FaEnvelope,
  FaTrash,
  FaLock,
  FaPlus,
  FaCheck,
  FaTimes,
  FaTasks,
  FaChevronDown,
  FaChevronRight,
  FaCopy,
  FaExternalLinkAlt,
  FaStickyNote,
  FaEdit,
} from "react-icons/fa";

// Import base component and shared types
import TransactionDetailBase, {
  TransactionTab,
} from "../../../components/TransactionDetailBase";
import FieldLabel from "../../../components/FieldLabel";
import { TransactionPartySelector } from "../../../components/PartySelector";

// Import existing components
import SalesOrderItemSearch from "../components/SalesOrderItemSearch";
import SalesOrderStatus from "../components/SalesOrderStatus";
import LineDetailsModal from "../../../components/LineDetailsModal";
import ActionsModal from "../../../components/ActionsModal";
import type { ItemSearchResult } from "../types/itemSearchType";

// Import types
import type {
  Transaction,
  TransactionLine,
  ActionItem,
} from "../../../types/transactionTypes";
import { DropDown, Input } from "@/components/wrapper";
import { Dropdown } from "@/components/ui/dropdown/Dropdown";

// Sales Order specific fields that extend base Transaction
interface SalesOrder extends Transaction {
  ida?: string;
  sales_order_no?: string;
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

// Sales Order specific tabs
const SALES_ORDER_TABS_BEFORE: TransactionTab[] = [];

// Dynamic tabs generator with badges based on data
const getSalesOrderTabsAfter = (data: Transaction): TransactionTab[] => {
  const salesOrderData = data as SalesOrder;
  const pendingActions =
    salesOrderData.actions?.items?.filter((a) => a.status === "pending")
      .length ?? 0;

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

// Status Badge Component
const StatusBadge: React.FC<{ status?: string }> = ({ status }) => {
  const statusStyles: Record<string, string> = {
    planned:
      "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
    released:
      "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    in_progress:
      "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    hold: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
    complete:
      "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    canceled: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  };

  return (
    <span
      className={`px-2 py-1 text-xs font-medium rounded-full ${
        statusStyles[status ?? "planned"] ?? statusStyles.planned
      }`}
    >
      {status?.replace("_", " ") ?? "planned"}
    </span>
  );
};

// Utility functions
const formatCurrency = (value?: number | null): string => {
  if (value === undefined || value === null) return "--";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(value);
};

const formatNumber = (value?: number | null): string => {
  if (value === undefined || value === null) return "--";
  return value.toLocaleString();
};

// Custom Sales Order Header Component
const SalesOrderHeader: React.FC<{
  data: SalesOrder;
  isEditing: boolean;
  onChange?: (field: keyof SalesOrder, value: unknown) => void;
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
    <div className="space-y-6">
      {/* Sales Order Header Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Order Details */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaShoppingCart className="text-blue-500" />
            Sales Order Details
          </h3>
          <dl className="space-y-3 text-xs">
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Order No"
                mandatory
                locked
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono font-medium text-slate-900 dark:text-white">
                {data.ida ?? "--"}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="ID"
                locked
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono text-slate-600 dark:text-slate-300">
                {data.id ?? "--"}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Date"
                mandatory
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <Input
                  type="date"
                  value={
                    data.dt ? new Date(data.dt).toISOString().split("T")[0] : ""
                  }
                  onChange={(e) => onChange("dt", e.target.value)}
                  className="px-2 py-1 rounded text-xs bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.dt ? new Date(data.dt).toLocaleDateString() : "--"}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Due Date"
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <Input
                  type="date"
                  value={
                    data.due_date
                      ? new Date(data.due_date).toISOString().split("T")[0]
                      : ""
                  }
                  onChange={(e) => onChange("due_date", e.target.value)}
                  className="px-2 py-1 rounded text-xs bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.due_date
                    ? new Date(data.due_date).toLocaleDateString()
                    : "--"}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Terms"
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <Input
                  type="text"
                  value={data.terms ?? ""}
                  onChange={(e) => onChange("terms", e.target.value)}
                  className="px-2 py-1  rounded text-xs bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.terms ?? "--"}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="PO Number"
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <Input
                  type="text"
                  value={data.po_number ?? data.reference ?? ""}
                  onChange={(e) => onChange("po_number", e.target.value)}
                  className="px-2 py-1 rounded text-xs bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.po_number ?? data.reference ?? "--"}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Priority"
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <Input
                  type="text"
                  value={data.priority ?? ""}
                  onChange={(e) => onChange("priority", e.target.value)}
                  className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                  style={{ maxWidth: 180 }}
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.priority ?? "--"}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Price Level"
                className="text-slate-500 dark:text-slate-400"
              />
              {isEditing && onChange ? (
                <DropDown
                  id="purpose"
                  options={priceLable}
                  placeholder="Select Price Level"
                  value={data.price_level ?? ""}
                  onChange={(e) => onChange("price_level", e.target.value)}
                  className="dark:bg-dark-900"
                  disabled={!isEditing}
                />
              ) : (
                <dd className="text-slate-900 dark:text-white">
                  {data.price_level ?? "--"}
                </dd>
              )}
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Status"
                mandatory
                className="text-slate-500 dark:text-slate-400"
              />
              <dd>
                <StatusBadge status={data.status} />
              </dd>
            </div>
            {data.is_locked && (
              <div className="flex justify-between items-center pt-2 mt-2 border-t border-slate-200 dark:border-slate-700">
                <FieldLabel
                  label="Locked"
                  locked
                  className="text-slate-500 dark:text-slate-400"
                />
                <dd className="flex items-center gap-1 text-amber-600 dark:text-amber-400 font-medium">
                  <FaLock size={12} />
                  <span>Yes</span>
                </dd>
              </div>
            )}
          </dl>

          {/* Status Flow */}
          {onStatusChange && (
            <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
              <SalesOrderStatus
                currentStatus={
                  (data.status ?? "planned") as
                    | "planned"
                    | "released"
                    | "in_progress"
                    | "hold"
                    | "complete"
                    | "canceled"
                }
                onStatusChange={onStatusChange}
                readonly={!isEditing}
                showHistory={false}
              />
            </div>
          )}
        </div>

        {/* Center: Customer Info */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
            Customer
          </h3>
          {/* Customer selection or display */}
          {isEditing && !customerInfo ? (
            <div>
              <FieldLabel label="Customer" mandatory />
              <TransactionPartySelector
                transactionType="sales"
                value={data.customer_id ?? null}
                onChange={(party) =>
                  onChange && onChange("customer_id", party?.id ?? null)
                }
                className="text-sm"
              />
            </div>
          ) : customerInfo ? (
            <dl className="space-y-3 text-xs">
              <div className="flex justify-between items-center">
                <FieldLabel
                  label="Customer ID"
                  locked
                  className="text-slate-500 dark:text-slate-400"
                />
                <dd className="font-mono text-slate-600 dark:text-slate-300">
                  {data.customer_id ?? "--"}
                </dd>
              </div>
              <div className="flex justify-between items-center">
                <FieldLabel
                  label="Name"
                  className="text-slate-500 dark:text-slate-400"
                />
                <dd className="text-slate-900 dark:text-white">
                  {customerInfo.display_name ?? "--"}
                </dd>
              </div>
              <div className="flex justify-between items-center">
                <FieldLabel
                  label="IDA"
                  className="text-slate-500 dark:text-slate-400"
                />
                <dd className="font-mono text-slate-600 dark:text-slate-300">
                  {customerInfo.ida ?? "--"}
                </dd>
              </div>
            </dl>
          ) : (
            <p className="text-slate-400 text-xs">No customer linked</p>
          )}

          {billingContact && (
            <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
              <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
                Bill To
              </h4>
              <p className="text-xs text-slate-900 dark:text-white">
                {billingContact.display_name}
              </p>
              {billingContact.email && (
                <p className="text-xs text-slate-600 dark:text-slate-300">
                  {billingContact.email}
                </p>
              )}
              {billingContact.phone && (
                <p className="text-xs text-slate-600 dark:text-slate-300">
                  {billingContact.phone}
                </p>
              )}
            </div>
          )}

          {shippingContact && (
            <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
              <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
                Ship To
              </h4>
              <p className="text-xs text-slate-900 dark:text-white">
                {shippingContact.display_name}
              </p>
              {shippingContact.email && (
                <p className="text-xs text-slate-600 dark:text-slate-300">
                  {shippingContact.email}
                </p>
              )}
              {shippingContact.phone && (
                <p className="text-xs text-slate-600 dark:text-slate-300">
                  {shippingContact.phone}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Right: Totals */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
            Order Totals
          </h3>
          <dl className="space-y-3 text-xs">
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Subtotal"
                locked
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono text-slate-900 dark:text-white">
                {formatCurrency(data.totals?.subtotal ?? data.subtotal)}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Discount"
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono text-red-600 dark:text-red-400">
                {data.totals?.discount
                  ? `-${formatCurrency(data.totals.discount)}`
                  : "--"}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Tax"
                locked
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono text-slate-900 dark:text-white">
                {formatCurrency(data.totals?.tax ?? data.tax)}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Shipping"
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono text-slate-900 dark:text-white">
                {formatCurrency(data.totals?.shipping)}
              </dd>
            </div>
            <div className="flex justify-between items-center pt-2 border-t border-slate-200 dark:border-slate-700">
              <FieldLabel
                label="Total"
                mandatory
                locked
                className="text-slate-700 dark:text-slate-200 text-base"
              />
              <dd className="text-lg font-bold text-slate-900 dark:text-white">
                {formatCurrency(data.totals?.total ?? data.total)}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Cost"
                locked
                className="text-slate-500 dark:text-slate-400"
              />
              <dd className="font-mono text-slate-600 dark:text-slate-400">
                {formatCurrency(data.totals?.cost)}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <FieldLabel
                label="Margin"
                locked
                className="text-slate-500 dark:text-slate-400"
              />
              <dd
                className={`font-mono ${
                  (data.totals?.margin ?? 0) >= 0
                    ? "text-green-600 dark:text-green-400"
                    : "text-red-600 dark:text-red-400"
                }`}
              >
                {formatCurrency(data.totals?.margin)}
                {data.totals?.margin_pc != null && (
                  <span className="ml-1 text-xs">
                    ({data.totals.margin_pc.toFixed(1)}%)
                  </span>
                )}
              </dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex gap-2">
        <button
          type="button"
          className="px-4 py-2 text-xs font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors flex items-center gap-2"
        >
          <FaPrint size={14} />
          Print
        </button>
        <button
          type="button"
          className="px-4 py-2 text-xs font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors flex items-center gap-2"
        >
          <FaEnvelope size={14} />
          Email
        </button>
      </div>
    </div>
  );
};

// Sales Order Lines Component
const SalesOrderLines: React.FC<{
  lines: TransactionLine[];
  isEditing: boolean;
  isLocked?: boolean;
  onDeleteLine?: (lineId: number) => void;
  onUpdateLine?: (lineId: number, field: string, value: unknown) => void;
  onUpdateFullLine?: (line: TransactionLine) => void;
  onDuplicateLine?: (lineId: number) => void;
  onAddItem?: (item: ItemSearchResult, quantity: number) => void;
  onLinesChange?: (lines: TransactionLine[]) => void;
}> = ({
  lines,
  isEditing,
  isLocked = false,
  onDeleteLine,
  onUpdateLine,
  onUpdateFullLine,
  onDuplicateLine,
  onAddItem,
  onLinesChange,
}) => {
  // Track which line is pending delete (two-click pattern)
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);
  // Track which line/field is being edited (double-click inline editing)
  const [editingCell, setEditingCell] = useState<{
    lineId: number;
    field: string;
  } | null>(null);
  const [editValue, setEditValue] = useState<string>("");
  // Track expanded rows (for notes)
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  // Line details modal
  const [selectedLine, setSelectedLine] = useState<TransactionLine | null>(
    null,
  );
  const [showLineModal, setShowLineModal] = useState(false);
  // Selected lines for bulk actions
  const [selectedLineIds, setSelectedLineIds] = useState<Set<number>>(
    new Set(),
  );

  // Calculate totals for footer
  const lineCount = lines.length;
  const totalQty = lines.reduce((sum, l) => {
    const lRecord = l as unknown as Record<string, unknown>;
    const qty = lRecord.qty ?? l.quantity?.ordered ?? 0;
    return sum + Number(qty);
  }, 0);

  // Handle delete with two-click confirmation
  const handleDeleteClick = (lineId: number) => {
    if (pendingDeleteId === lineId) {
      // Second click - confirm delete
      onDeleteLine?.(lineId);
      setPendingDeleteId(null);
    } else {
      // First click - mark as pending
      setPendingDeleteId(lineId);
    }
  };

  // Cancel pending delete when clicking elsewhere
  const handleCancelPending = () => {
    setPendingDeleteId(null);
  };

  // Handle double-click to start inline editing
  const handleDoubleClick = (
    lineId: number,
    field: string,
    currentValue: string | number,
  ) => {
    if (isLocked || !isEditing) return;
    setEditingCell({ lineId, field });
    setEditValue(String(currentValue));
  };

  // Handle inline edit save
  const handleEditSave = () => {
    if (editingCell && onUpdateLine) {
      const value =
        editingCell.field === "qty" || editingCell.field === "unit_price"
          ? Number(editValue)
          : editValue;
      onUpdateLine(editingCell.lineId, editingCell.field, value);
    }
    setEditingCell(null);
    setEditValue("");
  };

  // Handle inline edit cancel
  const handleEditCancel = () => {
    setEditingCell(null);
    setEditValue("");
  };

  // Handle key press in edit mode
  const handleEditKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleEditSave();
    } else if (e.key === "Escape") {
      handleEditCancel();
    }
  };

  // Toggle row expansion (for notes)
  const toggleRowExpansion = (lineId: number) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(lineId)) {
      newExpanded.delete(lineId);
    } else {
      newExpanded.add(lineId);
    }
    setExpandedRows(newExpanded);
  };

  // Open line details modal
  const handleOpenLineDetails = (line: TransactionLine) => {
    setSelectedLine(line);
    setShowLineModal(true);
  };

  // Handle line modal save
  const handleLineModalSave = (updatedLine: TransactionLine) => {
    if (onUpdateFullLine) {
      onUpdateFullLine(updatedLine);
    }
  };

  // Open item in new window - accepts item id or item code
  const handleOpenItem = (itemIdOrCode: number | string) => {
    // If it's a number, use it as ID; if string, use as code
    const path =
      typeof itemIdOrCode === "number"
        ? `/products/items/${itemIdOrCode}`
        : `/products/items/code/${itemIdOrCode}`;
    window.open(path, "_blank", "width=1000,height=800");
  };

  // Toggle line selection
  const toggleLineSelection = (lineId: number) => {
    const newSelected = new Set(selectedLineIds);
    if (newSelected.has(lineId)) {
      newSelected.delete(lineId);
    } else {
      newSelected.add(lineId);
    }
    setSelectedLineIds(newSelected);
  };

  // Select/deselect all
  const toggleSelectAll = () => {
    if (selectedLineIds.size === lines.length) {
      setSelectedLineIds(new Set());
    } else {
      setSelectedLineIds(
        new Set(
          lines.map((l) => l.id).filter((id): id is number => id !== undefined),
        ),
      );
    }
  };

  // Bulk delete selected
  const handleBulkDelete = () => {
    selectedLineIds.forEach((id) => onDeleteLine?.(id));
    setSelectedLineIds(new Set());
  };

  const canEdit = isEditing && !isLocked;

  return (
    <div className="space-y-6">
      {/* Line Details Modal */}
      <LineDetailsModal
        line={selectedLine}
        isOpen={showLineModal}
        isEditing={canEdit}
        onClose={() => setShowLineModal(false)}
        onSave={handleLineModalSave}
        onOpenItem={handleOpenItem}
      />

      {/* Bulk Actions Bar */}
      {canEdit && selectedLineIds.size > 0 && (
        <div className="flex items-center gap-4 px-2 py-1 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <span className="text-xs font-medium text-blue-700 dark:text-blue-300">
            {selectedLineIds.size} line{selectedLineIds.size > 1 ? "s" : ""}{" "}
            selected
          </span>
          <button
            onClick={handleBulkDelete}
            className="px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-colors"
          >
            Delete Selected
          </button>
          <button
            onClick={() => setSelectedLineIds(new Set())}
            className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors"
          >
            Clear Selection
          </button>
        </div>
      )}

      {/* Item Search Panel - only in edit mode and when not locked */}
      {isEditing && !isLocked && onLinesChange && (
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-2">
          {/* <h3 className="font-semibold text-slate-900 dark:text-white mb-2">
            Add Items
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
            Search the catalog and add items to this order.
          </p> */}
          <SalesOrderItemSearch
            onAddItem={(item, quantity) => {
              // Extract item ID - check multiple possible field names
              const itemId = item.id ?? item.item_id ?? item.itemId ?? null;

              // Extract item code - check multiple possible field names
              const idaItem =
                item.ida_item ??
                item.item_code ??
                item.sku ??
                item.item_num ??
                item.itemNum ??
                "";

              // Extract description
              const description =
                item.description ?? item.description_text ?? item.name ?? "";

              // Extract unit of measure
              const unitMeasure =
                item.unit_of_measure ??
                item.unitOfMeasure ??
                item.unit_measure ??
                "EA";

              // Extract price - handle various formats
              let unitPrice = 0;
              if (typeof item.price === "number") {
                unitPrice = item.price;
              } else if (typeof item.price === "string") {
                unitPrice = parseFloat(item.price) || 0;
              } else if (item.price && typeof item.price === "object") {
                // Handle nested price object
                const priceObj = item.price as Record<string, unknown>;
                unitPrice = Number(
                  priceObj.base ??
                    priceObj.retail ??
                    priceObj.sell ??
                    priceObj.unit ??
                    0,
                );
              }
              // Check alternative price fields
              if (unitPrice === 0) {
                unitPrice = Number(
                  item.unit_price ?? item.priceA ?? item.price_a ?? 0,
                );
              }

              // Extract cost - handle various formats
              let unitCost = 0;
              if (typeof item.cost === "number") {
                unitCost = item.cost;
              } else if (typeof item.cost === "string") {
                unitCost = parseFloat(item.cost) || 0;
              } else if (item.cost && typeof item.cost === "object") {
                const costObj = item.cost as Record<string, unknown>;
                unitCost = Number(
                  costObj.avg ?? costObj.last ?? costObj.unit ?? 0,
                );
              }
              // Check alternative cost fields
              if (unitCost === 0) {
                unitCost = Number(item.unit_cost ?? item.costA ?? 0);
              }

              // Convert item to line and add to lines array
              const newLine: Omit<TransactionLine, "id"> = {
                item: {
                  item_id: itemId,
                  ida_item: idaItem,
                  description: description,
                  unit_measure: unitMeasure,
                },
                quantity: {
                  ordered: quantity,
                },
                price: {
                  unit: unitPrice,
                  extended: unitPrice * quantity,
                },
                cost: {
                  unit: unitCost,
                },
              };

              onLinesChange?.([...lines, newLine as TransactionLine]);

              // Also call the original handler if provided
              onAddItem?.(item, quantity);
            }}
          />
        </div>
      )}

      {/* Lines Table */}
      {!lines.length ? (
        <div className="text-center py-12 text-slate-400">
          <FaShoppingCart size={32} className="mx-auto mb-3 opacity-50" />
          <p>No line items on this order</p>
          {isEditing && (
            <p className="mt-2 text-xs">
              Use the search above to find and add products
            </p>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto cus-bg-purple-light">
          <table className="w-full my-0">
            <thead className="bg-success-600 text-white text-sm">
              <tr>
                {/* Checkbox column for bulk selection */}
                {canEdit && (
                  <th className="px-2 py-1 w-10">
                    <input
                      type="checkbox"
                      checked={
                        selectedLineIds.size === lines.length &&
                        lines.length > 0
                      }
                      onChange={toggleSelectAll}
                      className="rounded border-slate-300 dark:border-slate-600 text-blue-600 focus:ring-blue-500"
                    />
                  </th>
                )}
                {/* Expand column */}
                <th className="px-2 py-1 w-8"></th>
                <th className="px-2 py-1 text-left text-xs font-semibold uppercase tracking-wide w-32">
                  Item Code
                </th>
                <th className="px-2 py-1 w-30 text-left text-xs font-semibold uppercase tracking-wide">
                  Description
                </th>
                <th className="px-2 py-1 text-right text-xs font-semibold uppercase tracking-wide w-24">
                  Qty
                </th>
                <th className="px-2 py-1 text-right text-xs font-semibold uppercase tracking-wide w-24">
                  UOM
                </th>
                <th className="px-2 py-1 text-right text-xs font-semibold uppercase tracking-wide w-28">
                  Unit Price
                </th>
                <th className="px-2 py-1 text-right text-xs font-semibold uppercase tracking-wide w-28">
                  Unit Cost
                </th>
                <th className="px-2 py-1 text-right text-xs font-semibold uppercase tracking-wide w-28">
                  Extended
                </th>
                <th className="px-3 py-3 text-center text-xs font-semibold uppercase tracking-wide w-24">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700 text-xs">
              {lines.map((line, idx) => {
                // Handle different line data structures - use unknown first for safe casting
                const lineRecord = line as unknown as Record<string, unknown>;
                const itemCode = String(
                  lineRecord.ida_item ?? line.item?.ida_item ?? "--",
                );
                let description = String(
                  lineRecord.description ?? line.item?.description ?? "--",
                );
                if (description.length > 15) {
                  description = description.substring(0, 15) + "...";
                }
                const qty = lineRecord.qty ?? line.quantity?.ordered ?? 0;
                const uom = String(
                  lineRecord.unit_measure ?? line.item?.unit_measure ?? "EA",
                );
                const priceRecord = lineRecord.price as
                  | Record<string, unknown>
                  | undefined;
                const unitPrice =
                  priceRecord?.sell ??
                  priceRecord?.unit ??
                  line.price?.unit ??
                  0;
                const costRecord = lineRecord.cost as
                  | Record<string, unknown>
                  | undefined;
                const unitCost = costRecord?.unit ?? line.cost?.unit ?? 0;
                const extended =
                  priceRecord?.extended ??
                  line.price?.extended ??
                  Number(qty) * Number(unitPrice);
                const lineId = line.id ?? idx;
                const canEditLine = isEditing && !isLocked;
                const notesObj = lineRecord.notes as
                  | Record<string, string>
                  | undefined;
                const hasNotes =
                  notesObj &&
                  (notesObj.public || notesObj.internal || notesObj.warehouse);
                const isExpanded =
                  typeof lineId === "number" && expandedRows.has(lineId);
                const isSelected =
                  typeof lineId === "number" && selectedLineIds.has(lineId);

                // Editable cell renderer
                const renderEditableCell = (
                  field: string,
                  value: string | number,
                  displayValue: string,
                  className: string,
                  inputType: "text" | "number" = "text",
                ) => {
                  const isEditingThis =
                    editingCell?.lineId === lineId &&
                    editingCell?.field === field;

                  if (isEditingThis) {
                    return (
                      <td className={className}>
                        <input
                          type={inputType}
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          onBlur={handleEditSave}
                          onKeyDown={handleEditKeyDown}
                          autoFocus
                          className="w-full px-2 py-1 text-xs border border-blue-500 rounded bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                          style={
                            inputType === "number" ? { textAlign: "right" } : {}
                          }
                        />
                      </td>
                    );
                  }

                  return (
                    <td
                      className={`${className} ${
                        canEditLine
                          ? "cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20"
                          : ""
                      }`}
                      onDoubleClick={() =>
                        canEditLine &&
                        line.id &&
                        handleDoubleClick(line.id, field, value)
                      }
                      title={canEditLine ? "Double-click to edit" : undefined}
                    >
                      {displayValue}
                    </td>
                  );
                };

                // Stripe effect: even rows get bg-slate-50/dark:bg-slate-800/30
                const stripeClass =
                  idx % 2 === 1 ? "bg-slate-50 dark:bg-slate-800/30" : "";

                return (
                  <React.Fragment key={lineId}>
                    <tr
                      className={`hover:bg-blue-50 dark:hover:bg-blue-900/20 ${stripeClass} ${
                        isSelected ? "bg-blue-50 dark:bg-blue-900/20" : ""
                      }`}
                    >
                      {/* Checkbox for bulk selection */}
                      {canEdit && (
                        <td className="px-2 py-1 text-center">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() =>
                              typeof lineId === "number" &&
                              toggleLineSelection(lineId)
                            }
                            className="rounded border-slate-300 dark:border-slate-600 text-blue-600 focus:ring-blue-500"
                          />
                        </td>
                      )}
                      {/* Expand button for notes */}
                      <td className="px-2 py-1 text-center">
                        {hasNotes ? (
                          <button
                            type="button"
                            onClick={() =>
                              typeof lineId === "number" &&
                              toggleRowExpansion(lineId)
                            }
                            className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                            title={
                              isExpanded ? "Collapse notes" : "Expand notes"
                            }
                          >
                            {isExpanded ? (
                              <FaChevronDown size={12} />
                            ) : (
                              <FaChevronRight size={12} />
                            )}
                          </button>
                        ) : (
                          <span className="p-1 text-slate-200 dark:text-slate-700">
                            <FaStickyNote size={10} />
                          </span>
                        )}
                      </td>
                      <td className="px-2 py-1 text-xs font-mono font-medium text-slate-900 dark:text-white">
                        {itemCode}
                      </td>
                      <td className="flex px-2 py-1 text-xs text-slate-600 dark:text-slate-300 relative group justify-right items-center">
                        <span>{description}</span>
                        {line.item?.description &&
                          line.item.description.length > 15 && (
                            <span
                              className="ml-1 text-slate-400 cursor-pointer group-hover:text-blue-500"
                              title={line.item.description}
                            >
                              <FaStickyNote size={12} />
                            </span>
                          )}
                      </td>
                      {renderEditableCell(
                        "qty",
                        Number(qty),
                        formatNumber(Number(qty)),
                        "px-2 py-1 text-xs text-right text-slate-900 dark:text-white",
                        "number",
                      )}
                      <td className="px-2 py-1 text-xs text-right text-slate-600 dark:text-slate-300">
                        {String(uom)}
                      </td>
                      {renderEditableCell(
                        "unit_price",
                        Number(unitPrice),
                        formatCurrency(Number(unitPrice)),
                        "px-2 py-1 text-xs text-right text-slate-900 dark:text-white",
                        "number",
                      )}
                      <td className="px-2 py-1 text-xs text-right text-slate-600 dark:text-slate-300">
                        {formatCurrency(Number(unitCost))}
                      </td>
                      <td className="px-2 py-1 text-xs text-right font-medium text-slate-900 dark:text-white">
                        {formatCurrency(Number(extended))}
                      </td>
                      {/* Actions column - always visible */}
                      <td className="px-3 py-3 text-center">
                        <div className="flex items-center justify-center gap-1">
                          {/* Open Line Details Modal */}
                          <button
                            type="button"
                            onClick={() => handleOpenLineDetails(line)}
                            className="p-1 text-slate-400 hover:text-blue-500 transition-colors"
                            title="View/Edit line details"
                          >
                            <FaEdit size={14} />
                          </button>
                          {/* Open Item in new window */}
                          {itemCode !== "--" && (
                            <button
                              type="button"
                              onClick={() => handleOpenItem(itemCode)}
                              className="p-1 text-slate-400 hover:text-green-500 transition-colors"
                              title="Open item in new window"
                            >
                              <FaExternalLinkAlt size={12} />
                            </button>
                          )}
                          {/* Duplicate Line */}
                          {canEditLine && onDuplicateLine && line.id && (
                            <button
                              type="button"
                              onClick={() => onDuplicateLine(line.id!)}
                              className="p-1 text-slate-400 hover:text-purple-500 transition-colors"
                              title="Duplicate line"
                            >
                              <FaCopy size={12} />
                            </button>
                          )}
                          {/* Delete Line */}
                          {canEditLine &&
                            onDeleteLine &&
                            line.id &&
                            (pendingDeleteId === line.id ? (
                              <div className="flex items-center gap-1">
                                <button
                                  type="button"
                                  onClick={() => handleDeleteClick(line.id!)}
                                  className="px-2 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
                                  title="Click to confirm delete"
                                >
                                  Yes
                                </button>
                                <button
                                  type="button"
                                  onClick={handleCancelPending}
                                  className="px-2 py-1 text-xs bg-slate-300 dark:bg-slate-600 text-slate-700 dark:text-slate-200 rounded hover:bg-slate-400 dark:hover:bg-slate-500 transition-colors"
                                  title="Cancel delete"
                                >
                                  No
                                </button>
                              </div>
                            ) : (
                              <button
                                type="button"
                                onClick={() => handleDeleteClick(line.id!)}
                                className="p-1 text-slate-400 hover:text-red-500 transition-colors"
                                title="Delete line"
                              >
                                <FaTrash size={14} />
                              </button>
                            ))}
                        </div>
                      </td>
                    </tr>
                    {/* Expandable notes row */}
                    {isExpanded && hasNotes && (
                      <tr className="bg-amber-50 dark:bg-amber-900/20">
                        <td colSpan={canEdit ? 10 : 9} className="px-6 py-3">
                          <div className="flex flex-wrap gap-4 text-xs">
                            {notesObj?.public && (
                              <div className="flex-1 min-w-50">
                                <span className="font-medium text-amber-700 dark:text-amber-400">
                                  Public:{" "}
                                </span>
                                <span className="text-slate-600 dark:text-slate-300">
                                  {notesObj.public}
                                </span>
                              </div>
                            )}
                            {notesObj?.internal && (
                              <div className="flex-1 min-w-50">
                                <span className="font-medium text-blue-700 dark:text-blue-400">
                                  Internal:{" "}
                                </span>
                                <span className="text-slate-600 dark:text-slate-300">
                                  {notesObj.internal}
                                </span>
                              </div>
                            )}
                            {notesObj?.warehouse && (
                              <div className="flex-1 min-w-50">
                                <span className="font-medium text-green-700 dark:text-green-400">
                                  Warehouse:{" "}
                                </span>
                                <span className="text-slate-600 dark:text-slate-300">
                                  {notesObj.warehouse}
                                </span>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
            <tfoot className="bg-slate-50 dark:bg-slate-900/50 border-t-2 border-slate-300 dark:border-slate-600">
              {/* Single summary row with counts and total */}
              <tr>
                {/* Skip checkbox and expand columns */}
                {canEdit && <td></td>}
                <td></td>
                <td className="px-4 py-2 text-xs font-medium text-slate-600 dark:text-slate-300">
                  {lineCount} {lineCount === 1 ? "line" : "lines"}
                </td>
                <td className="px-4 py-2 text-xs text-slate-600 dark:text-slate-300">
                  {/* Description column empty */}
                </td>
                <td className="px-4 py-2 text-xs text-right text-slate-600 dark:text-slate-300">
                  {formatNumber(totalQty)} items
                </td>
                <td colSpan={2}></td>
                <td className="px-4 py-2 text-xs font-medium text-slate-500 dark:text-slate-400 text-right">
                  Total:
                </td>
                <td className="px-4 py-2 text-xs font-bold text-slate-900 dark:text-white text-right">
                  {formatCurrency(
                    lines.reduce((sum, l) => {
                      const lRecord = l as unknown as Record<string, unknown>;
                      const lPrice = lRecord.price as
                        | Record<string, unknown>
                        | undefined;
                      const ext = lPrice?.extended ?? l.price?.extended ?? 0;
                      return sum + Number(ext);
                    }, 0),
                  )}
                </td>
                <td></td>
                {/* Actions column */}
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      {/* Line Details Modal */}
      {selectedLine && (
        <LineDetailsModal
          line={selectedLine}
          isOpen={showLineModal}
          isEditing={isEditing && !isLocked}
          onClose={() => {
            setShowLineModal(false);
            setSelectedLine(null);
          }}
          onSave={handleLineModalSave}
          onOpenItem={handleOpenItem}
        />
      )}
    </div>
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
        <button
          type="button"
          onClick={() => setShowAddForm(true)}
          className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
        >
          <FaPlus size={12} />
          Add Action
        </button>
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
  data: SalesOrder;
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

// Main SalesOrderDetail Component
interface SalesOrderDetailProps {
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
  onCancelInline?: () => void;
}

const SalesOrderDetail: React.FC<SalesOrderDetailProps> = ({
  isAdmin = false,
  inline = false,
  modeProp,
  dataProp,
  onSaved,
  onCancelInline,
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
  const renderCustomTab = useCallback(
    (
      tabId: string,
      data: Transaction,
      isEditing: boolean,
      onFieldChange?: (field: string, value: unknown) => void,
    ) => {
      const salesOrderData = data as SalesOrder;
      const currentActions = salesOrderData.actions?.items ?? [];

      // Action handlers that use onFieldChange to update the data
      const handleAddAction = (action: ActionItem) => {
        if (onFieldChange) {
          const newActions = [...currentActions, { ...action, id: Date.now() }];
          onFieldChange("actions", {
            ...salesOrderData.actions,
            items: newActions,
          });
        }
      };

      const handleUpdateAction = (index: number, action: ActionItem) => {
        if (onFieldChange) {
          const newActions = [...currentActions];
          newActions[index] = action;
          onFieldChange("actions", {
            ...salesOrderData.actions,
            items: newActions,
          });
        }
      };

      const handleDeleteAction = (index: number) => {
        if (onFieldChange) {
          const newActions = currentActions.filter((_, i) => i !== index);
          onFieldChange("actions", {
            ...salesOrderData.actions,
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
              isLocked={salesOrderData.is_locked}
              onAddAction={handleAddAction}
              onUpdateAction={handleUpdateAction}
              onDeleteAction={handleDeleteAction}
            />
          );
        case "shipping":
          return <ShippingTab data={salesOrderData} isEditing={isEditing} />;
        default:
          return null;
      }
    },
    [],
  ); // No dependencies - handlers are created inline with closure over data

  // Custom header renderer
  const renderHeader = useCallback(
    (
      data: Transaction,
      isEditing: boolean,
      onChange?: (field: string, value: unknown) => void,
    ) => (
      <SalesOrderHeader
        data={data as SalesOrder}
        isEditing={isEditing}
        onChange={
          onChange as
            | ((field: keyof SalesOrder, value: unknown) => void)
            | undefined
        }
        onStatusChange={handleStatusChange}
      />
    ),
    [handleStatusChange],
  );

  // Custom lines renderer - includes item search when editing
  const renderLines = useCallback(
    (
      lines: TransactionLine[],
      isEditing: boolean,
      data?: Transaction,
      onLinesChange?: (lines: TransactionLine[]) => void,
    ) => (
      <SalesOrderLines
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
      transactionType="sales_order"
      typeLabel="Sales Order"
      modelName="salesorder"
      customTabsBefore={SALES_ORDER_TABS_BEFORE}
      getCustomTabsAfter={getSalesOrderTabsAfter}
      renderCustomTab={renderCustomTab}
      renderHeader={renderHeader}
      renderLines={renderLines}
      isAdmin={isAdmin}
      canEdit={canEdit}
      inline={inline}
      modeProp={modeProp}
      dataProp={dataProp}
      onSaved={onSaved}
      onCancelInline={onCancelInline}
    />
  );
};

export default SalesOrderDetail;

// is used on all order, invoice, and transfer transaction types, so it has some conditional logic based on transactionType prop and the shape of the line objects (which can vary between transactions and between existing lines vs new lines being added from the item search)
import React from "react";
import {
  FaShoppingCart,
  FaChevronDown,
  FaChevronRight,
  FaStickyNote,
  FaEdit,
  FaExternalLinkAlt,
  FaCopy,
  FaTrash,
  FaBoxes,
} from "react-icons/fa";
import LineDetailsModal from "../components/LineDetailsModal";
import InventoryCheckDialog from "../components/InventoryCheckDialog";
import OrderItemSearch from "../models/order/components/OrderItemSearch";
import { lineKey } from "../utils/lineHelpers";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

// You may need to import types for TransactionLine, ItemSearchResult, etc.

interface LinesCardProps {
  lines: any[];
  isEditing: boolean;
  isLocked?: boolean;
  priceLevel?: string | null;
  transactionType?: string;
  onDeleteLine?: (lineId: number) => void;
  onUpdateLine?: (lineId: number, field: string, value: unknown) => void;
  onUpdateFullLine?: (line: any) => void;
  onDuplicateLine?: (lineId: number) => void;
  onAddItem?: (item: any, quantity: number) => void;
  onLinesChange?: (lines: any[]) => void;
}

const LinesCard: React.FC<LinesCardProps> = ({
  lines,
  isEditing,
  isLocked = false,
  priceLevel,
  transactionType: _transactionType,
  onDeleteLine,
  onUpdateLine,
  onUpdateFullLine,
  onDuplicateLine,
  onAddItem,
  onLinesChange,
}) => {
  const [pendingDeleteId, setPendingDeleteId] = React.useState<number | null>(
    null,
  );
  const [editingCell, setEditingCell] = React.useState<{
    lineId: number;
    field: string;
  } | null>(null);
  const [editValue, setEditValue] = React.useState<string>("");
  const [expandedRows, setExpandedRows] = React.useState<Set<number>>(
    new Set(),
  );
  const [selectedLine, setSelectedLine] = React.useState<any | null>(null);
  const [showLineModal, setShowLineModal] = React.useState(false);
  const [selectedLineIds, setSelectedLineIds] = React.useState<Set<number>>(
    new Set(),
  );
  const [inventoryCheck, setInventoryCheck] = React.useState<{
    itemId: number;
    itemCode: string;
  } | null>(null);

  const lineCount = lines.length;
  const totalQty = lines.reduce((sum, l) => {
    const lRecord = l as unknown as Record<string, unknown>;
    const qty = lRecord.qty ?? l.quantity?.active ?? 0;
    return sum + Number(qty);
  }, 0);

  const handleDeleteClick = (lineId: number) => {
    if (pendingDeleteId === lineId) {
      onDeleteLine?.(lineId);
      setPendingDeleteId(null);
    } else {
      setPendingDeleteId(lineId);
    }
  };

  const handleCancelPending = () => {
    setPendingDeleteId(null);
  };

  const handleDoubleClick = (
    lineId: number,
    field: string,
    currentValue: string | number,
  ) => {
    if (isLocked || !isEditing) return;
    setEditingCell({ lineId, field });
    setEditValue(String(currentValue));
  };

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

  const handleEditCancel = () => {
    setEditingCell(null);
    setEditValue("");
  };

  const handleEditKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleEditSave();
    } else if (e.key === "Escape") {
      handleEditCancel();
    }
  };

  const toggleRowExpansion = (lineId: number) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(lineId)) {
      newExpanded.delete(lineId);
    } else {
      newExpanded.add(lineId);
    }
    setExpandedRows(newExpanded);
  };

  const handleOpenLineDetails = (line: any) => {
    setSelectedLine(line);
    setShowLineModal(true);
  };

  const handleLineModalSave = (updatedLine: any) => {
    if (onUpdateFullLine) {
      onUpdateFullLine(updatedLine);
    }
  };

  const handleOpenItem = (itemIdOrCode: number | string) => {
    const path =
      typeof itemIdOrCode === "number"
        ? `/products/items/${itemIdOrCode}`
        : `/products/items/code/${itemIdOrCode}`;
    window.open(path, "_blank", "width=1000,height=800");
  };

  const toggleLineSelection = (lineId: number) => {
    const newSelected = new Set(selectedLineIds);
    if (newSelected.has(lineId)) {
      newSelected.delete(lineId);
    } else {
      newSelected.add(lineId);
    }
    setSelectedLineIds(newSelected);
  };

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

  const handleBulkDelete = () => {
    selectedLineIds.forEach((id) => onDeleteLine?.(id));
    setSelectedLineIds(new Set());
  };

  const canEdit = isEditing && !isLocked;

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

  return (
    <div className="space-y-6 my-2">
      {/* Line Details Drawer (right sidebar) */}
      {showLineModal && (
        <div className="pointer-events-none fixed inset-0 z-[200000] flex items-stretch justify-end">
          {/* Overlay */}
          <div
            className="pointer-events-auto fixed inset-0 "
            onClick={() => {
              setShowLineModal(false);
              setSelectedLine(null);
            }}
          />
          {/* Drawer */}
          <div className="pointer-events-auto ml-auto flex h-full w-full max-h-screen flex-col overflow-hidden border-l border-blue-200 dark:border-blue-800 bg-white dark:bg-slate-800 shadow-2xl no-scrollbar sm:w-[480px] lg:w-[33vw] lg:min-w-[360px]">
            <LineDetailsModal
              line={selectedLine}
              isOpen={showLineModal}
              isEditing={canEdit}
              onClose={() => {
                setShowLineModal(false);
                setSelectedLine(null);
              }}
              onSave={handleLineModalSave}
              onOpenItem={handleOpenItem}
            />
          </div>
        </div>
      )}
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
          <OrderItemSearch
            onAddItem={(item, quantity) => {
              const itemId = item.id ?? item.item_id ?? item.itemId ?? null;
              const idaItem =
                item.ida_item ??
                item.item_code ??
                item.sku ??
                item.item_num ??
                item.itemNum ??
                "";
              const description =
                item.description ?? item.description_text ?? item.name ?? "";
              const unitMeasure =
                item.unit_of_measure ??
                item.unitOfMeasure ??
                item.unit_measure ??
                "EA";
              // Default price level to "retail" if not provided ("retail" and "base" are equivalent)
              const level = priceLevel || "retail";
              let unitPrice = 0;
              if (typeof item.price === "number") {
                unitPrice = item.price;
              } else if (typeof item.price === "string") {
                unitPrice = parseFloat(item.price) || 0;
              } else if (item.price && typeof item.price === "object") {
                const priceObj = item.price as Record<string, unknown>;
                // Look up price by level; "retail" and "base" are equivalent
                let levelValue = priceObj[level];
                if (levelValue === undefined || levelValue === null) {
                  if (level === "retail") {
                    levelValue = priceObj.base;
                  } else if (level === "base") {
                    levelValue = priceObj.retail;
                  } else {
                    levelValue = priceObj.base ?? priceObj.retail;
                  }
                }
                unitPrice = Number(levelValue ?? 0);
              }
              if (unitPrice === 0) {
                unitPrice = Number(
                  item.unit_price ?? item.priceA ?? item.price_a ?? 0,
                );
              }
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
              if (unitCost === 0) {
                unitCost = Number(item.unit_cost ?? item.costA ?? 0);
              }
              const newLine: Omit<any, "id"> = {
                item: {
                  item_id: itemId,
                  ida_item: idaItem,
                  description: description,
                  unit_measure: unitMeasure,
                },
                // New lines: processing = user input, staged mirrors, remaining = staged (standalone)
                // Backend normalize_quantity_map enforces the correct semantics
                quantity: { active: quantity, staged: quantity, remaining: quantity },
                price: {
                  unit: unitPrice,
                  extended: unitPrice * quantity,
                },
                cost: {
                  unit: unitCost,
                },
              };
              onLinesChange?.([...lines, newLine as any]);
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
                <th className="px-2 py-1 w-8"></th>
                <th className="px-2 py-1 text-left text-xs font-semibold uppercase tracking-wide w-32">
                  Item Code
                </th>
                <th className="px-2 py-1 w-30 text-left text-xs font-semibold uppercase tracking-wide">
                  Description
                </th>
                <th className="px-2 py-1 text-right text-xs font-semibold uppercase tracking-wide w-24">
                  Active
                </th>
                <th className="px-2 py-1 text-right text-xs font-semibold uppercase tracking-wide w-24">
                  Remaining
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
                // Display active as the user-editable quantity
                // (staged mirrors active for standalone; backend enforces semantics)
                const qty = lineRecord.qty ?? line.quantity?.active ?? 0;
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
                const lineId = lineKey(line, idx);
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

                const renderEditableCell = (
                  field: string,
                  value: string | number,
                  displayValue: string,
                  className: string,
                  isNumeric: boolean = false,
                ) => {
                  const isEditingThis =
                    editingCell?.lineId === lineId &&
                    editingCell?.field === field;

                  if (isEditingThis) {
                    return (
                      <td className={className}>
                        <input
                          type="text"
                          inputMode={isNumeric ? "decimal" : "text"}
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          onBlur={handleEditSave}
                          onKeyDown={handleEditKeyDown}
                          autoFocus
                          className="w-full px-2 py-1 text-xs border border-blue-500 rounded bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                          style={isNumeric ? { textAlign: "right" } : {}}
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
                        lineId != null &&
                        handleDoubleClick(lineId as number, field, value)
                      }
                      title={canEditLine ? "Double-click to edit" : undefined}
                    >
                      {displayValue}
                    </td>
                  );
                };

                const stripeClass =
                  idx % 2 === 1 ? "bg-slate-50 dark:bg-slate-800/30" : "";

                return (
                  <React.Fragment key={lineId}>
                    <tr
                      className={`hover:bg-blue-50 dark:hover:bg-blue-900/20 ${stripeClass} ${
                        isSelected ? "bg-blue-50 dark:bg-blue-900/20" : ""
                      }`}
                    >
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
                        {line.item?.description &&
                        line.item.description.length > 15 ? (
                          <span
                            className="ml-1 text-slate-400 cursor-pointer group-hover:text-blue-500"
                            title={line.item.description}
                          >
                            {description}
                          </span>
                        ) : (
                          <>{line.item?.description}</>
                        )}
                      </td>
                      <td className="px-2 py-1 text-xs text-right text-slate-900 dark:text-white">
                        {canEditLine && line.item?.is_active !== false ? (
                          <input
                            type="text"
                            inputMode="decimal"
                            value={
                              editingCell?.lineId === lineId && editingCell?.field === "qty"
                                ? editValue
                                : String(qty)
                            }
                            onChange={(e) => {
                              if (
                                editingCell?.lineId !== lineId ||
                                editingCell?.field !== "qty"
                              ) {
                                setEditingCell({ lineId: lineId as number, field: "qty" });
                              }
                              setEditValue(e.target.value);
                            }}
                            onFocus={() => {
                              setEditingCell({ lineId: lineId as number, field: "qty" });
                              setEditValue(String(qty));
                            }}
                            onBlur={handleEditSave}
                            onKeyDown={handleEditKeyDown}
                            className="w-20 px-2 py-0.5 text-xs text-right border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                          />
                        ) : (
                          formatNumber(Number(qty))
                        )}
                      </td>
                      <td className="px-2 py-1 text-xs text-right text-slate-500 dark:text-slate-400">
                        {formatNumber(Number(line.quantity?.remaining ?? 0))}
                      </td>
                      <td className="px-2 py-1 text-xs text-right text-slate-600 dark:text-slate-300">
                        {String(uom)}
                      </td>
                      {renderEditableCell(
                        "unit_price",
                        Number(unitPrice),
                        formatCurrency(Number(unitPrice)),
                        "px-2 py-1 text-xs text-right text-slate-900 dark:text-white",
                        true,
                      )}
                      <td className="px-2 py-1 text-xs text-right text-slate-600 dark:text-slate-300">
                        {formatCurrency(Number(unitCost))}
                      </td>
                      <td className="px-2 py-1 text-xs text-right font-medium text-slate-900 dark:text-white">
                        {formatCurrency(Number(extended))}
                      </td>
                      <td className="px-3 py-3 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <button
                            type="button"
                            onClick={() => handleOpenLineDetails(line)}
                            className="p-1 text-slate-400 hover:text-blue-500 transition-colors"
                            title="View/Edit line details"
                          >
                            <FaEdit size={14} />
                          </button>
                          {itemCode !== "--" && (
                            <button
                              type="button"
                              onClick={() => {
                                const id = Number(
                                  (line as any).item_id ??
                                  line.item?.id ??
                                  line.item?.item_id,
                                );
                                if (id) setInventoryCheck({ itemId: id, itemCode });
                              }}
                              className="p-1 text-slate-400 hover:text-amber-500 transition-colors"
                              title="Check inventory"
                            >
                              <FaBoxes size={13} />
                            </button>
                          )}
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
                    {isExpanded && hasNotes && (
                      <tr className="bg-amber-50 dark:bg-amber-900/20">
                        <td colSpan={canEdit ? 11 : 10} className="px-6 py-3">
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
              <tr>
                {canEdit && <td></td>}
                <td></td>
                <td className="px-4 py-2 text-xs font-medium text-slate-600 dark:text-slate-300">
                  {lineCount} {lineCount === 1 ? "line" : "lines"}
                </td>
                <td className="px-4 py-2 text-xs text-slate-600 dark:text-slate-300"></td>
                <td className="px-4 py-2 text-xs text-right text-slate-600 dark:text-slate-300">
                  {formatNumber(totalQty)} items
                </td>
                <td></td>
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
              </tr>
            </tfoot>
          </table>
        </div>
      )}
      {/* Only sidebar modal is used above; remove duplicate modal here. */}

      {/* Inventory check dialog */}
      {inventoryCheck && (
        <InventoryCheckDialog
          itemId={inventoryCheck.itemId}
          itemCode={inventoryCheck.itemCode}
          onClose={() => setInventoryCheck(null)}
        />
      )}
    </div>
  );
};

export default withDevIdentifier(LinesCard, 'LinesCard', 'amber');
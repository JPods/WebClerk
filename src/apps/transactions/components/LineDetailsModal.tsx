/**
 * LineDetailsModal - Modal for viewing/editing full line item details
 * Includes all fields, notes, and link to open item record
 */
import React, { useState, useEffect } from "react";
import {
  FaTimes,
  FaExternalLinkAlt,
  FaSave,
  FaBox,
  FaStickyNote,
  FaDollarSign,
  FaWarehouse,
} from "react-icons/fa";
import type { TransactionLine } from "../types/transactionTypes";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

interface LineDetailsModalProps {
  line: TransactionLine | null;
  isOpen: boolean;
  isEditing: boolean;
  onClose: () => void;
  onSave?: (line: TransactionLine) => void;
  onOpenItem?: (itemIdOrCode: number | string) => void;
}

const LineDetailsModal: React.FC<LineDetailsModalProps> = ({
  line,
  isOpen,
  isEditing,
  onClose,
  onSave,
  onOpenItem,
}) => {
  const [editLine, setEditLine] = useState<TransactionLine | null>(null);
  const [activeSection, setActiveSection] = useState<
    "details" | "pricing" | "notes"
  >("details");

  // Reset edit state when line changes
  useEffect(() => {
    if (line) {
      setEditLine({ ...line });
    }
  }, [line]);

  if (!isOpen || !line) return null;

  const lineRecord = (editLine ?? line) as unknown as Record<string, unknown>;

  const handleFieldChange = (field: string, value: unknown) => {
    if (!editLine) return;
    setEditLine({
      ...editLine,
      [field]: value,
    } as TransactionLine);
  };

  const handleNestedFieldChange = (
    parent: string,
    field: string,
    value: unknown,
  ) => {
    if (!editLine) return;
    const parentObj =
      ((editLine as unknown as Record<string, unknown>)[parent] as Record<
        string,
        unknown
      >) ?? {};
    setEditLine({
      ...editLine,
      [parent]: { ...parentObj, [field]: value },
    } as TransactionLine);
  };

  const handleSaveClick = () => {
    if (editLine && onSave) {
      onSave(editLine);
      onClose();
    }
  };

  const formatCurrency = (val: unknown) => {
    if (val === undefined || val === null) return "--";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(Number(val));
  };

  const itemId = lineRecord.item_id as number | undefined;
  const priceObj = (lineRecord.price as Record<string, unknown>) ?? {};
  const costObj = (lineRecord.cost as Record<string, unknown>) ?? {};
  const notesObj = (lineRecord.notes as Record<string, string>) ?? {};

  return (
    <div className="pointer-events-none fixed inset-0 z-[200000] flex items-stretch justify-end">
      <div className="pointer-events-auto ml-auto flex h-full w-full max-h-screen flex-col overflow-hidden border-l border-blue-200 dark:border-blue-800 bg-white dark:bg-slate-800 shadow-2xl no-scrollbar sm:w-[480px] lg:w-[33vw] lg:min-w-[360px]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-blue-200 dark:border-blue-800 bg-slate-50 dark:bg-slate-900">
          <div className="flex items-center gap-3">
            <FaBox className="text-blue-500" size={20} />
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                Line #{String(lineRecord.line_no ?? line.id ?? "?")}
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 font-mono">
                {String(
                  lineRecord.ida_item ?? line.item?.ida_item ?? "No Item",
                )}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {itemId && onOpenItem && (
              <button
                onClick={() => onOpenItem(itemId)}
                className="px-3 py-1.5 text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded-lg transition-colors flex items-center gap-2"
                title="Open item record in new window"
              >
                <FaExternalLinkAlt size={12} />
                View Item
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
            >
              <FaTimes size={18} />
            </button>
          </div>
        </div>

        {/* Section Tabs */}
        <div className="flex border-b border-blue-200 dark:border-blue-800">
          {[
            { id: "details", label: "Details", icon: <FaBox size={12} /> },
            {
              id: "pricing",
              label: "Pricing & Cost",
              icon: <FaDollarSign size={12} />,
            },
            { id: "notes", label: "Notes", icon: <FaStickyNote size={12} /> },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() =>
                setActiveSection(tab.id as "details" | "pricing" | "notes")
              }
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeSection === tab.id
                  ? "border-blue-500 text-blue-600 dark:text-blue-400"
                  : "border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300"
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 pb-6 pt-4 space-y-4">
          {activeSection === "details" && (
            <div className="space-y-6">
              {/* Item Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                    Item Code
                  </label>
                  <input
                    type="text"
                    value={String(lineRecord.ida_item ?? "")}
                    onChange={(e) =>
                      handleFieldChange("ida_item", e.target.value)
                    }
                    disabled={!isEditing}
                    className="w-full px-3 py-2 text-xs font-mono border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                    Line #
                  </label>
                  <input
                    type="number"
                    value={Number(lineRecord.line_no ?? 0)}
                    onChange={(e) =>
                      handleFieldChange("line_no", Number(e.target.value))
                    }
                    disabled={!isEditing}
                    className="w-full px-3 py-2 text-xs border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed"
                  />
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                  Description
                </label>
                <textarea
                  value={String(lineRecord.description ?? "")}
                  onChange={(e) =>
                    handleFieldChange("description", e.target.value)
                  }
                  disabled={!isEditing}
                  rows={2}
                  className="w-full px-3 py-2 text-xs border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed resize-none"
                />
              </div>

              {/* Quantity & UOM */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                    Quantity
                  </label>
                  <input
                    type="number"
                    value={Number(lineRecord.qty ?? 0)}
                    onChange={(e) =>
                      handleFieldChange("qty", Number(e.target.value))
                    }
                    disabled={!isEditing}
                    step="0.01"
                    className="w-full px-3 py-2 text-xs text-right border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                    UOM
                  </label>
                  <input
                    type="text"
                    value={String(lineRecord.unit_measure ?? "EA")}
                    onChange={(e) =>
                      handleFieldChange("unit_measure", e.target.value)
                    }
                    disabled={!isEditing}
                    className="w-full px-3 py-2 text-xs border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                    Weight
                  </label>
                  <input
                    type="number"
                    value={Number(lineRecord.weight ?? 0)}
                    onChange={(e) =>
                      handleFieldChange("weight", Number(e.target.value))
                    }
                    disabled={!isEditing}
                    step="0.01"
                    className="w-full px-3 py-2 text-xs text-right border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed"
                  />
                </div>
              </div>

              {/* Warehouse */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1 flex items-center gap-1">
                    <FaWarehouse size={10} /> Warehouse
                  </label>
                  <input
                    type="text"
                    value={String(lineRecord.warehouse ?? "")}
                    onChange={(e) =>
                      handleFieldChange("warehouse", e.target.value)
                    }
                    disabled={!isEditing}
                    className="w-full px-3 py-2 text-xs border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                    Location
                  </label>
                  <input
                    type="text"
                    value={String(lineRecord.location ?? "")}
                    onChange={(e) =>
                      handleFieldChange("location", e.target.value)
                    }
                    disabled={!isEditing}
                    className="w-full px-3 py-2 text-xs border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed"
                  />
                </div>
              </div>
            </div>
          )}

          {activeSection === "pricing" && (
            <div className="space-y-6">
              {/* Selling Price */}
              <div>
                <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
                  Selling Price
                </h4>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                      Unit Price
                    </label>
                    <input
                      type="number"
                      value={Number(priceObj.unit ?? priceObj.sell ?? 0)}
                      onChange={(e) =>
                        handleNestedFieldChange(
                          "price",
                          "unit",
                          Number(e.target.value),
                        )
                      }
                      disabled={!isEditing}
                      step="0.01"
                      className="w-full px-3 py-2 text-xs text-right border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                      Discount %
                    </label>
                    <input
                      type="number"
                      value={Number(priceObj.discount_pc ?? 0)}
                      onChange={(e) =>
                        handleNestedFieldChange(
                          "price",
                          "discount_pc",
                          Number(e.target.value),
                        )
                      }
                      disabled={!isEditing}
                      step="0.1"
                      className="w-full px-3 py-2 text-xs text-right border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                      Extended
                    </label>
                    <div className="px-3 py-2 text-xs text-right font-semibold text-slate-900 dark:text-white bg-slate-100 dark:bg-slate-700 rounded-lg">
                      {formatCurrency(priceObj.extended)}
                    </div>
                  </div>
                </div>
              </div>

              {/* Cost */}
              <div>
                <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
                  Cost
                </h4>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                      Unit Cost
                    </label>
                    <input
                      type="number"
                      value={Number(costObj.unit ?? 0)}
                      onChange={(e) =>
                        handleNestedFieldChange(
                          "cost",
                          "unit",
                          Number(e.target.value),
                        )
                      }
                      disabled={!isEditing}
                      step="0.01"
                      className="w-full px-3 py-2 text-xs text-right border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                      Landed Cost
                    </label>
                    <input
                      type="number"
                      value={Number(costObj.landed ?? 0)}
                      onChange={(e) =>
                        handleNestedFieldChange(
                          "cost",
                          "landed",
                          Number(e.target.value),
                        )
                      }
                      disabled={!isEditing}
                      step="0.01"
                      className="w-full px-3 py-2 text-xs text-right border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                      Extended Cost
                    </label>
                    <div className="px-3 py-2 text-xs text-right font-semibold text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-700 rounded-lg">
                      {formatCurrency(costObj.extended)}
                    </div>
                  </div>
                </div>
              </div>

              {/* Margin */}
              <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4">
                <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
                  Margin
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                      Margin Amount
                    </label>
                    <div
                      className={`px-3 py-2 text-xs text-right font-semibold rounded-lg ${
                        Number(priceObj.margin ?? 0) >= 0
                          ? "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20"
                          : "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20"
                      }`}
                    >
                      {formatCurrency(priceObj.margin)}
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                      Margin %
                    </label>
                    <div
                      className={`px-3 py-2 text-xs text-right font-semibold rounded-lg ${
                        Number(priceObj.margin_pc ?? 0) >= 0
                          ? "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20"
                          : "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20"
                      }`}
                    >
                      {priceObj.margin_pc != null
                        ? `${Number(priceObj.margin_pc).toFixed(1)}%`
                        : "--"}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeSection === "notes" && (
            <div className="space-y-6">
              <div>
                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                  Public Notes (visible on documents)
                </label>
                <textarea
                  value={String(notesObj.public ?? "")}
                  onChange={(e) =>
                    handleNestedFieldChange("notes", "public", e.target.value)
                  }
                  disabled={!isEditing}
                  rows={3}
                  placeholder="Notes that appear on invoices, packing slips, etc."
                  className="w-full px-3 py-2 text-xs border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed resize-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                  Internal Notes (not visible to customer)
                </label>
                <textarea
                  value={String(notesObj.internal ?? "")}
                  onChange={(e) =>
                    handleNestedFieldChange("notes", "internal", e.target.value)
                  }
                  disabled={!isEditing}
                  rows={3}
                  placeholder="Internal processing notes"
                  className="w-full px-3 py-2 text-xs border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed resize-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                  Warehouse Instructions
                </label>
                <textarea
                  value={String(notesObj.warehouse ?? "")}
                  onChange={(e) =>
                    handleNestedFieldChange(
                      "notes",
                      "warehouse",
                      e.target.value,
                    )
                  }
                  disabled={!isEditing}
                  rows={2}
                  placeholder="Special handling, packing instructions, etc."
                  className="w-full px-3 py-2 text-xs border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed resize-none"
                />
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-5 py-4 border-t border-blue-200 dark:border-blue-800 bg-slate-50 dark:bg-slate-900">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            {isEditing ? "Cancel" : "Close"}
          </button>
          {isEditing && onSave && (
            <button
              onClick={handleSaveClick}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center gap-2"
            >
              <FaSave size={14} />
              Save Changes
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default withDevIdentifier(LineDetailsModal, 'LineDetailsModal');
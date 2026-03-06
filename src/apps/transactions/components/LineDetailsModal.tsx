/**
 * LineDetailsModal – Slide-out panel for viewing/editing a transaction line.
 *
 * Single scrollable page with item info, line details, and pricing.
 * "Notes" is the only secondary tab.
 * Fetches item data (name, category, inventory) when item_id is present.
 *
 * NOTE: This component renders the panel *content* only (header, body, footer).
 * The fixed overlay + drawer wrapper is provided by LinesCard.
 */
import React, { useState, useEffect, useCallback } from "react";
import {
  FaExternalLinkAlt,
  FaSave,
  FaBox,
  FaStickyNote,
  FaDollarSign,
  FaWarehouse,
  FaBoxes,
  FaSyncAlt,
} from "react-icons/fa";
import type { TransactionLine } from "../types/transactionTypes";
import { getRecord } from "@/api/wcapi";
import { withDevIdentifier } from "@/components/common/DevIdentifier";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface LineDetailsModalProps {
  line: TransactionLine | null;
  isOpen: boolean;
  isEditing: boolean;
  onClose: () => void;
  onSave?: (line: TransactionLine) => void;
  onOpenItem?: (itemIdOrCode: number | string) => void;
}

interface ItemRecord {
  id?: number;
  name?: string;
  sku?: string;
  ida_item?: string;
  description?: string;
  description_text?: string;
  category?: string;
  product_category?: string;
  unit_of_measure?: string;
  unit_measure?: string;
  weight?: number;
  is_active?: boolean;
  quantity?: QuantityBuckets;
}

interface QuantityBuckets {
  on_hand?: number;
  available?: number;
  allocated?: number;
  on_so?: number;
  on_po?: number;
  on_p?: number;
  on_wo?: number;
  on_in?: number;
}

const BUCKET_ROWS: {
  key: keyof QuantityBuckets;
  label: string;
  highlight?: boolean;
}[] = [
  { key: "on_hand", label: "On Hand", highlight: true },
  { key: "available", label: "Available", highlight: true },
  { key: "allocated", label: "Allocated" },
  { key: "on_so", label: "On SO" },
  { key: "on_po", label: "On PO" },
  { key: "on_p", label: "On Proposal" },
  { key: "on_wo", label: "On WO" },
  { key: "on_in", label: "On Invoice" },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const fmtCurrency = (val: unknown): string => {
  if (val === undefined || val === null) return "--";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(Number(val));
};

const fmtNumber = (v: number) => v.toLocaleString();

// Shared field input class – compact inline inputs
const fieldCls =
  "px-2 py-0.5 text-sm border border-slate-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-slate-900 dark:text-white disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed";

// Inline label: muted, snug against its value
const lbl = "text-xs text-slate-400 dark:text-slate-500 mr-0.5";
// Inline value (read-only): darker, slightly bolder
const val = "text-sm font-medium text-slate-800 dark:text-slate-200 tabular-nums";
// Cluster row – wrapping flex, pairs flow like words
const cluster = "flex flex-wrap items-baseline gap-x-4 gap-y-1 text-sm";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const LineDetailsModal: React.FC<LineDetailsModalProps> = ({
  line,
  isOpen,
  isEditing,
  onClose,
  onSave,
  onOpenItem,
}) => {
  const [editLine, setEditLine] = useState<TransactionLine | null>(null);
  const [activeSection, setActiveSection] = useState<"details" | "notes">(
    "details",
  );

  // Item data fetched from API
  const [itemData, setItemData] = useState<ItemRecord | null>(null);
  const [itemLoading, setItemLoading] = useState(false);
  const [itemError, setItemError] = useState<string | null>(null);
  const [showInventory, setShowInventory] = useState(false);

  // ------------------------------------------------------------------
  // Reset state when the line prop changes
  // ------------------------------------------------------------------
  useEffect(() => {
    if (line) {
      setEditLine({ ...line });
      setActiveSection("details");
      setShowInventory(false);
      setItemData(null);
      setItemError(null);
    }
  }, [line]);

  // ------------------------------------------------------------------
  // Resolve item_id from the line (supports flat + nested shapes)
  // ------------------------------------------------------------------
  const resolveItemId = useCallback((): number | null => {
    if (!line) return null;
    const rec = line as unknown as Record<string, unknown>;
    const id =
      rec.item_id ??
      (line.item as Record<string, unknown> | undefined)?.item_id ??
      (line.item as Record<string, unknown> | undefined)?.id;
    return id ? Number(id) : null;
  }, [line]);

  // ------------------------------------------------------------------
  // Fetch item data by item_id
  // ------------------------------------------------------------------
  const fetchItem = useCallback(async () => {
    const id = resolveItemId();
    if (!id) {
      setItemData(null);
      return;
    }
    setItemLoading(true);
    setItemError(null);
    try {
      const payload = await getRecord("item", id);
      const record = payload?.record;
      if (!record) {
        setItemError(`Item #${id} not found`);
        setItemData(null);
        return;
      }
      setItemData(record as ItemRecord);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to fetch item data";
      setItemError(msg);
      setItemData(null);
    } finally {
      setItemLoading(false);
    }
  }, [resolveItemId]);

  useEffect(() => {
    if (isOpen && line) fetchItem();
  }, [isOpen, line, fetchItem]);

  // ------------------------------------------------------------------
  // Early return
  // ------------------------------------------------------------------
  if (!isOpen || !line) return null;

  // ------------------------------------------------------------------
  // Derived data
  // ------------------------------------------------------------------
  const lineRecord = (editLine ?? line) as unknown as Record<string, unknown>;
  const itemId = resolveItemId();
  const priceObj = (lineRecord.price as Record<string, unknown>) ?? {};
  const costObj = (lineRecord.cost as Record<string, unknown>) ?? {};
  const notesObj = (lineRecord.notes as Record<string, string>) ?? {};
  const itemObj = (lineRecord.item ?? line.item ?? {}) as Record<
    string,
    unknown
  >;
  const itemCode = String(
    lineRecord.ida_item ?? itemObj.ida_item ?? itemData?.ida_item ?? "--",
  );
  const itemName =
    itemData?.name || itemData?.description || itemData?.description_text || "";
  const itemCategory =
    itemData?.category || itemData?.product_category || "";
  const inventoryBuckets = itemData?.quantity ?? null;

  // Resolve line quantity object
  const qtyObj = (lineRecord.quantity as Record<string, unknown>) ?? {};
  const taxObj = (lineRecord.tax as Record<string, unknown>) ?? {};
  const physObj = (lineRecord.physical as Record<string, unknown>) ?? {};

  // ------------------------------------------------------------------
  // Handlers
  // ------------------------------------------------------------------
  const handleFieldChange = (field: string, value: unknown) => {
    if (!editLine) return;
    setEditLine({ ...editLine, [field]: value } as TransactionLine);
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

  // Fetch item quantity from wc3 and fill into line.quantity
  const [qtyLoading, setQtyLoading] = useState(false);
  const fetchItemQuantity = useCallback(async () => {
    const id = resolveItemId();
    if (!id || !editLine) return;
    setQtyLoading(true);
    try {
      const payload = await getRecord("item", id);
      const rec = payload?.record as ItemRecord | undefined;
      const buckets = rec?.quantity;
      if (buckets) {
        const currentQty =
          ((editLine as unknown as Record<string, unknown>).quantity as Record<string, unknown>) ?? {};
        setEditLine({
          ...editLine,
          quantity: {
            ...currentQty,
            ...buckets,
            // preserve line-specific qty fields
            staged: currentQty.staged ?? buckets.on_hand,
            active: currentQty.active,
            remaining: currentQty.remaining,
          },
        } as TransactionLine);
        // also refresh the full item data
        setItemData(rec ?? null);
      }
    } catch {
      // silently fail – item data section already shows errors
    } finally {
      setQtyLoading(false);
    }
  }, [resolveItemId, editLine]);

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------
  return (
    <>
      {/* ── Header with action buttons ── */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-blue-200 dark:border-blue-800 bg-slate-50 dark:bg-slate-900">
        <div className="flex items-center gap-2">
          <FaBox className="text-blue-500" size={16} />
          <div>
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">
              Line #
              {String(
                lineRecord.line_no ??
                  lineRecord.line_number ??
                  line.id ??
                  "?",
              )}
            </h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 font-mono">
              {itemCode}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isEditing && onSave && (
            <button
              onClick={handleSaveClick}
              className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center gap-1.5"
            >
              <FaSave size={12} />
              Save
            </button>
          )}
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            {isEditing ? "Cancel" : "Close"}
          </button>
          {itemId && onOpenItem && (
            <button
              onClick={() => onOpenItem(itemId)}
              className="p-1.5 text-blue-500 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
              title="Open item record in new window"
            >
              <FaExternalLinkAlt size={13} />
            </button>
          )}
        </div>
      </div>

      {/* ── Tabs (Details | Notes) ── */}
      <div className="flex border-b border-blue-200 dark:border-blue-800">
        {(
          [
            { id: "details", label: "Details", icon: <FaBox size={12} /> },
            {
              id: "notes",
              label: "Notes",
              icon: <FaStickyNote size={12} />,
            },
          ] as const
        ).map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveSection(tab.id)}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
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

      {/* ── Content ── */}
      <div className="flex-1 overflow-y-auto px-4 pb-4 pt-3 space-y-3">
        {activeSection === "details" && (
          <>
            {/* ─── Item Information (fetched from API) ─── */}
            <section>
              <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5 flex items-center gap-2">
                <FaBox size={10} className="text-blue-400" />
                Item Information
                {itemId && (
                  <button
                    type="button"
                    onClick={fetchItem}
                    disabled={itemLoading}
                    className="ml-auto p-1 text-slate-400 hover:text-blue-500 transition-colors"
                    title="Refresh item data"
                  >
                    <FaSyncAlt
                      size={10}
                      className={itemLoading ? "animate-spin" : ""}
                    />
                  </button>
                )}
              </h4>

              {itemError && (
                <div className="text-xs text-red-500 mb-2 px-3 py-2 bg-red-50 dark:bg-red-900/20 rounded-lg">
                  {itemError}
                </div>
              )}

              {itemLoading && !itemData && (
                <div className="text-xs text-slate-400 py-4 text-center">
                  Loading item data…
                </div>
              )}

              {itemData && (
                <div className="bg-blue-50/50 dark:bg-blue-900/10 rounded-lg p-2 space-y-1">
                  <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-sm">
                    <div>
                      <span className="text-slate-500 dark:text-slate-400">
                        Name
                      </span>
                      <p className="font-medium text-slate-900 dark:text-white truncate">
                        {itemName || "--"}
                      </p>
                    </div>
                    <div>
                      <span className="text-slate-500 dark:text-slate-400">
                        SKU
                      </span>
                      <p className="font-medium text-slate-900 dark:text-white font-mono">
                        {itemData.sku || itemData.ida_item || "--"}
                      </p>
                    </div>
                    <div>
                      <span className="text-slate-500 dark:text-slate-400">
                        Category
                      </span>
                      <p className="font-medium text-slate-900 dark:text-white">
                        {itemCategory || "--"}
                      </p>
                    </div>
                    <div>
                      <span className="text-slate-500 dark:text-slate-400">
                        UOM
                      </span>
                      <p className="font-medium text-slate-900 dark:text-white">
                        {itemData.unit_of_measure ||
                          itemData.unit_measure ||
                          "--"}
                      </p>
                    </div>
                  </div>
                  {itemData.description_text &&
                    itemData.description_text !== itemData.name && (
                      <div className="text-sm">
                        <span className="text-slate-500 dark:text-slate-400">
                          Description
                        </span>
                        <p className="text-slate-700 dark:text-slate-300">
                          {itemData.description_text}
                        </p>
                      </div>
                    )}
                  {itemData.is_active === false && (
                    <div className="text-sm font-medium text-red-500 bg-red-50 dark:bg-red-900/20 rounded px-2 py-1 inline-block">
                      Inactive Item
                    </div>
                  )}
                </div>
              )}

              {!itemId && (
                <div className="text-xs text-slate-400 italic py-2">
                  No item linked to this line
                </div>
              )}
            </section>

            {/* ─── Inventory (collapsible) ─── */}
            {itemId && (
              <section>
                <button
                  type="button"
                  onClick={() => setShowInventory((v) => !v)}
                  className="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider hover:text-blue-600 dark:hover:text-blue-400 transition-colors w-full"
                >
                  <FaBoxes size={10} className="text-amber-500" />
                  Inventory
                  <span className="ml-auto text-[10px] font-normal normal-case">
                    {showInventory ? "hide" : "show"}
                  </span>
                </button>

                {showInventory && (
                  <div className="mt-2 bg-amber-50/50 dark:bg-amber-900/10 rounded-lg p-3">
                    {itemLoading && (
                      <div className="text-xs text-slate-400 py-2 text-center">
                        Loading…
                      </div>
                    )}
                    {!itemLoading && !inventoryBuckets && (
                      <div className="text-xs text-slate-400 py-2 text-center">
                        No inventory data available
                      </div>
                    )}
                    {inventoryBuckets && (
                      <table className="w-full text-xs">
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                          {BUCKET_ROWS.map(({ key, label, highlight }) => (
                            <tr key={key}>
                              <td
                                className={`py-1.5 pr-3 ${
                                  highlight
                                    ? "font-semibold text-slate-900 dark:text-white"
                                    : "text-slate-600 dark:text-slate-400"
                                }`}
                              >
                                {label}
                              </td>
                              <td
                                className={`py-1.5 text-right tabular-nums ${
                                  highlight
                                    ? "font-semibold text-slate-900 dark:text-white"
                                    : "text-slate-700 dark:text-slate-300"
                                }`}
                              >
                                {fmtNumber(inventoryBuckets[key] ?? 0)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                    <div className="mt-2 text-right">
                      <button
                        type="button"
                        onClick={fetchItem}
                        disabled={itemLoading}
                        className="text-[10px] text-blue-500 hover:text-blue-700 dark:hover:text-blue-300 transition-colors flex items-center gap-1 ml-auto"
                      >
                        <FaSyncAlt
                          size={9}
                          className={itemLoading ? "animate-spin" : ""}
                        />
                        Refresh
                      </button>
                    </div>
                  </div>
                )}
              </section>
            )}

            {/* ─── Line Details ─── */}
            <section>
              <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
                Line Details
              </h4>
              <div className="space-y-1.5">
                {/* Item Code · Line # */}
                <div className={`${cluster} line-row-item`}>
                  <span>
                    <span className={lbl}>Item</span>
                    <input
                      type="text"
                      value={String(lineRecord.ida_item ?? itemObj.ida_item ?? "")}
                      onChange={(e) => handleFieldChange("ida_item", e.target.value)}
                      disabled={!isEditing}
                      className={`${fieldCls} w-28 font-mono`}
                    />
                  </span>
                  <span>
                    <span className={lbl}>Line #</span>
                    <input
                      type="number"
                      value={Number(lineRecord.line_no ?? lineRecord.line_number ?? 0)}
                      onChange={(e) => handleFieldChange("line_no", Number(e.target.value))}
                      disabled={!isEditing}
                      className={`${fieldCls} w-16 text-right`}
                    />
                  </span>
                </div>

                {/* Description – full width */}
                <div className="line-row-item">
                  <span className={lbl}>Description</span>
                  <textarea
                    value={String(lineRecord.description ?? itemObj.description ?? "")}
                    onChange={(e) => handleFieldChange("description", e.target.value)}
                    disabled={!isEditing}
                    rows={2}
                    className={`${fieldCls} w-full resize-none mt-0.5`}
                  />
                </div>

                {/* Qty Staged · Active · Remaining · UOM + Fetch */}
                <div className={`${cluster} line-row-qty items-center`}>
                  <span>
                    <span className={lbl}>Staged</span>
                    <input
                      type="number"
                      value={Number(qtyObj.staged ?? lineRecord.qty ?? 0)}
                      onChange={(e) => handleNestedFieldChange("quantity", "staged", Number(e.target.value))}
                      disabled={!isEditing}
                      step="0.01"
                      className={`${fieldCls} w-20 text-right`}
                    />
                  </span>
                  <span>
                    <span className={lbl}>Active</span>
                    <input
                      type="number"
                      value={Number(qtyObj.active ?? 0)}
                      onChange={(e) => handleNestedFieldChange("quantity", "active", Number(e.target.value))}
                      disabled={!isEditing}
                      step="0.01"
                      className={`${fieldCls} w-20 text-right`}
                    />
                  </span>
                  <span>
                    <span className={lbl}>Remaining</span>
                    <span className={`${val} font-semibold`}>
                      {fmtNumber(Number(qtyObj.remaining ?? 0))}
                    </span>
                  </span>
                  <span>
                    <span className={lbl}>UOM</span>
                    <input
                      type="text"
                      value={String(lineRecord.unit_measure ?? itemObj.unit_measure ?? "EA")}
                      onChange={(e) => handleFieldChange("unit_measure", e.target.value)}
                      disabled={!isEditing}
                      className={`${fieldCls} w-14`}
                    />
                  </span>
                  {itemId && (
                    <button
                      type="button"
                      onClick={fetchItemQuantity}
                      disabled={qtyLoading}
                      className="px-2 py-0.5 text-xs font-medium text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 hover:bg-amber-100 dark:hover:bg-amber-900/30 rounded transition-colors flex items-center gap-1"
                      title="Fetch latest quantity from item record"
                    >
                      <FaSyncAlt size={9} className={qtyLoading ? "animate-spin" : ""} />
                      Fetch Qty
                    </button>
                  )}
                </div>

                {/* Weight · Warehouse · Location */}
                <div className={`${cluster} line-row-item`}>
                  <span>
                    <span className={lbl}>Weight</span>
                    <input
                      type="number"
                      value={Number(lineRecord.weight ?? 0)}
                      onChange={(e) => handleFieldChange("weight", Number(e.target.value))}
                      disabled={!isEditing}
                      step="0.01"
                      className={`${fieldCls} w-20 text-right`}
                    />
                  </span>
                  <span>
                    <span className={lbl}><FaWarehouse size={10} className="inline mr-0.5" />Whse</span>
                    <input
                      type="text"
                      value={String(lineRecord.warehouse ?? "")}
                      onChange={(e) => handleFieldChange("warehouse", e.target.value)}
                      disabled={!isEditing}
                      className={`${fieldCls} w-20`}
                    />
                  </span>
                  <span>
                    <span className={lbl}>Location</span>
                    <input
                      type="text"
                      value={String(lineRecord.location ?? "")}
                      onChange={(e) => handleFieldChange("location", e.target.value)}
                      disabled={!isEditing}
                      className={`${fieldCls} w-20`}
                    />
                  </span>
                </div>
              </div>
            </section>

            {/* ─── Pricing & Cost (matrix) ─── */}
            <section>
              <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5 flex items-center gap-2">
                <FaDollarSign size={10} className="text-green-500" />
                Pricing &amp; Cost
              </h4>

              {/* ── Price / Cost matrix table ── */}
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="text-xs text-slate-400 dark:text-slate-500">
                    <th className="text-left font-medium pr-2 pb-0.5 w-14"></th>
                    <th className="text-right font-medium px-1 pb-0.5 w-[90px]">Unit</th>
                    <th className="text-right font-medium px-1 pb-0.5 w-[90px]">Base</th>
                    <th className="text-right font-medium px-1 pb-0.5 w-[60px]">Disc%</th>
                    <th className="text-right font-medium px-1 pb-0.5 w-[80px]">Disc$</th>
                    <th className="text-right font-medium pl-1 pb-0.5 w-[100px]">Extended</th>
                  </tr>
                </thead>
                <tbody>
                  {/* Price row */}
                  <tr className="line-row-price border-t border-slate-100 dark:border-slate-700">
                    <td className="pr-2 py-1 text-xs font-semibold text-slate-600 dark:text-slate-300">Price</td>
                    <td className="px-1 py-1">
                      <input
                        type="number"
                        value={Number(priceObj.unit ?? priceObj.sell ?? 0)}
                        onChange={(e) => handleNestedFieldChange("price", "unit", Number(e.target.value))}
                        disabled={!isEditing}
                        step="0.01"
                        className={`${fieldCls} w-full text-right`}
                      />
                    </td>
                    <td className={`px-1 py-1 text-right ${val}`}>{fmtCurrency(priceObj.unit_base)}</td>
                    <td className="px-1 py-1">
                      <input
                        type="number"
                        value={Number(priceObj.discount_percent ?? priceObj.discount_pc ?? 0)}
                        onChange={(e) => handleNestedFieldChange("price", "discount_percent", Number(e.target.value))}
                        disabled={!isEditing}
                        step="0.1"
                        className={`${fieldCls} w-full text-right`}
                      />
                    </td>
                    <td className={`px-1 py-1 text-right ${val}`}>{fmtCurrency(priceObj.discount_amount)}</td>
                    <td className={`pl-1 py-1 text-right font-semibold ${val}`}>{fmtCurrency(priceObj.extended)}</td>
                  </tr>
                  {/* Cost row */}
                  <tr className="line-row-cost border-t border-slate-100 dark:border-slate-700">
                    <td className="pr-2 py-1 text-xs font-semibold text-slate-600 dark:text-slate-300">Cost</td>
                    <td className="px-1 py-1">
                      <input
                        type="number"
                        value={Number(costObj.unit ?? 0)}
                        onChange={(e) => handleNestedFieldChange("cost", "unit", Number(e.target.value))}
                        disabled={!isEditing}
                        step="0.01"
                        className={`${fieldCls} w-full text-right`}
                      />
                    </td>
                    <td className={`px-1 py-1 text-right ${val}`}>{fmtCurrency(costObj.unit_base)}</td>
                    <td className={`px-1 py-1 text-right ${val}`}>
                      {costObj.discount_percent != null ? `${Number(costObj.discount_percent).toFixed(1)}%` : "--"}
                    </td>
                    <td className={`px-1 py-1 text-right ${val}`}>{fmtCurrency(costObj.discount_amount)}</td>
                    <td className={`pl-1 py-1 text-right font-semibold ${val}`}>{fmtCurrency(costObj.extended)}</td>
                  </tr>
                  {/* Margin row */}
                  <tr className="line-row-margin border-t border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-900/50">
                    <td className="pr-2 py-1 text-xs font-semibold text-slate-600 dark:text-slate-300">Margin</td>
                    <td className={`px-1 py-1 text-right font-semibold tabular-nums ${
                      Number(priceObj.margin ?? 0) >= 0
                        ? "text-green-600 dark:text-green-400"
                        : "text-red-600 dark:text-red-400"
                    }`}>
                      {fmtCurrency(priceObj.margin)}
                    </td>
                    <td></td>
                    <td></td>
                    <td></td>
                    <td className={`pl-1 py-1 text-right font-semibold tabular-nums ${
                      Number(priceObj.margin_pc ?? 0) >= 0
                        ? "text-green-600 dark:text-green-400"
                        : "text-red-600 dark:text-red-400"
                    }`}>
                      {priceObj.margin_pc != null
                        ? `${Number(priceObj.margin_pc).toFixed(1)}%`
                        : "--"}
                    </td>
                  </tr>
                </tbody>
              </table>

              {/* ── Additional cost items + tax (inline clusters) ── */}
              <div className="mt-1.5 space-y-1">
                <div className={`${cluster} line-row-cost`}>
                  <span><span className={lbl}>Shipping</span><span className={val}>{fmtCurrency(costObj.shipping)}</span></span>
                  <span><span className={lbl}>Freight</span><span className={val}>{fmtCurrency(costObj.freight)}</span></span>
                  <span><span className={lbl}>Handling</span><span className={val}>{fmtCurrency(costObj.handling)}</span></span>
                </div>
                <div className={`${cluster} line-row-tax`}>
                  <span className="line-row-price">
                    <span className={lbl}>Sales Tax</span>
                    <span className={val}>{fmtCurrency(taxObj.sales)}</span>
                    {taxObj.sales_rate != null && (
                      <span className="text-xs text-slate-400 ml-0.5">({Number(taxObj.sales_rate).toFixed(2)}%)</span>
                    )}
                  </span>
                  <span className="line-row-cost">
                    <span className={lbl}>Cost Tax</span>
                    <span className={val}>{fmtCurrency(taxObj.cost)}</span>
                    {taxObj.cost_rate != null && (
                      <span className="text-xs text-slate-400 ml-0.5">({Number(taxObj.cost_rate).toFixed(2)}%)</span>
                    )}
                  </span>
                </div>
              </div>
            </section>
          </>
        )}

        {activeSection === "notes" && (
          <div className="space-y-3">
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
                rows={2}
                placeholder="Notes that appear on invoices, packing slips, etc."
                className={`${fieldCls} resize-none`}
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
                rows={2}
                placeholder="Internal processing notes"
                className={`${fieldCls} resize-none`}
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                Warehouse Instructions
              </label>
              <textarea
                value={String(notesObj.warehouse ?? "")}
                onChange={(e) =>
                  handleNestedFieldChange("notes", "warehouse", e.target.value)
                }
                disabled={!isEditing}
                rows={2}
                placeholder="Special handling, packing instructions, etc."
                className={`${fieldCls} resize-none`}
              />
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default withDevIdentifier(LineDetailsModal, "LineDetailsModal");
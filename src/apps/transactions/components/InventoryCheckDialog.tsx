/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * InventoryCheckDialog — modal dialog that fetches and displays an item's
 * inventory quantity buckets.  Launched from the LinesCard inventory badge.
 *
 * Designed to be expanded later with images, BOM data, etc.
 */
import React, { useEffect, useState } from "react";
import { FaTimes, FaSyncAlt, FaBoxes } from "react-icons/fa";
import { getRecord } from "@/api/wcapi";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface QuantityBuckets {
  on_hand: number;
  available: number;
  allocated: number;
  on_so: number;
  on_po: number;
  on_p: number;
  on_wo: number;
  on_in: number;
}

interface InventoryCheckDialogProps {
  /** The item's primary key (numeric ID) */
  itemId: number;
  /** Human-readable item code / SKU shown in the header */
  itemCode: string;
  /** Called when the user closes the dialog */
  onClose: () => void;
}

// ---------------------------------------------------------------------------
// Bucket display config
// ---------------------------------------------------------------------------

const BUCKET_ROWS: { key: keyof QuantityBuckets; label: string; highlight?: boolean }[] = [
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
// Component
// ---------------------------------------------------------------------------

const InventoryCheckDialog: React.FC<InventoryCheckDialogProps> = ({
  itemId,
  itemCode,
  onClose,
}) => {
  const [buckets, setBuckets] = useState<QuantityBuckets | null>(null);
  const [itemName, setItemName] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchInventory = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await getRecord("item", itemId);
      const record = payload?.record;
      if (!record) {
        setError(`Item #${itemId} not found`);
        setBuckets(null);
        return;
      }
      const qty = record.quantity ?? {};
      setBuckets({
        on_hand: qty.on_hand ?? 0,
        available: qty.available ?? 0,
        allocated: qty.allocated ?? 0,
        on_so: qty.on_so ?? 0,
        on_po: qty.on_po ?? 0,
        on_p: qty.on_p ?? 0,
        on_wo: qty.on_wo ?? 0,
        on_in: qty.on_in ?? 0,
      });
      setItemName(record.name || record.sku || `Item #${itemId}`);
    } catch (err: any) {
      setError(err?.message || "Failed to fetch inventory");
      setBuckets(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInventory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [itemId]);

  // Close on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const fmt = (v: number) => v.toLocaleString();

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      {/* Dialog */}
      <div
        className="bg-white dark:bg-slate-800 rounded-lg shadow-xl w-80 max-w-[90vw] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
          <div className="flex items-center gap-2">
            <FaBoxes className="text-blue-500" size={16} />
            <div>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                Inventory Check
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 truncate max-w-[180px]">
                {itemCode}{itemName ? ` — ${itemName}` : ""}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={fetchInventory}
              className="p-1.5 text-slate-400 hover:text-blue-500 transition-colors rounded hover:bg-slate-100 dark:hover:bg-slate-700"
              title="Refresh"
              disabled={loading}
            >
              <FaSyncAlt size={12} className={loading ? "animate-spin" : ""} />
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-red-500 transition-colors rounded hover:bg-slate-100 dark:hover:bg-slate-700"
              title="Close"
            >
              <FaTimes size={14} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="px-4 py-3">
          {error && (
            <div className="text-xs text-red-500 mb-2">{error}</div>
          )}

          {loading && !buckets && (
            <div className="flex items-center justify-center py-6 text-slate-400 text-xs">
              Loading inventory…
            </div>
          )}

          {buckets && (
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
                      {fmt(buckets[key])}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer — spacer for future expansion (images, BOM, etc.) */}
        <div className="px-4 py-2 border-t border-slate-100 dark:border-slate-700 text-right">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 text-xs font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 rounded hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default InventoryCheckDialog;

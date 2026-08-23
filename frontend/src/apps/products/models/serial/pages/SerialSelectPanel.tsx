/**
 * SerialSelectPanel — Select serial numbers for shipping on an invoice line.
 *
 * Two modes:
 *   1. Auto-select: system picks serials by strategy (FIFO, LIFO, cost)
 *   2. Manual pick: user clicks to select/deselect from available serials
 *
 * Quantity selected must match quantity shipped — exact match required.
 * Panel shows count validation in real time.
 */
import { useEffect, useState, useMemo, useCallback } from "react";
import { getRecords } from "@/api/wcapi";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import {
  Check,
  X,
  Zap,
  Hash,
  Package,
  DollarSign,
  AlertTriangle,
  CheckCircle,
} from "lucide-react";
import ComponentCard from "@/components/common/ComponentCard";
import { Button } from "@/components/wrapper";

// -- Types ------------------------------------------------------------------

interface SerialOption {
  id: number;
  serial_ida: string;
  model_ida: string;
  description: string;
  status: string;
  cost: number;
  site: Record<string, any>;
}

interface SerialSelectPanelProps {
  itemId: number;
  itemIda: string;
  qtyRequired: number;
  onSelectionConfirmed: (serialIds: number[]) => void;
  onCancel?: () => void;
}

type Strategy = "fifo" | "lifo" | "cost_low" | "cost_high";

const STRATEGY_LABELS: Record<Strategy, string> = {
  fifo: "FIFO (oldest first)",
  lifo: "LIFO (newest first)",
  cost_low: "Lowest cost first",
  cost_high: "Highest cost first",
};

// -- Component --------------------------------------------------------------

export default function SerialSelectPanel({
  itemId,
  itemIda,
  qtyRequired,
  onSelectionConfirmed,
  onCancel,
}: SerialSelectPanelProps) {
  const dispatch = useDispatch();
  const [availableSerials, setAvailableSerials] = useState<SerialOption[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [strategy, setStrategy] = useState<Strategy>("fifo");

  // Load available serials for this item
  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const result = await getRecords("serial", {
          item_id: itemId,
          status: "available",
          page_size: 500,
        });
        const items = result?.items || result?.data?.items || [];
        setAvailableSerials(items);
      } catch (err) {
        console.error("Failed to load available serials:", err);
        dispatch(
          showToast({ message: "Failed to load serials", type: "error" })
        );
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [itemId, dispatch]);

  // Count validation
  const selectedCount = selectedIds.size;
  const isExactMatch = selectedCount === qtyRequired;
  const isOverSelected = selectedCount > qtyRequired;

  // Toggle serial selection (click = select/deselect)
  const toggleSerial = useCallback(
    (id: number) => {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        if (next.has(id)) {
          next.delete(id);
        } else {
          next.add(id);
        }
        return next;
      });
    },
    []
  );

  // Auto-select by strategy
  const autoSelect = useCallback(() => {
    const sorted = [...availableSerials];

    switch (strategy) {
      case "fifo":
        sorted.sort((a, b) => a.id - b.id);
        break;
      case "lifo":
        sorted.sort((a, b) => b.id - a.id);
        break;
      case "cost_low":
        sorted.sort((a, b) => (a.cost || 0) - (b.cost || 0));
        break;
      case "cost_high":
        sorted.sort((a, b) => (b.cost || 0) - (a.cost || 0));
        break;
    }

    const picked = sorted.slice(0, qtyRequired);
    setSelectedIds(new Set(picked.map((s) => s.id)));
  }, [availableSerials, qtyRequired, strategy]);

  // Clear selection
  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  // Confirm
  const handleConfirm = useCallback(() => {
    if (!isExactMatch) {
      dispatch(
        showToast({
          message: `Select exactly ${qtyRequired} serials (${selectedCount} selected)`,
          type: "error",
        })
      );
      return;
    }
    onSelectionConfirmed(Array.from(selectedIds));
  }, [isExactMatch, qtyRequired, selectedCount, selectedIds, onSelectionConfirmed, dispatch]);

  // Selected serials summary
  const selectedSerials = useMemo(
    () => availableSerials.filter((s) => selectedIds.has(s.id)),
    [availableSerials, selectedIds]
  );

  const totalCost = useMemo(
    () => selectedSerials.reduce((sum, s) => sum + (s.cost || 0), 0),
    [selectedSerials]
  );

  if (loading) {
    return (
      <ComponentCard>
        <div className="flex justify-center items-center py-8">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-brand-500" />
          <span className="ml-3 text-slate-500">Loading serials...</span>
        </div>
      </ComponentCard>
    );
  }

  return (
    <ComponentCard>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold text-slate-900 dark:text-white">
            Select Serial Numbers
          </h3>
          <p className="text-sm text-slate-500 mt-0.5">
            <Package size={12} className="inline mr-1" />
            {itemIda} — {availableSerials.length} available
          </p>
        </div>

        {/* Count indicator */}
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
            isExactMatch
              ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
              : isOverSelected
              ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
              : "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200"
          }`}
        >
          {isExactMatch ? (
            <CheckCircle size={14} />
          ) : (
            <AlertTriangle size={14} />
          )}
          {selectedCount} / {qtyRequired}
        </div>
      </div>

      {/* Auto-select controls */}
      <div className="flex items-center gap-3 mb-4 p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
        <Zap size={14} className="text-slate-500" />
        <select
          className="px-2 py-1 rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-sm text-slate-900 dark:text-white"
          value={strategy}
          onChange={(e) => setStrategy(e.target.value as Strategy)}
        >
          {Object.entries(STRATEGY_LABELS).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
        <Button variant="outline" size="sm" onClick={autoSelect}>
          Auto-Select {qtyRequired}
        </Button>
        {selectedCount > 0 && (
          <Button variant="outline" size="sm" onClick={clearSelection}>
            Clear
          </Button>
        )}
      </div>

      {/* Available serials list */}
      {availableSerials.length === 0 ? (
        <div className="text-center py-8 text-slate-500">
          <AlertTriangle size={24} className="mx-auto mb-2" />
          No available serials for this item
        </div>
      ) : (
        <div className="max-h-80 overflow-y-auto border border-slate-200 dark:border-slate-700 rounded-lg divide-y divide-slate-100 dark:divide-slate-800">
          {availableSerials.map((serial) => {
            const isSelected = selectedIds.has(serial.id);
            return (
              <button
                key={serial.id}
                className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                  isSelected
                    ? "bg-blue-50 dark:bg-blue-900/30 border-l-2 border-l-blue-500"
                    : "hover:bg-slate-50 dark:hover:bg-slate-800 border-l-2 border-l-transparent"
                }`}
                onClick={() => toggleSerial(serial.id)}
              >
                {/* Selection indicator */}
                <div
                  className={`w-5 h-5 rounded flex items-center justify-center flex-shrink-0 ${
                    isSelected
                      ? "bg-blue-500 text-white"
                      : "border border-slate-300 dark:border-slate-600"
                  }`}
                >
                  {isSelected && <Check size={12} />}
                </div>

                {/* Serial info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-900 dark:text-white">
                      <Hash size={12} className="inline mr-0.5" />
                      {serial.serial_ida}
                    </span>
                    {serial.model_ida && (
                      <span className="text-xs text-slate-500">
                        {serial.model_ida}
                      </span>
                    )}
                  </div>
                  {serial.description && (
                    <div className="text-xs text-slate-500 truncate">
                      {serial.description}
                    </div>
                  )}
                </div>

                {/* Cost */}
                <div className="text-xs text-slate-500 flex-shrink-0">
                  <DollarSign size={10} className="inline" />
                  {(serial.cost || 0).toFixed(2)}
                </div>
              </button>
            );
          })}
        </div>
      )}

      {/* Selection summary */}
      {selectedCount > 0 && (
        <div className="mt-3 p-3 bg-slate-50 dark:bg-slate-800 rounded-lg text-sm">
          <div className="flex justify-between text-slate-600 dark:text-slate-400">
            <span>Selected: {selectedCount} units</span>
            <span>
              Total cost: <DollarSign size={10} className="inline" />
              {totalCost.toFixed(2)}
            </span>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-2 mt-4">
        {onCancel && (
          <Button variant="outline" size="sm" onClick={onCancel}>
            Cancel
          </Button>
        )}
        <Button
          variant="primary"
          size="sm"
          onClick={handleConfirm}
          disabled={!isExactMatch}
        >
          {isExactMatch
            ? `Confirm ${selectedCount} Serials`
            : `Select ${qtyRequired - selectedCount} more`}
        </Button>
      </div>
    </ComponentCard>
  );
}

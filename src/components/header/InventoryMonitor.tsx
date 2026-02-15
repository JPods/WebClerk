/**
 * InventoryMonitor – floating window that polls a single Item's quantity
 * buckets every 10 seconds and displays them in real time.
 *
 * Launched from the MacTopBar via a small toolbar button.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  FaBoxes,
  FaSyncAlt,
  FaTimes,
  FaGripHorizontal,
} from "react-icons/fa";
import { getRecord } from "@/api/wcapi";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface QuantityBuckets {
  on_hand: number;
  on_so: number;
  on_po: number;
  on_wo: number;
  on_in: number;
  on_p: number;
  available?: number;
  allocated?: number;
}

const BUCKET_LABELS: { key: keyof QuantityBuckets; label: string }[] = [
  { key: "on_hand", label: "On Hand" },
  { key: "available", label: "Available" },
  { key: "allocated", label: "Allocated" },
  { key: "on_so", label: "On SO" },
  { key: "on_po", label: "On PO" },
  { key: "on_wo", label: "On WO" },
  { key: "on_in", label: "On IN" },
  { key: "on_p", label: "On P" },
];

const POLL_INTERVAL = 10_000; // 10 seconds

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface Props {
  onClose: () => void;
}

export default function InventoryMonitor({ onClose }: Props) {
  const [itemId, setItemId] = useState<number>(1);
  const [inputValue, setInputValue] = useState("1");
  const [buckets, setBuckets] = useState<QuantityBuckets | null>(null);
  const [itemName, setItemName] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Drag state
  const [pos, setPos] = useState({ x: window.innerWidth - 340, y: 60 });
  const dragging = useRef(false);
  const dragOffset = useRef({ x: 0, y: 0 });

  // ---- Fetch -----------------------------------------------------------
  const fetchItem = useCallback(async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      const payload = await getRecord("item", id);
      const record = payload?.record;
      if (!record) {
        setError(`Item #${id} not found`);
        setBuckets(null);
        setItemName("");
      } else {
        const qty = record.quantity ?? {};
        setBuckets({
          on_hand: qty.on_hand ?? 0,
          on_so: qty.on_so ?? 0,
          on_po: qty.on_po ?? 0,
          on_wo: qty.on_wo ?? 0,
          on_in: qty.on_in ?? 0,
          on_p: qty.on_p ?? 0,
          available: qty.available ?? 0,
          allocated: qty.allocated ?? 0,
        });
        setItemName(record.name || record.sku || `Item #${id}`);
        setLastUpdate(new Date());
      }
    } catch (err: any) {
      setError(err?.message || "Failed to fetch item");
      setBuckets(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // ---- Polling ----------------------------------------------------------
  useEffect(() => {
    fetchItem(itemId);
    timerRef.current = setInterval(() => fetchItem(itemId), POLL_INTERVAL);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [itemId, fetchItem]);

  // ---- Dragging ---------------------------------------------------------
  const onMouseDown = (e: React.MouseEvent) => {
    dragging.current = true;
    dragOffset.current = { x: e.clientX - pos.x, y: e.clientY - pos.y };
    e.preventDefault();
  };

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      setPos({
        x: e.clientX - dragOffset.current.x,
        y: e.clientY - dragOffset.current.y,
      });
    };
    const onMouseUp = () => {
      dragging.current = false;
    };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, []);

  // ---- Handlers ---------------------------------------------------------
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = parseInt(inputValue, 10);
    if (!isNaN(parsed) && parsed > 0) {
      setItemId(parsed);
    }
  };

  // ---- Render -----------------------------------------------------------
  return (
    <div
      className="fixed z-[9999] w-[300px] rounded-xl border border-slate-200 bg-white shadow-2xl dark:border-slate-700 dark:bg-slate-800"
      style={{ left: pos.x, top: pos.y }}
    >
      {/* Title bar – draggable */}
      <div
        className="flex cursor-grab items-center justify-between rounded-t-xl bg-slate-100 px-3 py-2 dark:bg-slate-700"
        onMouseDown={onMouseDown}
      >
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-200">
          <FaGripHorizontal className="text-slate-400" />
          <FaBoxes className="text-emerald-500" />
          Inventory Monitor
        </div>
        <button
          onClick={onClose}
          className="rounded p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-700 dark:hover:bg-slate-600 dark:hover:text-white"
          title="Close"
        >
          <FaTimes size={12} />
        </button>
      </div>

      <div className="p-3 space-y-3">
        {/* Item ID input */}
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <label className="text-[11px] font-medium text-slate-500 dark:text-slate-400 whitespace-nowrap">
            Item ID
          </label>
          <input
            type="number"
            min={1}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            className="w-20 rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-800 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200"
          />
          <button
            type="submit"
            className="rounded bg-emerald-500 px-2 py-1 text-[11px] font-medium text-white hover:bg-emerald-600"
          >
            Go
          </button>
          <button
            type="button"
            onClick={() => fetchItem(itemId)}
            className="rounded p-1 text-slate-400 hover:text-emerald-500"
            title="Refresh now"
          >
            <FaSyncAlt size={12} className={loading ? "animate-spin" : ""} />
          </button>
        </form>

        {/* Item name */}
        {itemName && (
          <div className="text-xs font-medium text-slate-700 dark:text-slate-300 truncate">
            {itemName}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="rounded bg-red-50 px-2 py-1 text-[11px] text-red-600 dark:bg-red-900/30 dark:text-red-400">
            {error}
          </div>
        )}

        {/* Buckets */}
        {buckets && (
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            {BUCKET_LABELS.map(({ key, label }) => (
              <div key={key} className="flex items-center justify-between">
                <span className="text-[11px] text-slate-500 dark:text-slate-400">
                  {label}
                </span>
                <span
                  className={`text-xs font-mono font-semibold ${
                    key === "on_hand"
                      ? "text-emerald-600 dark:text-emerald-400"
                      : "text-slate-700 dark:text-slate-300"
                  }`}
                >
                  {buckets[key] ?? 0}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Last update timestamp */}
        {lastUpdate && (
          <div className="text-[10px] text-slate-400 dark:text-slate-500 text-right">
            Updated {lastUpdate.toLocaleTimeString()} · polls every 10s
          </div>
        )}
      </div>
    </div>
  );
}

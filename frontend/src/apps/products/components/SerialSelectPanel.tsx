/**
 * SerialSelectPanel -- search and select serials for assignment to transactions.
 * Used in order/invoice line editing to pick available serial numbers.
 * Pattern matches TransactionItemSearch.
 */
import React, { useState, useCallback, useRef } from "react";
import { getRecords } from "@/api/wcapi";

const STATUS_COLORS: Record<string, string> = {
  available: "text-green-500",
  received: "text-blue-400",
  reserved: "text-amber-400",
  issued: "text-slate-400",
};

export interface SerialSelectResult {
  id: number;
  serial_ida: string;
  item_ida: string;
  model_ida: string;
  status: string;
  warranty: any;
  config: any;
}

interface Props {
  /** Called when user selects a serial */
  onSelect: (serial: SerialSelectResult) => void;
  /** Filter to specific item */
  itemId?: number;
  /** Only show serials with these statuses (default: available) */
  statusFilter?: string[];
  /** Placeholder text */
  placeholder?: string;
}

export default function SerialSelectPanel({
  onSelect,
  itemId,
  statusFilter = ["available"],
  placeholder = "Search serial number...",
}: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const search = useCallback(async () => {
    const q = query.trim();
    if (!q) {
      setResults([]);
      return;
    }

    setLoading(true);
    try {
      const params: any = { keyword: q, limit: 25 };
      if (itemId) params.item_id = itemId;
      if (statusFilter.length === 1) params.status = statusFilter[0];

      const res = await getRecords("serial", params);
      let rows = res?.results || res?.records || [];

      // Client-side status filter if multiple statuses
      if (statusFilter.length > 1) {
        rows = rows.filter((r: any) => statusFilter.includes(r.status));
      }

      setResults(rows);
    } catch {
      setResults([]);
    }
    setLoading(false);
  }, [query, itemId, statusFilter]);

  const handleSelect = (serial: any) => {
    onSelect({
      id: serial.id,
      serial_ida: serial.serial_ida || serial.ida || "",
      item_ida: serial.item_ida || "",
      model_ida: serial.model_ida || "",
      status: serial.status || "",
      warranty: serial.warranty || {},
      config: serial.config || {},
    });
    setResults([]);
    setQuery("");
    inputRef.current?.focus();
  };

  return (
    <div className="space-y-1">
      {/* Search input */}
      <div className="flex gap-1">
        <input
          ref={inputRef}
          type="text"
          value={query}
          placeholder={placeholder}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
          className="flex-1 px-2 py-1 text-xs border border-slate-600 rounded bg-slate-900 text-slate-200"
        />
        <button
          onClick={search}
          disabled={loading}
          className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          {loading ? "..." : "Search"}
        </button>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="border border-slate-700 rounded max-h-48 overflow-y-auto">
          {results.map((s: any) => {
            const serialNum = s.serial_ida || s.ida || "";
            const status = s.status || "";
            const itemCode = s.item_ida || "";
            const model = s.model_ida || "";

            return (
              <div
                key={s.id}
                onClick={() => handleSelect(s)}
                className="flex items-center gap-2 px-2 py-1 text-xs border-b border-slate-800 last:border-0 hover:bg-slate-800 cursor-pointer"
              >
                <span className="font-mono font-semibold text-slate-200 w-32 truncate">{serialNum}</span>
                <span className={`w-20 ${STATUS_COLORS[status] || "text-slate-400"}`}>{status}</span>
                <span className="text-slate-500 w-20 truncate">{itemCode}</span>
                <span className="text-slate-500 flex-1 truncate">{model}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

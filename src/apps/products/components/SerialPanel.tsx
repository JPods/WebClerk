/**
 * SerialViewPanel -- shows serials for an item on the Item dashboard.
 * Header row + filterable list of SerialCards. Click opens in DataBrowser.
 */
import React, { useState, useEffect, useCallback } from "react";
import { getRecords } from "@/api/wcapi";
import { useWindowManager } from "@/context/WindowManagerContext";
import SerialCard from "./SerialCard";

export interface SerialPanelProps {
  /** Filter by item (Item dashboard) */
  itemId?: number;
  itemCode?: string;
  /** Filter by customer (Customer record -- shows serials they hold) */
  customerId?: number;
  /** Filter by vendor (Vendor record -- shows serials sourced from them) */
  vendorId?: number;
  /** Filter by manufacturer (shows serials of their items) */
  manufacturerId?: number;
  /** Label override */
  title?: string;
}

const STATUSES = [
  { value: "", label: "All" },
  { value: "available", label: "Available" },
  { value: "received", label: "Received" },
  { value: "reserved", label: "Reserved" },
  { value: "issued", label: "Issued" },
  { value: "returned", label: "Returned" },
  { value: "referenced", label: "Referenced" },
  { value: "warranty", label: "Warranty" },
  { value: "damaged", label: "Damaged" },
  { value: "scrapped", label: "Scrapped" },
];

const SerialPanel: React.FC<SerialPanelProps> = ({
  itemId, itemCode, customerId, vendorId, manufacturerId, title,
}) => {
  const [serials, setSerials] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const windowManager = useWindowManager();

  const panelTitle = title
    || (itemCode ? `Serials for ${itemCode}` : "Serials");

  const fetchSerials = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = { limit: 200 };
      if (itemId) params.item_id = itemId;
      if (customerId) params["config__customer_id"] = customerId;
      if (vendorId) params["config__vendor_id"] = vendorId;
      if (manufacturerId) params["item__manufacturer_id"] = manufacturerId;
      if (statusFilter) params.status = statusFilter;
      const res = await getRecords("serial", params);
      setSerials(res?.results || res?.records || []);
    } catch {
      setSerials([]);
    }
    setLoading(false);
  }, [itemId, customerId, vendorId, manufacturerId, statusFilter]);

  useEffect(() => {
    fetchSerials();
  }, [fetchSerials]);

  const handleClick = (id: number) => {
    windowManager.ensureWindow(`/serial?id=${id}`, `Serial #${id}`);
  };

  // Count by status
  const counts: Record<string, number> = {};
  for (const s of serials) {
    const st = s.status || "unknown";
    counts[st] = (counts[st] || 0) + 1;
  }

  return (
    <div className="p-2">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-bold text-slate-600 dark:text-slate-300">
          {panelTitle}
        </span>
        <span className="text-[9px] text-slate-400">({serials.length})</span>
        <span className="flex-1" />
        {/* Status counts */}
        {Object.entries(counts).map(([st, n]) => (
          <button
            key={st}
            onClick={() => setStatusFilter(statusFilter === st ? "" : st)}
            className={`text-[9px] px-1.5 py-0.5 rounded ${
              statusFilter === st
                ? "bg-blue-600 text-white"
                : "bg-slate-700 text-slate-400 hover:bg-slate-600"
            }`}
          >
            {st} ({n})
          </button>
        ))}
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="text-[10px] px-1 py-0.5 border border-slate-600 rounded bg-slate-800 text-slate-300"
        >
          {STATUSES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      {/* Header */}
      <div className="flex items-center gap-2 px-2 py-1 text-[10px] font-medium text-slate-500 border-b-2 border-slate-700">
        <span className="w-32">Serial #</span>
        <span className="w-20">Status</span>
        <span className="w-20">Item</span>
        <span className="flex-1">Party</span>
        <span className="w-24 text-right">Document</span>
      </div>

      {loading ? (
        <div className="text-xs text-slate-400 py-4 text-center">Loading...</div>
      ) : serials.length === 0 ? (
        <div className="text-xs text-slate-400 italic py-4 text-center">
          No serial numbers{statusFilter ? ` with status "${statusFilter}"` : ""}
        </div>
      ) : (
        serials.map((s: any) => (
          <SerialCard key={s.id} data={s} onClick={handleClick} />
        ))
      )}
    </div>
  );
};

export default SerialPanel;

/**
 * SerialViewPanel -- shows serials for an item on the Item dashboard.
 * Header row + filterable list of SerialCards. Click opens in DataBrowser.
 */
import React, { useMemo, useState } from "react";
import { usePanelFrame } from "@/apps/common/components/CollapsiblePanel";
import { usePanelRecords } from "@/hooks/usePanelRecords";
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
  const [statusFilter, setStatusFilter] = useState("");
  const windowManager = useWindowManager();

  // One read path and one status (usePanelRecords); the frame draws title, count and status.
  const params = useMemo(() => {
    const p: Record<string, unknown> = { limit: 200 };
    if (itemId) p.item_id = itemId;
    if (customerId) p["config__customer_id"] = customerId;
    if (vendorId) p["config__vendor_id"] = vendorId;
    if (manufacturerId) p["item__manufacturer_id"] = manufacturerId;
    if (statusFilter) p.status = statusFilter;
    return p;
  }, [itemId, customerId, vendorId, manufacturerId, statusFilter]);
  const { records: serials, status } = usePanelRecords<any>("serial", params, {
    emptyText: `No serial numbers${statusFilter ? ` with status "${statusFilter}"` : ""}${itemCode ? ` for ${itemCode}` : ""}`,
  });

  const handleClick = (id: number) => {
    windowManager.ensureWindow(`/serial?id=${id}`, `Serial #${id}`);
  };

  // Count by status
  const counts: Record<string, number> = {};
  for (const s of serials) {
    const st = s.status || "unknown";
    counts[st] = (counts[st] || 0) + 1;
  }
  const countKey = JSON.stringify(counts);

  const filters = useMemo(() => (
    <>
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
        title={title}
      >
        {STATUSES.map((s) => (
          <option key={s.value} value={s.value}>
            {s.label}
          </option>
        ))}
      </select>
    </>
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ), [countKey, statusFilter, title]);
  usePanelFrame({ badge: serials.length, headerActions: filters, status });

  return (
    <div>
      {/* Column labels stay in view while the rows scroll (TFTS 2026-10-27) */}
      <div className="sticky top-0 flex items-center gap-2 px-2 py-1 text-[10px] font-medium text-slate-500 border-b-2 border-slate-700"
           style={{ background: "var(--db-surface, #fff)", zIndex: 1 }}>
        <span className="w-32">Serial #</span>
        <span className="w-20">Status</span>
        <span className="w-20">Item</span>
        <span className="flex-1">Party</span>
        <span className="w-24 text-right">Document</span>
      </div>
      {serials.map((s: any) => (
        <SerialCard key={s.id} data={s} onClick={handleClick} />
      ))}
    </div>
  );
};

export default SerialPanel;

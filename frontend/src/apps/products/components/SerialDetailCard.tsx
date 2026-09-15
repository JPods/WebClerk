/**
 * SerialDetailCard -- expanded view of a single serial.
 * Shows full config (customer, vendor, document refs, cost/price, floor plan),
 * warranty status, and action log. Used in DataBrowser detail view.
 */
import React, { useEffect, useState } from "react";
import { getRecords } from "@/api/wcapi";
import { formatDt } from '@/utils/fieldFormatters';
import { formatCurrency } from '@/utils/stringUtils';

const STATUS_COLORS: Record<string, string> = {
  available: "bg-green-600",
  received: "bg-blue-500",
  reserved: "bg-amber-500",
  issued: "bg-slate-500",
  returned: "bg-purple-500",
  referenced: "bg-cyan-500",
  warranty: "bg-orange-500",
  damaged: "bg-red-600",
  scrapped: "bg-slate-700",
};

interface Props {
  data: any;
}

export default function SerialDetailCard({ data }: Props) {
  const [logs, setLogs] = useState<any[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);

  const cfg = data.config || {};
  const warranty = data.warranty || {};
  const status = data.status || "";
  const serialNum = data.serial_ida || data.ida || "";
  const itemCode = data.item_ida || "";
  const model = data.model_ida || "";

  useEffect(() => {
    if (!data.id) return;
    setLogsLoading(true);
    getRecords("serial_log", { serial_id: data.id, limit: 50 })
      .then((res: any) => setLogs(res?.results || res?.records || []))
      .catch(() => setLogs([]))
      .finally(() => setLogsLoading(false));
  }, [data.id]);

  const fmtDate = (iso: string | null) => {
    if (!iso) return "--";
    return formatDt(iso, 'date');
  };

  return (
    <div className="space-y-3 p-3">
      {/* Header */}
      <div className="flex items-center gap-3">
        <span className="font-mono text-base font-bold text-slate-200">{serialNum}</span>
        <span className={`text-[10px] px-2 py-0.5 rounded-full text-white ${STATUS_COLORS[status] || "bg-slate-600"}`}>
          {status}
        </span>
        {model && <span className="text-xs text-slate-500">Model: {model}</span>}
        {itemCode && <span className="text-xs text-slate-500">Item: {itemCode}</span>}
      </div>

      {/* Two-column details */}
      <div className="grid grid-cols-2 gap-3">
        {/* Transaction context */}
        <div className="bg-slate-800/50 rounded p-2 space-y-1">
          <div className="text-[10px] font-bold text-slate-400 uppercase mb-1">Transaction</div>
          <Row label="Customer" value={cfg.customer_id} />
          <Row label="Vendor" value={cfg.vendor_id} />
          <Row label="Invoice" value={cfg.invoice_id} />
          <Row label="Order" value={cfg.order_id} />
          <Row label="Purchase" value={cfg.purchase_id} />
          <Row label="Received" value={fmtDate(cfg.dt_received)} />
          <Row label="Shipped" value={fmtDate(cfg.dt_shipped)} />
          <Row label="Days on plan" value={cfg.days_on_plan} />
        </div>

        {/* Financials + Warranty */}
        <div className="space-y-3">
          <div className="bg-slate-800/50 rounded p-2 space-y-1">
            <div className="text-[10px] font-bold text-slate-400 uppercase mb-1">Financials</div>
            <Row label="Cost" value={formatCurrency(cfg.cost) || "--"} />
            <Row label="Price" value={formatCurrency(cfg.price) || "--"} />
            <Row label="Discount" value={cfg.discount ? `${cfg.discount}%` : "--"} />
          </div>

          <div className="bg-slate-800/50 rounded p-2 space-y-1">
            <div className="text-[10px] font-bold text-slate-400 uppercase mb-1">Warranty</div>
            <Row label="Days" value={warranty.days || "--"} />
            <Row label="Start" value={fmtDate(warranty.dt_start)} />
            <Row label="End" value={fmtDate(warranty.dt_end)} />
            {warranty.dt_end && new Date(warranty.dt_end) > new Date() && (
              <div className="text-[10px] text-green-400 font-semibold">Active</div>
            )}
            {warranty.dt_end && new Date(warranty.dt_end) <= new Date() && (
              <div className="text-[10px] text-red-400 font-semibold">Expired</div>
            )}
          </div>

          {cfg.floor_plan?.is_active && (
            <div className="bg-slate-800/50 rounded p-2 space-y-1">
              <div className="text-[10px] font-bold text-slate-400 uppercase mb-1">Floor Plan</div>
              <Row label="Expires" value={fmtDate(cfg.floor_plan.dt_expires)} />
              <Row label="Plan line" value={cfg.floor_plan.plan_line} />
            </div>
          )}
        </div>
      </div>

      {/* Action log */}
      <div>
        <div className="text-[10px] font-bold text-slate-400 uppercase mb-1">Action History</div>
        {logsLoading ? (
          <div className="text-xs text-slate-500 py-2">Loading...</div>
        ) : logs.length === 0 ? (
          <div className="text-xs text-slate-500 italic py-2">No actions recorded</div>
        ) : (
          <div className="border border-slate-700 rounded overflow-hidden">
            {logs.map((log: any) => {
              const logCfg = log.config || {};
              const dt = log.dt ? formatDt(log.dt, 'datetime') : "";
              return (
                <div key={log.id} className="flex items-center gap-2 px-2 py-1 text-xs border-b border-slate-800 last:border-0">
                  <span className="text-slate-500 w-36 shrink-0">{dt}</span>
                  <span className="text-slate-200 flex-1">{log.action}</span>
                  {logCfg.doc_type && (
                    <span className="text-slate-500 w-24 text-right">
                      {logCfg.doc_type} #{logCfg.doc_id}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: any }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="flex justify-between text-xs">
      <span className="text-slate-500">{label}</span>
      <span className="text-slate-300 font-mono">{String(value)}</span>
    </div>
  );
}

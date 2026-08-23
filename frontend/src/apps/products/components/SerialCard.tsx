/**
 * SerialCard -- row in a serial list.
 * Shows serial number, status badge, item, customer/vendor, document ref.
 * Used by SerialViewPanel and DataBrowser list views.
 */
import React from "react";

const STATUS_COLORS: Record<string, string> = {
  available: "text-green-500",
  received: "text-blue-400",
  reserved: "text-amber-400",
  issued: "text-slate-400",
  returned: "text-purple-400",
  referenced: "text-cyan-400",
  warranty: "text-orange-400",
  damaged: "text-red-500",
  scrapped: "text-slate-600",
};

export interface SerialCardProps {
  data: any;
  onClick?: (id: number) => void;
}

const SerialCard: React.FC<SerialCardProps> = ({ data, onClick }) => {
  const serialNum = data.serial_ida || data.ida || "";
  const status = data.status || "";
  const cfg = data.config || {};
  const itemCode = data.item_ida || "";

  // Show the most relevant party
  const party = cfg.customer_id
    ? `Customer #${cfg.customer_id}`
    : cfg.vendor_id
    ? `Vendor #${cfg.vendor_id}`
    : "";

  // Show the most relevant document
  const doc = cfg.invoice_id
    ? `Invoice #${cfg.invoice_id}`
    : cfg.order_id
    ? `Order #${cfg.order_id}`
    : cfg.purchase_id
    ? `PO #${cfg.purchase_id}`
    : "";

  return (
    <div
      className="flex items-center gap-2 px-2 py-1 text-xs border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer"
      onClick={() => onClick?.(data.id)}
    >
      <span className="font-mono text-slate-700 dark:text-slate-200 w-32 truncate">{serialNum}</span>
      <span className={`w-20 ${STATUS_COLORS[status] || "text-slate-400"}`}>{status}</span>
      <span className="text-slate-500 w-20 truncate">{itemCode}</span>
      <span className="text-slate-500 flex-1 truncate">{party}</span>
      <span className="font-mono text-slate-400 w-24 truncate text-right">{doc}</span>
    </div>
  );
};

export default SerialCard;

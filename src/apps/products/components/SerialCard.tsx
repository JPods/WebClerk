/* LastChecked: 2026-08-03 | WhereUsed: ItemDetail Serials tab | WhoCreated: Claude */
/**
 * SerialCard — renders a single serial number record.
 * Shows serial number, status, assignment (customer/order/invoice).
 */
import React from 'react';

export interface SerialCardProps {
  data: any;
  onClick?: (id: number) => void;
}

const SerialCard: React.FC<SerialCardProps> = ({ data, onClick }) => {
  const serialNum = data.serial_number || data.config?.serial_number || data.ida || '';
  const status = data.status || data.config?.status || '';
  const customer = data.config?.customer_name || data.customer_name || '';
  const orderId = data.config?.order_ida || data.order_ida || '';

  const statusColor = status === 'available' ? 'text-green-600'
    : status === 'sold' ? 'text-slate-500'
    : status === 'reserved' ? 'text-amber-600'
    : status === 'defective' ? 'text-red-600'
    : 'text-slate-400';

  return (
    <div className="flex items-center gap-2 px-2 py-1 text-xs border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer"
      onClick={() => onClick?.(data.id)}
    >
      <span className="font-mono text-slate-700 dark:text-slate-200 w-32 truncate">{serialNum}</span>
      <span className={`w-16 ${statusColor}`}>{status}</span>
      <span className="text-slate-500 flex-1 truncate">{customer}</span>
      <span className="font-mono text-slate-400 w-20 truncate">{orderId}</span>
    </div>
  );
};

export default SerialCard;

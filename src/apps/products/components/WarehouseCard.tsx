/* LastChecked: 2026-08-03 | WhereUsed: ItemDetail Inventory tab | WhoCreated: Claude */
/**
 * WarehouseCard — shows one warehouse/location record for an item.
 * Displays: warehouse name, bin, qty on hand, qty available.
 */
import React from 'react';

export interface WarehouseCardProps {
  data: any;
  onClick?: (id: number) => void;
}

const WarehouseCard: React.FC<WarehouseCardProps> = ({ data, onClick }) => {
  return (
    <div className="flex items-center gap-2 px-2 py-1 text-xs border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 cursor-pointer"
      onClick={() => onClick?.(data.id)}>
      <span className="font-medium text-slate-700 w-28 truncate">{data.name || data.ida || ''}</span>
      <span className="text-slate-500 w-20 truncate">{data.bin || data.location_bin || ''}</span>
      <span className="font-mono text-right w-16">{data.qty_on_hand ?? data.config?.qty_on_hand ?? '—'}</span>
      <span className="font-mono text-right w-16 text-slate-400">{data.qty_available ?? data.config?.qty_available ?? '—'}</span>
    </div>
  );
};

export default WarehouseCard;

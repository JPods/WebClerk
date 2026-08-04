/* LastChecked: 2026-08-03 | WhereUsed: ItemDetail Variants tab | WhoCreated: Claude */
/**
 * VariantCard — shows one item variant (size, color, style, etc.)
 */
import React from 'react';

export interface VariantCardProps {
  data: any;
  onClick?: (id: number) => void;
}

const VariantCard: React.FC<VariantCardProps> = ({ data, onClick }) => {
  return (
    <div className="flex items-center gap-2 px-2 py-1 text-xs border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 cursor-pointer"
      onClick={() => onClick?.(data.id)}>
      <span className="font-mono text-slate-700 w-28 truncate">{data.ida || data.sku || ''}</span>
      <span className="text-slate-500 flex-1 truncate">{data.description || data.name || ''}</span>
      <span className="text-slate-400 w-16">{data.attribute_1 || data.config?.color || ''}</span>
      <span className="text-slate-400 w-16">{data.attribute_2 || data.config?.size || ''}</span>
      <span className="font-mono text-right w-16">{data.qty_on_hand ?? '—'}</span>
    </div>
  );
};

export default VariantCard;

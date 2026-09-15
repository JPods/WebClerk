/* LastChecked: 2026-08-03 | WhereUsed: ItemDetail Specs tab | WhoCreated: Claude */
/**
 * SpecCard — shows one specification record (name, value, unit).
 */
import React from 'react';

export interface SpecCardProps {
  data: any;
}

const SpecCard: React.FC<SpecCardProps> = ({ data }) => {
  return (
    <div className="flex items-center gap-2 px-2 py-1 text-xs border-b border-slate-100 dark:border-slate-700">
      <span className="font-medium text-slate-700 w-32 truncate">{data.name || ''}</span>
      <span className="font-mono text-slate-900 w-24">{data.value || ''}</span>
      <span className="text-slate-400 w-16">{data.unit || ''}</span>
      <span className="text-slate-400 flex-1 truncate">{data.category || ''}</span>
    </div>
  );
};

export default SpecCard;

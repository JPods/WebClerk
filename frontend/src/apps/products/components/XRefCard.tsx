/* LastChecked: 2026-08-03 | WhereUsed: ItemDetail XRef tab | WhoCreated: Claude */
/**
 * XRefCard — shows one cross-reference record (customer part#, vendor part#, etc.)
 */
import React from 'react';

export interface XRefCardProps {
  data: any;
  onClick?: (id: number) => void;
}

const XRefCard: React.FC<XRefCardProps> = ({ data, onClick }) => {
  return (
    <div className="flex items-center gap-2 px-2 py-1 text-xs border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 cursor-pointer"
      onClick={() => onClick?.(data.id)}>
      <span className="text-slate-400 w-16">{data.type || data.xref_type || 'xref'}</span>
      <span className="font-mono text-slate-700 w-28 truncate">{data.xref_code || data.ida || ''}</span>
      <span className="text-slate-500 flex-1 truncate">{data.description || data.org_name || ''}</span>
      <span className="text-slate-400 w-20 truncate">{data.org_ida || ''}</span>
    </div>
  );
};

export default XRefCard;

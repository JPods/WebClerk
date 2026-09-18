/* LastChecked: 2026-08-03 | WhereUsed: ItemDetail tabs | WhoCreated: Claude */
/**
 * ProductListPanel — generic list panel for product sub-models.
 * Fetches records by parent item, renders with a card component.
 * Used for: warehouse, variants, xrefs, specs, catalogs, usage.
 *
 * Usage:
 *   <ProductListPanel model="warehouse" itemId={256} itemCode="BB401"
 *     CardComponent={WarehouseCard} headers={['Name','Bin','On Hand','Available']}
 *     headerWidths={['w-28','w-20','w-16','w-16']} />
 */
import React, { useState, useEffect, useCallback } from 'react';
import { getRecords } from '@/api/wcapi';

export interface ProductListPanelProps {
  model: string;
  itemId: number;
  itemCode: string;
  filterField?: string;  // default: 'item_id'
  CardComponent: React.FC<any>;
  headers: string[];
  headerWidths?: string[];
  onCardClick?: (id: number) => void;
}

const ProductListPanel: React.FC<ProductListPanelProps> = ({
  model, itemId, itemCode, filterField = 'item_id',
  CardComponent, headers, headerWidths, onCardClick,
}) => {
  const [records, setRecords] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchRecords = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getRecords(model, { [filterField]: itemId, limit: 200 });
      setRecords(res?.results || res?.records || []);
    } catch { setRecords([]); }
    setLoading(false);
  }, [model, itemId, filterField]);

  useEffect(() => { fetchRecords(); }, [fetchRecords]);

  return (
    <div className="p-2">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-bold text-slate-600 capitalize">{model}s for {itemCode}</span>
        <span className="text-[9px] text-slate-400">({records.length})</span>
      </div>
      {/* Header */}
      <div className="flex items-center gap-2 px-2 py-1 text-[10px] font-medium text-slate-400 border-b-2 border-slate-200">
        {headers.map((h, i) => (
          <span key={h} className={headerWidths?.[i] || 'flex-1'}>{h}</span>
        ))}
      </div>
      {loading ? (
        <div className="text-xs text-slate-400 py-4 text-center">Loading...</div>
      ) : records.length === 0 ? (
        <div className="text-xs text-slate-400 italic py-4 text-center">No {model} records</div>
      ) : (
        records.map((r: any) => (
          <CardComponent key={r.id} data={r} onClick={onCardClick} />
        ))
      )}
    </div>
  );
};

export default ProductListPanel;

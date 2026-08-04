/* LastChecked: 2026-08-03 | WhereUsed: ItemDetail BOM tab | WhoCreated: Claude */
/**
 * BomPanel — shows BOM components for an item.
 * Header row + list of BomCards. Add button for new components.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { getRecords } from '@/api/wcapi';
import { useWindowManager } from '@/context/WindowManagerContext';
import BomCard from './BomCard';

export interface BomPanelProps {
  itemId: number;
  itemCode: string;
}

const BomPanel: React.FC<BomPanelProps> = ({ itemId, itemCode }) => {
  const [components, setComponents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const windowManager = useWindowManager();

  const fetchBom = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getRecords('bill_of_material', { parent_item_id: itemId, limit: 100 });
      setComponents(res?.results || res?.records || []);
    } catch { setComponents([]); }
    setLoading(false);
  }, [itemId]);

  useEffect(() => { fetchBom(); }, [fetchBom]);

  return (
    <div className="p-2">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-bold text-slate-600">Components of {itemCode}</span>
        <span className="text-[9px] text-slate-400">({components.length})</span>
        <span className="flex-1" />
        <button onClick={() => {/* TODO: add component search */}}
          className="text-[9px] text-green-600 hover:text-green-800 font-medium">+ add component</button>
      </div>
      {/* Header */}
      <div className="flex items-center gap-2 px-2 py-1 text-[10px] font-medium text-slate-400 border-b-2 border-slate-200">
        <span className="w-28">Item</span>
        <span className="flex-1">Description</span>
        <span className="w-16 text-right">Qty</span>
        <span className="w-8">UOM</span>
        <span className="w-16"></span>
      </div>
      {loading ? (
        <div className="text-xs text-slate-400 py-4 text-center">Loading...</div>
      ) : components.length === 0 ? (
        <div className="text-xs text-slate-400 italic py-4 text-center">No BOM components</div>
      ) : (
        components.map((c: any) => (
          <BomCard
            key={c.id}
            data={c}
            parentItemId={itemId}
            onSave={() => fetchBom()}
            onDelete={() => fetchBom()}
            onClick={(childId) => {
              if (childId) windowManager.ensureWindow(`/item/${childId}`, `Item #${childId}`);
            }}
          />
        ))
      )}
    </div>
  );
};

export default BomPanel;

/* LastChecked: 2026-08-03 | WhereUsed: ItemDetail Serials tab | WhoCreated: Claude */
/**
 * SerialPanel — shows serial numbers for an item.
 * Header row + list of SerialCards. Filterable by status.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { getRecords } from '@/api/wcapi';
import SerialCard from './SerialCard';

export interface SerialPanelProps {
  itemId: number;
  itemCode: string;
}

const SerialPanel: React.FC<SerialPanelProps> = ({ itemId, itemCode }) => {
  const [serials, setSerials] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');

  const fetchSerials = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = { item_id: itemId, limit: 200 };
      if (statusFilter) params.status = statusFilter;
      const res = await getRecords('serial_log', params);
      setSerials(res?.results || res?.records || []);
    } catch { setSerials([]); }
    setLoading(false);
  }, [itemId, statusFilter]);

  useEffect(() => { fetchSerials(); }, [fetchSerials]);

  return (
    <div className="p-2">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-bold text-slate-600">Serials for {itemCode}</span>
        <span className="text-[9px] text-slate-400">({serials.length})</span>
        <span className="flex-1" />
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="text-[10px] px-1 py-0.5 border border-slate-300 rounded bg-white text-slate-600">
          <option value="">All</option>
          <option value="available">Available</option>
          <option value="sold">Sold</option>
          <option value="reserved">Reserved</option>
          <option value="defective">Defective</option>
          <option value="returned">Returned</option>
        </select>
      </div>
      {/* Header */}
      <div className="flex items-center gap-2 px-2 py-1 text-[10px] font-medium text-slate-400 border-b-2 border-slate-200">
        <span className="w-32">Serial #</span>
        <span className="w-16">Status</span>
        <span className="flex-1">Customer</span>
        <span className="w-20">Order</span>
      </div>
      {loading ? (
        <div className="text-xs text-slate-400 py-4 text-center">Loading...</div>
      ) : serials.length === 0 ? (
        <div className="text-xs text-slate-400 italic py-4 text-center">No serial numbers{statusFilter ? ` with status "${statusFilter}"` : ''}</div>
      ) : (
        serials.map((s: any) => (
          <SerialCard key={s.id} data={s} />
        ))
      )}
    </div>
  );
};

export default SerialPanel;

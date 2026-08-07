/* LastChecked: 2026-08-06 | WhereUsed: ItemDetail BOM tab | WhoCreated: Claude */
/**
 * BomPanel — BOM editor for an item.
 * List of BomCards with add-component search, inline editing of all fields.
 * Backend handles cycle detection and cost rollup.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { getRecords, saveRecord } from '@/api/wcapi';
import { searchItems } from '@/api/wcapi';
import apiClient from '@/api/axios';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';
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
  const dispatch = useDispatch();

  // Selection
  const [selectedId, setSelectedId] = useState<number | null>(null);

  // Build from BOM
  const [showBuild, setShowBuild] = useState(false);
  const [buildQty, setBuildQty] = useState('1');
  const [buildReason, setBuildReason] = useState('');
  const [building, setBuilding] = useState(false);

  // Add component search
  const [showSearch, setShowSearch] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const [adding, setAdding] = useState(false);

  const fetchBom = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getRecords('bill_of_material', { parent_item_id: itemId, limit: 100 });
      const items = res?.results || res?.records || [];
      // Sort by sequence then id
      items.sort((a: any, b: any) => (a.sequence || 0) - (b.sequence || 0) || (a.id || 0) - (b.id || 0));
      setComponents(items);
    } catch { setComponents([]); }
    setLoading(false);
  }, [itemId]);

  useEffect(() => { fetchBom(); }, [fetchBom]);

  // Search for items to add as components
  const handleSearch = useCallback(async (q: string) => {
    setSearchQuery(q);
    if (q.length < 2) { setSearchResults([]); return; }
    setSearching(true);
    try {
      const res = await searchItems(q);
      const items = res?.results || res || [];
      // Filter out self and already-added components
      const existingChildIds = new Set(components.map((c: any) => c.child_item_id || c.child_item));
      const filtered = items.filter((item: any) => {
        const id = item.id || item.item_id;
        return id !== itemId && !existingChildIds.has(id);
      });
      setSearchResults(filtered.slice(0, 10));
    } catch { setSearchResults([]); }
    setSearching(false);
  }, [itemId, components]);

  // Add a component
  const handleAddComponent = useCallback(async (item: any) => {
    setAdding(true);
    try {
      const childId = item.id || item.item_id;
      const childCode = item.ida_item || item.item_num || item.sku || '';
      const childDesc = item.description || item.name || '';
      await saveRecord('bill_of_material', {
        parent_item_id: itemId,
        parent_ida: itemCode,
        child_item_id: childId,
        child_ida: childCode,
        child_description: childDesc,
        quantity: 1,
        sequence: (components.length + 1) * 10,
      });
      dispatch(showToast({ message: `Added ${childCode || childId} to BOM`, type: 'success' }));
      setShowSearch(false);
      setSearchQuery('');
      setSearchResults([]);
      fetchBom();
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.response?.data?.message || 'Failed to add component';
      dispatch(showToast({ message: msg, type: 'error' }));
    }
    setAdding(false);
  }, [itemId, itemCode, components.length, dispatch, fetchBom]);

  const handleBuild = useCallback(async () => {
    const qty = parseFloat(buildQty);
    if (!qty || qty <= 0) {
      dispatch(showToast({ message: 'Enter a valid quantity', type: 'error' }));
      return;
    }
    setBuilding(true);
    try {
      const res = await apiClient.post(`/api/products/items/${itemId}/bom/consume/`, {
        qty,
        adjust_for_on_hand: false,
        reason: buildReason || `Build ${qty} × ${itemCode}`,
      });
      const data = res.data?.data || res.data;
      const applied = data?.applied ?? data?.movements ?? '?';
      dispatch(showToast({
        message: `Built ${qty} × ${itemCode} — ${applied} inventory movements posted`,
        type: 'success',
      }));
      setShowBuild(false);
      setBuildQty('1');
      setBuildReason('');
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.response?.data?.message || e?.response?.data?.error || 'Build failed';
      dispatch(showToast({ message: msg, type: 'error' }));
    }
    setBuilding(false);
  }, [itemId, itemCode, buildQty, buildReason, dispatch]);

  return (
    <div className="p-2">
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-bold text-slate-600 dark:text-slate-300">
          Components of {itemCode}
        </span>
        <span className="text-[9px] text-slate-400">({components.length})</span>
        <span className="flex-1" />
        {components.length > 0 && (
          <button
            onClick={() => { setShowBuild(!showBuild); setShowSearch(false); }}
            className="text-[9px] text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-medium mr-2"
          >
            {showBuild ? '× cancel' : 'Build from BOM'}
          </button>
        )}
        <button
          onClick={() => { setShowSearch(!showSearch); setShowBuild(false); }}
          className="text-[9px] text-green-600 hover:text-green-800 dark:text-green-400 dark:hover:text-green-300 font-medium"
        >
          {showSearch ? '× cancel' : '+ add component'}
        </button>
      </div>

      {/* Build from BOM */}
      {showBuild && (
        <div className="mb-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="text-xs font-medium text-slate-700 dark:text-slate-300 mb-2">
            Build {itemCode} — increments parent, decrements all children
          </div>
          <div className="flex items-end gap-3">
            <div>
              <label className="text-[10px] text-slate-500 dark:text-slate-400">Quantity to build</label>
              <input
                type="number"
                step="1"
                min="1"
                value={buildQty}
                onChange={(e) => setBuildQty(e.target.value)}
                autoFocus
                className="w-24 px-2 py-1.5 text-xs rounded border border-blue-300 dark:border-blue-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
              />
            </div>
            <div className="flex-1">
              <label className="text-[10px] text-slate-500 dark:text-slate-400">Reason (optional)</label>
              <input
                type="text"
                value={buildReason}
                onChange={(e) => setBuildReason(e.target.value)}
                placeholder="Production run, work order #, etc."
                className="w-full px-2 py-1.5 text-xs rounded border border-blue-300 dark:border-blue-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
              />
            </div>
            <button
              onClick={handleBuild}
              disabled={building || !buildQty || parseFloat(buildQty) <= 0}
              className="px-3 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded disabled:opacity-50"
            >
              {building ? 'Building...' : `Build ${buildQty || 0}`}
            </button>
          </div>
        </div>
      )}

      {/* Add component search */}
      {showSearch && (
        <div className="mb-3 p-2 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Search items by code or description..."
            autoFocus
            className="w-full px-2 py-1.5 text-xs rounded border border-green-300 dark:border-green-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-1 focus:ring-green-500"
          />
          {searching && <div className="text-[10px] text-slate-400 mt-1">Searching...</div>}
          {searchResults.length > 0 && (
            <div className="mt-1 max-h-40 overflow-y-auto">
              {searchResults.map((item: any) => {
                const code = item.ida_item || item.item_num || item.sku || '';
                const desc = item.description || item.name || '';
                return (
                  <button
                    key={item.id || item.item_id}
                    onClick={() => handleAddComponent(item)}
                    disabled={adding}
                    className="w-full flex items-center gap-2 px-2 py-1 text-xs text-left hover:bg-green-100 dark:hover:bg-green-800/30 rounded"
                  >
                    <span className="font-mono text-slate-700 dark:text-slate-200 w-28 truncate">{code}</span>
                    <span className="text-slate-500 dark:text-slate-400 flex-1 truncate">{desc}</span>
                    <span className="text-green-600 dark:text-green-400 text-[9px] font-medium">+ add</span>
                  </button>
                );
              })}
            </div>
          )}
          {searchQuery.length >= 2 && !searching && searchResults.length === 0 && (
            <div className="text-[10px] text-slate-400 mt-1">No items found</div>
          )}
        </div>
      )}

      {/* Column headers */}
      <div className="flex items-center gap-2 px-2 py-1 text-[10px] font-medium text-slate-400 border-b-2 border-slate-200 dark:border-slate-700">
        <span className="w-8 text-center">#</span>
        <span className="w-28">Item</span>
        <span className="flex-1">Description</span>
        <span className="w-16 text-right">Qty</span>
        <span className="w-16 text-right">Scrap%</span>
        <span className="w-8">UOM</span>
        <span className="w-12 text-center">Opt</span>
        <span className="w-20"></span>
      </div>

      {/* Component list */}
      {loading ? (
        <div className="text-xs text-slate-400 py-4 text-center">Loading...</div>
      ) : components.length === 0 ? (
        <div className="text-xs text-slate-400 italic py-4 text-center">
          No BOM components — click "+ add component" to build the bill of materials
        </div>
      ) : (
        components.map((c: any) => (
          <BomCard
            key={c.id}
            data={c}
            parentItemId={itemId}
            selected={selectedId === c.id}
            onSave={() => fetchBom()}
            onDelete={() => fetchBom()}
            onSelect={(id) => setSelectedId(id === selectedId ? null : id)}
            onOpen={(childId) => {
              if (childId) window.open(`/item?id=${childId}`, '_blank');
            }}
          />
        ))
      )}
    </div>
  );
};

export default BomPanel;

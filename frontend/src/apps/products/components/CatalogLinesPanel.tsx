/* LastChecked: 2026-10-22 | WhereUsed: Catalog detail, "lines" panel | WhoCreated: Claude */
/**
 * CatalogLinesPanel — a catalog's price rules, edited on the catalog's page.
 *
 * A line prices one item, or the items its scope covers (all items, categories,
 * vendors) — never neither (Bill, 2026-10-22; the door refuses it). Each line is its own
 * record through the door: `new` under the catalog, then a save with the item or scope,
 * edits as saves, removal as a delete. The resolver reads them:
 * backend/apps/products/services/price_resolver.py → _catalog_line.
 */
import React, { useState, useEffect, useMemo } from 'react';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';
import { createRecord, saveRecord, deleteRecord, searchItems } from '@/api/wcapi';
import { usePanelRecords } from '@/hooks/usePanelRecords';
import { usePanelFrame, PanelLabels } from '@/apps/common/components/CollapsiblePanel';

export interface CatalogLinesPanelProps {
  catalogId: number;
}

const ADJUSTMENTS = [
  { value: 'percent_off', label: '% off' },
  { value: 'amount_off', label: 'amount off' },
  { value: 'fixed_price', label: 'fixed price' },
];

const errMsg = (e: any, fallback: string) =>
  e?.response?.data?.detail || e?.response?.data?.message || e?.response?.data?.error || fallback;

/** What a line covers, in words. */
function covers(line: any): string {
  if (line.item) return line.item_ida || `item #${line.item}`;
  const scope = line.scope || {};
  const parts: string[] = [];
  if (scope.all_items) parts.push('all items');
  if (scope.categories?.length) parts.push(`categories: ${scope.categories.join(', ')}`);
  if (scope.vendors?.length) parts.push(`vendors: ${scope.vendors.join(', ')}`);
  return parts.join(' · ') || '(nothing)';
}

const num = (v: string) => (v.trim() === '' ? null : Number(v));

const CatalogLineRow: React.FC<{ line: any; onChanged: () => void }> = ({ line, onChanged }) => {
  const dispatch = useDispatch();
  const [draft, setDraft] = useState<any>(line);
  useEffect(() => { setDraft(line); }, [line]);

  const save = async (patch: Record<string, any>) => {
    try {
      await saveRecord('catalog_line', { id: line.id, version: line.version, ...patch });
      onChanged();
    } catch (e: any) {
      dispatch(showToast({ message: errMsg(e, 'Catalog line not saved'), type: 'error' }));
      setDraft(line);
    }
  };

  const remove = async () => {
    try {
      await deleteRecord('catalog_line', line.id);
      onChanged();
    } catch (e: any) {
      dispatch(showToast({ message: errMsg(e, 'Catalog line not removed'), type: 'error' }));
    }
  };

  const field = (key: string, width: string) => (
    <input
      type="number"
      value={draft[key] ?? ''}
      onChange={(e) => setDraft({ ...draft, [key]: e.target.value })}
      onBlur={(e) => {
        if (String(line[key] ?? '') !== e.target.value) save({ [key]: num(e.target.value) });
      }}
      className={`${width} px-1 py-0.5 text-xs text-right rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white`}
    />
  );

  return (
    <div className="flex items-center gap-2 px-2 py-1 text-xs border-b border-slate-100 dark:border-slate-800">
      <span className="flex-1 truncate text-slate-700 dark:text-slate-200" title={line.item ? 'item line' : 'scope line'}>
        {covers(line)}
      </span>
      <select
        value={draft.adjustment_type || 'percent_off'}
        onChange={(e) => save({ adjustment_type: e.target.value })}
        className="w-24 px-1 py-0.5 text-xs rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
      >
        {ADJUSTMENTS.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
      </select>
      {field('adjustment_value', 'w-20')}
      {field('price_unit', 'w-20')}
      {field('min_qty', 'w-16')}
      {field('max_qty', 'w-16')}
      <button onClick={remove} className="w-12 text-[9px] text-red-600 hover:text-red-800 dark:text-red-400">
        remove
      </button>
    </div>
  );
};

const CatalogLinesPanel: React.FC<CatalogLinesPanelProps> = ({ catalogId }) => {
  const dispatch = useDispatch();
  const [adding, setAdding] = useState<'' | 'item' | 'scope'>('');
  const [query, setQuery] = useState('');
  const [found, setFound] = useState<any[]>([]);
  const [scope, setScope] = useState({ all_items: false, categories: '', vendors: '' });

  const { records, refresh: fetchLines, status } = usePanelRecords('catalog_line',
    { catalog_id: catalogId, limit: 500 },
    { emptyText: 'No lines — a catalog prices nothing until it has a line or a universal %' });
  // Item lines first, as the resolver tries them first.
  const lines = useMemo(() => [...records].sort((a: any, b: any) =>
    (a.item ? 0 : 1) - (b.item ? 0 : 1) || a.id - b.id), [records]);

  const add = async (values: Record<string, any>) => {
    try {
      // A line cannot exist without its catalog: that goes to `new`; the rest is its save.
      await createRecord('catalog_line', values, { catalog_id: catalogId });
      setAdding(''); setQuery(''); setFound([]);
      setScope({ all_items: false, categories: '', vendors: '' });
    } catch (e: any) {
      dispatch(showToast({ message: errMsg(e, 'Catalog line not added'), type: 'error' }));
    }
    fetchLines();
  };

  const search = async (q: string) => {
    setQuery(q);
    if (q.length < 2) { setFound([]); return; }
    try {
      const res: any = await searchItems(q, { limit: 10 });
      setFound(res?.results || res || []);
    } catch { setFound([]); }
  };

  const addScope = () => {
    const list = (s: string) => s.split(',').map(x => x.trim()).filter(Boolean);
    add({
      scope: {
        all_items: scope.all_items,
        categories: list(scope.categories),
        vendors: list(scope.vendors).map(Number).filter(n => Number.isInteger(n) && n > 0),
      },
    });
  };

  const input = 'px-2 py-1 text-xs rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white';

  const headerActions = useMemo(() => (
    <>
      <button onClick={() => setAdding(a => (a === 'item' ? '' : 'item'))}
        className="text-[9px] text-green-600 hover:text-green-800 dark:text-green-400 font-medium">
        {adding === 'item' ? '× cancel' : '+ item line'}
      </button>
      <button onClick={() => setAdding(a => (a === 'scope' ? '' : 'scope'))}
        className="text-[9px] text-green-600 hover:text-green-800 dark:text-green-400 font-medium">
        {adding === 'scope' ? '× cancel' : '+ scope line'}
      </button>
    </>
  ), [adding]);
  usePanelFrame({ badge: lines.length, headerActions, status });

  return (
    <div className="p-2">
      {adding === 'item' && (
        <div className="mb-2 p-2 rounded border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20">
          <input autoFocus value={query} onChange={(e) => search(e.target.value)}
            placeholder="Search items by code or description..." className={`w-full ${input}`} />
          {found.map((item: any) => (
            <button key={item.id} onClick={() => add({ item_id: item.id })}
              className="w-full flex gap-2 px-2 py-1 text-xs text-left hover:bg-green-100 dark:hover:bg-green-800/30 rounded">
              <span className="font-mono w-28 truncate text-slate-700 dark:text-slate-200">{item.ida || item.sku}</span>
              <span className="flex-1 truncate text-slate-500 dark:text-slate-400">{item.name || item.description}</span>
            </button>
          ))}
        </div>
      )}

      {adding === 'scope' && (
        <div className="mb-2 p-2 rounded border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 flex flex-wrap items-center gap-2">
          <label className="text-xs text-slate-600 dark:text-slate-300 flex items-center gap-1">
            <input type="checkbox" checked={scope.all_items}
              onChange={(e) => setScope({ ...scope, all_items: e.target.checked })} />
            all items
          </label>
          <input value={scope.categories} onChange={(e) => setScope({ ...scope, categories: e.target.value })}
            placeholder="categories, comma separated" className={`flex-1 ${input}`} />
          <input value={scope.vendors} onChange={(e) => setScope({ ...scope, vendors: e.target.value })}
            placeholder="vendor ids, comma separated" className={`w-48 ${input}`} />
          <button onClick={addScope} className="px-2 py-1 text-xs font-medium text-white bg-green-600 hover:bg-green-700 rounded">
            add
          </button>
        </div>
      )}

      {lines.length > 0 && (
        <PanelLabels>
          <span className="flex-1">Covers</span>
          <span className="w-24">Adjustment</span>
          <span className="w-20 text-right">Value</span>
          <span className="w-20 text-right">Price unit</span>
          <span className="w-16 text-right">Min qty</span>
          <span className="w-16 text-right">Max qty</span>
          <span className="w-12" />
        </PanelLabels>
      )}
      {lines.map((line: any) => <CatalogLineRow key={line.id} line={line} onChanged={fetchLines} />)}
    </div>
  );
};

export default CatalogLinesPanel;

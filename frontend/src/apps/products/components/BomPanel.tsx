/* LastChecked: 2026-11-01 | WhereUsed: panelRegistry `bom` (item form) | WhoCreated: Claude */
/**
 * BomPanel — an item's bill of materials, one panel with two views (Bill, 2026-11-01):
 *
 *   lines   the BOM lines whose parent_item_id is the item, on the shared list
 *           (LinkedRecordsPanel); "+ add" picks the component item; a line opens in its card.
 *   costed  the whole tree from the server (bom/expand, depth-first) on TreeList: each
 *           sub-assembly's cost rolled up from its parts, the build's total, a build quantity
 *           and cost basis. Quantity and unit cost take what-if values: the server recalculates
 *           with them as you type and nothing is saved (the screen shows the server's numbers).
 *
 * Its own: "Build from BOM" — a production workorder (build line → expand one level → complete).
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useDispatch } from 'react-redux';
import { LinkedRecordsPanel } from '@/apps/common/components/panels/LinkedRecordsPanel';
import { TreeList } from '@/apps/common/components/panels/TreeList';
import type { DbColumnDef } from '@/apps/common/components/panels/DbColumns';
import { formatCell } from '@/apps/common/components/panels/cellFormat';
import { apiClient } from '@/api/axios';
import { buildItem } from '@/api/workorderApi';
import { showToast } from '@/store/slices/toastSlice';

export interface BomPanelProps {
  itemId: number;
  itemCode: string;
}

type View = 'lines' | 'costed';
type Row = Record<string, any>;
interface WhatIf { cost: Record<number, string>; quantity: Record<number, string> }

const money = (v: unknown) => formatCell(v, 'cost', { type: 'currency' });
const num = (v: unknown) => formatCell(v, 'qty', { type: 'number', precision: 2 });

/** The costed tree: the server's rollup, asked again with what-if values as they change. */
const BomCostTree: React.FC<{ itemId: number; header: React.ReactNode }> = ({ itemId, header }) => {
  const [buildQty, setBuildQty] = useState('1');
  const [basis, setBasis] = useState('avg');
  const [whatIf, setWhatIf] = useState<WhatIf>({ cost: {}, quantity: {} });
  const [data, setData] = useState<{ rows: Row[]; total_cost: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const changed = Object.keys(whatIf.cost).length + Object.keys(whatIf.quantity).length > 0;

  // Asked a moment after the last change: the server calculates, the screen shows it.
  useEffect(() => {
    const t = setTimeout(async () => {
      setLoading(true);
      const url = `/wcapi/products/items/${itemId}/bom/expand/`;
      const params = { qty: buildQty || '1', cost_basis: basis };
      const clean = (m: Record<number, string>) =>
        Object.fromEntries(Object.entries(m).filter(([, v]) => v !== '' && !isNaN(Number(v))));
      try {
        const resp = changed
          ? await apiClient.post(url, { ...params, what_if: { cost: clean(whatIf.cost), quantity: clean(whatIf.quantity) } })
          : await apiClient.get(url, { params });
        setData(resp.data?.data ?? resp.data);
        setError(null);
      } catch (e: any) {
        setError(e?.response?.data?.message || 'Could not cost the BOM');
      }
      setLoading(false);
    }, 300);
    return () => clearTimeout(t);
  }, [itemId, buildQty, basis, whatIf, changed]);

  const rows = useMemo(() => (data?.rows ?? []).map((r, i) => ({ ...r, _key: `${i}:${r.bom_id}` })), [data]);

  const edit = (kind: keyof WhatIf, key: number, shown: string) => (
    <input className="db-input" style={{ width: 70, textAlign: 'right', padding: '0 4px' }}
      value={whatIf[kind][key] ?? shown}
      onClick={(e) => e.stopPropagation()}
      onChange={(e) => setWhatIf((w) => ({ ...w, [kind]: { ...w[kind], [key]: e.target.value } }))} />
  );

  const columns: DbColumnDef<Row>[] = [
    { key: 'item_ida', label: 'item', render: (r) => r.item_ida },
    { key: 'description', label: 'description', render: (r) => r.description },
    { key: 'quantity', label: 'qty per', align: 'right', width: 80,
      render: (r) => edit('quantity', r.bom_id, String(+(r.qty_plan / (1 + (r.scrap_factor || 0))).toFixed(4))) },
    { key: 'qty_actual', label: 'qty build', align: 'right', width: 80, render: (r) => num(r.qty_actual) },
    // A part's own cost takes a what-if; a sub-assembly's is its parts', so it is not typed.
    { key: 'cost_unit', label: 'unit cost', align: 'right', width: 90,
      render: (r) => (r.is_subassembly ? money(r.cost_rollup) : edit('cost', r.item_id, String(r.cost_unit))) },
    { key: 'cost_extended', label: 'extended', align: 'right', width: 90, calculated: true, render: (r) => money(r.cost_extended) },
  ];

  return (
    <TreeList<Row>
      storageKey="panel:item:bom-costed"
      sectionLabel="Bill of materials"
      columns={columns}
      data={rows}
      rowKey={(r) => r._key}
      treeColumn="item_ida"
      level={(r) => Number(r.level ?? 1)}
      hasChildren={(r) => !!r.is_subassembly}
      compact
      loading={loading && !data}
      error={error}
      emptyMessage="No components"
      extraActions={header}
    >
      <div className="px-3 py-2 flex items-center gap-3 db-font-sm" style={{ borderTop: '1px solid var(--db-border)' }}>
        <label>Build <input type="number" min="1" value={buildQty} onChange={(e) => setBuildQty(e.target.value)}
          className="db-input" style={{ width: 60 }} /></label>
        <label>cost <select value={basis} onChange={(e) => setBasis(e.target.value)} className="db-input">
          <option value="avg">average</option><option value="last">last receipt</option>
          <option value="min">min (conservative)</option><option value="landed">landed</option>
        </select></label>
        {changed && <button type="button" className="db-section-header__action"
          onClick={() => setWhatIf({ cost: {}, quantity: {} })}>clear what-if</button>}
        <span style={{ marginLeft: 'auto', fontWeight: 600 }}
          title={changed ? 'With your what-if values — nothing is saved' : 'The build at the chosen cost'}>
          {changed ? 'what-if total ' : 'total '}{money(data?.total_cost ?? 0)}
        </span>
      </div>
    </TreeList>
  );
};

const BomPanel: React.FC<BomPanelProps> = ({ itemId, itemCode }) => {
  const dispatch = useDispatch();
  const [view, setView] = useState<View>('lines');
  const [showBuild, setShowBuild] = useState(false);
  const [buildQty, setBuildQty] = useState('1');
  const [building, setBuilding] = useState(false);

  const handleBuild = useCallback(async () => {
    const qty = parseFloat(buildQty);
    if (!qty || qty <= 0) {
      dispatch(showToast({ message: 'Enter a valid quantity', type: 'error' }));
      return;
    }
    setBuilding(true);
    try {
      const done: any = await buildItem(itemId, qty, 1);
      dispatch(showToast({
        message: `Built ${qty} × ${itemCode} on workorder ${done.workorder_id} (${done.lines_applied ?? '?'} lines applied)`,
        type: 'success',
      }));
      setShowBuild(false);
      setBuildQty('1');
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.response?.data?.message || e?.response?.data?.error || 'Build failed';
      dispatch(showToast({ message: msg, type: 'error' }));
    }
    setBuilding(false);
  }, [itemId, itemCode, buildQty, dispatch]);

  const switcher = (
    <button type="button" className="db-section-header__action"
      title={view === 'lines' ? 'The whole tree with costs rolled up' : 'The lines, to change'}
      onClick={(e) => { e.stopPropagation(); setView((v) => (v === 'lines' ? 'costed' : 'lines')); }}>
      {view === 'lines' ? 'costed' : 'lines'}
    </button>
  );

  if (view === 'costed') return <BomCostTree itemId={itemId} header={switcher} />;

  return (
    <LinkedRecordsPanel
      linkedModel="bill_of_material" parentModel="item" parentId={itemId} byField="parent_item_id"
      title="Bill of materials" defaultCollapsed={false}
      pick={{
        model: 'item', field: 'child_item_id',
        values: (item, rows) => ({
          parent_ida: itemCode,
          child_ida: item.ida_item || item.ida || item.sku || '',
          child_description: item.description || item.name || '',
          sequence: (rows.length + 1) * 10,
        }),
      }}
      extraActions={
        <>
          {switcher}
          <button type="button" className="db-section-header__action"
            onClick={(e) => { e.stopPropagation(); setShowBuild(v => !v); }}>
            {showBuild ? '× cancel' : 'Build from BOM'}
          </button>
        </>
      }
    >
      {showBuild && (
        <div className="px-3 py-2 flex items-end gap-3" style={{ borderTop: '1px solid var(--db-border)' }}>
          <div>
            <label className="db-font-xs db-text-dim block">Build {itemCode}: quantity</label>
            <input type="number" step="1" min="1" value={buildQty} autoFocus
              onChange={(e) => setBuildQty(e.target.value)} className="db-input w-24" />
          </div>
          <button type="button" onClick={handleBuild} disabled={building || !(parseFloat(buildQty) > 0)}
            className="db-section-header__action">
            {building ? 'Building…' : `Build ${buildQty || 0}`}
          </button>
        </div>
      )}
    </LinkedRecordsPanel>
  );
};

export default BomPanel;

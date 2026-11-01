/* LastChecked: 2026-08-14 | WhereUsed: DataBrowser detail pane (item model) | WhoCreated: Bill+Claude */
import React, { useCallback, useEffect, useState } from 'react';
import { apiClient } from '../../api/axios';
import { TreeList } from '@/apps/common/components/panels/TreeList';
import { buildColumnsFromSpecs } from '@/apps/common/components/panels/panelColumnUtils';

// ---------------------------------------------------------------------------
// BOM Panel — shows when viewing an Item with BOM children
// ---------------------------------------------------------------------------

const BOM_COLUMNS = buildColumnsFromSpecs([
  { field: 'item_ida' }, { field: 'description' },
  { field: 'qty_plan', format: 'number' }, { field: 'qty_actual', format: 'number' },
  { field: 'cost_avg', format: 'currency' }, { field: 'cost_last', format: 'currency' },
  { field: 'cost_extended', format: 'currency' },
]);

export const BOMPanel: React.FC<{ itemId: number }> = ({ itemId }) => {
  const [bomData, setBomData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [costBasis, setCostBasis] = useState('avg');
  const [buildQty, setBuildQty] = useState('1');

  const fetchBom = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await apiClient.get(`/wcapi/products/items/${itemId}/bom/expand/`, {
        params: { qty: buildQty, cost_basis: costBasis },
      });
      setBomData(resp.data?.data || resp.data);
    } catch { setBomData(null); }
    setLoading(false);
  }, [itemId, costBasis, buildQty]);

  useEffect(() => { fetchBom(); }, [fetchBom]);

  if (loading) return <div className="db-status-msg">Loading BOM...</div>;
  if (!bomData?.rows?.length) return null; // No BOM — hide panel
  // Each row's place in the tree is its key: the same item can sit under two parents.
  const rows = bomData.rows.map((r: any, i: number) => ({ ...r, _key: `${i}:${r.item_id}` }));

  return (
    <div className="db-bom-panel">
      <div className="db-bom-header">
        <span className="db-bom-title">Bill of Materials</span>
        <label className="db-bom-control">
          Qty: <input type="number" min="1" value={buildQty}
            onChange={(e) => setBuildQty(e.target.value)} className="db-bom-input" />
        </label>
        <label className="db-bom-control">
          Cost:
          <select value={costBasis} onChange={(e) => setCostBasis(e.target.value)} className="db-bom-input">
            <option value="avg">Average</option>
            <option value="last">Last Receipt</option>
            <option value="min">Min (conservative)</option>
            <option value="landed">Landed</option>
          </select>
        </label>
        <span className="db-bom-total">Total: ${(bomData.total_cost || 0).toFixed(2)}</span>
        <button className="db-btn db-btn--small db-btn--ghost" onClick={() => {
          window.open(`/bill_of_material?parent_id=${itemId}`, '_blank');
        }}>Open BOM ↗</button>
      </div>
      <TreeList<any>
        storageKey="panel:item:bom-tree"
        columns={BOM_COLUMNS}
        data={rows}
        rowKey={(r) => r._key}
        treeColumn="item_ida"
        level={(r) => Number(r.level ?? 1)}
        hasChildren={(r) => !!r.is_subassembly}
        compact
        onOpenRow={(row) => { if (row?.item_id) window.open(`/item?id=${row.item_id}`, '_blank'); }}
      />
    </div>
  );
};

export default BOMPanel;

/* LastChecked: 2026-08-14 | WhereUsed: DataBrowser detail pane (item model) | WhoCreated: Bill+Claude */
import React, { useCallback, useEffect, useState } from 'react';
import { apiClient } from '../../api/axios';
import DataGrid from '../../components/common/DataGrid';

// ---------------------------------------------------------------------------
// BOM Panel — shows when viewing an Item with BOM children
// ---------------------------------------------------------------------------

const BOM_COLUMNS = ['item_ida', 'description', 'qty_plan', 'qty_actual', 'cost_avg', 'cost_last', 'cost_extended'];

export const BOMPanel: React.FC<{ itemId: number; theme: any; fontSize: number }> = ({ itemId, theme, fontSize }) => {
  const [bomData, setBomData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [costBasis, setCostBasis] = useState('avg');
  const [buildQty, setBuildQty] = useState('1');

  const fetchBom = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await apiClient.get(`/products/items/${itemId}/bom/expand/`, {
        params: { qty: buildQty, cost_basis: costBasis },
      });
      setBomData(resp.data?.data || resp.data);
    } catch { setBomData(null); }
    setLoading(false);
  }, [itemId, costBasis, buildQty]);

  useEffect(() => { fetchBom(); }, [fetchBom]);

  if (loading) return <div className="db-status-msg">Loading BOM...</div>;
  if (!bomData?.rows?.length) return null; // No BOM — hide panel

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
      <DataGrid
        records={bomData.rows}
        columns={BOM_COLUMNS}
        treeColumn="item_ida"
        levelField="level"
        childFlag="is_subassembly"
        theme={theme}
        fontSize={fontSize - 1}
        hideToolbar
        numId={(v: unknown) => typeof v === 'number' ? v : null}
        onRowDoubleClicked={(row: any) => {
          if (row?.is_subassembly && row?.item_id) {
            window.open(`/item?id=${row.item_id}`, '_blank');
          }
        }}
      />
    </div>
  );
};

export default BOMPanel;

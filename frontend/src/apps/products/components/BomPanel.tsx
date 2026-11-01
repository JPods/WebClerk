/* LastChecked: 2026-10-31 | WhereUsed: panelRegistry `bom` (item form) | WhoCreated: Claude */
/**
 * BomPanel — an item's bill of materials on the shared list (LinkedRecordsPanel): the BOM lines
 * whose parent_item_id is the item, by sequence. "+ add" picks the component item and makes the
 * line with both items at once (a line cannot exist without them); a line opens in its card.
 * Its own: "Build from BOM" — a production workorder (build line → expand one level →
 * complete). Backend handles cycle detection and cost rollup.
 */
import React, { useCallback, useState } from 'react';
import { useDispatch } from 'react-redux';
import { LinkedRecordsPanel } from '@/apps/common/components/panels/LinkedRecordsPanel';
import { buildItem } from '@/api/workorderApi';
import { showToast } from '@/store/slices/toastSlice';

export interface BomPanelProps {
  itemId: number;
  itemCode: string;
}

type Rec = Record<string, any>;
const bySequence = (a: Rec, b: Rec) => (a.sequence || 0) - (b.sequence || 0) || (a.id || 0) - (b.id || 0);

const BomPanel: React.FC<BomPanelProps> = ({ itemId, itemCode }) => {
  const dispatch = useDispatch();
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

  return (
    <LinkedRecordsPanel
      linkedModel="bill_of_material" parentModel="item" parentId={itemId} byField="parent_item_id"
      title="Bill of materials" defaultCollapsed={false} sort={bySequence}
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
        <button type="button" className="db-section-header__action"
          onClick={(e) => { e.stopPropagation(); setShowBuild(v => !v); }}>
          {showBuild ? '× cancel' : 'Build from BOM'}
        </button>
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

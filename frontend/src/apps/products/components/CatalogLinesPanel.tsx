/* LastChecked: 2026-10-31 | WhereUsed: panelRegistry `catalog_lines` (catalog form) | WhoCreated: Claude */
/**
 * CatalogLinesPanel — a catalog's price rules on the shared list (LinkedRecordsPanel): the lines
 * whose catalog_id is the catalog, item lines first as the resolver tries them first. A line
 * prices one item, or the items its scope covers (all items, categories, vendors) — never
 * neither (Bill, 2026-10-22; the door refuses it). "+ add" picks the item; a line opens in its
 * card. Its own: "+ scope line", a line made with a scope instead of an item. The resolver reads
 * them: backend/apps/products/services/price_resolver.py → _catalog_line.
 */
import React, { useState } from 'react';
import { useDispatch } from 'react-redux';
import { LinkedRecordsPanel } from '@/apps/common/components/panels/LinkedRecordsPanel';
import { createRecord } from '@/api/wcapi';
import { showToast } from '@/store/slices/toastSlice';

export interface CatalogLinesPanelProps {
  catalogId: number;
}

type Rec = Record<string, any>;
const itemLinesFirst = (a: Rec, b: Rec) => (a.item ? 0 : 1) - (b.item ? 0 : 1) || a.id - b.id;
const list = (s: string) => s.split(',').map(x => x.trim()).filter(Boolean);

const CatalogLinesPanel: React.FC<CatalogLinesPanelProps> = ({ catalogId }) => {
  const dispatch = useDispatch();
  const [open, setOpen] = useState(false);
  const [scope, setScope] = useState({ all_items: false, categories: '', vendors: '' });

  const addScope = async () => {
    try {
      // A line cannot exist without its catalog: that goes to `new`; the scope is its save.
      await createRecord('catalog_line', {
        scope: {
          all_items: scope.all_items,
          categories: list(scope.categories),
          vendors: list(scope.vendors).map(Number).filter(n => Number.isInteger(n) && n > 0),
        },
      }, { catalog_id: catalogId });
      setOpen(false);
      setScope({ all_items: false, categories: '', vendors: '' });
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.response?.data?.message || e?.message || 'Catalog line not added';
      dispatch(showToast({ message: msg, type: 'error' }));
    }
  };

  return (
    <LinkedRecordsPanel
      linkedModel="catalog_line" parentModel="catalog" parentId={catalogId} byField="catalog_id"
      title="Lines" defaultCollapsed={false} sort={itemLinesFirst}
      pick={{ model: 'item', field: 'item_id' }}
      extraActions={
        <button type="button" className="db-section-header__action"
          onClick={(e) => { e.stopPropagation(); setOpen(v => !v); }}>
          {open ? '× cancel' : '+ scope line'}
        </button>
      }
    >
      {open && (
        <div className="px-3 py-2 flex flex-wrap items-center gap-2" style={{ borderTop: '1px solid var(--db-border)' }}>
          <label className="db-font-xs flex items-center gap-1">
            <input type="checkbox" checked={scope.all_items}
              onChange={(e) => setScope({ ...scope, all_items: e.target.checked })} />
            all items
          </label>
          <input value={scope.categories} onChange={(e) => setScope({ ...scope, categories: e.target.value })}
            placeholder="categories, comma separated" className="db-input flex-1" />
          <input value={scope.vendors} onChange={(e) => setScope({ ...scope, vendors: e.target.value })}
            placeholder="vendor ids, comma separated" className="db-input w-48" />
          <button type="button" onClick={addScope} className="db-section-header__action">add</button>
        </div>
      )}
    </LinkedRecordsPanel>
  );
};

export default CatalogLinesPanel;

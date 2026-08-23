/* LastChecked: 2026-08-13 | WhereUsed: LinesCard | WhoCreated: Claude */
// Inventory peek panel — "L" button in WC2.
// Shows inventory for selected (or all) line items in a compact table below the grid.
import React from 'react';
import { getRecords } from '@/api/wcapi';
import { formatCurrency } from '@/utils/stringUtils';

interface InventoryPanelProps {
  /** Item IDs to show inventory for */
  itemIds: number[];
  /** Item codes for display (parallel array) */
  itemCodes: string[];
}

interface InventoryRow {
  id: number;
  ida: string;
  name: string;
  available: number | null;
  on_hand: number | null;
  on_so: number | null;
  on_po: number | null;
  lead_time: number | null;
  price_retail: number | null;
}

const formatNum = (v: number | null | undefined): string =>
  v == null ? '—' : v.toLocaleString();


const InventoryPanel: React.FC<InventoryPanelProps> = ({ itemIds }) => {
  const [rows, setRows] = React.useState<InventoryRow[]>([]);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    if (!itemIds.length) { setRows([]); return; }

    let cancelled = false;
    setLoading(true);

    // Fetch inventory via bulk endpoint or fallback to individual item queries
    const fetchInventory = async () => {
      try {
        // Try bulk endpoint first
        const resp = await fetch(`/wcapi/products/items/inventory/?ids=${itemIds.join(',')}`, {
          credentials: 'include',
        });
        if (resp.ok) {
          const json = await resp.json();
          if (!cancelled) setRows(json.data || []);
        } else {
          // Fallback: fetch each item individually via wcapi
          const results: InventoryRow[] = [];
          for (const id of itemIds.slice(0, 50)) { // cap at 50
            try {
              const res = await getRecords('item', { id, limit: 1 });
              const item = res?.records?.[0];
              if (item) {
                const qty = item.quantity || {};
                results.push({
                  id: item.id,
                  ida: item.ida || '',
                  name: item.name || '',
                  available: qty.available ?? null,
                  on_hand: qty.on_hand ?? null,
                  on_so: qty.on_so ?? null,
                  on_po: qty.on_po ?? null,
                  lead_time: item.config?.lead_time ?? null,
                  price_retail: item.price?.retail ?? null,
                });
              }
            } catch { /* skip failed items */ }
          }
          if (!cancelled) setRows(results);
        }
      } catch {
        if (!cancelled) setRows([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchInventory();
    return () => { cancelled = true; };
  }, [itemIds.join(',')]);

  if (loading) {
    return (
      <div className="px-3 py-2 text-xs" style={{ color: 'var(--db-text-muted)' }}>
        Loading inventory…
      </div>
    );
  }

  if (!rows.length) {
    return (
      <div className="px-3 py-2 text-xs" style={{ color: 'var(--db-text-dim)' }}>
        No inventory data available
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr style={{ background: 'var(--db-surface-alt)', color: 'var(--db-text-muted)' }}>
            <th className="text-left px-2 py-1 font-medium">Item</th>
            <th className="text-left px-2 py-1 font-medium">Description</th>
            <th className="text-right px-2 py-1 font-medium">Available</th>
            <th className="text-right px-2 py-1 font-medium">On S/O</th>
            <th className="text-right px-2 py-1 font-medium">On P/O</th>
            <th className="text-right px-2 py-1 font-medium">Lead</th>
            <th className="text-right px-2 py-1 font-medium">Price</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr
              key={r.id}
              style={{ borderBottom: '1px solid var(--db-border)' }}
            >
              <td className="px-2 py-1 font-mono">{r.ida}</td>
              <td className="px-2 py-1 max-w-[200px] truncate" style={{ color: 'var(--db-text-muted)' }}>{r.name}</td>
              <td className="px-2 py-1 text-right font-medium">{formatNum(r.available)}</td>
              <td className="px-2 py-1 text-right" style={{ color: 'var(--db-accent-gold)' }}>{formatNum(r.on_so)}</td>
              <td className="px-2 py-1 text-right" style={{ color: 'var(--db-accent)' }}>{formatNum(r.on_po)}</td>
              <td className="px-2 py-1 text-right">{r.lead_time != null ? `${r.lead_time}d` : '—'}</td>
              <td className="px-2 py-1 text-right">{formatCurrency(r.price_retail)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default InventoryPanel;

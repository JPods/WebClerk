/* LastChecked: 2026-10-27 | WhereUsed: LineCardRenderer | WhoCreated: Claude */
// Inventory peek panel — "L" button in WC2.
// Shows inventory for selected (or all) line items in a compact table below the grid. The
// line card's panel frame draws the label, count and status.
import { getItemsInventory } from '@/api/workorderApi';
import { usePanelRecords } from '@/hooks/usePanelRecords';
import { usePanelFrame } from '@/apps/common/components/CollapsiblePanel';
import { formatCurrency } from '@/utils/stringUtils';

interface InventoryPanelProps {
  /** Item IDs to show inventory for */
  itemIds: number[];
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


const InventoryPanel = ({ itemIds }: InventoryPanelProps) => {
  const { records: rows, status } = usePanelRecords<InventoryRow>('item inventory', { ids: itemIds.join(',') },
    { enabled: itemIds.length > 0, read: getItemsInventory, emptyText: 'No inventory data available' });
  usePanelFrame({ badge: rows.length, status });
  if (!rows.length) return null;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs border-collapse">
        <thead className="sticky top-0">
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

/* LastChecked: 2026-10-27 | WhereUsed: LineCardRenderer | WhoCreated: Claude */
// Inventory peek panel — "L" button in WC2.
// Shows inventory for selected (or all) line items in a compact table below the grid. The
// line card's panel frame draws the label, count and status.
import { getItemsInventory } from '@/api/workorderApi';
import { usePanelRecords } from '@/hooks/usePanelRecords';
import { usePanelFrame } from '@/apps/common/components/CollapsiblePanel';
import { formatCurrency } from '@/utils/stringUtils';
import { DbColumns, type DbColumnDef } from '@/apps/common/components/panels/DbColumns';
import { usePanelOpen } from '@/hooks/usePanelAdd';

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


// The shared list's columns (DbColumns): one row per item; a row opens the item.
const COLUMNS: DbColumnDef<InventoryRow>[] = [
  { key: 'ida', label: 'item', width: '120px', className: 'font-mono', render: (r) => r.ida },
  { key: 'name', label: 'description', render: (r) => <span style={{ color: 'var(--db-text-muted)' }}>{r.name}</span> },
  { key: 'available', label: 'available', width: '80px', className: 'text-right font-medium', render: (r) => formatNum(r.available) },
  { key: 'on_so', label: 'on s/o', width: '70px', className: 'text-right', render: (r) => <span style={{ color: 'var(--db-accent-gold)' }}>{formatNum(r.on_so)}</span> },
  { key: 'on_po', label: 'on p/o', width: '70px', className: 'text-right', render: (r) => <span style={{ color: 'var(--db-accent)' }}>{formatNum(r.on_po)}</span> },
  { key: 'lead_time', label: 'lead', width: '60px', className: 'text-right', render: (r) => r.lead_time != null ? `${r.lead_time}d` : '—' },
  { key: 'price_retail', label: 'price', width: '90px', className: 'text-right', render: (r) => formatCurrency(r.price_retail) },
];

const InventoryPanel = ({ itemIds }: InventoryPanelProps) => {
  const { records: rows, status } = usePanelRecords<InventoryRow>('item inventory', { ids: itemIds.join(',') },
    { enabled: itemIds.length > 0, read: getItemsInventory, emptyText: 'No inventory data available' });
  usePanelFrame({ badge: rows.length, status });
  const opener = usePanelOpen('item');
  if (!rows.length) return null;

  return (
    <DbColumns<InventoryRow>
      storageKey="panel:lines:inventory"
      columns={COLUMNS}
      data={rows}
      rowKey={(r) => r.id}
      onOpenRow={(r, el) => opener.open(r.id, r.ida, el)}
      onOpenWindow={(r) => opener.openWindow(r.id)}
      onMoveRow={(r, el) => opener.move(r.id, r.ida, el)}
      openKey={opener.openId}
      compact
    >
      {opener.recordCard}
    </DbColumns>
  );
};

export default InventoryPanel;

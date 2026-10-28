/* LastChecked: 2026-10-27 | WhereUsed: LineCardRenderer | WhoCreated: Claude */
// Specification panel — "S" button in WC2.
// Shows the selected line item's spec/detail. Read-only in line context.
// Edit by opening item in floating window. The line card's panel frame draws the label and status.
import { getRecord } from '@/api/wcapi';
import { usePanelRecords } from '@/hooks/usePanelRecords';
import { usePanelFrame } from '@/apps/common/components/CollapsiblePanel';

interface SpecPanelProps {
  itemId: number;
}

/** One record has its own path (/wcapi/item/<id>/); a list read with ?id= is refused. */
const readItem = async ({ itemId }: Record<string, unknown>) => {
  const res: any = await getRecord('item', Number(itemId));
  return res?.record ? [res.record] : [];
};

const SpecPanel = ({ itemId }: SpecPanelProps) => {
  const { records, status } = usePanelRecords('item', { itemId }, { read: readItem, emptyText: 'Item not found' });
  usePanelFrame({ status });
  const item: any = records[0];
  if (!item) return null;

  const price = item.price || {};
  const cost = item.cost || {};
  const qty = item.quantity || {};
  const flags = item.flags || {};

  return (
    <div className="px-3 py-2 text-xs space-y-3">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="flex-1">
          <div className="font-mono font-bold text-sm db-text">{item.ida}</div>
          <div className="db-text-muted">{item.name}</div>
          {item.description && (
            <div className="mt-1 db-text-muted">{item.description}</div>
          )}
        </div>
        <div className="text-right db-text-muted">
          <div>UOM: {item.uom || 'EA'}</div>
          <div>Kind: {item.kind || '—'}</div>
        </div>
      </div>

      {/* Price levels */}
      <div>
        <div className="font-medium mb-1 db-text">Price Levels</div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
          {['retail', 'wholesale', 'distributor', 'sample'].map(level => (
            price[level] != null && (
              <div key={level} className="flex justify-between">
                <span className="capitalize db-text-muted">{level}</span>
                <span className="font-mono">${Number(price[level]).toFixed(2)}</span>
              </div>
            )
          ))}
          {price.msrp != null && (
            <div className="flex justify-between">
              <span className="db-text-muted">MSRP</span>
              <span className="font-mono">${Number(price.msrp).toFixed(2)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Cost */}
      <div>
        <div className="font-medium mb-1 db-text">Cost</div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
          {cost.standard != null && (
            <div className="flex justify-between">
              <span className="db-text-muted">Standard</span>
              <span className="font-mono">${Number(cost.standard).toFixed(4)}</span>
            </div>
          )}
          {cost.last != null && (
            <div className="flex justify-between">
              <span className="db-text-muted">Last</span>
              <span className="font-mono">${Number(cost.last).toFixed(4)}</span>
            </div>
          )}
          {cost.avg != null && (
            <div className="flex justify-between">
              <span className="db-text-muted">Average</span>
              <span className="font-mono">${Number(cost.avg).toFixed(4)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Inventory */}
      <div>
        <div className="font-medium mb-1 db-text">Inventory</div>
        <div className="grid grid-cols-3 gap-x-4 gap-y-0.5">
          {[
            ['On Hand', qty.on_hand],
            ['Available', qty.available],
            ['On S/O', qty.on_so],
            ['On P/O', qty.on_po],
            ['Allocated', qty.allocated],
          ].map(([label, val]) => (
            val != null && (
              <div key={label as string} className="flex justify-between">
                <span className="db-text-muted">{label}</span>
                <span className="font-mono">{Number(val).toLocaleString()}</span>
              </div>
            )
          ))}
        </div>
      </div>

      {/* Flags */}
      <div className="flex flex-wrap gap-2">
        {flags.serialized && <span className="px-1.5 py-0.5 rounded db-badge-accent">Serialized</span>}
        {flags.discountable && <span className="px-1.5 py-0.5 rounded db-badge-green">Discountable</span>}
        {flags.back_order_allowed && <span className="px-1.5 py-0.5 rounded db-badge-gold">Backorder OK</span>}
        {flags.not_tracked && <span className="px-1.5 py-0.5 rounded db-badge-muted">Not Tracked</span>}
      </div>
    </div>
  );
};

export default SpecPanel;

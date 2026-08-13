/* LastChecked: 2026-08-13 | WhereUsed: LinesCard | WhoCreated: Claude */
// Specification panel — "S" button in WC2.
// Shows the selected line item's spec/detail. Read-only in line context.
// Edit by opening item in floating window.
import React from 'react';
import { getRecords } from '@/api/wcapi';

interface SpecPanelProps {
  itemId: number | null;
  itemCode: string;
}

const SpecPanel: React.FC<SpecPanelProps> = ({ itemId, itemCode }) => {
  const [item, setItem] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    if (!itemId) { setItem(null); return; }

    let cancelled = false;
    setLoading(true);

    (async () => {
      try {
        const res = await getRecords('item', { id: itemId, limit: 1 });
        const rec = res?.records?.[0];
        if (!cancelled) setItem(rec || null);
      } catch {
        if (!cancelled) setItem(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [itemId]);

  if (!itemId) {
    return (
      <div className="px-3 py-2 text-xs" style={{ color: 'var(--db-text-dim)' }}>
        Select a line to view item specification
      </div>
    );
  }

  if (loading) {
    return (
      <div className="px-3 py-2 text-xs" style={{ color: 'var(--db-text-muted)' }}>
        Loading specification for {itemCode}…
      </div>
    );
  }

  if (!item) {
    return (
      <div className="px-3 py-2 text-xs" style={{ color: 'var(--db-text-dim)' }}>
        Item not found
      </div>
    );
  }

  const price = item.price || {};
  const cost = item.cost || {};
  const qty = item.quantity || {};
  const flags = item.flags || {};

  return (
    <div className="px-3 py-2 text-xs space-y-3">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="flex-1">
          <div className="font-mono font-bold text-sm" style={{ color: 'var(--db-text)' }}>{item.ida}</div>
          <div style={{ color: 'var(--db-text-muted)' }}>{item.name}</div>
          {item.description && (
            <div className="mt-1" style={{ color: 'var(--db-text-muted)' }}>{item.description}</div>
          )}
        </div>
        <div className="text-right" style={{ color: 'var(--db-text-muted)' }}>
          <div>UOM: {item.uom || 'EA'}</div>
          <div>Kind: {item.kind || '—'}</div>
        </div>
      </div>

      {/* Price levels */}
      <div>
        <div className="font-medium mb-1" style={{ color: 'var(--db-text)' }}>Price Levels</div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
          {['retail', 'wholesale', 'distributor', 'sample'].map(level => (
            price[level] != null && (
              <div key={level} className="flex justify-between">
                <span className="capitalize" style={{ color: 'var(--db-text-muted)' }}>{level}</span>
                <span className="font-mono">${Number(price[level]).toFixed(2)}</span>
              </div>
            )
          ))}
          {price.msrp != null && (
            <div className="flex justify-between">
              <span style={{ color: 'var(--db-text-muted)' }}>MSRP</span>
              <span className="font-mono">${Number(price.msrp).toFixed(2)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Cost */}
      <div>
        <div className="font-medium mb-1" style={{ color: 'var(--db-text)' }}>Cost</div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
          {cost.standard != null && (
            <div className="flex justify-between">
              <span style={{ color: 'var(--db-text-muted)' }}>Standard</span>
              <span className="font-mono">${Number(cost.standard).toFixed(4)}</span>
            </div>
          )}
          {cost.last != null && (
            <div className="flex justify-between">
              <span style={{ color: 'var(--db-text-muted)' }}>Last</span>
              <span className="font-mono">${Number(cost.last).toFixed(4)}</span>
            </div>
          )}
          {cost.avg != null && (
            <div className="flex justify-between">
              <span style={{ color: 'var(--db-text-muted)' }}>Average</span>
              <span className="font-mono">${Number(cost.avg).toFixed(4)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Inventory */}
      <div>
        <div className="font-medium mb-1" style={{ color: 'var(--db-text)' }}>Inventory</div>
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
                <span style={{ color: 'var(--db-text-muted)' }}>{label}</span>
                <span className="font-mono">{Number(val).toLocaleString()}</span>
              </div>
            )
          ))}
        </div>
      </div>

      {/* Flags */}
      <div className="flex flex-wrap gap-2">
        {flags.serialized && <span className="px-1.5 py-0.5 rounded" style={{ background: 'color-mix(in srgb, var(--db-accent) 15%, transparent)', color: 'var(--db-accent)' }}>Serialized</span>}
        {flags.discountable && <span className="px-1.5 py-0.5 rounded" style={{ background: 'color-mix(in srgb, var(--db-accent-green) 15%, transparent)', color: 'var(--db-accent-green)' }}>Discountable</span>}
        {flags.back_order_allowed && <span className="px-1.5 py-0.5 rounded" style={{ background: 'color-mix(in srgb, var(--db-accent-gold) 15%, transparent)', color: 'var(--db-accent-gold)' }}>Backorder OK</span>}
        {flags.not_tracked && <span className="px-1.5 py-0.5 rounded" style={{ background: 'var(--db-surface-alt)', color: 'var(--db-text-muted)' }}>Not Tracked</span>}
      </div>
    </div>
  );
};

export default SpecPanel;

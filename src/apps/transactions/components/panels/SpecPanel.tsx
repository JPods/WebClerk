/* LastChecked: 2026-08-01 | WhereUsed: LinesCard | WhoCreated: Claude */
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
      <div className="px-3 py-2 text-xs text-slate-400 dark:text-slate-500">
        Select a line to view item specification
      </div>
    );
  }

  if (loading) {
    return (
      <div className="px-3 py-2 text-xs text-slate-500 dark:text-slate-400">
        Loading specification for {itemCode}…
      </div>
    );
  }

  if (!item) {
    return (
      <div className="px-3 py-2 text-xs text-slate-400">
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
          <div className="font-mono font-bold text-sm text-slate-900 dark:text-white">{item.ida}</div>
          <div className="text-slate-600 dark:text-slate-300">{item.name}</div>
          {item.description && (
            <div className="text-slate-500 dark:text-slate-400 mt-1">{item.description}</div>
          )}
        </div>
        <div className="text-right text-slate-500 dark:text-slate-400">
          <div>UOM: {item.uom || 'EA'}</div>
          <div>Kind: {item.kind || '—'}</div>
        </div>
      </div>

      {/* Price levels */}
      <div>
        <div className="font-medium text-slate-700 dark:text-slate-200 mb-1">Price Levels</div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
          {['retail', 'wholesale', 'distributor', 'sample'].map(level => (
            price[level] != null && (
              <div key={level} className="flex justify-between">
                <span className="text-slate-500 capitalize">{level}</span>
                <span className="font-mono">${Number(price[level]).toFixed(2)}</span>
              </div>
            )
          ))}
          {price.msrp != null && (
            <div className="flex justify-between">
              <span className="text-slate-500">MSRP</span>
              <span className="font-mono">${Number(price.msrp).toFixed(2)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Cost */}
      <div>
        <div className="font-medium text-slate-700 dark:text-slate-200 mb-1">Cost</div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
          {cost.standard != null && (
            <div className="flex justify-between">
              <span className="text-slate-500">Standard</span>
              <span className="font-mono">${Number(cost.standard).toFixed(4)}</span>
            </div>
          )}
          {cost.last != null && (
            <div className="flex justify-between">
              <span className="text-slate-500">Last</span>
              <span className="font-mono">${Number(cost.last).toFixed(4)}</span>
            </div>
          )}
          {cost.avg != null && (
            <div className="flex justify-between">
              <span className="text-slate-500">Average</span>
              <span className="font-mono">${Number(cost.avg).toFixed(4)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Inventory */}
      <div>
        <div className="font-medium text-slate-700 dark:text-slate-200 mb-1">Inventory</div>
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
                <span className="text-slate-500">{label}</span>
                <span className="font-mono">{Number(val).toLocaleString()}</span>
              </div>
            )
          ))}
        </div>
      </div>

      {/* Flags */}
      <div className="flex flex-wrap gap-2">
        {flags.serialized && <span className="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded">Serialized</span>}
        {flags.discountable && <span className="px-1.5 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded">Discountable</span>}
        {flags.back_order_allowed && <span className="px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded">Backorder OK</span>}
        {flags.not_tracked && <span className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded">Not Tracked</span>}
      </div>
    </div>
  );
};

export default SpecPanel;

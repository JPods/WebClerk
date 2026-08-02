/* LastChecked: 2026-08-01 | WhereUsed: LinesCard | WhoCreated: Claude */
// Cross-reference panel — "XRef" button in WC2.
// Shows vendor/manufacturer cross-references for the selected line's item.
import React from 'react';
import { getRecords } from '@/api/wcapi';

interface XRefPanelProps {
  itemId: number | null;
  itemCode: string;
}

interface XRefRow {
  source: string;
  xref_id: string;
  description: string;
  price_cost: number | null;
  lead: number | null;
}

const formatCurrency = (v: number | null | undefined): string => {
  if (v == null) return '—';
  return `$${v.toFixed(2)}`;
};

const XRefPanel: React.FC<XRefPanelProps> = ({ itemId, itemCode }) => {
  const [xrefs, setXrefs] = React.useState<XRefRow[]>([]);
  const [item, setItem] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    if (!itemId) { setXrefs([]); setItem(null); return; }

    let cancelled = false;
    setLoading(true);

    (async () => {
      try {
        const res = await getRecords('item', { id: itemId, limit: 1 });
        const rec = res?.records?.[0];
        if (cancelled) return;
        setItem(rec);

        // Extract cross-references from item refs or related records
        const refs = rec?.refs || {};
        const rows: XRefRow[] = [];

        // Vendor xref
        if (rec?.vendor_item_num || refs.vendor_item_id) {
          rows.push({
            source: 'Vendor',
            xref_id: String(rec.vendor_item_num || refs.vendor_item_id || ''),
            description: rec.vendor?.name || '',
            price_cost: rec.cost?.last ?? null,
            lead: rec.config?.lead_time ?? null,
          });
        }

        // Manufacturer xref
        if (rec?.mfg_item_num || refs.mfg_item_id) {
          rows.push({
            source: 'Manufacturer',
            xref_id: String(rec.mfg_item_num || refs.mfg_item_id || ''),
            description: rec.manufacturer?.name || '',
            price_cost: rec.cost?.standard ?? null,
            lead: null,
          });
        }

        // Any additional xrefs stored in refs.xrefs array
        if (Array.isArray(refs.xrefs)) {
          for (const xr of refs.xrefs) {
            rows.push({
              source: xr.source || 'Other',
              xref_id: xr.xref_id || xr.item_id || '',
              description: xr.description || '',
              price_cost: xr.price ?? xr.cost ?? null,
              lead: xr.lead_time ?? null,
            });
          }
        }

        if (!cancelled) setXrefs(rows);
      } catch {
        if (!cancelled) { setXrefs([]); setItem(null); }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [itemId]);

  if (!itemId) {
    return (
      <div className="px-3 py-2 text-xs text-slate-400 dark:text-slate-500">
        Select a line to view cross-references
      </div>
    );
  }

  if (loading) {
    return (
      <div className="px-3 py-2 text-xs text-slate-500 dark:text-slate-400">
        Loading cross-references for {itemCode}…
      </div>
    );
  }

  return (
    <div className="px-3 py-2 text-xs">
      {/* Header */}
      <div className="font-medium text-slate-700 dark:text-slate-200 mb-2">
        X-Ref: {itemCode}
        {item && (
          <span className="ml-2 text-slate-500 dark:text-slate-400 font-normal">
            {item.name}
          </span>
        )}
      </div>

      {xrefs.length === 0 ? (
        <div className="text-slate-400 dark:text-slate-500 py-2">
          No cross-references for this item
        </div>
      ) : (
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              <th className="text-left px-2 py-1 font-medium">Source</th>
              <th className="text-left px-2 py-1 font-medium">Item XRef</th>
              <th className="text-left px-2 py-1 font-medium">Description</th>
              <th className="text-right px-2 py-1 font-medium">Price/Cost</th>
              <th className="text-right px-2 py-1 font-medium">Lead</th>
            </tr>
          </thead>
          <tbody>
            {xrefs.map((xr, i) => (
              <tr
                key={i}
                className="border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50"
              >
                <td className="px-2 py-1 text-slate-500">{xr.source}</td>
                <td className="px-2 py-1 font-mono">{xr.xref_id}</td>
                <td className="px-2 py-1 text-slate-600 dark:text-slate-300">{xr.description}</td>
                <td className="px-2 py-1 text-right">{formatCurrency(xr.price_cost)}</td>
                <td className="px-2 py-1 text-right">{xr.lead != null ? `${xr.lead}d` : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default XRefPanel;

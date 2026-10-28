/**
 * InventoryLayersPanel — FIFO/LIFO cost layers for an item, grouped by warehouse.
 * Shows on Item dashboard "Layers" tab. The panel frame draws the header, count and status.
 */
import { getInventoryLayers } from "@/api/workorderApi";
import { usePanelRecords } from "@/hooks/usePanelRecords";
import { usePanelFrame } from "@/apps/common/components/CollapsiblePanel";

interface Layer {
  id: number;
  warehouse_name: string;
  warehouse_code: string;
  lot: string;
  received: number;
  issued: number;
  scrapped: number;
  remaining: number;
  unit_po: number;
  landed: number;
  moving_avg: number;
  fifo_snapshot: number;
  lifo_snapshot: number;
  freight: number;
  duty: number;
  currency: string;
  dt_created: number | null;
  parent_model: string;
  parent_id: number | null;
}

interface Props {
  itemId: number;
}

export default function InventoryLayersPanel({ itemId }: Props) {
  const { records: layers, status } = usePanelRecords<Layer>("inventory layers", { item_id: itemId },
    { enabled: !!itemId, read: getInventoryLayers, emptyText: "No inventory layers for this item." });
  usePanelFrame({ badge: layers.length, status });

  // Group by warehouse
  const byWarehouse: Record<string, Layer[]> = {};
  for (const l of layers) {
    const key = l.warehouse_name || l.warehouse_code || "Default";
    if (!byWarehouse[key]) byWarehouse[key] = [];
    byWarehouse[key].push(l);
  }

  return (
    <div className="space-y-4 p-2">
      {Object.entries(byWarehouse).map(([wh, whLayers]) => {
        // Aggregate of server-provided per-layer values — no server-side warehouse aggregate available
        const totalRemaining = whLayers.reduce((s, l) => s + l.remaining, 0);
        const totalValue = whLayers.reduce((s, l) => s + l.remaining * l.landed, 0);
        return (
          <div key={wh}>
            <div className="flex items-center justify-between mb-1 px-1">
              <span className="text-xs font-bold text-slate-300">{wh}</span>
              <span className="text-xs text-slate-500">
                {totalRemaining} units | ${totalValue.toFixed(2)} value
              </span>
            </div>
            <table className="w-full text-xs border-collapse">
              <thead className="sticky top-0" style={{ background: "var(--db-surface, #fff)" }}>
                <tr className="text-slate-500 border-b border-slate-700">
                  <th className="text-left px-2 py-1">Lot</th>
                  <th className="text-right px-2 py-1">Rcvd</th>
                  <th className="text-right px-2 py-1">Issued</th>
                  <th className="text-right px-2 py-1">Remain</th>
                  <th className="text-right px-2 py-1">PO Cost</th>
                  <th className="text-right px-2 py-1">Landed</th>
                  <th className="text-right px-2 py-1">FIFO</th>
                  <th className="text-right px-2 py-1">LIFO</th>
                  <th className="text-right px-2 py-1">Avg</th>
                  <th className="text-right px-2 py-1">Ext Value</th>
                  <th className="text-center px-2 py-1">Source</th>
                </tr>
              </thead>
              <tbody>
                {whLayers.map((l) => (
                  <tr
                    key={l.id}
                    className={`border-b border-slate-800 ${l.remaining <= 0 ? "opacity-40" : ""}`}
                  >
                    <td className="px-2 py-1 text-slate-300">{l.lot || "-"}</td>
                    <td className="px-2 py-1 text-right">{l.received}</td>
                    <td className="px-2 py-1 text-right">{l.issued}</td>
                    <td className="px-2 py-1 text-right font-semibold">{l.remaining}</td>
                    <td className="px-2 py-1 text-right">{l.unit_po.toFixed(2)}</td>
                    <td className="px-2 py-1 text-right">{l.landed.toFixed(2)}</td>
                    <td className="px-2 py-1 text-right text-slate-400">{l.fifo_snapshot.toFixed(2)}</td>
                    <td className="px-2 py-1 text-right text-slate-400">{l.lifo_snapshot.toFixed(2)}</td>
                    <td className="px-2 py-1 text-right text-slate-400">{l.moving_avg.toFixed(2)}</td>
                    <td className="px-2 py-1 text-right font-semibold">
                      {(l.remaining * l.landed).toFixed(2)}
                    </td>
                    <td className="px-2 py-1 text-center text-slate-500">
                      {l.parent_model ? `${l.parent_model} #${l.parent_id}` : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })}
    </div>
  );
}

/**
 * InventoryLayersPanel — FIFO/LIFO cost layers for an item, grouped by warehouse.
 * Shows on Item dashboard "Layers" tab.
 */
import React, { useEffect, useState } from "react";

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
  is_locked: boolean;
  dt_created: string | null;
  source_doc_type: string;
  source_doc_id: number | null;
}

interface Props {
  itemId: number;
}

export default function InventoryLayersPanel({ itemId }: Props) {
  const [layers, setLayers] = useState<Layer[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!itemId) return;
    setLoading(true);
    const token = document.cookie
      .split("; ")
      .find((c) => c.startsWith("access_token="))
      ?.split("=")[1];

    fetch(`/wcapi/products/inventory/layers/?item_id=${itemId}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      credentials: "include",
    })
      .then((r) => r.json())
      .then((resp) => {
        setLayers(resp.data || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [itemId]);

  if (loading) return <div className="p-4 text-xs text-slate-400">Loading layers...</div>;
  if (layers.length === 0) return <div className="p-4 text-xs text-slate-400">No inventory layers for this item.</div>;

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
              <thead>
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
                  <th className="text-center px-1 py-1"></th>
                </tr>
              </thead>
              <tbody>
                {whLayers.map((l) => (
                  <tr
                    key={l.id}
                    className={`border-b border-slate-800 ${l.is_locked ? "bg-yellow-900/20" : ""} ${l.remaining <= 0 ? "opacity-40" : ""}`}
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
                      {l.source_doc_type ? `${l.source_doc_type} #${l.source_doc_id}` : "-"}
                    </td>
                    <td className="px-1 py-1 text-center">
                      {l.is_locked && <span title="Locked" className="text-yellow-500">L</span>}
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

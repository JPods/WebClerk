/**
 * CycleCountPanel — cycle count workflow on the Item dashboard.
 * Shows current layer quantities, lets user enter actual counts,
 * calculates variance, and creates adjustments for differences.
 */
import React, { useEffect, useState, useCallback } from "react";

interface LayerCount {
  layer_id: number;
  warehouse_name: string;
  lot: string;
  system_qty: number;
  counted_qty: number | null;
  variance: number;
}

interface Props {
  itemId: number;
  itemCode?: string;
}

export default function CycleCountPanel({ itemId, itemCode }: Props) {
  const [rows, setRows] = useState<LayerCount[]>([]);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(false);
  const [message, setMessage] = useState("");

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
        const layers = resp.data || [];
        setRows(
          layers
            .filter((l: any) => l.remaining > 0)
            .map((l: any) => ({
              layer_id: l.id,
              warehouse_name: l.warehouse_name || l.warehouse_code || "Default",
              lot: l.lot || "-",
              system_qty: l.remaining,
              counted_qty: null,
              variance: 0,
            }))
        );
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [itemId]);

  const updateCount = useCallback((idx: number, value: number | null) => {
    setRows((prev) =>
      prev.map((r, i) => {
        if (i !== idx) return r;
        const counted = value;
        return {
          ...r,
          counted_qty: counted,
          variance: counted !== null ? counted - r.system_qty : 0,
        };
      })
    );
  }, []);

  const applyAdjustments = useCallback(async () => {
    const diffs = rows.filter((r) => r.counted_qty !== null && r.variance !== 0);
    if (diffs.length === 0) {
      setMessage("No variances to apply.");
      return;
    }

    setApplying(true);
    setMessage("");

    try {
      const token = document.cookie
        .split("; ")
        .find((c) => c.startsWith("access_token="))
        ?.split("=")[1];

      // Get warehouse_id from layers endpoint — we need it for the adjustment
      const layerResp = await fetch(`/wcapi/products/inventory/layers/?item_id=${itemId}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        credentials: "include",
      });
      const layerData = await layerResp.json();
      const layerMap: Record<number, any> = {};
      for (const l of layerData.data || []) {
        layerMap[l.id] = l;
      }

      // Group adjustments by warehouse
      const byWarehouse: Record<number, { item_id: number; qty: number; reason: string; notes: string }[]> = {};
      for (const d of diffs) {
        const layer = layerMap[d.layer_id];
        if (!layer) continue;
        const wid = layer.warehouse_id;
        if (!byWarehouse[wid]) byWarehouse[wid] = [];
        byWarehouse[wid].push({
          item_id: itemId,
          qty: d.variance,
          reason: "cycle_count",
          notes: `Cycle count: system=${d.system_qty}, counted=${d.counted_qty}, variance=${d.variance}`,
        });
      }

      let totalApplied = 0;
      let totalPending = 0;

      for (const [whId, lines] of Object.entries(byWarehouse)) {
        const resp = await fetch("/wcapi/products/inventory/adjust/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          credentials: "include",
          body: JSON.stringify({ warehouse_id: Number(whId), lines }),
        });
        const result = await resp.json();
        const data = result.data || result;
        totalApplied += data.applied || 0;
        totalPending += data.pending || 0;
      }

      setMessage(`Cycle count: ${totalApplied} applied, ${totalPending} pending.`);
      // Reset counted values
      setRows((prev) =>
        prev.map((r) => ({
          ...r,
          system_qty: r.counted_qty !== null && r.variance !== 0 ? r.counted_qty! : r.system_qty,
          counted_qty: null,
          variance: 0,
        }))
      );
    } catch (err: any) {
      setMessage(`Error: ${err.message}`);
    }
    setApplying(false);
  }, [rows, itemId]);

  if (loading) return <div className="p-4 text-xs text-slate-400">Loading...</div>;
  if (rows.length === 0) return <div className="p-4 text-xs text-slate-400">No active inventory layers for cycle count.</div>;

  const hasVariances = rows.some((r) => r.counted_qty !== null && r.variance !== 0);
  // Aggregate of user-entered variance values — no server-side aggregate available
  const totalVariance = rows.reduce((s, r) => s + r.variance, 0);

  return (
    <div className="p-2">
      <div className="flex items-center justify-between mb-2 px-1">
        <span className="text-xs font-bold text-slate-300">
          Cycle Count — {itemCode || `Item #${itemId}`}
        </span>
        {hasVariances && (
          <span className={`text-xs font-semibold ${totalVariance >= 0 ? "text-green-400" : "text-red-400"}`}>
            Net variance: {totalVariance > 0 ? "+" : ""}{totalVariance}
          </span>
        )}
      </div>

      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="text-slate-500 border-b border-slate-700">
            <th className="text-left px-2 py-1">Warehouse</th>
            <th className="text-left px-2 py-1">Lot</th>
            <th className="text-right px-2 py-1">System Qty</th>
            <th className="text-right px-2 py-1 w-24">Counted</th>
            <th className="text-right px-2 py-1">Variance</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, idx) => (
            <tr
              key={r.layer_id}
              className={`border-b border-slate-800 ${
                r.variance !== 0
                  ? r.variance > 0
                    ? "bg-green-900/10"
                    : "bg-red-900/10"
                  : ""
              }`}
            >
              <td className="px-2 py-1 text-slate-300">{r.warehouse_name}</td>
              <td className="px-2 py-1 text-slate-400">{r.lot}</td>
              <td className="px-2 py-1 text-right font-mono">{r.system_qty}</td>
              <td className="px-2 py-1 text-right">
                <input
                  type="number"
                  value={r.counted_qty ?? ""}
                  placeholder="-"
                  onChange={(e) => {
                    const v = e.target.value;
                    updateCount(idx, v === "" ? null : Number(v));
                  }}
                  className="w-20 px-1 py-0.5 text-right rounded border border-slate-600 bg-slate-900 text-slate-200 text-xs"
                />
              </td>
              <td
                className={`px-2 py-1 text-right font-semibold ${
                  r.variance > 0 ? "text-green-400" : r.variance < 0 ? "text-red-400" : "text-slate-500"
                }`}
              >
                {r.counted_qty !== null
                  ? `${r.variance > 0 ? "+" : ""}${r.variance}`
                  : "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="flex items-center justify-between mt-3 px-1">
        <span className={`text-xs ${message.startsWith("Error") ? "text-red-400" : "text-green-400"}`}>
          {message}
        </span>
        <button
          onClick={applyAdjustments}
          disabled={!hasVariances || applying}
          className={`px-4 py-1.5 rounded text-xs font-semibold ${
            hasVariances
              ? "bg-blue-600 text-white cursor-pointer hover:bg-blue-700"
              : "bg-slate-700 text-slate-500 cursor-default"
          }`}
        >
          {applying ? "Applying..." : "Apply Adjustments"}
        </button>
      </div>
    </div>
  );
}

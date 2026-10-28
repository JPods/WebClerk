/**
 * CycleCountPanel — cycle count workflow on the Item dashboard.
 * Shows current layer quantities, lets user enter actual counts,
 * calculates variance, and creates adjustments for differences. After a count is saved the
 * layers are read again: the server's quantities, not a local guess (TFTS 2026-10-26).
 */
import { useEffect, useMemo, useState, useCallback } from "react";
import { saveCorrection, getInventoryLayers } from "@/api/workorderApi";
import { usePanelRecords } from "@/hooks/usePanelRecords";
import { usePanelFrame } from "@/apps/common/components/CollapsiblePanel";

interface LayerCount {
  layer_id: number;
  warehouse_name: string;
  lot: string;
  system_qty: number;
  unit_cost: number;
  counted_qty: number | null;
  variance: number;
}

interface Props {
  itemId: number;
}

export default function CycleCountPanel({ itemId }: Props) {
  const [rows, setRows] = useState<LayerCount[]>([]);
  const [applying, setApplying] = useState(false);
  const [message, setMessage] = useState("");
  const { records: layers, refresh, status } = usePanelRecords<any>("inventory layers", { item_id: itemId },
    { enabled: !!itemId, read: getInventoryLayers });

  // A fresh read replaces the counts entered against the old one.
  useEffect(() => {
    setRows(
      layers
        .filter((l) => l.remaining > 0)
        .map((l) => ({
          layer_id: l.id,
          warehouse_name: l.warehouse_name || l.warehouse_code || "Default",
          lot: l.lot || "-",
          system_qty: l.remaining,
          unit_cost: Number(l.landed) || 0,
          counted_qty: null,
          variance: 0,
        }))
    );
  }, [layers]);

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
      // A layer's count is an adjustment of that layer (stock plan §16b): the variance, the layer it
      // belongs to, and what was seen, on one count workorder. More than the layer held lands in a
      // layer of its own at this layer's cost.
      const saved: any = await saveCorrection(
        diffs.map((d) => ({
          item_id: itemId,
          line_type: "adjust" as const,
          quantity: d.variance,
          layer_id: d.layer_id,
          unit_cost: d.variance > 0 ? d.unit_cost : undefined,
          reason: `Cycle count, layer ${d.layer_id} (${d.lot}): system ${d.system_qty}, counted ${d.counted_qty}`,
        }))
      );
      const woIda = saved?.record?.ida ?? saved?.ida ?? "";
      setMessage(`Cycle count saved as workorder ${woIda}: ${diffs.length} layer(s) corrected.`);
      refresh();
    } catch (err: any) {
      setMessage(`Error: ${err?.response?.data?.message || err.message}`);
    }
    setApplying(false);
  }, [rows, itemId, refresh]);

  const hasVariances = rows.some((r) => r.counted_qty !== null && r.variance !== 0);
  // Aggregate of user-entered variance values — no server-side aggregate available
  const totalVariance = rows.reduce((s, r) => s + r.variance, 0);

  const headerActions = useMemo(() => hasVariances ? (
    <span className={`text-xs font-semibold ${totalVariance >= 0 ? "text-green-400" : "text-red-400"}`}>
      Net variance: {totalVariance > 0 ? "+" : ""}{totalVariance}
    </span>
  ) : null, [hasVariances, totalVariance]);
  const frameStatus = useMemo(() => ({
    ...status,
    empty: status.empty || (layers.length > 0 && !layers.some((l) => l.remaining > 0)),
    emptyText: "No active inventory layers for cycle count.",
  }), [status, layers]);
  usePanelFrame({ badge: rows.length, headerActions, status: frameStatus });
  if (rows.length === 0) return null;

  return (
    <div className="p-2">
      <table className="w-full text-xs border-collapse">
        <thead className="sticky top-0" style={{ background: "var(--db-surface, #fff)" }}>
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

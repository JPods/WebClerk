/**
 * InventoryAdjust — spreadsheet-style inventory adjustment page.
 * Based on WC2 diaInvAdjust pattern: search items, see on-hand, type adjustment + reason, Apply.
 * Every adjustment flows through PendingInventoryAdjustment — one path, one audit trail.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import apiClient from "@/api/axios";
import { getRecords, searchItems } from "@/api/wcapi";
import "@/pages/admin/DataBrowser.css";

interface AdjustmentLine {
  item_id: number;
  ida: string;
  name: string;
  qty_on_hand: number;
  adjust: number;
  new_on_hand: number;
  unit_cost: number;
  reason: string;
  notes: string;
}

interface Warehouse {
  id: number;
  name: string;
  code: string;
}

const REASON_CODES = [
  { value: "cycle_count", label: "Cycle Count" },
  { value: "damage", label: "Damage" },
  { value: "return", label: "Return" },
  { value: "shrinkage", label: "Shrinkage" },
  { value: "correction", label: "Correction" },
  { value: "receipt", label: "Receipt" },
  { value: "other", label: "Other" },
];

export default function InventoryAdjust() {
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [warehouseId, setWarehouseId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [lines, setLines] = useState<AdjustmentLine[]>([]);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [message, setMessage] = useState("");
  const [bomMode, setBomMode] = useState<"off" | "single" | "multi">("off");
  const searchRef = useRef<HTMLInputElement>(null);

  // Load warehouses on mount
  useEffect(() => {
    getRecords("warehouse", { is_active: true }).then((resp: any) => {
      const wh = resp?.data || resp?.results || resp || [];
      setWarehouses(Array.isArray(wh) ? wh : []);
      if (Array.isArray(wh) && wh.length > 0) {
        setWarehouseId(wh[0].id);
      }
    });
  }, []);

  // Search items
  const doSearch = useCallback(async () => {
    if (!searchQuery.trim()) return;
    setLoading(true);
    try {
      const resp = await searchItems(searchQuery, { limit: 50 });
      const items = resp?.data || resp?.results || resp || [];
      setSearchResults(Array.isArray(items) ? items : []);
    } catch {
      setSearchResults([]);
    }
    setLoading(false);
  }, [searchQuery]);

  // Add item to adjustment lines
  const addItem = useCallback(
    (item: any) => {
      const id = item.id || item.item_id;
      if (lines.some((l) => l.item_id === id)) return; // already in list

      const qty = item.quantity || {};
      const on_hand =
        typeof qty === "object"
          ? (qty.on_hand ?? qty.available ?? (qty.received || 0) - (qty.issued || 0) - (qty.scrapped || 0))
          : 0;
      const cost = item.cost?.standard ?? item.cost?.landed ?? item.unit_cost ?? 0;

      setLines((prev) => [
        ...prev,
        {
          item_id: id,
          ida: item.ida || item.item_num || item.sku || String(id),
          name: item.name || item.description || "",
          qty_on_hand: Number(on_hand) || 0,
          adjust: 0,
          new_on_hand: Number(on_hand) || 0,
          unit_cost: Number(cost) || 0,
          reason: "cycle_count",
          notes: "",
        },
      ]);
    },
    [lines]
  );

  // Update adjustment qty for a line
  const updateAdjust = useCallback((idx: number, value: number) => {
    setLines((prev) =>
      prev.map((l, i) =>
        i === idx
          ? { ...l, adjust: value, new_on_hand: l.qty_on_hand + value }
          : l
      )
    );
  }, []);

  // Update reason for a line
  const updateReason = useCallback((idx: number, reason: string) => {
    setLines((prev) =>
      prev.map((l, i) => (i === idx ? { ...l, reason } : l))
    );
  }, []);

  // Remove a line
  const removeLine = useCallback((idx: number) => {
    setLines((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  // Apply adjustments
  const applyAdjustments = useCallback(async () => {
    const toApply = lines.filter((l) => l.adjust !== 0);
    if (toApply.length === 0) {
      setMessage("No adjustments to apply.");
      return;
    }
    if (!warehouseId) {
      setMessage("Select a warehouse.");
      return;
    }

    setApplying(true);
    setMessage("");

    try {
      const resp = await apiClient.post("/wcapi/products/inventory/adjust/", {
          warehouse_id: warehouseId,
          lines: toApply.map((l) => ({
            item_id: l.item_id,
            qty: l.adjust,
            reason: l.reason,
            notes: l.notes,
          })),
        });

      const result = resp.data;
      if (result.success !== false) {
        const data = result.data || result;
        setMessage(
          `Applied ${data.applied || 0}, pending ${data.pending || 0}.`
        );
        // Update on-hand from results
        const resultLines = data.lines || [];
        setLines((prev) =>
          prev.map((l) => {
            const rl = resultLines.find(
              (r: any) => r.item_id === l.item_id
            );
            if (rl) {
              return {
                ...l,
                qty_on_hand: rl.new_on_hand,
                adjust: 0,
                new_on_hand: rl.new_on_hand,
              };
            }
            return { ...l, adjust: 0, new_on_hand: l.qty_on_hand };
          })
        );
      } else {
        setMessage(`Error: ${result.message || "Failed"}`);
      }
    } catch (err: any) {
      setMessage(`Error: ${err.message}`);
    }
    setApplying(false);
  }, [lines, warehouseId]);

  // BOM adjust
  const applyBOM = useCallback(
    async (itemId: number, qty: number) => {
      if (!warehouseId) return;

      const resp = await apiClient.post("/wcapi/products/inventory/adjust-bom/", {
          item_id: itemId,
          warehouse_id: warehouseId,
          qty,
          reason: "bom_build",
        });

      const result = resp.data;
      if (result.success !== false) {
        const data = result.data || result;
        setMessage(
          `BOM: Applied ${data.applied || 0}, pending ${data.pending || 0}.`
        );
      } else {
        setMessage(`BOM Error: ${result.message || "Failed"}`);
      }
    },
    [warehouseId]
  );

  const hasChanges = lines.some((l) => l.adjust !== 0);
  const selectedWarehouse = warehouses.find((w) => w.id === warehouseId);

  return (
    <div
      className="db-root"
      data-theme="dark"
      style={{
        maxWidth: 1100,
        margin: "0 auto",
        padding: 24,
      }}
    >
      {/* Header */}
      <div className="db-flex-between" style={{ marginBottom: 16 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>Adjust Inventory</h1>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <label className="db-text-muted db-font-sm">Warehouse</label>
          <select
            value={warehouseId || ""}
            onChange={(e) => setWarehouseId(Number(e.target.value))}
            className="db-input"
            style={{ padding: "6px 10px", width: "auto" }}
          >
            {warehouses.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name || w.code}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Search bar */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16, alignItems: "center" }}>
        <input
          ref={searchRef}
          type="text"
          placeholder="Item number or keyword..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && doSearch()}
          className="db-input"
          style={{ flex: 1, padding: "8px 12px", fontSize: 14 }}
        />
        <button
          onClick={doSearch}
          disabled={loading}
          className="db-btn db-btn--primary"
          style={{ padding: "8px 20px", fontSize: 14 }}
        >
          Search
        </button>
      </div>

      {/* Search results dropdown */}
      {searchResults.length > 0 && (
        <div
          className="db-panel-input"
          style={{ borderRadius: 4, marginBottom: 16, maxHeight: 200, overflowY: "auto" }}
        >
          {searchResults.map((item: any) => {
            const id = item.id || item.item_id;
            const qty = item.quantity || {};
            const onHand =
              typeof qty === "object"
                ? (qty.on_hand ?? qty.available ?? 0)
                : 0;
            return (
              <div
                key={id}
                onClick={() => {
                  addItem(item);
                  setSearchResults([]);
                  setSearchQuery("");
                  searchRef.current?.focus();
                }}
                className="db-border-bottom-light"
                style={{
                  padding: "6px 12px",
                  cursor: "pointer",
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 13,
                }}
                onMouseOver={(e) =>
                  (e.currentTarget.style.background = "var(--db-row-hover)")
                }
                onMouseOut={(e) =>
                  (e.currentTarget.style.background = "transparent")
                }
              >
                <span className="db-font-bold" style={{ width: 120 }}>
                  {item.ida || item.sku || item.item_num}
                </span>
                <span className="db-text-muted" style={{ flex: 1 }}>
                  {item.name || item.description}
                </span>
                <span style={{ width: 60, textAlign: "right" }}>
                  {onHand}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Adjustment grid */}
      <div className="db-border-all" style={{ borderRadius: 4, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr className="db-bg-surface db-border-bottom db-text-muted db-font-base" style={{ textTransform: "uppercase" }}>

              <th style={{ padding: "8px 12px", textAlign: "left" }}>Item</th>
              <th style={{ padding: "8px 12px", textAlign: "left" }}>
                Description
              </th>
              <th style={{ padding: "8px 12px", textAlign: "left", width: 130 }}>
                Reason
              </th>
              <th
                style={{
                  padding: "8px 12px",
                  textAlign: "right",
                  width: 80,
                }}
              >
                Qty O/H
              </th>
              <th
                style={{
                  padding: "8px 12px",
                  textAlign: "right",
                  width: 90,
                }}
              >
                Adjust
              </th>
              <th
                style={{
                  padding: "8px 12px",
                  textAlign: "right",
                  width: 80,
                }}
              >
                New O/H
              </th>
              <th
                style={{
                  padding: "8px 12px",
                  textAlign: "right",
                  width: 80,
                }}
              >
                Cost
              </th>
              <th style={{ width: 36 }}></th>
            </tr>
          </thead>
          <tbody>
            {lines.length === 0 && (
              <tr>
                <td
                  colSpan={8}
                  className="db-text-dim"
                  style={{ padding: 24, textAlign: "center", fontSize: 13 }}
                >
                  Search for items above and add them to this list.
                </td>
              </tr>
            )}
            {lines.map((line, idx) => (
              <tr
                key={line.item_id}
                className="db-border-bottom-light"
                style={{
                  background:
                    line.adjust !== 0
                      ? line.adjust > 0
                        ? "rgba(34,197,94,0.08)"
                        : "rgba(239,68,68,0.08)"
                      : "transparent",
                }}
              >
                <td className="db-font-bold" style={{ padding: "6px 12px", fontSize: 13 }}>
                  {line.ida}
                </td>
                <td className="db-text-muted" style={{ padding: "6px 12px", fontSize: 13 }}>
                  {line.name}
                </td>
                <td style={{ padding: "4px 8px" }}>
                  <select
                    value={line.reason}
                    onChange={(e) => updateReason(idx, e.target.value)}
                    className="db-input"
                    style={{ width: "100%", padding: "4px 6px", fontSize: 12 }}
                  >
                    {REASON_CODES.map((r) => (
                      <option key={r.value} value={r.value}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                </td>
                <td
                  style={{
                    padding: "6px 12px",
                    textAlign: "right",
                    fontSize: 13,
                  }}
                >
                  {line.qty_on_hand}
                </td>
                <td style={{ padding: "4px 8px", textAlign: "right" }}>
                  <input
                    type="number"
                    value={line.adjust || ""}
                    onChange={(e) =>
                      updateAdjust(idx, Number(e.target.value) || 0)
                    }
                    className="db-input db-font-bold"
                    style={{
                      width: 70,
                      padding: "4px 6px",
                      color:
                        line.adjust > 0
                          ? "var(--db-accent-green)"
                          : line.adjust < 0
                          ? "var(--db-accent-red)"
                          : "var(--db-text)",
                      textAlign: "right",
                      fontSize: 13,
                    }}
                  />
                </td>
                <td
                  style={{
                    padding: "6px 12px",
                    textAlign: "right",
                    fontSize: 13,
                    fontWeight: line.adjust !== 0 ? 600 : 400,
                    color:
                      line.new_on_hand < 0
                        ? "var(--db-accent-red)"
                        : line.adjust !== 0
                        ? "#fff"
                        : "var(--db-text-muted)",
                  }}
                >
                  {line.new_on_hand}
                </td>
                <td
                  className="db-text-muted"
                  style={{ padding: "6px 12px", textAlign: "right", fontSize: 13 }}
                >
                  {line.unit_cost.toFixed(2)}
                </td>
                <td style={{ padding: "4px" }}>
                  <button
                    onClick={() => removeLine(idx)}
                    className="db-text-dim"
                    style={{
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      fontSize: 16,
                      padding: "2px 6px",
                    }}
                    title="Remove"
                  >
                    ×
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer buttons */}
      <div className="db-flex-between" style={{ marginTop: 16 }}>
        <div style={{
          fontSize: 13,
          color: message.startsWith("Error") ? "var(--db-accent-red)" : "var(--db-accent-green)",
        }}>
          {message}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={applyAdjustments}
            disabled={!hasChanges || applying}
            className={`db-btn ${hasChanges ? "db-btn--primary" : ""} db-font-bold`}
            style={{ padding: "8px 24px", fontSize: 14 }}
          >
            {applying ? "Applying..." : "Apply"}
          </button>
          <button
            onClick={() => {
              setLines([]);
              setMessage("");
            }}
            className="db-btn"
            style={{ padding: "8px 16px", fontSize: 14 }}
          >
            Clear
          </button>
        </div>
      </div>
    </div>
  );
}

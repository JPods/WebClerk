/**
 * InventoryAdjust — spreadsheet-style inventory adjustment page.
 * Based on WC2 diaInvAdjust pattern: search items, see on-hand, type adjustment + reason, Apply.
 * Every adjustment flows through PendingInventoryAdjustment — one path, one audit trail.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { getRecords, searchItems } from "../../../api/wcapi";

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
      const token = document.cookie
        .split("; ")
        .find((c) => c.startsWith("access_token="))
        ?.split("=")[1];

      const resp = await fetch("/api/products/inventory/adjust/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        credentials: "include",
        body: JSON.stringify({
          warehouse_id: warehouseId,
          lines: toApply.map((l) => ({
            item_id: l.item_id,
            qty: l.adjust,
            reason: l.reason,
            notes: l.notes,
          })),
        }),
      });

      const result = await resp.json();
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

      const token = document.cookie
        .split("; ")
        .find((c) => c.startsWith("access_token="))
        ?.split("=")[1];

      const resp = await fetch("/api/products/inventory/adjust-bom/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        credentials: "include",
        body: JSON.stringify({
          item_id: itemId,
          warehouse_id: warehouseId,
          qty,
          reason: "bom_build",
        }),
      });

      const result = await resp.json();
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
      style={{
        maxWidth: 1100,
        margin: "0 auto",
        padding: 24,
        fontFamily: "system-ui, sans-serif",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <h1 style={{ margin: 0, fontSize: 22 }}>Adjust Inventory</h1>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <label style={{ fontSize: 13, color: "#888" }}>Warehouse</label>
          <select
            value={warehouseId || ""}
            onChange={(e) => setWarehouseId(Number(e.target.value))}
            style={{
              padding: "6px 10px",
              borderRadius: 4,
              border: "1px solid #555",
              background: "#1e1e1e",
              color: "#e0e0e0",
            }}
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
      <div
        style={{
          display: "flex",
          gap: 8,
          marginBottom: 16,
          alignItems: "center",
        }}
      >
        <input
          ref={searchRef}
          type="text"
          placeholder="Item number or keyword..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && doSearch()}
          style={{
            flex: 1,
            padding: "8px 12px",
            borderRadius: 4,
            border: "1px solid #555",
            background: "#1e1e1e",
            color: "#e0e0e0",
            fontSize: 14,
          }}
        />
        <button
          onClick={doSearch}
          disabled={loading}
          style={{
            padding: "8px 20px",
            borderRadius: 4,
            border: "none",
            background: "#2563eb",
            color: "#fff",
            cursor: "pointer",
            fontSize: 14,
          }}
        >
          Search
        </button>
      </div>

      {/* Search results dropdown */}
      {searchResults.length > 0 && (
        <div
          style={{
            border: "1px solid #444",
            borderRadius: 4,
            marginBottom: 16,
            maxHeight: 200,
            overflowY: "auto",
            background: "#1a1a1a",
          }}
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
                style={{
                  padding: "6px 12px",
                  cursor: "pointer",
                  display: "flex",
                  justifyContent: "space-between",
                  borderBottom: "1px solid #333",
                  fontSize: 13,
                }}
                onMouseOver={(e) =>
                  (e.currentTarget.style.background = "#2a2a2a")
                }
                onMouseOut={(e) =>
                  (e.currentTarget.style.background = "transparent")
                }
              >
                <span style={{ fontWeight: 600, width: 120 }}>
                  {item.ida || item.sku || item.item_num}
                </span>
                <span style={{ flex: 1, color: "#aaa" }}>
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
      <div
        style={{
          border: "1px solid #444",
          borderRadius: 4,
          overflow: "hidden",
        }}
      >
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr
              style={{
                background: "#252525",
                borderBottom: "1px solid #444",
                fontSize: 12,
                textTransform: "uppercase",
                color: "#999",
              }}
            >
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
                  style={{
                    padding: 24,
                    textAlign: "center",
                    color: "#666",
                    fontSize: 13,
                  }}
                >
                  Search for items above and add them to this list.
                </td>
              </tr>
            )}
            {lines.map((line, idx) => (
              <tr
                key={line.item_id}
                style={{
                  borderBottom: "1px solid #333",
                  background:
                    line.adjust !== 0
                      ? line.adjust > 0
                        ? "rgba(34,197,94,0.08)"
                        : "rgba(239,68,68,0.08)"
                      : "transparent",
                }}
              >
                <td
                  style={{
                    padding: "6px 12px",
                    fontWeight: 600,
                    fontSize: 13,
                  }}
                >
                  {line.ida}
                </td>
                <td style={{ padding: "6px 12px", fontSize: 13, color: "#bbb" }}>
                  {line.name}
                </td>
                <td style={{ padding: "4px 8px" }}>
                  <select
                    value={line.reason}
                    onChange={(e) => updateReason(idx, e.target.value)}
                    style={{
                      width: "100%",
                      padding: "4px 6px",
                      borderRadius: 3,
                      border: "1px solid #555",
                      background: "#1e1e1e",
                      color: "#e0e0e0",
                      fontSize: 12,
                    }}
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
                    style={{
                      width: 70,
                      padding: "4px 6px",
                      borderRadius: 3,
                      border: "1px solid #555",
                      background: "#1e1e1e",
                      color:
                        line.adjust > 0
                          ? "#22c55e"
                          : line.adjust < 0
                          ? "#ef4444"
                          : "#e0e0e0",
                      textAlign: "right",
                      fontSize: 13,
                      fontWeight: 600,
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
                        ? "#ef4444"
                        : line.adjust !== 0
                        ? "#fff"
                        : "#bbb",
                  }}
                >
                  {line.new_on_hand}
                </td>
                <td
                  style={{
                    padding: "6px 12px",
                    textAlign: "right",
                    fontSize: 13,
                    color: "#888",
                  }}
                >
                  {line.unit_cost.toFixed(2)}
                </td>
                <td style={{ padding: "4px" }}>
                  <button
                    onClick={() => removeLine(idx)}
                    style={{
                      background: "none",
                      border: "none",
                      color: "#666",
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
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: 16,
        }}
      >
        <div style={{ fontSize: 13, color: message.startsWith("Error") ? "#ef4444" : "#22c55e" }}>
          {message}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={applyAdjustments}
            disabled={!hasChanges || applying}
            style={{
              padding: "8px 24px",
              borderRadius: 4,
              border: "none",
              background: hasChanges ? "#2563eb" : "#333",
              color: hasChanges ? "#fff" : "#666",
              cursor: hasChanges ? "pointer" : "default",
              fontSize: 14,
              fontWeight: 600,
            }}
          >
            {applying ? "Applying..." : "Apply"}
          </button>
          <button
            onClick={() => {
              setLines([]);
              setMessage("");
            }}
            style={{
              padding: "8px 16px",
              borderRadius: 4,
              border: "1px solid #555",
              background: "transparent",
              color: "#ccc",
              cursor: "pointer",
              fontSize: 14,
            }}
          >
            Clear
          </button>
        </div>
      </div>
    </div>
  );
}

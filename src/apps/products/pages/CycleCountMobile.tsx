/**
 * CycleCountMobile — phone-sized cycle count page.
 * Barcode/QR scanning, location display, expected vs actual count.
 * Standalone page at /cycle-count — no login sidebar, no desktop chrome.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";

interface CountEntry {
  item_id: number;
  ida: string;
  name: string;
  warehouse_name: string;
  location: string;
  expected: number;
  actual: number | null;
  variance: number;
  layer_id: number;
  warehouse_id: number;
}

export default function CycleCountMobile() {
  const [entries, setEntries] = useState<CountEntry[]>([]);
  const [scanInput, setScanInput] = useState("");
  const [scanning, setScanning] = useState(false);
  const [message, setMessage] = useState("");
  const [applying, setApplying] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const scanRef = useRef<HTMLInputElement>(null);

  // Focus scan input on mount
  useEffect(() => {
    scanRef.current?.focus();
  }, []);

  const getToken = () =>
    document.cookie
      .split("; ")
      .find((c) => c.startsWith("access_token="))
      ?.split("=")[1];

  // Look up item by scan (ida, barcode, or QR code content)
  const lookupItem = useCallback(async (code: string) => {
    if (!code.trim()) return;
    setScanning(true);
    setMessage("");

    try {
      const token = getToken();
      // Search by ida/sku
      const resp = await fetch(
        `/wcapi/get/?model_name=item&keyword=${encodeURIComponent(code.trim())}&limit=1`,
        {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          credentials: "include",
        }
      );
      const result = await resp.json();
      const items = result.data || result.results || [];

      if (!items.length) {
        setMessage(`Not found: ${code}`);
        setScanning(false);
        return;
      }

      const item = items[0];
      const itemId = item.id;

      // Already in list?
      if (entries.some((e) => e.item_id === itemId)) {
        setMessage(`Already in count list: ${item.ida || code}`);
        setScanning(false);
        return;
      }

      // Get layers for this item
      const layerResp = await fetch(
        `/api/products/inventory/layers/?item_id=${itemId}`,
        {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          credentials: "include",
        }
      );
      const layerResult = await layerResp.json();
      const layers = (layerResult.data || []).filter((l: any) => l.remaining > 0);

      if (layers.length === 0) {
        // No layers — add with expected 0
        setEntries((prev) => [
          {
            item_id: itemId,
            ida: item.ida || code,
            name: item.name || "",
            warehouse_name: "Default",
            location: "",
            expected: 0,
            actual: null,
            variance: 0,
            layer_id: 0,
            warehouse_id: 0,
          },
          ...prev,
        ]);
      } else {
        // Add one entry per layer
        const newEntries: CountEntry[] = layers.map((l: any) => ({
          item_id: itemId,
          ida: item.ida || code,
          name: item.name || "",
          warehouse_name: l.warehouse_name || l.warehouse_code || "Default",
          location: l.lot || "",
          expected: l.remaining,
          actual: null,
          variance: 0,
          layer_id: l.id,
          warehouse_id: l.warehouse_id,
        }));
        setEntries((prev) => [...newEntries, ...prev]);
      }

      setMessage(`Added: ${item.ida || code}`);
    } catch (err: any) {
      setMessage(`Error: ${err.message}`);
    }
    setScanning(false);
    setScanInput("");
    scanRef.current?.focus();
  }, [entries]);

  // Camera barcode scanning using BarcodeDetector API
  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
        setCameraActive(true);

        // Use BarcodeDetector if available
        if ("BarcodeDetector" in window) {
          const detector = new (window as any).BarcodeDetector({
            formats: ["qr_code", "ean_13", "ean_8", "code_128", "code_39", "upc_a", "upc_e"],
          });

          const scan = async () => {
            if (!videoRef.current || !cameraActive) return;
            try {
              const barcodes = await detector.detect(videoRef.current);
              if (barcodes.length > 0) {
                const code = barcodes[0].rawValue;
                stopCamera();
                lookupItem(code);
                return;
              }
            } catch {}
            if (cameraActive) requestAnimationFrame(scan);
          };
          requestAnimationFrame(scan);
        }
      }
    } catch {
      setMessage("Camera not available");
    }
  }, [cameraActive, lookupItem]);

  const stopCamera = useCallback(() => {
    if (videoRef.current?.srcObject) {
      (videoRef.current.srcObject as MediaStream).getTracks().forEach((t) => t.stop());
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
  }, []);

  // Update actual count
  const updateActual = useCallback((idx: number, value: number | null) => {
    setEntries((prev) =>
      prev.map((e, i) => {
        if (i !== idx) return e;
        return {
          ...e,
          actual: value,
          variance: value !== null ? value - e.expected : 0,
        };
      })
    );
  }, []);

  // Apply all variances
  const applyAll = useCallback(async () => {
    const diffs = entries.filter((e) => e.actual !== null && e.variance !== 0);
    if (diffs.length === 0) {
      setMessage("No variances to apply.");
      return;
    }

    setApplying(true);
    setMessage("");

    try {
      const token = getToken();
      const byWarehouse: Record<number, any[]> = {};
      for (const d of diffs) {
        const wid = d.warehouse_id || 0;
        if (!byWarehouse[wid]) byWarehouse[wid] = [];
        byWarehouse[wid].push({
          item_id: d.item_id,
          qty: d.variance,
          reason: "cycle_count",
          notes: `Mobile count: expected=${d.expected}, counted=${d.actual}, variance=${d.variance}`,
        });
      }

      let total = 0;
      for (const [whId, lines] of Object.entries(byWarehouse)) {
        const resp = await fetch("/api/products/inventory/adjust/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          credentials: "include",
          body: JSON.stringify({ warehouse_id: Number(whId), lines }),
        });
        const result = await resp.json();
        total += (result.data?.applied || 0);
      }

      setMessage(`Applied ${total} adjustment(s).`);
      setEntries((prev) =>
        prev.map((e) => ({
          ...e,
          expected: e.actual !== null && e.variance !== 0 ? e.actual : e.expected,
          actual: null,
          variance: 0,
        }))
      );
    } catch (err: any) {
      setMessage(`Error: ${err.message}`);
    }
    setApplying(false);
  }, [entries]);

  const hasVariances = entries.some((e) => e.actual !== null && e.variance !== 0);

  return (
    <div
      style={{
        maxWidth: 480,
        margin: "0 auto",
        padding: "12px 8px",
        fontFamily: "system-ui, sans-serif",
        minHeight: "100vh",
        background: "#0f0f0f",
        color: "#e0e0e0",
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h1 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>Cycle Count</h1>
        <span style={{ fontSize: 11, color: "#888" }}>
          {entries.length} item{entries.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Scan bar */}
      <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
        <input
          ref={scanRef}
          type="text"
          inputMode="search"
          placeholder="Scan or type item..."
          value={scanInput}
          onChange={(e) => setScanInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              lookupItem(scanInput);
            }
          }}
          style={{
            flex: 1,
            padding: "10px 12px",
            borderRadius: 8,
            border: "1px solid #444",
            background: "#1a1a1a",
            color: "#e0e0e0",
            fontSize: 16,
          }}
        />
        <button
          onClick={() => (cameraActive ? stopCamera() : startCamera())}
          style={{
            padding: "10px 14px",
            borderRadius: 8,
            border: "none",
            background: cameraActive ? "#ef4444" : "#2563eb",
            color: "#fff",
            fontSize: 18,
            cursor: "pointer",
          }}
          title={cameraActive ? "Stop camera" : "Scan barcode"}
        >
          {cameraActive ? "X" : "\u{1F4F7}"}
        </button>
      </div>

      {/* Camera preview */}
      {cameraActive && (
        <div style={{ marginBottom: 8, borderRadius: 8, overflow: "hidden", background: "#000" }}>
          <video
            ref={videoRef}
            style={{ width: "100%", maxHeight: 200, objectFit: "cover" }}
            playsInline
            muted
          />
        </div>
      )}

      {/* Message */}
      {message && (
        <div
          style={{
            padding: "6px 10px",
            marginBottom: 8,
            borderRadius: 6,
            fontSize: 12,
            background: message.startsWith("Error") ? "#7f1d1d" : "#14532d",
            color: message.startsWith("Error") ? "#fca5a5" : "#86efac",
          }}
        >
          {message}
        </div>
      )}

      {/* Count cards */}
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {entries.map((entry, idx) => (
          <div
            key={`${entry.item_id}-${entry.layer_id}-${idx}`}
            style={{
              padding: "10px 12px",
              borderRadius: 8,
              border: `1px solid ${
                entry.variance > 0 ? "#166534" : entry.variance < 0 ? "#7f1d1d" : "#333"
              }`,
              background:
                entry.variance !== 0
                  ? entry.variance > 0
                    ? "rgba(34,197,94,0.06)"
                    : "rgba(239,68,68,0.06)"
                  : "#1a1a1a",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
              <span style={{ fontWeight: 700, fontSize: 14 }}>{entry.ida}</span>
              <span style={{ fontSize: 11, color: "#888" }}>{entry.warehouse_name}</span>
            </div>
            <div style={{ fontSize: 12, color: "#999", marginBottom: 6 }}>
              {entry.name}
              {entry.location && <span style={{ marginLeft: 8, color: "#666" }}>Loc: {entry.location}</span>}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 10, color: "#666", textTransform: "uppercase" }}>Expected</div>
                <div style={{ fontSize: 20, fontWeight: 700, fontFamily: "monospace" }}>{entry.expected}</div>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 10, color: "#666", textTransform: "uppercase" }}>Actual</div>
                <input
                  type="number"
                  inputMode="numeric"
                  value={entry.actual ?? ""}
                  placeholder="-"
                  onChange={(e) => {
                    const v = e.target.value;
                    updateActual(idx, v === "" ? null : Number(v));
                  }}
                  style={{
                    width: "100%",
                    padding: "6px 8px",
                    borderRadius: 6,
                    border: "1px solid #555",
                    background: "#0f0f0f",
                    color: "#fff",
                    fontSize: 20,
                    fontWeight: 700,
                    fontFamily: "monospace",
                    textAlign: "center",
                  }}
                />
              </div>
              <div style={{ width: 60, textAlign: "right" }}>
                <div style={{ fontSize: 10, color: "#666", textTransform: "uppercase" }}>Variance</div>
                <div
                  style={{
                    fontSize: 20,
                    fontWeight: 700,
                    fontFamily: "monospace",
                    color:
                      entry.variance > 0 ? "#22c55e" : entry.variance < 0 ? "#ef4444" : "#555",
                  }}
                >
                  {entry.actual !== null
                    ? `${entry.variance > 0 ? "+" : ""}${entry.variance}`
                    : "-"}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {entries.length === 0 && (
        <div
          style={{
            textAlign: "center",
            padding: 40,
            color: "#555",
            fontSize: 14,
          }}
        >
          Scan an item barcode or type an item number to start counting.
        </div>
      )}

      {/* Apply button — fixed at bottom */}
      {entries.length > 0 && (
        <div style={{ position: "sticky", bottom: 0, padding: "12px 0", background: "#0f0f0f" }}>
          <button
            onClick={applyAll}
            disabled={!hasVariances || applying}
            style={{
              width: "100%",
              padding: "14px 0",
              borderRadius: 10,
              border: "none",
              background: hasVariances ? "#2563eb" : "#222",
              color: hasVariances ? "#fff" : "#555",
              fontSize: 16,
              fontWeight: 700,
              cursor: hasVariances ? "pointer" : "default",
            }}
          >
            {applying ? "Applying..." : `Apply ${entries.filter((e) => e.actual !== null && e.variance !== 0).length} Variance(s)`}
          </button>
        </div>
      )}
    </div>
  );
}

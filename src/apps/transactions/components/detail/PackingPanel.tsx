/**
 * PackingPanel — Pick, pack, and ship workflow for orders.
 *
 * Three-step flow:
 *   1. Pick: show order lines with qty to pick, sorted by warehouse/bin
 *   2. Pack: assign picked items to boxes, capture weight per box
 *   3. Ship: enter carrier/tracking, confirm → creates invoice via conversion chain
 *
 * quantity.active on the order line = ordered.
 * quantity.remaining on the order line = not yet shipped.
 * quantity.active on the resulting invoice line = shipped.
 * The document type gives the quantity its meaning.
 *
 * Backend: apps/transactions/services/shipping.py
 *   generate_pick_list(order_id) → pick list sorted by warehouse/bin
 *   confirm_pack(order_id, packed_lines) → records box contents in metadata
 *   ship_order(order_id, shipping_data) → order→invoice conversion = ship event
 *
 * LastChecked: 2026-08-05 | WhereUsed: Order detail | WhoCreated: Bill+Claude
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useScale, type ScaleStatus } from '@/hooks/useScale';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PickLine {
  line_id: number;
  item_id: number | null;
  item_ida: string;
  item_name: string;
  qty: number;
  bin_location: string;
  warehouse: string;
  line_number: number;
}

interface BoxLine {
  line_id: number;
  item_ida: string;
  item_name: string;
  qty_packed: number;
}

interface Box {
  id: number;
  label: string;
  weight: string;
  lines: BoxLine[];
}

interface PackingPanelProps {
  orderId: number;
  orderIda?: string;
  onComplete?: () => void;
  onClose?: () => void;
}

// ---------------------------------------------------------------------------
// API helper
// ---------------------------------------------------------------------------

async function callManage(action: string, params: Record<string, unknown>): Promise<any> {
  const { default: apiClient } = await import('@/api/axios');
  const res = await apiClient.post('/wcapi/manage/', { action, params });
  return res.data?.data;
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const S = {
  panel: {
    background: '#1a1a2a', color: '#ddd', borderRadius: 8,
    border: '1px solid #333', overflow: 'hidden',
  } as React.CSSProperties,
  header: {
    padding: '10px 16px', borderBottom: '1px solid #333',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  } as React.CSSProperties,
  title: { fontWeight: 700, fontSize: 15, color: '#88ccff' } as React.CSSProperties,
  step: {
    display: 'inline-flex', alignItems: 'center', gap: 6,
    padding: '3px 10px', borderRadius: 12, fontSize: 12, fontWeight: 600,
  } as React.CSSProperties,
  body: { padding: '12px 16px', maxHeight: 500, overflowY: 'auto' } as React.CSSProperties,
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 } as React.CSSProperties,
  th: {
    textAlign: 'left' as const, padding: '6px 8px', borderBottom: '1px solid #444',
    color: '#999', fontSize: 11, fontWeight: 700, textTransform: 'uppercase' as const,
  },
  td: { padding: '6px 8px', borderBottom: '1px solid #2a2a3a' } as React.CSSProperties,
  btn: {
    padding: '6px 16px', borderRadius: 4, cursor: 'pointer',
    fontSize: 13, fontWeight: 600, border: 'none',
  } as React.CSSProperties,
  btnPrimary: { background: '#2563eb', color: '#fff' } as React.CSSProperties,
  btnDefault: { background: 'rgba(255,255,255,0.08)', color: '#ccc', border: '1px solid #555' } as React.CSSProperties,
  btnSuccess: { background: '#16a34a', color: '#fff' } as React.CSSProperties,
  footer: {
    padding: '10px 16px', borderTop: '1px solid #333',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8,
  } as React.CSSProperties,
  input: {
    background: '#2a2a3a', border: '1px solid #555', borderRadius: 4,
    padding: '4px 8px', color: '#ddd', fontSize: 13,
  } as React.CSSProperties,
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function PackingPanel({ orderId, orderIda, onComplete, onClose }: PackingPanelProps) {
  const [step, setStep] = useState<'pick' | 'pack' | 'ship'>('pick');
  const [pickList, setPickList] = useState<PickLine[]>([]);
  const [pickedLines, setPickedLines] = useState<Set<number>>(new Set());
  const [boxes, setBoxes] = useState<Box[]>([]);
  const [activeBoxId, setActiveBoxId] = useState<number>(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [shipResult, setShipResult] = useState<any>(null);

  // Scale — same algorithm as WC2 PkScaleProcess
  const scale = useScale();

  // Ship form
  const [carrier, setCarrier] = useState('');
  const [trackingNumber, setTrackingNumber] = useState('');
  const [shipDate, setShipDate] = useState(new Date().toISOString().slice(0, 10));
  const [freightCost, setFreightCost] = useState('');

  // Load pick list on mount
  useEffect(() => {
    setLoading(true);
    setError('');
    callManage('generate_pick_list', { order_id: orderId })
      .then((data) => {
        const list = Array.isArray(data) ? data : data?.pick_list || [];
        setPickList(list);
        // Start with one empty box
        setBoxes([{ id: 1, label: 'Box 1', weight: '', lines: [] }]);
      })
      .catch((e) => setError(e?.response?.data?.message || 'Failed to load pick list'))
      .finally(() => setLoading(false));
  }, [orderId]);

  // Toggle pick checkbox
  const togglePicked = useCallback((lineId: number) => {
    setPickedLines(prev => {
      const next = new Set(prev);
      if (next.has(lineId)) next.delete(lineId);
      else next.add(lineId);
      return next;
    });
  }, []);

  // Pick all
  const pickAll = useCallback(() => {
    setPickedLines(new Set(pickList.map(l => l.line_id)));
  }, [pickList]);

  // Add picked lines to active box
  const addToBox = useCallback(() => {
    const activeBox = boxes.find(b => b.id === activeBoxId);
    if (!activeBox) return;

    const newBoxLines: BoxLine[] = [];
    for (const pl of pickList) {
      if (!pickedLines.has(pl.line_id)) continue;
      // Check if already in any box
      const alreadyPacked = boxes.some(b => b.lines.some(bl => bl.line_id === pl.line_id));
      if (alreadyPacked) continue;
      newBoxLines.push({
        line_id: pl.line_id,
        item_ida: pl.item_ida,
        item_name: pl.item_name,
        qty_packed: pl.qty,
      });
    }

    if (newBoxLines.length === 0) return;

    setBoxes(prev => prev.map(b =>
      b.id === activeBoxId
        ? { ...b, lines: [...b.lines, ...newBoxLines] }
        : b
    ));
  }, [pickList, pickedLines, boxes, activeBoxId]);

  // Add new box
  const addBox = useCallback(() => {
    const nextId = Math.max(0, ...boxes.map(b => b.id)) + 1;
    setBoxes(prev => [...prev, { id: nextId, label: `Box ${nextId}`, weight: '', lines: [] }]);
    setActiveBoxId(nextId);
  }, [boxes]);

  // Remove line from box
  const removeFromBox = useCallback((boxId: number, lineId: number) => {
    setBoxes(prev => prev.map(b =>
      b.id === boxId
        ? { ...b, lines: b.lines.filter(l => l.line_id !== lineId) }
        : b
    ));
  }, []);

  // Update box weight
  const setBoxWeight = useCallback((boxId: number, weight: string) => {
    setBoxes(prev => prev.map(b => b.id === boxId ? { ...b, weight } : b));
  }, []);

  // Update qty packed for a line in a box
  const setQtyPacked = useCallback((boxId: number, lineId: number, qty: number) => {
    setBoxes(prev => prev.map(b =>
      b.id === boxId
        ? { ...b, lines: b.lines.map(l => l.line_id === lineId ? { ...l, qty_packed: qty } : l) }
        : b
    ));
  }, []);

  // Confirm pack — send box contents to backend
  const confirmPack = useCallback(async () => {
    const allPackedLines = boxes.flatMap(box =>
      box.lines.map(l => ({
        line_id: l.line_id,
        qty_packed: l.qty_packed,
        carrier,
        tracking_number: trackingNumber,
        weight: parseFloat(box.weight) || null,
      }))
    );
    if (allPackedLines.length === 0) { setError('No items packed'); return; }

    setLoading(true);
    setError('');
    try {
      await callManage('confirm_pack', { order_id: orderId, packed_lines: allPackedLines });
      setStep('ship');
    } catch (e: any) {
      setError(e?.response?.data?.message || 'Pack confirmation failed');
    } finally {
      setLoading(false);
    }
  }, [boxes, orderId, carrier, trackingNumber]);

  // Ship — order→invoice conversion
  const shipOrder = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await callManage('ship_order', {
        order_id: orderId,
        shipping_data: {
          carrier,
          tracking_number: trackingNumber,
          ship_date: shipDate,
          freight_cost: parseFloat(freightCost) || 0,
        },
      });
      setShipResult(result);
    } catch (e: any) {
      setError(e?.response?.data?.message || 'Ship failed');
    } finally {
      setLoading(false);
    }
  }, [orderId, carrier, trackingNumber, shipDate, freightCost]);

  // Summary counts
  const totalToPick = pickList.length;
  const totalPicked = pickedLines.size;
  const totalPacked = boxes.reduce((sum, b) => sum + b.lines.length, 0);
  const allPacked = totalPacked >= totalToPick && totalToPick > 0;

  const stepColor = (s: string) => s === step ? '#2563eb' : '#444';

  // ── Ship complete ──
  if (shipResult) {
    return (
      <div style={S.panel}>
        <div style={S.header}>
          <span style={S.title}>Shipment Complete</span>
        </div>
        <div style={{ ...S.body, textAlign: 'center', padding: '32px 16px' }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>&#x2714;</div>
          <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>
            Invoice {shipResult.invoice_ida || `#${shipResult.invoice_id}`} created
          </div>
          <div style={{ color: '#999', fontSize: 13 }}>
            {shipResult.lines_shipped} lines shipped
            {shipResult.lines_remaining > 0 &&
              ` · ${shipResult.lines_remaining} lines remaining on order`}
          </div>
          {trackingNumber && (
            <div style={{ marginTop: 8, color: '#88ccff', fontSize: 13 }}>
              Tracking: {trackingNumber}
            </div>
          )}
        </div>
        <div style={S.footer}>
          <div />
          <button style={{ ...S.btn, ...S.btnPrimary }} onClick={() => { onComplete?.(); onClose?.(); }}>
            Done
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={S.panel}>
      {/* Header with step indicator */}
      <div style={S.header}>
        <span style={S.title}>
          Pack &amp; Ship — {orderIda || `Order #${orderId}`}
        </span>
        <div style={{ display: 'flex', gap: 4 }}>
          {(['pick', 'pack', 'ship'] as const).map((s, i) => (
            <span key={s} style={{
              ...S.step,
              background: stepColor(s),
              color: s === step ? '#fff' : '#888',
              cursor: s === 'pick' || (s === 'pack' && totalPicked > 0) ? 'pointer' : 'default',
            }}
            onClick={() => {
              if (s === 'pick') setStep('pick');
              if (s === 'pack' && totalPicked > 0) setStep('pack');
            }}
            >
              {i + 1}. {s.charAt(0).toUpperCase() + s.slice(1)}
            </span>
          ))}
        </div>
        {onClose && (
          <button onClick={onClose} style={{
            background: 'none', border: 'none', color: '#888', cursor: 'pointer', fontSize: 18,
          }}>&times;</button>
        )}
      </div>

      {/* Error bar */}
      {error && (
        <div style={{ padding: '6px 16px', background: 'rgba(255,60,60,0.15)', color: '#ff6b6b', fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* STEP 1: PICK */}
      {step === 'pick' && (
        <>
          <div style={S.body}>
            {loading && <div style={{ color: '#888', padding: 16 }}>Loading pick list...</div>}
            {!loading && pickList.length === 0 && (
              <div style={{ color: '#888', padding: 16, textAlign: 'center' }}>
                No lines to pick — all items shipped or order empty.
              </div>
            )}
            {!loading && pickList.length > 0 && (
              <table style={S.table}>
                <thead>
                  <tr>
                    <th style={{ ...S.th, width: 32 }}>
                      <input type="checkbox"
                        checked={totalPicked === totalToPick}
                        onChange={() => totalPicked === totalToPick ? setPickedLines(new Set()) : pickAll()}
                      />
                    </th>
                    <th style={S.th}>Item</th>
                    <th style={S.th}>Description</th>
                    <th style={{ ...S.th, textAlign: 'right' }}>Qty</th>
                    <th style={S.th}>Warehouse</th>
                    <th style={S.th}>Bin</th>
                  </tr>
                </thead>
                <tbody>
                  {pickList.map(pl => (
                    <tr key={pl.line_id}
                      onClick={() => togglePicked(pl.line_id)}
                      style={{ cursor: 'pointer', background: pickedLines.has(pl.line_id) ? 'rgba(37,99,235,0.1)' : 'transparent' }}
                    >
                      <td style={S.td}>
                        <input type="checkbox" checked={pickedLines.has(pl.line_id)} readOnly />
                      </td>
                      <td style={{ ...S.td, fontFamily: 'monospace', color: '#88ccff' }}>{pl.item_ida}</td>
                      <td style={S.td}>{pl.item_name}</td>
                      <td style={{ ...S.td, textAlign: 'right', fontWeight: 600 }}>{pl.qty}</td>
                      <td style={{ ...S.td, color: '#999' }}>{pl.warehouse}</td>
                      <td style={{ ...S.td, color: '#ccc', fontWeight: 600 }}>{pl.bin_location}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <div style={S.footer}>
            <span style={{ fontSize: 13, color: '#999' }}>
              {totalPicked} of {totalToPick} picked
            </span>
            <button
              style={{ ...S.btn, ...S.btnPrimary }}
              disabled={totalPicked === 0}
              onClick={() => setStep('pack')}
            >
              Pack {totalPicked} items
            </button>
          </div>
        </>
      )}

      {/* STEP 2: PACK */}
      {step === 'pack' && (
        <>
          <div style={S.body}>
            {/* Scale status bar */}
            <ScaleBar scale={scale} onReadWeight={(w) => setBoxWeight(activeBoxId, String(w))} />

            {/* Box tabs */}
            <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
              {boxes.map(box => (
                <button key={box.id}
                  onClick={() => setActiveBoxId(box.id)}
                  style={{
                    ...S.btn,
                    ...(box.id === activeBoxId ? S.btnPrimary : S.btnDefault),
                    padding: '4px 12px', fontSize: 12,
                  }}
                >
                  {box.label} ({box.lines.length})
                </button>
              ))}
              <button onClick={addBox} style={{ ...S.btn, ...S.btnDefault, padding: '4px 8px', fontSize: 12 }}>
                + Box
              </button>
            </div>

            {/* Add picked items to active box */}
            {pickedLines.size > 0 && (
              <div style={{ marginBottom: 12 }}>
                <button onClick={addToBox} style={{ ...S.btn, ...S.btnDefault, fontSize: 12 }}>
                  Add picked items to {boxes.find(b => b.id === activeBoxId)?.label || 'box'}
                </button>
              </div>
            )}

            {/* Active box contents */}
            {boxes.filter(b => b.id === activeBoxId).map(box => (
              <div key={box.id}>
                {/* Weight input */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                  <label style={{ fontSize: 12, color: '#999' }}>Weight:</label>
                  <input
                    style={{ ...S.input, width: 80 }}
                    type="number" step="0.1" placeholder="lbs"
                    value={box.weight}
                    onChange={e => setBoxWeight(box.id, e.target.value)}
                  />
                </div>

                {box.lines.length === 0 ? (
                  <div style={{ color: '#666', fontSize: 13, padding: '16px 0', textAlign: 'center' }}>
                    No items in this box. Pick items first, then click "Add picked items."
                  </div>
                ) : (
                  <table style={S.table}>
                    <thead>
                      <tr>
                        <th style={S.th}>Item</th>
                        <th style={S.th}>Description</th>
                        <th style={{ ...S.th, textAlign: 'right', width: 80 }}>Qty</th>
                        <th style={{ ...S.th, width: 32 }}></th>
                      </tr>
                    </thead>
                    <tbody>
                      {box.lines.map(bl => (
                        <tr key={bl.line_id}>
                          <td style={{ ...S.td, fontFamily: 'monospace', color: '#88ccff' }}>{bl.item_ida}</td>
                          <td style={S.td}>{bl.item_name}</td>
                          <td style={{ ...S.td, textAlign: 'right' }}>
                            <input
                              type="number" min="0" step="1"
                              value={bl.qty_packed}
                              onChange={e => setQtyPacked(box.id, bl.line_id, parseFloat(e.target.value) || 0)}
                              style={{ ...S.input, width: 60, textAlign: 'right' }}
                            />
                          </td>
                          <td style={S.td}>
                            <button
                              onClick={() => removeFromBox(box.id, bl.line_id)}
                              style={{ background: 'none', border: 'none', color: '#ff6b6b', cursor: 'pointer', fontSize: 14 }}
                              title="Remove from box"
                            >&times;</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            ))}

            {/* All boxes summary */}
            {boxes.length > 1 && (
              <div style={{ marginTop: 12, fontSize: 12, color: '#999' }}>
                {boxes.map(b => `${b.label}: ${b.lines.length} items${b.weight ? ', ' + b.weight + ' lbs' : ''}`).join(' · ')}
              </div>
            )}
          </div>
          <div style={S.footer}>
            <button style={{ ...S.btn, ...S.btnDefault }} onClick={() => setStep('pick')}>
              Back to Pick
            </button>
            <span style={{ fontSize: 13, color: '#999' }}>
              {totalPacked} items in {boxes.filter(b => b.lines.length > 0).length} box(es)
            </span>
            <button
              style={{ ...S.btn, ...S.btnSuccess }}
              disabled={totalPacked === 0 || loading}
              onClick={confirmPack}
            >
              {loading ? 'Confirming...' : 'Confirm Pack & Ship'}
            </button>
          </div>
        </>
      )}

      {/* STEP 3: SHIP */}
      {step === 'ship' && (
        <>
          <div style={S.body}>
            <div style={{ fontSize: 13, color: '#999', marginBottom: 16 }}>
              Pack confirmed. Enter shipping details to create the invoice.
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '10px 12px', alignItems: 'center', maxWidth: 400 }}>
              <label style={{ fontSize: 13, color: '#999' }}>Carrier:</label>
              <input style={S.input} value={carrier} onChange={e => setCarrier(e.target.value)} placeholder="UPS, FedEx, USPS..." />

              <label style={{ fontSize: 13, color: '#999' }}>Tracking #:</label>
              <input style={S.input} value={trackingNumber} onChange={e => setTrackingNumber(e.target.value)} placeholder="Tracking number" />

              <label style={{ fontSize: 13, color: '#999' }}>Ship Date:</label>
              <input style={S.input} type="date" value={shipDate} onChange={e => setShipDate(e.target.value)} />

              <label style={{ fontSize: 13, color: '#999' }}>Freight Cost:</label>
              <input style={S.input} type="number" step="0.01" value={freightCost} onChange={e => setFreightCost(e.target.value)} placeholder="0.00" />
            </div>

            {/* Box summary */}
            <div style={{ marginTop: 16, padding: '10px 12px', background: '#2a2a3a', borderRadius: 6, fontSize: 13 }}>
              <div style={{ fontWeight: 600, marginBottom: 6, color: '#88ccff' }}>Packed:</div>
              {boxes.filter(b => b.lines.length > 0).map(b => (
                <div key={b.id} style={{ color: '#ccc' }}>
                  {b.label}: {b.lines.map(l => `${l.item_ida} ×${l.qty_packed}`).join(', ')}
                  {b.weight && <span style={{ color: '#999' }}> — {b.weight} lbs</span>}
                </div>
              ))}
            </div>
          </div>
          <div style={S.footer}>
            <button style={{ ...S.btn, ...S.btnDefault }} onClick={() => setStep('pack')}>
              Back to Pack
            </button>
            <button
              style={{ ...S.btn, ...S.btnSuccess }}
              disabled={loading}
              onClick={shipOrder}
            >
              {loading ? 'Shipping...' : 'Ship Order'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ScaleBar — live scale status, connect/tare buttons
// ---------------------------------------------------------------------------

const SCALE_COLORS: Record<ScaleStatus, string> = {
  ok: '#16a34a',
  mismatch: '#dc2626',
  negative_tare: '#dc2626',
  no_reading: '#d97706',
  disconnected: '#666',
  connecting: '#2563eb',
};

function ScaleBar({ scale, onReadWeight }: {
  scale: ReturnType<typeof useScale>;
  onReadWeight: (weight: number) => void;
}) {
  const color = SCALE_COLORS[scale.status] || '#666';

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '6px 10px', marginBottom: 10,
      background: '#2a2a3a', borderRadius: 6,
      border: `1px solid ${color}33`,
    }}>
      {/* Status dot */}
      <div style={{
        width: 8, height: 8, borderRadius: '50%',
        background: color, flexShrink: 0,
      }} />

      {scale.connected ? (
        <>
          {/* Live weight */}
          <span style={{ fontFamily: 'monospace', fontSize: 18, fontWeight: 700, color, minWidth: 80 }}>
            {scale.weightScale.toFixed(3)}
          </span>
          <span style={{ fontSize: 11, color: '#888' }}>lbs</span>

          {/* Deviation */}
          {scale.status === 'mismatch' && (
            <span style={{ fontSize: 12, color: '#ff6b6b', marginLeft: 8 }}>
              {scale.message}
            </span>
          )}
          {scale.status === 'ok' && scale.weightScale > 0 && (
            <span style={{ fontSize: 12, color: '#4ade80' }}>OK</span>
          )}

          {/* Stable indicator */}
          {scale.stable && (
            <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>STABLE</span>
          )}

          <div style={{ flex: 1 }} />

          {/* Tare button */}
          <button
            onClick={scale.tare}
            style={{ ...S.btn, ...S.btnDefault, padding: '2px 8px', fontSize: 11 }}
          >
            Tare
          </button>

          {/* Read weight into box */}
          <button
            onClick={() => onReadWeight(scale.weightScale)}
            style={{ ...S.btn, ...S.btnDefault, padding: '2px 8px', fontSize: 11 }}
            title="Set box weight from scale"
          >
            Read
          </button>

          {/* Disconnect */}
          <button
            onClick={scale.disconnect}
            style={{ ...S.btn, ...S.btnDefault, padding: '2px 8px', fontSize: 11 }}
          >
            Disconnect
          </button>
        </>
      ) : (
        <>
          <span style={{ fontSize: 12, color: '#888' }}>{scale.message}</span>
          <div style={{ flex: 1 }} />
          <button
            onClick={scale.connect}
            style={{ ...S.btn, ...S.btnPrimary, padding: '3px 12px', fontSize: 12 }}
          >
            Connect Scale
          </button>
        </>
      )}
    </div>
  );
}

/**
 * useScale — Web Serial API hook for packing scale integration.
 *
 * Same algorithm as WC2 PkScaleProcess/PKWtScaleCalc:
 *   - Polls scale continuously via serial port
 *   - Sends "W\r" (or "H\r") command, reads weight back
 *   - Compares scale reading to expected weight (product + tare)
 *   - Reports status: ok | mismatch | negative_tare | no_reading | disconnected
 *   - Per-item delta check: weight change after scan vs expected item weight
 *
 * WC2 variables mapped to this hook:
 *   <>vrWeightScale      → weightScale     (live scale reading)
 *   <>vrWeightProduct     → weightProduct   (sum of unit weights × qty)
 *   <>vrWeightTare        → weightTare      (box weight = scale − product)
 *   <>vrWeightDeviation   → deviation       (product + tare − scale)
 *   <>vrWeightErrPC       → deviationPct    (deviation as %)
 *   <>wtPrecisionPC       → precisionPct    (allowed variance %)
 *   <>wtDitherFactor      → ditherFactor    (noise floor — readings below = 0)
 *   <>scanScaleItemWt     → lastScaleWeight (scale weight before last scan)
 *   <>itemWt              → expectedItemWt  (expected weight of item just scanned)
 *   <>itemDeltaWt         → itemDelta       (actual weight change from last scan)
 *   <>pkScaleComment      → status + message
 *
 * Serial config: 9600 baud, 8 data bits, 1 stop bit, no parity
 * (WC2 used 7 data bits + even parity on some scales — configurable via options)
 *
 * LastChecked: 2026-08-05 | WhereUsed: PackingPanel | WhoCreated: Bill+Claude
 */
import { useState, useRef, useCallback, useEffect } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ScaleStatus = 'disconnected' | 'connecting' | 'ok' | 'mismatch' | 'negative_tare' | 'no_reading';

export interface ScaleState {
  /** Live scale reading (lbs/kg) */
  weightScale: number;
  /** Expected product weight (sum of unit weights × qty scanned) */
  weightProduct: number;
  /** Tare weight (box/container weight) */
  weightTare: number;
  /** Deviation: product + tare − scale (should be ~0 when correct) */
  deviation: number;
  /** Deviation as percentage of scale weight */
  deviationPct: number;
  /** Weight change from last item scan */
  itemDelta: number;
  /** Item delta as percentage of expected item weight */
  itemDeltaPct: number;
  /** Scale status */
  status: ScaleStatus;
  /** Human-readable message */
  message: string;
  /** Whether scale is connected */
  connected: boolean;
  /** Stable reading (hasn't changed for stabilityCount polls) */
  stable: boolean;
}

export interface ScaleOptions {
  /** Baud rate (default 9600) */
  baudRate?: number;
  /** Data bits (default 8; WC2 used 7 on some scales) */
  dataBits?: 7 | 8;
  /** Stop bits (default 1) */
  stopBits?: 1 | 2;
  /** Parity (default 'none'; WC2 used 'even' on some scales) */
  parity?: 'none' | 'even' | 'odd';
  /** Command to send (default "W\r"; some scales use "H\r") */
  weightCommand?: string;
  /** Poll interval in ms (default 500 — WC2 used ~167ms / 10 ticks) */
  pollInterval?: number;
  /** Allowed weight variance percent (default 5) — WC2 <>wtPrecisionPC */
  precisionPct?: number;
  /** Noise floor — readings below this treated as 0 (default 0.05) — WC2 <>wtDitherFactor */
  ditherFactor?: number;
  /** Decimal precision for weight (default 3) — WC2 <>wtPrecision */
  precision?: number;
  /** Number of stable readings before declaring stable (default 6) */
  stabilityCount?: number;
}

const DEFAULTS: Required<ScaleOptions> = {
  baudRate: 9600,
  dataBits: 8,
  stopBits: 1,
  parity: 'none',
  weightCommand: 'W\r',
  pollInterval: 500,
  precisionPct: 5,
  ditherFactor: 0.05,
  precision: 3,
  stabilityCount: 6,
};

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useScale(options?: ScaleOptions) {
  const opts = { ...DEFAULTS, ...options };

  const [state, setState] = useState<ScaleState>({
    weightScale: 0, weightProduct: 0, weightTare: 0,
    deviation: 0, deviationPct: 0,
    itemDelta: 0, itemDeltaPct: 0,
    status: 'disconnected', message: 'Not connected', connected: false, stable: false,
  });

  const portRef = useRef<SerialPort | null>(null);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const writerRef = useRef<WritableStreamDefaultWriter<Uint8Array> | null>(null);
  const pollingRef = useRef<number | null>(null);
  const stableCountRef = useRef(0);
  const lastReadingRef = useRef(0);
  const lastScanWeightRef = useRef(0);
  const weightProductRef = useRef(0);
  const weightTareRef = useRef(0);
  const expectedItemWtRef = useRef(0);

  // ── Connect to scale ───────────────────────────────────────────────
  const connect = useCallback(async () => {
    if (!('serial' in navigator)) {
      setState(s => ({ ...s, status: 'disconnected', message: 'Web Serial API not available — use Chrome or Edge' }));
      return;
    }
    try {
      setState(s => ({ ...s, status: 'connecting', message: 'Requesting port...' }));
      const port = await (navigator as any).serial.requestPort();
      await port.open({
        baudRate: opts.baudRate,
        dataBits: opts.dataBits,
        stopBits: opts.stopBits,
        parity: opts.parity,
      });
      portRef.current = port;

      if (port.readable) {
        readerRef.current = port.readable.getReader();
      }
      if (port.writable) {
        writerRef.current = port.writable.getWriter();
      }

      setState(s => ({ ...s, status: 'ok', message: 'Connected', connected: true }));
      startPolling();
    } catch (e: any) {
      setState(s => ({
        ...s, status: 'disconnected', connected: false,
        message: e?.message || 'Failed to connect',
      }));
    }
  }, [opts.baudRate, opts.dataBits, opts.stopBits, opts.parity]);

  // ── Disconnect ─────────────────────────────────────────────────────
  const disconnect = useCallback(async () => {
    stopPolling();
    try {
      if (readerRef.current) { await readerRef.current.cancel(); readerRef.current = null; }
      if (writerRef.current) { writerRef.current.releaseLock(); writerRef.current = null; }
      if (portRef.current) { await portRef.current.close(); portRef.current = null; }
    } catch {}
    setState(s => ({ ...s, status: 'disconnected', message: 'Disconnected', connected: false, weightScale: 0 }));
  }, []);

  // ── Read one weight from scale ─────────────────────────────────────
  const readWeight = useCallback(async (): Promise<number | null> => {
    if (!writerRef.current || !readerRef.current) return null;

    const encoder = new TextEncoder();
    const cmd = encoder.encode(opts.weightCommand);

    try {
      await writerRef.current.write(cmd);

      // Read response — scale sends weight as ASCII string
      const { value } = await readerRef.current.read();
      if (!value) return null;

      const decoder = new TextDecoder();
      const text = decoder.decode(value).trim();
      // Parse first 12 chars as number (WC2: Substring 1..11)
      const numStr = text.substring(0, 12).trim();
      const weight = parseFloat(numStr);
      if (isNaN(weight)) return null;

      // Apply dither — readings below noise floor = 0
      return Math.abs(weight) < opts.ditherFactor ? 0 : round(weight, opts.precision);
    } catch {
      return null;
    }
  }, [opts.weightCommand, opts.ditherFactor, opts.precision]);

  // ── Poll loop ──────────────────────────────────────────────────────
  const poll = useCallback(async () => {
    const reading = await readWeight();
    if (reading === null) {
      setState(s => ({ ...s, status: 'no_reading', message: 'No reading from scale' }));
      return;
    }

    const prev = lastReadingRef.current;
    const product = weightProductRef.current;
    const tare = weightTareRef.current;

    // Stability detection (WC2: $cntStable / $cntChange)
    if (reading === prev) {
      stableCountRef.current = Math.min(stableCountRef.current + 1, opts.stabilityCount);
    } else {
      stableCountRef.current = 0;
    }
    lastReadingRef.current = reading;
    const stable = stableCountRef.current >= opts.stabilityCount;

    // Deviation (WC2: <>vrWeightDeviation = product + tare − scale)
    const deviation = round(product + tare - reading, opts.precision);
    const deviationPct = reading !== 0
      ? round(Math.abs(deviation / reading) * 100, 1)
      : (product === 0 ? 0 : 100);

    // Per-item delta (WC2: <>itemDeltaWt = scale − lastScanWeight)
    const itemDelta = round(reading - lastScanWeightRef.current, opts.precision);
    const expectedItem = expectedItemWtRef.current;
    const itemDeltaPct = expectedItem !== 0
      ? round(itemDelta / expectedItem * 100, 2)
      : 0;

    // Dither percent of total weight (WC2: <>wtDitherPC)
    const ditherPct = reading !== 0
      ? Math.abs(round(opts.ditherFactor / reading * 100, 1))
      : 0;

    // Status determination (WC2: PkScaleProcess case block)
    let status: ScaleStatus = 'ok';
    let message = 'OK';

    if (tare < -(opts.ditherFactor + reading * opts.precisionPct * 0.01) && tare !== 0) {
      status = 'negative_tare';
      message = 'Negative Tare';
    } else if (deviationPct > (opts.precisionPct + ditherPct) && reading > opts.ditherFactor) {
      status = 'mismatch';
      if (deviation > 0) {
        message = `Scale Under By: ${Math.abs(deviation).toFixed(opts.precision)} (${deviationPct.toFixed(1)}%)`;
      } else {
        message = `Scale Over By: ${Math.abs(deviation).toFixed(opts.precision)} (${deviationPct.toFixed(1)}%)`;
      }
    }

    setState({
      weightScale: reading,
      weightProduct: product,
      weightTare: tare,
      deviation, deviationPct,
      itemDelta, itemDeltaPct,
      status, message,
      connected: true, stable,
    });
  }, [readWeight, opts]);

  const startPolling = useCallback(() => {
    if (pollingRef.current) return;
    const id = window.setInterval(poll, opts.pollInterval);
    pollingRef.current = id;
  }, [poll, opts.pollInterval]);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  // ── Set expected product weight (called as items are scanned) ──────
  const setWeightProduct = useCallback((weight: number) => {
    weightProductRef.current = weight;
    setState(s => ({ ...s, weightProduct: weight }));
  }, []);

  // ── Tare (WC2: <>vrWeightTare = scale − product) ──────────────────
  const tare = useCallback(() => {
    const t = lastReadingRef.current - weightProductRef.current;
    weightTareRef.current = t;
    setState(s => ({ ...s, weightTare: t }));
  }, []);

  // ── Reset tare ─────────────────────────────────────────────────────
  const resetTare = useCallback(() => {
    weightTareRef.current = 0;
    setState(s => ({ ...s, weightTare: 0 }));
  }, []);

  // ── Record item scan (snapshot scale weight before, set expected) ──
  const recordItemScan = useCallback((expectedWeight: number) => {
    lastScanWeightRef.current = lastReadingRef.current;
    expectedItemWtRef.current = expectedWeight;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => { stopPolling(); };
  }, [stopPolling]);

  return {
    ...state,
    connect,
    disconnect,
    tare,
    resetTare,
    setWeightProduct,
    recordItemScan,
  };
}

// ---------------------------------------------------------------------------
// Util
// ---------------------------------------------------------------------------

function round(val: number, places: number): number {
  const factor = Math.pow(10, places);
  return Math.round(val * factor) / factor;
}

export default useScale;

/* LastChecked: 2026-08-04 | WhereUsed: PrivateRoute (global) | WhoCreated: Claude */
/**
 * ZoneTooltip — Shift+hover shows zone name, CSS class, and component file.
 *
 * Any element with data-zone will show a tooltip on Shift+hover.
 * Format: data-zone="zoneName | .cssClass | ComponentFile.tsx"
 *
 * Click the tooltip to copy the zone path to clipboard — paste into Help
 * for support. Part of the Shift-for-Help standard.
 *
 * Auto-hides after duration (default 3s). Duration configurable via
 * Setting purpose='ui_webclerk' → config.zone_tooltip_ms
 */
import { useEffect, useState, useCallback, useRef } from 'react';

const DEFAULT_DURATION_MS = 3000;

interface ZoneInfo {
  name: string;
  cssClass: string;
  file: string;
  x: number;
  y: number;
}

export default function ZoneTooltip() {
  const [zone, setZone] = useState<ZoneInfo | null>(null);
  const [copied, setCopied] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const copiedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const durationRef = useRef(DEFAULT_DURATION_MS);

  // Load duration from Setting on mount
  useEffect(() => {
    (async () => {
      try {
        const { getRecords } = await import('@/api/wcapi');
        const res = await getRecords('setting', { purpose: 'ui_webclerk', limit: 1 }) as any;
        const setting = (res?.results || [])[0];
        if (setting?.config?.zone_tooltip_ms) {
          durationRef.current = Number(setting.config.zone_tooltip_ms) || DEFAULT_DURATION_MS;
        }
      } catch {}
    })();
  }, []);

  const clearTimer = useCallback(() => {
    if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null; }
  }, []);

  const startTimer = useCallback(() => {
    clearTimer();
    timerRef.current = setTimeout(() => setZone(null), durationRef.current);
  }, [clearTimer]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!e.shiftKey) {
      if (zone) { setZone(null); clearTimer(); setCopied(false); }
      return;
    }

    // If tooltip is already showing, don't reposition — let user click it
    if (zone) return;

    // Walk up from target to find nearest data-zone
    let el = e.target as HTMLElement | null;
    while (el) {
      const attr = el.getAttribute('data-zone');
      if (attr) {
        const parts = attr.split('|').map(s => s.trim());
        const newName = parts[0] || '';
        // Position near cursor but clamp to viewport
        const x = Math.min(e.clientX + 12, window.innerWidth - 340);
        const y = Math.min(e.clientY + 12, window.innerHeight - 100);
        setZone({ name: newName, cssClass: parts[1] || '', file: parts[2] || '', x, y });
        setCopied(false);
        startTimer();
        return;
      }
      el = el.parentElement;
    }
  }, [zone, startTimer, clearTimer]);

  const handleKeyUp = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Shift') { setZone(null); clearTimer(); setCopied(false); }
  }, [clearTimer]);

  const handleCopy = useCallback(() => {
    if (!zone) return;
    const text = [zone.name, zone.cssClass, zone.file].filter(Boolean).join(' > ');
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      if (copiedTimerRef.current) clearTimeout(copiedTimerRef.current);
      copiedTimerRef.current = setTimeout(() => setCopied(false), 1500);
      // Reset auto-hide timer so user can see "Copied"
      clearTimer();
      timerRef.current = setTimeout(() => setZone(null), 2000);
    }).catch(() => {});
  }, [zone, clearTimer]);

  useEffect(() => {
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('keyup', handleKeyUp);
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('keyup', handleKeyUp);
      clearTimer();
    };
  }, [handleMouseMove, handleKeyUp, clearTimer]);

  if (!zone) return null;

  return (
    <div
      onClick={handleCopy}
      style={{
        position: 'fixed',
        left: zone.x,
        top: zone.y,
        zIndex: 99999,
        pointerEvents: 'auto',
        cursor: 'pointer',
        background: copied ? '#1a3a2a' : '#1a1a2e',
        color: '#e0e0e0',
        border: `1px solid ${copied ? '#4ade80' : '#444'}`,
        borderRadius: 6,
        padding: '6px 10px',
        fontSize: 12,
        fontFamily: 'monospace',
        lineHeight: 1.5,
        boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
        maxWidth: 320,
        whiteSpace: 'nowrap',
        transition: 'background 0.15s, border-color 0.15s',
      }}
    >
      <div style={{ color: copied ? '#4ade80' : '#9cdcfe', fontWeight: 700 }}>
        {copied ? 'Copied!' : zone.name}
      </div>
      {!copied && zone.cssClass && <div style={{ color: '#ce9178' }}>{zone.cssClass}</div>}
      {!copied && zone.file && <div style={{ color: '#888' }}>{zone.file}</div>}
      {!copied && <div style={{ color: '#666', fontSize: 10, marginTop: 2 }}>click to copy</div>}
    </div>
  );
}

/* LastChecked: 2026-09-11 | WhereUsed: TransactionItemSearch, LineCardRenderer, DataBrowser | WhoCreated: Claude */
/**
 * ItemCard — Quick-view card for item details.
 *
 * The middle layer between a search result row and the full item.detail record.
 * Shows image, identity, pricing, inventory — enough to decide "is this the right item?"
 * "Open Item" button launches full item.detail in a new window.
 *
 * Dismisses on click-outside, Escape, or scroll (same pattern as ItemImagePopup).
 */
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useWindowManager } from '@/context/WindowManagerContext';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ItemCardProps {
  /** Item IDA (e.g. "DEV-641") */
  ida: string;
  /** Anchor rectangle for positioning */
  anchorRect: DOMRect;
  /** Close callback */
  onClose: () => void;
}

interface ItemDetail {
  id?: number;
  ida?: string;
  name?: string;
  sku?: string;
  description?: string;
  kind?: string;
  uom?: string;
  vendor?: string | null;
  manufacturer?: string | null;
  status?: string;
  price?: { retail?: number | string; wholesale?: number | string };
  cost?: { standard?: number | string; last?: number | string };
  quantity?: { on_hand?: number | string; on_order?: number | string; committed?: number | string };
  margin_pct?: number | string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const ItemCard: React.FC<ItemCardProps> = ({ ida, anchorRect, onClose }) => {
  const ref = useRef<HTMLDivElement>(null);
  const windowManager = useWindowManager();
  const [item, setItem] = useState<ItemDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Use fetched item's IDA for image (the passed ida might be a SKU)
  const imgIda = item?.ida || ida;
  const imgUrl = `/wcapi/_image/Item/${encodeURIComponent(imgIda)}/md.jpg`;

  // ── Fetch item data ──
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    // Try IDA first, then fall back to SKU search
    const tryFetch = async () => {
      // 1. Try by IDA
      const r1 = await fetch(`/wcapi/get/?model_name=item&ida=${encodeURIComponent(ida)}`);
      if (r1.ok) {
        const d1 = await r1.json();
        const rec = d1?.data?.results?.[0] || d1?.record || (d1?.id ? d1 : null);
        if (rec) return rec;
      }
      // 2. Fall back to SKU search
      const r2 = await fetch(`/wcapi/get/?model_name=item&search=${encodeURIComponent(ida)}`);
      if (r2.ok) {
        const d2 = await r2.json();
        const rec = d2?.data?.results?.[0];
        if (rec) return rec;
      }
      throw new Error('Item not found');
    };

    tryFetch()
      .then(rec => {
        if (cancelled) return;
        setItem(rec);
        setLoading(false);
      })
      .catch(err => {
        if (cancelled) return;
        setError(err.message);
        setLoading(false);
      });

    return () => { cancelled = true; };
  }, [ida]);

  // ── Dismiss handlers ──
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    const handleScroll = () => onClose();
    document.addEventListener('keydown', handleKey);
    document.addEventListener('mousedown', handleClick);
    window.addEventListener('scroll', handleScroll, true);
    return () => {
      document.removeEventListener('keydown', handleKey);
      document.removeEventListener('mousedown', handleClick);
      window.removeEventListener('scroll', handleScroll, true);
    };
  }, [onClose]);

  // ── Position: right of anchor, clamped to viewport ──
  const cardWidth = 420;
  const cardHeight = 340;
  let left = anchorRect.right + 8;
  let top = anchorRect.top;
  // If card would overflow right edge, show to the left of anchor
  if (left + cardWidth > window.innerWidth - 16) {
    left = anchorRect.left - cardWidth - 8;
  }
  // Clamp vertical
  if (top + cardHeight > window.innerHeight - 16) {
    top = window.innerHeight - cardHeight - 16;
  }
  if (top < 8) top = 8;

  const style: React.CSSProperties = {
    position: 'fixed',
    zIndex: 9999,
    left,
    top,
    width: cardWidth,
    background: 'var(--wc-surface, #fff)',
    border: '1px solid var(--wc-border, #dee2e6)',
    borderRadius: 8,
    boxShadow: '0 12px 32px rgba(0,0,0,0.2)',
    overflow: 'hidden',
  };

  const fmt = (v: number | string | undefined | null) => {
    if (v == null) return '—';
    const n = typeof v === 'string' ? parseFloat(v) : v;
    return isNaN(n) ? '—' : n.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
  };

  const fmtQty = (v: number | string | undefined | null) => {
    if (v == null) return '—';
    const n = typeof v === 'string' ? parseFloat(v) : v;
    return isNaN(n) ? '—' : n.toLocaleString();
  };

  const handleOpenItem = () => {
    if (item?.id) {
      windowManager.ensureWindow(`/item/${item.id}`, `Item ${ida}`, { maximized: false });
    }
    onClose();
  };

  return createPortal(
    <div ref={ref} style={style}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '8px 12px', borderBottom: '1px solid var(--wc-border, #dee2e6)',
        background: 'var(--wc-surface-alt, #f8fafc)',
      }}>
        <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--wc-text, #1e293b)' }}>{ida}</span>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            onClick={handleOpenItem}
            style={{
              fontSize: 11, padding: '3px 10px', borderRadius: 4,
              background: 'var(--wc-accent, #2563eb)', color: '#fff',
              border: 'none', cursor: 'pointer', fontWeight: 600,
            }}
          >
            Open Item
          </button>
          <button
            onClick={onClose}
            style={{
              fontSize: 11, padding: '3px 10px', borderRadius: 4,
              background: 'transparent', color: 'var(--wc-text-muted, #6c757d)',
              border: '1px solid var(--wc-border, #dee2e6)', cursor: 'pointer', fontWeight: 600,
            }}
          >
            ✕ Cancel
          </button>
        </div>
      </div>

      {/* Body */}
      <div style={{ display: 'flex', padding: 12, gap: 12 }}>
        {/* Image */}
        <div style={{ flexShrink: 0, width: 120, height: 120 }}>
          <img
            src={imgUrl}
            alt={ida}
            style={{ width: 120, height: 120, objectFit: 'contain', borderRadius: 4, background: '#f8f9fa' }}
            onError={(e) => { const img = e.target as HTMLImageElement; img.onerror = null; img.src = '/images/no-image.svg'; }}
          />
        </div>

        {/* Details */}
        <div style={{ flex: 1, minWidth: 0, fontSize: 12, color: 'var(--wc-text, #1e293b)' }}>
          {loading ? (
            <div style={{ color: 'var(--wc-text-muted, #6c757d)', padding: '20px 0' }}>Loading…</div>
          ) : error ? (
            <div style={{ color: '#dc2626' }}>Error: {error}</div>
          ) : item ? (
            <>
              <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {item.name || '—'}
              </div>
              <Row label="sku" value={item.sku} />
              <Row label="kind" value={item.kind} />
              <Row label="uom" value={item.uom} />
              <Row label="vendor" value={item.vendor} />
              <Row label="manufacturer" value={item.manufacturer} />
              <Row label="status" value={item.status} />
              {item.description && (
                <div style={{
                  marginTop: 6, padding: '4px 0', fontSize: 11,
                  color: 'var(--wc-text-muted, #6c757d)',
                  overflow: 'hidden', textOverflow: 'ellipsis',
                  display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
                }}>
                  {item.description}
                </div>
              )}
            </>
          ) : null}
        </div>
      </div>

      {/* Pricing + Inventory footer */}
      {item && !loading && (
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr',
          gap: 0, borderTop: '1px solid var(--wc-border, #dee2e6)',
          fontSize: 11, color: 'var(--wc-text, #1e293b)',
        }}>
          {/* Pricing */}
          <div style={{ padding: '8px 12px', borderRight: '1px solid var(--wc-border, #dee2e6)' }}>
            <div style={{ fontWeight: 600, fontSize: 10, textTransform: 'uppercase', color: 'var(--wc-text-muted, #6c757d)', marginBottom: 4 }}>pricing</div>
            <Row label=".retail" value={fmt(item.price?.retail)} mono />
            <Row label=".wholesale" value={fmt(item.price?.wholesale)} mono />
            <Row label=".standard" value={fmt(item.cost?.standard)} mono />
            <Row label=".last" value={fmt(item.cost?.last)} mono />
            {item.margin_pct != null && <Row label="margin" value={`${item.margin_pct}%`} mono />}
          </div>
          {/* Inventory */}
          <div style={{ padding: '8px 12px' }}>
            <div style={{ fontWeight: 600, fontSize: 10, textTransform: 'uppercase', color: 'var(--wc-text-muted, #6c757d)', marginBottom: 4 }}>inventory</div>
            <Row label=".on_hand" value={fmtQty(item.quantity?.on_hand)} mono />
            <Row label=".on_order" value={fmtQty(item.quantity?.on_order)} mono />
            <Row label=".committed" value={fmtQty(item.quantity?.committed)} mono />
          </div>
        </div>
      )}
    </div>,
    document.body,
  );
};

// ---------------------------------------------------------------------------
// Row helper
// ---------------------------------------------------------------------------

const Row: React.FC<{ label: string; value?: string | number | null; mono?: boolean }> = ({ label, value, mono }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '1px 0' }}>
    <span style={{ color: 'var(--wc-text-muted, #6c757d)' }}>{label}</span>
    <span style={{ fontFamily: mono ? 'monospace' : 'inherit', fontWeight: mono ? 500 : 400, textAlign: 'right' }}>
      {value ?? '—'}
    </span>
  </div>
);

export default ItemCard;

// ---------------------------------------------------------------------------
// Hook — same pattern as useItemImagePopup
// ---------------------------------------------------------------------------

export function useItemCard(): [React.ReactNode, (ida: string, rect: DOMRect) => void] {
  const [card, setCard] = useState<{ ida: string; rect: DOMRect } | null>(null);
  const close = useCallback(() => setCard(null), []);
  const show = useCallback((ida: string, rect: DOMRect) => setCard({ ida, rect }), []);

  const element = card
    ? React.createElement(ItemCard, { ida: card.ida, anchorRect: card.rect, onClose: close })
    : null;

  return [element, show];
}

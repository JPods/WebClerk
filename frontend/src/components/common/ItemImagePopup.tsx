/* LastChecked: 2026-09-10 | WhereUsed: DataGrid, useLineCard, LineDetailsModal | WhoCreated: Claude */
/**
 * ItemImagePopup — Cmd-click image preview for item codes.
 *
 * Shows the md-size image from /wcapi/_image/Item/{ida}/md.jpg
 * in a floating popup. Dismisses on click-outside, Escape, or scroll.
 */
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';

interface ItemImagePopupProps {
  ida: string;
  anchorRect: DOMRect;
  onClose: () => void;
}

const ItemImagePopup: React.FC<ItemImagePopupProps> = ({ ida, anchorRect, onClose }) => {
  const ref = useRef<HTMLDivElement>(null);
  const imgUrl = `/wcapi/_image/Item/${encodeURIComponent(ida)}/md.jpg`;

  // Position: below-right of anchor, clamped to viewport
  const style: React.CSSProperties = {
    position: 'fixed',
    zIndex: 9999,
    left: Math.min(anchorRect.left, window.innerWidth - 280),
    top: Math.min(anchorRect.bottom + 4, window.innerHeight - 280),
    background: 'var(--wc-surface, #fff)',
    border: '1px solid var(--wc-border, #dee2e6)',
    borderRadius: 6,
    boxShadow: '0 8px 24px rgba(0,0,0,0.18)',
    padding: 6,
    maxWidth: 264,
    maxHeight: 264,
  };

  // Dismiss handlers
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

  return createPortal(
    <div ref={ref} style={style}>
      <img
        src={imgUrl}
        alt={ida}
        style={{ maxWidth: 252, maxHeight: 252, objectFit: 'contain', display: 'block', borderRadius: 4 }}
        onError={(e) => { const img = e.target as HTMLImageElement; img.onerror = null; img.src = '/images/no-image.svg'; }}
      />
    </div>,
    document.body,
  );
};

export default ItemImagePopup;

/**
 * Hook for managing the image popup state.
 * Returns [popupElement, showPopup] — render popupElement; call showPopup(ida, rect) on cmd-click.
 */
export function useItemImagePopup(): [React.ReactNode, (ida: string, rect: DOMRect) => void] {
  const [popup, setPopup] = useState<{ ida: string; rect: DOMRect } | null>(null);
  const close = useCallback(() => setPopup(null), []);
  const show = useCallback((ida: string, rect: DOMRect) => setPopup({ ida, rect }), []);

  const element = popup
    ? React.createElement(ItemImagePopup, { ida: popup.ida, anchorRect: popup.rect, onClose: close })
    : null;

  return [element, show];
}

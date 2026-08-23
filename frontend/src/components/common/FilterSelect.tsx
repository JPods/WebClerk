/**
 * FilterSelect — the standard select list for wc3.
 *
 * Replaces native <select> everywhere. Features:
 *   - Text input with begins-with filtering (configurable to contains)
 *   - Div list with keyboard-navigable highlighted row
 *   - Arrow Up/Down moves highlight
 *   - Enter selects highlighted item
 *   - Click selects
 *   - Escape closes
 *   - Auto-scroll highlighted item into view
 *   - Current value shown bold
 *
 * Usage:
 *   <FilterSelect
 *     items={[{value: 'customer', label: 'Customer'}, ...]}
 *     value={selectedModel}
 *     onChange={(value) => setSelectedModel(value)}
 *     placeholder="Select model..."
 *   />
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

export interface FilterSelectItem {
  value: string;
  label: string;
  group?: string;  // optional group header
}

export interface FilterSelectProps {
  items: FilterSelectItem[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  filterMode?: 'startsWith' | 'contains';
  maxHeight?: number;
  className?: string;
  style?: React.CSSProperties;
  // Display
  inline?: boolean;           // true = always open (no toggle button)
  buttonLabel?: string;       // custom button label (overrides value display)
  buttonStyle?: React.CSSProperties;
  // Theme
  dark?: boolean;
}

export default function FilterSelect({
  items, value, onChange, placeholder = 'Search...',
  filterMode = 'startsWith', maxHeight = 240, className,
  style, inline, buttonLabel, buttonStyle, dark,
}: FilterSelectProps) {
  const [open, setOpen] = useState(inline || false);
  const [filterText, setFilterText] = useState('');
  const [highlight, setHighlight] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Colors
  const bg = dark ? '#252526' : '#ffffff';
  const bgAlt = dark ? '#1e1e1e' : '#f8f9fa';
  const border = dark ? '#3c3c3c' : '#dee2e6';
  const text = dark ? '#d4d4d4' : '#212529';
  const textMuted = dark ? '#888' : '#6c757d';
  const hlBg = dark ? '#094771' : '#cfe2ff';
  const hlText = dark ? '#fff' : '#000';
  const selBg = dark ? '#2d2d2d' : '#f1f3f5';

  // Filter items
  const filtered = useMemo(() => {
    if (!filterText.trim()) return items;
    const q = filterText.toLowerCase();
    return items.filter((item) =>
      filterMode === 'startsWith'
        ? item.label.toLowerCase().startsWith(q) || item.value.toLowerCase().startsWith(q)
        : item.label.toLowerCase().includes(q) || item.value.toLowerCase().includes(q)
    );
  }, [items, filterText, filterMode]);

  // Reset highlight when filter changes
  useEffect(() => { setHighlight(0); }, [filterText]);

  // Close on outside click
  useEffect(() => {
    if (!open || inline) return;
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false); setFilterText('');
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open, inline]);

  // Focus input when opening
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50);
  }, [open]);

  const select = useCallback((val: string) => {
    onChange(val);
    if (!inline) { setOpen(false); setFilterText(''); }
  }, [onChange, inline]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setHighlight((h) => Math.min(h + 1, filtered.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setHighlight((h) => Math.max(h - 1, 0)); }
    else if (e.key === 'Enter' && filtered.length) { e.preventDefault(); select(filtered[highlight].value); }
    else if (e.key === 'Escape') { if (!inline) { setOpen(false); setFilterText(''); } }
  }, [filtered, highlight, select, inline]);

  // Current label
  const currentLabel = useMemo(() => {
    const item = items.find((i) => i.value === value);
    return buttonLabel || item?.label || value || placeholder;
  }, [items, value, buttonLabel, placeholder]);

  return (
    <div ref={containerRef} style={{ position: 'relative', ...style }} className={className}>
      {/* Toggle button (hidden in inline mode) */}
      {!inline && (
        <button onClick={() => setOpen(!open)} type="button"
          style={{
            background: bgAlt, border: `1px solid ${border}`, borderRadius: 4,
            padding: '4px 12px', color: dark ? '#9cdcfe' : '#0d6efd',
            fontSize: 13, fontWeight: 700, cursor: 'pointer', textAlign: 'left',
            width: '100%', ...buttonStyle,
          }}>
          {currentLabel}
        </button>
      )}

      {/* Dropdown / inline list */}
      {open && (
        <div style={{
          ...(inline ? {} : { position: 'absolute', top: '100%', left: 0, zIndex: 100, marginTop: 2, boxShadow: '0 8px 24px rgba(0,0,0,0.2)' }),
          background: bg, border: `1px solid ${border}`, borderRadius: 6,
          width: inline ? '100%' : undefined, minWidth: 200,
          display: 'flex', flexDirection: 'column',
        }}>
          {/* Filter input */}
          <div style={{ padding: 6 }}>
            <input ref={inputRef} type="text" value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              style={{
                width: '100%', padding: '4px 8px', fontSize: 12,
                background: bgAlt, border: `1px solid ${border}`, borderRadius: 4,
                color: text, outline: 'none',
              }}
            />
          </div>

          {/* Item list */}
          <div ref={listRef} style={{ maxHeight, overflowY: 'auto', padding: '0 2px 4px' }}>
            {filtered.map((item, i) => (
              <div key={item.value}
                onClick={() => select(item.value)}
                onMouseEnter={() => setHighlight(i)}
                ref={i === highlight ? (el) => el?.scrollIntoView({ block: 'nearest' }) : undefined}
                style={{
                  padding: '5px 10px', cursor: 'pointer', fontSize: 12, borderRadius: 3,
                  background: i === highlight ? hlBg : item.value === value ? selBg : 'transparent',
                  color: i === highlight ? hlText : text,
                  fontWeight: item.value === value ? 700 : 400,
                }}>
                {item.label}
              </div>
            ))}
            {filtered.length === 0 && (
              <div style={{ padding: '8px 10px', fontSize: 11, color: textMuted }}>No matches</div>
            )}
          </div>

          {/* Footer */}
          <div style={{ padding: '4px 8px', borderTop: `1px solid ${border}`, fontSize: 10, color: textMuted }}>
            {filtered.length}/{items.length} · ↑↓ navigate · Enter select
          </div>
        </div>
      )}
    </div>
  );
}

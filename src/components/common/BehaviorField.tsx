/**
 * BehaviorField — renders one field based on field_behaviors config.
 *
 * Reusable in DataBrowser, OrgPage, any detail page.
 * Handles: email→mailto, phone→tel, address→map, geo→map, url→link,
 * select (inline), lookup (FK), currency, boolean, json, textarea,
 * timestamp, readonly, number, text.
 *
 * Label color: blue=actionable, green=select, purple=lookup, gray=readonly.
 * Cmd+Option+Shift+click any label → opens field-level help in Help Dashboard.
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { openFieldHelp } from './HelpMenu';
import { getRecords } from '@/api/wcapi';

interface BehaviorFieldProps {
  name: string;
  value: unknown;
  behavior: Record<string, any>;
  onChange: (value: unknown) => void;
  record?: Record<string, unknown>;  // full record for geo pair lookups
  fontSize?: number;
  theme?: {
    inputBg: string; inputBorder: string; text: string; textMuted: string; textDim: string;
    accent: string; accentGreen: string; accentPurple: string; surfaceAlt: string; border: string;
  };
  rowSize?: number;
  typeHint?: string;  // layout-level override for widget type
  error?: string;     // validation error message to display
}

export default function BehaviorField({
  name, value: v, behavior: beh, onChange, record, fontSize = 12, theme: t, rowSize,
  typeHint, error,
}: BehaviorFieldProps) {
  const behType = typeHint || beh.type || '';
  const isJson = typeof v === 'object' && v !== null;
  const isLong = typeof v === 'string' && (v as string).length > 100;
  const span2 = (isJson || isLong || behType === 'textarea' || behType === 'json');

  // Default theme
  const th = t || {
    inputBg: '#fff', inputBorder: '#ced4da', text: '#212529', textMuted: '#6c757d', textDim: '#adb5bd',
    accent: '#0d6efd', accentGreen: '#198754', accentPurple: '#6f42c1', surfaceAlt: '#f8f9fa', border: '#dee2e6',
  };

  const inputStyle: React.CSSProperties = {
    background: th.inputBg, border: `1px solid ${th.inputBorder}`, borderRadius: 4,
    color: th.text, fontSize: fontSize - 1, padding: '4px 8px', outline: 'none',
  };

  const labelColor = behType === 'email' || behType === 'phone' || behType === 'address' || behType === 'geo' || behType === 'url' ? th.accent
    : behType === 'select' ? th.accentGreen
    : behType === 'lookup' ? th.accentPurple
    : behType === 'readonly' || behType === 'timestamp' ? th.textDim
    : th.textMuted;

  const labelStyle: React.CSSProperties = {
    display: 'block', fontSize: fontSize - 2, fontWeight: 600, color: labelColor,
    marginBottom: 3, letterSpacing: '0.02em', cursor: beh.action ? 'pointer' : 'default',
  };

  const wcModel = (record as any)?._model || '';
  const labelTitle = wcModel ? `${wcModel}.${name}` : name;

  // Click on label: if field has an action defined, execute it.
  // Shift+click → open field help (Shift-for-Help standard).
  const handleLabelClick = (e: React.MouseEvent) => {
    if (e.shiftKey) {
      e.preventDefault();
      e.stopPropagation();
      const model = wcModel || 'system';
      openFieldHelp(model, name);
      return;
    }
    if (beh.action === 'lookup' && behType === 'lookup') {
      // Click label on lookup → focus the input
      const input = (e.currentTarget as HTMLElement)?.parentElement?.querySelector('input');
      if (input) input.focus();
    }
  };

  const wrapStyle: React.CSSProperties = span2 ? { gridColumn: '1 / -1' } : {};
  const wcAttrs = { 'data-wc': `field-${name}`, 'data-wc-field': name, ...(wcModel ? { 'data-wc-model': wcModel } : {}) };

  // ── Readonly ──
  if (behType === 'readonly') {
    const display = (f_startsDt(name) && typeof v === 'number') ? new Date(v).toLocaleString() : String(v ?? '--');
    return <div style={wrapStyle} {...wcAttrs}><span style={labelStyle} title={labelTitle} onClick={handleLabelClick}>{name}</span>
      <div style={{ background: th.surfaceAlt, border: `1px solid ${th.border}`, borderRadius: 4, padding: '4px 8px', fontSize, color: th.textMuted, fontFamily: 'monospace' }}>{display}</div>
    </div>;
  }

  // ── Email ──
  if (behType === 'email') return <div style={wrapStyle} {...wcAttrs}>
    <a href={v ? `mailto:${v}` : undefined} style={{ ...labelStyle, cursor: v ? 'pointer' : 'default', textDecoration: 'none' }} title={v ? `Email ${v}` : name}>{name} ✉</a>
    <input type="email" style={{ ...inputStyle, width: '100%' }} value={String(v ?? '')} onChange={(e) => onChange(e.target.value)} />
  </div>;

  // ── Phone ──
  if (behType === 'phone') return <div style={wrapStyle} {...wcAttrs}>
    <a href={v ? `tel:${v}` : undefined} style={{ ...labelStyle, cursor: v ? 'pointer' : 'default', textDecoration: 'none' }} title={v ? `Call ${v}` : name}>{name} ☎</a>
    <input type="tel" style={{ ...inputStyle, width: '100%' }} value={String(v ?? '')} onChange={(e) => onChange(e.target.value)} />
  </div>;

  // ── Address ──
  if (behType === 'address') return <div style={wrapStyle} {...wcAttrs}>
    <a href={v ? `https://maps.google.com/?q=${encodeURIComponent(String(v))}` : undefined} target="_blank" rel="noopener noreferrer"
      style={{ ...labelStyle, cursor: v ? 'pointer' : 'default', textDecoration: 'none' }}>{name} 📍</a>
    <input style={{ ...inputStyle, width: '100%' }} value={String(v ?? '')} onChange={(e) => onChange(e.target.value)} />
  </div>;

  // ── Geo ──
  if (behType === 'geo') {
    const pair = beh.pair;
    const lat = name === 'latitude' ? v : record?.[pair];
    const lng = name === 'longitude' ? v : record?.[pair];
    const mapUrl = lat && lng ? `https://maps.google.com/?q=${lat},${lng}` : undefined;
    return <div style={wrapStyle} {...wcAttrs}>
      <a href={mapUrl} target="_blank" rel="noopener noreferrer" style={{ ...labelStyle, color: mapUrl ? th.accent : th.textMuted, cursor: mapUrl ? 'pointer' : 'default', textDecoration: 'none' }}>{name} 🗺</a>
      <input type="number" step="any" style={{ ...inputStyle, width: '100%', fontFamily: 'monospace' }} value={v != null ? v : ''} onChange={(e) => onChange(parseFloat(e.target.value) || 0)} />
    </div>;
  }

  // ── URL ──
  if (behType === 'url') return <div style={wrapStyle} {...wcAttrs}>
    <a href={v && String(v).startsWith('http') ? String(v) : v ? `https://${v}` : undefined} target="_blank" rel="noopener noreferrer"
      style={{ ...labelStyle, cursor: v ? 'pointer' : 'default', textDecoration: 'none' }}>{name} 🔗</a>
    <input style={{ ...inputStyle, width: '100%' }} value={String(v ?? '')} onChange={(e) => onChange(e.target.value)} />
  </div>;

  // ── Select (with optional freehand via allow_custom) ──
  if (behType === 'select' && beh.options) {
    const currentVal = String(v ?? '');
    const inList = beh.options.some((o: any) => o.value === currentVal);
    // If allow_custom and value is not in the list, show it as an option
    return <div style={wrapStyle} {...wcAttrs}>
      <span style={labelStyle} title={labelTitle} onClick={handleLabelClick}>{name}</span>
      {beh.allow_custom ? (
        <div style={{ display: 'flex', gap: 4 }}>
          <select style={{ ...inputStyle, flex: 1, cursor: 'pointer' }}
            value={inList ? currentVal : '__custom__'}
            onChange={(e) => { if (e.target.value !== '__custom__') onChange(e.target.value); }}>
            <option value="">--</option>
            {beh.options.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
            {!inList && currentVal && <option value="__custom__">{currentVal}</option>}
            <option value="__custom__">other...</option>
          </select>
          {(!inList || currentVal === '') && (
            <input style={{ ...inputStyle, flex: 1 }} value={currentVal} onChange={(e) => onChange(e.target.value)}
              placeholder="type here" />
          )}
        </div>
      ) : (
        <select style={{ ...inputStyle, width: '100%', cursor: 'pointer' }} value={currentVal} onChange={(e) => onChange(e.target.value)}>
          <option value="">--</option>
          {beh.options.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      )}
    </div>;
  }

  // ── Hidden ──
  if (behType === 'hidden') return null;

  // ── Lookup (search by name, store ID) ──
  if (behType === 'lookup') return <LookupSearch
    name={name} value={v} model={beh.model} onChange={onChange}
    labelStyle={labelStyle} inputStyle={inputStyle} wrapStyle={wrapStyle}
    wcAttrs={wcAttrs} theme={th} fontSize={fontSize} handleLabelClick={handleLabelClick}
  />;

  // ── Currency ──
  if (behType === 'currency') return <div style={wrapStyle} {...wcAttrs}>
    <span style={labelStyle} title={labelTitle} onClick={handleLabelClick}>{name}</span>
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <span style={{ color: th.textMuted, fontSize }}>$</span>
      <input type="number" step="0.01" style={{ ...inputStyle, flex: 1, fontFamily: 'monospace', textAlign: 'right' }} value={v != null ? v : ''} onChange={(e) => onChange(parseFloat(e.target.value) || 0)} />
    </div>
  </div>;

  // ── Timestamp ──
  if (behType === 'timestamp') return <div style={wrapStyle} {...wcAttrs}>
    <span style={labelStyle} title={labelTitle} onClick={handleLabelClick}>{name}</span>
    <div style={{ background: th.surfaceAlt, border: `1px solid ${th.border}`, borderRadius: 4, padding: '4px 8px', fontSize, color: th.textMuted, fontFamily: 'monospace' }}>
      {v ? new Date(v as number).toLocaleString() : '--'}
    </div>
  </div>;

  // ── Boolean ──
  if (behType === 'boolean' || typeof v === 'boolean') return <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', ...wrapStyle }}>
    <input type="checkbox" checked={!!v} onChange={(e) => onChange(e.target.checked)} />
    <span style={{ fontSize, color: th.text }}>{name}</span>
  </label>;

  // ── JSON ──
  if (behType === 'json' || isJson) {
    const js = JSON.stringify(v, null, 2);
    const rows = rowSize || (js.length > 200 ? 8 : 3);
    return <div style={{ gridColumn: '1 / -1' }}>
      <span style={labelStyle}>{name} <span style={{ fontWeight: 400, textTransform: 'none' }}>({js.length})</span></span>
      <textarea style={{ ...inputStyle, width: '100%', fontFamily: 'monospace', fontSize: fontSize - 1, resize: 'vertical' }} rows={rows} value={js}
        onChange={(e) => { try { onChange(JSON.parse(e.target.value)); } catch { /* typing */ } }} />
    </div>;
  }

  // ── Textarea ──
  if (behType === 'textarea' || isLong) {
    const rows = rowSize || 4;
    return <div style={{ gridColumn: '1 / -1' }}>
      <span style={labelStyle} title={labelTitle} onClick={handleLabelClick}>{name}</span>
      <textarea style={{ ...inputStyle, width: '100%', resize: 'vertical' }} rows={rows} value={String(v ?? '')} onChange={(e) => onChange(e.target.value)} />
    </div>;
  }

  // ── Number ──
  if (behType === 'number' || (typeof v === 'number' && !f_startsDt(name))) return <div style={wrapStyle} {...wcAttrs}>
    <span style={labelStyle} title={labelTitle} onClick={handleLabelClick}>{name}</span>
    <input type="number" style={{ ...inputStyle, width: '100%', fontFamily: 'monospace' }} value={v != null ? v : ''} onChange={(e) => onChange(parseFloat(e.target.value) || 0)} />
  </div>;

  // ── Default text ──
  return <div style={wrapStyle} {...wcAttrs}>
    <span style={labelStyle} title={labelTitle} onClick={handleLabelClick}>{name}</span>
    <input style={{ ...inputStyle, width: '100%' }} value={String(v ?? '')} onChange={(e) => onChange(e.target.value)} />
  </div>;
}

// ── LookupSearch — search by name, display name, store FK ID ──
function LookupSearch({ name, value: v, model, onChange, labelStyle, inputStyle, wrapStyle, wcAttrs, theme: th, fontSize, handleLabelClick }: {
  name: string; value: unknown; model: string; onChange: (v: unknown) => void;
  labelStyle: React.CSSProperties; inputStyle: React.CSSProperties; wrapStyle: React.CSSProperties;
  wcAttrs: Record<string, string>; theme: any; fontSize: number; handleLabelClick: (e: React.MouseEvent) => void;
}) {
  const [query, setQuery] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
  const wrapRef = useRef<HTMLDivElement>(null);

  // Resolve display name from ID on mount or value change
  useEffect(() => {
    if (!v) { setDisplayName(''); return; }
    getRecords(model, { id: v, limit: 1 }).then((res: any) => {
      const rec = (res?.results || [])[0];
      if (rec) {
        setDisplayName(rec.display_name || rec.name || rec.company || rec.ida || `#${rec.id}`);
      }
    }).catch(() => {});
  }, [v, model]);

  // Search on typing
  const doSearch = useCallback((q: string) => {
    if (q.length < 2) { setResults([]); return; }
    setLoading(true);
    getRecords(model, { keyword: q, limit: 10 }).then((res: any) => {
      setResults(res?.results || []);
      setOpen(true);
    }).catch(() => setResults([]))
      .finally(() => setLoading(false));
  }, [model]);

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const q = e.target.value;
    setQuery(q);
    setDisplayName('');
    onChange(null); // clear FK until they pick
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => doSearch(q), 250);
  };

  const handleSelect = (rec: any) => {
    onChange(rec.id);
    setDisplayName(rec.display_name || rec.name || rec.company || rec.ida || `#${rec.id}`);
    setQuery('');
    setOpen(false);
  };

  const handleAddNew = async () => {
    try {
      const { saveRecord } = await import('@/api/wcapi');
      const blank: any = { ida: query };
      // For contact, set name fields
      if (model === 'contact') {
        const parts = query.trim().split(/\s+/);
        blank.name_first = parts[0] || query;
        blank.name_last = parts.slice(1).join(' ') || '';
      } else {
        blank.name = query;
      }
      const result = await saveRecord(model, blank) as any;
      if (result?.id) handleSelect(result);
    } catch (err) {
      console.error('[LookupSearch] add new failed:', err);
    }
  };

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div style={{ ...wrapStyle, position: 'relative' }} ref={wrapRef} {...wcAttrs}>
      <span style={labelStyle} title={labelTitle} onClick={handleLabelClick}>{name}</span>
      <input
        style={{ ...inputStyle, width: '100%' }}
        value={displayName || query}
        onChange={handleInput}
        onFocus={() => { if (displayName) { setQuery(displayName); setDisplayName(''); } }}
        placeholder={`search ${model}...`}
      />
      {open && results.length > 0 && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 999,
          background: th.inputBg, border: `1px solid ${th.inputBorder}`, borderRadius: 4,
          maxHeight: 200, overflowY: 'auto', boxShadow: '0 4px 12px rgba(0,0,0,.2)',
        }}>
          {results.map((r) => (
            <div key={r.id} onClick={() => handleSelect(r)} style={{
              padding: '6px 10px', cursor: 'pointer', fontSize: fontSize - 1,
              color: th.text, borderBottom: `1px solid ${th.border}`,
            }}
              onMouseEnter={(e) => (e.currentTarget.style.background = th.surfaceAlt)}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <span style={{ fontWeight: 600 }}>{r.display_name || r.name || r.company || r.ida}</span>
              {r.email && <span style={{ marginLeft: 8, color: th.textMuted, fontSize: fontSize - 2 }}>{r.email}</span>}
            </div>
          ))}
          <div onClick={handleAddNew} style={{
            padding: '6px 10px', cursor: 'pointer', fontSize: fontSize - 1,
            color: th.accentGreen, fontWeight: 600, borderTop: `1px solid ${th.border}`,
          }}
            onMouseEnter={(e) => (e.currentTarget.style.background = th.surfaceAlt)}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          >
            + Add "{query}"
          </div>
        </div>
      )}
      {open && results.length === 0 && query.length >= 2 && !loading && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 999,
          background: th.inputBg, border: `1px solid ${th.inputBorder}`, borderRadius: 4,
          boxShadow: '0 4px 12px rgba(0,0,0,.2)',
        }}>
          <div style={{ padding: '6px 10px', color: th.textMuted, fontSize: fontSize - 1 }}>No matches</div>
          <div onClick={handleAddNew} style={{
            padding: '6px 10px', cursor: 'pointer', fontSize: fontSize - 1,
            color: th.accentGreen, fontWeight: 600,
          }}
            onMouseEnter={(e) => (e.currentTarget.style.background = th.surfaceAlt)}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          >
            + Add "{query}"
          </div>
        </div>
      )}
    </div>
  );
}

function f_startsDt(name: string) { return name.startsWith('dt_'); }

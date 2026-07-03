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
import React from 'react';
import { openFieldHelp } from './HelpMenu';

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
}

export default function BehaviorField({
  name, value: v, behavior: beh, onChange, record, fontSize = 12, theme: t, rowSize,
}: BehaviorFieldProps) {
  const behType = beh.type || '';
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
    marginBottom: 3, textTransform: 'uppercase', letterSpacing: '0.04em',
  };

  // Cmd+Option+Shift+click on label → open field help
  const handleLabelClick = (e: React.MouseEvent) => {
    if (e.metaKey && e.altKey && e.shiftKey) {
      e.preventDefault();
      e.stopPropagation();
      // Try to get model from parent context — fallback to 'system'
      const model = (record as any)?._model || 'system';
      openFieldHelp(model, name);
    }
  };

  const wrapStyle: React.CSSProperties = span2 ? { gridColumn: '1 / -1' } : {};
  const wcModel = (record as any)?._model || '';
  const wcAttrs = { 'data-wc': `field-${name}`, 'data-wc-field': name, ...(wcModel ? { 'data-wc-model': wcModel } : {}) };

  // ── Readonly ──
  if (behType === 'readonly') {
    const display = (f_startsDt(name) && typeof v === 'number') ? new Date(v).toLocaleString() : String(v ?? '--');
    return <div style={wrapStyle} {...wcAttrs}><span style={labelStyle} onClick={handleLabelClick}>{name}</span>
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

  // ── Select ──
  if (behType === 'select' && beh.options) return <div style={wrapStyle} {...wcAttrs}>
    <span style={labelStyle} onClick={handleLabelClick}>{name}</span>
    <select style={{ ...inputStyle, width: '100%', cursor: 'pointer' }} value={String(v ?? '')} onChange={(e) => onChange(e.target.value)}>
      <option value="">--</option>
      {beh.options.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  </div>;

  // ── Lookup ──
  if (behType === 'lookup') return <div style={wrapStyle} {...wcAttrs}>
    <span style={labelStyle}>{name} <span style={{ fontWeight: 400, textTransform: 'none', color: th.textDim }}>→ {beh.model}</span></span>
    <input style={{ ...inputStyle, width: '100%' }} value={String(v ?? '')} onChange={(e) => onChange(e.target.value)} placeholder={`${beh.model} ID`} />
  </div>;

  // ── Currency ──
  if (behType === 'currency') return <div style={wrapStyle} {...wcAttrs}>
    <span style={labelStyle} onClick={handleLabelClick}>{name}</span>
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <span style={{ color: th.textMuted, fontSize }}>$</span>
      <input type="number" step="0.01" style={{ ...inputStyle, flex: 1, fontFamily: 'monospace', textAlign: 'right' }} value={v != null ? v : ''} onChange={(e) => onChange(parseFloat(e.target.value) || 0)} />
    </div>
  </div>;

  // ── Timestamp ──
  if (behType === 'timestamp') return <div style={wrapStyle} {...wcAttrs}>
    <span style={labelStyle} onClick={handleLabelClick}>{name}</span>
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
      <span style={labelStyle} onClick={handleLabelClick}>{name}</span>
      <textarea style={{ ...inputStyle, width: '100%', resize: 'vertical' }} rows={rows} value={String(v ?? '')} onChange={(e) => onChange(e.target.value)} />
    </div>;
  }

  // ── Number ──
  if (behType === 'number' || (typeof v === 'number' && !f_startsDt(name))) return <div style={wrapStyle} {...wcAttrs}>
    <span style={labelStyle} onClick={handleLabelClick}>{name}</span>
    <input type="number" style={{ ...inputStyle, width: '100%', fontFamily: 'monospace' }} value={v != null ? v : ''} onChange={(e) => onChange(parseFloat(e.target.value) || 0)} />
  </div>;

  // ── Default text ──
  return <div style={wrapStyle} {...wcAttrs}>
    <span style={labelStyle} onClick={handleLabelClick}>{name}</span>
    <input style={{ ...inputStyle, width: '100%' }} value={String(v ?? '')} onChange={(e) => onChange(e.target.value)} />
  </div>;
}

function f_startsDt(name: string) { return name.startsWith('dt_'); }

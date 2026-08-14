/**
 * TokenBuilder — standalone {{token}} field picker.
 *
 * Users open this from any page, see all fields for a model,
 * click a field → {{field.path}} copies to clipboard.
 * Toggle List (CSV column headers) vs Detail (single record tokens).
 * "Copy All" dumps selected tokens for paste into Gmail, Word, Pages.
 *
 * WC3 is not a formatting tool. We provide {{field.path}} and let
 * users choose everything about formatting in their own tools.
 */
import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { getModelNames } from '@/api/wcapi';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RegistryField {
  field: string;
  label: string;
  type: string;
  source: string;
  group?: string;
}

interface ReportFieldsResponse {
  model: string;
  direct: RegistryField[];
  related: Record<string, RegistryField[]>;
  json_paths: RegistryField[];
  lines: RegistryField[];
  line_model?: string;
}

interface TokenBuilderProps {
  /** Current model context (pre-selects model) */
  model?: string;
  /** Dark mode */
  dark?: boolean;
  /** Called when panel closes */
  onClose?: () => void;
}

// ---------------------------------------------------------------------------
// Clipboard helper
// ---------------------------------------------------------------------------

function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    return navigator.clipboard.writeText(text);
  }
  // Fallback
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.left = '-9999px';
  document.body.appendChild(ta);
  ta.select();
  document.execCommand('copy');
  document.body.removeChild(ta);
  return Promise.resolve();
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const TokenBuilder: React.FC<TokenBuilderProps> = ({ model: initialModel, dark = true, onClose }) => {
  const [allModels, setAllModels] = useState<string[]>([]);
  const [activeModel, setActiveModel] = useState(initialModel || '');
  const [registry, setRegistry] = useState<ReportFieldsResponse | null>(null);
  const [selected, setSelected] = useState<RegistryField[]>([]);
  const [mode, setMode] = useState<'detail' | 'list'>('detail');
  const [filter, setFilter] = useState('');
  const [copied, setCopied] = useState('');
  const registryCache = useRef<Record<string, ReportFieldsResponse>>({});
  const filterRef = useRef<HTMLInputElement>(null);

  // Colors
  const bg = dark ? '#1e1e2e' : '#fff';
  const surface = dark ? '#252536' : '#f5f5f5';
  const border = dark ? '#3c3c3c' : '#ddd';
  const text = dark ? '#d4d4d4' : '#222';
  const textMuted = dark ? '#888' : '#999';
  const accent = dark ? '#9cdcfe' : '#0066cc';
  const accentGreen = dark ? '#4ec98c' : '#2e7d32';
  const highlight = dark ? '#2a2d3e' : '#e8f0fe';

  // Fetch models
  useEffect(() => {
    getModelNames().then((res: any) => {
      const names = res?.model_names || res?.data?.model_names || [];
      setAllModels(names.sort());
    }).catch(() => {});
  }, []);

  // Fetch fields for model
  const fetchFields = useCallback((m: string) => {
    if (!m) return;
    if (registryCache.current[m]) {
      setRegistry(registryCache.current[m]);
      setActiveModel(m);
      return;
    }
    fetch(`/wcapi/report-fields/?model=${encodeURIComponent(m)}`, { credentials: 'include' })
      .then(r => r.json())
      .then(data => {
        if (data && !data.error) {
          registryCache.current[m] = data;
          setRegistry(data);
          setActiveModel(m);
        }
      })
      .catch(() => {});
  }, []);

  // Load initial model
  useEffect(() => { if (initialModel) fetchFields(initialModel); }, [initialModel, fetchFields]);

  // All available fields
  const allFields = useMemo(() => {
    if (!registry) return [];
    const all: RegistryField[] = [...(registry.direct || [])];
    for (const relFields of Object.values(registry.related || {})) all.push(...relFields);
    for (const f of registry.json_paths || []) all.push(f);
    return all;
  }, [registry]);

  const lineFields = useMemo(() => registry?.lines || [], [registry]);

  // Filter
  const filtered = useMemo(() => {
    if (!filter) return allFields;
    const lf = filter.toLowerCase();
    return allFields.filter(f =>
      f.field.toLowerCase().includes(lf) || f.label.toLowerCase().includes(lf)
    );
  }, [allFields, filter]);

  // Selected field paths for quick lookup
  const selectedPaths = useMemo(() => new Set(selected.map(f => f.field)), [selected]);

  // Click field → copy token to clipboard
  const handleFieldClick = useCallback((f: RegistryField) => {
    const token = `{{${f.field}}}`;
    copyToClipboard(token).then(() => {
      setCopied(token);
      setTimeout(() => setCopied(''), 1500);
    });
  }, []);

  // Shift-click → add to selected list
  const handleFieldSelect = useCallback((f: RegistryField, e: React.MouseEvent) => {
    if (e.shiftKey) {
      setSelected(prev =>
        selectedPaths.has(f.field)
          ? prev.filter(s => s.field !== f.field)
          : [...prev, f]
      );
    } else {
      handleFieldClick(f);
    }
  }, [selectedPaths, handleFieldClick]);

  // Remove from selected
  const handleRemove = useCallback((field: string) => {
    setSelected(prev => prev.filter(f => f.field !== field));
  }, []);

  // Copy All — format depends on mode
  const handleCopyAll = useCallback(() => {
    let text: string;
    if (mode === 'list') {
      // CSV header row + token row
      const headers = selected.map(f => f.label).join('\t');
      const tokens = selected.map(f => `{{${f.field}}}`).join('\t');
      text = `${headers}\n${tokens}`;
    } else {
      // Detail — one token per line with label
      text = selected.map(f => `{{${f.field}}}`).join('\n');
    }
    copyToClipboard(text).then(() => {
      setCopied('All copied');
      setTimeout(() => setCopied(''), 1500);
    });
  }, [selected, mode]);

  // Clear selected
  const handleClear = useCallback(() => setSelected([]), []);

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      background: bg, color: text, fontSize: 13, fontFamily: 'system-ui, sans-serif',
    }}>
      {/* Toolbar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px',
        borderBottom: `1px solid ${border}`, background: surface,
      }}>
        <span style={{ fontWeight: 700, color: accent }}>{'{{'}Tokens{'}}'}</span>
        <button onClick={handleClear}
          style={{ background: 'none', border: `1px solid ${border}`, color: textMuted, borderRadius: 3, padding: '2px 8px', cursor: 'pointer', fontSize: 11 }}>
          Clear
        </button>
        <div style={{ display: 'flex', gap: 2, marginLeft: 4 }}>
          <button onClick={() => setMode('detail')}
            style={{ background: mode === 'detail' ? accent : 'none', color: mode === 'detail' ? '#000' : textMuted, border: `1px solid ${border}`, borderRadius: '3px 0 0 3px', padding: '2px 8px', cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
            Detail
          </button>
          <button onClick={() => setMode('list')}
            style={{ background: mode === 'list' ? accent : 'none', color: mode === 'list' ? '#000' : textMuted, border: `1px solid ${border}`, borderRadius: '0 3px 3px 0', padding: '2px 8px', cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
            List
          </button>
        </div>
        {selected.length > 0 && (
          <button onClick={handleCopyAll}
            style={{ background: accentGreen, color: '#fff', border: 'none', borderRadius: 3, padding: '3px 10px', cursor: 'pointer', fontSize: 11, fontWeight: 600, marginLeft: 'auto' }}>
            Copy All ({selected.length})
          </button>
        )}
        {copied && (
          <span style={{ fontSize: 11, color: accentGreen, marginLeft: 'auto' }}>{copied}</span>
        )}
        {onClose && (
          <button onClick={onClose}
            style={{ background: 'none', border: 'none', color: textMuted, cursor: 'pointer', fontSize: 16, marginLeft: onClose && !copied ? 'auto' : 0 }}>
            ×
          </button>
        )}
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* Selected fields (top tier in WC2) */}
        <div style={{ flex: '0 0 50%', display: 'flex', flexDirection: 'column', borderRight: `1px solid ${border}` }}>
          {/* Selected list */}
          <div style={{ flex: 1, overflow: 'auto', padding: 0 }}>
            <div style={{ padding: '4px 8px', fontSize: 11, color: textMuted, borderBottom: `1px solid ${border}`, background: surface }}>
              Selected ({selected.length}) — click to copy, shift-click in field list to add
            </div>
            {selected.map(f => (
              <div key={f.field}
                onClick={() => handleFieldClick(f)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6, padding: '3px 8px',
                  cursor: 'pointer', borderBottom: `1px solid ${border}`,
                }}
              >
                <span style={{ flex: 1, fontSize: 12 }}>{`{{${f.field}}}`}</span>
                <span style={{ fontSize: 10, color: textMuted }}>{f.type}</span>
                <span onClick={(e) => { e.stopPropagation(); handleRemove(f.field); }}
                  style={{ color: textMuted, cursor: 'pointer', fontSize: 14 }}>×</span>
              </div>
            ))}
            {selected.length === 0 && (
              <div style={{ padding: '12px 8px', color: textMuted, fontSize: 11 }}>
                Shift-click fields to build a set. Click any field to copy its token.
              </div>
            )}
          </div>

          {/* Line fields (if model has lines) */}
          {lineFields.length > 0 && (
            <div style={{ borderTop: `1px solid ${border}` }}>
              <div style={{ padding: '4px 8px', fontSize: 11, color: textMuted, background: surface }}>
                Line fields ({lineFields.length})
              </div>
              <div style={{ maxHeight: 120, overflow: 'auto' }}>
                {lineFields.map(f => (
                  <div key={f.field}
                    onClick={(e) => handleFieldSelect(f, e)}
                    style={{
                      display: 'flex', gap: 6, padding: '2px 8px', cursor: 'pointer',
                      background: selectedPaths.has(f.field) ? highlight : 'transparent',
                      borderBottom: `1px solid ${border}`,
                    }}
                  >
                    <span style={{ flex: 1, fontSize: 12 }}>{f.label}</span>
                    <span style={{ fontSize: 10, color: textMuted }}>{f.field}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Model selector (bottom tier in WC2) */}
          <div style={{ borderTop: `1px solid ${border}`, maxHeight: 140, overflow: 'auto' }}>
            <div style={{ padding: '4px 8px', fontSize: 11, color: textMuted, background: surface }}>
              Models
            </div>
            {allModels.map(m => (
              <div key={m}
                onClick={() => fetchFields(m)}
                style={{
                  padding: '2px 8px', cursor: 'pointer', fontSize: 12,
                  background: m === activeModel ? highlight : 'transparent',
                  fontWeight: m === activeModel ? 600 : 400,
                }}
              >
                {m}
              </div>
            ))}
          </div>
        </div>

        {/* Available fields (middle tier in WC2) */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '4px 8px',
            borderBottom: `1px solid ${border}`, background: surface,
          }}>
            <span style={{ fontSize: 11, color: textMuted }}>{activeModel} fields</span>
            <input
              ref={filterRef}
              value={filter}
              onChange={e => setFilter(e.target.value)}
              placeholder="filter..."
              style={{
                flex: 1, background: bg, border: `1px solid ${border}`,
                borderRadius: 3, padding: '2px 6px', color: text, fontSize: 11,
              }}
            />
          </div>
          <div style={{ flex: 1, overflow: 'auto' }}>
            {filtered.map(f => (
              <div key={f.field}
                onClick={(e) => handleFieldSelect(f, e)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6, padding: '3px 8px',
                  cursor: 'pointer', borderBottom: `1px solid ${border}`,
                  background: selectedPaths.has(f.field) ? highlight : 'transparent',
                }}
              >
                <span style={{ flex: 1, fontSize: 12 }}>{f.label}</span>
                <span style={{ fontSize: 10, color: textMuted, maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis' }}>{f.field}</span>
                <span style={{ fontSize: 10, color: textMuted, width: 50, textAlign: 'right' }}>{f.type}</span>
              </div>
            ))}
            {filtered.length === 0 && (
              <div style={{ padding: '12px 8px', color: textMuted, fontSize: 11 }}>
                {allFields.length === 0 ? 'Select a model' : 'No matches'}
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};

export default TokenBuilder;

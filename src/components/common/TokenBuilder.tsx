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

const TokenBuilder: React.FC<TokenBuilderProps> = ({ model: initialModel, onClose }) => {
  const [allModels, setAllModels] = useState<string[]>([]);
  const [activeModel, setActiveModel] = useState(initialModel || '');
  const [registry, setRegistry] = useState<ReportFieldsResponse | null>(null);
  const [selected, setSelected] = useState<RegistryField[]>([]);
  const [mode, setMode] = useState<'detail' | 'list'>('detail');
  const [filter, setFilter] = useState('');
  const [copied, setCopied] = useState('');
  const registryCache = useRef<Record<string, ReportFieldsResponse>>({});
  const filterRef = useRef<HTMLInputElement>(null);

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
    <div className="db-bg db-text" style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      fontSize: 13, fontFamily: 'system-ui, sans-serif',
    }}>
      {/* Toolbar */}
      <div className="db-section-bg" style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px',
      }}>
        <span className="db-text-accent db-font-bolder">{'{{'}Tokens{'}}'}</span>
        <button onClick={handleClear}
          className="db-text-muted db-border-all" style={{ background: 'none', borderRadius: 3, padding: '2px 8px', cursor: 'pointer', fontSize: 11 }}>
          Clear
        </button>
        <div style={{ display: 'flex', gap: 2, marginLeft: 4 }}>
          <button onClick={() => setMode('detail')}
            className={`db-font-bold db-font-sm db-border-all ${mode === 'detail' ? 'db-btn--ghost' : 'db-text-muted'}`}
            style={{ background: mode === 'detail' ? 'var(--db-accent)' : 'none', color: mode === 'detail' ? '#000' : undefined, borderRadius: '3px 0 0 3px', padding: '2px 8px', cursor: 'pointer' }}>
            Detail
          </button>
          <button onClick={() => setMode('list')}
            className={`db-font-bold db-font-sm db-border-all ${mode === 'list' ? 'db-btn--ghost' : 'db-text-muted'}`}
            style={{ background: mode === 'list' ? 'var(--db-accent)' : 'none', color: mode === 'list' ? '#000' : undefined, borderRadius: '0 3px 3px 0', padding: '2px 8px', cursor: 'pointer' }}>
            List
          </button>
        </div>
        {selected.length > 0 && (
          <button onClick={handleCopyAll}
            className="db-btn db-btn--save db-font-bold db-font-sm" style={{ marginLeft: 'auto' }}>
            Copy All ({selected.length})
          </button>
        )}
        {copied && (
          <span className="db-text-green db-font-sm" style={{ marginLeft: 'auto' }}>{copied}</span>
        )}
        {onClose && (
          <button onClick={onClose}
            className="db-text-muted" style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, marginLeft: onClose && !copied ? 'auto' : 0 }}>
            ×
          </button>
        )}
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* Selected fields (top tier in WC2) */}
        <div style={{ flex: '0 0 50%', display: 'flex', flexDirection: 'column', borderRight: '1px solid var(--db-border)' }}>
          {/* Selected list */}
          <div style={{ flex: 1, overflow: 'auto', padding: 0 }}>
            <div className="db-text-muted db-bg-surface-alt db-border-bottom db-font-sm" style={{ padding: '4px 8px' }}>
              Selected ({selected.length}) — click to copy, shift-click in field list to add
            </div>
            {selected.map(f => (
              <div key={f.field}
                onClick={() => handleFieldClick(f)}
                className="db-border-bottom-light"
                style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '3px 8px', cursor: 'pointer' }}
              >
                <span className="db-font-base" style={{ flex: 1 }}>{`{{${f.field}}}`}</span>
                <span className="db-text-muted db-font-xs">{f.type}</span>
                <span onClick={(e) => { e.stopPropagation(); handleRemove(f.field); }}
                  className="db-text-muted" style={{ cursor: 'pointer', fontSize: 14 }}>×</span>
              </div>
            ))}
            {selected.length === 0 && (
              <div className="db-text-muted db-font-sm" style={{ padding: '12px 8px' }}>
                Shift-click fields to build a set. Click any field to copy its token.
              </div>
            )}
          </div>

          {/* Line fields (if model has lines) */}
          {lineFields.length > 0 && (
            <div className="db-border-top">
              <div className="db-text-muted db-bg-surface-alt db-font-sm" style={{ padding: '4px 8px' }}>
                Line fields ({lineFields.length})
              </div>
              <div style={{ maxHeight: 120, overflow: 'auto' }}>
                {lineFields.map(f => (
                  <div key={f.field}
                    onClick={(e) => handleFieldSelect(f, e)}
                    className={`db-border-bottom-light ${selectedPaths.has(f.field) ? 'db-bg-row-active' : ''}`}
                    style={{ display: 'flex', gap: 6, padding: '2px 8px', cursor: 'pointer' }}
                  >
                    <span className="db-font-base" style={{ flex: 1 }}>{f.label}</span>
                    <span className="db-text-muted db-font-xs">{f.field}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Model selector (bottom tier in WC2) */}
          <div className="db-border-top" style={{ maxHeight: 140, overflow: 'auto' }}>
            <div className="db-text-muted db-bg-surface-alt db-font-sm" style={{ padding: '4px 8px' }}>
              Models
            </div>
            {allModels.map(m => (
              <div key={m}
                onClick={() => fetchFields(m)}
                className={`db-font-base ${m === activeModel ? 'db-bg-row-active db-font-bold' : ''}`}
                style={{ padding: '2px 8px', cursor: 'pointer' }}
              >
                {m}
              </div>
            ))}
          </div>
        </div>

        {/* Available fields (middle tier in WC2) */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div className="db-section-bg" style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '4px 8px',
          }}>
            <span className="db-text-muted db-font-sm">{activeModel} fields</span>
            <input
              ref={filterRef}
              value={filter}
              onChange={e => setFilter(e.target.value)}
              placeholder="filter..."
              className="db-panel-input-text db-font-sm"
              style={{ flex: 1, borderRadius: 3, padding: '2px 6px' }}
            />
          </div>
          <div style={{ flex: 1, overflow: 'auto' }}>
            {filtered.map(f => (
              <div key={f.field}
                onClick={(e) => handleFieldSelect(f, e)}
                className={`db-border-bottom-light ${selectedPaths.has(f.field) ? 'db-bg-row-active' : ''}`}
                style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '3px 8px', cursor: 'pointer' }}
              >
                <span className="db-font-base" style={{ flex: 1 }}>{f.label}</span>
                <span className="db-text-muted db-font-xs" style={{ maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis' }}>{f.field}</span>
                <span className="db-text-muted db-font-xs" style={{ width: 50, textAlign: 'right' }}>{f.type}</span>
              </div>
            ))}
            {filtered.length === 0 && (
              <div className="db-text-muted db-font-sm" style={{ padding: '12px 8px' }}>
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

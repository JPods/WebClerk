/**
 * JsonEnvelopePanel — DataBrowser plugin.
 *
 * Shows all JSON envelope fields (metadata, prefs, config, refs)
 * for the selected record in a collapsible panel with JsonTree widgets.
 * Click any field label → opens full JSON Tree editor in a floating window.
 * Edits in the floating window flow back to the record on close.
 *
 * Usage:
 *   <JsonEnvelopePanel record={record} onChange={handleFieldChange} modelName="order" recordId={34} />
 */
import React, { useState, useCallback, useEffect, useRef } from 'react';
import { JsonTree } from '@/components/widgets/JsonTreeWidget';

// prefs and config are always editable; metadata and refs require json_expert pref
const ENVELOPE_FIELDS = [
  { key: 'metadata', label: 'Metadata', expertOnly: true },
  { key: 'prefs',    label: 'Prefs',    expertOnly: false },
  { key: 'config',   label: 'Config',   expertOnly: false },
  { key: 'refs',     label: 'Refs',     expertOnly: true },
] as const;

interface JsonEnvelopePanelProps {
  record: Record<string, any>;
  onChange?: (field: string, value: any) => void;
  modelName?: string;
  recordId?: number | string;
  jsonExpert?: boolean;  // from user.prefs.staff.json_expert — unlocks metadata/refs editing
  fontSize?: number;
  style?: React.CSSProperties;
}

// ── Floating JSON editor window ──────────────────────────────────────

function FloatingJsonEditor({ field, label, data, modelName, recordId, onSave, onClose }: {
  field: string; label: string; data: any; modelName?: string; recordId?: number | string;
  onSave: (data: any) => void; onClose: () => void;
}) {
  const [code, setCode] = useState(() => JSON.stringify(data, null, 2));
  const [treeData, setTreeData] = useState(data);
  const [error, setError] = useState('');
  const overlayRef = useRef<HTMLDivElement>(null);

  const handleCodeChange = useCallback((text: string) => {
    setCode(text);
    try { const parsed = JSON.parse(text); setTreeData(parsed); setError(''); }
    catch (e: any) { setError(e.message); }
  }, []);

  const handleTreeChange = useCallback((newData: any) => {
    setTreeData(newData);
    setCode(JSON.stringify(newData, null, 2));
    setError('');
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const title = [modelName, recordId ? `#${recordId}` : '', label].filter(Boolean).join(' ');

  const handleSave = () => { if (!error) { onSave(treeData); onClose(); } };

  return (
    <div ref={overlayRef} className="db-dialog-overlay" style={{ zIndex: 9999 }}
      onClick={e => { if (e.target === overlayRef.current) onClose(); }}>
      <div className="db-panel-input" style={{ width: '90vw', maxWidth: 1200, height: '85vh', display: 'flex', flexDirection: 'column',
        borderRadius: 8, boxShadow: '0 20px 60px rgba(0,0,0,0.3)', overflow: 'hidden' }}>
        {/* Title bar */}
        <div className="db-section-bg db-flex-between" style={{ padding: '8px 16px', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span className="db-text db-font-bolder" style={{ fontSize: 13 }}>{title}</span>
            {error && <span className="db-font-mono" style={{ fontSize: 11, color: '#f87171' }}>{error}</span>}
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button onClick={handleSave} disabled={!!error}
              className="db-btn db-btn--primary" style={{ borderRadius: 4,
                background: error ? '#64748b' : undefined, cursor: error ? 'not-allowed' : 'pointer' }}>
              Save
            </button>
            <button onClick={onClose}
              className="db-btn" style={{ borderRadius: 4 }}>
              Close
            </button>
          </div>
        </div>
        {/* Split pane */}
        <div style={{ flex: 1, minHeight: 0, display: 'flex', overflow: 'hidden' }}>
          {/* Code — left */}
          <div style={{ width: '45%', display: 'flex', flexDirection: 'column', borderRight: '1px solid var(--db-border)' }}>
            <div className="db-section-bg db-text-muted db-font-bold" style={{ padding: '3px 10px', fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.06em', flexShrink: 0 }}>
              Code
            </div>
            <textarea value={code} onChange={e => handleCodeChange(e.target.value)} spellCheck={false}
              className="db-panel-input-text" style={{ flex: 1, resize: 'none', border: 'none', outline: 'none', padding: 12,
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace", fontSize: 11, lineHeight: 1.6, tabSize: 2 }} />
          </div>
          {/* Tree — right */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
            <div className="db-section-bg db-text-muted db-font-bold" style={{ padding: '3px 10px', fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.06em', flexShrink: 0 }}>
              Tree
            </div>
            <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 8 }}>
              {error ? (
                <div className="db-text-muted" style={{ padding: 32, textAlign: 'center', fontSize: 12 }}>
                  Fix the JSON to see the tree
                </div>
              ) : (
                <JsonTree data={treeData} onChange={handleTreeChange} defaultExpanded maxHeight="none"
                  style={{ border: 'none', background: 'transparent' }} />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main panel ───────────────────────────────────────────────────────

export default function JsonEnvelopePanel({
  record, onChange, modelName, recordId, jsonExpert = false, fontSize = 12, style,
}: JsonEnvelopePanelProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [floatingField, setFloatingField] = useState<string | null>(null);

  const present = ENVELOPE_FIELDS.filter(f => record[f.key] != null && typeof record[f.key] === 'object');
  if (present.length === 0) return null;

  const handleLabelClick = useCallback((key: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setFloatingField(key);
  }, []);

  const handleFloatSave = useCallback((field: string, data: any) => {
    if (onChange) onChange(field, data);
  }, [onChange]);

  const floatingEntry = floatingField ? present.find(f => f.key === floatingField) : null;

  return (
    <>
      <div className="db-panel-input" style={{ borderRadius: 6, overflow: 'hidden', ...style }}>
        {/* header */}
        <div
          className="db-bg-surface-alt"
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '6px 12px', borderBottom: collapsed ? 'none' : '1px solid var(--db-border)',
            cursor: 'pointer', userSelect: 'none',
          }}
          onClick={() => setCollapsed(!collapsed)}
        >
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="var(--db-text-muted)" strokeWidth="1.5">
            {collapsed ? <path d="M3 1 L7 5 L3 9" /> : <path d="M1 3 L5 7 L9 3" />}
          </svg>
          <span className="db-text-muted db-font-bold" style={{ fontSize: fontSize - 1, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            JSON Envelopes
          </span>
          <span className="db-text-muted" style={{ fontSize: fontSize - 2, fontWeight: 400 }}>
            ({present.length})
          </span>
        </div>

        {/* body */}
        {!collapsed && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 8, padding: 8 }}>
            {present.map(({ key, label, expertOnly }) => {
            const readOnly = !onChange || (expertOnly && !jsonExpert);
            return (
              <JsonTree
                key={key}
                data={record[key]}
                label={label}
                readOnly={readOnly}
                onChange={readOnly ? undefined : (d) => onChange!(key, d)}
                onLabelClick={(e) => handleLabelClick(key, e)}
              />
            );
          })}
          </div>
        )}
      </div>

      {/* Floating editor */}
      {floatingEntry && (
        <FloatingJsonEditor
          field={floatingEntry.key}
          label={floatingEntry.label}
          data={record[floatingEntry.key]}
          modelName={modelName}
          recordId={recordId}
          onSave={(d) => handleFloatSave(floatingEntry.key, d)}
          onClose={() => setFloatingField(null)}
        />
      )}
    </>
  );
}

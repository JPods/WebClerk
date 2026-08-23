import React, { useCallback, useState, useEffect, useRef } from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';
import { JsonTree } from '@/components/widgets/JsonTreeWidget';

// ── Floating JSON editor (split-pane: code left, tree right) ────────

function JsonFloatingEditor({ name, data, onChange, onClose }: {
  name: string; data: any; onChange: (v: any) => void; onClose: () => void;
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

  const handleSave = () => {
    if (error) return;
    onChange(treeData);
    onClose();
  };

  return (
    <div ref={overlayRef} className="db-json-overlay"
      onClick={e => { if (e.target === overlayRef.current) onClose(); }}>
      <div className="db-json-editor">
        <div className="db-json-editor-titlebar">
          <div className="db-json-editor-title">
            <span>{name}</span>
            {error && <span className="db-json-editor-error">{error}</span>}
          </div>
          <div className="db-json-editor-actions">
            <button onClick={handleSave} disabled={!!error} className="db-json-editor-save">Save</button>
            <button onClick={onClose} className="db-json-editor-close">Close</button>
          </div>
        </div>
        <div className="db-json-editor-body">
          <div className="db-json-editor-code">
            <div className="db-json-editor-pane-label">Code</div>
            <textarea className="db-json-editor-textarea" value={code}
              onChange={e => handleCodeChange(e.target.value)} spellCheck={false} />
          </div>
          <div className="db-json-editor-tree">
            <div className="db-json-editor-pane-label">Tree</div>
            <div className="db-json-editor-tree-scroll">
              {error ? (
                <div className="db-json-editor-tree-empty">Fix the JSON to see the tree</div>
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

// ── JsonField — textarea editor with floating split-pane ────────

export default function JsonField(props: FieldWidgetProps & { rows?: number }) {
  const { name, value, onChange, disabled, rows } = props;
  const [editorOpen, setEditorOpen] = useState(false);
  const js = JSON.stringify(value, null, 2);
  const rowCount = rows || (js.length > 200 ? 8 : 3);

  return (
    <BaseField props={{ ...props, span2: true }} labelColor="actionable"
      labelOnClick={() => setEditorOpen(true)}
      labelSuffix={<span className="db-json-count">({js.length})</span>}>
      <textarea className="db-input db-input--mono db-input--textarea" rows={rowCount} value={js}
        onChange={(e) => { try { onChange(JSON.parse(e.target.value)); } catch { /* typing */ } }}
        disabled={disabled} />
      {editorOpen && <JsonFloatingEditor name={name} data={value} onChange={onChange}
        onClose={() => setEditorOpen(false)} />}
    </BaseField>
  );
}

// ── JsonTreeField — tree-only view with optional floating editor ────────

export function JsonTreeField(props: FieldWidgetProps & { readOnly?: boolean }) {
  const { name, value, onChange, readOnly } = props;
  const [editorOpen, setEditorOpen] = useState(false);

  return (
    <BaseField props={{ ...props, span2: true }}>
      <JsonTree data={value as any} onChange={readOnly ? undefined : (d) => onChange(d)}
        readOnly={readOnly} label={name}
        onLabelClick={() => setEditorOpen(true)} />
      {editorOpen && <JsonFloatingEditor name={name} data={value} onChange={onChange}
        onClose={() => setEditorOpen(false)} />}
    </BaseField>
  );
}

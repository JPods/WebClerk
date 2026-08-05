/**
 * JsonTreeWidget — tree editor for JSON envelope fields.
 *
 * Registered as 'json-tree' in WIDGETS.
 * Replaces raw textarea for prefs, metadata, config, refs.
 * Same WidgetProps contract as all other widgets.
 *
 * Three usage levels:
 *   Widget  — field-level renderer in BehaviorField / DynamicDetail
 *   Plugin  — DataBrowser panel showing all JSON envelopes for selected record
 *   Applet  — standalone page at /json-tree for exploring any JSON
 */
import React, { useState, useCallback, useRef, useEffect } from 'react';
import type { WidgetProps } from './types';

// ═══════════════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════════════

type JsonValue = string | number | boolean | null | JsonValue[] | { [k: string]: JsonValue };

function typeOf(v: any): string {
  if (v === null) return 'null';
  if (Array.isArray(v)) return 'array';
  return typeof v;
}

function typeLabel(v: any): string {
  const t = typeOf(v);
  if (t === 'array') return `[${v.length}]`;
  if (t === 'object') return `{${Object.keys(v).length}}`;
  return t;
}

const TYPE_COLORS: Record<string, string> = {
  string: '#198754', number: '#0d6efd', boolean: '#d97706', null: '#adb5bd',
};

function isContainer(v: any): v is Record<string, any> | any[] {
  return v !== null && typeof v === 'object';
}

function defaultForType(type: string): JsonValue {
  const map: Record<string, JsonValue> = { string: '', number: 0, boolean: false, null: null, object: {}, array: [] };
  return map[type] ?? '';
}

function setAtPath(root: any, path: (string | number)[], value: any): any {
  if (path.length === 0) return value;
  const copy = Array.isArray(root) ? [...root] : { ...root };
  const [head, ...rest] = path;
  copy[head] = rest.length === 0 ? value : setAtPath(copy[head], rest, value);
  return copy;
}

function removeAtPath(root: any, path: (string | number)[]): any {
  if (path.length === 0) return root;
  if (path.length === 1) {
    if (Array.isArray(root)) { const c = [...root]; c.splice(path[0] as number, 1); return c; }
    const { [path[0] as string]: _, ...rest } = root;
    return rest;
  }
  const copy = Array.isArray(root) ? [...root] : { ...root };
  const [head, ...rest] = path;
  copy[head] = removeAtPath(copy[head], rest);
  return copy;
}

function addKeyAtPath(root: any, path: (string | number)[], key: string, value: any): any {
  const target = path.reduce((o, k) => o[k], root);
  if (Array.isArray(target)) return setAtPath(root, path, [...target, value]);
  return setAtPath(root, path, { ...target, [key]: value });
}

// ═══════════════════════════════════════════════════════════════════════
// Inline value editor
// ═══════════════════════════════════════════════════════════════════════

function ValueEditor({ value, onCommit, onCancel }: {
  value: any; onCommit: (v: JsonValue) => void; onCancel: () => void;
}) {
  const ref = useRef<HTMLInputElement>(null);
  const t = typeOf(value);

  useEffect(() => { ref.current?.focus(); ref.current?.select(); }, []);

  if (t === 'boolean') {
    return <button onClick={() => onCommit(!value)}
      style={{ padding: '1px 6px', borderRadius: 3, fontSize: 11, fontFamily: 'monospace', background: '#f1f5f9', border: '1px solid #e2e8f0', cursor: 'pointer' }}>
      {String(!value)}
    </button>;
  }

  const commit = (raw: string) => {
    if (t === 'null' && raw === '') { onCommit(null); return; }
    if (t === 'number') { const n = Number(raw); onCommit(isNaN(n) ? raw : n); return; }
    onCommit(raw);
  };

  return <input ref={ref}
    style={{ padding: '1px 6px', borderRadius: 3, fontSize: 11, fontFamily: 'monospace', background: '#f1f5f9', border: '1px solid #cbd5e1', width: t === 'null' ? 100 : 160, outline: 'none' }}
    defaultValue={t === 'null' ? '' : String(value)}
    placeholder={t === 'null' ? 'type a value...' : undefined}
    onKeyDown={e => { if (e.key === 'Enter') commit((e.target as HTMLInputElement).value); if (e.key === 'Escape') onCancel(); }}
    onBlur={e => commit(e.target.value)}
  />;
}

// ═══════════════════════════════════════════════════════════════════════
// Add key dialog (inline)
// ═══════════════════════════════════════════════════════════════════════

function AddKeyDialog({ isArray, onAdd, onCancel }: {
  isArray: boolean; onAdd: (key: string, type: string) => void; onCancel: () => void;
}) {
  const ref = useRef<HTMLInputElement>(null);
  const [type, setType] = useState('string');
  useEffect(() => { ref.current?.focus(); }, []);

  const selectStyle: React.CSSProperties = { padding: '1px 4px', borderRadius: 3, fontSize: 11, fontFamily: 'monospace', background: '#f1f5f9', border: '1px solid #e2e8f0' };
  const btnStyle: React.CSSProperties = { padding: '1px 6px', borderRadius: 3, fontSize: 11, cursor: 'pointer', border: 'none' };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4, paddingLeft: 16, paddingTop: 2, paddingBottom: 2 }}>
      {!isArray && <input ref={ref}
        style={{ ...selectStyle, width: 90 }}
        placeholder="key name"
        onKeyDown={e => { if (e.key === 'Enter') onAdd((e.target as HTMLInputElement).value, type); if (e.key === 'Escape') onCancel(); }}
      />}
      <select style={selectStyle} value={type} onChange={e => setType(e.target.value)}>
        {['string', 'number', 'boolean', 'null', 'object', 'array'].map(t => <option key={t} value={t}>{t}</option>)}
      </select>
      <button style={{ ...btnStyle, background: '#465fff', color: '#fff' }}
        onClick={() => { const key = isArray ? '' : (ref.current?.value || ''); if (isArray || key) onAdd(key, type); }}>Add</button>
      <button style={{ ...btnStyle, color: '#6c757d' }} onClick={onCancel}>Cancel</button>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// Tree node
// ═══════════════════════════════════════════════════════════════════════

interface NodeProps {
  keyName: string | number;
  value: any;
  path: (string | number)[];
  depth: number;
  maxDepth: number;
  expanded: Set<string>;
  editing: string | null;
  adding: string | null;
  readOnly: boolean;
  onToggle: (p: string) => void;
  onEdit: (p: string | null) => void;
  onAdd: (p: string | null) => void;
  onChange: (path: (string | number)[], value: any) => void;
  onRemove: (path: (string | number)[]) => void;
  onAddKey: (path: (string | number)[], key: string, type: string) => void;
  isArrayItem: boolean;
  theme: { text: string; textMuted: string; border: string; surfaceAlt: string; inputBg: string };
}

function TreeNode({
  keyName, value, path, depth, maxDepth, expanded, editing, adding,
  readOnly, onToggle, onEdit, onAdd, onChange, onRemove, onAddKey,
  isArrayItem, theme: th,
}: NodeProps) {
  const pathStr = path.join('.');
  const container = isContainer(value);
  const isExpanded = expanded.has(pathStr);
  const isEditing = editing === pathStr;
  const isAdding = adding === pathStr;
  const t = typeOf(value);
  const [hovered, setHovered] = useState(false);

  const rowStyle: React.CSSProperties = {
    display: 'flex', alignItems: 'center', gap: 2,
    paddingLeft: depth * 16 + 4, paddingRight: 8, paddingTop: 2, paddingBottom: 2,
    borderRadius: 3, background: isEditing ? '#eff6ff' : hovered ? th.surfaceAlt : 'transparent',
    transition: 'background 150ms',
  };

  const chevron = container ? (
    <button onClick={() => onToggle(pathStr)}
      style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 16, height: 16, border: 'none', background: 'none', cursor: 'pointer', color: th.textMuted, padding: 0, flexShrink: 0 }}>
      <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
        {isExpanded ? <path d="M1 3 L5 7 L9 3" fill="none" stroke="currentColor" strokeWidth="1.5" /> : <path d="M3 1 L7 5 L3 9" fill="none" stroke="currentColor" strokeWidth="1.5" />}
      </svg>
    </button>
  ) : <span style={{ width: 16, flexShrink: 0 }} />;

  const keyLabel = <span style={{ fontSize: 11, fontFamily: 'monospace', color: isArrayItem ? th.textMuted : th.text, flexShrink: 0 }}>
    {isArrayItem ? `[${keyName}]` : String(keyName)}
  </span>;

  const colon = <span style={{ color: th.textMuted, fontSize: 11, margin: '0 2px' }}>:</span>;

  let valueEl: React.ReactNode;
  if (isEditing && !container) {
    valueEl = <ValueEditor value={value} onCommit={v => { onChange(path, v); onEdit(null); }} onCancel={() => onEdit(null)} />;
  } else if (container) {
    valueEl = <span style={{ fontSize: 11, fontFamily: 'monospace', color: th.textMuted }}>{typeLabel(value)}</span>;
  } else {
    valueEl = <span
      style={{ fontSize: 11, fontFamily: 'monospace', color: TYPE_COLORS[t] || th.text, cursor: readOnly ? 'default' : 'pointer', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
      onClick={() => !readOnly && onEdit(pathStr)}
      title={String(value)}>
      {t === 'string' ? `"${value}"` : String(value)}
    </span>;
  }

  const actions = !readOnly && hovered ? (
    <span style={{ marginLeft: 'auto', display: 'flex', gap: 2, flexShrink: 0 }}>
      {container && depth < maxDepth && (
        <button onClick={() => onAdd(pathStr)} title={Array.isArray(value) ? 'Add item' : 'Add key'}
          style={{ border: 'none', background: 'none', cursor: 'pointer', color: th.textMuted, padding: '0 2px', fontSize: 13 }}>+</button>
      )}
      {depth > 0 && (
        <button onClick={() => onRemove(path)} title="Remove"
          style={{ border: 'none', background: 'none', cursor: 'pointer', color: th.textMuted, padding: '0 2px', fontSize: 11 }}>✕</button>
      )}
    </span>
  ) : null;

  const renderChildren = () => {
    if (!container || !isExpanded || depth >= maxDepth) return null;
    const entries = Array.isArray(value)
      ? value.map((item, i) => ({ k: i, v: item, isArr: true }))
      : Object.entries(value).map(([k, v]) => ({ k, v, isArr: false }));
    return (
      <div>
        {entries.map(({ k, v, isArr }) => (
          <TreeNode key={`${pathStr}.${k}`} keyName={k} value={v} path={[...path, k]}
            depth={depth + 1} maxDepth={maxDepth} expanded={expanded} editing={editing}
            adding={adding} readOnly={readOnly} onToggle={onToggle} onEdit={onEdit}
            onAdd={onAdd} onChange={onChange} onRemove={onRemove} onAddKey={onAddKey}
            isArrayItem={isArr} theme={th} />
        ))}
        {isAdding && <AddKeyDialog isArray={Array.isArray(value)}
          onAdd={(key, type) => { onAddKey(path, key, type); onAdd(null); }}
          onCancel={() => onAdd(null)} />}
      </div>
    );
  };

  return (
    <div>
      <div style={rowStyle} onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}>
        {chevron}{keyLabel}{colon}{valueEl}{actions}
      </div>
      {renderChildren()}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// Core tree component (used by widget, plugin, and applet)
// ═══════════════════════════════════════════════════════════════════════

export interface JsonTreeProps {
  data: Record<string, any> | any[] | null;
  onChange?: (data: Record<string, any> | any[]) => void;
  readOnly?: boolean;
  defaultExpanded?: boolean | string[];
  maxDepth?: number;
  maxHeight?: number | 'none';
  label?: string;
  onLabelClick?: (e: React.MouseEvent) => void;
  theme?: { text: string; textMuted: string; border: string; surfaceAlt: string; inputBg: string };
  style?: React.CSSProperties;
}

export function JsonTree({
  data, onChange, readOnly = false, defaultExpanded = false,
  maxDepth = 10, maxHeight = 384, label, onLabelClick, theme, style,
}: JsonTreeProps) {
  const safeData = data ?? {};
  const th = theme || { text: '#212529', textMuted: '#6c757d', border: '#dee2e6', surfaceAlt: '#f8f9fa', inputBg: '#fff' };

  const buildExpanded = useCallback((): Set<string> => {
    if (defaultExpanded === false) return new Set<string>();
    if (defaultExpanded === true) {
      const paths = new Set<string>();
      const walk = (obj: any, prefix: string) => {
        if (!isContainer(obj)) return;
        paths.add(prefix);
        if (Array.isArray(obj)) obj.forEach((v, i) => walk(v, prefix ? `${prefix}.${i}` : String(i)));
        else Object.entries(obj).forEach(([k, v]) => walk(v, prefix ? `${prefix}.${k}` : k));
      };
      walk(safeData, '');
      return paths;
    }
    return new Set(defaultExpanded);
  }, []);

  const [expanded, setExpanded] = useState(buildExpanded);
  const [editing, setEditing] = useState<string | null>(null);
  const [adding, setAdding] = useState<string | null>(null);

  const handleToggle = useCallback((p: string) => {
    setExpanded(prev => { const n = new Set(prev); if (n.has(p)) n.delete(p); else n.add(p); return n; });
  }, []);

  const handleChange = useCallback((path: (string | number)[], value: any) => {
    if (!onChange) return;
    onChange(path.length === 0 ? value : setAtPath(safeData, path, value));
  }, [safeData, onChange]);

  const handleRemove = useCallback((path: (string | number)[]) => {
    if (!onChange || path.length === 0) return;
    onChange(removeAtPath(safeData, path));
  }, [safeData, onChange]);

  const handleAddKey = useCallback((path: (string | number)[], key: string, type: string) => {
    if (!onChange) return;
    onChange(addKeyAtPath(safeData, path, key, defaultForType(type)));
    setExpanded(prev => new Set(prev).add(path.join('.')));
  }, [safeData, onChange]);

  const expandAll = useCallback(() => {
    const paths = new Set<string>();
    const walk = (obj: any, prefix: string) => {
      if (!isContainer(obj)) return;
      paths.add(prefix);
      if (Array.isArray(obj)) obj.forEach((v, i) => walk(v, prefix ? `${prefix}.${i}` : String(i)));
      else Object.entries(obj).forEach(([k, v]) => walk(v, prefix ? `${prefix}.${k}` : k));
    };
    walk(safeData, '');
    setExpanded(paths);
  }, [safeData]);

  const collapseAll = useCallback(() => setExpanded(new Set()), []);

  const isEmpty = isContainer(safeData)
    ? (Array.isArray(safeData) ? safeData.length === 0 : Object.keys(safeData).length === 0)
    : true;

  const toolbarBtnStyle: React.CSSProperties = {
    padding: '1px 6px', borderRadius: 3, fontSize: 11, border: 'none', cursor: 'pointer',
    background: 'none', color: th.textMuted,
  };

  return (
    <div style={{ border: `1px solid ${th.border}`, borderRadius: 6, overflow: 'hidden', background: th.inputBg, ...style }}>
      {/* toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 10px', borderBottom: `1px solid ${th.border}`, background: th.surfaceAlt }}>
        {label && <span onClick={onLabelClick} style={{ fontSize: 10, fontWeight: 600, color: onLabelClick ? th.text : th.textMuted, textTransform: 'uppercase', letterSpacing: '0.04em', cursor: onLabelClick ? 'pointer' : 'default' }} title={onLabelClick ? 'Click to open in editor' : undefined}>{label}</span>}
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 2 }}>
          <button style={toolbarBtnStyle} onClick={expandAll}>Expand</button>
          <button style={toolbarBtnStyle} onClick={collapseAll}>Collapse</button>
          {!readOnly && !isEmpty && <button style={{ ...toolbarBtnStyle, fontSize: 13 }} onClick={() => setAdding('')} title="Add top-level key">+</button>}
        </span>
      </div>
      {/* body */}
      <div style={{ padding: '4px 4px', maxHeight: maxHeight === 'none' ? undefined : maxHeight, overflowY: 'auto', fontFamily: 'monospace', fontSize: 11, flex: maxHeight === 'none' ? 1 : undefined }}>
        {isEmpty ? (
          <div style={{ textAlign: 'center', padding: 16, color: th.textMuted, fontSize: 11 }}>
            {readOnly ? 'Empty' : <button style={{ background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline', color: th.textMuted }} onClick={() => setAdding('')}>Add first key</button>}
          </div>
        ) : (
          <>
            {(Array.isArray(safeData)
              ? safeData.map((item, i) => ({ k: i, v: item, isArr: true }))
              : Object.entries(safeData).map(([k, v]) => ({ k, v, isArr: false }))
            ).map(({ k, v, isArr }) => (
              <TreeNode key={k} keyName={k} value={v} path={[k]} depth={0} maxDepth={maxDepth}
                expanded={expanded} editing={editing} adding={adding} readOnly={readOnly}
                onToggle={handleToggle} onEdit={setEditing} onAdd={setAdding}
                onChange={handleChange} onRemove={handleRemove} onAddKey={handleAddKey}
                isArrayItem={isArr} theme={th} />
            ))}
            {adding === '' && <AddKeyDialog isArray={Array.isArray(safeData)}
              onAdd={(key, type) => { handleAddKey([], key, type); setAdding(null); }}
              onCancel={() => setAdding(null)} />}
          </>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// Widget wrapper — implements WidgetProps for the WIDGETS registry
// ═══════════════════════════════════════════════════════════════════════

export const JsonTreeWidgetAdapter: React.FC<WidgetProps> = ({
  name, value, onChange, disabled, mode, record,
}) => {
  if (mode === 'print') {
    const js = JSON.stringify(value, null, 2);
    return <pre style={{ fontSize: 9, fontFamily: 'monospace', whiteSpace: 'pre-wrap', margin: 0 }}>{js}</pre>;
  }

  const parsed = typeof value === 'string' ? (() => { try { return JSON.parse(value); } catch { return value; } })() : value;

  if (!isContainer(parsed)) {
    return <span style={{ fontSize: 11, fontFamily: 'monospace', color: '#6c757d' }}>{String(parsed ?? '—')}</span>;
  }

  return <JsonTree
    data={parsed}
    onChange={disabled ? undefined : onChange}
    readOnly={!!disabled}
    label={name}
  />;
};

/**
 * MarkdownEditor — View, edit, and template markdown with field tokens.
 *
 * Features:
 *   - View mode: rendered markdown
 *   - Edit mode: split editor + preview (via @uiw/react-md-editor)
 *   - Token insertion: {{field.path}} tokens populated from record or list data
 *   - Submit to WC_HQ: user contributions flow upstream via Alice Action record
 *
 * Token syntax:
 *   {{field.path}}           — resolved from record data (dot-notation)
 *   {{field.path|currency}}  — with format hint (currency, date, number, percent)
 *   {{#each lines}}...{{/each}} — iterate over a list field
 *
 * The document type gives quantity.active its meaning. The template context
 * gives {{tokens}} their meaning. Same principle.
 *
 * LastChecked: 2026-08-05 | WhereUsed: standalone, DataBrowser tabs | WhoCreated: Bill+Claude
 */
import React, { useState, useCallback, useRef, useMemo } from 'react';
import MDEditor from '@uiw/react-md-editor';
import { saveRecord } from '@/api/wcapi';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface MarkdownEditorProps {
  /** Markdown content */
  value: string;
  /** Called when content changes (edit mode) */
  onChange?: (value: string) => void;
  /** Start in edit mode */
  defaultEdit?: boolean;
  /** Read-only — no edit toggle */
  readOnly?: boolean;
  /** Record data for token resolution */
  record?: Record<string, any>;
  /** List data for {{#each}} resolution */
  listData?: Record<string, any>[];
  /** Model name (for field path autocomplete and WC_HQ submit) */
  modelName?: string;
  /** Available field paths (passed in or auto-fetched) */
  fieldPaths?: FieldPath[];
  /** Template name (for saving/submitting) */
  templateName?: string;
  /** Called after submit to WC_HQ */
  onSubmit?: (actionId: number) => void;
  /** Height in px */
  height?: number;
  /** Dark mode override */
  darkMode?: boolean;
}

export interface FieldPath {
  path: string;       // e.g. "quantity.active"
  label: string;      // e.g. "Quantity Active"
  type?: string;      // e.g. "number", "string", "date"
  format?: string;    // e.g. "currency", "date"
}

// ---------------------------------------------------------------------------
// Token resolution — same dot-notation as UniversalPrint
// ---------------------------------------------------------------------------

function resolve(data: any, path: string): unknown {
  if (!data || !path) return undefined;
  return path.split('.').reduce((obj: any, key: string) => obj?.[key], data);
}

function formatValue(v: unknown, format?: string): string {
  if (v == null || v === '') return '';
  if (format === 'currency') {
    const n = Number(v);
    return isNaN(n) ? String(v) : n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 });
  }
  if (format === 'date') {
    if (typeof v === 'number') {
      const ms = v > 1e12 ? v : v * 1000;
      return new Date(ms).toLocaleDateString();
    }
    const d = new Date(String(v));
    return isNaN(d.getTime()) ? String(v) : d.toLocaleDateString();
  }
  if (format === 'number') {
    const n = Number(v);
    return isNaN(n) ? String(v) : n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  if (format === 'percent') {
    const n = Number(v);
    return isNaN(n) ? String(v) : (n * 100).toFixed(1) + '%';
  }
  return String(v);
}

/**
 * Resolve all {{token}} and {{token|format}} in markdown text.
 * Also handles {{#each fieldName}}...{{/each}} blocks.
 */
export function resolveTokens(
  markdown: string,
  record?: Record<string, any>,
  listData?: Record<string, any>[],
): string {
  if (!markdown) return '';

  let result = markdown;

  // Handle {{#each field}}...{{/each}} blocks
  result = result.replace(
    /\{\{#each\s+(\w+(?:\.\w+)*)\}\}([\s\S]*?)\{\{\/each\}\}/g,
    (_match, field: string, body: string) => {
      const items = (record ? resolve(record, field) : listData) as any[];
      if (!Array.isArray(items) || items.length === 0) return '';
      return items.map((item) => resolveTokens(body, item)).join('');
    }
  );

  // Handle {{field.path}} and {{field.path|format}}
  result = result.replace(
    /\{\{([^}|]+)(?:\|([^}]+))?\}\}/g,
    (_match, path: string, format?: string) => {
      const val = resolve(record, path.trim());
      if (val === undefined) return _match; // leave unresolved tokens visible
      return formatValue(val, format?.trim());
    }
  );

  return result;
}

// ---------------------------------------------------------------------------
// Field token picker
// ---------------------------------------------------------------------------

interface TokenPickerProps {
  fields: FieldPath[];
  onInsert: (token: string) => void;
  onClose: () => void;
}

function TokenPicker({ fields, onInsert, onClose }: TokenPickerProps) {
  const [filter, setFilter] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  React.useEffect(() => { inputRef.current?.focus(); }, []);

  const filtered = useMemo(() => {
    if (!filter) return fields;
    const lf = filter.toLowerCase();
    return fields.filter(f =>
      f.path.toLowerCase().includes(lf) || f.label.toLowerCase().includes(lf)
    );
  }, [fields, filter]);

  return (
    <div style={{
      position: 'absolute', top: 32, right: 0, zIndex: 1000,
      background: '#1e1e2e', border: '1px solid #444', borderRadius: 6,
      width: 320, maxHeight: 360, display: 'flex', flexDirection: 'column',
      boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
    }}>
      <div style={{ padding: '8px 10px', borderBottom: '1px solid #333', display: 'flex', gap: 6 }}>
        <input
          ref={inputRef}
          value={filter}
          onChange={e => setFilter(e.target.value)}
          placeholder="Filter fields..."
          style={{
            flex: 1, background: '#2a2a3a', border: '1px solid #555',
            borderRadius: 4, padding: '4px 8px', color: '#ddd', fontSize: 13,
          }}
        />
        <button onClick={onClose} style={{
          background: 'none', border: 'none', color: '#888', cursor: 'pointer', fontSize: 16,
        }}>×</button>
      </div>
      <div style={{ overflowY: 'auto', flex: 1 }}>
        {filtered.map(f => (
          <div
            key={f.path}
            onClick={() => { onInsert(`{{${f.path}${f.format ? '|' + f.format : ''}}}`); onClose(); }}
            style={{
              padding: '6px 12px', cursor: 'pointer', borderBottom: '1px solid #2a2a3a',
              fontSize: 13, display: 'flex', justifyContent: 'space-between',
            }}
            onMouseEnter={e => (e.currentTarget.style.background = '#2a2a4a')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            <span style={{ color: '#88ccff', fontFamily: 'monospace' }}>{f.path}</span>
            <span style={{ color: '#888', fontSize: 12 }}>{f.label}</span>
          </div>
        ))}
        {filtered.length === 0 && (
          <div style={{ padding: '12px', color: '#666', textAlign: 'center', fontSize: 13 }}>
            No matching fields
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Submit to WC_HQ
// ---------------------------------------------------------------------------

async function submitToWCHQ(
  content: string,
  modelName: string,
  templateName: string,
): Promise<number | null> {
  try {
    const result = await saveRecord('action', {
      ida: `TEMPLATE-SUBMIT-${Date.now()}`,
      name: `Template contribution: ${templateName || modelName}`,
      description: `User submitted a markdown template for ${modelName}.\n\nTemplate name: ${templateName}\n\nThis template should be reviewed and sent to WC_HQ for distribution.`,
      status: 'pending',
      config: {
        template_content: content,
        model_name: modelName,
        template_name: templateName,
        submitted_at: new Date().toISOString(),
        destination: 'wc_hq',
      },
      metadata: {
        source: 'markdown_editor',
        type: 'template_contribution',
      },
    });
    return result?.id || null;
  } catch (err) {
    console.error('[MarkdownEditor] Submit to WC_HQ failed:', err);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function MarkdownEditor({
  value,
  onChange,
  defaultEdit = false,
  readOnly = false,
  record,
  listData,
  modelName,
  fieldPaths = [],
  templateName = '',
  onSubmit,
  height = 500,
  darkMode = true,
}: MarkdownEditorProps) {
  const [editing, setEditing] = useState(defaultEdit);
  const [showTokenPicker, setShowTokenPicker] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState<'success' | 'error' | null>(null);
  const editorRef = useRef<HTMLDivElement>(null);

  // Resolved preview — tokens replaced with record data
  const resolvedContent = useMemo(
    () => resolveTokens(value, record, listData),
    [value, record, listData]
  );

  const handleInsertToken = useCallback((token: string) => {
    if (!onChange) return;
    // Insert at cursor position if possible, otherwise append
    onChange(value + token);
  }, [value, onChange]);

  const handleSubmit = useCallback(async () => {
    if (!modelName) return;
    setSubmitting(true);
    setSubmitResult(null);
    const actionId = await submitToWCHQ(value, modelName, templateName);
    setSubmitting(false);
    if (actionId) {
      setSubmitResult('success');
      onSubmit?.(actionId);
      setTimeout(() => setSubmitResult(null), 3000);
    } else {
      setSubmitResult('error');
    }
  }, [value, modelName, templateName, onSubmit]);

  // Toolbar styles
  const btnStyle: React.CSSProperties = {
    background: 'rgba(255,255,255,0.08)', border: '1px solid #555',
    borderRadius: 4, padding: '4px 12px', color: '#ccc', cursor: 'pointer',
    fontSize: 13, transition: 'background 0.15s',
  };

  return (
    <div
      ref={editorRef}
      data-color-mode={darkMode ? 'dark' : 'light'}
      style={{ position: 'relative' }}
    >
      {/* Toolbar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '6px 8px', background: '#1a1a2a',
        borderBottom: '1px solid #333', borderRadius: '6px 6px 0 0',
      }}>
        {!readOnly && (
          <button
            onClick={() => setEditing(!editing)}
            style={{ ...btnStyle, background: editing ? 'rgba(100,160,255,0.2)' : btnStyle.background }}
          >
            {editing ? 'Preview' : 'Edit'}
          </button>
        )}

        {editing && fieldPaths.length > 0 && (
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setShowTokenPicker(!showTokenPicker)}
              style={btnStyle}
              title="Insert field token"
            >
              {'{{ }}  Insert Field'}
            </button>
            {showTokenPicker && (
              <TokenPicker
                fields={fieldPaths}
                onInsert={handleInsertToken}
                onClose={() => setShowTokenPicker(false)}
              />
            )}
          </div>
        )}

        <div style={{ flex: 1 }} />

        {/* Submit to WC_HQ */}
        {modelName && !readOnly && (
          <button
            onClick={handleSubmit}
            disabled={submitting}
            style={{
              ...btnStyle,
              background: submitResult === 'success' ? 'rgba(80,200,120,0.2)'
                : submitResult === 'error' ? 'rgba(255,80,80,0.2)'
                : btnStyle.background,
            }}
          >
            {submitting ? 'Submitting...'
              : submitResult === 'success' ? 'Submitted'
              : submitResult === 'error' ? 'Failed — retry'
              : 'Submit to WC_HQ'}
          </button>
        )}
      </div>

      {/* Editor / Preview */}
      {editing ? (
        <MDEditor
          value={value}
          onChange={(val) => onChange?.(val || '')}
          height={height}
          preview="live"
          hideToolbar={false}
        />
      ) : (
        <div
          style={{
            height, overflowY: 'auto', padding: '16px 20px',
            background: darkMode ? '#1e1e2e' : '#fff',
            color: darkMode ? '#ddd' : '#222',
            borderRadius: '0 0 6px 6px',
            border: '1px solid #333', borderTop: 'none',
          }}
        >
          <MDEditor.Markdown source={resolvedContent} />
        </div>
      )}
    </div>
  );
}

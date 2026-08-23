/**
 * FieldEditor — inline editor row for a single PrintField.
 *
 * Renders: grip | field | label | align | format | width | delete
 * All editing is inline — no popups.
 *
 * LastChecked: 2026-08-07 | WhereUsed: SectionCard | WhoCreated: Claude
 */
import React from 'react';
import type { PrintField } from './printLayoutTypes';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FieldEditorProps {
  field: PrintField;
  onChange: (field: PrintField) => void;
  onRemove: () => void;
  draggable?: boolean;
  onDragStart?: () => void;
  onDragOver?: (e: React.DragEvent) => void;
  onDragEnd?: () => void;
  isDragging?: boolean;
  fontSize: number;
  /** Show style column (for totals rows with bold) */
  showStyle?: boolean;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ALIGNS: Array<PrintField['align']> = ['left', 'center', 'right'];
const FORMATS: Array<NonNullable<PrintField['format']>> = ['text', 'currency', 'date', 'number', 'percent'];

const ALIGN_LABELS: Record<string, string> = { left: 'L', center: 'C', right: 'R' };

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const FieldEditor: React.FC<FieldEditorProps> = ({
  field, onChange, onRemove,
  draggable, onDragStart, onDragOver, onDragEnd, isDragging,
  fontSize, showStyle,
}) => {
  const fs = fontSize - 2;

  const inputStyle: React.CSSProperties = {
    background: 'var(--db-bg)', color: 'var(--db-text)', border: '1px solid var(--db-border-light)',
    borderRadius: 3, padding: '2px 4px', fontSize: fs,
    outline: 'none', width: '100%',
  };

  const cycleAlign = () => {
    const idx = ALIGNS.indexOf(field.align || 'left');
    onChange({ ...field, align: ALIGNS[(idx + 1) % ALIGNS.length] });
  };

  const cycleStyle = () => {
    const styles = ['', 'bold', 'italic', 'bold italic'];
    const idx = styles.indexOf(field.style || '');
    onChange({ ...field, style: styles[(idx + 1) % styles.length] || undefined });
  };

  return (
    <div
      data-wc="field-editor"
      draggable={draggable}
      onDragStart={(e) => { e.stopPropagation(); onDragStart?.(); }}
      onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); onDragOver?.(e); }}
      onDragEnd={(e) => { e.stopPropagation(); onDragEnd?.(); }}
      style={{
        display: 'grid',
        gridTemplateColumns: showStyle
          ? '18px 1fr 1fr 36px 70px 50px 40px 20px'
          : '18px 1fr 1fr 36px 70px 50px 20px',
        gap: 4, alignItems: 'center',
        padding: '3px 0',
        opacity: isDragging ? 0.4 : 1,
        borderBottom: '1px solid var(--db-border-light)',
      }}
    >
      {/* Drag grip */}
      <span style={{ cursor: draggable ? 'grab' : 'default', color: 'var(--db-text-dim)', fontSize: fs, textAlign: 'center', userSelect: 'none' }}>
        ⋮⋮
      </span>

      {/* Field path */}
      <input
        value={field.field}
        onChange={(e) => onChange({ ...field, field: e.target.value })}
        placeholder="field.path"
        style={{ ...inputStyle, fontFamily: 'monospace' }}
        title="Dot-notation field path"
      />

      {/* Label */}
      <input
        value={field.label || ''}
        onChange={(e) => onChange({ ...field, label: e.target.value || undefined })}
        placeholder="Label"
        style={inputStyle}
        title="Display label"
      />

      {/* Align cycle */}
      <span
        onClick={cycleAlign}
        title={`Alignment: ${field.align || 'left'} (click to cycle)`}
        style={{
          cursor: 'pointer', textAlign: 'center', fontSize: fs - 1,
          fontWeight: 700, color: 'var(--db-accent)', userSelect: 'none',
          border: '1px solid var(--db-border-light)', borderRadius: 3,
          padding: '2px 0',
        }}
      >
        {ALIGN_LABELS[field.align || 'left']}
      </span>

      {/* Format select */}
      <select
        value={field.format || 'text'}
        onChange={(e) => onChange({ ...field, format: e.target.value as PrintField['format'] })}
        style={{
          ...inputStyle, cursor: 'pointer', padding: '1px 2px',
        }}
      >
        {FORMATS.map(f => <option key={f} value={f}>{f}</option>)}
      </select>

      {/* Width */}
      <input
        value={field.width || ''}
        onChange={(e) => onChange({ ...field, width: e.target.value || undefined })}
        placeholder="width"
        style={{ ...inputStyle, fontSize: fs - 1 }}
        title="CSS width (e.g. 40%, 120px)"
      />

      {/* Style cycle (optional) */}
      {showStyle && (
        <span
          onClick={cycleStyle}
          title={`Style: ${field.style || 'normal'} (click to cycle)`}
          style={{
            cursor: 'pointer', textAlign: 'center', fontSize: fs - 1,
            fontWeight: field.style?.includes('bold') ? 700 : 400,
            fontStyle: field.style?.includes('italic') ? 'italic' : 'normal',
            color: field.style ? 'var(--db-accent)' : 'var(--db-text-dim)',
            border: '1px solid var(--db-border-light)', borderRadius: 3,
            padding: '2px 0', userSelect: 'none',
          }}
        >
          {field.style || 'N'}
        </span>
      )}

      {/* Delete */}
      <span
        onClick={onRemove}
        title="Remove field"
        style={{
          cursor: 'pointer', color: 'var(--db-text-dim)', textAlign: 'center',
          fontSize: fs, userSelect: 'none',
        }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = '#e55'; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = 'var(--db-text-dim)'; }}
      >
        &times;
      </span>
    </div>
  );
};

export default FieldEditor;
export type { FieldEditorProps };

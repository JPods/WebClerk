/**
 * SectionCard — expandable editor card for one PrintLayout section.
 *
 * Three editing shapes:
 *   Toggle:     company_header — boolean switches
 *   Source:     comments, conditions — text input for source path
 *   Field-list: meta_row, footer, line_items, totals, data_table, address_blocks
 *               — draggable FieldEditor rows + section-specific options
 *   Signature:  blocks with string arrays
 *
 * LastChecked: 2026-08-12 | WhereUsed: PrintLayoutDesigner | WhoCreated: Claude
 */
import React, { useState } from 'react';
import type { PrintLayoutSection, PrintField } from './printLayoutTypes';
import FieldEditor from './FieldEditor';
import './SectionCard.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Theme {
  bg: string; surface: string; surfaceAlt: string;
  border: string; borderLight: string;
  text: string; textMuted: string; textDim: string;
  accent: string; accentRed: string;
  [k: string]: string;
}

interface SectionCardProps {
  section: PrintLayoutSection;
  index: number;
  onChange: (section: PrintLayoutSection) => void;
  onRemove: () => void;
  draggable?: boolean;
  onDragStart?: () => void;
  onDragOver?: (e: React.DragEvent) => void;
  onDragEnd?: () => void;
  isDragging?: boolean;
  theme: Theme;
  fontSize: number;
}

// ---------------------------------------------------------------------------
// Section type labels + colors
// ---------------------------------------------------------------------------

const TYPE_COLORS: Record<string, string> = {
  company_header: '#0e639c',
  address_blocks: '#1a6b2e',
  meta_row: '#6f42c1',
  comments: '#2c8c99',
  line_items: '#c05621',
  totals: '#fd7e14',
  conditions: '#666',
  signature: '#9c6b0e',
  footer: '#555',
  data_table: '#c05621',
};

// ---------------------------------------------------------------------------
// Toggle — click to flip boolean (no checkboxes)
// ---------------------------------------------------------------------------

const Toggle: React.FC<{ label: string; value: boolean; onChange: (v: boolean) => void }> = ({
  label, value, onChange,
}) => (
  <div className="sc-toggle">
    <span className="sc-toggle-label">{label}</span>
    <span
      onClick={() => onChange(!value)}
      className={`sc-toggle-value${value ? ' sc-toggle-value--on' : ''}`}
    >
      {value ? 'ON' : 'off'}
    </span>
  </div>
);

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const SectionCard: React.FC<SectionCardProps> = ({
  section, index, onChange, onRemove,
  draggable, onDragStart, onDragOver, onDragEnd, isDragging,
  theme: t, fontSize,
}) => {
  const [expanded, setExpanded] = useState(false);
  const [dragFieldIdx, setDragFieldIdx] = useState<number | null>(null);

  const sType = section.type;
  const badgeColor = TYPE_COLORS[sType] || '#555';

  // Helpers to update section immutably
  const update = (patch: Partial<PrintLayoutSection>) => onChange({ ...section, ...patch } as PrintLayoutSection);

  const updateField = (fields: PrintField[], idx: number, field: PrintField) => {
    const next = [...fields];
    next[idx] = field;
    return next;
  };

  const removeField = (fields: PrintField[], idx: number) => fields.filter((_, i) => i !== idx);

  const addField = (fields: PrintField[]) => [...fields, { field: 'new_field', label: 'New' } as PrintField];

  // Field drag reorder within a section
  const reorderFields = (fields: PrintField[], from: number, to: number) => {
    const next = [...fields];
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    return next;
  };

  const handleFieldDragOver = (e: React.DragEvent, targetIdx: number) => {
    e.preventDefault();
    if (dragFieldIdx === null || dragFieldIdx === targetIdx) return;
    // Get the current fields array depending on section type
    const fields = getFields();
    if (!fields) return;
    setFields(reorderFields(fields, dragFieldIdx, targetIdx));
    setDragFieldIdx(targetIdx);
  };

  // Get/set fields array for the current section type
  const getFields = (): PrintField[] | null => {
    if ('fields' in section && Array.isArray((section as any).fields)) return (section as any).fields;
    if ('columns' in section && sType === 'line_items') return (section as any).columns;
    if ('columns' in section && sType === 'data_table') return (section as any).columns;
    if ('rows' in section && sType === 'totals') return (section as any).rows;
    return null;
  };

  const setFields = (fields: PrintField[]) => {
    if (sType === 'meta_row' || sType === 'footer') update({ fields } as any);
    else if (sType === 'line_items' || sType === 'data_table') update({ columns: fields } as any);
    else if (sType === 'totals') update({ rows: fields } as any);
  };

  const fieldKey = sType === 'line_items' || sType === 'data_table' ? 'columns'
    : sType === 'totals' ? 'rows' : 'fields';

  // ---------------------------------------------------------------------------
  // Render body based on section type
  // ---------------------------------------------------------------------------

  const renderBody = () => {
    // --- Toggle: company_header ---
    if (sType === 'company_header') {
      const s = section as any;
      return (
        <div className="sc-body-inner">
          <Toggle label="Logo" value={s.logo !== false} onChange={(v) => update({ logo: v } as any)} />
          <Toggle label="Address" value={s.show_address !== false} onChange={(v) => update({ show_address: v } as any)} />
          <Toggle label="Contact" value={s.show_contact !== false} onChange={(v) => update({ show_contact: v } as any)} />
        </div>
      );
    }

    // --- Source: comments, conditions ---
    if (sType === 'comments') {
      const s = section as any;
      return (
        <div className="sc-source-column">
          <label className="sc-input-label">
            Source: <input value={s.source || ''} onChange={(e) => update({ source: e.target.value } as any)}
              className="sc-input sc-input--mono" style={{ width: 180 }} />
          </label>
          <label className="sc-input-label">
            Label: <input value={s.label || ''} onChange={(e) => update({ label: e.target.value || undefined } as any)}
              className="sc-input" style={{ width: 120 }} />
          </label>
        </div>
      );
    }

    if (sType === 'conditions') {
      const s = section as any;
      return (
        <div className="sc-body-inner">
          <label className="sc-input-label">
            Source: <input value={s.source || ''} onChange={(e) => update({ source: e.target.value } as any)}
              className="sc-input sc-input--mono" style={{ width: 200 }} />
          </label>
        </div>
      );
    }

    // --- Signature ---
    if (sType === 'signature') {
      const s = section as any;
      const blocks: { label: string; lines: string[] }[] = s.blocks || [];
      return (
        <div className="sc-body-inner">
          {s.preamble !== undefined && (
            <label className="sc-input-label sc-input-label--block">
              Preamble: <input value={s.preamble || ''} onChange={(e) => update({ preamble: e.target.value || undefined } as any)}
                className="sc-input" style={{ width: 250 }} />
            </label>
          )}
          {blocks.map((block, bi) => (
            <div key={bi} className="sc-sig-block">
              <div className="sc-sig-block-header">
                <input value={block.label} onChange={(e) => {
                  const next = [...blocks]; next[bi] = { ...block, label: e.target.value };
                  update({ blocks: next } as any);
                }}
                  className="sc-input sc-input--bold" style={{ width: 120 }} />
                <span onClick={() => update({ blocks: blocks.filter((_, i) => i !== bi) } as any)}
                  className="sc-remove-btn">&times;</span>
              </div>
              {block.lines.map((line, li) => (
                <div key={li} className="sc-sig-line-row">
                  <input value={line} onChange={(e) => {
                    const lines = [...block.lines]; lines[li] = e.target.value;
                    const next = [...blocks]; next[bi] = { ...block, lines };
                    update({ blocks: next } as any);
                  }}
                    className="sc-input" />
                  <span onClick={() => {
                    const lines = block.lines.filter((_, i) => i !== li);
                    const next = [...blocks]; next[bi] = { ...block, lines };
                    update({ blocks: next } as any);
                  }} className="sc-remove-btn">&times;</span>
                </div>
              ))}
              <span onClick={() => {
                const next = [...blocks]; next[bi] = { ...block, lines: [...block.lines, 'Line'] };
                update({ blocks: next } as any);
              }} className="sc-add-link">+ line</span>
            </div>
          ))}
          <span onClick={() => update({ blocks: [...blocks, { label: 'Block', lines: ['Signature'] }] } as any)}
            className="sc-add-link">+ block</span>
        </div>
      );
    }

    // --- Address blocks (nested columns with fields) ---
    if (sType === 'address_blocks') {
      const s = section as any;
      const columns: { title: string; fields: PrintField[] }[] = s.columns || [];
      return (
        <div className="sc-body-inner">
          {columns.map((col, ci) => (
            <div key={ci} className="sc-addr-block">
              <div className="sc-addr-block-header">
                <input value={col.title} onChange={(e) => {
                  const next = [...columns]; next[ci] = { ...col, title: e.target.value };
                  update({ columns: next } as any);
                }}
                  className="sc-input sc-input--bold" style={{ width: 140 }} />
                <span onClick={() => update({ columns: columns.filter((_, i) => i !== ci) } as any)}
                  className="sc-remove-btn">&times;</span>
              </div>
              {col.fields.map((f, fi) => (
                <FieldEditor
                  key={fi}
                  field={f}
                  onChange={(nf) => {
                    const fields = updateField(col.fields, fi, nf);
                    const next = [...columns]; next[ci] = { ...col, fields };
                    update({ columns: next } as any);
                  }}
                  onRemove={() => {
                    const fields = removeField(col.fields, fi);
                    const next = [...columns]; next[ci] = { ...col, fields };
                    update({ columns: next } as any);
                  }}
                  theme={t}
                  fontSize={fontSize}
                />
              ))}
              <span onClick={() => {
                const next = [...columns]; next[ci] = { ...col, fields: addField(col.fields) };
                update({ columns: next } as any);
              }} className="sc-add-link">+ field</span>
            </div>
          ))}
          <span onClick={() => update({ columns: [...columns, { title: 'Column', fields: [{ field: 'field', label: 'Label' }] }] } as any)}
            className="sc-add-link">+ column</span>
        </div>
      );
    }

    // --- Field-list sections: meta_row, footer, line_items, totals, data_table ---
    const fields = getFields();
    if (!fields) return <div className="sc-no-content">No editable content</div>;

    const showStyle = sType === 'totals';

    return (
      <div className="sc-body-inner">
        {/* Column headers */}
        <div className={`sc-field-header ${showStyle ? 'sc-field-header--with-style' : 'sc-field-header--standard'}`}>
          <span></span>
          <span>Field</span>
          <span>Label</span>
          <span className="sc-field-header-center">Aln</span>
          <span>Format</span>
          <span>Width</span>
          {showStyle && <span>Style</span>}
          <span></span>
        </div>

        {/* Field rows */}
        {fields.map((f, fi) => (
          <FieldEditor
            key={fi}
            field={f}
            onChange={(nf) => setFields(updateField(fields, fi, nf))}
            onRemove={() => setFields(removeField(fields, fi))}
            draggable
            onDragStart={() => setDragFieldIdx(fi)}
            onDragOver={(e) => handleFieldDragOver(e, fi)}
            onDragEnd={() => setDragFieldIdx(null)}
            isDragging={dragFieldIdx === fi}
            theme={t}
            fontSize={fontSize}
            showStyle={showStyle}
          />
        ))}

        {/* Add field */}
        <div className="sc-add-field-row">
          <span onClick={() => setFields(addField(fields))}
            className="sc-add-link">+ field</span>
        </div>

        {/* Section-specific options */}
        {sType === 'line_items' && (
          <Toggle label="Footer totals" value={(section as any).show_footer_totals !== false}
            onChange={(v) => update({ show_footer_totals: v } as any)} />
        )}
        {sType === 'totals' && (
          <label className="sc-options-label">
            Left text: <input value={(section as any).left_text || ''} onChange={(e) => update({ left_text: e.target.value || undefined } as any)}
              className="sc-input" style={{ width: 200 }} />
          </label>
        )}
        {sType === 'data_table' && (
          <div className="sc-options-column">
            <label className="sc-input-label">
              Group by: <input value={(section as any).group_by || ''} onChange={(e) => update({ group_by: e.target.value || undefined } as any)}
                className="sc-input sc-input--mono" style={{ width: 120 }} />
            </label>
            <label className="sc-input-label">
              Group label: <input value={(section as any).group_label || ''} onChange={(e) => update({ group_label: e.target.value || undefined } as any)}
                className="sc-input" style={{ width: 120 }} />
            </label>
            <Toggle label="Subtotals" value={!!(section as any).group_subtotals}
              onChange={(v) => update({ group_subtotals: v } as any)} />
            <Toggle label="Grand total" value={!!(section as any).grand_totals}
              onChange={(v) => update({ grand_totals: v } as any)} />
          </div>
        )}
      </div>
    );
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div
      data-wc="section-card"
      className={`sc-root${isDragging ? ' sc-root--dragging' : ''}`}
      draggable={draggable}
      onDragStart={(e) => { onDragStart?.(); }}
      onDragOver={(e) => { e.preventDefault(); onDragOver?.(e); }}
      onDragEnd={() => onDragEnd?.()}
      style={{
        borderLeftWidth: 3,
        borderLeftStyle: 'solid',
        borderLeftColor: badgeColor,
        '--sc-fs': `${fontSize}px`,
        '--sc-fs-sm': `${fontSize - 2}px`,
        '--sc-fs-xs': `${fontSize - 3}px`,
      } as React.CSSProperties}
    >
      {/* Header */}
      <div
        onClick={() => setExpanded(!expanded)}
        className="sc-header"
      >
        {/* Drag grip */}
        <span className="sc-drag-grip">⋮⋮</span>

        {/* Section type badge */}
        <span className="sc-type-badge" style={{ background: badgeColor }}>{sType.replace(/_/g, ' ')}</span>

        {/* Expand indicator */}
        <span className="sc-expand-indicator">
          {expanded ? '▾' : '▸'}
        </span>

        {/* Delete */}
        <span
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
          title="Remove section"
          className="sc-delete-btn"
        >&times;</span>
      </div>

      {/* Body */}
      {expanded && (
        <div className="sc-body">
          {renderBody()}
        </div>
      )}
    </div>
  );
};

export default SectionCard;

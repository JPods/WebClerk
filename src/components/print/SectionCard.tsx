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
 * LastChecked: 2026-08-07 | WhereUsed: PrintLayoutDesigner | WhoCreated: Claude
 */
import React, { useState } from 'react';
import type { PrintLayoutSection, PrintField } from './printLayoutTypes';
import FieldEditor from './FieldEditor';

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

const Toggle: React.FC<{ label: string; value: boolean; onChange: (v: boolean) => void; theme: Theme; fontSize: number }> = ({
  label, value, onChange, theme: t, fontSize,
}) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '2px 0' }}>
    <span style={{ fontSize: fontSize - 2, color: t.textMuted, width: 100 }}>{label}</span>
    <span
      onClick={() => onChange(!value)}
      style={{
        cursor: 'pointer', fontSize: fontSize - 2, fontWeight: 700,
        color: value ? t.accent : t.textDim,
        padding: '1px 6px', borderRadius: 3,
        border: `1px solid ${value ? t.accent : t.borderLight}`,
        userSelect: 'none',
      }}
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
        <div style={{ padding: '4px 0' }}>
          <Toggle label="Logo" value={s.logo !== false} onChange={(v) => update({ logo: v } as any)} theme={t} fontSize={fontSize} />
          <Toggle label="Address" value={s.show_address !== false} onChange={(v) => update({ show_address: v } as any)} theme={t} fontSize={fontSize} />
          <Toggle label="Contact" value={s.show_contact !== false} onChange={(v) => update({ show_contact: v } as any)} theme={t} fontSize={fontSize} />
        </div>
      );
    }

    // --- Source: comments, conditions ---
    if (sType === 'comments') {
      const s = section as any;
      return (
        <div style={{ padding: '4px 0', display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={{ fontSize: fontSize - 2, color: t.textMuted }}>
            Source: <input value={s.source || ''} onChange={(e) => update({ source: e.target.value } as any)}
              style={{ background: t.bg, color: t.text, border: `1px solid ${t.borderLight}`, borderRadius: 3, padding: '2px 4px', fontSize: fontSize - 2, fontFamily: 'monospace', width: 180 }} />
          </label>
          <label style={{ fontSize: fontSize - 2, color: t.textMuted }}>
            Label: <input value={s.label || ''} onChange={(e) => update({ label: e.target.value || undefined } as any)}
              style={{ background: t.bg, color: t.text, border: `1px solid ${t.borderLight}`, borderRadius: 3, padding: '2px 4px', fontSize: fontSize - 2, width: 120 }} />
          </label>
        </div>
      );
    }

    if (sType === 'conditions') {
      const s = section as any;
      return (
        <div style={{ padding: '4px 0' }}>
          <label style={{ fontSize: fontSize - 2, color: t.textMuted }}>
            Source: <input value={s.source || ''} onChange={(e) => update({ source: e.target.value } as any)}
              style={{ background: t.bg, color: t.text, border: `1px solid ${t.borderLight}`, borderRadius: 3, padding: '2px 4px', fontSize: fontSize - 2, fontFamily: 'monospace', width: 200 }} />
          </label>
        </div>
      );
    }

    // --- Signature ---
    if (sType === 'signature') {
      const s = section as any;
      const blocks: { label: string; lines: string[] }[] = s.blocks || [];
      return (
        <div style={{ padding: '4px 0' }}>
          {s.preamble !== undefined && (
            <label style={{ fontSize: fontSize - 2, color: t.textMuted, display: 'block', marginBottom: 4 }}>
              Preamble: <input value={s.preamble || ''} onChange={(e) => update({ preamble: e.target.value || undefined } as any)}
                style={{ background: t.bg, color: t.text, border: `1px solid ${t.borderLight}`, borderRadius: 3, padding: '2px 4px', fontSize: fontSize - 2, width: 250 }} />
            </label>
          )}
          {blocks.map((block, bi) => (
            <div key={bi} style={{ border: `1px solid ${t.borderLight}`, borderRadius: 4, padding: 6, marginBottom: 4 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <input value={block.label} onChange={(e) => {
                  const next = [...blocks]; next[bi] = { ...block, label: e.target.value };
                  update({ blocks: next } as any);
                }}
                  style={{ background: t.bg, color: t.text, border: `1px solid ${t.borderLight}`, borderRadius: 3, padding: '2px 4px', fontSize: fontSize - 2, fontWeight: 600, width: 120 }} />
                <span onClick={() => update({ blocks: blocks.filter((_, i) => i !== bi) } as any)}
                  style={{ cursor: 'pointer', color: t.textDim, fontSize: fontSize - 2 }}>&times;</span>
              </div>
              {block.lines.map((line, li) => (
                <div key={li} style={{ display: 'flex', gap: 4, marginBottom: 2 }}>
                  <input value={line} onChange={(e) => {
                    const lines = [...block.lines]; lines[li] = e.target.value;
                    const next = [...blocks]; next[bi] = { ...block, lines };
                    update({ blocks: next } as any);
                  }}
                    style={{ background: t.bg, color: t.text, border: `1px solid ${t.borderLight}`, borderRadius: 3, padding: '2px 4px', fontSize: fontSize - 2, flex: 1 }} />
                  <span onClick={() => {
                    const lines = block.lines.filter((_, i) => i !== li);
                    const next = [...blocks]; next[bi] = { ...block, lines };
                    update({ blocks: next } as any);
                  }} style={{ cursor: 'pointer', color: t.textDim, fontSize: fontSize - 2 }}>&times;</span>
                </div>
              ))}
              <span onClick={() => {
                const next = [...blocks]; next[bi] = { ...block, lines: [...block.lines, 'Line'] };
                update({ blocks: next } as any);
              }} style={{ cursor: 'pointer', color: t.accent, fontSize: fontSize - 2 }}>+ line</span>
            </div>
          ))}
          <span onClick={() => update({ blocks: [...blocks, { label: 'Block', lines: ['Signature'] }] } as any)}
            style={{ cursor: 'pointer', color: t.accent, fontSize: fontSize - 2 }}>+ block</span>
        </div>
      );
    }

    // --- Address blocks (nested columns with fields) ---
    if (sType === 'address_blocks') {
      const s = section as any;
      const columns: { title: string; fields: PrintField[] }[] = s.columns || [];
      return (
        <div style={{ padding: '4px 0' }}>
          {columns.map((col, ci) => (
            <div key={ci} style={{ border: `1px solid ${t.borderLight}`, borderRadius: 4, padding: 6, marginBottom: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <input value={col.title} onChange={(e) => {
                  const next = [...columns]; next[ci] = { ...col, title: e.target.value };
                  update({ columns: next } as any);
                }}
                  style={{ background: t.bg, color: t.text, border: `1px solid ${t.borderLight}`, borderRadius: 3, padding: '2px 4px', fontSize: fontSize - 1, fontWeight: 700, width: 140 }} />
                <span onClick={() => update({ columns: columns.filter((_, i) => i !== ci) } as any)}
                  style={{ cursor: 'pointer', color: t.textDim, fontSize: fontSize - 2 }}>&times;</span>
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
              }} style={{ cursor: 'pointer', color: t.accent, fontSize: fontSize - 2 }}>+ field</span>
            </div>
          ))}
          <span onClick={() => update({ columns: [...columns, { title: 'Column', fields: [{ field: 'field', label: 'Label' }] }] } as any)}
            style={{ cursor: 'pointer', color: t.accent, fontSize: fontSize - 2 }}>+ column</span>
        </div>
      );
    }

    // --- Field-list sections: meta_row, footer, line_items, totals, data_table ---
    const fields = getFields();
    if (!fields) return <div style={{ fontSize: fontSize - 2, color: t.textDim, padding: 4 }}>No editable content</div>;

    const showStyle = sType === 'totals';

    return (
      <div style={{ padding: '4px 0' }}>
        {/* Column headers */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: showStyle
            ? '18px 1fr 1fr 36px 70px 50px 40px 20px'
            : '18px 1fr 1fr 36px 70px 50px 20px',
          gap: 4, padding: '0 0 3px 0',
          fontSize: fontSize - 3, fontWeight: 700, color: t.textDim,
          textTransform: 'uppercase', letterSpacing: '0.04em',
          borderBottom: `1px solid ${t.border}`,
        }}>
          <span></span>
          <span>Field</span>
          <span>Label</span>
          <span style={{ textAlign: 'center' }}>Aln</span>
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
        <div style={{ padding: '4px 0' }}>
          <span onClick={() => setFields(addField(fields))}
            style={{ cursor: 'pointer', color: t.accent, fontSize: fontSize - 2 }}>+ field</span>
        </div>

        {/* Section-specific options */}
        {sType === 'line_items' && (
          <Toggle label="Footer totals" value={(section as any).show_footer_totals !== false}
            onChange={(v) => update({ show_footer_totals: v } as any)} theme={t} fontSize={fontSize} />
        )}
        {sType === 'totals' && (
          <label style={{ fontSize: fontSize - 2, color: t.textMuted, display: 'block', marginTop: 4 }}>
            Left text: <input value={(section as any).left_text || ''} onChange={(e) => update({ left_text: e.target.value || undefined } as any)}
              style={{ background: t.bg, color: t.text, border: `1px solid ${t.borderLight}`, borderRadius: 3, padding: '2px 4px', fontSize: fontSize - 2, width: 200 }} />
          </label>
        )}
        {sType === 'data_table' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 4 }}>
            <label style={{ fontSize: fontSize - 2, color: t.textMuted }}>
              Group by: <input value={(section as any).group_by || ''} onChange={(e) => update({ group_by: e.target.value || undefined } as any)}
                style={{ background: t.bg, color: t.text, border: `1px solid ${t.borderLight}`, borderRadius: 3, padding: '2px 4px', fontSize: fontSize - 2, fontFamily: 'monospace', width: 120 }} />
            </label>
            <label style={{ fontSize: fontSize - 2, color: t.textMuted }}>
              Group label: <input value={(section as any).group_label || ''} onChange={(e) => update({ group_label: e.target.value || undefined } as any)}
                style={{ background: t.bg, color: t.text, border: `1px solid ${t.borderLight}`, borderRadius: 3, padding: '2px 4px', fontSize: fontSize - 2, width: 120 }} />
            </label>
            <Toggle label="Subtotals" value={!!(section as any).group_subtotals}
              onChange={(v) => update({ group_subtotals: v } as any)} theme={t} fontSize={fontSize} />
            <Toggle label="Grand total" value={!!(section as any).grand_totals}
              onChange={(v) => update({ grand_totals: v } as any)} theme={t} fontSize={fontSize} />
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
      draggable={draggable}
      onDragStart={(e) => { onDragStart?.(); }}
      onDragOver={(e) => { e.preventDefault(); onDragOver?.(e); }}
      onDragEnd={() => onDragEnd?.()}
      style={{
        border: `1px solid ${isDragging ? '#d97706' : t.borderLight}`,
        borderLeft: `3px solid ${badgeColor}`,
        borderRadius: 4, marginBottom: 4,
        background: isDragging ? t.surfaceAlt : t.surface,
        opacity: isDragging ? 0.5 : 1,
        transition: 'opacity 0.1s, border-color 0.1s',
      }}
    >
      {/* Header */}
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '6px 8px', cursor: 'pointer',
          userSelect: 'none',
        }}
      >
        {/* Drag grip */}
        <span style={{ color: t.textDim, fontSize: fontSize - 1, cursor: 'grab' }}>⋮⋮</span>

        {/* Section type badge */}
        <span style={{
          padding: '1px 6px', borderRadius: 3, fontSize: fontSize - 3,
          fontWeight: 700, background: badgeColor, color: '#fff',
          textTransform: 'uppercase', letterSpacing: '0.04em',
        }}>{sType.replace(/_/g, ' ')}</span>

        {/* Expand indicator */}
        <span style={{ color: t.textDim, fontSize: fontSize - 2, flex: 1 }}>
          {expanded ? '▾' : '▸'}
        </span>

        {/* Delete */}
        <span
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
          title="Remove section"
          style={{ color: t.textDim, fontSize: fontSize - 1, cursor: 'pointer', padding: '0 2px' }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = '#e55'; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = t.textDim; }}
        >&times;</span>
      </div>

      {/* Body */}
      {expanded && (
        <div style={{ padding: '0 8px 8px 28px' }}>
          {renderBody()}
        </div>
      )}
    </div>
  );
};

export default SectionCard;

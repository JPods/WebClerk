/**
 * SectionTypePicker — dropdown for adding a new PrintLayout section.
 *
 * Shows all 10 section types with descriptions. Click adds a blank
 * section with sensible defaults.
 *
 * LastChecked: 2026-08-07 | WhereUsed: PrintLayoutDesigner | WhoCreated: Claude
 */
import React, { useState, useRef, useEffect } from 'react';
import type { PrintLayoutSection } from './printLayoutTypes';

// ---------------------------------------------------------------------------
// Section type registry
// ---------------------------------------------------------------------------

interface SectionDef {
  type: string;
  label: string;
  desc: string;
  factory: () => PrintLayoutSection;
}

const SECTION_TYPES: SectionDef[] = [
  {
    type: 'company_header', label: 'Company Header', desc: 'Logo, name, address',
    factory: () => ({ type: 'company_header', logo: true, show_address: true, show_contact: true }),
  },
  {
    type: 'address_blocks', label: 'Address Blocks', desc: 'Bill To / Ship To columns',
    factory: () => ({
      type: 'address_blocks',
      columns: [{ title: 'Bill To', fields: [{ field: 'company', label: 'Company' }] }],
    }),
  },
  {
    type: 'meta_row', label: 'Meta Row', desc: 'Inline info fields',
    factory: () => ({ type: 'meta_row', fields: [{ field: 'ida', label: 'ID' }] }),
  },
  {
    type: 'comments', label: 'Comments', desc: 'Comments block',
    factory: () => ({ type: 'comments', source: 'comments.public', label: 'Comments' }),
  },
  {
    type: 'line_items', label: 'Line Items', desc: 'Line item table',
    factory: () => ({
      type: 'line_items',
      columns: [
        { field: 'item.ida_item', label: 'Item', align: 'left' },
        { field: 'item.description', label: 'Description', align: 'left', width: '40%' },
        { field: 'quantity.active', label: 'Qty', align: 'right' },
      ],
      show_footer_totals: true,
    }),
  },
  {
    type: 'totals', label: 'Totals', desc: 'Totals summary',
    factory: () => ({
      type: 'totals',
      rows: [
        { field: 'totals.subtotal', label: 'Subtotal', format: 'currency' },
        { field: 'totals.total', label: 'Total', format: 'currency', style: 'bold' },
      ],
    }),
  },
  {
    type: 'conditions', label: 'Conditions', desc: 'Terms and conditions',
    factory: () => ({ type: 'conditions', source: 'conditions_description' }),
  },
  {
    type: 'signature', label: 'Signature', desc: 'Signature blocks',
    factory: () => ({
      type: 'signature',
      blocks: [{ label: 'Authorized', lines: ['Signature', 'Date'] }],
    }),
  },
  {
    type: 'footer', label: 'Footer', desc: 'Page footer fields',
    factory: () => ({ type: 'footer', fields: [{ field: 'ida', label: 'ID' }] }),
  },
  {
    type: 'data_table', label: 'Data Table', desc: 'List report table',
    factory: () => ({
      type: 'data_table',
      columns: [{ field: 'ida', label: 'ID', align: 'left' }],
      grand_totals: true,
    }),
  },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface Props {
  onAdd: (section: PrintLayoutSection) => void;
  theme: { bg: string; surface: string; surfaceAlt: string; border: string; borderLight: string; text: string; textMuted: string; textDim: string; accent: string; [k: string]: string };
  fontSize: number;
}

const SectionTypePicker: React.FC<Props> = ({ onAdd, theme: t, fontSize }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div ref={ref} style={{ position: 'relative', display: 'inline-block' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          padding: '4px 10px', borderRadius: 4, cursor: 'pointer',
          fontSize: fontSize - 1, fontWeight: 600,
          background: 'none', border: `1px solid ${t.border}`,
          color: t.text,
        }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = t.surfaceAlt; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'none'; }}
      >
        + Section
      </button>

      {open && (
        <div
          data-wc="section-type-picker"
          style={{
            position: 'absolute', bottom: '100%', left: 0,
            marginBottom: 4, zIndex: 100,
            background: t.surface, border: `1px solid ${t.border}`,
            borderRadius: 6, boxShadow: '0 4px 16px rgba(0,0,0,0.3)',
            minWidth: 220, maxHeight: 320, overflowY: 'auto',
          }}
        >
          {SECTION_TYPES.map(def => (
            <div
              key={def.type}
              onClick={() => { onAdd(def.factory()); setOpen(false); }}
              style={{
                padding: '6px 12px', cursor: 'pointer',
                borderBottom: `1px solid ${t.borderLight}`,
                transition: 'background 0.1s',
              }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = t.surfaceAlt; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
            >
              <div style={{ fontSize: fontSize - 1, fontWeight: 600, color: t.text }}>{def.label}</div>
              <div style={{ fontSize: fontSize - 3, color: t.textDim }}>{def.desc}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SectionTypePicker;
export { SECTION_TYPES };

/**
 * PrintLayoutDesigner — visual report layout editor.
 *
 * Two-list design:
 *   Left top:    Available fields (from model schema, not yet on report)
 *   Left bottom: Used fields (on the report, grouped by zone: Header / List / Footer)
 *   Right:       Live preview
 *
 * User picks fields and assigns zones. Claude/Alice auto-arrange into
 * proper PrintLayout sections with correct alignment, formatting, widths.
 *
 * Entry: shift-click a report row in ReportsDialog, or Design button.
 *
 * LastChecked: 2026-08-07 | WhereUsed: ReportsDialog | WhoCreated: Bill+Claude
 */
import React, { useState, useCallback, useEffect, useRef } from 'react';
import type { PrintLayout, PrintField } from './printLayoutTypes';
import { generatePrintHtml } from './UniversalPrint';
import type { ReportRecord } from '../common/ReportsDialog';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Theme {
  bg: string; surface: string; surfaceAlt: string;
  border: string; borderLight: string;
  text: string; textMuted: string; textDim: string;
  accent: string; accentGreen: string; accentGold: string; accentRed: string; accentPurple: string;
  [k: string]: string;
}

interface PrintLayoutDesignerProps {
  report: ReportRecord;
  model: string;
  layout: PrintLayout;
  theme: Theme;
  fontSize: number;
  companyInfo: any;
  sampleData: any;
  onSave: (layout: PrintLayout) => void;
  onClose: () => void;
}

type Zone = 'header' | 'list' | 'footer';

interface UsedField {
  field: string;
  label: string;
  zone: Zone;
  format?: string;
}

const ZONE_LABELS: Record<Zone, string> = { header: 'Header', list: 'List / Body', footer: 'Footer' };
const ZONE_COLORS: Record<Zone, string> = { header: '#0e639c', list: '#c05621', footer: '#555' };
const ZONES: Zone[] = ['header', 'list', 'footer'];

// ---------------------------------------------------------------------------
// Auto-arrange: convert UsedField[] → PrintLayout
// Claude/Alice logic — proper sections, alignment, formatting, widths
// ---------------------------------------------------------------------------

function guessFormat(field: string): string {
  if (/price|cost|total|amount|balance|tax|commission|subtotal|shipping|discount/.test(field)) return 'currency';
  if (/dt_|date|created|modified|deadline|completed/.test(field)) return 'date';
  if (/qty|quantity|count|weight|pieces/.test(field)) return 'number';
  if (/percent|rate|margin/.test(field)) return 'percent';
  return 'text';
}

function guessAlign(format: string): 'left' | 'right' | 'center' {
  if (format === 'currency' || format === 'number' || format === 'percent') return 'right';
  return 'left';
}

function guessWidth(field: string, format: string): string | undefined {
  if (format === 'currency') return '12%';
  if (format === 'date') return '10%';
  if (format === 'number' || format === 'percent') return '8%';
  if (/description|name|company|address|comment|note/.test(field)) return '25%';
  return undefined;
}

function autoLabel(field: string): string {
  // config.ship_to.company → Ship To Company
  // totals.subtotal → Subtotal
  // dt_created → Date Created
  const last = field.includes('.') ? field.split('.').pop()! : field;
  return last
    .replace(/^dt_/, 'Date ')
    .replace(/^ida$/, 'ID')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

function arrangeLayout(used: UsedField[], model: string, title: string, paper: string): PrintLayout {
  const headerFields = used.filter(f => f.zone === 'header');
  const listFields = used.filter(f => f.zone === 'list');
  const footerFields = used.filter(f => f.zone === 'footer');

  const sections: any[] = [];

  // Always include company header
  sections.push({ type: 'company_header', logo: true, show_address: true, show_contact: true });

  // Header fields → meta_row
  if (headerFields.length > 0) {
    sections.push({
      type: 'meta_row',
      fields: headerFields.map(f => ({
        field: f.field,
        label: f.label,
        format: f.format || guessFormat(f.field),
        align: guessAlign(f.format || guessFormat(f.field)),
      })),
    });
  }

  // List fields → line_items or data_table
  if (listFields.length > 0) {
    const isSell = ['order', 'invoice', 'proposal'].includes(model);
    // Use line_items for sell transactions, data_table for reports/lists
    const hasLineItemFields = listFields.some(f =>
      /^item\.|^quantity\.|^price\.|^cost\./.test(f.field)
    );

    if (hasLineItemFields) {
      sections.push({
        type: 'line_items',
        columns: listFields.map(f => {
          const fmt = f.format || guessFormat(f.field);
          return {
            field: f.field,
            label: f.label,
            format: fmt,
            align: guessAlign(fmt),
            width: guessWidth(f.field, fmt),
          };
        }),
        show_footer_totals: listFields.some(f => guessFormat(f.field) === 'currency'),
      });
    } else {
      sections.push({
        type: 'data_table',
        columns: listFields.map(f => {
          const fmt = f.format || guessFormat(f.field);
          return {
            field: f.field,
            label: f.label,
            format: fmt,
            align: guessAlign(fmt),
            width: guessWidth(f.field, fmt),
          };
        }),
        grand_totals: listFields.some(f => guessFormat(f.field) === 'currency'),
      });
    }
  }

  // Footer fields → footer section
  if (footerFields.length > 0) {
    sections.push({
      type: 'footer',
      fields: footerFields.map(f => ({
        field: f.field,
        label: f.label,
        format: f.format || guessFormat(f.field),
      })),
    });
  }

  return {
    model,
    title: title || model.charAt(0).toUpperCase() + model.slice(1),
    paper: (paper as any) || 'letter',
    sections,
  };
}

// ---------------------------------------------------------------------------
// Extract used fields from existing PrintLayout
// ---------------------------------------------------------------------------

function extractUsedFields(layout: PrintLayout): UsedField[] {
  const used: UsedField[] = [];
  for (const section of layout.sections) {
    if (section.type === 'meta_row' && 'fields' in section) {
      for (const f of (section as any).fields || []) {
        used.push({ field: f.field, label: f.label || autoLabel(f.field), zone: 'header', format: f.format });
      }
    }
    if ((section.type === 'line_items' || section.type === 'data_table') && 'columns' in section) {
      for (const f of (section as any).columns || []) {
        used.push({ field: f.field, label: f.label || autoLabel(f.field), zone: 'list', format: f.format });
      }
    }
    if (section.type === 'totals' && 'rows' in section) {
      for (const f of (section as any).rows || []) {
        used.push({ field: f.field, label: f.label || autoLabel(f.field), zone: 'footer', format: f.format });
      }
    }
    if (section.type === 'footer' && 'fields' in section) {
      for (const f of (section as any).fields || []) {
        used.push({ field: f.field, label: f.label || autoLabel(f.field), zone: 'footer', format: f.format });
      }
    }
    if (section.type === 'address_blocks' && 'columns' in section) {
      for (const col of (section as any).columns || []) {
        for (const f of col.fields || []) {
          used.push({ field: f.field, label: f.label || autoLabel(f.field), zone: 'header', format: f.format });
        }
      }
    }
  }
  return used;
}

// ---------------------------------------------------------------------------
// Extract available fields from sample data (flatten nested objects)
// ---------------------------------------------------------------------------

function flattenKeys(obj: any, prefix = ''): string[] {
  if (!obj || typeof obj !== 'object') return [];
  const keys: string[] = [];
  for (const [k, v] of Object.entries(obj)) {
    if (k.startsWith('_') || k === 'lines') continue; // skip private + lines (handled separately)
    const path = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      keys.push(...flattenKeys(v, path));
    } else {
      keys.push(path);
    }
  }
  return keys;
}

// Common fields that exist on most transaction models
const COMMON_FIELDS = [
  'ida', 'status', 'company', 'attention', 'phone', 'email',
  'dt_created', 'dt_modified', 'terms', 'price_level',
  'totals.subtotal', 'totals.tax', 'totals.shipping', 'totals.total',
  'totals.balance', 'totals.commission',
  'item.ida_item', 'item.description', 'quantity.active',
  'price.unit', 'price.extended', 'cost.unit', 'cost.extended',
  'customer_id', 'rep', 'po_number', 'ship_via',
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const PrintLayoutDesigner: React.FC<PrintLayoutDesignerProps> = ({
  report, model, layout: initialLayout,
  theme: t, fontSize, companyInfo, sampleData,
  onSave, onClose,
}) => {
  const [used, setUsed] = useState<UsedField[]>(() => extractUsedFields(initialLayout));
  const [title, setTitle] = useState(initialLayout.title || report.name || '');
  const [paper, setPaper] = useState(initialLayout.paper || 'letter');
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [previewHtml, setPreviewHtml] = useState('');
  const [dragField, setDragField] = useState<{ field: string; source: 'available' | Zone } | null>(null);
  const [customField, setCustomField] = useState('');
  const previewTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Build available fields from sample data + common fields
  const allFields = React.useMemo(() => {
    const fromData = sampleData ? flattenKeys(sampleData) : [];
    const combined = new Set([...COMMON_FIELDS, ...fromData]);
    return [...combined].sort();
  }, [sampleData]);

  const usedFieldPaths = new Set(used.map(f => f.field));
  const available = allFields.filter(f => !usedFieldPaths.has(f));

  // --- Add field to a zone ---
  const addField = useCallback((field: string, zone: Zone) => {
    if (usedFieldPaths.has(field)) return;
    const fmt = guessFormat(field);
    setUsed(prev => [...prev, { field, label: autoLabel(field), zone, format: fmt }]);
    setDirty(true);
  }, [usedFieldPaths]);

  // --- Remove field ---
  const removeField = useCallback((idx: number) => {
    setUsed(prev => prev.filter((_, i) => i !== idx));
    setDirty(true);
  }, []);

  // --- Change zone ---
  const changeZone = useCallback((idx: number, zone: Zone) => {
    setUsed(prev => prev.map((f, i) => i === idx ? { ...f, zone } : f));
    setDirty(true);
  }, []);

  // --- Edit label ---
  const editLabel = useCallback((idx: number, label: string) => {
    setUsed(prev => prev.map((f, i) => i === idx ? { ...f, label } : f));
    setDirty(true);
  }, []);

  // --- Drag reorder within a zone ---
  const reorderInZone = useCallback((zone: Zone, fromIdx: number, toIdx: number) => {
    const zoneItems = used.filter(f => f.zone === zone);
    const otherItems = used.filter(f => f.zone !== zone);
    const [moved] = zoneItems.splice(fromIdx, 1);
    zoneItems.splice(toIdx, 0, moved);
    // Reconstruct: keep zone order (header, list, footer)
    const reordered: UsedField[] = [];
    for (const z of ZONES) {
      if (z === zone) reordered.push(...zoneItems);
      else reordered.push(...otherItems.filter(f => f.zone === z));
    }
    setUsed(reordered);
    setDirty(true);
  }, [used]);

  // --- Add custom field path ---
  const addCustomField = useCallback((zone: Zone) => {
    if (!customField.trim()) return;
    addField(customField.trim(), zone);
    setCustomField('');
  }, [customField, addField]);

  // --- Debounced preview ---
  useEffect(() => {
    if (previewTimer.current) clearTimeout(previewTimer.current);
    previewTimer.current = setTimeout(() => {
      try {
        const layout = arrangeLayout(used, model, title, paper);
        const data = sampleData || { ida: 'SAMPLE-001', status: 'draft', company: 'Sample Co.' };
        const html = generatePrintHtml(data, companyInfo, layout);
        setPreviewHtml(html);
      } catch (e) {
        console.error('[PrintLayoutDesigner] Preview failed:', e);
      }
    }, 300);
    return () => { if (previewTimer.current) clearTimeout(previewTimer.current); };
  }, [used, title, paper, model, sampleData, companyInfo]);

  // --- Save ---
  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const layout = arrangeLayout(used, model, title, paper);
      onSave(layout);
      setDirty(false);
      setStatusMsg('Saved');
      setTimeout(() => setStatusMsg(''), 2000);
    } catch (e: any) {
      setStatusMsg(`Save failed: ${e?.message || 'unknown'}`);
    } finally {
      setSaving(false);
    }
  }, [used, model, title, paper, onSave]);

  // --- Styles ---
  const fieldItemStyle = (selected?: boolean): React.CSSProperties => ({
    padding: '3px 8px', cursor: 'pointer', fontSize: fontSize - 2,
    borderBottom: `1px solid ${t.borderLight}`,
    background: selected ? t.surfaceAlt : 'transparent',
    display: 'flex', alignItems: 'center', gap: 6,
    transition: 'background 0.1s',
  });

  const zoneBadge = (zone: Zone): React.CSSProperties => ({
    padding: '1px 5px', borderRadius: 3, fontSize: fontSize - 4,
    fontWeight: 700, background: ZONE_COLORS[zone], color: '#fff',
    textTransform: 'uppercase' as const, letterSpacing: '0.04em',
    cursor: 'pointer', userSelect: 'none' as const,
  });

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div data-wc="print-layout-designer" style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      flex: 1, minWidth: 0,
    }}>
      {/* Toolbar */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '6px 12px', borderBottom: `1px solid ${t.border}`,
        background: t.surface,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontWeight: 700, fontSize, color: t.accent }}>Design</span>
          <span style={{ fontSize: fontSize - 2, color: t.textMuted }}>{report.name}</span>
          <span style={{ fontSize: fontSize - 3, color: t.textDim }}>|</span>
          <label style={{ fontSize: fontSize - 2, color: t.textMuted }}>
            Title: <input value={title} onChange={(e) => { setTitle(e.target.value); setDirty(true); }}
              style={{ background: t.bg, color: t.text, border: `1px solid ${t.borderLight}`, borderRadius: 3, padding: '2px 4px', fontSize: fontSize - 2, width: 120 }} />
          </label>
          <span onClick={() => { setPaper(paper === 'a4' ? 'letter' : 'a4'); setDirty(true); }}
            style={{ cursor: 'pointer', fontWeight: 700, color: t.accent, fontSize: fontSize - 2, userSelect: 'none' }}>
            {paper}
          </span>
          {dirty && <span style={{ fontSize: fontSize - 3, color: t.accentGold, fontWeight: 700 }}>UNSAVED</span>}
          {statusMsg && <span style={{ fontSize: fontSize - 2, color: t.accentGreen }}>{statusMsg}</span>}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button onClick={handleSave} disabled={saving || !dirty}
            style={{
              padding: '4px 12px', borderRadius: 4, cursor: dirty ? 'pointer' : 'default',
              fontSize: fontSize - 1, fontWeight: 600,
              background: dirty ? t.accent : 'none',
              border: dirty ? 'none' : `1px solid ${t.border}`,
              color: dirty ? '#fff' : t.textMuted, opacity: saving ? 0.6 : 1,
            }}>
            {saving ? 'Saving...' : 'Save'}
          </button>
          <button onClick={onClose}
            style={{
              padding: '4px 10px', borderRadius: 4, cursor: 'pointer',
              fontSize: fontSize - 1, fontWeight: 600,
              background: 'none', border: `1px solid ${t.border}`, color: t.text,
            }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = t.surfaceAlt; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'none'; }}>
            Close
          </button>
        </div>
      </div>

      {/* Body: two lists + preview */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* Left panel: Available + Used */}
        <div style={{ flex: '0 0 340px', display: 'flex', flexDirection: 'column', background: t.bg, borderRight: `1px solid ${t.border}` }}>

          {/* Available fields */}
          <div style={{ flex: '0 0 40%', display: 'flex', flexDirection: 'column', borderBottom: `2px solid ${t.border}` }}>
            <div style={{
              padding: '6px 10px', fontSize: fontSize - 2, fontWeight: 700, color: t.textMuted,
              textTransform: 'uppercase', letterSpacing: '0.04em',
              background: t.surface, borderBottom: `1px solid ${t.borderLight}`,
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <span>Available ({available.length})</span>
              <span style={{ fontSize: fontSize - 3, color: t.textDim, fontWeight: 400, textTransform: 'none' }}>Click to add</span>
            </div>
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {available.map(field => (
                <div key={field}
                  style={fieldItemStyle()}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = t.surfaceAlt; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                >
                  <span style={{ flex: 1, fontFamily: 'monospace', color: t.text }}>{field}</span>
                  <span onClick={() => addField(field, 'header')} style={zoneBadge('header')} title="Add to header">H</span>
                  <span onClick={() => addField(field, 'list')} style={zoneBadge('list')} title="Add to list/body">L</span>
                  <span onClick={() => addField(field, 'footer')} style={zoneBadge('footer')} title="Add to footer">F</span>
                </div>
              ))}
            </div>
            {/* Custom field entry */}
            <div style={{
              padding: '4px 8px', borderTop: `1px solid ${t.borderLight}`,
              display: 'flex', gap: 4, alignItems: 'center',
            }}>
              <input value={customField} onChange={(e) => setCustomField(e.target.value)}
                placeholder="custom.field.path"
                onKeyDown={(e) => { if (e.key === 'Enter') addCustomField('header'); }}
                style={{
                  flex: 1, background: t.bg, color: t.text, border: `1px solid ${t.borderLight}`,
                  borderRadius: 3, padding: '2px 4px', fontSize: fontSize - 2, fontFamily: 'monospace',
                }} />
              <span onClick={() => addCustomField('header')} style={zoneBadge('header')}>H</span>
              <span onClick={() => addCustomField('list')} style={zoneBadge('list')}>L</span>
              <span onClick={() => addCustomField('footer')} style={zoneBadge('footer')}>F</span>
            </div>
          </div>

          {/* Used fields — grouped by zone */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <div style={{
              padding: '6px 10px', fontSize: fontSize - 2, fontWeight: 700, color: t.textMuted,
              textTransform: 'uppercase', letterSpacing: '0.04em',
              background: t.surface, borderBottom: `1px solid ${t.borderLight}`,
            }}>
              Used ({used.length})
            </div>
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {ZONES.map(zone => {
                const zoneFields = used.map((f, i) => ({ ...f, globalIdx: i })).filter(f => f.zone === zone);
                if (zoneFields.length === 0 && zone !== 'header') return null;
                return (
                  <div key={zone}>
                    {/* Zone header */}
                    <div style={{
                      padding: '4px 10px', fontSize: fontSize - 3, fontWeight: 700,
                      color: ZONE_COLORS[zone], textTransform: 'uppercase',
                      background: t.surfaceAlt, borderBottom: `1px solid ${t.borderLight}`,
                      letterSpacing: '0.06em',
                    }}>
                      {ZONE_LABELS[zone]} ({zoneFields.length})
                    </div>
                    {/* Zone fields */}
                    {zoneFields.map((f, zoneIdx) => (
                      <div key={f.field + f.globalIdx}
                        draggable
                        onDragStart={() => setDragField({ field: f.field, source: zone })}
                        onDragEnd={() => setDragField(null)}
                        style={{
                          ...fieldItemStyle(),
                          cursor: 'grab',
                          borderLeft: `3px solid ${ZONE_COLORS[zone]}`,
                          paddingLeft: 6,
                        }}
                        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = t.surfaceAlt; }}
                        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                      >
                        {/* Drag grip */}
                        <span style={{ color: t.textDim, fontSize: fontSize - 2, userSelect: 'none' }}>⋮⋮</span>
                        {/* Field path */}
                        <span style={{ fontFamily: 'monospace', color: t.textDim, fontSize: fontSize - 3, minWidth: 80 }}>
                          {f.field}
                        </span>
                        {/* Editable label */}
                        <input value={f.label}
                          onChange={(e) => editLabel(f.globalIdx, e.target.value)}
                          onClick={(e) => e.stopPropagation()}
                          style={{
                            flex: 1, background: 'transparent', color: t.text,
                            border: 'none', borderBottom: `1px solid ${t.borderLight}`,
                            fontSize: fontSize - 2, padding: '1px 2px', outline: 'none',
                            minWidth: 50,
                          }} />
                        {/* Zone cycle */}
                        <span onClick={(e) => {
                          e.stopPropagation();
                          const nextZone = ZONES[(ZONES.indexOf(zone) + 1) % ZONES.length];
                          changeZone(f.globalIdx, nextZone);
                        }} style={zoneBadge(zone)} title={`Click to move to ${ZONE_LABELS[ZONES[(ZONES.indexOf(zone) + 1) % ZONES.length]]}`}>
                          {zone.charAt(0).toUpperCase()}
                        </span>
                        {/* Remove */}
                        <span onClick={(e) => { e.stopPropagation(); removeField(f.globalIdx); }}
                          style={{ color: t.textDim, cursor: 'pointer', fontSize: fontSize - 2, userSelect: 'none' }}
                          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = '#e55'; }}
                          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = t.textDim; }}
                        >&times;</span>
                      </div>
                    ))}
                    {zoneFields.length === 0 && (
                      <div style={{ padding: '8px 10px', fontSize: fontSize - 3, color: t.textDim, fontStyle: 'italic' }}>
                        Click H/L/F on available fields to add here
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right: live preview */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div style={{
            padding: '4px 12px', borderBottom: `1px solid ${t.borderLight}`,
            fontSize: fontSize - 2, color: t.textMuted,
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <span>Preview</span>
            <span style={{ fontSize: fontSize - 3, color: t.textDim }}>
              {sampleData?.ida ? `Record: ${sampleData.ida}` : 'Sample data'} · Auto-arranged
            </span>
          </div>
          <iframe
            srcDoc={previewHtml}
            style={{ flex: 1, border: 'none', background: '#fff', minHeight: 300 }}
            title="PrintLayout Preview"
          />
        </div>
      </div>
    </div>
  );
};

export default PrintLayoutDesigner;

/**
 * PrintLayoutDesigner — panel-based visual report layout editor.
 *
 * Three-panel design:
 *   Left:   Model/group selector (top) + Available fields (bottom)
 *   Middle: Sections as panels — drag to reorder, drop fields onto panels
 *   Right:  Live preview via UniversalPrint
 *
 * Panels are PrintLayout section types: company_header, address_blocks,
 * meta_row, line_items, totals, detail_fields, comments, signature, footer.
 * Insert pre-built panels from the + menu. Drag fields from left onto panels.
 *
 * LastChecked: 2026-08-10 | WhereUsed: ReportsDialog | WhoCreated: Bill+Claude
 */
import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import type { PrintLayout, PrintLayoutSection, PrintField } from './printLayoutTypes';
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

// Report field registry response shape (from /wcapi/report-fields/)
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

// ---------------------------------------------------------------------------
// Section type metadata
// ---------------------------------------------------------------------------

const SECTION_META: Record<string, { label: string; color: string; icon: string; hasFields: boolean }> = {
  company_header:  { label: 'Company Header',  color: '#0e639c', icon: 'H', hasFields: false },
  address_blocks:  { label: 'Address Blocks',  color: '#0e639c', icon: 'A', hasFields: true },
  meta_row:        { label: 'Info Row',         color: '#2563eb', icon: 'I', hasFields: true },
  detail_fields:   { label: 'Detail Fields',    color: '#2e7d32', icon: 'D', hasFields: true },
  comments:        { label: 'Comments',         color: '#6b7280', icon: 'C', hasFields: false },
  line_items:      { label: 'Line Items',       color: '#c05621', icon: 'L', hasFields: true },
  data_table:      { label: 'Data Table',       color: '#c05621', icon: 'T', hasFields: true },
  totals:          { label: 'Totals',           color: '#7b1fa2', icon: '$', hasFields: true },
  conditions:      { label: 'Conditions',       color: '#6b7280', icon: 'K', hasFields: false },
  signature:       { label: 'Signature',        color: '#555',    icon: 'S', hasFields: false },
  footer:          { label: 'Footer',           color: '#555',    icon: 'F', hasFields: true },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function guessFormat(field: string): PrintField['format'] {
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
  const last = field.includes('.') ? field.split('.').pop()! : field;
  return last
    .replace(/^dt_/, 'Date ')
    .replace(/^ida$/, 'ID')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

function makePrintField(field: string): PrintField {
  const fmt = guessFormat(field);
  return {
    field, label: autoLabel(field), format: fmt,
    align: guessAlign(fmt), width: guessWidth(field, fmt),
  };
}

/** Get field array from a section (fields, columns, or rows depending on type) */
function getSectionFields(section: PrintLayoutSection): PrintField[] {
  if ('fields' in section && Array.isArray((section as any).fields)) return (section as any).fields;
  if ('columns' in section && Array.isArray((section as any).columns)) {
    // address_blocks has columns[].fields — flatten
    if (section.type === 'address_blocks') {
      return (section as any).columns.flatMap((col: any) => col.fields || []);
    }
    return (section as any).columns;
  }
  if ('rows' in section && Array.isArray((section as any).rows)) return (section as any).rows;
  return [];
}

/** Set field array back into a section */
function setSectionFields(section: PrintLayoutSection, fields: PrintField[]): PrintLayoutSection {
  const s = { ...section } as any;
  if (section.type === 'meta_row' || section.type === 'detail_fields' || section.type === 'footer') {
    s.fields = fields;
  } else if (section.type === 'line_items' || section.type === 'data_table') {
    s.columns = fields;
  } else if (section.type === 'totals') {
    s.rows = fields;
  } else if (section.type === 'address_blocks') {
    // For address_blocks, add to last column or create one
    if (!s.columns?.length) s.columns = [{ title: 'Info', fields }];
    else {
      const last = { ...s.columns[s.columns.length - 1] };
      last.fields = [...(last.fields || []), ...fields];
      s.columns = [...s.columns.slice(0, -1), last];
    }
  }
  return s;
}

// ---------------------------------------------------------------------------
// Pre-built panel templates
// ---------------------------------------------------------------------------

const PANEL_TEMPLATES: Record<string, () => PrintLayoutSection> = {
  company_header: () => ({ type: 'company_header', logo: true, show_address: true, show_contact: true }),
  address_blocks: () => ({
    type: 'address_blocks',
    columns: [
      { title: 'Bill To', fields: [
        { field: 'attention', label: 'Attn' },
        { field: 'company', label: 'Company' },
        { field: 'address_full', label: 'Address' },
      ]},
      { title: 'Ship To', fields: [
        { field: 'config.ship_to.company', label: 'Company' },
        { field: 'config.ship_to.attention', label: 'Attn' },
        { field: 'config.ship_to.address1', label: 'Address' },
      ]},
      { title: 'Info', fields: [
        { field: 'ida', label: 'Order #' },
        { field: 'status', label: 'Status' },
        { field: 'dt_created', label: 'Date', format: 'date' as const },
        { field: 'terms', label: 'Terms' },
      ]},
    ],
  }),
  meta_row: () => ({
    type: 'meta_row',
    fields: [
      { field: 'ida', label: 'ID' },
      { field: 'status', label: 'Status' },
      { field: 'dt_created', label: 'Date', format: 'date' as const },
    ],
  }),
  detail_fields: () => ({ type: 'detail_fields', fields: [] }),
  comments: () => ({ type: 'comments', source: 'comments.public', label: 'Comments' }),
  line_items: () => ({
    type: 'line_items',
    columns: [
      { field: 'item.ida_item', label: 'Item', align: 'left' as const },
      { field: 'item.description', label: 'Description', align: 'left' as const, width: '40%' },
      { field: 'quantity.active', label: 'Qty', align: 'right' as const },
      { field: 'price.unit', label: 'Unit Price', align: 'right' as const, format: 'currency' as const },
      { field: 'price.extended', label: 'Extended', align: 'right' as const, format: 'currency' as const },
    ],
    show_footer_totals: true,
  }),
  data_table: () => ({ type: 'data_table', columns: [], grand_totals: true }),
  totals: () => ({
    type: 'totals',
    rows: [
      { field: 'totals.subtotal', label: 'Subtotal', format: 'currency' as const },
      { field: 'totals.tax', label: 'Tax', format: 'currency' as const },
      { field: 'totals.shipping', label: 'Shipping', format: 'currency' as const },
      { field: 'totals.total', label: 'Total', format: 'currency' as const, bold: true },
    ],
    left_text: 'Thank you for your business.',
  }),
  conditions: () => ({ type: 'conditions', source: 'conditions_description' }),
  signature: () => ({
    type: 'signature',
    preamble: 'Authorized by:',
    blocks: [{ label: 'Signature', lines: ['Signature', 'Date'] }],
  }),
  footer: () => ({
    type: 'footer',
    fields: [
      { field: 'ida', label: 'Order #' },
      { field: 'customer_id', label: 'Customer #' },
    ],
  }),
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const PrintLayoutDesigner: React.FC<PrintLayoutDesignerProps> = ({
  report, model, layout: initialLayout,
  theme: t, fontSize, companyInfo, sampleData,
  onSave, onClose,
}) => {
  const [sections, setSections] = useState<PrintLayoutSection[]>(initialLayout.sections || []);
  const [title, setTitle] = useState(initialLayout.title || report.name || '');
  const [paper, setPaper] = useState(initialLayout.paper || 'letter');
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [previewHtml, setPreviewHtml] = useState('');
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<number>(0);
  const [insertMenuOpen, setInsertMenuOpen] = useState(false);
  const previewTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch fields from /wcapi/report-fields/ registry
  const [registry, setRegistry] = useState<ReportFieldsResponse | null>(null);
  useEffect(() => {
    if (!model) return;
    fetch(`/wcapi/report-fields/?model=${encodeURIComponent(model)}`, { credentials: 'include' })
      .then(r => r.json())
      .then(data => { if (data && !data.error) setRegistry(data); })
      .catch(() => {});
  }, [model]);

  // Build field groups from registry
  const { groups, groupNames } = useMemo(() => {
    if (!registry) return { groups: {} as Record<string, RegistryField[]>, groupNames: [] as string[] };
    const grp: Record<string, RegistryField[]> = {};
    grp[model] = registry.direct || [];
    for (const [relName, relFields] of Object.entries(registry.related || {})) grp[relName] = relFields;
    for (const f of registry.json_paths || []) {
      const g = f.group || 'json';
      if (!grp[g]) grp[g] = [];
      grp[g].push(f);
    }
    if ((registry.lines || []).length > 0) grp[registry.line_model || 'lines'] = registry.lines;
    const names = Object.keys(grp).sort((a, b) => a === model ? -1 : b === model ? 1 : a.localeCompare(b));
    return { groups: grp, groupNames: names };
  }, [registry, model]);

  // Auto-select first group
  useEffect(() => {
    if (!selectedGroup && groupNames.length > 0) setSelectedGroup(groupNames[0]);
  }, [groupNames, selectedGroup]);

  // Collect all used field paths across all sections
  const usedFieldPaths = useMemo(() => {
    const paths = new Set<string>();
    for (const s of sections) {
      for (const f of getSectionFields(s)) paths.add(f.field);
    }
    return paths;
  }, [sections]);

  const visibleFields: RegistryField[] = selectedGroup
    ? (groups[selectedGroup] || []).filter(f => !usedFieldPaths.has(f.field))
    : [];

  // --- Section operations ---
  const addSection = useCallback((type: string) => {
    const template = PANEL_TEMPLATES[type];
    if (!template) return;
    setSections(prev => [...prev, template()]);
    setDirty(true);
    setInsertMenuOpen(false);
    setSelectedSection(sections.length); // select newly added
  }, [sections.length]);

  const removeSection = useCallback((idx: number) => {
    setSections(prev => prev.filter((_, i) => i !== idx));
    setDirty(true);
    if (selectedSection >= idx && selectedSection > 0) setSelectedSection(selectedSection - 1);
  }, [selectedSection]);

  const moveSection = useCallback((idx: number, dir: -1 | 1) => {
    setSections(prev => {
      const newIdx = idx + dir;
      if (newIdx < 0 || newIdx >= prev.length) return prev;
      const arr = [...prev];
      [arr[idx], arr[newIdx]] = [arr[newIdx], arr[idx]];
      return arr;
    });
    setSelectedSection(idx + dir);
    setDirty(true);
  }, []);

  // Add field to selected section
  const addFieldToSection = useCallback((fieldPath: string) => {
    if (selectedSection < 0 || selectedSection >= sections.length) return;
    const section = sections[selectedSection];
    const meta = SECTION_META[section.type];
    if (!meta?.hasFields) return;

    const pf = makePrintField(fieldPath);
    setSections(prev => prev.map((s, i) => {
      if (i !== selectedSection) return s;
      const existing = getSectionFields(s);
      return setSectionFields(s, [...existing, pf]);
    }));
    setDirty(true);
  }, [selectedSection, sections]);

  // Remove field from a section
  const removeFieldFromSection = useCallback((sectionIdx: number, fieldIdx: number) => {
    setSections(prev => prev.map((s, i) => {
      if (i !== sectionIdx) return s;
      const fields = getSectionFields(s).filter((_, fi) => fi !== fieldIdx);
      return setSectionFields({ ...s } as any, fields);
    }));
    setDirty(true);
  }, []);

  // Edit field label in a section
  const editFieldLabel = useCallback((sectionIdx: number, fieldIdx: number, label: string) => {
    setSections(prev => prev.map((s, i) => {
      if (i !== sectionIdx) return s;
      const fields = getSectionFields(s).map((f, fi) => fi === fieldIdx ? { ...f, label } : f);
      return setSectionFields({ ...s } as any, fields);
    }));
    setDirty(true);
  }, []);

  // --- Build layout from sections ---
  const buildLayout = useCallback((): PrintLayout => ({
    model,
    title: title || model.charAt(0).toUpperCase() + model.slice(1),
    paper: (paper as any) || 'letter',
    sections,
  }), [model, title, paper, sections]);

  // --- Debounced preview ---
  useEffect(() => {
    if (previewTimer.current) clearTimeout(previewTimer.current);
    previewTimer.current = setTimeout(() => {
      try {
        const layout = buildLayout();
        const data = sampleData || { ida: 'SAMPLE-001', status: 'draft', company: 'Sample Co.' };
        const html = generatePrintHtml(data, companyInfo, layout);
        setPreviewHtml(html);
      } catch (e) {
        console.error('[PrintLayoutDesigner] Preview failed:', e);
      }
    }, 300);
    return () => { if (previewTimer.current) clearTimeout(previewTimer.current); };
  }, [sections, title, paper, model, sampleData, companyInfo, buildLayout]);

  // --- Save ---
  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      onSave(buildLayout());
      setDirty(false);
      setStatusMsg('Saved');
      setTimeout(() => setStatusMsg(''), 2000);
    } catch (e: any) {
      setStatusMsg(`Save failed: ${e?.message || 'unknown'}`);
    } finally {
      setSaving(false);
    }
  }, [buildLayout, onSave]);

  // --- Style helper ---
  const panelHeader = (label: string): React.CSSProperties => ({
    padding: '6px 10px', fontSize: fontSize - 2, fontWeight: 700, color: t.textMuted,
    textTransform: 'uppercase', letterSpacing: '0.04em',
    background: t.surface, borderBottom: `1px solid ${t.borderLight}`,
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    userSelect: 'none',
  });

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div data-wc="print-layout-designer" style={{
      display: 'flex', flexDirection: 'column', height: '100%', flex: 1, minWidth: 0,
    }}>
      {/* Toolbar */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '6px 12px', borderBottom: `1px solid ${t.border}`, background: t.surface,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontWeight: 700, fontSize, color: t.accent }}>Edit</span>
          <span style={{ fontSize: fontSize - 2, color: t.textMuted }}>{report.name}</span>
          <span style={{ fontSize: fontSize - 3, color: t.textDim }}>|</span>
          <label style={{ fontSize: fontSize - 2, color: t.textMuted }}>
            Title: <input value={title} onChange={(e) => { setTitle(e.target.value); setDirty(true); }}
              style={{ background: t.bg, color: t.text, border: `1px solid ${t.borderLight}`,
                borderRadius: 3, padding: '2px 4px', fontSize: fontSize - 2, width: 140 }} />
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

      {/* Body: three panels */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* === LEFT PANEL: Models + Fields === */}
        <div style={{
          flex: '0 0 240px', display: 'flex', flexDirection: 'column',
          background: t.bg, borderRight: `1px solid ${t.border}`,
        }}>
          {/* Model group selector */}
          <div style={{ flex: '0 0 auto', borderBottom: `2px solid ${t.border}` }}>
            <div style={panelHeader('Groups')}>
              <span>Models</span>
              <span style={{ fontSize: fontSize - 3, color: t.textDim, fontWeight: 400, textTransform: 'none' }}>
                {groupNames.length}
              </span>
            </div>
            <div style={{ maxHeight: 160, overflowY: 'auto' }}>
              {groupNames.map(g => (
                <div key={g}
                  onClick={() => setSelectedGroup(g)}
                  style={{
                    padding: '4px 10px', cursor: 'pointer', fontSize: fontSize - 1,
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    background: selectedGroup === g ? t.surfaceAlt : 'transparent',
                    borderLeft: selectedGroup === g ? `3px solid ${t.accent}` : '3px solid transparent',
                    color: selectedGroup === g ? t.text : t.textMuted,
                    fontWeight: selectedGroup === g ? 600 : 400,
                  }}
                  onMouseEnter={(e) => { if (selectedGroup !== g) (e.currentTarget as HTMLElement).style.background = t.surfaceAlt; }}
                  onMouseLeave={(e) => { if (selectedGroup !== g) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                >
                  <span>{g}</span>
                  <span style={{ fontSize: fontSize - 3, color: t.textDim }}>
                    {(groups[g] || []).length}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Available fields */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <div style={panelHeader('Fields')}>
              <span>Fields</span>
              <span style={{ fontSize: fontSize - 3, color: t.textDim, fontWeight: 400, textTransform: 'none' }}>
                dbl-click to add
              </span>
            </div>
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {visibleFields.map(rf => (
                <div key={rf.field}
                  onDoubleClick={() => addFieldToSection(rf.field)}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData('text/plain', rf.field);
                    e.dataTransfer.effectAllowed = 'copy';
                  }}
                  style={{
                    padding: '3px 10px', cursor: 'pointer', fontSize: fontSize - 2,
                    display: 'flex', alignItems: 'center', gap: 6,
                    borderBottom: `1px solid ${t.borderLight}`,
                    background: 'transparent',
                  }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = t.surfaceAlt; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                >
                  <span style={{ flex: 1, color: t.text }}>{rf.label}</span>
                  <span style={{ fontFamily: 'monospace', fontSize: fontSize - 4, color: t.textDim }}>{rf.field}</span>
                  <span style={{ fontSize: fontSize - 4, color: t.textDim, fontStyle: 'italic' }}>{rf.type}</span>
                </div>
              ))}
              {visibleFields.length === 0 && (
                <div style={{ padding: '12px 10px', fontSize: fontSize - 2, color: t.textDim, textAlign: 'center' }}>
                  {selectedGroup ? 'All fields in use' : 'Select a model'}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* === MIDDLE PANEL: Sections as panels === */}
        <div style={{
          flex: '0 0 340px', display: 'flex', flexDirection: 'column',
          background: t.bg, borderRight: `1px solid ${t.border}`,
        }}>
          <div style={{
            ...panelHeader('Panels'),
            gap: 6,
          }}>
            <span>Panels ({sections.length})</span>
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => setInsertMenuOpen(!insertMenuOpen)}
                style={{
                  padding: '2px 8px', borderRadius: 3, cursor: 'pointer',
                  fontSize: fontSize - 2, fontWeight: 700,
                  background: t.accent, border: 'none', color: '#fff',
                }}
              >+ Insert</button>
              {insertMenuOpen && (
                <div style={{
                  position: 'absolute', top: '100%', right: 0, zIndex: 100,
                  background: t.surface, border: `1px solid ${t.border}`,
                  borderRadius: 4, boxShadow: '0 4px 16px rgba(0,0,0,0.3)',
                  minWidth: 180, maxHeight: 300, overflowY: 'auto',
                }}>
                  {Object.entries(SECTION_META).map(([type, meta]) => (
                    <div key={type}
                      onClick={() => addSection(type)}
                      style={{
                        padding: '6px 12px', cursor: 'pointer', fontSize: fontSize - 1,
                        display: 'flex', alignItems: 'center', gap: 8,
                        borderBottom: `1px solid ${t.borderLight}`,
                      }}
                      onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = t.surfaceAlt; }}
                      onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                    >
                      <span style={{
                        width: 20, height: 20, borderRadius: 3,
                        background: meta.color, color: '#fff',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: fontSize - 3, fontWeight: 700,
                      }}>{meta.icon}</span>
                      <span style={{ color: t.text }}>{meta.label}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {sections.map((section, sIdx) => {
              const meta = SECTION_META[section.type] || { label: section.type, color: '#555', icon: '?', hasFields: false };
              const isSelected = sIdx === selectedSection;
              const fields = getSectionFields(section);

              return (
                <div key={sIdx}
                  onClick={() => setSelectedSection(sIdx)}
                  onDragOver={(e) => {
                    e.preventDefault();
                    if (meta.hasFields) setSelectedSection(sIdx);
                  }}
                  onDrop={(e) => {
                    e.preventDefault();
                    const fieldName = e.dataTransfer.getData('text/plain');
                    if (fieldName && !usedFieldPaths.has(fieldName) && meta.hasFields) {
                      setSelectedSection(sIdx);
                      // Need to add directly since selectedSection update is async
                      const pf = makePrintField(fieldName);
                      setSections(prev => prev.map((s, i) => {
                        if (i !== sIdx) return s;
                        return setSectionFields(s, [...getSectionFields(s), pf]);
                      }));
                      setDirty(true);
                    }
                  }}
                  style={{
                    borderBottom: `1px solid ${t.borderLight}`,
                    borderLeft: isSelected ? `3px solid ${meta.color}` : '3px solid transparent',
                    background: isSelected ? t.surfaceAlt : 'transparent',
                    cursor: 'pointer',
                  }}
                >
                  {/* Panel header */}
                  <div style={{
                    padding: '6px 8px', display: 'flex', alignItems: 'center', gap: 6,
                    borderTop: `2px solid ${meta.color}`,
                  }}>
                    <span style={{
                      width: 18, height: 18, borderRadius: 3,
                      background: meta.color, color: '#fff',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: fontSize - 3, fontWeight: 700, flexShrink: 0,
                    }}>{meta.icon}</span>
                    <span style={{ flex: 1, fontSize: fontSize - 1, fontWeight: 600, color: t.text }}>
                      {meta.label}
                    </span>
                    {fields.length > 0 && (
                      <span style={{ fontSize: fontSize - 3, color: t.textDim }}>{fields.length}</span>
                    )}
                    {/* Move up/down */}
                    <span onClick={(e) => { e.stopPropagation(); moveSection(sIdx, -1); }}
                      style={{ cursor: sIdx > 0 ? 'pointer' : 'default', color: sIdx > 0 ? t.textMuted : t.borderLight, fontSize: fontSize - 2, userSelect: 'none' }}
                    >▲</span>
                    <span onClick={(e) => { e.stopPropagation(); moveSection(sIdx, 1); }}
                      style={{ cursor: sIdx < sections.length - 1 ? 'pointer' : 'default', color: sIdx < sections.length - 1 ? t.textMuted : t.borderLight, fontSize: fontSize - 2, userSelect: 'none' }}
                    >▼</span>
                    {/* Remove */}
                    <span onClick={(e) => { e.stopPropagation(); removeSection(sIdx); }}
                      style={{ color: t.textDim, cursor: 'pointer', fontSize: fontSize - 1, userSelect: 'none' }}
                      onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = '#e55'; }}
                      onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = t.textDim; }}
                    >&times;</span>
                  </div>

                  {/* Panel fields — shown when selected */}
                  {isSelected && meta.hasFields && (
                    <div style={{ padding: '0 0 4px 0' }}>
                      {fields.map((f, fIdx) => (
                        <div key={f.field + fIdx}
                          style={{
                            padding: '2px 8px 2px 28px', fontSize: fontSize - 2,
                            display: 'flex', alignItems: 'center', gap: 4,
                            borderBottom: `1px solid ${t.borderLight}`,
                          }}
                        >
                          <input value={f.label || ''}
                            onChange={(e) => editFieldLabel(sIdx, fIdx, e.target.value)}
                            onClick={(e) => e.stopPropagation()}
                            style={{
                              flex: 1, background: 'transparent', color: t.text,
                              border: 'none', borderBottom: `1px solid ${t.borderLight}`,
                              fontSize: fontSize - 2, padding: '1px 2px', outline: 'none',
                              minWidth: 40,
                            }} />
                          <span style={{ fontFamily: 'monospace', color: t.textDim, fontSize: fontSize - 4 }}>
                            {f.field}
                          </span>
                          <span onClick={(e) => { e.stopPropagation(); removeFieldFromSection(sIdx, fIdx); }}
                            style={{ color: t.textDim, cursor: 'pointer', fontSize: fontSize - 1, userSelect: 'none' }}
                            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = '#e55'; }}
                            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = t.textDim; }}
                          >&times;</span>
                        </div>
                      ))}
                      {fields.length === 0 && (
                        <div style={{ padding: '6px 28px', fontSize: fontSize - 3, color: t.textDim, fontStyle: 'italic' }}>
                          Double-click or drag fields here
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
            {sections.length === 0 && (
              <div style={{ padding: '24px 16px', color: t.textDim, textAlign: 'center', fontSize: fontSize - 1 }}>
                Click <strong>+ Insert</strong> to add panels
              </div>
            )}
          </div>
        </div>

        {/* === RIGHT PANEL: Live preview === */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div style={{
            padding: '6px 12px', borderBottom: `1px solid ${t.borderLight}`,
            fontSize: fontSize - 2, color: t.textMuted,
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <span>Preview</span>
            <span style={{ fontSize: fontSize - 3, color: t.textDim }}>
              {sampleData?.ida ? `Record: ${sampleData.ida}` : 'Sample data'}
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

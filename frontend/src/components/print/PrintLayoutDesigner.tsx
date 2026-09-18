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
 * LastChecked: 2026-08-12 | WhereUsed: ReportsDialog | WhoCreated: Bill+Claude
 */
import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import type { PrintLayout, PrintLayoutSection, PrintField } from './printLayoutTypes';
import { generatePrintHtml } from './UniversalPrint';
import { generateFormSvg, downloadSvg } from './SvgFormGenerator';
import type { ReportRecord } from '../common/ReportsDialog';
import { getModelNames } from '@/api/wcapi';
import './PrintLayoutDesigner.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PrintLayoutDesignerProps {
  report: ReportRecord;
  model: string;
  layout: PrintLayout;
  fontSize: number;
  companyInfo: any;
  sampleData: any;
  onSave: (layout: PrintLayout) => void;
  onClose: () => void;
}

// Report field registry response shape (from /wcapi/_report_fields/)
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
  conditional_text:{ label: 'Conditional Text', color: '#b45309', icon: '?', hasFields: false },
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
    .replace(/^dt_/, 'date ')
    .replace(/^ida$/, 'id')
    .replace(/_/g, ' ');
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
        { field: 'attention', label: 'attn' },
        { field: 'company', label: 'company' },
        { field: 'address_full', label: 'address' },
      ]},
      { title: 'Ship To', fields: [
        { field: 'config.ship_to.company', label: 'company' },
        { field: 'config.ship_to.attention', label: 'attn' },
        { field: 'config.ship_to.address1', label: 'address' },
      ]},
      { title: 'Info', fields: [
        { field: 'ida', label: 'order #' },
        { field: 'status', label: 'status' },
        { field: 'dt_created', label: 'date', format: 'date' as const },
        { field: 'terms', label: 'terms' },
      ]},
    ],
  }),
  meta_row: () => ({
    type: 'meta_row',
    fields: [
      { field: 'ida', label: 'id' },
      { field: 'status', label: 'status' },
      { field: 'dt_created', label: 'date', format: 'date' as const },
    ],
  }),
  detail_fields: () => ({ type: 'detail_fields', fields: [] }),
  comments: () => ({ type: 'comments', source: 'comments.public', label: 'Comments' }),
  line_items: () => ({
    type: 'line_items',
    columns: [
      { field: 'item.ida_item', label: 'item', align: 'left' as const },
      { field: 'item.description', label: 'description', align: 'left' as const, width: '40%' },
      { field: 'quantity.active', label: 'qty', align: 'right' as const },
      { field: 'price.unit', label: 'unit price', align: 'right' as const, format: 'currency' as const },
      { field: 'price.extended', label: 'extended', align: 'right' as const, format: 'currency' as const },
    ],
    show_footer_totals: true,
  }),
  data_table: () => ({ type: 'data_table', columns: [], grand_totals: true }),
  totals: () => ({
    type: 'totals',
    rows: [
      { field: 'totals.subtotal', label: 'subtotal', format: 'currency' as const },
      { field: 'totals.tax', label: 'tax', format: 'currency' as const },
      { field: 'totals.shipping', label: 'shipping', format: 'currency' as const },
      { field: 'totals.total', label: 'total', format: 'currency' as const, bold: true },
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
      { field: 'ida', label: 'order #' },
      { field: 'customer_id', label: 'customer #' },
    ],
  }),
  conditional_text: () => ({ type: 'conditional_text', source: 'statement.comments' } as any),
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const PrintLayoutDesigner: React.FC<PrintLayoutDesignerProps> = ({
  report, model, layout: initialLayout,
  fontSize, companyInfo, sampleData,
  onSave, onClose,
}) => {
  const [sections, setSections] = useState<PrintLayoutSection[]>(initialLayout.sections || []);
  const [title, setTitle] = useState(initialLayout.title || report.name || '');
  const [paper, setPaper] = useState(initialLayout.paper || 'letter');
  const [linesPage1, setLinesPage1] = useState(initialLayout.lines_page_1 || 15);
  const [linesFollowing, setLinesFollowing] = useState(initialLayout.lines_following || 25);
  const [maxDescLines, setMaxDescLines] = useState(initialLayout.max_description_lines || 2);
  const [showPageNumbers, setShowPageNumbers] = useState(initialLayout.show_page_numbers ?? true);
  const [showDomain, setShowDomain] = useState(initialLayout.show_domain ?? true);
  const [textFormat, setTextFormat] = useState<'markdown' | 'plain'>(initialLayout.text_format || 'plain');
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [previewHtml, setPreviewHtml] = useState('');
  const [selectedSection, setSelectedSection] = useState<number>(0);
  const [insertMenuOpen, setInsertMenuOpen] = useState(false);
  const previewTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // --- Resizable panel widths ---
  const [leftWidth, setLeftWidth] = useState(240);
  const [midWidth, setMidWidth] = useState(340);
  const dragRef = useRef<{ which: 'left' | 'mid'; startX: number; startW: number } | null>(null);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!dragRef.current) return;
      const delta = e.clientX - dragRef.current.startX;
      const newW = Math.max(160, Math.min(600, dragRef.current.startW + delta));
      if (dragRef.current.which === 'left') setLeftWidth(newW);
      else setMidWidth(newW);
    };
    const onMouseUp = () => { dragRef.current = null; document.body.style.cursor = ''; document.body.style.userSelect = ''; };
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    return () => { window.removeEventListener('mousemove', onMouseMove); window.removeEventListener('mouseup', onMouseUp); };
  }, []);

  // Fetch all model names for the model list
  const [allModelNames, setAllModelNames] = useState<string[]>([]);
  useEffect(() => {
    getModelNames().then((res: any) => {
      const names = res?.model_names || res?.data?.model_names || [];
      setAllModelNames(names.sort());
    }).catch(() => {});
  }, []);

  // Fetch fields for a model — cache results
  const registryCache = useRef<Record<string, ReportFieldsResponse>>({});
  const [activeModel, setActiveModel] = useState(model); // which model's fields are shown
  const [registry, setRegistry] = useState<ReportFieldsResponse | null>(null);

  const fetchModelFields = useCallback((m: string) => {
    if (registryCache.current[m]) {
      setRegistry(registryCache.current[m]);
      setActiveModel(m);
      return;
    }
    fetch(`/wcapi/_report_fields/?model=${encodeURIComponent(m)}`, { credentials: 'include' })
      .then(r => r.json())
      .then(data => {
        if (data && !data.error) {
          registryCache.current[m] = data;
          setRegistry(data);
          setActiveModel(m);
        }
      })
      .catch(() => {});
  }, []);

  // Fetch base model on mount
  useEffect(() => { if (model) fetchModelFields(model); }, [model, fetchModelFields]);

  // Build field groups from current registry
  const fieldGroups = useMemo(() => {
    if (!registry) return [] as RegistryField[];
    const all: RegistryField[] = [...(registry.direct || [])];
    for (const relFields of Object.values(registry.related || {})) all.push(...relFields);
    for (const f of registry.json_paths || []) all.push(f);
    if ((registry.lines || []).length > 0) all.push(...registry.lines);
    return all;
  }, [registry]);

  // Collect all used field paths across all sections
  const usedFieldPaths = useMemo(() => {
    const paths = new Set<string>();
    for (const s of sections) {
      for (const f of getSectionFields(s)) paths.add(f.field);
    }
    return paths;
  }, [sections]);

  const visibleFields: RegistryField[] = fieldGroups.filter(f => !usedFieldPaths.has(f.field));

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
    lines_page_1: linesPage1,
    lines_following: linesFollowing,
    max_description_lines: maxDescLines,
    show_page_numbers: showPageNumbers,
    show_domain: showDomain,
    text_format: textFormat,
    sections,
    ...((window as any).__pld_svg_template ? { svg_template: (window as any).__pld_svg_template } : {}),
  }), [model, title, paper, linesPage1, linesFollowing, maxDescLines, showPageNumbers, showDomain, textFormat, sections]);

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

  // --- Import SVG (designed template handed back) ---
  const svgFileRef = useRef<HTMLInputElement>(null);
  const handleImportSvg = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const svgString = reader.result as string;
      // Store SVG template in the layout — saved to the Setting on next Save
      setSections(prev => prev); // trigger dirty
      // We store the raw SVG string; buildLayout will include it
      (window as any).__pld_svg_template = svgString;
      setDirty(true);
      setStatusMsg('SVG imported');
      setTimeout(() => setStatusMsg(''), 2000);
    };
    reader.readAsText(file);
    // Reset input so same file can be re-imported
    e.target.value = '';
  }, []);

  // --- Export SVG ---
  const handleExportSvg = useCallback(() => {
    const layout = buildLayout();
    const svg = generateFormSvg(layout);
    const filename = `${model}_${title || 'form'}_template`.replace(/\s+/g, '_');
    downloadSvg(svg, filename);
    setStatusMsg('SVG exported');
    setTimeout(() => setStatusMsg(''), 2000);
  }, [buildLayout, model, title]);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div data-wc="print-layout-designer" className="pld-root"
      style={{ '--pld-fs': `${fontSize}px` } as React.CSSProperties}>
      {/* Toolbar */}
      <div className="pld-toolbar">
        <div className="pld-toolbar-left">
          <span className="pld-toolbar-title">Edit</span>
          <span className="pld-toolbar-subtitle">{report.name}</span>
          <span className="pld-toolbar-sep">|</span>
          <label className="pld-toolbar-label">
            Title: <input value={title} onChange={(e) => { setTitle(e.target.value); setDirty(true); }}
              className="pld-toolbar-input" />
          </label>
          <select value={paper}
            onChange={(e) => { setPaper(e.target.value); setDirty(true); }}
            className="pld-toolbar-select"
          >
            <option value="letter">US Letter</option>
            <option value="legal">US Legal</option>
            <option value="a4">A4</option>
          </select>
          <span className="pld-toolbar-sep">|</span>
          <label className="pld-toolbar-label" title="Line item rows on page 1">
            Pg1: <input type="number" value={linesPage1} min={1} max={50}
              onChange={(e) => { setLinesPage1(Number(e.target.value)); setDirty(true); }}
              className="pld-toolbar-input pld-toolbar-input--narrow" />
          </label>
          <label className="pld-toolbar-label" title="Line item rows on following pages">
            Pg2+: <input type="number" value={linesFollowing} min={1} max={50}
              onChange={(e) => { setLinesFollowing(Number(e.target.value)); setDirty(true); }}
              className="pld-toolbar-input pld-toolbar-input--narrow" />
          </label>
          <label className="pld-toolbar-label" title="Max description lines before truncation">
            Wrap: <input type="number" value={maxDescLines} min={1} max={10}
              onChange={(e) => { setMaxDescLines(Number(e.target.value)); setDirty(true); }}
              className="pld-toolbar-input pld-toolbar-input--narrow" />
          </label>
          <span className="pld-toolbar-sep">|</span>
          <label className="pld-toolbar-label pld-toolbar-label--check">
            <input type="checkbox" checked={showPageNumbers}
              onChange={(e) => { setShowPageNumbers(e.target.checked); setDirty(true); }} />
            Pg #
          </label>
          <label className="pld-toolbar-label pld-toolbar-label--check">
            <input type="checkbox" checked={showDomain}
              onChange={(e) => { setShowDomain(e.target.checked); setDirty(true); }} />
            Domain
          </label>
          <select value={textFormat}
            onChange={(e) => { setTextFormat(e.target.value as any); setDirty(true); }}
            className="pld-toolbar-select"
            title="Rich text format for comments/conditions"
          >
            <option value="plain">Plain text</option>
            <option value="markdown">Markdown</option>
          </select>
          {dirty && <span className="pld-unsaved">UNSAVED</span>}
          {statusMsg && <span className="pld-status">{statusMsg}</span>}
        </div>
        <div className="pld-toolbar-right">
          <button onClick={handleExportSvg} className="pld-btn-export" title="Export SVG template for external design">
            Export SVG
          </button>
          <button onClick={() => svgFileRef.current?.click()} className="pld-btn-export" title="Import designed SVG template back">
            Import SVG
          </button>
          <input ref={svgFileRef} type="file" accept=".svg" onChange={handleImportSvg} style={{ display: 'none' }} />
          <button onClick={handleSave} disabled={saving || !dirty}
            className={`pld-btn-save${dirty ? ' pld-btn-save--dirty' : ''}${saving ? ' pld-btn-save--saving' : ''}`}>
            {saving ? 'Saving...' : 'Save'}
          </button>
          <button onClick={onClose} className="pld-btn-close">
            Close
          </button>
        </div>
      </div>

      {/* Body: Panels | Preview | Fields+Models */}
      <div className="pld-body">

        {/* === LEFT PANEL: Sections as panels === */}
        <div className="pld-panels-col" style={{ flex: `0 0 ${midWidth}px` }}>
          <div className="pld-panel-header pld-panel-header--gap">
            <span>Panels ({sections.length})</span>
            <div className="pld-insert-wrap">
              <button
                onClick={() => setInsertMenuOpen(!insertMenuOpen)}
                className="pld-insert-btn"
              >+ Insert</button>
              {insertMenuOpen && (
                <div className="pld-insert-menu">
                  {Object.entries(SECTION_META).map(([type, meta]) => (
                    <div key={type}
                      onClick={() => addSection(type)}
                      className="pld-insert-item"
                    >
                      <span className="pld-section-icon"
                        style={{ background: meta.color }}>{meta.icon}</span>
                      <span className="pld-insert-item-label">{meta.label}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
          <div className="pld-panels-scroll">
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
                      const pf = makePrintField(fieldName);
                      setSections(prev => prev.map((s, i) => {
                        if (i !== sIdx) return s;
                        return setSectionFields(s, [...getSectionFields(s), pf]);
                      }));
                      setDirty(true);
                    }
                  }}
                  className={`pld-section-card${isSelected ? ' pld-section-card--selected' : ''}`}
                  style={{ '--pld-section-color': meta.color } as React.CSSProperties}
                >
                  {/* Panel header */}
                  <div className="pld-section-head" style={{ borderTop: `2px solid ${meta.color}` }}>
                    <span className="pld-section-icon pld-section-icon--sm"
                      style={{ background: meta.color }}>{meta.icon}</span>
                    <span className="pld-section-title">{meta.label}</span>
                    {fields.length > 0 && (
                      <span className="pld-section-count">{fields.length}</span>
                    )}
                    <span onClick={(e) => { e.stopPropagation(); moveSection(sIdx, -1); }}
                      className={`pld-section-move ${sIdx > 0 ? 'pld-section-move--active' : 'pld-section-move--disabled'}`}
                    >&#9650;</span>
                    <span onClick={(e) => { e.stopPropagation(); moveSection(sIdx, 1); }}
                      className={`pld-section-move ${sIdx < sections.length - 1 ? 'pld-section-move--active' : 'pld-section-move--disabled'}`}
                    >&#9660;</span>
                    <span onClick={(e) => { e.stopPropagation(); removeSection(sIdx); }}
                      className="pld-section-remove"
                    >&times;</span>
                  </div>

                  {/* Panel fields — shown when selected */}
                  {isSelected && meta.hasFields && (
                    <div className="pld-section-fields">
                      {fields.map((f, fIdx) => (
                        <div key={f.field + fIdx} className="pld-section-field-row">
                          <input value={f.label || ''}
                            onChange={(e) => editFieldLabel(sIdx, fIdx, e.target.value)}
                            onClick={(e) => e.stopPropagation()}
                            className="pld-section-field-input" />
                          <span className="pld-section-field-path">{f.field}</span>
                          <span onClick={(e) => { e.stopPropagation(); removeFieldFromSection(sIdx, fIdx); }}
                            className="pld-section-field-remove"
                          >&times;</span>
                        </div>
                      ))}
                      {fields.length === 0 && (
                        <div className="pld-section-empty-hint">
                          Double-click or drag fields here
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
            {sections.length === 0 && (
              <div className="pld-panels-empty">
                Click <strong>+ Insert</strong> to add panels
              </div>
            )}
          </div>
        </div>

        {/* Drag handle: panels / preview */}
        <div
          onMouseDown={(e) => {
            dragRef.current = { which: 'left', startX: e.clientX, startW: leftWidth };
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
          }}
          className="pld-drag-handle"
        />

        {/* === CENTER PANEL: Live preview — fixed to paper size === */}
        <div className="pld-preview-col">
          <div className="pld-preview-header">
            <span>Preview</span>
            <span className="pld-preview-record">
              {sampleData?.ida ? `Record: ${sampleData.ida}` : 'Sample data'}
            </span>
          </div>
          <div className="pld-preview-body">
            <iframe
              srcDoc={previewHtml}
              className="pld-preview-iframe"
              style={{
                width: paper === 'a4' ? 595 : 612,
                height: paper === 'legal' ? 1008 : paper === 'a4' ? 842 : 792,
              }}
              title="PrintLayout Preview"
            />
          </div>
        </div>

        {/* Drag handle: preview / fields */}
        <div
          onMouseDown={(e) => {
            dragRef.current = { which: 'mid', startX: e.clientX, startW: midWidth };
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
          }}
          className="pld-drag-handle"
        />

        {/* === RIGHT PANEL: Fields (top) + Models (bottom) === */}
        <div className="pld-fields-col" style={{ flex: `0 0 ${midWidth}px` }}>
          {/* Fields for selected model — top, takes most space */}
          <div className="pld-fields-inner">
            <div className="pld-panel-header">
              <span>{activeModel} fields</span>
              <span className="pld-fields-hint">dbl-click to add</span>
            </div>
            <div className="pld-fields-scroll">
              {visibleFields.map(rf => (
                <div key={rf.field}
                  onDoubleClick={() => addFieldToSection(rf.field)}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData('text/plain', rf.field);
                    e.dataTransfer.effectAllowed = 'copy';
                  }}
                  className="pld-field-row"
                >
                  <span className="pld-field-label">{rf.label}</span>
                  <span className="pld-field-path">{rf.field}</span>
                  <span className="pld-field-type">{rf.type}</span>
                </div>
              ))}
              {visibleFields.length === 0 && (
                <div className="pld-fields-empty">
                  {fieldGroups.length === 0 ? 'Loading...' : 'All fields in use'}
                </div>
              )}
            </div>
          </div>

          {/* Models — bottom, compact */}
          <div className="pld-models-section">
            <div className="pld-panel-header">
              <span>Models</span>
            </div>
            <div className="pld-models-scroll">
              {/* Base model first */}
              <div
                onClick={() => fetchModelFields(model)}
                className={`pld-model-row pld-model-row--base${activeModel === model ? ' pld-model-row--active' : ''}`}
              >
                <span>{model}</span>
                <span className="pld-model-base-tag">base</span>
              </div>
              <div className="pld-models-divider" />
              {allModelNames.filter(m => m !== model).map(m => (
                <div key={m}
                  onClick={() => fetchModelFields(m)}
                  className={`pld-model-row${activeModel === m ? ' pld-model-row--active' : ''}`}
                >
                  <span>{m}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PrintLayoutDesigner;

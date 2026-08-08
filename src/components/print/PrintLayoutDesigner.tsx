/**
 * PrintLayoutDesigner — visual report layout editor (WC2 pattern).
 *
 * Three-panel design:
 *   Left:   Model/group selector (top) + Available fields (bottom)
 *   Middle: Used fields grouped by zone (Header / Body-List / Footer)
 *   Right:  Live preview — auto-arranged by Claude/Alice
 *
 * Interactions:
 *   - Double-click available field → add to default zone (Body/List)
 *   - Drag from available → drop on a zone in middle panel
 *   - Drag within middle panel to reorder
 *   - × to remove a field
 *   - Click zone badge to cycle H → L → F
 *
 * Entry: shift-click a report row in ReportsDialog, or Design button.
 *
 * LastChecked: 2026-08-07 | WhereUsed: ReportsDialog | WhoCreated: Bill+Claude
 */
import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react';
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

type Zone = 'header' | 'body' | 'list' | 'total' | 'footer';

interface UsedField {
  field: string;
  label: string;
  zone: Zone;
  format?: string;
}

const ZONE_LABELS: Record<Zone, string> = {
  header: 'Header', body: 'Body', list: 'List', total: 'Total', footer: 'Footer',
};
const ZONE_COLORS: Record<Zone, string> = {
  header: '#0e639c', body: '#2e7d32', list: '#c05621', total: '#7b1fa2', footer: '#555',
};
const ZONES: Zone[] = ['header', 'body', 'list', 'total', 'footer'];

// ---------------------------------------------------------------------------
// Auto-arrange: convert UsedField[] → PrintLayout
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
  const last = field.includes('.') ? field.split('.').pop()! : field;
  return last
    .replace(/^dt_/, 'Date ')
    .replace(/^ida$/, 'ID')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

function formatTypeLabel(field: string): string {
  const fmt = guessFormat(field);
  return fmt === 'text' ? 'string' : fmt;
}

function arrangeLayout(used: UsedField[], model: string, title: string, paper: string): PrintLayout {
  const headerFields = used.filter(f => f.zone === 'header');
  const bodyFields = used.filter(f => f.zone === 'body');
  const listFields = used.filter(f => f.zone === 'list');
  const totalFields = used.filter(f => f.zone === 'total');
  const footerFields = used.filter(f => f.zone === 'footer');

  const sections: any[] = [];

  // Company header (always present)
  sections.push({ type: 'company_header', logo: true, show_address: true, show_contact: true });

  // Header — meta fields (invoice #, date, terms, etc.)
  if (headerFields.length > 0) {
    sections.push({
      type: 'meta_row',
      fields: headerFields.map(f => ({
        field: f.field, label: f.label,
        format: f.format || guessFormat(f.field),
        align: guessAlign(f.format || guessFormat(f.field)),
      })),
    });
  }

  // Body — detail fields (attention, company, address, phone — non-repeating)
  if (bodyFields.length > 0) {
    sections.push({
      type: 'detail_fields',
      fields: bodyFields.map(f => ({
        field: f.field, label: f.label,
        format: f.format || guessFormat(f.field),
      })),
    });
  }

  // List — repeating line items or data table rows
  if (listFields.length > 0) {
    const hasLineItemFields = listFields.some(f =>
      /^item\.|^quantity\.|^price\.|^cost\./.test(f.field)
    );

    sections.push({
      type: hasLineItemFields ? 'line_items' : 'data_table',
      columns: listFields.map(f => {
        const fmt = f.format || guessFormat(f.field);
        return {
          field: f.field, label: f.label, format: fmt,
          align: guessAlign(fmt), width: guessWidth(f.field, fmt),
        };
      }),
      ...(hasLineItemFields
        ? { show_footer_totals: listFields.some(f => guessFormat(f.field) === 'currency') }
        : { grand_totals: listFields.some(f => guessFormat(f.field) === 'currency') }
      ),
    });
  }

  // Total — grand totals (subtotal, tax, shipping, total, balance)
  if (totalFields.length > 0) {
    sections.push({
      type: 'totals',
      rows: totalFields.map(f => ({
        field: f.field, label: f.label,
        format: f.format || guessFormat(f.field),
        bold: /total$|balance/.test(f.field),
      })),
    });
  }

  // Footer — page footer
  if (footerFields.length > 0) {
    sections.push({
      type: 'footer',
      fields: footerFields.map(f => ({
        field: f.field, label: f.label,
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
    if (section.type === 'detail_fields' && 'fields' in section) {
      for (const f of (section as any).fields || []) {
        used.push({ field: f.field, label: f.label || autoLabel(f.field), zone: 'body', format: f.format });
      }
    }
    if (section.type === 'totals' && 'rows' in section) {
      for (const f of (section as any).rows || []) {
        used.push({ field: f.field, label: f.label || autoLabel(f.field), zone: 'total', format: f.format });
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
    if (k.startsWith('_') || k === 'lines') continue;
    const path = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      keys.push(...flattenKeys(v, path));
    } else {
      keys.push(path);
    }
  }
  return keys;
}

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
// Group fields by prefix for the model/group selector
// ---------------------------------------------------------------------------

function groupFields(fields: string[]): Record<string, string[]> {
  const groups: Record<string, string[]> = {};
  for (const f of fields) {
    const dot = f.indexOf('.');
    const group = dot > 0 ? f.substring(0, dot) : '(record)';
    if (!groups[group]) groups[group] = [];
    groups[group].push(f);
  }
  return groups;
}

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
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const [dropTarget, setDropTarget] = useState<{ zone: Zone; idx: number } | null>(null);
  const previewTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Build available fields from sample data + common fields
  const allFields = useMemo(() => {
    const fromData = sampleData ? flattenKeys(sampleData) : [];
    const combined = new Set([...COMMON_FIELDS, ...fromData]);
    return [...combined].sort();
  }, [sampleData]);

  const groups = useMemo(() => groupFields(allFields), [allFields]);
  const groupNames = useMemo(() => Object.keys(groups).sort((a, b) => {
    if (a === '(record)') return -1;
    if (b === '(record)') return 1;
    return a.localeCompare(b);
  }), [groups]);

  // Auto-select first group
  useEffect(() => {
    if (!selectedGroup && groupNames.length > 0) setSelectedGroup(groupNames[0]);
  }, [groupNames, selectedGroup]);

  const usedFieldPaths = new Set(used.map(f => f.field));
  const visibleFields = selectedGroup
    ? (groups[selectedGroup] || []).filter(f => !usedFieldPaths.has(f))
    : allFields.filter(f => !usedFieldPaths.has(f));

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

  // --- Drag reorder within used fields ---
  const handleDragStart = useCallback((idx: number) => {
    setDragIdx(idx);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, zone: Zone, zoneIdx: number) => {
    e.preventDefault();
    setDropTarget({ zone, idx: zoneIdx });
  }, []);

  const handleDrop = useCallback((e: React.DragEvent, targetZone: Zone, targetZoneIdx: number) => {
    e.preventDefault();
    if (dragIdx === null) return;

    setUsed(prev => {
      const item = prev[dragIdx];
      if (!item) return prev;

      // Remove from old position
      const without = prev.filter((_, i) => i !== dragIdx);

      // Change zone if needed
      const updated = { ...item, zone: targetZone };

      // Find insertion point: get items in target zone, insert at targetZoneIdx
      const zoneItems = without.filter(f => f.zone === targetZone);
      const otherItems = without.filter(f => f.zone !== targetZone);
      const insertAt = Math.min(targetZoneIdx, zoneItems.length);
      zoneItems.splice(insertAt, 0, updated);

      // Reconstruct in zone order
      const result: UsedField[] = [];
      for (const z of ZONES) {
        if (z === targetZone) result.push(...zoneItems);
        else result.push(...otherItems.filter(f => f.zone === z));
      }
      return result;
    });
    setDirty(true);
    setDragIdx(null);
    setDropTarget(null);
  }, [dragIdx]);

  const handleDragEnd = useCallback(() => {
    setDragIdx(null);
    setDropTarget(null);
  }, []);

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
  const panelHeader = (label: string, count?: number): React.CSSProperties => ({
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
          <span style={{ fontWeight: 700, fontSize, color: t.accent }}>Design</span>
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

        {/* === LEFT PANEL: Groups + Available Fields === */}
        <div style={{
          flex: '0 0 220px', display: 'flex', flexDirection: 'column',
          background: t.bg, borderRight: `1px solid ${t.border}`,
        }}>
          {/* Group / model selector */}
          <div style={{ flex: '0 0 auto', borderBottom: `2px solid ${t.border}` }}>
            <div style={panelHeader(`Groups`)}>
              <span>Models</span>
              <span style={{ fontSize: fontSize - 3, color: t.textDim, fontWeight: 400, textTransform: 'none' }}>
                {groupNames.length}
              </span>
            </div>
            <div style={{ maxHeight: 140, overflowY: 'auto' }}>
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
                    transition: 'background 0.1s',
                  }}
                  onMouseEnter={(e) => {
                    if (selectedGroup !== g) (e.currentTarget as HTMLElement).style.background = t.surfaceAlt;
                  }}
                  onMouseLeave={(e) => {
                    if (selectedGroup !== g) (e.currentTarget as HTMLElement).style.background = 'transparent';
                  }}
                >
                  <span>{g}</span>
                  <span style={{ fontSize: fontSize - 3, color: t.textDim }}>
                    {(groups[g] || []).length}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Available fields from selected group */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <div style={panelHeader('Fields')}>
              <span>Fields</span>
              <span style={{ fontSize: fontSize - 3, color: t.textDim, fontWeight: 400, textTransform: 'none' }}>
                dbl-click to add
              </span>
            </div>
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {visibleFields.map(field => {
                const shortName = field.includes('.') ? field.split('.').pop()! : field;
                const typeLabel = formatTypeLabel(field);
                return (
                  <div key={field}
                    onDoubleClick={() => addField(field, 'body')}
                    draggable
                    onDragStart={(e) => {
                      e.dataTransfer.setData('text/plain', field);
                      e.dataTransfer.effectAllowed = 'copy';
                    }}
                    style={{
                      padding: '3px 10px', cursor: 'pointer', fontSize: fontSize - 2,
                      display: 'flex', alignItems: 'center', gap: 6,
                      borderBottom: `1px solid ${t.borderLight}`,
                      background: 'transparent',
                      transition: 'background 0.1s',
                    }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = t.surfaceAlt; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                  >
                    <span style={{ flex: 1, color: t.text }}>{shortName}</span>
                    <span style={{
                      fontSize: fontSize - 3, color: t.textDim, fontStyle: 'italic',
                      minWidth: 44, textAlign: 'right',
                    }}>{typeLabel}</span>
                  </div>
                );
              })}
              {visibleFields.length === 0 && (
                <div style={{ padding: '12px 10px', fontSize: fontSize - 2, color: t.textDim, textAlign: 'center' }}>
                  {selectedGroup ? 'All fields in use' : 'Select a group'}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* === MIDDLE PANEL: Used fields by zone === */}
        <div style={{
          flex: '0 0 280px', display: 'flex', flexDirection: 'column',
          background: t.bg, borderRight: `1px solid ${t.border}`,
        }}>
          <div style={panelHeader('Used')}>
            <span>Used ({used.length})</span>
          </div>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {ZONES.map(zone => {
              const zoneFields = used.map((f, i) => ({ ...f, globalIdx: i })).filter(f => f.zone === zone);
              const zoneColor = ZONE_COLORS[zone];
              return (
                <div key={zone}
                  onDragOver={(e) => {
                    e.preventDefault();
                    // Allow drop from available fields
                    if (dragIdx === null) setDropTarget({ zone, idx: zoneFields.length });
                  }}
                  onDrop={(e) => {
                    e.preventDefault();
                    const fieldName = e.dataTransfer.getData('text/plain');
                    if (fieldName && !usedFieldPaths.has(fieldName) && dragIdx === null) {
                      addField(fieldName, zone);
                    }
                  }}
                >
                  {/* Zone header */}
                  <div style={{
                    padding: '5px 10px', fontSize: fontSize - 2, fontWeight: 700,
                    color: zoneColor, textTransform: 'uppercase',
                    background: t.surfaceAlt, borderBottom: `1px solid ${t.borderLight}`,
                    borderTop: `2px solid ${zoneColor}`,
                    letterSpacing: '0.06em',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  }}>
                    <span>{ZONE_LABELS[zone]}</span>
                    <span style={{ fontWeight: 400, fontSize: fontSize - 3 }}>{zoneFields.length}</span>
                  </div>

                  {/* Zone fields */}
                  {zoneFields.map((f, zoneIdx) => {
                    const isDropHere = dropTarget?.zone === zone && dropTarget?.idx === zoneIdx;
                    return (
                      <div key={f.field + f.globalIdx}
                        draggable
                        onDragStart={() => handleDragStart(f.globalIdx)}
                        onDragEnd={handleDragEnd}
                        onDragOver={(e) => handleDragOver(e, zone, zoneIdx)}
                        onDrop={(e) => handleDrop(e, zone, zoneIdx)}
                        style={{
                          padding: '3px 6px', cursor: 'grab', fontSize: fontSize - 2,
                          display: 'flex', alignItems: 'center', gap: 4,
                          borderBottom: `1px solid ${t.borderLight}`,
                          borderLeft: `3px solid ${zoneColor}`,
                          borderTop: isDropHere ? `2px solid ${t.accent}` : '2px solid transparent',
                          background: dragIdx === f.globalIdx ? t.surfaceAlt : 'transparent',
                          opacity: dragIdx === f.globalIdx ? 0.5 : 1,
                          transition: 'background 0.1s',
                        }}
                        onMouseEnter={(e) => {
                          if (dragIdx !== f.globalIdx)
                            (e.currentTarget as HTMLElement).style.background = t.surfaceAlt;
                        }}
                        onMouseLeave={(e) => {
                          if (dragIdx !== f.globalIdx)
                            (e.currentTarget as HTMLElement).style.background = 'transparent';
                        }}
                      >
                        {/* Drag grip */}
                        <span style={{ color: t.textDim, fontSize: fontSize - 2, userSelect: 'none', cursor: 'grab' }}>⋮⋮</span>

                        {/* Editable label */}
                        <input value={f.label}
                          onChange={(e) => editLabel(f.globalIdx, e.target.value)}
                          onClick={(e) => e.stopPropagation()}
                          style={{
                            flex: 1, background: 'transparent', color: t.text,
                            border: 'none', borderBottom: `1px solid ${t.borderLight}`,
                            fontSize: fontSize - 2, padding: '1px 2px', outline: 'none',
                            minWidth: 40,
                          }} />

                        {/* Field path (dim) */}
                        <span style={{ fontFamily: 'monospace', color: t.textDim, fontSize: fontSize - 4 }}>
                          {f.field}
                        </span>

                        {/* Zone cycle badge */}
                        <span onClick={(e) => {
                          e.stopPropagation();
                          const nextZone = ZONES[(ZONES.indexOf(zone) + 1) % ZONES.length];
                          changeZone(f.globalIdx, nextZone);
                        }} style={{
                          padding: '1px 4px', borderRadius: 3, fontSize: fontSize - 4,
                          fontWeight: 700, background: zoneColor, color: '#fff',
                          cursor: 'pointer', userSelect: 'none',
                        }} title={`Move to ${ZONE_LABELS[ZONES[(ZONES.indexOf(zone) + 1) % ZONES.length]]}`}>
                          {zone.charAt(0).toUpperCase()}
                        </span>

                        {/* Remove */}
                        <span onClick={(e) => { e.stopPropagation(); removeField(f.globalIdx); }}
                          style={{ color: t.textDim, cursor: 'pointer', fontSize: fontSize - 1, userSelect: 'none', lineHeight: 1 }}
                          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = '#e55'; }}
                          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = t.textDim; }}
                        >&times;</span>
                      </div>
                    );
                  })}

                  {/* Empty zone drop target */}
                  {zoneFields.length === 0 && (
                    <div
                      onDragOver={(e) => { e.preventDefault(); setDropTarget({ zone, idx: 0 }); }}
                      onDrop={(e) => {
                        e.preventDefault();
                        const fieldName = e.dataTransfer.getData('text/plain');
                        if (fieldName && !usedFieldPaths.has(fieldName) && dragIdx === null) {
                          addField(fieldName, zone);
                        } else if (dragIdx !== null) {
                          handleDrop(e, zone, 0);
                        }
                      }}
                      style={{
                        padding: '10px', fontSize: fontSize - 3, color: t.textDim,
                        textAlign: 'center', fontStyle: 'italic',
                        borderBottom: `1px solid ${t.borderLight}`,
                        borderLeft: `3px solid ${zoneColor}`,
                        background: dropTarget?.zone === zone ? `${zoneColor}11` : 'transparent',
                        transition: 'background 0.15s',
                      }}
                    >
                      Double-click or drag fields here
                    </div>
                  )}

                  {/* Bottom drop target for zone */}
                  {zoneFields.length > 0 && (
                    <div
                      onDragOver={(e) => handleDragOver(e, zone, zoneFields.length)}
                      onDrop={(e) => handleDrop(e, zone, zoneFields.length)}
                      style={{
                        height: dropTarget?.zone === zone && dropTarget?.idx === zoneFields.length ? 4 : 2,
                        background: dropTarget?.zone === zone && dropTarget?.idx === zoneFields.length
                          ? t.accent : 'transparent',
                        transition: 'height 0.1s, background 0.1s',
                      }}
                    />
                  )}
                </div>
              );
            })}
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

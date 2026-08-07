/**
 * PrintLayoutDesigner — visual editor for PrintLayout JSON.
 *
 * Renders section cards on the left, live preview on the right.
 * Drag sections to reorder, expand to edit fields, save to Report.config.form.
 *
 * Entry: shift-click a report row in ReportsDialog.
 *
 * LastChecked: 2026-08-07 | WhereUsed: ReportsDialog | WhoCreated: Claude
 */
import React, { useState, useCallback, useEffect, useRef } from 'react';
import type { PrintLayout, PrintLayoutSection } from './printLayoutTypes';
import { generatePrintHtml, PRINT_CSS } from './UniversalPrint';
import SectionCard from './SectionCard';
import SectionTypePicker from './SectionTypePicker';
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

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const PrintLayoutDesigner: React.FC<PrintLayoutDesignerProps> = ({
  report, model, layout: initialLayout,
  theme: t, fontSize, companyInfo, sampleData,
  onSave, onClose,
}) => {
  const [layout, setLayout] = useState<PrintLayout>(() =>
    JSON.parse(JSON.stringify(initialLayout))
  );
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const [previewHtml, setPreviewHtml] = useState('');
  const previewTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Mark dirty on any layout change
  const updateLayout = useCallback((next: PrintLayout) => {
    setLayout(next);
    setDirty(true);
  }, []);

  // --- Section operations ---
  const updateSection = useCallback((idx: number, section: PrintLayoutSection) => {
    updateLayout({
      ...layout,
      sections: layout.sections.map((s, i) => i === idx ? section : s),
    });
  }, [layout, updateLayout]);

  const removeSection = useCallback((idx: number) => {
    updateLayout({
      ...layout,
      sections: layout.sections.filter((_, i) => i !== idx),
    });
  }, [layout, updateLayout]);

  const addSection = useCallback((section: PrintLayoutSection) => {
    updateLayout({
      ...layout,
      sections: [...layout.sections, section],
    });
  }, [layout, updateLayout]);

  // --- Section drag reorder ---
  const handleDragOver = useCallback((e: React.DragEvent, targetIdx: number) => {
    e.preventDefault();
    if (dragIdx === null || dragIdx === targetIdx) return;
    const sections = [...layout.sections];
    const [moved] = sections.splice(dragIdx, 1);
    sections.splice(targetIdx, 0, moved);
    setLayout(prev => ({ ...prev, sections }));
    setDirty(true);
    setDragIdx(targetIdx);
  }, [dragIdx, layout.sections]);

  // --- Debounced preview ---
  useEffect(() => {
    if (previewTimer.current) clearTimeout(previewTimer.current);
    previewTimer.current = setTimeout(() => {
      try {
        const data = sampleData || { ida: 'SAMPLE-001', status: 'draft', company: 'Sample Co.' };
        const html = generatePrintHtml(data, companyInfo, layout);
        setPreviewHtml(html);
      } catch (e) {
        console.error('[PrintLayoutDesigner] Preview generation failed:', e);
      }
    }, 300);
    return () => { if (previewTimer.current) clearTimeout(previewTimer.current); };
  }, [layout, sampleData, companyInfo]);

  // --- Save ---
  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      onSave(layout);
      setDirty(false);
      setStatusMsg('Saved');
      setTimeout(() => setStatusMsg(''), 2000);
    } catch (e: any) {
      setStatusMsg(`Save failed: ${e?.message || 'unknown'}`);
    } finally {
      setSaving(false);
    }
  }, [layout, onSave]);

  // --- Layout-level properties ---
  const updateProp = useCallback((key: string, value: any) => {
    updateLayout({ ...layout, [key]: value });
  }, [layout, updateLayout]);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div data-wc="print-layout-designer" style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      borderLeft: `1px solid ${t.border}`,
    }}>
      {/* Toolbar */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '6px 12px', borderBottom: `1px solid ${t.border}`,
        background: t.surface,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontWeight: 700, fontSize: fontSize, color: t.accent }}>
            Design
          </span>
          <span style={{ fontSize: fontSize - 2, color: t.textMuted }}>
            {report.name}
          </span>
          {dirty && <span style={{ fontSize: fontSize - 3, color: t.accentGold, fontWeight: 700 }}>UNSAVED</span>}
          {statusMsg && <span style={{ fontSize: fontSize - 2, color: t.accentGreen }}>{statusMsg}</span>}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <SectionTypePicker onAdd={addSection} theme={t} fontSize={fontSize} />
          <button
            onClick={handleSave}
            disabled={saving || !dirty}
            style={{
              padding: '4px 12px', borderRadius: 4, cursor: dirty ? 'pointer' : 'default',
              fontSize: fontSize - 1, fontWeight: 600,
              background: dirty ? t.accent : 'none',
              border: dirty ? 'none' : `1px solid ${t.border}`,
              color: dirty ? '#fff' : t.textMuted,
              opacity: saving ? 0.6 : 1,
            }}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
          <button
            onClick={onClose}
            style={{
              padding: '4px 10px', borderRadius: 4, cursor: 'pointer',
              fontSize: fontSize - 1, fontWeight: 600,
              background: 'none', border: `1px solid ${t.border}`, color: t.text,
            }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = t.surfaceAlt; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'none'; }}
          >
            Close
          </button>
        </div>
      </div>

      {/* Body: editor + preview */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* Left: section editor */}
        <div style={{
          flex: '0 0 55%', overflowY: 'auto', padding: 8,
          background: t.bg,
        }}>
          {/* Layout-level props */}
          <div style={{
            display: 'flex', gap: 8, alignItems: 'center',
            padding: '4px 8px', marginBottom: 6,
            border: `1px solid ${t.borderLight}`, borderRadius: 4,
            fontSize: fontSize - 2, color: t.textMuted,
          }}>
            <label>Title: <input value={layout.title || ''} onChange={(e) => updateProp('title', e.target.value || undefined)}
              style={{ background: t.bg, color: t.text, border: `1px solid ${t.borderLight}`, borderRadius: 3, padding: '2px 4px', fontSize: fontSize - 2, width: 100 }} /></label>
            <label>Paper:
              <span onClick={() => updateProp('paper', layout.paper === 'a4' ? 'letter' : 'a4')}
                style={{ cursor: 'pointer', fontWeight: 700, color: t.accent, marginLeft: 4, userSelect: 'none' }}>
                {layout.paper || 'letter'}
              </span>
            </label>
            <label>Model: <span style={{ fontFamily: 'monospace', color: t.text }}>{layout.model || model}</span></label>
          </div>

          {/* Section cards */}
          {layout.sections.map((section, idx) => (
            <SectionCard
              key={`${section.type}-${idx}`}
              section={section}
              index={idx}
              onChange={(s) => updateSection(idx, s)}
              onRemove={() => removeSection(idx)}
              draggable
              onDragStart={() => setDragIdx(idx)}
              onDragOver={(e) => handleDragOver(e, idx)}
              onDragEnd={() => setDragIdx(null)}
              isDragging={dragIdx === idx}
              theme={t}
              fontSize={fontSize}
            />
          ))}

          {layout.sections.length === 0 && (
            <div style={{
              padding: 24, textAlign: 'center',
              color: t.textDim, fontSize: fontSize - 1,
            }}>
              No sections. Click "+ Section" to add one.
            </div>
          )}
        </div>

        {/* Right: live preview */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderLeft: `1px solid ${t.border}` }}>
          <div style={{
            padding: '4px 12px', borderBottom: `1px solid ${t.borderLight}`,
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

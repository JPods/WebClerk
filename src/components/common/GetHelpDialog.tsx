/**
 * GetHelpDialog — paste any UI element to get contextual help.
 *
 * User workflow:
 *   1. Right-click any element → Inspect → Copy Element
 *   2. Press Cmd+? (or click ? Help → Get Help)
 *   3. Paste the element HTML
 *   4. Alice + WCHQ provide contextual help
 *
 * The data-wc attribute on the pasted element identifies:
 *   - Which component (db-model-picker, db-search, db-list-pane, etc.)
 *   - Which model context (from data-wc-model if present)
 *   - Which field (from data-wc-field if present)
 *
 * Alice looks up:
 *   - AliceObservation records for that context
 *   - Training documents mentioning that component
 *   - Field-level help from field_access Settings
 *   - WCHQ knowledge base matches
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';

interface GetHelpDialogProps {
  open: boolean;
  onClose: () => void;
}

// Map data-wc IDs to human descriptions + help topics
const WC_HELP_MAP: Record<string, { label: string; topic: string; training?: string }> = {
  'databrowser': { label: 'DataBrowser', topic: 'The main data editing interface. Browse, search, and edit records for any model.', training: 'WC Training: Administration Skills' },
  'db-header': { label: 'DataBrowser Header', topic: 'Model selector, search, layout controls, and display settings.' },
  'db-model-picker': { label: 'Model Picker', topic: 'Click to switch models. Type to filter (begins with). Cmd+Shift+M shortcut.', training: 'WC Training: Data Setup Checklist' },
  'db-search': { label: 'Search', topic: 'Search across all text fields. Results update as you type (400ms debounce). Alice tracks your searches to suggest presets.' },
  'db-layouts-label': { label: 'Saved Layouts', topic: 'Named field configurations. Click to load, Shift-click to delete. alice_guess and alphabetical are system layouts that cannot be overwritten.' },
  'db-font-size': { label: 'Font Size', topic: 'Cycles S → M → L. Saved to your contact record so it follows you across browsers.' },
  'db-theme-toggle': { label: 'Theme Toggle', topic: 'Dark/Light mode. Saved to your contact record.' },
  'db-list-pane': { label: 'List Pane', topic: 'Shows records for the selected model. Click a row to see details. Shift-click for alternate actions.' },
  'db-list-toolbar': { label: 'List Toolbar', topic: 'List Order: configure columns. Sel All/Clear: select rows. Show/Omit: filter to selected. Arrows: pagination.' },
  'db-detail-pane': { label: 'Detail Pane', topic: 'Edit the selected record. Fields are ordered by the active layout. JSON fields show as expandable editors.' },
  'db-detail-toolbar': { label: 'Detail Toolbar', topic: '+ New: create blank record. Form Order: configure detail fields. Save/Delete: persist changes.' },
  'db-layout-selector': { label: 'Layout Selector', topic: 'Choose from saved layouts. alice_guess orders fields by importance. alphabetical sorts A-Z. Save your own layouts.' },
  'alice-hint-bar': { label: 'Alice Hints', topic: 'Coaching suggestions from Alice (green), WCHQ best practices (blue), and power user tips (gold). Dismiss with ×.' },
};

function parseDataWc(html: string): { wcId: string; wcModel?: string; wcField?: string; rawAttrs: Record<string, string> } {
  const result: { wcId: string; wcModel?: string; wcField?: string; rawAttrs: Record<string, string> } = { wcId: '', rawAttrs: {} };

  // Extract data-wc attribute
  const wcMatch = html.match(/data-wc="([^"]+)"/);
  if (wcMatch) result.wcId = wcMatch[1];

  // Extract data-wc-model
  const modelMatch = html.match(/data-wc-model="([^"]+)"/);
  if (modelMatch) result.wcModel = modelMatch[1];

  // Extract data-wc-field
  const fieldMatch = html.match(/data-wc-field="([^"]+)"/);
  if (fieldMatch) result.wcField = fieldMatch[1];

  // Extract all data- attributes for context
  const allAttrs = html.matchAll(/data-([a-z-]+)="([^"]+)"/g);
  for (const m of allAttrs) {
    result.rawAttrs[`data-${m[1]}`] = m[2];
  }

  // If no data-wc, try to extract useful info from class, id, or text content
  if (!result.wcId) {
    const idMatch = html.match(/\bid="([^"]+)"/);
    if (idMatch) result.wcId = idMatch[1];
    const classMatch = html.match(/\bclass="([^"]+)"/);
    if (classMatch) result.rawAttrs['class'] = classMatch[1];
  }

  return result;
}

export default function GetHelpDialog({ open, onClose }: GetHelpDialogProps) {
  const [pastedHtml, setPastedHtml] = useState('');
  const [helpResult, setHelpResult] = useState<{
    label: string;
    topic: string;
    training?: string;
    field_help?: string;
    alice_notes?: string[];
    wchq_notes?: string[];
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (open) {
      setPastedHtml('');
      setHelpResult(null);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [open]);

  const analyzeElement = useCallback(async (html: string) => {
    if (!html.trim()) return;
    setLoading(true);

    const parsed = parseDataWc(html);
    const helpInfo = WC_HELP_MAP[parsed.wcId] || null;

    const result: typeof helpResult = {
      label: helpInfo?.label || parsed.wcId || 'Unknown Element',
      topic: helpInfo?.topic || 'No specific help available for this element. Try copying an element with a data-wc attribute.',
      training: helpInfo?.training,
      alice_notes: [],
      wchq_notes: [],
    };

    // Look up field-level help if we have model + field context
    if (parsed.wcField && parsed.wcModel) {
      try {
        const { getRecords } = await import('@/api/wcapi');
        const faRes = await getRecords('setting', { parent_model: parsed.wcModel, purpose: 'field_access' }) as any;
        const faRec = (faRes?.results || [])[0];
        const behaviors = faRec?.data?.field_behaviors || {};
        const fieldBehavior = behaviors[parsed.wcField];
        if (fieldBehavior) {
          result.field_help = `Field: ${parsed.wcField} — Type: ${fieldBehavior.type || 'text'}${fieldBehavior.help ? ` — ${fieldBehavior.help}` : ''}`;
        }
      } catch { /* silent */ }
    }

    // Look up Alice observations for this context
    try {
      const { getRecords } = await import('@/api/wcapi');
      const obsRes = await getRecords('alice_observation', {
        model_name: parsed.wcModel || '',
        resolved: false,
        limit: 5,
      }) as any;
      const obs = obsRes?.results || [];
      result.alice_notes = obs.map((o: any) => o.message).filter(Boolean);
    } catch { /* silent */ }

    // Look up training documents
    if (result.training) {
      try {
        const { getRecords } = await import('@/api/wcapi');
        const docRes = await getRecords('document', { name: result.training, limit: 1 }) as any;
        const doc = (docRes?.results || [])[0];
        if (doc?.body) {
          // Show first 500 chars of training doc
          result.wchq_notes = [doc.body.slice(0, 500) + (doc.body.length > 500 ? '...' : '')];
        }
      } catch { /* silent */ }
    }

    setHelpResult(result);
    setLoading(false);
  }, []);

  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    const text = e.clipboardData.getData('text');
    setPastedHtml(text);
    analyzeElement(text);
  }, [analyzeElement]);

  if (!open) return null;

  return (
    <div data-wc="get-help-dialog" style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 9999,
    }} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{
        background: '#1e1e1e', border: '1px solid #3c3c3c', borderRadius: 8,
        width: 600, maxHeight: '80vh', overflow: 'auto', padding: 20,
        color: '#d4d4d4', fontSize: 13,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2 style={{ margin: 0, fontSize: 16, color: '#9cdcfe' }}>Get Help</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#888', fontSize: 18, cursor: 'pointer' }}>×</button>
        </div>

        <p style={{ fontSize: 11, color: '#888', marginBottom: 12 }}>
          Right-click any element → Inspect → Copy Element → Paste here. Alice and WCHQ will provide contextual help.
        </p>

        <textarea
          ref={inputRef}
          data-wc="help-paste-area"
          value={pastedHtml}
          onChange={(e) => { setPastedHtml(e.target.value); }}
          onPaste={handlePaste}
          placeholder="Paste copied element here..."
          style={{
            width: '100%', height: 80, background: '#252526', border: '1px solid #3c3c3c',
            borderRadius: 4, padding: 8, color: '#d4d4d4', fontSize: 11,
            fontFamily: 'monospace', resize: 'vertical',
          }}
        />

        {pastedHtml && !helpResult && !loading && (
          <button onClick={() => analyzeElement(pastedHtml)}
            style={{ marginTop: 8, padding: '6px 16px', background: '#0d6efd', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>
            Analyze
          </button>
        )}

        {loading && <div style={{ marginTop: 12, color: '#888' }}>Looking up help...</div>}

        {helpResult && (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#9cdcfe', marginBottom: 8 }}>
              {helpResult.label}
            </div>
            <div style={{ fontSize: 12, lineHeight: 1.6, marginBottom: 12 }}>
              {helpResult.topic}
            </div>

            {helpResult.field_help && (
              <div style={{ padding: '6px 10px', background: '#1a2a3e', borderRadius: 4, fontSize: 11, marginBottom: 8 }}>
                <span style={{ color: '#60a5fa', fontWeight: 600 }}>Field Info:</span> {helpResult.field_help}
              </div>
            )}

            {helpResult.alice_notes && helpResult.alice_notes.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#4ade80', textTransform: 'uppercase', marginBottom: 4 }}>Alice Notes</div>
                {helpResult.alice_notes.map((note, i) => (
                  <div key={i} style={{ padding: '4px 10px', background: '#1a3a2e', borderRadius: 4, fontSize: 11, marginBottom: 3 }}>
                    {note}
                  </div>
                ))}
              </div>
            )}

            {helpResult.training && (
              <div style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#60a5fa', textTransform: 'uppercase', marginBottom: 4 }}>Training Available</div>
                <div style={{ padding: '4px 10px', background: '#1a2a3e', borderRadius: 4, fontSize: 11 }}>
                  {helpResult.training}
                </div>
              </div>
            )}

            {helpResult.wchq_notes && helpResult.wchq_notes.length > 0 && (
              <div>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#60a5fa', textTransform: 'uppercase', marginBottom: 4 }}>WCHQ Documentation</div>
                {helpResult.wchq_notes.map((note, i) => (
                  <div key={i} style={{ padding: '6px 10px', background: '#1a2a3e', borderRadius: 4, fontSize: 11, lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                    {note}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

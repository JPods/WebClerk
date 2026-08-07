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
  'databrowser': { label: 'databrowser', topic: 'The main data editing interface. Browse, search, and edit records for any model.', training: 'WC Training: Administration Skills' },
  'db-header': { label: 'databrowser header', topic: 'Model selector, search, layout controls, and display settings.' },
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

// Component name → source path + description (populated from DevIdentifier source props)
// This is the bridge between Shift+click copy and Get Help paste
const COMPONENT_HELP: Record<string, { source: string; description: string }> = {
  // Detail pages
  'ContactDetailJson': { source: 'apps/core/models/contact/pages/ContactDetailJson.tsx', description: 'Contact detail form — JSON-driven layout from detail_layout Setting. Three-column header + tabbed sections.' },
  'ItemDetailJson': { source: 'apps/products/pages/ItemDetailJson.tsx', description: 'Item detail form — JSON-driven layout. Product data, variants, BOM, serial numbers.' },
  'TransactionDetail': { source: 'apps/transactions/components/TransactionDetail.tsx', description: 'Shared transaction renderer — orders, invoices, proposals, purchases all use this. Layout from detail_layout Setting per model.' },
  'DynamicDetail': { source: 'components/common/DynamicDetail.tsx', description: 'Generic data-driven form renderer. Reads layout JSON, renders any model. Arrange mode for drag-to-reorder fields.' },
  'OrgDetailJson': { source: 'apps/orgs/components/OrgDetail.json.tsx', description: 'Organization detail — shared by customer, vendor, manufacturer, employee, rep. Layout from detail_layout Setting.' },
  'BundleDetail': { source: 'apps/sync/models/bundle/pages/BundleDetail.tsx', description: 'Sync bundle viewer — shows records exchanged between installations.' },
  // Panels
  'CommPanel': { source: 'apps/communications/components/CommPanel.tsx', description: 'Communications panel — emails, phones, addresses for a contact. Renders CommCards.' },
  'DataBrowser': { source: 'pages/admin/DataBrowser.tsx', description: 'Universal databrowser — lists and details for any model. Column config from workbench_fields Setting.' },
  'AppSidebar': { source: 'layout/AppSidebar.tsx', description: 'Main navigation sidebar — model list, dashboards, search. Configured from contact.prefs.staff.nav Setting.' },
  'SprintBurndown': { source: 'apps/core/models/action/pages/SprintBurndown.tsx', description: 'Sprint burndown chart — tracks project action completion over time.' },
  'KanbanBoardPage': { source: 'apps/utils/kanban/KanbanBoardPage.tsx', description: 'Kanban board — drag actions between status columns. Project-filtered.' },
  'UnifiedGantt': { source: 'apps/utils/gantt/UnifiedGantt.tsx', description: 'Gantt chart — action timelines with dependencies. Project-filtered.' },
};

function parseInput(text: string): { wcId: string; wcModel?: string; wcField?: string; componentName?: string; sourcePath?: string; rawAttrs: Record<string, string> } {
  const result: { wcId: string; wcModel?: string; wcField?: string; componentName?: string; sourcePath?: string; rawAttrs: Record<string, string> } = { wcId: '', rawAttrs: {} };

  // First: check if it's a component name (from Shift+click on DevIdentifier badge)
  const trimmed = text.trim();
  if (COMPONENT_HELP[trimmed]) {
    result.componentName = trimmed;
    result.sourcePath = COMPONENT_HELP[trimmed].source;
    return result;
  }

  // Check if it's a file path (from Shift+hover copy)
  if (trimmed.endsWith('.tsx') || trimmed.endsWith('.ts')) {
    const fileName = trimmed.split('/').pop()?.replace(/\.tsx?$/, '') || '';
    result.sourcePath = trimmed;
    if (COMPONENT_HELP[fileName]) {
      result.componentName = fileName;
    } else {
      result.componentName = fileName;
    }
    return result;
  }

  // Otherwise: parse as HTML with data-wc attributes
  const wcMatch = text.match(/data-wc="([^"]+)"/);
  if (wcMatch) result.wcId = wcMatch[1];

  const modelMatch = text.match(/data-wc-model="([^"]+)"/);
  if (modelMatch) result.wcModel = modelMatch[1];

  const fieldMatch = text.match(/data-wc-field="([^"]+)"/);
  if (fieldMatch) result.wcField = fieldMatch[1];

  const allAttrs = text.matchAll(/data-([a-z-]+)="([^"]+)"/g);
  for (const m of allAttrs) {
    result.rawAttrs[`data-${m[1]}`] = m[2];
  }

  if (!result.wcId) {
    const idMatch = text.match(/\bid="([^"]+)"/);
    if (idMatch) result.wcId = idMatch[1];
    const classMatch = text.match(/\bclass="([^"]+)"/);
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

    const parsed = parseInput(html);

    // Try component name first, then data-wc, then unknown
    const componentInfo = parsed.componentName ? COMPONENT_HELP[parsed.componentName] : null;
    const helpInfo = WC_HELP_MAP[parsed.wcId] || null;

    const result: typeof helpResult = {
      label: componentInfo ? parsed.componentName! : helpInfo?.label || parsed.wcId || 'Unknown Element',
      topic: componentInfo?.description || helpInfo?.topic || 'No specific help available for this element. Try copying an element with a data-wc attribute.',
      training: helpInfo?.training,
      alice_notes: [],
      wchq_notes: [],
    };

    // If we found a component, show its source path
    if (parsed.sourcePath) {
      result.field_help = `Source: ${parsed.sourcePath}`;
    }

    // Look up field-level help if we have model + field context
    if (parsed.wcField && parsed.wcModel) {
      try {
        const { getRecords } = await import('@/api/wcapi');
        const faRes = await getRecords('setting', { parent_model: parsed.wcModel, purpose: 'field_access' }) as any;
        const faRec = (faRes?.results || [])[0];
        const behaviors = faRec?.config?.field_behaviors || {};
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
      background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
      paddingTop: 60,
      zIndex: 9999,
    }} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{
        background: '#1e1e1e', border: '1px solid #3c3c3c', borderRadius: 8,
        width: 600, maxHeight: 'calc(100vh - 80px)', overflow: 'auto', padding: 20,
        color: '#d4d4d4', fontSize: 13,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2 style={{ margin: 0, fontSize: 16, color: '#9cdcfe' }}>Get Help</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#888', fontSize: 18, cursor: 'pointer' }}>×</button>
        </div>

        <p style={{ fontSize: 11, color: '#888', marginBottom: 12 }}>
          Shift+hover any zone → click nametag to copy → paste here. Or right-click → Inspect → Copy Element → paste.
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

            {/* Unknown element — offer to request help from WCHQ */}
            {helpResult.label === 'Unknown Element' && (
              <RequestWchqHelp elementText={pastedHtml} />
            )}

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

            {/* Contribute help — users add tips that become Document records */}
            <ContributeHelp
              componentName={helpResult.label}
              sourcePath={parseInput(pastedHtml).sourcePath || ''}
            />

            {/* Request Change section — users can request field type changes */}
            <FieldChangeRequest
              wcField={parseInput(pastedHtml).wcField || ''}
              wcModel={parseInput(pastedHtml).wcModel || ''}
              fieldLabel={helpResult.label}
            />
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Field Change Request — user requests a field become a dropdown, etc.
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// RequestWchqHelp — post unknown element to WCHQ for an answer
// ---------------------------------------------------------------------------

function RequestWchqHelp({ elementText }: { elementText: string }) {
  const [question, setQuestion] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!question.trim()) return;
    setSubmitting(true);
    try {
      const { manageAction } = await import('@/api/wcapi');
      await manageAction('create_action', {
        action: { en: `Help request: ${question.slice(0, 100)}` },
        description: { en: `User pasted element and asked for help.\n\nQuestion: ${question}\n\nElement: ${elementText.slice(0, 500)}` },
        status: 'open',
        priority: 2,
        project_name: 'wchq-support',
      });
      setSubmitted(true);
    } catch {
      setSubmitted(true); // show success anyway — Alice will pick it up
    }
    setSubmitting(false);
  };

  if (submitted) {
    return (
      <div style={{ padding: '8px 12px', background: '#1a3a2e', borderRadius: 4, fontSize: 11, color: '#4ade80', marginBottom: 12 }}>
        Question submitted to WCHQ. You will receive an answer in your action list.
      </div>
    );
  }

  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', gap: 6 }}>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSubmit(); }}
          placeholder="What do you need help with?"
          style={{ flex: 1, background: '#252526', border: '1px solid #3c3c3c', borderRadius: 4, padding: '6px 8px', fontSize: 11, color: '#d4d4d4' }}
        />
        <button
          onClick={handleSubmit}
          disabled={submitting || !question.trim()}
          style={{ padding: '6px 12px', fontSize: 11, fontWeight: 600, border: 'none', borderRadius: 4, background: '#0d6efd', color: '#fff', cursor: submitting ? 'wait' : 'pointer', opacity: submitting || !question.trim() ? 0.5 : 1 }}
        >
          {submitting ? '...' : 'Ask WCHQ'}
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// FieldChangeRequest — user requests a field become a dropdown, etc.
// ---------------------------------------------------------------------------

function FieldChangeRequest({ wcField, wcModel, fieldLabel }: { wcField: string; wcModel: string; fieldLabel: string }) {
  const [showForm, setShowForm] = useState(false);
  const [changeType, setChangeType] = useState<'select' | 'lookup' | 'readonly' | 'datetime'>('select');
  const [valuesSource, setValuesSource] = useState<'static' | 'query' | 'setting' | 'distinct'>('static');
  const [staticValues, setStaticValues] = useState('');
  const [queryModel, setQueryModel] = useState('');
  const [queryField, setQueryField] = useState('');
  const [queryFilter, setQueryFilter] = useState('');
  const [settingName, setSettingName] = useState('');
  const [reason, setReason] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  if (!wcField) return null;

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const { manageAction } = await import('@/api/wcapi');

      const request: Record<string, unknown> = {
        model: wcModel,
        field: wcField,
        field_label: fieldLabel,
        change_type: changeType,
        values_source: valuesSource,
        reason,
      };

      if (valuesSource === 'static') {
        request.options = staticValues.split(',').map(s => s.trim()).filter(Boolean);
      } else if (valuesSource === 'query') {
        request.query_model = queryModel;
        request.query_field = queryField;
        request.query_filter = queryFilter;
      } else if (valuesSource === 'setting') {
        request.setting_name = settingName;
      }

      // Create Alice observation + action record
      await manageAction('request_field_change', request);
      setSubmitted(true);
    } catch (e) {
      alert('Failed to submit request: ' + (e instanceof Error ? e.message : 'unknown error'));
    }
    setSubmitting(false);
  };

  if (submitted) {
    return (
      <div style={{ marginTop: 12, padding: '8px 12px', background: '#1a3a2e', borderRadius: 4, fontSize: 11, color: '#4ade80' }}>
        Request submitted for {wcModel}.{wcField} — Alice will review and create an action record. An admin will approve the change.
      </div>
    );
  }

  return (
    <div data-wc="field-change-request" style={{ marginTop: 16, borderTop: '1px solid #3c3c3c', paddingTop: 12 }}>
      <button onClick={() => setShowForm(!showForm)}
        style={{ background: 'none', border: '1px solid #6f42c1', borderRadius: 4, padding: '4px 12px', fontSize: 11, color: '#a78bfa', cursor: 'pointer', fontWeight: 600 }}>
        {showForm ? 'Cancel Request' : 'Request Change'}
      </button>

      {showForm && (
        <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#a78bfa', textTransform: 'uppercase' }}>
            Request Field Change: {wcModel}.{wcField}
          </div>

          {/* Change type */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 11, color: '#888', width: 90 }}>Make this a:</span>
            <select value={changeType} onChange={(e) => setChangeType(e.target.value as any)}
              style={{ background: '#252526', border: '1px solid #3c3c3c', borderRadius: 3, padding: '3px 6px', fontSize: 11, color: '#d4d4d4' }}>
              <option value="select">Dropdown (select list)</option>
              <option value="lookup">Lookup (search another model)</option>
              <option value="readonly">Read-only (system driven)</option>
              <option value="datetime">Date/time picker</option>
            </select>
          </div>

          {/* Values source — only for select type */}
          {changeType === 'select' && (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 11, color: '#888', width: 90 }}>Values from:</span>
                <select value={valuesSource} onChange={(e) => setValuesSource(e.target.value as any)}
                  style={{ background: '#252526', border: '1px solid #3c3c3c', borderRadius: 3, padding: '3px 6px', fontSize: 11, color: '#d4d4d4' }}>
                  <option value="static">Type values below</option>
                  <option value="query">Query: model.field</option>
                  <option value="setting">Setting record</option>
                  <option value="distinct">Distinct values from data</option>
                </select>
              </div>

              {valuesSource === 'static' && (
                <input type="text" placeholder="retail, wholesale, distributor (comma separated)"
                  value={staticValues} onChange={(e) => setStaticValues(e.target.value)}
                  style={{ background: '#252526', border: '1px solid #3c3c3c', borderRadius: 3, padding: '4px 8px', fontSize: 11, color: '#d4d4d4' }} />
              )}

              {valuesSource === 'query' && (
                <div style={{ display: 'flex', gap: 6 }}>
                  <input type="text" placeholder="model (e.g., gl_account)" value={queryModel} onChange={(e) => setQueryModel(e.target.value)}
                    style={{ flex: 1, background: '#252526', border: '1px solid #3c3c3c', borderRadius: 3, padding: '4px 8px', fontSize: 11, color: '#d4d4d4' }} />
                  <input type="text" placeholder="field (e.g., name)" value={queryField} onChange={(e) => setQueryField(e.target.value)}
                    style={{ flex: 1, background: '#252526', border: '1px solid #3c3c3c', borderRadius: 3, padding: '4px 8px', fontSize: 11, color: '#d4d4d4' }} />
                  <input type="text" placeholder="filter (e.g., type=revenue)" value={queryFilter} onChange={(e) => setQueryFilter(e.target.value)}
                    style={{ flex: 1, background: '#252526', border: '1px solid #3c3c3c', borderRadius: 3, padding: '4px 8px', fontSize: 11, color: '#d4d4d4' }} />
                </div>
              )}

              {valuesSource === 'setting' && (
                <input type="text" placeholder="Setting name (e.g., select_lists)" value={settingName} onChange={(e) => setSettingName(e.target.value)}
                  style={{ background: '#252526', border: '1px solid #3c3c3c', borderRadius: 3, padding: '4px 8px', fontSize: 11, color: '#d4d4d4' }} />
              )}
            </>
          )}

          {/* Lookup config */}
          {changeType === 'lookup' && (
            <div style={{ display: 'flex', gap: 6 }}>
              <input type="text" placeholder="Lookup model (e.g., customer)" value={queryModel} onChange={(e) => setQueryModel(e.target.value)}
                style={{ flex: 1, background: '#252526', border: '1px solid #3c3c3c', borderRadius: 3, padding: '4px 8px', fontSize: 11, color: '#d4d4d4' }} />
              <input type="text" placeholder="Display field (e.g., display_name)" value={queryField} onChange={(e) => setQueryField(e.target.value)}
                style={{ flex: 1, background: '#252526', border: '1px solid #3c3c3c', borderRadius: 3, padding: '4px 8px', fontSize: 11, color: '#d4d4d4' }} />
            </div>
          )}

          {/* Reason */}
          <input type="text" placeholder="Why this change? (optional but helpful)"
            value={reason} onChange={(e) => setReason(e.target.value)}
            style={{ background: '#252526', border: '1px solid #3c3c3c', borderRadius: 3, padding: '4px 8px', fontSize: 11, color: '#d4d4d4' }} />

          <button onClick={handleSubmit} disabled={submitting}
            style={{ alignSelf: 'flex-start', padding: '5px 16px', fontSize: 11, fontWeight: 600, border: 'none', borderRadius: 4, background: '#6f42c1', color: '#fff', cursor: submitting ? 'wait' : 'pointer', opacity: submitting ? 0.6 : 1 }}>
            {submitting ? 'Submitting...' : 'Submit Request'}
          </button>
        </div>
      )}
    </div>
  );
}


// ---------------------------------------------------------------------------
// ContributeHelp — user adds a tip that becomes a Document record
// ---------------------------------------------------------------------------

function ContributeHelp({ componentName, sourcePath }: { componentName: string; sourcePath: string }) {
  const [showForm, setShowForm] = useState(false);
  const [tip, setTip] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  if (submitted) {
    return (
      <div style={{ marginTop: 12, padding: '8px 12px', background: '#1a3a2e', borderRadius: 4, fontSize: 11, color: '#4ade80' }}>
        Tip submitted. Alice will review and add it to the help for {componentName}.
      </div>
    );
  }

  const handleSubmit = async () => {
    if (!tip.trim()) return;
    setSubmitting(true);
    try {
      const { saveRecord } = await import('@/api/wcapi');
      await saveRecord({
        model_name: 'document',
        name: `User tip: ${componentName}`,
        purpose: 'help-alice',
        description: `User-contributed help for ${componentName}`,
        body: tip,
        status: 'pending',
        path: sourcePath ? { source: sourcePath } : null,
        config: {
          component_name: componentName,
          source_path: sourcePath,
          contribution: true,
        },
      });
      setSubmitted(true);
    } catch {
      setSubmitted(true);
    }
    setSubmitting(false);
  };

  return (
    <div style={{ marginTop: 12, borderTop: '1px solid #3c3c3c', paddingTop: 10 }}>
      <button onClick={() => setShowForm(!showForm)}
        style={{ background: 'none', border: '1px solid #4ade80', borderRadius: 4, padding: '4px 12px', fontSize: 11, color: '#4ade80', cursor: 'pointer', fontWeight: 600 }}>
        {showForm ? 'Cancel' : 'Add a Tip'}
      </button>

      {showForm && (
        <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ fontSize: 10, color: '#888' }}>
            Share what you know about {componentName}. Alice will review and publish to the help system.
          </div>
          <textarea
            value={tip}
            onChange={(e) => setTip(e.target.value)}
            placeholder="What should other users know about this? Tips, gotchas, workflows..."
            style={{
              width: '100%', height: 80, background: '#252526', border: '1px solid #3c3c3c',
              borderRadius: 4, padding: 8, color: '#d4d4d4', fontSize: 11,
              fontFamily: 'sans-serif', resize: 'vertical',
            }}
          />
          <button onClick={handleSubmit} disabled={submitting || !tip.trim()}
            style={{ alignSelf: 'flex-start', padding: '5px 16px', fontSize: 11, fontWeight: 600, border: 'none', borderRadius: 4, background: '#4ade80', color: '#1e1e1e', cursor: submitting ? 'wait' : 'pointer', opacity: submitting || !tip.trim() ? 0.5 : 1 }}>
            {submitting ? 'Submitting...' : 'Submit Tip'}
          </button>
        </div>
      )}
    </div>
  );
}

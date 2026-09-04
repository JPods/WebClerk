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
import './GetHelpDialog.css';

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

// Component help loaded from Document records (purpose='help-alice') via wcapi.
// Falls back to this static map only if the query fails or returns empty.
const COMPONENT_HELP_FALLBACK: Record<string, { source: string; description: string }> = {
  'ModelDetailPage': { source: 'components/common/ModelDetailPage.tsx', description: 'Unified detail page — JSON-driven layout for contact, org, item, and any model with a detail_layout Setting.' },
  'UiDetail': { source: 'apps/transactions/components/TransactionDetail.tsx', description: 'Shared transaction renderer — orders, invoices, proposals, purchases.' },
  'DynamicDetail': { source: 'components/common/DynamicDetail.tsx', description: 'Generic data-driven form renderer. Reads layout JSON, renders any model.' },
  'DataBrowser': { source: 'pages/admin/DataBrowser.tsx', description: 'Universal databrowser — lists and details for any model.' },
};

// Cache for Document-based component help (loaded once per session)
let _componentHelpCache: Record<string, { source: string; description: string }> | null = null;
let _componentHelpLoading = false;

async function getComponentHelp(): Promise<Record<string, { source: string; description: string }>> {
  if (_componentHelpCache) return _componentHelpCache;
  if (_componentHelpLoading) return COMPONENT_HELP_FALLBACK;
  _componentHelpLoading = true;
  try {
    const { getRecords } = await import('@/api/wcapi');
    const res = await getRecords('document', {
      status: 'active',
      config__doc_system: 'help-alice',
      limit: 200,
    }) as any;
    const docs = res?.results || [];
    const map: Record<string, { source: string; description: string }> = {};
    for (const doc of docs) {
      const name = doc.config?.component_name || doc.name;
      if (name) {
        map[name] = {
          source: doc.config?.source_path || doc.path?.source || '',
          description: doc.body?.slice(0, 500) || doc.description || '',
        };
      }
    }
    // Merge fallback for any components not in DB yet
    _componentHelpCache = { ...COMPONENT_HELP_FALLBACK, ...map };
    return _componentHelpCache;
  } catch {
    _componentHelpCache = COMPONENT_HELP_FALLBACK;
    return _componentHelpCache;
  } finally {
    _componentHelpLoading = false;
  }
}

async function parseInput(text: string): Promise<{ wcId: string; wcModel?: string; wcField?: string; componentName?: string; sourcePath?: string; rawAttrs: Record<string, string> }> {
  const result: { wcId: string; wcModel?: string; wcField?: string; componentName?: string; sourcePath?: string; rawAttrs: Record<string, string> } = { wcId: '', rawAttrs: {} };
  const componentHelp = await getComponentHelp();

  // First: check if it's a component name (from Shift+click on DevIdentifier badge)
  const trimmed = text.trim();
  if (componentHelp[trimmed]) {
    result.componentName = trimmed;
    result.sourcePath = componentHelp[trimmed].source;
    return result;
  }

  // Check if it's a file path (from Shift+hover copy)
  if (trimmed.endsWith('.tsx') || trimmed.endsWith('.ts')) {
    const fileName = trimmed.split('/').pop()?.replace(/\.tsx?$/, '') || '';
    result.sourcePath = trimmed;
    result.componentName = fileName;
    return result;
  }

  // Check if it's a plain field name (no HTML tags, no spaces — just a field identifier)
  if (/^[a-z_][a-z0-9_.]*$/i.test(trimmed) && !trimmed.includes('<')) {
    result.wcField = trimmed.includes('.') ? trimmed.split('.').pop()! : trimmed;
    // If dotted like "contact.name_first", extract model
    if (trimmed.includes('.')) {
      result.wcModel = trimmed.split('.')[0];
    }
    result.wcId = `field-${result.wcField}`;
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
  const [parsedContext, setParsedContext] = useState<{ sourcePath?: string; wcField?: string; wcModel?: string }>({});
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (open) {
      setPastedHtml('');
      setHelpResult(null);
      setParsedContext({});
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [open]);

  const analyzeElement = useCallback(async (html: string) => {
    if (!html.trim()) return;
    setLoading(true);

    const parsed = await parseInput(html);
    setParsedContext({ sourcePath: parsed.sourcePath, wcField: parsed.wcField, wcModel: parsed.wcModel });
    const componentHelp = await getComponentHelp();

    // Try component name first, then data-wc, then unknown
    const componentInfo = parsed.componentName ? componentHelp[parsed.componentName] : null;
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

    // Look up field-level help from coaching + field_access Settings
    if (parsed.wcField) {
      try {
        const { getRecords } = await import('@/api/wcapi');
        let coachHelp: string | undefined;

        if (parsed.wcModel) {
          // Model known — look up directly
          const coachRes = await getRecords('setting', { parent_model: parsed.wcModel, purpose: 'wc:coaching', limit: 1 }) as any;
          const coachRec = (coachRes?.results || [])[0];
          coachHelp = coachRec?.config?.field_help?.[parsed.wcField];
        }

        if (!coachHelp) {
          // Model unknown or field not found — search all coaching records
          const allRes = await getRecords('setting', { purpose: 'wc:coaching', limit: 50 }) as any;
          const allRecs = allRes?.results || [];
          for (const rec of allRecs) {
            const help = rec?.config?.field_help?.[parsed.wcField];
            if (help) {
              coachHelp = help;
              // Update label to show which model this field belongs to
              if (rec.parent_model && rec.parent_model !== 'system') {
                result.label = `${rec.parent_model}.${parsed.wcField}`;
              }
              break;
            }
          }
        }

        if (coachHelp) {
          result.field_help = coachHelp;
        } else if (parsed.wcModel) {
          // Fall back to field_access behaviors
          const faRes = await getRecords('setting', { parent_model: parsed.wcModel, purpose: 'wc:field_access', limit: 1 }) as any;
          const faRec = (faRes?.results || [])[0];
          const fieldBehavior = faRec?.config?.field_behaviors?.[parsed.wcField];
          if (fieldBehavior) {
            result.field_help = `Field: ${parsed.wcField} — Type: ${fieldBehavior.type || 'text'}${fieldBehavior.help ? ` — ${fieldBehavior.help}` : ''}`;
          }
        }
      } catch { /* silent */ }
    }

    // Look up page-level help (buttons, sections, panels) — check wcId, wcField, or raw input
    if (!result.field_help) {
      const pageKeys = [parsed.wcId, parsed.wcField, html.trim()].filter(Boolean);
      try {
        const { getRecords } = await import('@/api/wcapi');
        const pageRes = await getRecords('setting', { purpose: 'wc:coaching', name: 'alice_coaching:page_help', limit: 1 }) as any;
        const pageRec = (pageRes?.results || [])[0];
        const pageHelpMap = pageRec?.config?.page_help || {};
        for (const key of pageKeys) {
          if (key && pageHelpMap[key]) {
            result.field_help = pageHelpMap[key];
            result.label = key;
            break;
          }
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

    // Log help lookup as AiMessage — frequency = confusion signal
    try {
      const { saveRecord } = await import('@/api/wcapi');
      saveRecord('ai_message', {
        kind: 'help_lookup',
        sender: 'user',
        receiver: 'alice',
        subject: parsed.wcField || parsed.wcId || parsed.componentName || 'unknown',
        body: html.trim().slice(0, 200),
        status: 'read',
        context: { field: parsed.wcField, element: parsed.wcId, component: parsed.componentName, model: parsed.wcModel, source: parsed.sourcePath },
      }).catch(() => {});
    } catch { /* silent */ }

    // Clear generic topic when we have real help content
    if (result.field_help && result.topic === 'No specific help available for this element. Try copying an element with a data-wc attribute.') {
      result.topic = '';
    }

    setHelpResult(result);
    setLoading(false);
  }, []);

  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    e.preventDefault();
    const text = e.clipboardData.getData('text');
    setPastedHtml(text);
    analyzeElement(text);
  }, [analyzeElement]);

  if (!open) return null;

  return (
    <div data-wc="get-help-dialog" className="gh-root gh-overlay"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="gh-panel" role="dialog" aria-modal="true" aria-label="Get help">
        <div className="gh-header">
          <h2 className="gh-title">Get Help</h2>
          <button onClick={onClose} className="gh-close-btn">×</button>
        </div>

        <p className="gh-instructions">
          Shift+hover any zone → click nametag to copy → paste here. Or right-click → Inspect → Copy Element → paste.
        </p>

        <textarea
          ref={inputRef}
          data-wc="help-paste-area"
          className="gh-textarea"
          value={pastedHtml}
          onChange={(e) => { setPastedHtml(e.target.value); }}
          onPaste={handlePaste}
          placeholder="Paste copied element here..."
        />

        {pastedHtml && !helpResult && !loading && (
          <button onClick={() => analyzeElement(pastedHtml)} className="gh-analyze-btn">
            Analyze
          </button>
        )}

        {loading && <div className="gh-loading">Looking up help...</div>}

        {helpResult && (
          <div className="gh-result">
            <div className="gh-result-label">
              {helpResult.label}
            </div>
            {helpResult.topic && (
              <div className="gh-result-topic">
                {helpResult.topic}
              </div>
            )}

            {/* Unknown element — offer to request help from WCHQ */}
            {helpResult.label === 'Unknown Element' && (
              <RequestWchqHelp elementText={pastedHtml} />
            )}

            {helpResult.field_help && (
              <div className="gh-field-info">
                <span className="gh-field-info-label">Field Info:</span> {helpResult.field_help}
              </div>
            )}

            {helpResult.alice_notes && helpResult.alice_notes.length > 0 && (
              <div className="gh-alice-notes">
                <div className="gh-section-header gh-section-header--alice">Alice Notes</div>
                {helpResult.alice_notes.map((note, i) => (
                  <div key={i} className="gh-alice-note">
                    {note}
                  </div>
                ))}
              </div>
            )}

            {helpResult.training && (
              <div className="gh-training">
                <div className="gh-section-header gh-section-header--training">Training Available</div>
                <div className="gh-training-content">
                  {helpResult.training}
                </div>
              </div>
            )}

            {helpResult.wchq_notes && helpResult.wchq_notes.length > 0 && (
              <div>
                <div className="gh-section-header gh-section-header--wchq">WCHQ Documentation</div>
                {helpResult.wchq_notes.map((note, i) => (
                  <div key={i} className="gh-wchq-note">
                    {note}
                  </div>
                ))}
              </div>
            )}

            {/* User feedback — tips, change requests, questions */}
            <UserFeedback
              label={helpResult.label}
              wcField={parsedContext.wcField || ''}
              wcModel={parsedContext.wcModel || ''}
              sourcePath={parsedContext.sourcePath || ''}
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
  const [existingAnswers, setExistingAnswers] = useState<any[]>([]);
  const [searched, setSearched] = useState(false);

  // Search existing Q&A first before creating a new question
  const handleSearch = async (q: string) => {
    if (!q.trim() || q.length < 3) return;
    try {
      const { manageAction } = await import('@/api/wcapi');
      const res = await manageAction('search_support_qa', { query: q, limit: 5 });
      setExistingAnswers(res?.data?.results || []);
      setSearched(true);
    } catch { setSearched(true); }
  };

  const handleSubmit = async () => {
    if (!question.trim()) return;
    setSubmitting(true);
    try {
      const { manageAction } = await import('@/api/wcapi');
      const { collectSupportContext } = await import('@/utils/supportContext');
      const context = collectSupportContext();

      // Create Q&A question with diagnostic context
      const qaRes = await manageAction('ask_support_qa', {
        question: question,
        context: elementText.slice(0, 500),
        asked_by: 'user',
      });

      // Post to WCHQ with full diagnostic context
      if (qaRes?.data?.id) {
        await manageAction('post_qa_to_wchq', {
          document_id: qaRes.data.id,
          context: { ...context, pasted_element: elementText.slice(0, 300) },
        });
      }
      setSubmitted(true);
    } catch {
      setSubmitted(true);
    }
    setSubmitting(false);
  };

  if (submitted) {
    return (
      <div className="gh-success gh-success--mb">
        Question submitted to WCHQ. You will receive an answer in your action list.
      </div>
    );
  }

  return (
    <div className="gh-wchq-request">
      <div className="gh-wchq-request-row">
        <input
          type="text"
          value={question}
          onChange={(e) => { setQuestion(e.target.value); setSearched(false); setExistingAnswers([]); }}
          onKeyDown={(e) => { if (e.key === 'Enter') { searched ? handleSubmit() : handleSearch(question); } }}
          placeholder="What do you need help with?"
          className="gh-input gh-input--flex"
        />
        {!searched ? (
          <button
            onClick={() => handleSearch(question)}
            disabled={!question.trim() || question.length < 3}
            className="gh-btn-accent"
          >
            Search
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={submitting || !question.trim()}
            className="gh-btn-accent"
          >
            {submitting ? '...' : 'Ask WCHQ'}
          </button>
        )}
      </div>

      {/* Show existing answers before letting user submit */}
      {searched && existingAnswers.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#4ade80', textTransform: 'uppercase', marginBottom: 4 }}>
            Existing Answers ({existingAnswers.length})
          </div>
          {existingAnswers.map((a: any, i: number) => (
            <div key={i} style={{ padding: '6px 10px', background: '#1a3a2e', borderRadius: 4, fontSize: 11, marginBottom: 3, cursor: 'pointer' }}
              title={a.answer_preview}>
              <span style={{ color: '#4ade80', fontWeight: 600 }}>{a.question}</span>
              {a.score_avg > 0 && <span style={{ color: '#888', marginLeft: 8 }}>★ {a.score_avg}</span>}
              <div style={{ color: '#aaa', marginTop: 2 }}>{a.answer_preview?.slice(0, 150)}</div>
            </div>
          ))}
          <div style={{ fontSize: 10, color: '#888', marginTop: 4 }}>
            Not what you need? Click "Ask WCHQ" to submit your question to the team.
          </div>
        </div>
      )}

      {searched && existingAnswers.length === 0 && (
        <div style={{ fontSize: 10, color: '#888', marginTop: 4 }}>
          No existing answers found. Click "Ask WCHQ" to submit to Bill, Alice, and the team.
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// UserFeedback — single button for tips, change requests, questions
// Alice classifies the content during her review.
// ---------------------------------------------------------------------------

function UserFeedback({ label, wcField, wcModel, sourcePath }: { label: string; wcField: string; wcModel: string; sourcePath: string }) {
  const [showForm, setShowForm] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  if (submitted) {
    return (
      <div className="gh-success gh-success--mt">
        Feedback submitted for {label}. Alice will review and take action.
      </div>
    );
  }

  const handleSubmit = async () => {
    if (!feedback.trim()) return;
    setSubmitting(true);
    try {
      const { submitFeedback } = await import('@/apps/docs/models/document/services/documentApi');
      await submitFeedback({ label, feedback, field: wcField, model: wcModel, sourcePath });
      setSubmitted(true);
    } catch {
      setSubmitted(true);
    }
    setSubmitting(false);
  };

  return (
    <div className="gh-contribute">
      <button onClick={() => setShowForm(!showForm)} className="gh-btn-outline-green">
        {showForm ? 'Cancel' : 'Feedback'}
      </button>

      {showForm && (
        <div className="gh-contribute-form">
          <div className="gh-contribute-hint">
            Tips, corrections, change requests — anything about {label}. Alice will review.
          </div>
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="What should we know? Tips, corrections, suggestions..."
            className="gh-contribute-textarea"
          />
          <button onClick={handleSubmit} disabled={submitting || !feedback.trim()} className="gh-btn-green">
            {submitting ? 'Submitting...' : 'Submit'}
          </button>
        </div>
      )}
    </div>
  );
}

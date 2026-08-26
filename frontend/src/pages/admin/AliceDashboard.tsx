/**
 * AliceDashboard — Alice's coaching and monitoring dashboard.
 *
 * Shows: coaching tips, console errors, user actions, training docs,
 * system health, and "Ask Alice" input.
 *
 * Route: /alice-dashboard
 */
import React, { useCallback, useEffect, useMemo, useState, Suspense } from 'react';
import { getRecords } from '@/api/wcapi';
import { formatDt } from '@/utils/fieldFormatters';
import { consoleCapture, type ConsoleEntry } from '@/utils/consoleCapture';
import { useAppSelector } from '@/store/hooks';
import { useWindowManager } from '@/context/WindowManagerContext';

const AliceQuiz = React.lazy(() => import('./AliceQuiz'));
const PdfDesigner = React.lazy(() => import('../tools/PdfDesigner'));

/**
 * DocSection — a collapsible section whose content is a Document record.
 * Fetches the document body only when expanded (lazy load).
 * Content is stored as a Document record with a known ida.
 *
 * Usage: <DocSection ida="HELP-SEARCH" title="How Search Works" />
 */
function DocSection({ ida, title, subtitle }: { ida: string; title: string; subtitle?: string }) {
  const [body, setBody] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);

  const handleToggle = useCallback(async () => {
    if (!open && body === null) {
      setLoading(true);
      try {
        const res = await getRecords('document', { ida, limit: 1 }) as any;
        const doc = (res?.results || [])[0];
        setBody(doc?.body || doc?.description || '(No content found. Create a Document with ida="' + ida + '" to populate this section.)');
      } catch {
        setBody('(Failed to load content.)');
      } finally {
        setLoading(false);
      }
    }
    setOpen(!open);
  }, [open, body, ida]);

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg">
      <button onClick={handleToggle}
        className="w-full flex items-center justify-between p-3 text-left hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg">
        <div>
          <span className="text-sm font-medium text-gray-800 dark:text-gray-200">{title}</span>
          {subtitle && <span className="ml-2 text-xs text-gray-500">{subtitle}</span>}
        </div>
        <span className="text-gray-400 text-xs">{open ? '▼' : '▶'}</span>
      </button>
      {open && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-600 dark:text-gray-400">
          {loading ? (
            <span className="text-gray-400">Loading...</span>
          ) : (
            <pre className="whitespace-pre-wrap font-sans">{body}</pre>
          )}
        </div>
      )}
    </div>
  );
}

export default function AliceDashboard() {
  const { user } = useAppSelector((s) => s.auth);
  const { ensureWindow, activateWindow } = useWindowManager();
  const [coaching, setCoaching] = useState<any>(null);
  const [actions, setActions] = useState<any[]>([]);
  const [trainingDocs, setTrainingDocs] = useState<any[]>([]);
  const [consoleEntries, setConsoleEntries] = useState<ConsoleEntry[]>([]);
  const [consoleSummary, setConsoleSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [askText, setAskText] = useState('');

  // Read ?tab= and ?report= from URL query params
  const urlTab = useMemo(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('tab') as any || 'coaching';
  }, []);
  const urlReportId = useMemo(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('report') || null;
  }, []);

  const [activeTab, setActiveTab] = useState<'coaching' | 'console' | 'actions' | 'training' | 'health' | 'llm' | 'quiz' | 'reports' | 'pdf-designer' | 'data-quality' | 'import' | 'library' | 'readmes'>(urlTab);
  const [llmConfig, setLlmConfig] = useState<any>(null);
  const [llmSaving, setLlmSaving] = useState(false);
  const [importPath, setImportPath] = useState('');
  const [importStatus, setImportStatus] = useState<'idle' | 'analyzing' | 'preview' | 'reviewing' | 'ready' | 'error'>('idle');
  const [importPreview, setImportPreview] = useState<any>(null);
  const [importConnection, setImportConnection] = useState<any>(null);
  const [importBundle, setImportBundle] = useState<any>(null);

  // Load data
  useEffect(() => {
    (async () => {
      try {
        // Coaching tips (generic system coaching)
        const cRes = await getRecords('setting', { purpose: 'wc:coaching', limit: 10 }) as any;
        const coachingRecords = cRes?.results || [];
        setCoaching(coachingRecords);

        // User's actions (open, assigned to them)
        const aRes = await getRecords('action', { kanban_column: 'todo', ordering: '-priority', limit: 20 }) as any;
        setActions(aRes?.results || []);

        // Training documents
        const tRes = await getRecords('document', { filters: { model_name: 'system', status: 'published' }, ordering: 'name', limit: 20 }) as any;
        setTrainingDocs(tRes?.results || []);

        // LLM config
        const lRes = await getRecords('setting', { name: 'alice_llm_config', purpose: 'wc:coaching' }) as any;
        const llmRec = (lRes?.results || [])[0];
        setLlmConfig(llmRec?.config || {
          provider: 'ollama',
          model: 'allie:latest',
          endpoint: 'http://localhost:11434',
          temperature: 0.7,
          max_tokens: 2000,
          system_prompt: 'You are Alice, the WebClerk coaching agent. Help users learn the system.',
        });
      } catch { /* silent */ }
      finally { setLoading(false); }
    })();
  }, []);

  // Refresh console entries periodically
  useEffect(() => {
    const refresh = () => {
      setConsoleEntries(consoleCapture.getEntries());
      setConsoleSummary(consoleCapture.getSummary());
    };
    refresh();
    const interval = setInterval(refresh, 3000);
    return () => clearInterval(interval);
  }, []);

  // Send console to Alice
  const handleSendConsole = useCallback(async () => {
    await consoleCapture.sendToAlice(`User: ${user?.email || 'unknown'}, Tab: ${activeTab}`);
    alert('Console log sent to Alice.');
  }, [user, activeTab]);

  // Start/stop capture
  const [captureActive, setCaptureActive] = useState(false);
  const toggleCapture = useCallback(() => {
    if (captureActive) { consoleCapture.stop(); setCaptureActive(false); }
    else { consoleCapture.start(); setCaptureActive(true); }
  }, [captureActive]);

  const tabBtn = (tab: string, label: string, count?: number) => (
    <button key={tab}
      onClick={() => setActiveTab(tab as any)}
      className={`px-4 py-2 text-xs font-medium border-b-2 -mb-px transition ${
        activeTab === tab
          ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
          : 'border-transparent text-gray-500 hover:text-gray-700'
      }`}
    >
      {label}{count !== undefined ? ` (${count})` : ''}
    </button>
  );

  if (loading) return <div className="p-8 text-gray-500">Loading Alice Dashboard...</div>;

  return (
    <div className="max-w-5xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Alice Dashboard</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Coaching, monitoring, and training for {user?.email || 'you'}.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={toggleCapture}
            className={`px-3 py-1.5 text-xs font-medium rounded border transition ${
              captureActive ? 'bg-green-100 text-green-700 border-green-300' : 'text-gray-600 border-gray-300 hover:bg-gray-100'
            }`}>
            {captureActive ? '● Capturing' : 'Start Capture'}
          </button>
          <button onClick={handleSendConsole}
            className="px-3 py-1.5 text-xs font-medium rounded border border-blue-300 text-blue-600 hover:bg-blue-50">
            Send to Alice
          </button>
          <button onClick={() => consoleCapture.clear()}
            className="px-3 py-1.5 text-xs font-medium rounded border border-gray-300 text-gray-500 hover:bg-gray-100">
            Clear
          </button>
        </div>
      </div>

      {/* Table of Contents */}
      <details className="mb-6 border border-gray-200 dark:border-gray-700 rounded-lg">
        <summary className="p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg">
          <span className="text-sm font-bold text-gray-700 dark:text-gray-300">Table of Contents</span>
          <span className="ml-2 text-xs text-gray-400">15 tabs · 41 flowcharts · complete system reference</span>
        </summary>
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
          {[
            { tab: 'coaching', label: 'Coaching Tips', desc: 'Alice coaching tips per model' },
            { tab: 'console', label: 'Console', desc: 'Browser console capture + send to Alice' },
            { tab: 'actions', label: 'My Actions', desc: 'Open actions assigned to you' },
            { tab: 'training', label: 'Training', desc: '41 flowcharts + training documents' },
            { tab: 'health', label: 'System Health', desc: 'Console health, open actions, training progress' },
            { tab: 'llm', label: 'LLM Config', desc: 'Alice LLM provider, model, endpoint, prompt' },
            { tab: 'quiz', label: 'Quiz', desc: 'Commerce knowledge quiz from Alice' },
            { tab: 'data-quality', label: 'Data Quality', desc: '10 tasks — phone, email, dedup, address, OCR' },
            { tab: 'import', label: 'Import Data', desc: 'File → Alice analysis → mapping → Athena → bundle' },
            { tab: 'library', label: 'Library', desc: 'File upload, Celery pipeline, cloud transfer' },
            { tab: 'reports', label: 'Reports', desc: '13 print templates + report designer' },
            { tab: 'pdf-designer', label: 'PDF Designer', desc: 'pdfme template builder' },
            { tab: 'readmes', label: 'Readmes', desc: 'Scrollable index of all system documentation' },
          ].map((item) => (
            <button key={item.tab} onClick={() => setActiveTab(item.tab as any)}
              className={`text-left p-2 rounded border transition ${
                activeTab === item.tab
                  ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/30 dark:border-blue-600'
                  : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'
              }`}>
              <div className="font-medium text-gray-800 dark:text-gray-200">{item.label}</div>
              <div className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5">{item.desc}</div>
            </button>
          ))}
        </div>
      </details>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 mb-6">
        {tabBtn('coaching', 'Coaching Tips', coaching?.length)}
        {tabBtn('console', 'Console', consoleSummary?.errors + consoleSummary?.warns)}
        {tabBtn('actions', 'My Actions', actions.length)}
        {tabBtn('training', 'Training', trainingDocs.length)}
        {tabBtn('health', 'System Health')}
        {tabBtn('llm', 'LLM Config')}
        {tabBtn('quiz', 'Quiz')}
        {tabBtn('data-quality', 'Data Quality')}
        {tabBtn('import', 'Import Data')}
        {tabBtn('library', 'Library')}
        {tabBtn('reports', 'Reports')}
        {tabBtn('pdf-designer', 'PDF Designer')}
        {tabBtn('readmes', 'Readmes')}
      </div>

      {/* Tab content */}

      {/* ═══ Coaching Tips ═══ */}
      {activeTab === 'coaching' && (
        <div className="space-y-4">
          {coaching?.map((setting: any) => {
            const tips = setting.config?.tips || [];
            const modelName = setting.parent_model || 'system';
            return (
              <div key={setting.id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                <h3 className="text-sm font-bold text-blue-600 dark:text-blue-400 uppercase mb-2">{modelName}</h3>
                {tips.map((tip: any) => (
                  <div key={tip.id} className="mb-2 pl-3 border-l-2 border-blue-200 dark:border-blue-800">
                    <div className="text-sm font-semibold text-gray-800 dark:text-gray-200">{tip.title}</div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">{tip.body}</div>
                    {tip.link && (
                      <button
                        className="mt-1 text-xs font-medium px-3 py-1 rounded"
                        style={{ background: 'var(--db-accent)', color: 'var(--db-surface)' }}
                        onClick={() => { ensureWindow(tip.link, tip.link_label || tip.title); activateWindow(tip.link); }}
                      >
                        {tip.link_label || tip.title}
                      </button>
                    )}
                  </div>
                ))}
                {/* Field help */}
                {setting.config?.field_help && (
                  <details className="mt-2">
                    <summary className="text-xs text-gray-500 cursor-pointer">Field help ({Object.keys(setting.config.field_help).length} fields)</summary>
                    <div className="mt-1 grid grid-cols-2 gap-1">
                      {Object.entries(setting.config.field_help).map(([field, help]: [string, any]) => (
                        <div key={field} className="text-[10px]">
                          <span className="font-semibold text-gray-700 dark:text-gray-300">{field}:</span>{' '}
                          <span className="text-gray-500">{help}</span>
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            );
          })}
          {(!coaching || coaching.length === 0) && <p className="text-sm text-gray-500">No coaching content loaded.</p>}
        </div>
      )}

      {/* ═══ Console ═══ */}
      {activeTab === 'console' && (
        <div>
          <div className="flex gap-4 mb-4 text-xs text-gray-500">
            <span>Total: {consoleSummary?.total || 0}</span>
            <span className="text-red-500">Errors: {consoleSummary?.errors || 0}</span>
            <span className="text-yellow-600">Warnings: {consoleSummary?.warns || 0}</span>
            <span>{captureActive ? '● Capturing active' : '○ Capture stopped'}</span>
          </div>
          <div className="bg-gray-900 rounded-lg p-4 max-h-96 overflow-auto font-mono text-xs">
            {consoleEntries.length === 0 && (
              <div className="text-gray-500">
                {captureActive ? 'No console entries yet. Interact with the app to generate logs.' : 'Click "Start Capture" to begin logging console output.'}
              </div>
            )}
            {consoleEntries.map((entry, i) => (
              <div key={i} className={`py-0.5 ${
                entry.level === 'error' ? 'text-red-400' :
                entry.level === 'warn' ? 'text-yellow-400' : 'text-gray-300'
              }`}>
                <span className="text-gray-600">{formatDt(entry.dt, 'datetime')}</span>{' '}
                <span className={entry.level === 'error' ? 'text-red-500' : entry.level === 'warn' ? 'text-yellow-500' : 'text-blue-400'}>
                  [{entry.level.toUpperCase()}]
                </span>{' '}
                {entry.args.join(' ').slice(0, 300)}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ═══ Actions ═══ */}
      {activeTab === 'actions' && (
        <div>
          {actions.length === 0 && <p className="text-sm text-gray-500">No open actions.</p>}
          <div className="space-y-2">
            {actions.map((action: any) => (
              <div key={action.id} className="flex items-center gap-3 p-3 border border-gray-200 dark:border-gray-700 rounded-lg">
                <div className={`w-2 h-2 rounded-full ${
                  action.priority >= 3 ? 'bg-red-500' : action.priority === 2 ? 'bg-yellow-500' : 'bg-gray-400'
                }`} />
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-800 dark:text-gray-200">
                    {typeof action.action === 'object' ? action.action.en : action.action}
                  </div>
                  <div className="text-[10px] text-gray-500">
                    {action.project_name} · {action.kanban_column} · Priority {action.priority}
                  </div>
                </div>
                {action.percent_complete > 0 && (
                  <span className="text-xs text-blue-600 font-semibold">{action.percent_complete}%</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ═══ Training ═══ */}
      {activeTab === 'training' && (
        <div className="space-y-4">
          {/* ── Flowcharts ── */}
          <details open className="border border-indigo-200 dark:border-indigo-800 rounded-lg">
            <summary className="p-3 cursor-pointer bg-indigo-50 dark:bg-indigo-900/30 rounded-t-lg">
              <span className="text-sm font-bold text-indigo-700 dark:text-indigo-300">Commerce Flowcharts</span>
              <span className="ml-2 text-xs text-indigo-500">35 charts — WC3/R25 complete system</span>
            </summary>
            <div className="p-4 border-t border-indigo-200 dark:border-indigo-800">
              {[
                { title: 'Core Commerce Flow', charts: [
                  { name: 'Master Commerce Flow', file: 'wc3-master-flow', desc: 'Market → Contact → Proposal → Order → Invoice → Payment → GL' },
                  { name: 'Big 4 Transactions', file: 'wc3-big4-transactions', desc: 'Proposal/Order/Purchase/Invoice line quantities and pending inventory' },
                  { name: 'Order to Invoice', file: 'wc3-order-to-invoice', desc: 'Customer → verify → order → production → backorder/invoice' },
                  { name: 'Customer-Centered Sales', file: 'wc3-customer-centered-sales', desc: 'Commerce from the customer perspective' },
                ]},
                { title: 'Inventory & Purchasing', charts: [
                  { name: 'Inventory Buckets', file: 'wc3-inventory-buckets', desc: 'on_hand, on_so, on_po, on_wo → available' },
                  { name: 'Inventory Costing', file: 'wc3-inventory-costing', desc: 'Layer-based: LIFO / FIFO / Weighted Average' },
                  { name: 'Inventory Adjustment', file: 'wc3-inventory-adjustment', desc: 'Physical count → variance → adjustment → audit trail' },
                  { name: 'PO Receipt Flow', file: 'wc3-po-receipt', desc: 'Purchase → receive → layers → serials → GL' },
                  { name: 'Forecast & Purchasing', file: 'wc3-forecast-purchasing', desc: 'Demand signals → forecast → PO → receive' },
                  { name: 'Requisition Management', file: 'wc3-requisition-management', desc: 'Internal procurement: request → approve → PO' },
                  { name: 'Bill of Materials', file: 'wc3-bom', desc: 'Assembly tree: expand, build, cost rollup, where-used' },
                ]},
                { title: 'Cross-Instance Commerce', charts: [
                  { name: 'PO→SO Bundle', file: 'wc3-po-so-bundle', desc: 'Buyer PO → vendor SO; cost→price mapping; bundle UUID tracking; status polling' },
                ]},
                { title: 'Sales & Marketing', charts: [
                  { name: 'Sales Management', file: 'wc3-sales-management', desc: 'Pipeline, activity tracking, performance evaluation' },
                  { name: 'Lead Qualification', file: 'wc3-lead-qualification', desc: 'Marketing → leads → qualify → commit or disqualify' },
                  { name: 'Ad Source Tracking', file: 'wc3-ad-source-tracking', desc: 'Campaign ROI: source → lead → customer → revenue' },
                  { name: 'Territory Assignment', file: 'wc3-territory-assignment', desc: 'Auto-assign rep & sales ID by geography' },
                  { name: 'Commission Calculation', file: 'wc3-commission-calculation', desc: 'Rep rate × item commissionableness → line commission' },
                  { name: 'Price Cascade', file: 'wc3-price-cascade', desc: 'First-match-wins: item → level → customer → final price' },
                ]},
                { title: 'Support & Service', charts: [
                  { name: 'Service & RMA', file: 'wc3-service-rma', desc: 'Track, route, resolve, learn (Pareto + Alice)' },
                  { name: 'Returns & Credits', file: 'wc3-returns-credits', desc: 'RMA → credit memo → inventory reversal → GL' },
                  { name: 'QA Entity', file: 'wc3-qa-entity', desc: 'Quality inspection, surveys, customer feedback' },
                  { name: 'Serial Tracking', file: 'wc3-serial-tracking', desc: 'Receive → reserve → ship → return; warranty' },
                ]},
                { title: 'Financial', charts: [
                  { name: 'Payment & GL', file: 'wc3-payment-gl', desc: 'Payment → journals → GL; aging; erosion detection' },
                  { name: 'Management Dashboard', file: 'wc3-management-dashboard', desc: 'Input efforts → evaluation → business results' },
                ]},
                { title: 'Organization & Infrastructure', charts: [
                  { name: 'Project', file: 'wc3-project', desc: 'Project connects transactions; data layer' },
                  { name: 'Action', file: 'wc3-action', desc: 'Universal task: Who/What/Why/When' },
                  { name: 'Linkage', file: 'wc3-linkage', desc: 'Data package: project inheritance, transaction chain, item families' },
                  { name: 'Contact', file: 'wc3-contact', desc: 'Central identity: roles, linkage' },
                  { name: 'Sign-in / Register', file: 'wc3-signin-register', desc: 'Authentication + role assignment' },
                  { name: 'RBAC & Field Access', file: 'wc3-rbac-field-access', desc: 'Role → Setting → what each user sees and edits' },
                  { name: 'Save Pipeline', file: 'wc3-save-pipeline', desc: 'Setting-driven hooks: pre → validate → save → post → async' },
                  { name: 'Document Templates', file: 'wc3-document-template', desc: 'Template-driven: role-based fields, scripts, denormalization' },
                  { name: 'Report & Document Output', file: 'wc3-report-output', desc: 'PDF / email / API / webhook / sync bundle' },
                  { name: 'Report Script Pipeline', file: 'wc3-report-script-pipeline', desc: 'Before (once) → During (per record) → After (once); unload + read_only' },
                  { name: 'Data Sync', file: 'wc3-sync', desc: 'Connection model: bundles, field maps, conflict resolution' },
                  { name: 'Document Library', file: 'wc3-document-library', desc: 'Upload → local → Alice Celery → secure cloud transfer' },
                  { name: 'Celery Pipeline', file: 'wc3-celery-pipeline', desc: 'All 29 background tasks by domain and schedule' },
                  { name: 'Data Conversion Pipeline', file: 'wc3-data-conversion-pipeline', desc: 'External file → Alice/Claude → DynamicCatalogs → bundle → sync' },
                  { name: 'Products Item Support', file: 'wc3-products-item-support', desc: '19 models, 13 service modules — pricing, inventory, BOM, serial, variants' },
                  { name: 'Pending Records Intelligence', file: 'wc3-pending-records', desc: 'Intent → archive → trend/cycle/volatility/cash flow analysis' },
                  { name: 'Request Security Pipeline', file: 'wc3-request-security', desc: 'JSON-by-default, WriteGate, Demo Read-Only — three middleware layers' },
                ]},
              ].map((section) => (
                <div key={section.title} className="mb-3">
                  <h4 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">{section.title}</h4>
                  <table className="w-full text-xs">
                    <tbody>
                      {section.charts.map((chart) => (
                        <tr key={chart.file} className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                          <td className="py-1.5 pr-3">
                            <a href={`/static/training/flowcharts/${chart.file}.pdf`} target="_blank" rel="noopener noreferrer"
                               className="text-indigo-600 dark:text-indigo-400 hover:underline font-medium">
                              {chart.name}
                            </a>
                          </td>
                          <td className="py-1.5 text-gray-500 dark:text-gray-400">{chart.desc}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
              <div className="mt-3 pt-3 border-t border-indigo-100 dark:border-indigo-900 text-[10px] text-gray-400 dark:text-gray-600">
                Source: <code>readmes/charts/flowcharts/</code> (DOT + PDF) &middot; Static: <code>/static/training/flowcharts/</code> &middot; Derived from WC2 WebClerkComExFlowCharts.pdf + Miro boards
              </div>
            </div>
          </details>

          {/* ── Training Documents ── */}
          {trainingDocs.map((doc: any) => (
            <details key={doc.id} className="border border-gray-200 dark:border-gray-700 rounded-lg">
              <summary className="p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
                <span className="text-sm font-medium text-gray-800 dark:text-gray-200">{doc.name}</span>
                {doc.description && <span className="ml-2 text-xs text-gray-500">{doc.description}</span>}
              </summary>
              <div className="p-4 border-t border-gray-200 dark:border-gray-700 prose prose-sm dark:prose-invert max-w-none">
                <pre className="whitespace-pre-wrap text-xs text-gray-700 dark:text-gray-300">{doc.body}</pre>
              </div>
            </details>
          ))}
        </div>
      )}

      {/* ═══ System Health ═══ */}
      {activeTab === 'health' && (
        <div className="grid grid-cols-2 gap-4">
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">Console Health</h3>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between"><span>Total entries</span><span>{consoleSummary?.total || 0}</span></div>
              <div className="flex justify-between text-red-500"><span>Errors</span><span>{consoleSummary?.errors || 0}</span></div>
              <div className="flex justify-between text-yellow-600"><span>Warnings</span><span>{consoleSummary?.warns || 0}</span></div>
              <div className="flex justify-between"><span>Capture</span><span>{captureActive ? 'Active' : 'Stopped'}</span></div>
            </div>
          </div>
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">Last 5 Console Events</h3>
            <div className="space-y-1 text-[10px] font-mono">
              {(consoleSummary?.last5 || []).map((e: ConsoleEntry, i: number) => (
                <div key={i} className={e.level === 'error' ? 'text-red-500' : e.level === 'warn' ? 'text-yellow-600' : 'text-gray-500'}>
                  {e.args.join(' ').slice(0, 100)}
                </div>
              ))}
            </div>
          </div>
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">Open Actions</h3>
            <div className="text-2xl font-bold text-blue-600">{actions.length}</div>
            <div className="text-xs text-gray-500">assigned to you</div>
          </div>
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">Training Progress</h3>
            <div className="text-2xl font-bold text-green-600">{trainingDocs.length}</div>
            <div className="text-xs text-gray-500">documents available</div>
          </div>
        </div>
      )}

      {/* ═══ LLM Config ═══ */}
      {activeTab === 'llm' && llmConfig && (
        <div className="space-y-4">
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-4">Alice LLM Configuration</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Provider</label>
                <select value={llmConfig.provider || 'ollama'} onChange={(e) => setLlmConfig({ ...llmConfig, provider: e.target.value })}
                  className="w-full px-3 py-2 text-sm rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800">
                  <option value="ollama">Ollama (Local)</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="custom">Custom Endpoint</option>
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Model</label>
                <input type="text" value={llmConfig.model || ''} onChange={(e) => setLlmConfig({ ...llmConfig, model: e.target.value })}
                  className="w-full px-3 py-2 text-sm rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800" placeholder="allie:latest" />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Endpoint URL</label>
                <input type="text" value={llmConfig.endpoint || ''} onChange={(e) => setLlmConfig({ ...llmConfig, endpoint: e.target.value })}
                  className="w-full px-3 py-2 text-sm rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800" placeholder="http://localhost:11434" />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Temperature</label>
                <input type="number" step="0.1" min="0" max="2" value={llmConfig.temperature ?? 0.7} onChange={(e) => setLlmConfig({ ...llmConfig, temperature: parseFloat(e.target.value) })}
                  className="w-full px-3 py-2 text-sm rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800" />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Max Tokens</label>
                <input type="number" value={llmConfig.max_tokens ?? 2000} onChange={(e) => setLlmConfig({ ...llmConfig, max_tokens: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 text-sm rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800" />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">API Key (if required)</label>
                <input type="password" value={llmConfig.api_key || ''} onChange={(e) => setLlmConfig({ ...llmConfig, api_key: e.target.value })}
                  className="w-full px-3 py-2 text-sm rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800" placeholder="Leave blank for local models" />
              </div>
              <div className="col-span-2">
                <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">System Prompt</label>
                <textarea value={llmConfig.system_prompt || ''} onChange={(e) => setLlmConfig({ ...llmConfig, system_prompt: e.target.value })}
                  rows={4} className="w-full px-3 py-2 text-sm rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800" />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={async () => {
                setLlmSaving(true);
                try {
                  const { default: apiClient } = await import('@/api/axios');
                  const existing = await getRecords('setting', { name: 'alice_llm_config', purpose: 'wc:coaching' }) as any;
                  const existingRec = (existing?.results || [])[0];
                  await apiClient.post('/wcapi/save/', {
                    model_name: 'setting', id: existingRec?.id,
                    name: 'alice_llm_config', purpose: 'wc:coaching',
                    data: llmConfig,
                  });
                  alert('LLM configuration saved.');
                } catch { alert('Failed to save LLM config.'); }
                finally { setLlmSaving(false); }
              }}
                disabled={llmSaving}
                className="px-4 py-2 text-sm font-medium rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50">
                {llmSaving ? 'Saving...' : 'Save Configuration'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ Help Sections — Document records loaded on expand ═══ */}
      <div className="mt-8 space-y-2">
        <h3 className="text-sm font-bold text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-2">Reference</h3>
        <DocSection ida="HELP-SEARCH" title="How Search Works"
          subtitle="FTS, fragments, fuzzy matching, saved searches, RESTful range queries" />
        <DocSection ida="HELP-REPORTS" title="Reports & Saved Searches"
          subtitle="Personal → shared → delivered; TallyMaster replacement" />
        <DocSection ida="HELP-IMPORT" title="Import Pipeline"
          subtitle="Connection lessons, column mapping, Athena review" />
        <DocSection ida="HELP-MCP" title="MCP Server Integration"
          subtitle="Connect external APIs to Alice" />
        <DocSection ida="HELP-EXTEND" title="How to Extend Alice"
          subtitle="Coaching tips, training docs, onboarding, field behaviors" />
        <DocSection ida="HELP-AGENTS" title="Agent Architecture"
          subtitle="Allie, Alice, Claude Code, Nora, Natalie, Noelle — who does what" />
        <DocSection ida="HELP-WCHQ-SYNC" title="WCHQ Sync Convention"
          subtitle="ida prefix wchq-*, sync levels, promotion path" />
        <DocSection ida="HELP-SESSION-20260808" title="WC2 Salvage Session (2026-08-08)"
          subtitle="8 deliverables: denorm stack, FTS, range queries, 3-tier search, WCHQ ida" />
      </div>

      {/* ═══ How to Extend Alice (legacy inline — will migrate to Document) ═══ */}
      <div className="mt-8 border border-gray-200 dark:border-gray-700 rounded-lg p-5 bg-gray-50 dark:bg-gray-800">
        <h3 className="text-sm font-bold text-blue-600 dark:text-blue-400 mb-3">How to Extend Alice</h3>
        <div className="text-xs text-gray-600 dark:text-gray-400 space-y-2">
          <p><strong>Add coaching tips:</strong> Create Setting records with purpose="wc:coaching" and parent_model set to any model. Alice will show the tips when users work with that model. Tips include field_help, action guides, warnings, and code examples.</p>
          <p><strong>Submit training documents:</strong> Create Document records with model_name="system" and status="published". They appear in the Training tab. Submit useful documents for bonus credit via the Submit for Bonus page — Alice tracks adoption.</p>
          <p><strong>Create onboarding actions:</strong> Create Action records with project_name="Alice Onboarding". New users see these as their getting-started checklist.</p>
          <p><strong>Teach Alice field behaviors:</strong> Update the field_access Setting for any model to add field_behaviors — Alice uses these to know which fields are emails (mailto), phones (tel), addresses (map), selects, lookups, etc.</p>
          <p><strong>Improve column widths:</strong> Alice watches what column widths users set and refines her recommendations. The column_widths Setting (purpose="wc:coaching") is synced from WCHQ.</p>
          <p><strong>Configure her LLM:</strong> Use the LLM Config tab to set Alice's AI provider, model, endpoint, and system prompt. Local Ollama models work offline. Cloud providers (OpenAI, Anthropic) need API keys.</p>
          <p><strong>Ask Alice questions:</strong> Use the "Ask Alice" input below. Questions are saved as pending items. Alice reviews and responds during her coaching cycle. Over time, she learns what users need help with.</p>
          <p><strong>Capture console logs:</strong> Click "Start Capture" to log browser console output. Click "Send to Alice" to share errors and warnings. Alice uses this to identify common problems and coach proactively.</p>
          <p><strong>Connect external APIs via MCP:</strong> Alice can connect to external services through MCP (Model Context Protocol) servers. See the MCP guide below.</p>
        </div>
      </div>

      {/* ═══ MCP Server Guide ═══ */}
      <div className="mt-4 border border-gray-200 dark:border-gray-700 rounded-lg p-5">
        <details>
          <summary className="text-sm font-bold text-purple-600 dark:text-purple-400 cursor-pointer">MCP Server Integration Guide — Connect External APIs to Alice</summary>
          <div className="mt-4 text-xs text-gray-600 dark:text-gray-400 space-y-3">
            <p>MCP (Model Context Protocol) lets Alice and Claude Code connect to external APIs as tool providers. Each MCP server exposes tools that the LLM can call — like querying a database, sending an email, or checking inventory from a third-party system.</p>

            <h4 className="font-bold text-gray-800 dark:text-gray-200 mt-4">1. What is an MCP Server?</h4>
            <p>An MCP server is a small program that speaks the MCP protocol (JSON-RPC over stdio or HTTP). It advertises tools (functions) that an LLM can call. WebClerk already has one: <code>scripts/wc_mcp_server.py</code> — it exposes wcapi as tools Alice can use.</p>

            <h4 className="font-bold text-gray-800 dark:text-gray-200 mt-4">2. How to Create an MCP Server for Your API</h4>
            <pre className="bg-gray-100 dark:bg-gray-900 p-3 rounded text-[10px] overflow-auto">{`# my_api_mcp.py — MCP server for your external API
import json, sys

def handle_request(request):
    method = request.get("method")

    if method == "tools/list":
        return {"tools": [
            {"name": "check_shipping_rate",
             "description": "Get shipping rate for a package",
             "inputSchema": {
                 "type": "object",
                 "properties": {
                     "weight_lbs": {"type": "number"},
                     "zip_from": {"type": "string"},
                     "zip_to": {"type": "string"},
                 },
                 "required": ["weight_lbs", "zip_from", "zip_to"]
             }},
        ]}

    if method == "tools/call":
        tool = request["params"]["name"]
        args = request["params"]["arguments"]
        if tool == "check_shipping_rate":
            # Call your actual API here
            rate = call_shipping_api(args["weight_lbs"],
                                     args["zip_from"],
                                     args["zip_to"])
            return {"content": [{"type": "text",
                                 "text": json.dumps(rate)}]}

# Main loop — reads JSON-RPC from stdin, writes to stdout
for line in sys.stdin:
    request = json.loads(line)
    response = handle_request(request)
    response["id"] = request.get("id")
    sys.stdout.write(json.dumps(response) + "\\n")
    sys.stdout.flush()`}</pre>

            <h4 className="font-bold text-gray-800 dark:text-gray-200 mt-4">3. Register in Claude Code Settings</h4>
            <pre className="bg-gray-100 dark:bg-gray-900 p-3 rounded text-[10px] overflow-auto">{`// ~/.claude/settings.json
{
  "mcpServers": {
    "shipping": {
      "command": "python3",
      "args": ["/path/to/my_api_mcp.py"],
      "env": {"API_KEY": "your-key-here"}
    },
    "webclerk": {
      "command": "python3",
      "args": ["/path/to/scripts/wc_mcp_server.py"]
    }
  }
}`}</pre>

            <h4 className="font-bold text-gray-800 dark:text-gray-200 mt-4">4. Common API Integrations</h4>
            <div className="grid grid-cols-2 gap-2 mt-2">
              <div className="border border-gray-200 dark:border-gray-700 rounded p-2">
                <div className="font-semibold text-gray-700 dark:text-gray-300">Tax APIs</div>
                <div className="text-[10px] text-gray-500">Avalara, TaxJar — calculate sales tax by jurisdiction. Create MCP server that wraps their REST API.</div>
              </div>
              <div className="border border-gray-200 dark:border-gray-700 rounded p-2">
                <div className="font-semibold text-gray-700 dark:text-gray-300">Shipping APIs</div>
                <div className="text-[10px] text-gray-500">UPS, FedEx, USPS — get rates, create labels, track packages. One MCP server per carrier or unified.</div>
              </div>
              <div className="border border-gray-200 dark:border-gray-700 rounded p-2">
                <div className="font-semibold text-gray-700 dark:text-gray-300">Payment Gateways</div>
                <div className="text-[10px] text-gray-500">Stripe, PayPal — process payments, check status. MCP server wraps their SDK.</div>
              </div>
              <div className="border border-gray-200 dark:border-gray-700 rounded p-2">
                <div className="font-semibold text-gray-700 dark:text-gray-300">Time Tracking</div>
                <div className="text-[10px] text-gray-500">Toggl, Harvest, Clockify — pull time entries for work orders. Replaces built-in time tracking (GAP-13).</div>
              </div>
              <div className="border border-gray-200 dark:border-gray-700 rounded p-2">
                <div className="font-semibold text-gray-700 dark:text-gray-300">Email/SMS</div>
                <div className="text-[10px] text-gray-500">SendGrid, Twilio — send notifications, order confirmations. MCP server wraps their API.</div>
              </div>
              <div className="border border-gray-200 dark:border-gray-700 rounded p-2">
                <div className="font-semibold text-gray-700 dark:text-gray-300">Currency Rates</div>
                <div className="text-[10px] text-gray-500">Open Exchange Rates, Fixer — live exchange rates for multi-currency transactions.</div>
              </div>
            </div>

            <h4 className="font-bold text-gray-800 dark:text-gray-200 mt-4">5. WebClerk MCP Server (Already Built)</h4>
            <p>The existing <code>scripts/wc_mcp_server.py</code> exposes these tools to Claude Code and Allie:</p>
            <ul className="list-disc pl-5 space-y-1">
              <li><code>wc_search</code> — search any model via wcapi</li>
              <li><code>wc_get_item</code> / <code>wc_get_contact</code> / <code>wc_get_invoice</code> — get specific records</li>
              <li><code>wc_add_note</code> — add notes to Alice's log/pending queue</li>
              <li><code>wc_jpods_price</code> / <code>wc_jpods_travel</code> — JPods integration</li>
            </ul>
            <p className="mt-2">To add a new tool: add a handler function in wc_mcp_server.py, register it in the tools/list response, and handle it in tools/call. All data flows through wcapi — the single gate.</p>

            <h4 className="font-bold text-gray-800 dark:text-gray-200 mt-4">6. Alice Using MCP Tools</h4>
            <p>When Alice has her own LLM (configured in LLM Config tab), she can call MCP tools to:</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>Check shipping rates before confirming an order</li>
              <li>Calculate tax for a customer's jurisdiction</li>
              <li>Pull time entries from Toggl for work order costing</li>
              <li>Send order confirmation emails via SendGrid</li>
              <li>Convert currency amounts using live exchange rates</li>
              <li>Look up product data from vendor catalogs via DynamicCatalogs</li>
            </ul>
            <p className="mt-2">Each MCP server is a Connection record in WebClerk — syncable from WCHQ, auditable, and governed by the same RBAC rules as everything else.</p>

            <h4 className="font-bold text-gray-800 dark:text-gray-200 mt-4">7. Agent-to-Agent Communication via MCP</h4>
            <p>MCP is also how our agents talk to each other. Each agent runs its own MCP server and can call tools on other agents:</p>
            <div className="grid grid-cols-1 gap-2 mt-2">
              <div className="border border-gray-200 dark:border-gray-700 rounded p-3">
                <div className="font-semibold text-gray-700 dark:text-gray-300 mb-1">Current Agent MCP Servers</div>
                <table className="w-full text-[10px]">
                  <thead><tr className="text-left text-gray-500"><th className="py-1 pr-3">Agent</th><th className="py-1 pr-3">MCP Server</th><th className="py-1">Tools Exposed</th></tr></thead>
                  <tbody>
                    <tr><td className="py-1 pr-3 font-medium">Allie</td><td className="py-1 pr-3"><code>scripts/allie_mcp_server.py</code></td><td className="py-1">ask_allie, teach_allie, allie_recall, allie_flag</td></tr>
                    <tr><td className="py-1 pr-3 font-medium">Alice (WebClerk)</td><td className="py-1 pr-3"><code>scripts/wc_mcp_server.py</code></td><td className="py-1">wc_search, wc_get_item, wc_get_contact, wc_add_note, wc_get_invoice</td></tr>
                    <tr><td className="py-1 pr-3 font-medium">Claude Code</td><td className="py-1 pr-3">Built-in (Anthropic)</td><td className="py-1">Read, Write, Edit, Bash, Grep, Glob — full dev tools</td></tr>
                  </tbody>
                </table>
              </div>

              <div className="border border-gray-200 dark:border-gray-700 rounded p-3">
                <div className="font-semibold text-gray-700 dark:text-gray-300 mb-1">How Agents Communicate</div>
                <pre className="bg-gray-100 dark:bg-gray-900 p-2 rounded text-[10px] overflow-auto mt-1">{`Claude Code ──MCP──► Allie (ask_allie: "What do you know about X?")
                          Allie responds with cross-domain context

Claude Code ──MCP──► Alice (wc_add_note: "GAP-01 completed")
                          Alice logs it, creates action records

Alice ──wcapi──► WebClerk DB (all CRUD through single gate)

Allie ──nightly──► reads process/inbox/, sessions/, retrospections/
                   writes thoughts/YYYY-MM-DD-reflect.md
                   promotes patterns to Understanding entries`}</pre>
              </div>

              <div className="border border-gray-200 dark:border-gray-700 rounded p-3">
                <div className="font-semibold text-gray-700 dark:text-gray-300 mb-1">Adding a New Agent</div>
                <div className="text-[10px] space-y-1">
                  <p><strong>Step 1:</strong> Create an MCP server script (Python) that exposes the agent's tools.</p>
                  <p><strong>Step 2:</strong> Register it in <code>~/.claude/settings.json</code> under <code>mcpServers</code>.</p>
                  <p><strong>Step 3:</strong> Create a facet file at <code>~/Allie/facets/&lt;agent_name&gt;/facet.json</code> — this is the agent's persistent memory.</p>
                  <p><strong>Step 4:</strong> Add the agent to <code>readmes/agents/README.md</code> with responsibilities, decisions, and interfaces.</p>
                  <p><strong>Step 5:</strong> All data operations go through wcapi — the agent's MCP server calls wcapi, never the database directly.</p>
                </div>
              </div>

              <div className="border border-gray-200 dark:border-gray-700 rounded p-3">
                <div className="font-semibold text-gray-700 dark:text-gray-300 mb-1">Example: Adding a Shipping Agent (Natalie)</div>
                <pre className="bg-gray-100 dark:bg-gray-900 p-2 rounded text-[10px] overflow-auto mt-1">{`# natalie_mcp_server.py — shipping & logistics agent
# Tools:
#   get_shipping_rates(origin_zip, dest_zip, weight)
#   create_shipment(order_id, carrier, service)
#   track_shipment(tracking_number)
#   estimate_delivery(order_id)
#
# Natalie calls:
#   UPS/FedEx/USPS APIs for rates and tracking
#   wcapi to read orders and update shipping status
#   Alice (wc_add_note) to log shipping events
#
# Register in settings.json:
#   "natalie": {"command": "python3", "args": ["natalie_mcp_server.py"]}
#
# Claude Code can then call:
#   mcp__natalie__get_shipping_rates({origin: "27601", dest: "10001", weight: 5})
#   mcp__natalie__create_shipment({order_id: 42, carrier: "ups", service: "ground"})`}</pre>
              </div>
            </div>

            <h4 className="font-bold text-gray-800 dark:text-gray-200 mt-4">8. The Agent Architecture</h4>
            <p>Each agent has a specific domain. They coordinate through MCP tools and wcapi notes — never by sharing database connections or bypassing the single gate.</p>
            <pre className="bg-gray-100 dark:bg-gray-900 p-2 rounded text-[10px] overflow-auto mt-1">{`┌─────────────┐    MCP     ┌──────────────┐    MCP     ┌─────────────┐
│  Claude Code │◄─────────►│    Allie     │◄─────────►│   Alice     │
│  (dev tools) │           │ (cross-domain│           │ (commerce   │
│              │           │  memory)     │           │  coaching)  │
└──────────────┘           └──────────────┘           └──────┬──────┘
                                                            │ wcapi
                                                     ┌──────▼──────┐
                                                     │  WebClerk   │
                                                     │  Database   │
                                                     └──────┬──────┘
                                                            │ sync
                                                     ┌──────▼──────┐
                                                     │    WCHQ     │
                                                     │  (cloud)    │
                                                     └─────────────┘`}</pre>
            <p className="mt-2">To add agents for JPods (Nora, Natalie, Noelle, Sally), follow the same pattern. Each gets an MCP server, a facet for memory, and communicates through wcapi.</p>
          </div>
        </details>
      </div>

      {/* ═══ Ask Alice ═══ */}
      <div className="mt-8 border-t border-gray-200 dark:border-gray-700 pt-4">
        <div className="flex gap-2">
          <input type="text" placeholder="Ask Alice anything..."
            value={askText} onChange={(e) => setAskText(e.target.value)}
            onKeyDown={async (e) => {
              if (e.key === 'Enter' && askText.trim()) {
                try {
                  const { default: apiClient } = await import('@/api/axios');
                  await apiClient.post('/wcapi/save/', {
                    model_name: 'setting',
                    name: `Ask Alice: ${askText.slice(0, 200)}`,
                    purpose: 'alice_pending',
                    data: { question: askText, user: user?.email, dt: Date.now() },
                  });
                  setAskText('');
                  alert('Question sent to Alice. She will respond in her next review.');
                } catch { alert('Failed to send question.'); }
              }
            }}
            className="flex-1 px-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
          />
          <button onClick={async () => {
            if (!askText.trim()) return;
            try {
              const { default: apiClient } = await import('@/api/axios');
              await apiClient.post('/wcapi/save/', {
                model_name: 'setting',
                name: `Ask Alice: ${askText.slice(0, 200)}`,
                purpose: 'alice_pending',
                data: { question: askText, user: user?.email, dt: Date.now() },
              });
              setAskText('');
              alert('Question sent to Alice.');
            } catch { alert('Failed to send.'); }
          }}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700">
            Ask
          </button>
        </div>
        <p className="text-[10px] text-gray-400 mt-1">Questions are saved as pending items. Alice reviews and responds during her next coaching cycle.</p>
      </div>

      {/* ═══ Quiz ═══ */}
      {activeTab === 'quiz' && (
        <Suspense fallback={<div className="p-4 text-sm text-gray-500">Loading Quiz...</div>}>
          <AliceQuiz />
        </Suspense>
      )}



      {/* ═══ Library ═══ */}
      {activeTab === 'library' && (
        <div className="p-4 space-y-4 text-sm">
          <h3 className="text-lg font-bold text-gray-800 dark:text-gray-200">Library Management</h3>
          <p className="text-gray-500 text-xs">
            Alice manages file uploads, local storage, and secure cloud transfer via Celery tasks.
            Flowchart: <code>readmes/flowcharts/wc3-document-library.dot</code>
          </p>

          {/* Upload */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <h4 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-3">Upload Files</h4>
            <div className="flex gap-2 items-center">
              <input type="file" multiple
                className="text-xs text-gray-600 dark:text-gray-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-blue-50 file:text-blue-700 dark:file:bg-blue-900/40 dark:file:text-blue-400 hover:file:bg-blue-100"
                onChange={async (e) => {
                  const files = e.target.files;
                  if (!files?.length) return;
                  try {
                    const { default: apiClient } = await import('@/api/axios');
                    for (const file of Array.from(files)) {
                      const formData = new FormData();
                      formData.append('file', file);
                      formData.append('purpose', 'attachment');
                      await apiClient.post('/wcapi/upload/', formData, {
                        headers: { 'Content-Type': 'multipart/form-data' },
                      });
                    }
                    alert(`${files.length} file(s) uploaded successfully.`);
                  } catch {
                    alert('Upload failed.');
                  }
                }}
              />
            </div>
            <p className="mt-2 text-[10px] text-gray-400">
              Photos, videos, PDFs, spreadsheets. Each file becomes a Document record.
              Small files (&lt;5MB) stored inline. Larger files stored on filesystem.
            </p>
          </div>

          {/* Celery Tasks */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <h4 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-3">Alice Celery Tasks — Library Pipeline</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {[
                { name: 'Virus Scan', beat: 'Every 1 min', desc: 'Scan new uploads. status → scanned or virus_detected.', status: 'active' },
                { name: 'Thumbnail Generation', beat: 'Every 1 min', desc: 'Generate 200×200 thumbnails for images and video first-frames.', status: 'active' },
                { name: 'Cloud Transfer', beat: 'Async', desc: 'Upload verified files to secure cloud library. Set path.remote_url.', status: 'active' },
                { name: 'Transfer Verify', beat: 'Every 2 min', desc: 'Checksum match: local == remote. Trigger cleanup on match.', status: 'active' },
                { name: 'Local Cleanup', beat: 'Async', desc: 'Delete local copy after verified transfer. status → archived.', status: 'active' },
                { name: 'Failed Monitor', beat: 'Every 5 min', desc: 'Find stuck transfers (> 2 hours). Retry or write FAULT file.', status: 'active' },
                { name: 'Dedup Scan', beat: 'Every 5 min', desc: 'Catch duplicates that slipped past upload-time checksum check.', status: 'active' },
              ].map((task) => (
                <div key={task.name} className="border border-gray-200 dark:border-gray-700 rounded-lg p-3 bg-white dark:bg-gray-800">
                  <div className="flex justify-between items-start mb-1">
                    <span className="font-semibold text-gray-800 dark:text-gray-200 text-xs">{task.name}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300">
                      {task.beat}
                    </span>
                  </div>
                  <p className="text-[10px] text-gray-500 dark:text-gray-400">{task.desc}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Status Lifecycle */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <h4 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-3">Document Status Lifecycle</h4>
            <div className="flex items-center gap-1 text-xs flex-wrap">
              {['uploaded', 'scanned', 'transferring', 'archived'].map((step, i) => (
                <React.Fragment key={step}>
                  {i > 0 && <span className="text-gray-300 dark:text-gray-600">→</span>}
                  <span className="px-3 py-1 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400 font-medium">
                    {step}
                  </span>
                </React.Fragment>
              ))}
              <span className="ml-4 text-gray-300 dark:text-gray-600">|</span>
              <span className="px-3 py-1 rounded-full bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400 font-medium ml-2">
                virus_detected
              </span>
            </div>
          </div>

          {/* Sovereignty note */}
          <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
            <p className="text-xs text-green-700 dark:text-green-300">
              <strong>Sovereignty:</strong> Files belong to the user, not WebClerk. Cloud transfer is convenience, not dependency.
              Local-only mode works indefinitely. Users can export or permanently delete files at any time.
              No vendor lock-in. Encrypted at rest. Signed URLs for access — no permanent public links.
            </p>
          </div>

          {/* Parent linkage */}
          <details className="border border-gray-200 dark:border-gray-700 rounded-lg">
            <summary className="p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">File Attachments — Parent Linkage</span>
            </summary>
            <div className="p-4 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400">
              <p className="mb-2">Files attach to any WC3 model through <code>refs.parent</code>:</p>
              <div className="grid grid-cols-2 gap-2 mt-2">
                {[
                  { model: 'Order', examples: 'Custom specs, signed POs' },
                  { model: 'Invoice', examples: 'Proof of delivery, signed receipts' },
                  { model: 'Contact', examples: 'Profile photos, business cards, ID scans' },
                  { model: 'Item', examples: 'Product photos, spec sheets, certificates' },
                  { model: 'Action', examples: 'Task evidence, inspection photos, site photos' },
                  { model: 'Project', examples: 'Plans, drawings, progress photos' },
                ].map((p) => (
                  <div key={p.model} className="border border-gray-200 dark:border-gray-700 rounded p-2">
                    <span className="font-semibold text-gray-700 dark:text-gray-300">{p.model}</span>
                    <span className="ml-2 text-gray-400">{p.examples}</span>
                  </div>
                ))}
              </div>
            </div>
          </details>
        </div>
      )}

      {/* ═══ Reports ═══ */}
      {activeTab === 'reports' && (
        <div className="p-4 space-y-4 text-sm">
          <h3 className="text-lg font-bold text-gray-800 dark:text-gray-200">Reports — MVP Print Templates</h3>
          <p className="text-gray-500 text-xs">
            13 printable report templates. Edit visually at <a href="/report-designer" className="text-blue-500 hover:underline font-medium">/report-designer</a>.
            Field registry API: <code className="text-xs bg-gray-100 dark:bg-gray-800 px-1 rounded">/wcapi/_report_fields/?model=order</code>
          </p>

          <div className="flex gap-3">
            <a href="/report-designer" className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-xs font-medium no-underline">
              Open Report Designer
            </a>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mt-4">
            {[
              { name: 'Invoice', model: 'invoice', cat: 'customer_facing', desc: 'Line items, totals, payment terms' },
              { name: 'Credit Memo', model: 'invoice', cat: 'customer_facing', desc: 'Reversal document with reason code' },
              { name: 'Statement', model: 'customer', cat: 'statement', desc: 'Account statement with aging buckets' },
              { name: 'Aging Report', model: 'customer', cat: 'report', desc: 'AR aging by customer (current/30/60/90+)' },
              { name: 'Order Confirmation', model: 'order', cat: 'customer_facing', desc: 'Order with line items and delivery terms' },
              { name: 'Pick Ticket', model: 'order', cat: 'operations', desc: 'Warehouse pick list with bin locations' },
              { name: 'Packing Slip', model: 'order', cat: 'operations', desc: 'Shipment list — items and quantities, no prices' },
              { name: 'Purchase Order', model: 'purchase', cat: 'vendor_facing', desc: 'Vendor-facing PO with costs' },
              { name: 'Receiving Report', model: 'purchase', cat: 'operations', desc: 'What arrived vs. what was ordered' },
              { name: 'Proposal', model: 'proposal', cat: 'customer_facing', desc: 'Quote with acceptance signature block' },
              { name: 'Requisition', model: 'requisition', cat: 'operations', desc: 'Internal purchase request with approvals' },
              { name: 'Work Order', model: 'workorder', cat: 'operations', desc: 'Job ticket with materials and labor' },
              { name: 'Payment Receipt', model: 'payment', cat: 'customer_facing', desc: 'Proof of payment with applied invoices' },
            ].map((r, i) => (
              <div key={i} className="border border-gray-200 dark:border-gray-700 rounded-lg p-3 hover:border-blue-300 dark:hover:border-blue-600 transition">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-gray-800 dark:text-gray-200">{r.name}</span>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded ${
                    r.cat === 'customer_facing' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400'
                    : r.cat === 'operations' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400'
                    : r.cat === 'vendor_facing' ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-400'
                    : r.cat === 'statement' ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400'
                    : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
                  }`}>{r.cat.replace('_', ' ')}</span>
                </div>
                <div className="text-[10px] text-gray-500 dark:text-gray-400">{r.model} &middot; {r.desc}</div>
              </div>
            ))}
          </div>

          <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg text-xs text-gray-600 dark:text-gray-400">
            <p className="font-medium text-gray-700 dark:text-gray-300 mb-1">How it works</p>
            <ul className="list-disc ml-4 space-y-1">
              <li>Templates stored in <code>Report.config.pdfme_template</code> as JSON</li>
              <li>Visual editor: drag fields, resize, snap to alignment guides</li>
              <li>Fields from 4 sources: direct, related models, JSON paths, line items</li>
              <li>Table schema for repeating line item panels (coming soon)</li>
              <li>Full readme: <code>readmes/topics/print/pdfme-template-system.md</code></li>
            </ul>
          </div>
        </div>
      )}

      {/* ═══ PDF Designer ═══ */}
      {activeTab === 'pdf-designer' && (
        <Suspense fallback={<div className="p-4 text-sm text-gray-500">Loading PDF Designer...</div>}>
          <div className="h-[70vh]">
            <PdfDesigner />
          </div>
        </Suspense>
      )}

      {/* ═══ Data Quality ═══ */}
      {activeTab === 'data-quality' && (
        <div className="p-4 space-y-4 text-sm">
          <h3 className="text-lg font-bold text-gray-800 dark:text-gray-200">Data Quality — Automated Tasks</h3>
          <p className="text-gray-500 text-xs">Three-tier processing: algorithms → Alice LLM → general LLM. Full readme: <code>readmes/topics/ai/alice-data-quality.md</code></p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[
              { name: 'Phone Normalization', desc: 'Strip to digits + country code. Display formatted per nation.', schedule: 'On import + weekly', tier: 1 },
              { name: 'Email Scrubbing', desc: 'Detect garbled emails, OCR errors, concatenated phone+email. Move invalid to config.scrubbed.', schedule: 'On import + weekly', tier: 1 },
              { name: 'Zip/Postal Formatting', desc: 'Normalize to digits (US) or standard format per country.', schedule: 'On import + weekly', tier: 1 },
              { name: 'Dedup Scan', desc: 'Find duplicate records by name, email, phone, or company. Score and group for review.', schedule: 'On import + monthly', tier: 1 },
              { name: 'Email Validation', desc: 'ZeroBounce or other provider — validate deliverability, set health_rating.', schedule: 'On demand + quarterly', tier: 1 },
              { name: 'Address Verification', desc: 'SmartyStreets/USPS — standardize and verify mailing addresses.', schedule: 'On demand', tier: 1 },
              { name: 'OCR Pattern Learning', desc: 'Learn card reader garble patterns from this installation\'s data.', schedule: 'After dedup merges', tier: 2 },
              { name: 'Company → Email Mapping', desc: 'Learn which email domain each company uses for smart dedup suggestions.', schedule: 'Nightly', tier: 2 },
              { name: 'Name Fuzzy Matching', desc: 'Bill/William, Bob/Robert, nicknames. Suggest merges Alice\'s LLM recognizes.', schedule: 'Monthly', tier: 2 },
              { name: 'Unknown Format Resolution', desc: 'New country formats, unknown domains. Calls general LLM when Alice is unsure.', schedule: 'On flag only', tier: 3 },
            ].map((task, i) => (
              <div key={i} className="border border-gray-200 dark:border-gray-700 rounded-lg p-3 bg-white dark:bg-gray-800">
                <div className="flex justify-between items-start mb-1">
                  <span className="font-semibold text-gray-800 dark:text-gray-200">{task.name}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                    task.tier === 1 ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' :
                    task.tier === 2 ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' :
                    'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300'
                  }`}>Tier {task.tier}</span>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{task.desc}</p>
                <div className="flex justify-between items-center">
                  <span className="text-[10px] text-gray-400">{task.schedule}</span>
                  <div className="flex gap-1">
                    <button className="text-[10px] px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200">Run Now</button>
                    <button className="text-[10px] px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200">History</button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <p className="text-xs text-yellow-700 dark:text-yellow-300">
              <strong>The rule:</strong> Tier 1 always runs silently. Tier 2 runs on what Tier 1 can't resolve. Tier 3 never runs without asking.
              Every transformation preserves the original in <code>config</code>. Nothing is lost. Every action is reversible.
            </p>
          </div>
        </div>
      )}

      {/* ═══ Import Data ═══ */}
      {activeTab === 'import' && (
        <div className="space-y-4">
          {/* ── How it works ── */}
          <div className="p-3 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg">
            <p className="text-xs text-indigo-700 dark:text-indigo-300">
              <strong>Import pipeline:</strong> Drop a file path below → Alice examines the data → maps columns using learned lessons → produces a bundle.json outside WC3 → Athena reviews for hidden harms → you sign off → bundle enters WC3 through the Connection sync pipeline. All transformation happens outside WC3. Alice gets smarter with each import via lessons stored on the Connection record.
            </p>
          </div>

          {/* ── File path input ── */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">1. Provide Data Source</h3>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="File path: /Users/bill/Downloads/acme-products.csv"
                value={importPath}
                onChange={(e) => setImportPath(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && importPath.trim()) {
                    setImportStatus('analyzing');
                    // TODO: Call Alice import analysis endpoint
                  }
                }}
                className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-indigo-400 outline-none"
              />
              <button
                onClick={() => {
                  if (importPath.trim()) {
                    setImportStatus('analyzing');
                    // TODO: Call Alice import analysis endpoint
                  }
                }}
                disabled={!importPath.trim() || importStatus === 'analyzing'}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {importStatus === 'analyzing' ? 'Analyzing...' : 'Analyze'}
              </button>
            </div>
            <p className="mt-1 text-[10px] text-gray-400">Supports: CSV, JSON, XML, TSV. Alice reads the file, never moves or modifies the original.</p>
          </div>

          {/* ── Status flow ── */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-3">Pipeline Status</h3>
            <div className="flex items-center gap-1 text-[10px]">
              {['idle', 'analyzing', 'preview', 'reviewing', 'ready'].map((step, i) => (
                <React.Fragment key={step}>
                  {i > 0 && <span className="text-gray-300 dark:text-gray-600">→</span>}
                  <span className={`px-2 py-1 rounded-full font-medium ${
                    importStatus === step
                      ? 'bg-indigo-600 text-white'
                      : ['idle', 'analyzing', 'preview', 'reviewing', 'ready'].indexOf(importStatus) > i
                        ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                        : 'bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-600'
                  }`}>
                    {step === 'idle' ? 'Waiting' :
                     step === 'analyzing' ? 'Alice Analyzing' :
                     step === 'preview' ? 'Preview & Map' :
                     step === 'reviewing' ? 'Athena Review' :
                     'Sign Off & Import'}
                  </span>
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* ── Preview (shown after analysis) ── */}
          {importStatus === 'preview' && importPreview && (
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 space-y-3">
              <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300">2. Preview & Column Mapping</h3>

              {/* Connection match */}
              {importConnection && (
                <div className="p-2 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded text-xs text-green-700 dark:text-green-300">
                  Found existing Connection: <strong>{importConnection.name}</strong> — {importConnection.lessons_count} lessons learned. Last import: {importConnection.last_import_dt || 'never'}
                </div>
              )}

              {/* Sample data */}
              <div className="overflow-x-auto">
                <table className="w-full text-[10px] border-collapse">
                  <thead>
                    <tr className="bg-gray-100 dark:bg-gray-800">
                      <th className="p-1 text-left font-bold text-gray-600 dark:text-gray-400">Source Column</th>
                      <th className="p-1 text-left font-bold text-gray-600 dark:text-gray-400">→ WC3 Field</th>
                      <th className="p-1 text-left font-bold text-gray-600 dark:text-gray-400">Sample</th>
                      <th className="p-1 text-left font-bold text-gray-600 dark:text-gray-400">Confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(importPreview.mappings || []).map((m: any, i: number) => (
                      <tr key={i} className="border-b border-gray-100 dark:border-gray-800">
                        <td className="p-1 font-mono">{m.source}</td>
                        <td className="p-1">
                          <input type="text" defaultValue={m.target}
                            className="w-full px-1 py-0.5 text-[10px] border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-800" />
                        </td>
                        <td className="p-1 text-gray-500 truncate max-w-[200px]">{m.sample}</td>
                        <td className="p-1">
                          <span className={`px-1 py-0.5 rounded text-[9px] font-bold ${
                            m.confidence > 0.8 ? 'bg-green-100 text-green-700' :
                            m.confidence > 0.5 ? 'bg-yellow-100 text-yellow-700' :
                            'bg-red-100 text-red-700'
                          }`}>{Math.round(m.confidence * 100)}%</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex gap-2">
                <button className="px-3 py-1.5 text-xs font-medium rounded-lg bg-indigo-600 text-white hover:bg-indigo-700"
                  onClick={() => setImportStatus('reviewing')}>
                  Confirm Mappings → Athena Review
                </button>
                <button className="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300"
                  onClick={() => { setImportStatus('idle'); setImportPreview(null); }}>
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* ── Athena Review (shown after mapping confirmed) ── */}
          {importStatus === 'reviewing' && (
            <div className="border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 space-y-3 bg-yellow-50 dark:bg-yellow-900/10">
              <h3 className="text-sm font-bold text-yellow-700 dark:text-yellow-300">3. Athena Security Review</h3>
              <p className="text-xs text-yellow-600 dark:text-yellow-400">
                Athena inspects the bundle for hidden harms: malicious formulas, SQL injection in field values,
                PII in unexpected columns, data that contradicts existing records, suspicious patterns
                (e.g., all prices set to $0.01), embedded scripts, encoding attacks.
              </p>
              <div className="flex items-center gap-2">
                <div className="animate-spin h-4 w-4 border-2 border-yellow-600 border-t-transparent rounded-full" />
                <span className="text-xs text-yellow-700 dark:text-yellow-300">Athena reviewing bundle...</span>
              </div>
            </div>
          )}

          {/* ── Sign-off (shown after Athena clears) ── */}
          {importStatus === 'ready' && importBundle && (
            <div className="border border-green-200 dark:border-green-800 rounded-lg p-4 space-y-3 bg-green-50 dark:bg-green-900/10">
              <h3 className="text-sm font-bold text-green-700 dark:text-green-300">4. Sign Off & Import</h3>

              {/* Bundle header summary */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div><span className="text-gray-500">Source:</span> <strong>{importBundle.header?.source_name}</strong></div>
                <div><span className="text-gray-500">File:</span> <strong>{importBundle.header?.source_file}</strong></div>
                <div><span className="text-gray-500">Records:</span> <strong>{importBundle.header?.record_count}</strong></div>
                <div><span className="text-gray-500">Skipped:</span> <strong>{importBundle.header?.skipped_count}</strong></div>
                <div><span className="text-gray-500">Errors:</span> <strong>{importBundle.header?.error_count}</strong></div>
                <div><span className="text-gray-500">Target model:</span> <strong>{importBundle.header?.model_target}</strong></div>
                <div><span className="text-gray-500">Trust level:</span> <strong>{importBundle.header?.trust_level}</strong></div>
                <div><span className="text-gray-500">Athena:</span>
                  <strong className={importBundle.header?.athena_approved ? 'text-green-600' : 'text-red-600'}>
                    {importBundle.header?.athena_approved ? ' Cleared' : ' Flagged'}
                  </strong>
                </div>
                <div><span className="text-gray-500">Prepared by:</span> <strong>{importBundle.header?.prepared_by}</strong></div>
                <div><span className="text-gray-500">Responsible:</span> <strong>{importBundle.header?.responsible_person}</strong></div>
              </div>

              {/* Athena findings */}
              {(importBundle.header?.athena_findings || []).length > 0 && (
                <div className="p-2 bg-yellow-100 dark:bg-yellow-900/30 rounded text-xs">
                  <strong className="text-yellow-700">Athena findings:</strong>
                  <ul className="mt-1 list-disc list-inside text-yellow-600">
                    {importBundle.header.athena_findings.map((f: string, i: number) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex gap-2">
                <button className="px-4 py-2 text-sm font-medium rounded-lg bg-green-600 text-white hover:bg-green-700"
                  onClick={() => {
                    // TODO: POST bundle to /wcapi/sync/receive/
                    setImportStatus('idle');
                    setImportPreview(null);
                    setImportBundle(null);
                    setImportPath('');
                  }}>
                  Sign Off & Import
                </button>
                <button className="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-100 text-red-700 hover:bg-red-200"
                  onClick={() => { setImportStatus('idle'); setImportBundle(null); }}>
                  Reject
                </button>
              </div>

              <p className="text-[10px] text-gray-400">
                Signing off records your name, timestamp, and Athena's review on the bundle header.
                The bundle is processed through the Connection's sync pipeline. Alice saves confirmed mappings as lessons.
              </p>
            </div>
          )}

          {/* ── Error state ── */}
          {importStatus === 'error' && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-xs text-red-700 dark:text-red-300">
                Import failed. Check the file path and format. Alice will log the error for review.
              </p>
              <button className="mt-2 px-3 py-1 text-xs rounded bg-red-100 text-red-700 hover:bg-red-200"
                onClick={() => setImportStatus('idle')}>Try Again</button>
            </div>
          )}

          {/* ── Lessons & instructions ── */}
          <details className="border border-gray-200 dark:border-gray-700 rounded-lg">
            <summary className="p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Connection Lessons & Instructions</span>
              <span className="ml-2 text-xs text-gray-400">What Alice has learned per source</span>
            </summary>
            <div className="p-4 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400">
              <p className="mb-2">Each Connection record with <code>channel: "import"</code> stores:</p>
              <ul className="list-disc list-inside space-y-1">
                <li><strong>config.import_config.lessons[]</strong> — column mappings Alice learned from successful imports</li>
                <li><strong>config.import_config.user_instructions[]</strong> — rules you gave Alice (e.g., "skip blank UPC rows")</li>
                <li><strong>config.import_config.column_map</strong> — confirmed source→field mappings</li>
                <li><strong>config.import_config.skip_rules</strong> — conditions that skip rows</li>
              </ul>
              <p className="mt-2">Alice reads these before every import. She gets smarter per source. View/edit in databrowser → Connection.</p>
            </div>
          </details>
        </div>
      )}

      {/* ═══ Readmes ═══ */}
      {activeTab === 'readmes' && (
        <div className="space-y-4">
          <div className="p-3 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg">
            <p className="text-xs text-gray-600 dark:text-gray-400">
              <strong>System documentation index.</strong> All readmes from <code>readmes/</code> — architecture, operations, AI, transactions, infrastructure.
              Click any title to expand and read the content.
            </p>
          </div>
          <div className="max-h-[70vh] overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-lg">
            {[
              { section: 'Architecture & Core', docs: [
                { ida: 'README-ARCH', title: 'Architecture Overview', desc: 'Models, API patterns, key principles' },
                { ida: 'README-WCAPI', title: 'WCAPI Gateway', desc: 'Unified API — all CRUD flows through wcapi' },
                { ida: 'README-WCAPI-USAGE', title: 'WCAPI Usage Guide', desc: 'Query, save, manage endpoint patterns' },
                { ida: 'README-API-CONVENTIONS', title: 'API Conventions', desc: 'Universal request/response standards' },
                { ida: 'README-MODEL-REGISTRY', title: 'Model Registry', desc: '61 models — canonical names and table map' },
                { ida: 'README-SAVE-PIPELINE', title: 'Save Pipeline', desc: 'Setting-driven hooks: pre → validate → save → post → async' },
                { ida: 'README-JSON-ENVELOPE', title: 'JSON Envelope Policy', desc: '.prefs, .metadata, .refs on every record' },
                { ida: 'README-PYDANTIC', title: 'Pydantic Envelope Schemas', desc: 'Typed JSON at every layer' },
                { ida: 'README-DATA-DRIVEN-UI', title: 'Data-Driven UI', desc: 'DynamicDetail + ui.json + Settings — 45K→2K lines' },
                { ida: 'README-RBAC', title: 'RBAC & Field Access', desc: 'Role → Setting → what each user sees and edits' },
                { ida: 'README-DUAL-HOSTING', title: 'Dual Hosting Model', desc: 'Desktop + cloud, conflict resolution via uuid/dt/pending' },
                { ida: 'README-DESKTOP-LINEAGE', title: 'Desktop Hosting Lineage', desc: 'Origin in Desktop Hosting (Wiley 2002)' },
              ]},
              { section: 'Transactions', docs: [
                { ida: 'README-TRANSACTION-CALC', title: 'Transaction Calculations', desc: 'Price cascade, line extensions, totals, tax, GL' },
                { ida: 'README-TRANSACTION-SAVE', title: 'Transaction Save Patterns', desc: 'How orders, invoices, purchases save and calculate' },
                { ida: 'README-ORDER-INVOICE', title: 'Order to Invoice Flow', desc: 'Customer → verify → order → production → invoice' },
                { ida: 'README-PAYMENT-GL', title: 'Payment & GL', desc: 'Payment → journals → GL; aging; erosion detection' },
                { ida: 'README-PENDING', title: 'Pending Policy', desc: 'When changes queue vs apply immediately' },
                { ida: 'README-TERMS-LEDGERS', title: 'Terms & Ledgers', desc: 'Payment terms, aging buckets, ledger entries' },
                { ida: 'README-COMMISSION', title: 'Commission System', desc: 'Rep rate × item commissionableness → line commission' },
                { ida: 'README-EROSION', title: 'Erosion Tracking', desc: 'Detect margin erosion across time and customers' },
              ]},
              { section: 'Reports & Output', docs: [
                { ida: 'README-REPORTS-DASHBOARDS', title: 'Reports & Dashboards', desc: '35 standard reports, 7 dashboards, print template system' },
                { ida: 'README-REPORT-SCRIPTS', title: 'Report Script Pipeline', desc: 'Before/During/After — three-phase record processing' },
                { ida: 'README-REPORT-OUTPUT', title: 'Report & Document Output', desc: 'PDF / email / API / webhook / sync bundle routing' },
                { ida: 'README-PDFME', title: 'pdfme Template System', desc: 'WYSIWYG PDF designer — no code customization' },
              ]},
              { section: 'Inventory & Purchasing', docs: [
                { ida: 'README-INVENTORY', title: 'Inventory System', desc: 'Buckets, costing (LIFO/FIFO/WA), adjustments' },
                { ida: 'README-BOM', title: 'Bill of Materials', desc: 'Assembly tree: expand, build, cost rollup, where-used' },
                { ida: 'README-FORECAST', title: 'Forecasting', desc: 'Demand, supply, cash flow forecasting' },
                { ida: 'README-WAREHOUSE', title: 'Warehouse', desc: 'Bin locations, pick/pack/ship, receiving' },
              ]},
              { section: 'AI & Alice', docs: [
                { ida: 'README-ALICE-COACHING', title: 'Alice Coaching System', desc: 'Per-model coaching tips, onboarding, training' },
                { ida: 'README-ALICE-TOOLKIT', title: 'Alice Toolkit', desc: 'Open source tools and capabilities' },
                { ida: 'README-PATTERN-RECOGNITION', title: 'Pattern Recognition', desc: 'Observe → log → pattern → recommend → promote' },
                { ida: 'README-ALICE-DATA-QUALITY', title: 'Alice Data Quality', desc: 'Three-tier processing: phone, email, dedup, address' },
                { ida: 'README-ALICE-ESCALATION', title: 'Alice Escalation Protocol', desc: 'Capability boundaries — when Alice asks for help' },
                { ida: 'README-DATA-CONVERSION', title: 'Data Conversion Framework', desc: 'External file → Alice/Claude → DynamicCatalogs → bundle' },
              ]},
              { section: 'Infrastructure', docs: [
                { ida: 'README-DEV-SETUP', title: 'Developer Setup', desc: 'Requirements, environment, first run' },
                { ida: 'README-ENV-SETUP', title: 'Environment Setup', desc: 'Django backend .env configuration' },
                { ida: 'README-SETTINGS', title: 'Settings', desc: 'Setting model — system, company, user preferences' },
                { ida: 'README-SYNC', title: 'Data Sync', desc: 'Connection model: bundles, field maps, conflict resolution' },
                { ida: 'README-PO-SO-BUNDLE', title: 'PO→SO Cross-Instance Bundle', desc: 'Buyer PO → vendor SO; cost→price mapping; bundle UUID tracking' },
                { ida: 'README-CONNECTIONS', title: 'Connections', desc: 'Providers, API keys, auditing' },
                { ida: 'README-CELERY', title: 'Celery Pipeline', desc: 'All 29 background tasks by domain and schedule' },
                { ida: 'README-DB-MAINTENANCE', title: 'Database Maintenance', desc: 'Backup, restore, migration management' },
                { ida: 'README-TESTING', title: 'Testing', desc: 'Test strategy, fixtures, coverage' },
                { ida: 'README-EMAIL', title: 'Email System', desc: 'SMTP operations, templates, tracking' },
              ]},
              { section: 'Sales & Marketing', docs: [
                { ida: 'README-ONBOARDING', title: 'Onboarding', desc: "Alice's guide to new installations and new users" },
                { ida: 'README-SOURCE-ATTRIBUTION', title: 'Source Attribution', desc: 'Campaign ROI: source → lead → customer → revenue' },
                { ida: 'README-SAVED-SEARCHES', title: 'Saved Searches', desc: 'User-defined filters, shared views' },
                { ida: 'README-COMMUNITY', title: 'Community Contributions', desc: 'Marketplace + sharing — layouts, reports, templates' },
              ]},
              { section: 'Models & Data', docs: [
                { ida: 'README-DATABROWSER', title: 'databrowser Guide', desc: 'Operations guide — the universal model browser' },
                { ida: 'README-DATABROWSER-LAYOUTS', title: 'databrowser Layouts', desc: 'Initial layouts and seed data for 61 models' },
                { ida: 'README-REFS-PATTERN', title: 'Refs Pattern', desc: 'Links & keywords — denormalized relationship cache' },
                { ida: 'README-PREFS', title: 'Prefs Architecture', desc: 'Where defaults come from — three-tier inheritance' },
                { ida: 'README-VARIANTS', title: 'Variants', desc: 'Item variants: size, color, material matrix' },
                { ida: 'README-CONTACTS', title: 'Contact Field Map', desc: 'Central identity: roles, linkage, wc2 → wc3 mapping' },
              ]},
            ].map((section) => (
              <div key={section.section}>
                <h4 className="text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-wider px-4 pt-3 pb-1 bg-gray-50 dark:bg-gray-800/30 sticky top-0">
                  {section.section}
                </h4>
                <table className="w-full text-xs">
                  <tbody>
                    {section.docs.map((doc) => (
                      <DocSection key={doc.ida} ida={doc.ida} title={doc.title} subtitle={doc.desc} />
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
          <div className="text-[10px] text-gray-400 dark:text-gray-600 px-1">
            Source: <code>readmes/</code> and <code>readmes/topics/</code> &middot; Content loads from Document records by <code>ida</code> &middot; Create a Document with the matching ida to populate any section
          </div>
        </div>
      )}
    </div>
  );
}

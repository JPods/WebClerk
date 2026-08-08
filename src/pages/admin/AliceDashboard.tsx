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
import { consoleCapture, type ConsoleEntry } from '@/utils/consoleCapture';
import { useAppSelector } from '@/store/hooks';

const AliceQuiz = React.lazy(() => import('./AliceQuiz'));
const PageDesigner = React.lazy(() => import('../tools/PageDesigner'));
const PdfDesigner = React.lazy(() => import('../tools/PdfDesigner'));

export default function AliceDashboard() {
  const { user } = useAppSelector((s) => s.auth);
  const [coaching, setCoaching] = useState<any>(null);
  const [actions, setActions] = useState<any[]>([]);
  const [trainingDocs, setTrainingDocs] = useState<any[]>([]);
  const [consoleEntries, setConsoleEntries] = useState<ConsoleEntry[]>([]);
  const [consoleSummary, setConsoleSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [askText, setAskText] = useState('');
  const [activeTab, setActiveTab] = useState<'coaching' | 'console' | 'actions' | 'training' | 'health' | 'llm' | 'quiz' | 'page-designer' | 'pdf-designer' | 'data-quality'>('coaching');
  const [llmConfig, setLlmConfig] = useState<any>(null);
  const [llmSaving, setLlmSaving] = useState(false);

  // Load data
  useEffect(() => {
    (async () => {
      try {
        // Coaching tips (generic system coaching)
        const cRes = await getRecords('setting', { purpose: 'alice_coaching', limit: 10 }) as any;
        const coachingRecords = cRes?.results || [];
        setCoaching(coachingRecords);

        // User's actions (open, assigned to them)
        const aRes = await getRecords('action', { kanban_column: 'todo', ordering: '-priority', limit: 20 }) as any;
        setActions(aRes?.results || []);

        // Training documents
        const tRes = await getRecords('document', { model_name: 'system', status: 'published', ordering: 'name', limit: 20 }) as any;
        setTrainingDocs(tRes?.results || []);

        // LLM config
        const lRes = await getRecords('setting', { name: 'alice_llm_config', purpose: 'alice_coaching' }) as any;
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
        {tabBtn('page-designer', 'Page Designer')}
        {tabBtn('pdf-designer', 'PDF Designer')}
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
                <span className="text-gray-600">{new Date(entry.dt).toLocaleTimeString()}</span>{' '}
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
              <span className="ml-2 text-xs text-indigo-500">24 charts — WC3/R25 complete system</span>
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
                  { name: 'Forecast & Purchasing', file: 'wc3-forecast-purchasing', desc: 'Demand signals → forecast → PO → receive' },
                  { name: 'Requisition Management', file: 'wc3-requisition-management', desc: 'Internal procurement: request → approve → PO' },
                ]},
                { title: 'Sales & Marketing', charts: [
                  { name: 'Sales Management', file: 'wc3-sales-management', desc: 'Pipeline, activity tracking, performance evaluation' },
                  { name: 'Lead Qualification', file: 'wc3-lead-qualification', desc: 'Marketing → leads → qualify → commit or disqualify' },
                  { name: 'Ad Source Tracking', file: 'wc3-ad-source-tracking', desc: 'Campaign ROI: source → lead → customer → revenue' },
                  { name: 'Territory Assignment', file: 'wc3-territory-assignment', desc: 'Auto-assign rep & sales ID by geography' },
                  { name: 'Commission Calculation', file: 'wc3-commission-calculation', desc: 'Rep rate × item commissionableness → line commission' },
                ]},
                { title: 'Support & Service', charts: [
                  { name: 'Service & RMA', file: 'wc3-service-rma', desc: 'Track, route, resolve, learn (Pareto + Alice)' },
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
                  { name: 'Contact', file: 'wc3-contact', desc: 'Central identity: roles, linkage' },
                  { name: 'Sign-in / Register', file: 'wc3-signin-register', desc: 'Authentication + role assignment' },
                  { name: 'Report & Document Output', file: 'wc3-report-output', desc: 'PDF / email / API / webhook / sync bundle' },
                  { name: 'Data Sync', file: 'wc3-sync', desc: 'Connection model: bundles, field maps, conflict resolution' },
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
                  const existing = await getRecords('setting', { name: 'alice_llm_config', purpose: 'alice_coaching' }) as any;
                  const existingRec = (existing?.results || [])[0];
                  await apiClient.post('/wcapi/save/', {
                    model_name: 'setting', id: existingRec?.id,
                    name: 'alice_llm_config', purpose: 'alice_coaching',
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

      {/* ═══ How to Extend Alice ═══ */}
      <div className="mt-8 border border-gray-200 dark:border-gray-700 rounded-lg p-5 bg-gray-50 dark:bg-gray-800">
        <h3 className="text-sm font-bold text-blue-600 dark:text-blue-400 mb-3">How to Extend Alice</h3>
        <div className="text-xs text-gray-600 dark:text-gray-400 space-y-2">
          <p><strong>Add coaching tips:</strong> Create Setting records with purpose="alice_coaching" and parent_model set to any model. Alice will show the tips when users work with that model. Tips include field_help, action guides, warnings, and code examples.</p>
          <p><strong>Submit training documents:</strong> Create Document records with model_name="system" and status="published". They appear in the Training tab. Submit useful documents for bonus credit via the Submit for Bonus page — Alice tracks adoption.</p>
          <p><strong>Create onboarding actions:</strong> Create Action records with project_name="Alice Onboarding". New users see these as their getting-started checklist.</p>
          <p><strong>Teach Alice field behaviors:</strong> Update the field_access Setting for any model to add field_behaviors — Alice uses these to know which fields are emails (mailto), phones (tel), addresses (map), selects, lookups, etc.</p>
          <p><strong>Improve column widths:</strong> Alice watches what column widths users set and refines her recommendations. The column_widths Setting (purpose="alice_coaching") is synced from WCHQ.</p>
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


      {/* ═══ Page Designer ═══ */}
      {activeTab === 'page-designer' && (
        <Suspense fallback={<div className="p-4 text-sm text-gray-500">Loading Page Designer...</div>}>
          <div className="h-[70vh]">
            <PageDesigner />
          </div>
        </Suspense>
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
    </div>
  );
}

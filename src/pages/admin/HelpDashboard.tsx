/**
 * HelpDashboard — context-aware help center with three-source collection builder.
 *
 * Sources: Local (company docs), WCHQ (webclerk.net), User Groups (community)
 * Features: bookmarks, recently viewed, glossary, keyboard shortcuts,
 * report a problem, "was this helpful?" feedback, collection builder.
 *
 * Opens in its own window from the Help button.
 * Route: /help?context=invoice&model=invoice&field=total
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getRecords, saveRecord } from '@/api/wcapi';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface HelpItem {
  id: string;
  title: string;
  body: string;
  source: 'local' | 'wchq' | 'usergroup';
  category: string;
  url?: string;
}

// ---------------------------------------------------------------------------
// WCHQ resources (static until webclerk.com has an API)
// ---------------------------------------------------------------------------

const WCHQ_RESOURCES: HelpItem[] = [
  { id: 'wchq-1', title: 'Getting Started Videos', body: 'Video tutorials for new WebClerk users covering setup, first order, and invoicing.', source: 'wchq', category: 'video', url: 'https://webclerk.net/videos.html' },
  { id: 'wchq-2', title: 'WebClerk API Documentation', body: 'Complete wcapi endpoint reference — get, save, delete, manage.', source: 'wchq', category: 'api', url: 'https://webclerk.net/videos.html' },
  { id: 'wchq-3', title: 'Data Services Catalog', body: 'Available WCHQ data services: catalog cleaning, tax APIs, shipping rate APIs, proximity search.', source: 'wchq', category: 'service', url: 'https://webclerk.net/videos.html' },
  { id: 'wchq-4', title: 'MCP Server Templates', body: 'Downloadable MCP server templates for common integrations: tax, shipping, payments, time tracking.', source: 'wchq', category: 'developer', url: 'https://webclerk.net/videos.html' },
  { id: 'wchq-5', title: 'Community Layout Library', body: 'Browse and download DataBrowser layouts submitted by other users.', source: 'wchq', category: 'layout', url: 'https://webclerk.net/videos.html' },
  { id: 'wchq-6', title: 'User Group Forums', body: 'Connect with other WebClerk users. Share tips, ask questions, submit layouts for bonus credit.', source: 'wchq', category: 'community', url: 'https://webclerk.net/videos.html' },
];

// Keyboard shortcuts reference
const SHORTCUTS = [
  { keys: 'Cmd/Ctrl + Shift + M', action: 'Open model picker in DataBrowser' },
  { keys: 'Shift + click', action: 'Delete layout / Open any model in DataBrowser' },
  { keys: 'Shift + drag header', action: 'Reorder columns' },
  { keys: 'Ctrl/Cmd + click header', action: 'Multi-sort (add secondary sort)' },
  { keys: 'Double-click cell', action: 'Inline edit in DataGrid' },
  { keys: 'Enter', action: 'Save inline edit / Confirm dialog' },
  { keys: 'Escape', action: 'Cancel edit / Close dialog' },
  { keys: 'Tab', action: 'Save edit, move to next cell' },
  { keys: 'Arrow Up/Down', action: 'Navigate records in list' },
  { keys: 'Cmd+Opt+Shift + click label', action: 'Open field help in Help Dashboard' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function HelpDashboard() {
  const [searchParams] = useSearchParams();
  const context = searchParams.get('context') || 'general';
  const model = searchParams.get('model') || 'system';
  const field = searchParams.get('field') || null;

  const [localDocs, setLocalDocs] = useState<any[]>([]);
  const [coaching, setCoaching] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState<'local' | 'wchq' | 'usergroup' | 'collection' | 'glossary' | 'shortcuts'>('local');
  const [bookmarks, setBookmarks] = useState<Set<string>>(() => {
    try { return new Set(JSON.parse(localStorage.getItem('help-bookmarks') || '[]')); } catch { return new Set(); }
  });
  const [recentlyViewed, setRecentlyViewed] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem('help-recent') || '[]'); } catch { return []; }
  });
  const [feedback, setFeedback] = useState<Record<string, 'up' | 'down'>>({});
  const [showAddBookmark, setShowAddBookmark] = useState(false);
  const [newBookmark, setNewBookmark] = useState({ title: '', url: '', notes: '' });
  const [glossary, setGlossary] = useState<Record<string, string>>({});

  // Load data
  useEffect(() => {
    (async () => {
      try {
        // All published documents
        const dRes = await getRecords('document', { status: 'published', ordering: 'name', limit: 50 }) as any;
        setLocalDocs(dRes?.results || []);

        // Coaching for this model
        const cRes = await getRecords('setting', { parent_model: model, purpose: 'alice_coaching' }) as any;
        const cData = (cRes?.results || [])[0]?.data || null;
        setCoaching(cData);

        // Build glossary from all coaching field_help
        const allCoaching = await getRecords('setting', { purpose: 'alice_coaching', limit: 50 }) as any;
        const g: Record<string, string> = {};
        (allCoaching?.results || []).forEach((s: any) => {
          const fh = s.config?.field_help || {};
          Object.entries(fh).forEach(([k, v]) => { g[k] = v as string; });
        });
        setGlossary(g);
      } catch { /* silent */ }
      finally { setLoading(false); }
    })();
  }, [model]);

  // Track recently viewed
  const trackView = useCallback((id: string) => {
    setRecentlyViewed((prev) => {
      const next = [id, ...prev.filter((r) => r !== id)].slice(0, 10);
      localStorage.setItem('help-recent', JSON.stringify(next));
      return next;
    });
  }, []);

  // Toggle bookmark
  const toggleBookmark = useCallback((id: string) => {
    setBookmarks((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      localStorage.setItem('help-bookmarks', JSON.stringify([...next]));
      return next;
    });
  }, []);

  // Send feedback
  const sendFeedback = useCallback(async (itemId: string, vote: 'up' | 'down') => {
    setFeedback((p) => ({ ...p, [itemId]: vote }));
    try {
      await saveRecord('setting', {
        name: `help_feedback:${itemId}`,
        purpose: 'alice_log',
        config: { item_id: itemId, vote, context, model, dt: Date.now() },
      });
    } catch { /* silent */ }
  }, [context, model]);

  // Report problem
  const reportProblem = useCallback(async (description: string) => {
    try {
      await saveRecord('setting', {
        name: `Help problem: ${description.slice(0, 200)}`,
        purpose: 'alice_pending',
        config: { description, context, model, field, dt: Date.now(), url: window.location.href },
      });
      alert('Problem reported. Alice will review.');
    } catch { alert('Failed to report.'); }
  }, [context, model, field]);

  // Filter docs by search
  const filterItems = useCallback((items: any[]): any[] => {
    if (!searchTerm.trim()) return items;
    const q = searchTerm.toLowerCase();
    return items.filter((d) => (d.name || d.title || '').toLowerCase().includes(q) || (d.body || '').toLowerCase().includes(q));
  }, [searchTerm]);

  // Build collection from all sources
  const collection = useMemo(() => {
    const items: HelpItem[] = [];
    // Local bookmarked docs
    localDocs.filter((d) => bookmarks.has(`local-${d.id}`)).forEach((d) => {
      items.push({ id: `local-${d.id}`, title: d.name, body: d.body || d.description || '', source: 'local', category: 'document' });
    });
    // WCHQ bookmarked
    WCHQ_RESOURCES.filter((r) => bookmarks.has(r.id)).forEach((r) => items.push(r));
    return items;
  }, [localDocs, bookmarks]);

  const tabBtn = (tab: string, label: string, count?: number) => (
    <button key={tab} onClick={() => setActiveTab(tab as any)}
      className={`px-3 py-2 text-xs font-medium border-b-2 -mb-px transition ${
        activeTab === tab ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
      }`}>
      {label}{count !== undefined ? ` (${count})` : ''}
    </button>
  );

  // Render a help item
  const renderItem = (item: { id: string; name?: string; title?: string; body?: string; description?: string; url?: string }, source: 'local' | 'wchq' | 'usergroup') => {
    const id = source === 'local' ? `local-${item.id}` : (item as any).id || `${source}-${item.id}`;
    const title = item.name || (item as any).title || 'Untitled';
    const isBookmarked = bookmarks.has(id);
    const fb = feedback[id];

    return (
      <details key={id} className="border border-gray-200 dark:border-gray-700 rounded-lg group"
        onClick={() => trackView(id)}>
        <summary className="p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 flex items-center gap-2">
          <button onClick={(e) => { e.preventDefault(); e.stopPropagation(); toggleBookmark(id); }}
            className="text-sm flex-shrink-0" title={isBookmarked ? 'Remove bookmark' : 'Bookmark'}>
            {isBookmarked ? '★' : '☆'}
          </button>
          <span className={`text-[9px] px-1.5 py-0.5 rounded font-semibold uppercase ${
            source === 'local' ? 'bg-green-100 text-green-700' : source === 'wchq' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'
          }`}>{source}</span>
          <span className="text-sm font-medium text-gray-800 dark:text-gray-200 flex-1">{title}</span>
          {(item as any).url && (
            <a href={(item as any).url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}
              className="text-[10px] text-blue-500 hover:underline">Open ↗</a>
          )}
        </summary>
        <div className="p-4 pt-0 border-t border-gray-100 dark:border-gray-700">
          <pre className="whitespace-pre-wrap text-xs text-gray-700 dark:text-gray-300 leading-relaxed">{item.body || item.description || ''}</pre>
          {/* Feedback */}
          <div className="flex items-center gap-3 mt-3 pt-2 border-t border-gray-100 dark:border-gray-700">
            <span className="text-[10px] text-gray-400">Was this helpful?</span>
            <button onClick={() => sendFeedback(id, 'up')} className={`text-sm ${fb === 'up' ? 'text-green-600' : 'text-gray-400 hover:text-green-500'}`}>👍</button>
            <button onClick={() => sendFeedback(id, 'down')} className={`text-sm ${fb === 'down' ? 'text-red-600' : 'text-gray-400 hover:text-red-500'}`}>👎</button>
            <span className="flex-1" />
            <button onClick={() => { navigator.clipboard?.writeText(window.location.href); }}
              className="text-[10px] text-gray-400 hover:text-blue-500">📋 Copy link</button>
          </div>
        </div>
      </details>
    );
  };

  if (loading) return <div className="p-8 text-gray-500">Loading help...</div>;

  return (
    <div className="max-w-5xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Help Center</h1>
          <p className="text-xs text-gray-500 mt-1">
            Context: <span className="font-semibold text-blue-600">{context}</span>
            {model !== 'system' && <> · Model: <span className="font-semibold">{model}</span></>}
            {field && <> · Field: <span className="font-semibold text-green-600">{field}</span></>}
          </p>
        </div>
        <div className="flex gap-2">
          <input type="text" placeholder="Search all help..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)}
            className="px-3 py-1.5 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800 w-48" />
          <a href="https://webclerk.net/videos.html" target="_blank" rel="noopener noreferrer"
            className="px-2 py-1.5 text-[10px] font-medium rounded border border-blue-300 text-blue-600 hover:bg-blue-50">🌐 Videos</a>
          <a href="https://webclerk.net/videos.html" target="_blank" rel="noopener noreferrer"
            className="px-2 py-1.5 text-[10px] font-medium rounded border border-purple-300 text-purple-600 hover:bg-purple-50">👥 Groups</a>
          <button onClick={() => { const desc = prompt('Describe the problem:'); if (desc) reportProblem(desc); }}
            className="px-2 py-1.5 text-[10px] font-medium rounded border border-red-300 text-red-600 hover:bg-red-50">⚠ Report</button>
        </div>
      </div>

      {/* Field-specific help */}
      {field && coaching?.field_help?.[field] && (
        <div className="mb-4 border border-green-200 dark:border-green-800 rounded-lg p-3 bg-green-50 dark:bg-green-900/20">
          <h2 className="text-xs font-bold text-green-700 dark:text-green-400 uppercase mb-1">Field: {field}</h2>
          <div className="text-sm text-gray-700 dark:text-gray-300">{coaching.field_help[field]}</div>
        </div>
      )}

      {/* Bookmarks bar + Add Bookmark */}
      <div className="mb-4 flex items-center gap-1 flex-wrap">
        <span className="text-[10px] text-gray-400 font-semibold mr-1">★ Bookmarks:</span>
        {[...bookmarks].slice(0, 8).map((id) => {
          const doc = localDocs.find((d) => `local-${d.id}` === id);
          const wchq = WCHQ_RESOURCES.find((r) => r.id === id);
          const label = doc?.name || wchq?.title || id;
          return (
            <button key={id} onClick={() => setActiveTab('collection')}
              className="px-2 py-0.5 text-[10px] rounded border border-yellow-300 bg-yellow-50 text-yellow-800 hover:bg-yellow-100 truncate max-w-32">
              {label}
            </button>
          );
        })}
        <button onClick={() => setShowAddBookmark(true)}
          className="px-2 py-0.5 text-[10px] rounded border border-blue-300 text-blue-600 hover:bg-blue-50 font-semibold">
          + Add Link
        </button>
      </div>

      {/* Add Bookmark form */}
      {showAddBookmark && (
        <div className="mb-4 border border-blue-200 dark:border-blue-800 rounded-lg p-4 bg-blue-50 dark:bg-blue-900/20">
          <h3 className="text-xs font-bold text-blue-700 dark:text-blue-400 mb-3">Add Bookmark — paste a URL with your notes</h3>
          <div className="space-y-2">
            <input type="text" placeholder="Title — what is this link about?" value={newBookmark.title}
              onChange={(e) => setNewBookmark((p) => ({ ...p, title: e.target.value }))}
              className="w-full px-3 py-2 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800" />
            <input type="url" placeholder="Paste URL here..." value={newBookmark.url}
              onChange={(e) => setNewBookmark((p) => ({ ...p, url: e.target.value }))}
              className="w-full px-3 py-2 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800" />
            <textarea placeholder="Your notes — why is this useful? what does it explain?" value={newBookmark.notes}
              onChange={(e) => setNewBookmark((p) => ({ ...p, notes: e.target.value }))}
              rows={3} className="w-full px-3 py-2 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800" />
          </div>
          <div className="flex justify-end gap-2 mt-3">
            <button onClick={() => { setShowAddBookmark(false); setNewBookmark({ title: '', url: '', notes: '' }); }}
              className="px-3 py-1.5 text-xs rounded border border-gray-300 text-gray-500 hover:bg-gray-100">Cancel</button>
            <button disabled={!newBookmark.title.trim() || !newBookmark.url.trim()} onClick={async () => {
              try {
                const doc = await saveRecord('document', {
                  name: newBookmark.title,
                  slug: `bookmark-${Date.now()}`,
                  description: newBookmark.url,
                  body: `${newBookmark.notes}\n\nLink: ${newBookmark.url}`,
                  status: 'published',
                  model_name: 'system',
                  confidential: 'internal',
                  metadata: { health: 'bookmark', url: newBookmark.url, context, model },
                });
                // Add to bookmarks
                const newId = `local-${(doc as any)?.record?.id || (doc as any)?.id}`;
                toggleBookmark(newId);
                setShowAddBookmark(false);
                setNewBookmark({ title: '', url: '', notes: '' });
                // Refresh local docs
                const dRes = await getRecords('document', { status: 'published', ordering: 'name', limit: 50 }) as any;
                setLocalDocs(dRes?.results || []);
              } catch { alert('Failed to save bookmark.'); }
            }}
              className="px-3 py-1.5 text-xs rounded bg-blue-600 text-white hover:bg-blue-700 font-medium disabled:opacity-40">
              Save Bookmark
            </button>
          </div>
        </div>
      )}

      {/* Coaching quick tips */}
      {coaching?.tips?.length > 0 && (
        <div className="mb-4 border border-blue-200 dark:border-blue-800 rounded-lg p-3 bg-blue-50 dark:bg-blue-900/20">
          <h2 className="text-xs font-bold text-blue-700 dark:text-blue-400 uppercase mb-2">💡 Quick Tips: {model}</h2>
          {coaching.tips.map((tip: any) => (
            <div key={tip.id} className="mb-1 text-xs"><span className="font-semibold">{tip.title}:</span> {tip.body}</div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 mb-4 flex-wrap">
        {tabBtn('local', '📄 Local', localDocs.length)}
        {tabBtn('wchq', '🌐 WCHQ', WCHQ_RESOURCES.length)}
        {tabBtn('usergroup', '👥 User Groups', 0)}
        {tabBtn('collection', '★ My Collection', collection.length)}
        {tabBtn('glossary', '📖 Glossary', Object.keys(glossary).length)}
        {tabBtn('shortcuts', '⌨ Shortcuts', SHORTCUTS.length)}
      </div>

      {/* Tab content */}

      {activeTab === 'local' && (
        <div className="space-y-2">
          {filterItems(localDocs).length === 0 && <div className="text-sm text-gray-500 text-center py-4">No local documents found.</div>}
          {filterItems(localDocs).map((doc) => renderItem(doc, 'local'))}
        </div>
      )}

      {activeTab === 'wchq' && (
        <div className="space-y-2">
          {filterItems(WCHQ_RESOURCES).map((r) => renderItem(r as any, 'wchq'))}
        </div>
      )}

      {activeTab === 'usergroup' && (
        <div className="text-center py-8">
          <p className="text-sm text-gray-500 mb-4">User group content is community-submitted and moderated by WCHQ.</p>
          <a href="https://webclerk.net/videos.html" target="_blank" rel="noopener noreferrer"
            className="px-4 py-2 text-sm font-medium rounded bg-purple-600 text-white hover:bg-purple-700">
            👥 Join WebClerk User Groups
          </a>
          <p className="text-xs text-gray-400 mt-4">Submit layouts, training docs, and tips for bonus credit. Alice tracks adoption and rewards contributors.</p>
        </div>
      )}

      {activeTab === 'collection' && (
        <div className="space-y-2">
          {collection.length === 0 && <div className="text-sm text-gray-500 text-center py-4">No bookmarked items. Click ☆ on any help item to add it to your collection.</div>}
          {collection.map((item) => renderItem(item as any, item.source))}
        </div>
      )}

      {activeTab === 'glossary' && (
        <div>
          <p className="text-xs text-gray-500 mb-3">Field definitions from across all models. {Object.keys(glossary).length} terms.</p>
          <div className="grid grid-cols-1 gap-1">
            {Object.entries(glossary).sort(([a], [b]) => a.localeCompare(b)).filter(([k]) => !searchTerm || k.toLowerCase().includes(searchTerm.toLowerCase())).map(([field, help]) => (
              <div key={field} className="flex gap-3 py-1 border-b border-gray-100 dark:border-gray-800">
                <span className="text-xs font-semibold text-blue-600 dark:text-blue-400 w-32 flex-shrink-0">{field}</span>
                <span className="text-xs text-gray-600 dark:text-gray-400">{help}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'shortcuts' && (
        <div>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-200"><th className="py-2 text-left text-gray-500 w-48">Shortcut</th><th className="py-2 text-left text-gray-500">Action</th></tr>
            </thead>
            <tbody>
              {SHORTCUTS.map((s, i) => (
                <tr key={i} className="border-b border-gray-100 dark:border-gray-800">
                  <td className="py-2"><kbd className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-[10px] font-mono">{s.keys}</kbd></td>
                  <td className="py-2 text-gray-700 dark:text-gray-300">{s.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Recently viewed */}
      {recentlyViewed.length > 0 && (
        <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
          <h3 className="text-[10px] font-semibold text-gray-400 uppercase mb-2">Recently Viewed</h3>
          <div className="flex gap-1 flex-wrap">
            {recentlyViewed.slice(0, 6).map((id) => {
              const doc = localDocs.find((d) => `local-${d.id}` === id);
              const label = doc?.name || id;
              return <span key={id} className="px-2 py-0.5 text-[10px] rounded bg-gray-100 dark:bg-gray-800 text-gray-500 truncate max-w-40">{label}</span>;
            })}
          </div>
        </div>
      )}
    </div>
  );
}

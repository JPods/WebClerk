/**
 * DedupPanel — Duplicate detection and merge tool for DataBrowser.
 *
 * Server-side dedup via wcapi/manage { action: "find_duplicates" }.
 * Shows duplicate groups as cards. Pick the winner, merge losers into it.
 * Works for any model (contacts, items, etc.).
 *
 * Usage in DataBrowser:
 *   <DedupPanel model="contact" matchFields={["name_first+name_last"]}
 *     onMergeComplete={() => db.fetchRecords()} />
 */
import React, { useCallback, useEffect, useState } from 'react';
import { getUI } from '@/utils/contactUI';
import { formatDt } from '@/utils/fieldFormatters';
import './DedupPanel.css';

interface DedupRecord {
  id: number;
  ida: string;
  fields: Record<string, any>;
  score: number;
}

interface DedupGroup {
  match_key: string;
  match_fields: string[];
  records: DedupRecord[];
  recommended_winner: number;
}

interface DedupResult {
  groups: DedupGroup[];
  total_groups: number;
  total_duplicates: number;
}

interface DedupPanelProps {
  model: string;
  matchFields?: string[];
  onMergeComplete?: () => void;
  onClose?: () => void;
  fontSize?: number;
  /** Called when dedup results change — parent can filter the list to these IDs */
  onDedupIds?: (ids: number[], currentGroupIds: number[]) => void;
}

// Fields to display in cards — skip JSON blobs and system fields
const SKIP_FIELDS = new Set([
  'metadata', 'refs', 'prefs', 'actions', 'comments', 'config', 'password',
  'is_superuser', 'is_staff', 'dt_joined', 'last_login', 'search_vector',
  'is_active', 'is_deleted', 'is_archived', 'is_locked', 'security_level',
  'version', 'dt_created', 'dt_modified',
]);

const DEFAULT_MATCH_FIELDS: Record<string, string[]> = {
  contact: ['name_first+name_last'],
  item: ['ida'],
};

export default function DedupPanel({ model, matchFields, onMergeComplete, onClose, fontSize: fontSizeProp, onDedupIds }: DedupPanelProps) {
  const [fontScale, setFontScale] = useState<number>(() => getUI<number>('dedup.font_size', fontSizeProp || 13));
  const [result, setResult] = useState<DedupResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [currentGroupIdx, setCurrentGroupIdx] = useState(0);
  const [merging, setMerging] = useState(false);
  const [selectedWinner, setSelectedWinner] = useState<number | null>(null);
  // Capture text selection on mousedown — clicking a button clears window.getSelection()
  const lastSelection = React.useRef<string>('');
  React.useEffect(() => {
    const capture = () => {
      const sel = window.getSelection()?.toString()?.trim();
      if (sel) lastSelection.current = sel;
    };
    document.addEventListener('mousedown', capture);
    return () => document.removeEventListener('mousedown', capture);
  }, []);

  const [matchConfig, setMatchConfig] = useState<string[]>(
    matchFields || DEFAULT_MATCH_FIELDS[model] || ['ida']
  );
  const [customField, setCustomField] = useState('');

  const fetchDupes = useCallback(async () => {
    setLoading(true);
    try {
      const { manageAction } = await import('@/api/wcapi');
      const res = await manageAction('find_duplicates', {
        model,
        match_fields: matchConfig,
        limit: 500,
      });
      setResult(res as DedupResult);
      setCurrentGroupIdx(0);
      setSelectedWinner(null);
    } catch (e) {
      console.error('Dedup failed:', e);
    } finally {
      setLoading(false);
    }
  }, [model, matchConfig]);

  useEffect(() => { fetchDupes(); }, [fetchDupes]);

  const currentGroup = result?.groups?.[currentGroupIdx];

  // Notify parent of all dedup record IDs + current group IDs for list filtering
  useEffect(() => {
    if (!onDedupIds || !result) return;
    const allIds = result.groups.flatMap(g => g.records.map(r => r.id));
    const currentIds = currentGroup?.records.map(r => r.id) || [];
    onDedupIds(allIds, currentIds);
  }, [result, currentGroupIdx, onDedupIds]);

  useEffect(() => {
    if (currentGroup) {
      setSelectedWinner(currentGroup.recommended_winner);
    }
  }, [currentGroupIdx, currentGroup?.match_key]);

  const handleMerge = async () => {
    if (!currentGroup || !selectedWinner) return;
    const loserIds = currentGroup.records
      .filter(r => r.id !== selectedWinner)
      .map(r => r.id);
    if (!(window.event as any)?.shiftKey && !confirm(`Merge ${loserIds.length} record(s) into #${selectedWinner}? (Shift-click to skip this)`)) return;

    setMerging(true);
    try {
      const { manageAction } = await import('@/api/wcapi');
      await manageAction('merge_records', {
        model,
        winner_id: selectedWinner,
        loser_ids: loserIds,
      });
      // Remove this group and advance
      if (result) {
        const newGroups = result.groups.filter((_, i) => i !== currentGroupIdx);
        setResult({ ...result, groups: newGroups, total_groups: newGroups.length });
        if (currentGroupIdx >= newGroups.length) setCurrentGroupIdx(Math.max(0, newGroups.length - 1));
      }
      onMergeComplete?.();
    } catch (e) {
      alert('Merge failed: ' + (e as Error).message);
    } finally {
      setMerging(false);
    }
  };

  const handleSkip = () => {
    if (result && currentGroupIdx < result.groups.length - 1) {
      setCurrentGroupIdx(currentGroupIdx + 1);
    }
  };

  const handlePrev = () => {
    if (currentGroupIdx > 0) setCurrentGroupIdx(currentGroupIdx - 1);
  };

  // Render field value — truncate long values
  const renderVal = (v: any) => {
    if (v === null || v === undefined || v === '') return <span className="dp-field-empty">—</span>;
    const s = typeof v === 'object' ? JSON.stringify(v) : String(v);
    if (s.includes('placeholder')) return <span className="dp-field-empty">—</span>;
    return s.length > 50 ? s.slice(0, 50) + '…' : s;
  };

  // Get display fields from the first group's records
  const displayFields = currentGroup
    ? Array.from(new Set(
        currentGroup.records.flatMap(r => Object.keys(r.fields))
      )).filter(f => !SKIP_FIELDS.has(f)).slice(0, 15)
    : [];

  const scoreBadgeClass = (score: number) =>
    score >= 7 ? 'dp-badge dp-badge--score-high' :
    score >= 4 ? 'dp-badge dp-badge--score-mid' :
    'dp-badge dp-badge--score-low';

  return (
    <div className="dp-root" style={{ '--dp-fs': `${fontScale}px` } as React.CSSProperties}>
      {/* Header */}
      <div className="dp-header">
        <div>
          <span className="dp-title">Dedup: {model}</span>
          {result && (
            <span className="dp-stats">
              {result.total_groups} groups · {result.total_duplicates} duplicates
            </span>
          )}
        </div>
        <div className="dp-header-actions">
          {/* Match field selector */}
          <select
            className="dp-select"
            value={matchConfig.join(',')}
            onChange={e => setMatchConfig(e.target.value.split(','))}
          >
            <option value="name_first+name_last">By Name</option>
            <option value="email:email">By Email</option>
            <option value="phone:phone">By Phone</option>
            <option value="company:normalized">By Company</option>
            <option value="ida">By IDA</option>
          </select>
          <button onClick={fetchDupes} disabled={loading} className="dp-btn dp-btn--scan">
            {loading ? 'Scanning...' : 'Scan'}
          </button>
          {/* Font size controls */}
          <button onClick={() => setFontScale(s => { const n = Math.max(10, s - 2); import('@/utils/contactUI').then(m => m.setUI('dedup.font_size', n)); return n; })}
            className="dp-btn--font">
            A-
          </button>
          <button onClick={() => setFontScale(s => { const n = Math.min(22, s + 2); import('@/utils/contactUI').then(m => m.setUI('dedup.font_size', n)); return n; })}
            className="dp-btn--font">
            A+
          </button>
          {onClose && (
            <button onClick={onClose} className="dp-btn--close">
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Navigation */}
      {result && result.groups.length > 0 && (
        <div className="dp-nav">
          <button onClick={handlePrev} disabled={currentGroupIdx === 0}
            className="dp-btn dp-btn--nav">
            ← Prev
          </button>
          <span className="dp-nav-label">
            Group {currentGroupIdx + 1} of {result.groups.length}
            {currentGroup && <> — <strong className="dp-nav-match-key">{currentGroup.match_key}</strong> ({currentGroup.records.length} records)</>}
          </span>
          <div className="dp-nav-actions">
            <button onClick={async () => {
                if (!currentGroup) return;
                if (!(window.event as any)?.shiftKey && !confirm(`Delete all ${currentGroup.records.length} records in this group?`)) return;
                try {
                  const { deleteRecord: dr, manageAction } = await import('@/api/wcapi');
                  // Journal all records before delete — the hardhat
                  await manageAction('journal_dedup_delete', { model, record_ids: currentGroup.records.map(r => r.id) });
                  for (const rec of currentGroup.records) {
                    await dr(model, rec.id);
                  }
                  if (result) {
                    const newGroups = result.groups.filter((_, i) => i !== currentGroupIdx);
                    setResult({ ...result, groups: newGroups, total_groups: newGroups.length });
                    setCurrentGroupIdx(prev => Math.min(prev, Math.max(0, newGroups.length - 1)));
                  }
                  onMergeComplete?.();
                } catch (e) { alert('Delete failed: ' + (e as Error).message); }
              }}
              className="dp-btn dp-btn--delete-all">
              Delete All
            </button>
            <button onClick={handleSkip} disabled={currentGroupIdx >= result.groups.length - 1}
              className="dp-btn dp-btn--skip">
              Skip →
            </button>
            <button onClick={handleMerge} disabled={!selectedWinner || merging}
              className="dp-btn dp-btn--merge">
              {merging ? 'Merging...' : `Merge into #${selectedWinner || '?'}`}
            </button>
          </div>
        </div>
      )}

      {/* Group detail — records as cards */}
      <div className="dp-content">
        {loading && <div className="dp-loading">Scanning for duplicates...</div>}

        {!loading && result && result.groups.length === 0 && (
          <div className="dp-empty">No duplicates found. Clean data.</div>
        )}

        {currentGroup && currentGroup.records.map((rec, idx) => {
          const isWinner = rec.id === selectedWinner;
          const isRecommended = rec.id === currentGroup.recommended_winner;
          return (
            <div key={rec.id}
              onClick={() => setSelectedWinner(rec.id)}
              className={`dp-card${isWinner ? ' dp-card--winner' : ''}`}>
              {/* Card header */}
              <div className="dp-card-header">
                <div className="dp-card-header-left">
                  <span className="dp-card-id">
                    #{rec.id}
                  </span>
                  <span className="dp-card-ida">{rec.ida}</span>
                  <span className={scoreBadgeClass(rec.score)}>
                    score: {rec.score}
                  </span>
                  {isRecommended && (
                    <span className="dp-badge dp-badge--recommended">
                      recommended
                    </span>
                  )}
                  {isWinner && (
                    <span className="dp-badge dp-badge--keep">
                      ★ KEEP
                    </span>
                  )}
                </div>
                {/* Delete individual record */}
                <button
                  onClick={async (e) => {
                    e.stopPropagation();
                    if (!e.shiftKey && !confirm(`Delete record #${rec.id} (${rec.ida})? (Shift-click to skip this)`)) return;
                    try {
                      const { deleteRecord: dr, manageAction } = await import('@/api/wcapi');
                      // Journal before delete — the hardhat
                      await manageAction('journal_dedup_delete', { model, record_ids: [rec.id] });
                      await dr(model, rec.id);
                      // Remove from current group
                      if (result) {
                        const updatedGroup = {
                          ...result.groups[currentGroupIdx],
                          records: result.groups[currentGroupIdx].records.filter(r => r.id !== rec.id),
                        };
                        const remaining = updatedGroup.records.length;

                        if (remaining <= 1) {
                          // Group resolved — remove it and advance to next
                          const newGroups = result.groups.filter((_, i) => i !== currentGroupIdx);
                          setResult({ ...result, groups: newGroups, total_groups: newGroups.length });
                          setCurrentGroupIdx(prev => Math.min(prev, Math.max(0, newGroups.length - 1)));
                        } else {
                          // Group still has dupes — update in place, stay on it
                          const newGroups = [...result.groups];
                          newGroups[currentGroupIdx] = updatedGroup;
                          setResult({ ...result, groups: newGroups });
                        }
                      }
                      onMergeComplete?.();
                    } catch (err) { alert('Delete failed: ' + (err as Error).message); }
                  }}
                  className="dp-btn dp-btn--delete"
                  title={`Delete #${rec.id}`}
                >Delete</button>
                {/* Note -> button — save highlighted text as comment on the OTHER record */}
                {currentGroup && currentGroup.records.length === 2 && (
                  <button
                    onClick={async (e) => {
                      e.stopPropagation();
                      const sel = window.getSelection()?.toString()?.trim() || lastSelection.current;
                      if (!sel) { alert('Highlight text first, then click Note →'); return; }
                      lastSelection.current = '';
                      const otherId = currentGroup.records.find(r => r.id !== rec.id)?.id;
                      if (!otherId) return;
                      try {
                        const { getRecords, saveRecord } = await import('@/api/wcapi');
                        const res = await getRecords(model, { filters: { id: otherId }, limit: 1 }) as any;
                        const target = res?.results?.[0];
                        if (!target) { alert('Could not load target record'); return; }
                        const comments = target.comments && typeof target.comments === 'object' ? { ...target.comments } : {};
                        const process = Array.isArray(comments.process) ? [...comments.process] : [];
                        const now = formatDt(new Date(), 'datetime');
                        process.push({
                          mgs: `From #${rec.id}: ${sel}`,
                          time: now,
                          user: 'Dedup',
                          user_id: 0,
                        });
                        comments.process = process;
                        await saveRecord(model, { id: otherId, comments });
                        if (typeof App !== 'undefined' && (App as any).flash) (App as any).flash('Noted on #' + otherId, 2000);
                      } catch (err) { alert('Save failed: ' + (err as Error).message); }
                    }}
                    className="dp-btn dp-btn--note"
                    title="Save highlighted text as process comment on the other record"
                  >Note →</button>
                )}
                {/* Edit button — open record in new window */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    const routes: Record<string, string> = {
                      contact: '/core/contact/detail',
                      customer: '/org/customer/detail',
                      item: '/products/item/detail',
                      order: '/transactions/order/detail',
                      invoice: '/transactions/invoice/detail',
                      proposal: '/transactions/proposal/detail',
                      purchase: '/transactions/purchase/detail',
                      action: '/core/actions/detail',
                    };
                    const route = routes[model] || `/${model}`;
                    window.open(`${route}/${rec.id}`, '_blank');
                  }}
                  className="dp-btn dp-btn--edit"
                  title={`Edit #${rec.id} in new window`}
                >Edit</button>
                {/* Research buttons — company website + LinkedIn lookup */}
                {(() => {
                  const email = String(rec.fields.email || '');
                  const domain = email.includes('@') && !email.includes('placeholder') ? email.split('@')[1] : '';
                  const name = [rec.fields.name_first, rec.fields.name_last].filter(Boolean).join(' ') || rec.fields.attention || '';
                  const company = String(rec.fields.company || '');
                  return (
                    <>
                      {domain && !['gmail.com','yahoo.com','hotmail.com','aol.com','comcast.net','msn.com','outlook.com','icloud.com','me.com','mac.com','att.net','verizon.net','sbcglobal.net'].includes(domain) && (
                        <button onClick={(e) => { e.stopPropagation(); window.open(`https://${domain}`, '_blank'); }}
                          className="dp-btn--research" title={`Open ${domain}`}>🏢</button>
                      )}
                      {name && (
                        <button onClick={(e) => { e.stopPropagation(); window.open(`https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(name + (company ? ' ' + company : ''))}`, '_blank'); }}
                          className="dp-btn--research" title={`Search LinkedIn for ${name}`}>in</button>
                      )}
                    </>
                  );
                })()}
              </div>

              {/* Card fields — 2 column grid */}
              <div className="dp-fields-grid">
                {displayFields.map(f => {
                  const val = rec.fields[f];
                  if (val === undefined) return null;
                  return (
                    <React.Fragment key={f}>
                      <span className="dp-field-label">{f}</span>
                      <span className="dp-field-value">{renderVal(val)}</span>
                    </React.Fragment>
                  );
                }).filter(Boolean)}
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer stats */}
      {result && (
        <div className="dp-footer">
          Click a card to select the winner. Merge absorbs data from losers and soft-deletes them.
          All original data preserved in config.merged_records.
        </div>
      )}
    </div>
  );
}

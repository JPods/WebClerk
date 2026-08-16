/* LastChecked: 2026-08-14 | WhereUsed: DataBrowser detail pane (dedup/merge review) | WhoCreated: Bill+Claude */
import React, { useEffect, useState } from 'react';

// ---------------------------------------------------------------------------
// MatchCandidatesPanel — full detail cards for dedup/merge review
// ---------------------------------------------------------------------------

/** Maps DataBrowser model name → .tsx detail route (used for double-click new-tab). */
const APP_DETAIL_ROUTES: Record<string, string> = {
  order: '/order',
  invoice: '/invoice',
  proposal: '/proposal',
  purchase: '/purchase',
  workorder: '/work_order',
  work_order: '/work_order',
  receipt: '/receipt',
  requisition: '/requisition',
  payment: '/payment',
  customer: '/customer',
  item: '/item',
  contact: '/contact',
  vendor: '/vendor',
  manufacturer: '/manufacturer',
  employee: '/employee',
  rep: '/rep',
  action: '/action',
};

export type MatchPanelProps = {
  selectedRecord: any; selectedId: number | null; selectedModel: string;
  visibleFields: string[]; fieldBehaviors: Record<string, any>;
  detailFieldSpecs: any[]; detailRowSizes: Record<string, any>;
  theme: any; fontSize: number;
  onMerged: () => void; onDeleted: () => void;
};

export function MatchCandidatesPanel({
  selectedRecord, selectedId, selectedModel, visibleFields, fieldBehaviors,
  detailFieldSpecs, detailRowSizes, theme, fontSize, onMerged, onDeleted,
}: MatchPanelProps) {
  const [candidateRecords, setCandidateRecords] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const refs = selectedRecord?.refs as any;
  const candidates = refs?.contact;
  const isRisk = refs?.import === 'risk';

  // Fetch full records for each candidate
  useEffect(() => {
    if (!candidates || !Array.isArray(candidates) || candidates.length === 0) {
      setCandidateRecords([]);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const { getRecords } = await import('@/api/wcapi');
        const ids = candidates.map((c: any) => c.contact_id).filter(Boolean);
        if (ids.length === 0) { setCandidateRecords([]); return; }
        const res = await getRecords(selectedModel, { filters: { id__in: ids } });
        if (!cancelled) setCandidateRecords(res.results || []);
      } catch { if (!cancelled) setCandidateRecords([]); }
      finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, [selectedId, candidates?.length]);

  if ((!candidates || candidates.length === 0) && !isRisk) return null;

  // Pick display fields — shorter list for cards (skip large JSON fields)
  const cardFields = visibleFields.filter(f =>
    !['metadata', 'refs', 'prefs', 'actions', 'comments', 'config', 'password'].includes(f)
  ).slice(0, 12);

  const doMerge = async (candidateRecord: any, matchMeta: any) => {
    if (!confirm(`Merge into "${matchMeta?.name || candidateRecord.ida}"?\nThis updates the matched contact and deletes the risk record.`)) return;
    try {
      const { saveRecord: sr, deleteRecord: dr } = await import('@/api/wcapi');
      const rec = selectedRecord!;
      const config = rec.config || {};
      const orig = config.original_mac || {};
      const update: any = { id: candidateRecord.id };
      // Fill empty fields on the target from the risk record
      if (orig.first && !candidateRecord.name_first) update.name_first = orig.first;
      if (orig.last && !candidateRecord.name_last) update.name_last = orig.last;
      if (orig.org && !candidateRecord.company) update.company = orig.org;
      if (orig.title && !candidateRecord.title) update.title = orig.title;
      if (orig.dept && !candidateRecord.department) update.department = orig.dept;
      if (orig.addresses?.length && !candidateRecord.address_full) {
        const a = orig.addresses[0];
        update.address_full = [a.street, a.city, a.state, a.zip].filter(Boolean).join(', ');
      }
      if (orig.phones?.length && !candidateRecord.phone) {
        update.phone = orig.phones[0].number;
      }
      update.config = { ...(candidateRecord.config || {}), merged_from_risk: rec.ida, original_mac: orig };
      await sr(selectedModel, update);
      await dr(selectedModel, selectedId!);
      onMerged();
    } catch (e) { alert('Merge failed: ' + (e as Error).message); }
  };

  const doDelete = async () => {
    if (!confirm('Delete this risk record?')) return;
    try {
      const { deleteRecord: dr } = await import('@/api/wcapi');
      await dr(selectedModel, selectedId!);
      onDeleted();
    } catch (e) { alert('Delete failed: ' + (e as Error).message); }
  };

  return (
    <div className="db-match-panel">
      {/* Header with delete button for risk records */}
      <div className="db-match-header">
        <span className="db-match-title">
          {candidateRecords.length > 0 ? `Possible Matches (${candidateRecords.length})` : 'No Matches Found'}
        </span>
        {isRisk && (
          <button onClick={doDelete} className="db-match-delete-btn"
            title="Delete this risk record — garbage">
            Delete
          </button>
        )}
      </div>

      {loading && <div className="db-match-loading">Loading candidates...</div>}

      {/* Candidate detail cards */}
      {candidateRecords.map((rec, idx) => {
        const matchMeta = candidates?.find((c: any) => c.contact_id === rec.id) || {};
        return (
          <div key={rec.id} className="db-match-card">
            {/* Card header with merge/view buttons */}
            <div className="db-match-card-header">
              <div>
                <span className="db-match-card-name">
                  {rec.attention || rec.name_first && rec.name_last ? `${rec.name_first || ''} ${rec.name_last || ''}`.trim() : rec.ida}
                </span>
                <span className="db-match-card-id">#{rec.id}</span>
                {matchMeta.reason && (
                  <span className="db-match-card-reason">
                    {matchMeta.reason} (score: {matchMeta.score})
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', gap: 4 }}>
                <button onClick={() => doMerge(rec, matchMeta)} className="db-match-merge-btn">
                  Merge
                </button>
                <button onClick={() => {
                  const route = APP_DETAIL_ROUTES[selectedModel];
                  if (route) window.open(`${route}/${rec.id}`, '_blank');
                }} className="db-match-open-btn">
                  Open
                </button>
              </div>
            </div>

            {/* Card body — detail fields in 2-column grid */}
            <div className="db-match-grid">
              {cardFields.map(f => {
                const val = rec[f];
                if (val === null || val === undefined || val === '' || val === false) return null;
                const display = typeof val === 'object' ? JSON.stringify(val).slice(0, 60) : String(val).slice(0, 60);
                return (
                  <React.Fragment key={f}>
                    <span className="db-match-field-label">{f}</span>
                    <span className="db-match-field-value">{display}</span>
                  </React.Fragment>
                );
              }).filter(Boolean)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default MatchCandidatesPanel;

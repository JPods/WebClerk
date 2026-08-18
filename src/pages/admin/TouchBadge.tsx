/* LastChecked: 2026-08-17 | WhereUsed: TouchBar, detail panes | WhoCreated: Bill+Claude */
import { useState, useEffect } from 'react';

// ---------------------------------------------------------------------------
// TouchBadge — "📞 3 · 4d" or "📞 3 · -2d" (overdue = red)
//
// Shows: count of existing touches + days until next planned follow-up.
// Negative days = overdue (red). No plan = count only. Zero touches = "📞 0".
// Click opens a popover with recent touches + channel buttons.
// ---------------------------------------------------------------------------

interface TouchBadgeProps {
  /** Model name for the parent record */
  model: string;
  /** Parent record ID */
  recordId: number;
  /** Contact ID to query touches for (0 = use recordId as filter) */
  contactId?: number;
  /** Callback when badge is clicked */
  onClick?: () => void;
  /** Font size */
  fontSize?: number;
}

interface TouchSummary {
  count: number;
  daysUntilNext: number | null; // null = no plan
}

async function fetchTouchSummary(model: string, recordId: number, contactId: number): Promise<TouchSummary> {
  const { getRecords } = await import('@/api/wcapi');

  // Build filter based on model type
  const filter: Record<string, any> = { limit: 200 };
  if (model === 'contact') {
    filter.contact = recordId;
  } else if (model === 'action') {
    filter.action = recordId;
  } else if (['customer', 'vendor', 'manufacturer', 'rep', 'employee'].includes(model)) {
    filter.org_id = recordId;
    filter.org_model = model;
  } else if (contactId) {
    filter.contact = contactId;
  }

  try {
    const res = await getRecords('touch', filter) as any;
    const touches = res?.results || [];
    const count = touches.length;

    if (count === 0) return { count: 0, daysUntilNext: null };

    // Find the most recent touch with a plan > 0
    const now = Date.now();
    let nearestDue: number | null = null;

    for (const t of touches) {
      if (t.plan && t.plan > 0 && t.dt_created) {
        const dueMs = t.dt_created + (t.plan * 86400000);
        const daysLeft = Math.ceil((dueMs - now) / 86400000);
        if (nearestDue === null || daysLeft < nearestDue) {
          nearestDue = daysLeft;
        }
      }
    }

    return { count, daysUntilNext: nearestDue };
  } catch {
    return { count: 0, daysUntilNext: null };
  }
}

export const TouchBadge: React.FC<TouchBadgeProps> = ({ model, recordId, contactId = 0, onClick, fontSize = 12 }) => {
  const [summary, setSummary] = useState<TouchSummary>({ count: 0, daysUntilNext: null });
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!recordId) return;
    let cancelled = false;
    fetchTouchSummary(model, recordId, contactId).then(s => {
      if (!cancelled) { setSummary(s); setLoaded(true); }
    });
    return () => { cancelled = true; };
  }, [model, recordId, contactId]);

  if (!loaded) return null;

  const { count, daysUntilNext } = summary;
  const isOverdue = daysUntilNext !== null && daysUntilNext < 0;
  const isDueSoon = daysUntilNext !== null && daysUntilNext >= 0 && daysUntilNext <= 2;

  const badgeClass = isOverdue ? 'touch-badge touch-badge--overdue'
    : isDueSoon ? 'touch-badge touch-badge--soon'
    : 'touch-badge';

  const daysLabel = daysUntilNext !== null
    ? `${daysUntilNext > 0 ? '' : ''}${daysUntilNext}d`
    : null;

  return (
    <button className={badgeClass} onClick={onClick} style={{ fontSize: fontSize - 1 }}
      title={daysUntilNext !== null
        ? `${count} touch${count !== 1 ? 'es' : ''}, follow-up ${isOverdue ? `${Math.abs(daysUntilNext)} days overdue` : `in ${daysUntilNext} days`}`
        : `${count} touch${count !== 1 ? 'es' : ''}`}>
      📞 {count}{daysLabel !== null && <span className="touch-badge-days"> · {daysLabel}</span>}
    </button>
  );
};

export default TouchBadge;

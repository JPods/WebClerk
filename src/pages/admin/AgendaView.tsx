/**
 * AgendaView — combined touch + action daily agenda.
 *
 * Fetches pending touches (dt_next > 0) and open actions (dt_deadline > 0),
 * normalizes both to AgendaRow, sorts by date, groups into sections:
 * Overdue, Today, Tomorrow, This Week, Later.
 *
 * LastChecked: 2026-08-18 | WhereUsed: /agenda | WhoCreated: Bill+Claude
 */
import { useEffect, useState } from 'react';
import { getRecords } from '@/api/wcapi';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AgendaRow {
  type: 'touch' | 'action';
  id: number;
  date: number;
  icon: string;
  title: string;
  context: string;
  status: string;
  purpose: string;
  overdue: boolean;
  daysOut: number;
  parentModel?: string;
  parentId?: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const CHANNEL_ICONS: Record<string, string> = {
  call: '📞', email: '✉', visit: '📋', text: '💬', meeting: '🤝',
};

const DAY_MS = 86400000;

function startOfDay(epoch: number): number {
  const d = new Date(epoch);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

function normalizeTouches(touches: any[]): AgendaRow[] {
  const now = Date.now();
  const today = startOfDay(now);
  return touches
    .filter(t => t.dt_next && t.dt_next > 0)
    .map(t => {
      const daysOut = Math.ceil((t.dt_next - today) / DAY_MS);
      // Find first non-null parent for click-through
      const parents = t.refs?.parents || {};
      const parentModel = parents.customer ? 'customer'
        : parents.vendor ? 'vendor' : parents.action ? 'action'
        : parents.contact ? 'contact' : undefined;
      const parentId = parentModel ? parents[parentModel] : undefined;
      return {
        type: 'touch' as const,
        id: t.id,
        date: t.dt_next,
        icon: CHANNEL_ICONS[t.channel] || '📞',
        title: t.subject || t.summary?.slice(0, 60) || '(no subject)',
        context: t.comments?.process || '',
        status: t.outcome || '',
        purpose: t.purpose || '',
        overdue: daysOut < 0,
        daysOut,
        parentModel,
        parentId,
      };
    });
}

function normalizeActions(actions: any[]): AgendaRow[] {
  const now = Date.now();
  const today = startOfDay(now);
  return actions
    .filter(a => a.dt_deadline && a.dt_deadline > 0)
    .map(a => {
      const daysOut = Math.ceil((a.dt_deadline - today) / DAY_MS);
      return {
        type: 'action' as const,
        id: a.id,
        date: a.dt_deadline,
        icon: '🏃',
        title: typeof a.action === 'object' ? (a.action?.en || '') : String(a.action || ''),
        context: a.comments?.process || (typeof a.description === 'object' ? (a.description?.en || '') : String(a.description || '')).slice(0, 80),
        status: a.status || '',
        purpose: a.purpose || '',
        overdue: daysOut < 0,
        daysOut,
      };
    });
}

function groupRows(rows: AgendaRow[]): { label: string; rows: AgendaRow[] }[] {
  const overdue: AgendaRow[] = [];
  const today: AgendaRow[] = [];
  const tomorrow: AgendaRow[] = [];
  const thisWeek: AgendaRow[] = [];
  const later: AgendaRow[] = [];

  for (const r of rows) {
    if (r.daysOut < 0) overdue.push(r);
    else if (r.daysOut === 0) today.push(r);
    else if (r.daysOut === 1) tomorrow.push(r);
    else if (r.daysOut <= 7) thisWeek.push(r);
    else later.push(r);
  }

  const groups: { label: string; rows: AgendaRow[] }[] = [];
  if (overdue.length) groups.push({ label: 'Overdue', rows: overdue });
  if (today.length) groups.push({ label: 'Today', rows: today });
  if (tomorrow.length) groups.push({ label: 'Tomorrow', rows: tomorrow });
  if (thisWeek.length) groups.push({ label: 'This Week', rows: thisWeek });
  if (later.length) groups.push({ label: 'Later', rows: later });
  return groups;
}

function daysLabel(d: number): string {
  if (d < 0) return `${Math.abs(d)}d overdue`;
  if (d === 0) return 'due';
  return `in ${d}d`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const AgendaView: React.FC = () => {
  const [rows, setRows] = useState<AgendaRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [staffFilter, setStaffFilter] = useState('');
  const [staffOptions, setStaffOptions] = useState<{ id: string; name: string }[]>([]);

  useEffect(() => {
    (async () => {
      try {
        // Fetch staff for picker
        const staffRes = await getRecords('contact', { is_staff: true, is_active: true, limit: 200 }) as any;
        const staff = (staffRes?.results || []).map((c: any) => ({
          id: String(c.id),
          name: c.attention || `${c.name_first || ''} ${c.name_last || ''}`.trim() || `#${c.id}`,
        }));
        setStaffOptions(staff);

        // Fetch touches with dt_next > 0
        const touchRes = await getRecords('touch', { dt_next__gt: 0, limit: 200 }) as any;
        const touches = normalizeTouches(touchRes?.results || []);

        // Fetch open actions with deadlines
        const actionRes = await getRecords('action', { status__in: 'open,in_progress', dt_deadline__gt: 0, limit: 200 }) as any;
        const actions = normalizeActions(actionRes?.results || []);

        // Merge and sort by date
        const merged = [...touches, ...actions].sort((a, b) => a.date - b.date);
        setRows(merged);
      } catch (err) {
        console.error('[AgendaView] fetch failed:', err);
      }
      setLoading(false);
    })();
  }, []);

  const filteredRows = staffFilter
    ? rows // TODO: filter by assigned_to or logged_by matching staffFilter
    : rows;

  const groups = groupRows(filteredRows);
  const overdueCount = filteredRows.filter(r => r.overdue).length;
  const todayCount = filteredRows.filter(r => r.daysOut === 0).length;

  const openRecord = (row: AgendaRow) => {
    const model = row.type === 'touch' ? 'touch' : 'action';
    window.open(`/databrowser?model=${model}&id=${row.id}`, `${model}-${row.id}`);
  };

  const openParent = (row: AgendaRow) => {
    if (row.parentModel && row.parentId) {
      window.open(`/databrowser?model=${row.parentModel}&id=${row.parentId}`, `${row.parentModel}-${row.parentId}`);
    }
  };

  return (
    <div style={{ maxWidth: 700, margin: '0 auto', padding: '16px 20px', color: 'var(--db-text, #e2e8f0)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>Agenda</h2>
        {overdueCount > 0 && (
          <span style={{ background: '#e53e3e', color: '#fff', borderRadius: 10, padding: '2px 10px', fontSize: 12, fontWeight: 600 }}>
            {overdueCount} overdue
          </span>
        )}
        {todayCount > 0 && (
          <span style={{ background: '#3355FF', color: '#fff', borderRadius: 10, padding: '2px 10px', fontSize: 12, fontWeight: 600 }}>
            {todayCount} today
          </span>
        )}
        <span style={{ flex: 1 }} />
        <select value={staffFilter} onChange={(e) => setStaffFilter(e.target.value)}
          style={{ fontSize: 12, padding: '4px 8px', borderRadius: 4, border: '1px solid var(--db-border)', background: 'var(--db-surface-alt)', color: 'var(--db-text)' }}>
          <option value="">All staff</option>
          {staffOptions.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </div>

      {loading ? (
        <div style={{ color: 'var(--db-text-muted)', padding: 20 }}>Loading...</div>
      ) : groups.length === 0 ? (
        <div style={{ color: 'var(--db-text-muted)', padding: 20 }}>No pending touches or actions.</div>
      ) : (
        groups.map(group => (
          <div key={group.label} style={{ marginBottom: 20 }}>
            {/* Section header */}
            <div style={{
              fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1,
              color: group.label === 'Overdue' ? '#e53e3e' : 'var(--db-text-muted)',
              borderBottom: `2px solid ${group.label === 'Overdue' ? '#e53e3e' : 'var(--db-border)'}`,
              paddingBottom: 4, marginBottom: 8,
            }}>
              {group.label}
            </div>

            {/* Rows */}
            {group.rows.map(row => (
              <div key={`${row.type}-${row.id}`} style={{ marginBottom: 10 }}>
                {/* Line 1: icon + title + purpose + date */}
                <div
                  onClick={() => openRecord(row)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer',
                    padding: '4px 8px', borderRadius: 4,
                    transition: 'background 0.15s',
                  }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = 'color-mix(in srgb, var(--db-accent) 10%, transparent)'; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                >
                  <span style={{ fontSize: 16, width: 24, textAlign: 'center' }}>{row.icon}</span>
                  <span style={{ fontWeight: 600, fontSize: 13, flex: 1 }}>{row.title}</span>
                  {row.purpose && (
                    <span style={{ fontSize: 11, color: 'var(--db-text-muted)', padding: '1px 6px', border: '1px solid var(--db-border)', borderRadius: 3 }}>
                      {row.purpose}
                    </span>
                  )}
                  {row.status && (
                    <span style={{ fontSize: 11, color: 'var(--db-text-muted)' }}>{row.status}</span>
                  )}
                  <span style={{
                    fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap',
                    color: row.overdue ? '#e53e3e' : row.daysOut === 0 ? '#3355FF' : 'var(--db-text-muted)',
                  }}>
                    {row.overdue ? '⚠ ' : ''}{daysLabel(row.daysOut)}
                  </span>
                </div>

                {/* Line 2: context (comments.process) — click opens parent */}
                {row.context && (
                  <div
                    onClick={() => openParent(row)}
                    style={{
                      paddingLeft: 40, fontSize: 11, color: 'var(--db-text-muted)',
                      cursor: row.parentModel ? 'pointer' : 'default',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}
                    title={row.context}
                  >
                    {row.context}
                  </div>
                )}
              </div>
            ))}
          </div>
        ))
      )}
    </div>
  );
};

export default AgendaView;

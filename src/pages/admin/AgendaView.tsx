/**
 * AgendaView — combined touch + action daily agenda with trend cards.
 *
 * Layout:
 *   Toolbar row 1: title + badges + Alice feedback
 *   Toolbar row 2: staff chip filter bar
 *   Summary cards: touch + action trends (year/quarter/month/forecast)
 *   Scrollable list: Overdue / Today / Tomorrow / This Week / Later
 *
 * LastChecked: 2026-08-21 | WhereUsed: /agenda | WhoCreated: Bill+Claude
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { getRecords, saveRecord } from '@/api/wcapi';

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
  _raw: any;
}

interface PeriodStat {
  label: string;
  count: number;
  avg?: number;       // monthly average (past periods)
  pace?: string;      // "ahead" | "on track" | "behind" (this month only)
  forecast?: boolean;  // true for future periods
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const CHANNEL_ICONS: Record<string, string> = {
  call: '\u{1F4DE}', email: '\u2709', visit: '\u{1F4CB}', text: '\u{1F4AC}', meeting: '\u{1F91D}',
};

const DAY_MS = 86400000;

function startOfDay(epoch: number): number {
  const d = new Date(epoch);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

function epochRange(offsetMonths: number, spanMonths: number): { gte: number; lt: number } {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth() + offsetMonths, 1);
  const end = new Date(now.getFullYear(), now.getMonth() + offsetMonths + spanMonths, 1);
  return { gte: start.getTime(), lt: end.getTime() };
}

function normalizeTouches(touches: any[]): AgendaRow[] {
  const today = startOfDay(Date.now());
  return touches
    .filter(t => t.dt_next && t.dt_next > 0)
    .map(t => {
      const daysOut = Math.ceil((t.dt_next - today) / DAY_MS);
      const parents = t.refs?.parents || {};
      const parentModel = parents.customer ? 'customer'
        : parents.vendor ? 'vendor' : parents.action ? 'action'
        : parents.contact ? 'contact' : undefined;
      const parentId = parentModel ? parents[parentModel] : undefined;
      return {
        type: 'touch' as const, id: t.id, date: t.dt_next,
        icon: CHANNEL_ICONS[t.channel] || '\u{1F4DE}',
        title: t.subject || t.summary?.slice(0, 60) || '(no subject)',
        context: t.comments?.process || '',
        status: t.outcome || '', purpose: t.purpose || '',
        overdue: daysOut < 0, daysOut, parentModel, parentId, _raw: t,
      };
    });
}

function normalizeActions(actions: any[]): AgendaRow[] {
  const today = startOfDay(Date.now());
  return actions
    .filter(a => a.dt_deadline && a.dt_deadline > 0)
    .map(a => {
      const daysOut = Math.ceil((a.dt_deadline - today) / DAY_MS);
      return {
        type: 'action' as const, id: a.id, date: a.dt_deadline, icon: '\u{1F3C3}',
        title: typeof a.action === 'object' ? (a.action?.en || '') : String(a.action || ''),
        context: a.comments?.process || (typeof a.description === 'object' ? (a.description?.en || '') : String(a.description || '')).slice(0, 80),
        status: a.status || '', purpose: a.purpose || '',
        overdue: daysOut < 0, daysOut, _raw: a,
      };
    });
}

function groupRows(rows: AgendaRow[]): { label: string; rows: AgendaRow[] }[] {
  const buckets: Record<string, AgendaRow[]> = { Overdue: [], Today: [], Tomorrow: [], 'This Week': [], Later: [] };
  for (const r of rows) {
    if (r.daysOut < 0) buckets.Overdue.push(r);
    else if (r.daysOut === 0) buckets.Today.push(r);
    else if (r.daysOut === 1) buckets.Tomorrow.push(r);
    else if (r.daysOut <= 7) buckets['This Week'].push(r);
    else buckets.Later.push(r);
  }
  return Object.entries(buckets).filter(([, rows]) => rows.length > 0).map(([label, rows]) => ({ label, rows }));
}

function daysLabel(d: number): string {
  if (d < 0) return `${Math.abs(d)}d overdue`;
  if (d === 0) return 'due';
  return `in ${d}d`;
}

// ---------------------------------------------------------------------------
// Summary card fetching
// ---------------------------------------------------------------------------

async function fetchPeriodCounts(model: string, dateField: string, statusFilter?: Record<string, string>): Promise<PeriodStat[]> {
  const now = new Date();
  const thisMonthDay = now.getDate();
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();

  // Define periods: [label, offsetMonths, spanMonths, isForecast]
  const periods: [string, number, number, boolean][] = [
    ['Past Year', -12, 12, false],
    ['Past Qtr', -3, 3, false],
    ['Past Month', -1, 1, false],
    ['This Month', 0, 1, false],
    ['Next Month', 1, 1, true],
    ['Next Qtr', 1, 3, true],
  ];

  const results: PeriodStat[] = [];

  for (const [label, offset, span, isForecast] of periods) {
    const { gte, lt } = epochRange(offset, span);
    const params: Record<string, any> = {
      [`${dateField}__gte`]: gte,
      [`${dateField}__lt`]: lt,
      limit: 1,
      ...statusFilter,
    };
    try {
      const res = await getRecords(model, params) as any;
      const count = res?.count ?? res?.results?.length ?? 0;

      const stat: PeriodStat = { label, count, forecast: isForecast };

      // Monthly average for past periods
      if (!isForecast && span > 1) {
        stat.avg = Math.round(count / span);
      }

      // Pace indicator for "This Month"
      if (label === 'This Month' && results.length >= 3) {
        const pastMonthCount = results[2].count; // Past Month
        if (pastMonthCount > 0) {
          const expectedSoFar = pastMonthCount * (thisMonthDay / daysInMonth);
          if (count >= expectedSoFar * 1.15) stat.pace = 'ahead';
          else if (count >= expectedSoFar * 0.85) stat.pace = 'on track';
          else stat.pace = 'behind';
        }
      }

      results.push(stat);
    } catch {
      results.push({ label, count: 0, forecast: isForecast });
    }
  }

  return results;
}

// ---------------------------------------------------------------------------
// Trend Card Component
// ---------------------------------------------------------------------------

const TrendCard: React.FC<{ stat: PeriodStat }> = ({ stat }) => {
  const paceColor = stat.pace === 'ahead' ? 'text-emerald-400'
    : stat.pace === 'behind' ? 'text-red-400'
    : stat.pace === 'on track' ? 'text-blue-400' : '';

  return (
    <div className={`flex flex-col items-center px-3 py-2 rounded-lg border min-w-[90px] ${
      stat.forecast
        ? 'border-slate-600/50 bg-slate-800/30'
        : 'border-slate-600 bg-slate-800/60'
    }`}>
      <span className="text-[10px] text-slate-500 font-medium uppercase tracking-wide">{stat.label}</span>
      <span className={`text-lg font-bold ${stat.forecast ? 'text-slate-400' : 'text-slate-100'}`}>
        {stat.count}
      </span>
      {stat.avg != null && (
        <span className="text-[10px] text-slate-500">{stat.avg}/mo avg</span>
      )}
      {stat.pace && (
        <span className={`text-[10px] font-semibold ${paceColor}`}>{stat.pace}</span>
      )}
      {stat.forecast && !stat.pace && (
        <span className="text-[10px] text-slate-600">scheduled</span>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Alice Feedback Badge
// ---------------------------------------------------------------------------

const AliceFeedbackBadge: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);

  const handleSend = async () => {
    if (!text.trim()) return;
    setSending(true);
    try {
      await saveRecord('note', {
        subject: 'Agenda feedback',
        body: text.trim(),
        purpose: 'alice_log',
        source: 'agenda',
      });
      setText('');
      setOpen(false);
    } catch {
      // silent — Alice will catch it on next sweep
    }
    setSending(false);
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        title="Tell Alice what would be more helpful"
        className="flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-violet-600/20 text-violet-300 hover:bg-violet-600/30 transition-colors"
      >
        <span className="text-sm">A</span>
        <span>Feedback</span>
      </button>
    );
  }

  return (
    <div className="flex items-center gap-1.5">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') handleSend(); if (e.key === 'Escape') setOpen(false); }}
        placeholder="What would be more helpful?"
        autoFocus
        className="text-xs px-2 py-1 rounded border border-violet-500/50 bg-slate-800 text-slate-200 placeholder-slate-500 w-64 focus:outline-none focus:border-violet-400"
      />
      <button
        onClick={handleSend}
        disabled={sending || !text.trim()}
        className="px-2 py-1 rounded text-xs font-medium bg-violet-600 text-white hover:bg-violet-500 disabled:opacity-40"
      >
        {sending ? '...' : 'Send'}
      </button>
      <button
        onClick={() => { setOpen(false); setText(''); }}
        className="text-slate-500 hover:text-slate-300 text-xs px-1"
      >
        \u2715
      </button>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

const AgendaView: React.FC = () => {
  const [rows, setRows] = useState<AgendaRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedStaff, setSelectedStaff] = useState<Set<string>>(new Set());
  const [staffOptions, setStaffOptions] = useState<{ id: string; name: string; initials: string }[]>([]);
  const [touchStats, setTouchStats] = useState<PeriodStat[]>([]);
  const [actionStats, setActionStats] = useState<PeriodStat[]>([]);
  const [statsLoading, setStatsLoading] = useState(true);

  // Fetch agenda rows
  useEffect(() => {
    (async () => {
      try {
        const staffRes = await getRecords('contact', { is_staff: true, is_active: true, limit: 200 }) as any;
        const staff = (staffRes?.results || []).map((c: any) => {
          const name = c.attention || `${c.name_first || ''} ${c.name_last || ''}`.trim() || `#${c.id}`;
          const parts = name.split(/\s+/);
          const initials = parts.length > 1
            ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
            : name.slice(0, 2).toUpperCase();
          return { id: String(c.id), name, initials };
        });
        setStaffOptions(staff);

        const touchRes = await getRecords('touch', { dt_next__gt: 0, limit: 200 }) as any;
        const touches = normalizeTouches(touchRes?.results || []);

        const actionRes = await getRecords('action', { status__in: 'open,in_progress', dt_deadline__gt: 0, limit: 200 }) as any;
        const actions = normalizeActions(actionRes?.results || []);

        const merged = [...touches, ...actions].sort((a, b) => a.date - b.date);
        setRows(merged);
      } catch (err) {
        console.error('[AgendaView] fetch failed:', err);
      }
      setLoading(false);
    })();
  }, []);

  // Fetch summary stats
  useEffect(() => {
    (async () => {
      setStatsLoading(true);
      const [ts, as] = await Promise.all([
        fetchPeriodCounts('touch', 'dt_completed', { outcome__in: 'completed,reached,left_message' }),
        fetchPeriodCounts('action', 'dt_completed', { status: 'complete' }),
      ]);
      // For future periods, re-fetch using deadline/dt_next (scheduled, not completed)
      const [tsFuture, asFuture] = await Promise.all([
        fetchPeriodCounts('touch', 'dt_next'),
        fetchPeriodCounts('action', 'dt_deadline'),
      ]);
      // Replace forecast counts with scheduled counts
      ts[4] = { ...ts[4], count: tsFuture[4].count };
      ts[5] = { ...ts[5], count: tsFuture[5].count };
      as[4] = { ...as[4], count: asFuture[4].count };
      as[5] = { ...as[5], count: asFuture[5].count };
      setTouchStats(ts);
      setActionStats(as);
      setStatsLoading(false);
    })();
  }, []);

  const toggleStaff = (id: string) => {
    setSelectedStaff(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const filteredRows = selectedStaff.size > 0
    ? rows.filter(r => {
        const raw = r._raw;
        if (!raw) return true;
        const assignedTo = raw.assigned_to;
        if (Array.isArray(assignedTo) && assignedTo.some((a: any) => selectedStaff.has(String(a.id)))) return true;
        if (assignedTo && selectedStaff.has(String(assignedTo))) return true;
        if (raw.logged_by && selectedStaff.has(String(raw.logged_by))) return true;
        if (raw.contact_id && selectedStaff.has(String(raw.contact_id))) return true;
        return false;
      })
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
    <div className="flex flex-col h-full overflow-hidden text-[var(--db-text,#e2e8f0)]">
      {/* Toolbar row 1: title + badges + Alice feedback */}
      <div className="flex items-center gap-3 px-5 py-2 flex-shrink-0 border-b border-[var(--db-border,#334155)]">
        <h2 className="text-lg font-bold m-0">Agenda</h2>
        {overdueCount > 0 && (
          <span className="bg-red-600 text-white rounded-xl px-2.5 py-0.5 text-xs font-semibold">
            {overdueCount} overdue
          </span>
        )}
        {todayCount > 0 && (
          <span className="bg-blue-600 text-white rounded-xl px-2.5 py-0.5 text-xs font-semibold">
            {todayCount} today
          </span>
        )}
        <span className="flex-1" />
        <AliceFeedbackBadge />
        {selectedStaff.size > 0 && (
          <button
            onClick={() => setSelectedStaff(new Set())}
            className="text-xs text-slate-400 hover:text-slate-200 px-2 py-1 rounded border border-slate-600"
          >All</button>
        )}
      </div>

      {/* Toolbar row 2: staff chip filter */}
      {staffOptions.length > 0 && (
        <div className="flex flex-wrap gap-1.5 px-5 py-2 flex-shrink-0 border-b border-[var(--db-border,#334155)] bg-[var(--db-surface-alt,#1e293b)]">
          {staffOptions.map(s => {
            const active = selectedStaff.has(s.id);
            return (
              <button
                key={s.id}
                onClick={() => toggleStaff(s.id)}
                title={s.name}
                className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                  active
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-700/50 text-slate-400 hover:bg-slate-600/50 hover:text-slate-200'
                }`}
              >
                {s.name}
              </button>
            );
          })}
        </div>
      )}

      {/* Summary trend cards */}
      <div className="flex-shrink-0 px-5 py-3 border-b border-[var(--db-border,#334155)] space-y-2">
        {/* Touches row */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold uppercase tracking-wide text-slate-500 w-16 flex-shrink-0">Touches</span>
          <div className="flex gap-1.5 overflow-x-auto">
            {statsLoading
              ? <span className="text-xs text-slate-600">Loading...</span>
              : touchStats.map(s => <TrendCard key={s.label} stat={s} />)
            }
          </div>
        </div>
        {/* Actions row */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold uppercase tracking-wide text-slate-500 w-16 flex-shrink-0">Actions</span>
          <div className="flex gap-1.5 overflow-x-auto">
            {statsLoading
              ? <span className="text-xs text-slate-600">Loading...</span>
              : actionStats.map(s => <TrendCard key={s.label} stat={s} />)
            }
          </div>
        </div>
      </div>

      {/* Scrollable agenda list */}
      <div className="flex-1 overflow-y-auto px-5 py-3" style={{ maxWidth: 700, margin: '0 auto', width: '100%' }}>
      {loading ? (
        <div className="text-[var(--db-text-muted)] p-5">Loading...</div>
      ) : groups.length === 0 ? (
        <div className="text-[var(--db-text-muted)] p-5">No pending touches or actions.</div>
      ) : (
        groups.map(group => (
          <div key={group.label} className="mb-5">
            {/* Section header */}
            <div className={`text-[11px] font-bold uppercase tracking-wide pb-1 mb-2 border-b-2 ${
              group.label === 'Overdue'
                ? 'text-red-500 border-red-500'
                : 'text-[var(--db-text-muted)] border-[var(--db-border)]'
            }`}>
              {group.label}
            </div>

            {/* Rows */}
            {group.rows.map(row => (
              <div key={`${row.type}-${row.id}`} className="mb-2.5">
                {/* Line 1: icon + title + purpose + date */}
                <div
                  onClick={() => openRecord(row)}
                  className="flex items-center gap-2 cursor-pointer px-2 py-1 rounded hover:bg-[color-mix(in_srgb,var(--db-accent)_10%,transparent)]"
                >
                  <span className="text-base w-6 text-center">{row.icon}</span>
                  <span className="font-semibold text-[13px] flex-1">{row.title}</span>
                  {row.purpose && (
                    <span className="text-[11px] text-[var(--db-text-muted)] px-1.5 py-px border border-[var(--db-border)] rounded">
                      {row.purpose}
                    </span>
                  )}
                  {row.status && (
                    <span className="text-[11px] text-[var(--db-text-muted)]">{row.status}</span>
                  )}
                  <span className={`text-[11px] font-semibold whitespace-nowrap ${
                    row.overdue ? 'text-red-500' : row.daysOut === 0 ? 'text-blue-500' : 'text-[var(--db-text-muted)]'
                  }`}>
                    {row.overdue ? '\u26A0 ' : ''}{daysLabel(row.daysOut)}
                  </span>
                </div>

                {/* Line 2: context — click opens parent */}
                {row.context && (
                  <div
                    onClick={() => openParent(row)}
                    className={`pl-10 text-[11px] text-[var(--db-text-muted)] truncate ${
                      row.parentModel ? 'cursor-pointer' : ''
                    }`}
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
    </div>
  );
};

export default AgendaView;

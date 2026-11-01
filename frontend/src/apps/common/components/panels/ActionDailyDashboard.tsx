/**
 * ActionDailyDashboard — Staff daily cockpit.
 *
 * Shows a staff member's actions for a date range, aggregates the dollar
 * values from refs.links into summary cards. Click a card to see transactions.
 * Click a transaction to open it in a new window.
 *
 * Data flow:
 *   1. Fetch actions for selected staff + date range
 *   2. Read action.refs.links (denormalized transaction summaries)
 *   3. Aggregate by model type into summary cards
 *   4. Click card → expand to show transactions → click transaction → new window
 *
 * All styling via --db-* CSS variables.
 */
import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { getRecords } from '@/api/wcapi';
import { getModelDetailPath } from './getModelDetailPath';
import { formatCurrency } from '@/utils/stringUtils';
import { DbColumns, type DbColumnDef } from './DbColumns';
import { formatCell } from './cellFormat';
import { getUI } from '@/utils/contactUI';

// ── Types ────────────────────────────────────────────────────────────────────

interface LinkedRecord {
  id: number;
  ida?: string;
  company?: string;
  name?: string;
  totals?: { total?: number; balance?: number };
  amount?: number;
  status?: string;
  model: string;
}

interface ActionRecord {
  id: number;
  ida: string;
  action: string;
  description?: string;
  status: string;
  priority: number;
  assigned_to?: string;
  contact_id?: number;
  dt_created?: string;
  refs?: { links?: Record<string, LinkedRecord[]> };
}

interface CardSummary {
  model: string;
  label: string;
  count: number;
  total: number;
  records: LinkedRecord[];
}

interface StaffOption {
  id: number;
  name: string;
  ida?: string;
}

interface ActionDailyDashboardProps {
  defaultStaffId?: number;
  defaultDate?: string;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const MODEL_LABELS: Record<string, string> = {
  order: 'Orders',
  invoice: 'Invoices',
  purchase: 'Purchases',
  cash: 'Cash',
  contact: 'Contacts',
  customer: 'Customers',
};

const MODEL_ORDER = ['order', 'invoice', 'purchase', 'cash', 'customer', 'contact'];

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}


function aggregateLinks(actions: ActionRecord[]): CardSummary[] {
  const map = new Map<string, { records: LinkedRecord[]; seen: Set<number> }>();

  for (const a of actions) {
    const links = a.refs?.links || {};
    for (const [model, records] of Object.entries(links)) {
      if (!Array.isArray(records)) continue;
      if (!map.has(model)) map.set(model, { records: [], seen: new Set() });
      const entry = map.get(model)!;
      for (const r of records) {
        if (r.id && !entry.seen.has(r.id)) {
          entry.seen.add(r.id);
          entry.records.push({ ...r, model });
        }
      }
    }
  }

  return MODEL_ORDER
    .filter((m) => map.has(m))
    .map((m) => {
      const { records } = map.get(m)!;
      const total = records.reduce((sum, r) => sum + (r.totals?.total ?? 0), 0);
      return {
        model: m,
        label: MODEL_LABELS[m] || m,
        count: records.length,
        total,
        records,
      };
    });
}

// ── DbCard ───────────────────────────────────────────────────────────────────

const DbCard: React.FC<{
  label: string;
  count: number;
  value?: number;
  expanded: boolean;
  onClick: () => void;
  children?: React.ReactNode;
}> = ({ label, count, value, expanded, onClick, children }) => {
  const active = getUI<string>('theme.active', 'dark');
  const baseFontSize = getUI<number>(`theme.${active}.font.size`, 13);
  return (
  <div
    className="db-panel"
    style={{
      borderRadius: 6,
      minWidth: 120,
      flex: 1,
      cursor: 'pointer',
      transition: 'border-color 0.15s',
      borderColor: expanded ? 'var(--db-accent)' : undefined,
    }}
    onClick={onClick}
  >
    <div style={{ padding: '10px 14px' }}>
      <div className="db-text-muted" style={{ fontSize: baseFontSize - 3, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
        {label}
      </div>
      <div className="db-text" style={{ fontSize: baseFontSize + 9, fontWeight: 700 }}>
        {count}
      </div>
      {value != null && value > 0 && (
        <div className="db-text-green" style={{ fontSize: baseFontSize - 1, fontWeight: 600, marginTop: 2 }}>
          {formatCurrency(value)}
        </div>
      )}
    </div>
    {expanded && children && (
      <div className="db-border-top">
        {children}
      </div>
    )}
  </div>
  );
};

// ── Main Component ───────────────────────────────────────────────────────────

const CARD_COLUMNS: DbColumnDef<any>[] = [
  { key: 'ida', label: 'ida', width: 90, render: (r) => <strong>{r.ida || `#${r.id}`}</strong> },
  { key: 'name', label: 'name', render: (r) => r.company || r.name || '' },
  { key: 'total', label: 'total', align: 'right', width: 90, render: (r) => (r.totals?.total != null ? formatCurrency(r.totals.total) : '') },
  { key: 'status', label: 'status', width: 80, render: (r) => r.status || '' },
];

const STATUS_COLOR: Record<string, string> = {
  in_progress: 'var(--db-accent)', completed: 'var(--db-accent-green)', waiting: 'var(--db-accent-gold)',
};

const ActionDailyDashboard: React.FC<ActionDailyDashboardProps> = ({
  defaultStaffId,
  defaultDate,
}) => {
  const active = getUI<string>('theme.active', 'dark');
  const baseFontSize = getUI<number>(`theme.${active}.font.size`, 13);
  const [staffList, setStaffList] = useState<StaffOption[]>([]);
  const [selectedStaffId, setSelectedStaffId] = useState<number | null>(defaultStaffId ?? null);
  const [dateFrom, setDateFrom] = useState(defaultDate || todayISO());
  const [dateTo, setDateTo] = useState(defaultDate || todayISO());
  const [actions, setActions] = useState<ActionRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedCard, setExpandedCard] = useState<string | null>(null);

  // Load staff list
  useEffect(() => {
    (async () => {
      try {
        const res = await getRecords('contact', { is_staff: true, is_active: true }) as any;
        const contacts = res?.results || res || [];
        setStaffList(
          contacts.map((c: any) => ({
            id: c.id,
            name: `${c.name_first || ''} ${c.name_last || ''}`.trim() || c.ida || `#${c.id}`,
            ida: c.ida,
          }))
        );
        if (!selectedStaffId && contacts.length > 0) {
          setSelectedStaffId(contacts[0].id);
        }
      } catch {
        // Staff list unavailable
      }
    })();
  }, []);

  // Fetch actions for selected staff + date range
  const fetchActions = useCallback(async () => {
    if (!selectedStaffId) return;
    setLoading(true);
    try {
      const res = await getRecords('action', {
        contact_id: selectedStaffId,
        dt_created__gte: `${dateFrom}T00:00:00Z`,
        dt_created__lte: `${dateTo}T23:59:59Z`,
      }) as any;
      setActions(res?.results || res || []);
    } catch {
      setActions([]);
    }
    setLoading(false);
  }, [selectedStaffId, dateFrom, dateTo]);

  useEffect(() => { fetchActions(); }, [fetchActions]);

  // Aggregate
  const cards = useMemo(() => aggregateLinks(actions), [actions]);

  // Open transaction in new window
  const openTransaction = (model: string, id: number) => {
    const path = getModelDetailPath(model, id);
    window.open(path, `${model}-${id}`, 'width=1000,height=700');
  };

  // Date presets
  const setPreset = (preset: string) => {
    const today = todayISO();
    const d = new Date();
    switch (preset) {
      case 'today':
        setDateFrom(today); setDateTo(today); break;
      case 'yesterday': {
        d.setDate(d.getDate() - 1);
        const y = d.toISOString().slice(0, 10);
        setDateFrom(y); setDateTo(y); break;
      }
      case 'week': {
        d.setDate(d.getDate() - d.getDay());
        setDateFrom(d.toISOString().slice(0, 10)); setDateTo(today); break;
      }
      case 'month': {
        setDateFrom(`${today.slice(0, 7)}-01`); setDateTo(today); break;
      }
    }
  };

  const actionColumns: DbColumnDef<ActionRecord>[] = [
    { key: 'priority', label: 'P', align: 'center', width: 30, render: (a) => (
        <span style={{ fontWeight: 700, color: a.priority === 1 ? 'var(--db-accent-red)' : a.priority === 2 ? 'var(--db-accent-gold)' : 'var(--db-text-dim)' }}>
          {a.priority === 1 ? '!' : a.priority === 2 ? '·' : ''}</span>
      ) },
    { key: 'action', label: 'Action', render: (a) => formatCell(a.action, 'action') },
    { key: 'status', label: 'Status', width: 100, render: (a) => (
        <span style={{ fontWeight: 600, textTransform: 'uppercase', color: STATUS_COLOR[a.status as string] ?? 'var(--db-text-dim)' }}>{a.status}</span>
      ) },
    { key: 'links', label: 'Links', render: (a) => {
        const links = Object.entries(a.refs?.links || {})
          .filter(([, v]) => Array.isArray(v) && v.length > 0)
          .map(([model, records]) => ({ ...(records as LinkedRecord[])[0], model }));
        return (
          <span className="flex gap-2">
            {links.map((lm) => (
              <span key={`${lm.model}-${lm.id}`} className="db-bg-surface-alt"
                style={{ padding: '1px 6px', borderRadius: 3, border: '1px solid var(--db-border-light)', cursor: 'pointer', whiteSpace: 'nowrap' }}
                title={`Open ${lm.model} ${lm.ida || lm.id}`}
                onClick={(e) => { e.stopPropagation(); openTransaction(lm.model, lm.id); }}>
                {lm.model.slice(0, 3)}{lm.totals?.total != null && ` $${Math.round(lm.totals.total)}`}
              </span>
            ))}
          </span>
        );
      } },
  ];


  return (
    <div className="db-bg db-text" style={{ padding: 16 }}>
      {/* ── Toolbar ──────────────────────────────────────────── */}
      <div className="flex items-center gap-3 flex-wrap" style={{ marginBottom: 16 }}>
        <span style={{ fontSize: baseFontSize + 1, fontWeight: 700 }}>Action Dashboard</span>

        {/* Staff picker */}
        <select data-wc="select"
          value={selectedStaffId ?? ''}
          onChange={(e) => setSelectedStaffId(Number(e.target.value))}
          className="db-panel-input-text"
          style={{
            fontSize: baseFontSize - 1, padding: '4px 8px', borderRadius: 4,
          }}
        >
          {staffList.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>

        {/* Date presets */}
        {['today', 'yesterday', 'week', 'month'].map((p) => (
          <button
            key={p}
            onClick={() => setPreset(p)}
            className="db-text-muted"
            style={{
              fontSize: baseFontSize - 3, padding: '3px 8px', borderRadius: 3,
              background: 'var(--db-btn-bg)',
              border: '1px solid var(--db-border)', cursor: 'pointer',
              textTransform: 'capitalize',
            }}
          >
            {p}
          </button>
        ))}

        {/* Date inputs */}
        <input
          type="date" value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          className="db-panel-input-text"
          style={{ fontSize: baseFontSize - 2, padding: '3px 6px', borderRadius: 3 }}
        />
        <span className="db-text-dim" style={{ fontSize: baseFontSize - 2 }}>to</span>
        <input
          type="date" value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          className="db-panel-input-text"
          style={{ fontSize: baseFontSize - 2, padding: '3px 6px', borderRadius: 3 }}
        />

        <span className="db-text-dim" style={{ fontSize: baseFontSize - 2, marginLeft: 'auto' }}>
          {loading ? 'Loading...' : `${actions.length} actions`}
        </span>
      </div>

      {/* ── Summary Cards ────────────────────────────────────── */}
      {cards.length > 0 && (
        <div className="flex gap-3 flex-wrap" style={{ marginBottom: 16 }}>
          {cards.map((card) => (
            <DbCard
              key={card.model}
              label={card.label}
              count={card.count}
              value={card.total}
              expanded={expandedCard === card.model}
              onClick={() => setExpandedCard(expandedCard === card.model ? null : card.model)}
            >
              {/* Expanded: its transactions on the shared list (DbColumns); a double-click opens one */}
              <div onClick={(e) => e.stopPropagation()}>
                <DbColumns<any>
                  storageKey={`daily:card:${card.model}`}
                  columns={CARD_COLUMNS}
                  data={card.records}
                  rowKey={(r) => `${r.model}-${r.id}`}
                  compact
                  onOpenRow={(r) => openTransaction(r.model, r.id)}
                />
              </div>
            </DbCard>
          ))}
        </div>
      )}

      {/* ── Actions List: the shared list (DbColumns) in its panel frame ── */}
      <DbColumns<ActionRecord>
        storageKey="daily:actions"
        sectionLabel="Actions"
        columns={actionColumns}
        data={actions}
        rowKey={(a) => a.id}
        compact
        loading={loading}
        emptyMessage="No actions for this period"
      />
    </div>
  );
};

export default ActionDailyDashboard;

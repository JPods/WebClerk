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

// ── Types ────────────────────────────────────────────────────────────────────

interface LinkedRecord {
  id: number;
  ida?: string;
  company?: string;
  name?: string;
  total?: number;
  balance?: number;
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
  payment: 'Payments',
  contact: 'Contacts',
  customer: 'Customers',
};

const MODEL_ORDER = ['order', 'invoice', 'purchase', 'payment', 'customer', 'contact'];

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function formatCurrency(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(n);
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
      const total = records.reduce((sum, r) => sum + (r.totals?.total ?? r.amount ?? 0), 0);
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
}> = ({ label, count, value, expanded, onClick, children }) => (
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
      <div className="db-text-muted" style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
        {label}
      </div>
      <div className="db-text" style={{ fontSize: 22, fontWeight: 700 }}>
        {count}
      </div>
      {value != null && value > 0 && (
        <div className="db-text-green" style={{ fontSize: 12, fontWeight: 600, marginTop: 2 }}>
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

// ── Main Component ───────────────────────────────────────────────────────────

const ActionDailyDashboard: React.FC<ActionDailyDashboardProps> = ({
  defaultStaffId,
  defaultDate,
}) => {
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

  return (
    <div className="db-bg db-text" style={{ padding: 16 }}>
      {/* ── Toolbar ──────────────────────────────────────────── */}
      <div className="flex items-center gap-3 flex-wrap" style={{ marginBottom: 16 }}>
        <span style={{ fontSize: 14, fontWeight: 700 }}>Action Dashboard</span>

        {/* Staff picker */}
        <select
          value={selectedStaffId ?? ''}
          onChange={(e) => setSelectedStaffId(Number(e.target.value))}
          className="db-panel-input-text"
          style={{
            fontSize: 12, padding: '4px 8px', borderRadius: 4,
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
              fontSize: 10, padding: '3px 8px', borderRadius: 3,
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
          style={{ fontSize: 11, padding: '3px 6px', borderRadius: 3 }}
        />
        <span className="db-text-dim" style={{ fontSize: 11 }}>to</span>
        <input
          type="date" value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          className="db-panel-input-text"
          style={{ fontSize: 11, padding: '3px 6px', borderRadius: 3 }}
        />

        <span className="db-text-dim" style={{ fontSize: 11, marginLeft: 'auto' }}>
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
              {/* Expanded: list of individual transactions */}
              {card.records.map((r) => (
                <div
                  key={`${r.model}-${r.id}`}
                  className="db-list-row"
                  style={{ padding: '6px 14px', fontSize: 11, cursor: 'pointer' }}
                  onClick={(e) => { e.stopPropagation(); openTransaction(r.model, r.id); }}
                >
                  <span style={{ fontWeight: 600, marginRight: 8 }}>{r.ida || `#${r.id}`}</span>
                  <span className="db-text-muted" style={{ flex: 1 }}>
                    {r.company || r.name || ''}
                  </span>
                  {(r.totals?.total ?? r.amount) != null && (
                    <span style={{ fontWeight: 600, marginLeft: 8 }}>
                      {formatCurrency(r.totals?.total ?? r.amount ?? 0)}
                    </span>
                  )}
                  {r.status && (
                    <span className="db-text-dim" style={{ fontSize: 10, marginLeft: 8 }}>
                      {r.status}
                    </span>
                  )}
                  <span className="db-text-dim" style={{ marginLeft: 8 }}>↗</span>
                </div>
              ))}
            </DbCard>
          ))}
        </div>
      )}

      {/* ── Actions List ─────────────────────────────────────── */}
      <div>
        <div className="db-section-header" style={{ cursor: 'default' }}>
          <span className="db-section-header__label">Actions</span>
          <span className="db-section-header__count">({actions.length})</span>
        </div>

        {/* Column headers */}
        <div className="db-list-header">
          <span className="db-list-header__cell" style={{ width: 30, flexShrink: 0 }}>P</span>
          <span className="db-list-header__cell" style={{ flex: 2 }}>Action</span>
          <span className="db-list-header__cell" style={{ width: 90, flexShrink: 0 }}>Status</span>
          <span className="db-list-header__cell" style={{ flex: 1 }}>Links</span>
        </div>

        {actions.length === 0 && !loading && (
          <div className="db-list-empty">No actions for this period</div>
        )}

        {actions.map((a) => {
          const links = a.refs?.links || {};
          const linkModels = Object.entries(links)
            .filter(([, v]) => Array.isArray(v) && v.length > 0)
            .map(([model, records]) => {
              const r = (records as LinkedRecord[])[0];
              const value = r.totals?.total ?? r.amount;
              return { model, ida: r.ida, value, id: r.id };
            });

          return (
            <div key={a.id} className="db-list-row" style={{ padding: '6px 12px', fontSize: 12 }}>
              {/* Priority */}
              <span style={{
                width: 30, flexShrink: 0, textAlign: 'center',
                fontWeight: 700, fontSize: 11,
                color: a.priority === 1 ? 'var(--db-accent-red)'
                     : a.priority === 2 ? 'var(--db-accent-gold)'
                     : 'var(--db-text-dim)',
              }}>
                {a.priority === 1 ? '!' : a.priority === 2 ? '·' : ''}
              </span>

              {/* Action name */}
              <span style={{ flex: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {a.action}
              </span>

              {/* Status */}
              <span style={{
                width: 90, flexShrink: 0, fontSize: 10, fontWeight: 600, textTransform: 'uppercase',
                color: a.status === 'in_progress' ? 'var(--db-accent)'
                     : a.status === 'completed' ? 'var(--db-accent-green)'
                     : a.status === 'waiting' ? 'var(--db-accent-gold)'
                     : 'var(--db-text-dim)',
              }}>
                {a.status}
              </span>

              {/* Linked transaction badges */}
              <span className="flex gap-2" style={{ flex: 1 }}>
                {linkModels.map((lm) => (
                  <span
                    key={`${lm.model}-${lm.id}`}
                    className="db-bg-surface-alt"
                    style={{
                      fontSize: 10, padding: '1px 6px', borderRadius: 3,
                      border: '1px solid var(--db-border-light)',
                      cursor: 'pointer', whiteSpace: 'nowrap',
                    }}
                    title={`Open ${lm.model} ${lm.ida || lm.id}`}
                    onClick={(e) => { e.stopPropagation(); openTransaction(lm.model, lm.id); }}
                  >
                    {lm.model.slice(0, 3)}
                    {lm.value != null && ` $${Math.round(lm.value)}`}
                  </span>
                ))}
                {linkModels.length === 0 && (
                  <span className="db-text-dim" style={{ fontSize: 10 }}>—</span>
                )}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ActionDailyDashboard;

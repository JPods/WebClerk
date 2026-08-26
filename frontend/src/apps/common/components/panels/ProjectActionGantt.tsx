/**
 * ProjectActionGantt — Gantt timeline for a project's actions.
 *
 * Shows each action as a bar from dt_start to dt_deadline.
 * Dependency arrows drawn between linked actions.
 * Critical path highlighted (longest chain with zero slack).
 *
 * Pure CSS + SVG — no chart library dependency. Embeds in project detail tabs.
 *
 * LastChecked: 2026-08-24 | WhereUsed: panelRegistry (project_gantt) | WhoCreated: Bill+Claude
 */
import React, { useState, useEffect, useMemo, useRef } from 'react';
import { getRecords } from '@/api/wcapi';
import { formatDt } from '@/utils/fieldFormatters';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface GanttAction {
  id: number;
  ida?: string;
  sequence?: number;
  action: string;
  dt_start: number;
  dt_deadline: number;
  dt_completed?: number;
  percent_complete: number;
  priority: number;
  difficulty: number;
  kanban_column: string;
  assigned_to: string;
  depends_on: number[];        // action IDs this depends on
  card_number: string;
  isCritical: boolean;
  slack: number;               // days of float
}

interface ProjectActionGanttProps {
  projectId: number;
  projectName?: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DAY_MS = 86_400_000;
const ROW_HEIGHT = 32;
const LABEL_WIDTH = 200;
const MIN_BAR_WIDTH = 8;

const PRIORITY_COLORS: Record<number, string> = {
  1: '#ef4444',  // critical — red
  2: '#f59e0b',  // high — amber
  3: '#3b82f6',  // normal — blue
  4: '#6b7280',  // low — gray
};

const KANBAN_COLORS: Record<string, string> = {
  Backlog: '#6b7280',
  Planning: '#3b82f6',
  InProcess: '#10b981',
  Review: '#f59e0b',
  Complete: '#22c55e',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function extractTitle(action: any): string {
  if (typeof action === 'string') return action;
  if (action && typeof action === 'object') return action.en || Object.values(action)[0] || '';
  return '';
}

function extractDeps(record: any): number[] {
  // Check refs.parents[], depends_on, or metadata.depends_on
  const deps: number[] = [];
  if (record.refs?.parents) {
    for (const p of record.refs.parents) {
      if (typeof p === 'number') deps.push(p);
      else if (p?.id) deps.push(p.id);
    }
  }
  if (record.depends_on) {
    const arr = Array.isArray(record.depends_on) ? record.depends_on : [record.depends_on];
    for (const d of arr) {
      const n = typeof d === 'number' ? d : parseInt(d);
      if (!isNaN(n) && !deps.includes(n)) deps.push(n);
    }
  }
  return deps;
}

function parseEpoch(val: any): number {
  if (!val) return 0;
  const n = typeof val === 'number' ? val : parseInt(val);
  if (isNaN(n)) return 0;
  // Handle seconds vs milliseconds
  return n < 1e12 ? n * 1000 : n;
}

function fmtDate(ms: number): string {
  if (!ms) return '';
  return formatDt(ms, 'date');
}

// ---------------------------------------------------------------------------
// Critical Path Calculation
// ---------------------------------------------------------------------------

function calculateCriticalPath(actions: GanttAction[]): GanttAction[] {
  if (actions.length === 0) return actions;

  const byId = new Map<number, GanttAction>();
  for (const a of actions) byId.set(a.id, a);

  // Forward pass — earliest start (ES) and earliest finish (EF)
  const es = new Map<number, number>();
  const ef = new Map<number, number>();

  // Initialize
  for (const a of actions) {
    es.set(a.id, a.dt_start || Date.now());
    ef.set(a.id, a.dt_deadline || (a.dt_start || Date.now()) + DAY_MS);
  }

  // Iterate until stable (handles any dependency order)
  let changed = true;
  let iterations = 0;
  while (changed && iterations < 50) {
    changed = false;
    iterations++;
    for (const a of actions) {
      if (a.depends_on.length === 0) continue;
      let maxPredFinish = 0;
      for (const depId of a.depends_on) {
        const predEf = ef.get(depId);
        if (predEf && predEf > maxPredFinish) maxPredFinish = predEf;
      }
      if (maxPredFinish > 0) {
        const currentEs = es.get(a.id) || 0;
        const newEs = Math.max(currentEs, maxPredFinish);
        if (newEs !== currentEs) {
          es.set(a.id, newEs);
          const duration = (a.dt_deadline || newEs + DAY_MS) - (a.dt_start || newEs);
          ef.set(a.id, newEs + Math.max(duration, DAY_MS));
          changed = true;
        }
      }
    }
  }

  // Backward pass — latest start (LS) and latest finish (LF)
  const projectEnd = Math.max(...Array.from(ef.values()));
  const ls = new Map<number, number>();
  const lf = new Map<number, number>();

  // Initialize all to project end
  for (const a of actions) {
    lf.set(a.id, projectEnd);
    const duration = (ef.get(a.id) || projectEnd) - (es.get(a.id) || projectEnd);
    ls.set(a.id, projectEnd - duration);
  }

  // Iterate backward
  changed = true;
  iterations = 0;
  while (changed && iterations < 50) {
    changed = false;
    iterations++;
    for (const a of actions) {
      // Find all successors (actions that depend on this one)
      const successors = actions.filter(s => s.depends_on.includes(a.id));
      if (successors.length === 0) continue;
      let minSuccStart = projectEnd;
      for (const succ of successors) {
        const succLs = ls.get(succ.id);
        if (succLs !== undefined && succLs < minSuccStart) minSuccStart = succLs;
      }
      const currentLf = lf.get(a.id) || projectEnd;
      if (minSuccStart < currentLf) {
        lf.set(a.id, minSuccStart);
        const duration = (ef.get(a.id) || 0) - (es.get(a.id) || 0);
        ls.set(a.id, minSuccStart - duration);
        changed = true;
      }
    }
  }

  // Mark critical path: slack = LS - ES (zero or near-zero = critical)
  return actions.map(a => {
    const slack = ((ls.get(a.id) || 0) - (es.get(a.id) || 0)) / DAY_MS;
    return {
      ...a,
      isCritical: Math.abs(slack) < 0.5,  // less than half a day of float
      slack: Math.max(0, Math.round(slack)),
    };
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ProjectActionGantt({ projectId, projectName }: ProjectActionGanttProps) {
  const [actions, setActions] = useState<GanttAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCriticalOnly, setShowCriticalOnly] = useState(false);
  const svgRef = useRef<SVGSVGElement>(null);

  // Fetch actions for this project
  useEffect(() => {
    getRecords('action', { project_id: projectId, is_active: true, limit: 500 })
      .then((res: any) => {
        const rows = res?.results || res?.records || res?.data?.results || [];
        const mapped: GanttAction[] = rows
          .map((r: any, idx: number) => ({
            id: r.id,
            ida: r.ida || '',
            sequence: r.sequence || idx + 1,
            action: extractTitle(r.action),
            dt_start: parseEpoch(r.dt_start),
            dt_deadline: parseEpoch(r.dt_deadline) || parseEpoch(r.dt_end),
            dt_completed: parseEpoch(r.dt_completed),
            percent_complete: r.percent_complete || 0,
            priority: typeof r.priority === 'number' ? r.priority : 2,
            difficulty: r.difficulty || 4,
            kanban_column: r.kanban_column || 'Backlog',
            assigned_to: Array.isArray(r.assigned_to)
              ? r.assigned_to.map((a: any) => a.name || a.email || '').join(', ')
              : '',
            depends_on: extractDeps(r),
            card_number: r.ida || r.card_number || String(idx + 1),
            isCritical: false,
            slack: 0,
          }))
          .filter((a: GanttAction) => a.dt_start || a.dt_deadline);

        // Calculate critical path
        const withCritical = calculateCriticalPath(mapped);
        // Sort by sequence
        withCritical.sort((a, b) => (a.sequence || 0) - (b.sequence || 0));
        setActions(withCritical);
      })
      .catch((err) => console.error('ProjectActionGantt fetch error:', err))
      .finally(() => setLoading(false));
  }, [projectId]);

  // Filter
  const displayed = showCriticalOnly ? actions.filter(a => a.isCritical) : actions;

  // Timeline range
  const { minDate, maxDate, rangeMs, rangeDays } = useMemo(() => {
    const now = Date.now();
    let min = now;
    let max = now + 30 * DAY_MS;

    for (const a of displayed) {
      const start = a.dt_start || now;
      const end = a.dt_deadline || start + 7 * DAY_MS;
      if (start < min) min = start;
      if (end > max) max = end;
    }

    const range = max - min;
    const pad = Math.max(range * 0.05, 3 * DAY_MS);
    min -= pad;
    max += pad;

    return {
      minDate: min,
      maxDate: max,
      rangeMs: max - min,
      rangeDays: Math.ceil((max - min) / DAY_MS),
    };
  }, [displayed]);

  // Week/month markers
  const markers = useMemo(() => {
    const result: { label: string; left: number; isMonth: boolean }[] = [];
    const d = new Date(minDate);
    d.setDate(1);
    d.setHours(0, 0, 0, 0);
    if (d.getTime() < minDate) d.setMonth(d.getMonth() + 1);

    while (d.getTime() < maxDate) {
      const pct = ((d.getTime() - minDate) / rangeMs) * 100;
      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      result.push({
        label: `${monthNames[d.getMonth()]} ${d.getFullYear()}`,
        left: pct,
        isMonth: true,
      });
      d.setMonth(d.getMonth() + 1);
    }
    return result;
  }, [minDate, maxDate, rangeMs]);

  const todayPct = ((Date.now() - minDate) / rangeMs) * 100;

  // Build position map for dependency arrows
  const posMap = useMemo(() => {
    const map = new Map<number, { row: number; leftPct: number; rightPct: number; midY: number }>();
    displayed.forEach((a, idx) => {
      const start = a.dt_start || Date.now();
      const end = a.dt_deadline || start + 7 * DAY_MS;
      const leftPct = ((start - minDate) / rangeMs) * 100;
      const rightPct = ((end - minDate) / rangeMs) * 100;
      const midY = idx * ROW_HEIGHT + ROW_HEIGHT / 2;
      map.set(a.id, { row: idx, leftPct, rightPct, midY });
    });
    return map;
  }, [displayed, minDate, rangeMs]);

  // Stats
  const criticalCount = actions.filter(a => a.isCritical).length;
  const completeCount = actions.filter(a => a.kanban_column === 'Complete').length;

  if (loading) {
    return <div style={{ padding: 16, color: 'var(--db-text-muted)', fontSize: 12 }}>Loading actions...</div>;
  }

  if (actions.length === 0) {
    return (
      <div style={{ padding: 16, color: 'var(--db-text-dim)', fontSize: 12, textAlign: 'center' }}>
        No actions with dates for this project.
        <br />
        <span style={{ fontSize: 11, color: 'var(--db-text-muted)' }}>
          Set dt_start and dt_deadline on actions to see them here.
        </span>
      </div>
    );
  }

  const chartWidth = 800;
  const chartHeight = displayed.length * ROW_HEIGHT + 30;

  return (
    <div style={{ fontSize: 12 }}>
      {/* Toolbar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 16, padding: '8px 12px',
        borderBottom: '1px solid var(--db-border)',
        flexWrap: 'wrap',
      }}>
        <span style={{ fontWeight: 600, color: 'var(--db-text)' }}>
          {projectName || 'Project'} &mdash; {actions.length} actions
        </span>
        <span style={{ fontSize: 11, color: 'var(--db-text-muted)' }}>
          <span style={{ color: '#ef4444', fontWeight: 600 }}>{criticalCount}</span> critical path
          &nbsp;&middot;&nbsp;
          <span style={{ color: '#22c55e' }}>{completeCount}</span> complete
        </span>
        <label style={{ fontSize: 11, color: 'var(--db-text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
          <input
            type="checkbox"
            checked={showCriticalOnly}
            onChange={e => setShowCriticalOnly(e.target.checked)}
            style={{ accentColor: '#ef4444' }}
          />
          Critical path only
        </label>
      </div>

      <div style={{ display: 'flex', overflowX: 'auto' }}>
        {/* Left labels */}
        <div style={{ flexShrink: 0, width: LABEL_WIDTH }}>
          {/* Header spacer */}
          <div style={{ height: 24, borderBottom: '1px solid var(--db-border)' }} />
          {displayed.map((a, idx) => (
            <div
              key={a.id}
              style={{
                height: ROW_HEIGHT,
                display: 'flex',
                alignItems: 'center',
                padding: '0 8px',
                borderBottom: '1px solid var(--db-border)',
                gap: 6,
                background: a.isCritical ? 'rgba(239,68,68,0.06)' : undefined,
              }}
            >
              {/* Critical path indicator */}
              {a.isCritical && (
                <span style={{
                  fontSize: 8, fontWeight: 700, color: '#ef4444',
                  background: 'rgba(239,68,68,0.15)', padding: '1px 4px', borderRadius: 3,
                }}>CP</span>
              )}
              {/* Card number */}
              <span style={{ fontSize: 10, color: 'var(--db-text-muted)', fontFamily: 'monospace', minWidth: 28 }}>
                {a.card_number}
              </span>
              {/* Action name */}
              <span style={{
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                fontWeight: a.isCritical ? 600 : 400,
                color: a.isCritical ? 'var(--db-text)' : 'var(--db-text-muted)',
                cursor: 'pointer',
              }}
                title={`${a.action} — P${a.priority} ${a.kanban_column}${a.slack > 0 ? ` (${a.slack}d slack)` : ''}`}
              >
                {a.action}
              </span>
              {/* Dependency count */}
              {a.depends_on.length > 0 && (
                <span style={{
                  fontSize: 9, color: 'var(--db-text-dim)',
                  background: 'var(--db-bg-alt)', padding: '0 4px', borderRadius: 8,
                }}
                  title={`Depends on: ${a.depends_on.join(', ')}`}
                >
                  &larr;{a.depends_on.length}
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Right timeline */}
        <div style={{ flex: 1, minWidth: chartWidth, position: 'relative' }}>
          {/* Timeline header */}
          <div style={{ height: 24, position: 'relative', borderBottom: '1px solid var(--db-border)' }}>
            {markers.map((m, i) => (
              <div key={i} style={{
                position: 'absolute', left: `${m.left}%`,
                fontSize: 9, color: 'var(--db-text-dim)', fontWeight: 600,
                borderLeft: '1px solid var(--db-border)', paddingLeft: 3,
                top: 0, height: '100%', display: 'flex', alignItems: 'center',
              }}>
                {m.label}
              </div>
            ))}
            {todayPct > 0 && todayPct < 100 && (
              <div style={{
                position: 'absolute', left: `${todayPct}%`,
                width: 2, height: '100%', background: '#ef4444', zIndex: 2,
              }}>
                <span style={{ position: 'absolute', top: -1, left: 4, fontSize: 8, color: '#ef4444', fontWeight: 700 }}>
                  today
                </span>
              </div>
            )}
          </div>

          {/* Bars + dependency arrows */}
          <div style={{ position: 'relative' }}>
            {/* Row backgrounds */}
            {displayed.map((a, idx) => (
              <div key={a.id} style={{
                height: ROW_HEIGHT,
                borderBottom: '1px solid var(--db-border)',
                background: a.isCritical ? 'rgba(239,68,68,0.04)' : undefined,
                position: 'relative',
              }}>
                {/* Today line through rows */}
                {todayPct > 0 && todayPct < 100 && (
                  <div style={{
                    position: 'absolute', left: `${todayPct}%`,
                    width: 1, height: '100%', background: 'rgba(239,68,68,0.15)',
                  }} />
                )}

                {/* Month grid lines */}
                {markers.map((m, i) => (
                  <div key={i} style={{
                    position: 'absolute', left: `${m.left}%`,
                    width: 1, height: '100%', background: 'var(--db-border)',
                    opacity: 0.3,
                  }} />
                ))}

                {/* Action bar */}
                {(() => {
                  const start = a.dt_start || Date.now();
                  const end = a.dt_deadline || start + 7 * DAY_MS;
                  const leftPct = Math.max(0, ((start - minDate) / rangeMs) * 100);
                  const widthPct = Math.max(0.5, ((end - start) / rangeMs) * 100);
                  const color = a.isCritical
                    ? '#ef4444'
                    : (PRIORITY_COLORS[a.priority] || '#3b82f6');
                  const isDone = a.kanban_column === 'Complete';

                  return (
                    <div
                      style={{
                        position: 'absolute',
                        left: `${leftPct}%`,
                        width: `${widthPct}%`,
                        top: 6,
                        height: ROW_HEIGHT - 12,
                        borderRadius: 3,
                        background: isDone ? '#22c55e33' : `${color}30`,
                        border: `1.5px solid ${isDone ? '#22c55e' : color}`,
                        overflow: 'hidden',
                        cursor: 'pointer',
                        minWidth: MIN_BAR_WIDTH,
                      }}
                      title={`${a.action}\nP${a.priority} | ${a.kanban_column} | ${a.percent_complete}%\n${fmtDate(start)} → ${fmtDate(end)}${a.slack > 0 ? `\n${a.slack}d slack` : ''}${a.isCritical ? '\nCRITICAL PATH' : ''}`}
                    >
                      {/* Progress fill */}
                      {a.percent_complete > 0 && (
                        <div style={{
                          width: `${a.percent_complete}%`,
                          height: '100%',
                          background: isDone ? '#22c55e' : color,
                          opacity: 0.6,
                          borderRadius: '2px 0 0 2px',
                        }} />
                      )}
                      {/* Label */}
                      <span style={{
                        position: 'absolute', left: 4, top: 2,
                        fontSize: 9, color: 'var(--db-text)',
                        fontWeight: a.isCritical ? 600 : 400,
                        whiteSpace: 'nowrap',
                        textShadow: '0 0 4px var(--db-bg)',
                      }}>
                        {a.percent_complete > 0 ? `${a.percent_complete}%` : ''}
                      </span>
                    </div>
                  );
                })()}
              </div>
            ))}

            {/* Dependency arrows — SVG overlay */}
            <svg
              ref={svgRef}
              style={{
                position: 'absolute', top: 0, left: 0,
                width: '100%', height: chartHeight - 24,
                pointerEvents: 'none',
                overflow: 'visible',
              }}
            >
              <defs>
                <marker id="gantt-arrow" viewBox="0 0 10 10" refX="9" refY="5"
                        markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                  <path d="M 0 1 L 8 5 L 0 9 z" fill="#64748b" />
                </marker>
                <marker id="gantt-arrow-crit" viewBox="0 0 10 10" refX="9" refY="5"
                        markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                  <path d="M 0 1 L 8 5 L 0 9 z" fill="#ef4444" />
                </marker>
              </defs>
              {displayed.map(a => {
                if (a.depends_on.length === 0) return null;
                return a.depends_on.map(depId => {
                  const from = posMap.get(depId);
                  const to = posMap.get(a.id);
                  if (!from || !to) return null;

                  const isCritLink = a.isCritical && (actions.find(x => x.id === depId)?.isCritical || false);

                  // Calculate pixel positions (percentage-based approximation)
                  // We draw a right-angle path: from bar end → down/up → to bar start
                  const fromX = `${from.rightPct}%`;
                  const toX = `${to.leftPct}%`;
                  const fromY = from.midY;
                  const toY = to.midY;

                  // Simple path: horizontal from end, then vertical, then horizontal to start
                  const midXPct = (from.rightPct + to.leftPct) / 2;

                  return (
                    <g key={`${depId}-${a.id}`}>
                      <line
                        x1={fromX} y1={fromY}
                        x2={toX} y2={toY}
                        stroke={isCritLink ? '#ef4444' : '#64748b'}
                        strokeWidth={isCritLink ? 2 : 1}
                        strokeDasharray={isCritLink ? undefined : '4,3'}
                        opacity={isCritLink ? 0.8 : 0.4}
                        markerEnd={isCritLink ? 'url(#gantt-arrow-crit)' : 'url(#gantt-arrow)'}
                      />
                    </g>
                  );
                });
              })}
            </svg>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div style={{
        display: 'flex', gap: 16, padding: '8px 12px',
        borderTop: '1px solid var(--db-border)', fontSize: 10,
        color: 'var(--db-text-muted)', flexWrap: 'wrap',
      }}>
        <span><span style={{ display: 'inline-block', width: 12, height: 8, background: '#ef4444', borderRadius: 2, marginRight: 4 }} />Critical path</span>
        <span><span style={{ display: 'inline-block', width: 12, height: 8, background: '#3b82f6', borderRadius: 2, marginRight: 4 }} />Normal</span>
        <span><span style={{ display: 'inline-block', width: 12, height: 8, background: '#22c55e', borderRadius: 2, marginRight: 4 }} />Complete</span>
        <span style={{ marginLeft: 'auto' }}>
          Arrows = dependencies &middot; Dashed = normal &middot; Solid red = critical path
        </span>
      </div>
    </div>
  );
}

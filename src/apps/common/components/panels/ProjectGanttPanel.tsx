/**
 * ProjectGanttPanel — Gantt timeline for projects linked to a contact.
 *
 * Each bar = one project. Uses dt_start and dt_end (epoch ms) for timeline.
 * percent_complete shown as fill within the bar.
 * Color = attention level. Click to open in DataBrowser.
 *
 * Pure CSS — no chart library dependency. Lightweight for tab embedding.
 *
 * LastChecked: 2026-08-05 | WhereUsed: ContactDetailJson tabs | WhoCreated: Bill+Claude
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { getRecords } from '@/api/wcapi';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Project {
  id: number;
  ida: string;
  name: string;
  status: string;
  attention: string;
  priority: number;
  percent_complete: number;
  dt_start: number;
  dt_end: number;
  intent: string;
  category: string;
}

interface ProjectGanttPanelProps {
  contactId: number;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ATTENTION_COLORS: Record<string, string> = {
  low: '#6b7280',
  normal: '#3b82f6',
  high: '#f59e0b',
  critical: '#ef4444',
};

const STATUS_OPACITY: Record<string, number> = {
  done: 0.5,
  canceled: 0.3,
  draft: 0.7,
};

const DAY_MS = 86400000;

function fmtDate(ms: number): string {
  if (!ms) return '';
  return new Date(ms).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function fmtDateFull(ms: number): string {
  if (!ms) return '';
  return new Date(ms).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// ---------------------------------------------------------------------------
// Panel
// ---------------------------------------------------------------------------

export default function ProjectGanttPanel({ contactId }: ProjectGanttPanelProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRecords('project', { id_contact: contactId, is_active: true })
      .then((res: any) => {
        const rows = res?.results || res?.records || res?.data?.results || [];
        setProjects(rows.filter((p: Project) => p.dt_start || p.dt_end));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [contactId]);

  // Compute timeline range
  const { minDate, maxDate, rangeMs } = useMemo(() => {
    const now = Date.now();
    let min = now;
    let max = now + 30 * DAY_MS;

    for (const p of projects) {
      const start = p.dt_start || now;
      const end = p.dt_end || start + 14 * DAY_MS;
      if (start < min) min = start;
      if (end > max) max = end;
    }

    // Add 5% padding on each side
    const range = max - min;
    const pad = range * 0.05;
    min -= pad;
    max += pad;

    return { minDate: min, maxDate: max, rangeMs: max - min };
  }, [projects]);

  // Month markers
  const monthMarkers = useMemo(() => {
    const markers: { label: string; left: number }[] = [];
    const d = new Date(minDate);
    d.setDate(1);
    d.setHours(0, 0, 0, 0);
    if (d.getTime() < minDate) d.setMonth(d.getMonth() + 1);

    while (d.getTime() < maxDate) {
      const pct = ((d.getTime() - minDate) / rangeMs) * 100;
      markers.push({
        label: d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' }),
        left: pct,
      });
      d.setMonth(d.getMonth() + 1);
    }
    return markers;
  }, [minDate, maxDate, rangeMs]);

  // Today marker
  const todayPct = ((Date.now() - minDate) / rangeMs) * 100;

  if (loading) return <div style={{ padding: 16, color: '#888', fontSize: 12 }}>Loading projects...</div>;
  if (projects.length === 0) return <div style={{ padding: 16, color: '#666', fontSize: 12, textAlign: 'center' }}>No projects with dates for this contact</div>;

  // Sort by start date, then priority
  const sorted = [...projects].sort((a, b) => (a.dt_start || 0) - (b.dt_start || 0) || a.priority - b.priority);

  return (
    <div style={{ overflowX: 'auto', padding: '4px 0' }}>
      {/* Timeline header */}
      <div style={{ position: 'relative', height: 20, marginLeft: 160, marginBottom: 2 }}>
        {monthMarkers.map((m, i) => (
          <div key={i} style={{
            position: 'absolute', left: `${m.left}%`,
            fontSize: 9, color: '#666', fontWeight: 600,
            borderLeft: '1px solid #333', paddingLeft: 3, top: 0, height: '100%',
          }}>
            {m.label}
          </div>
        ))}
        {/* Today marker */}
        {todayPct > 0 && todayPct < 100 && (
          <div style={{
            position: 'absolute', left: `${todayPct}%`,
            width: 1, height: '100%', background: '#ef4444',
          }}>
            <span style={{ position: 'absolute', top: -2, left: 3, fontSize: 8, color: '#ef4444', fontWeight: 700 }}>today</span>
          </div>
        )}
      </div>

      {/* Rows */}
      {sorted.map(p => {
        const start = p.dt_start || Date.now();
        const end = p.dt_end || start + 14 * DAY_MS;
        const leftPct = ((start - minDate) / rangeMs) * 100;
        const widthPct = ((end - start) / rangeMs) * 100;
        const color = ATTENTION_COLORS[p.attention] || '#3b82f6';
        const opacity = STATUS_OPACITY[p.status] ?? 1;

        return (
          <div key={p.id} style={{
            display: 'flex', alignItems: 'center', height: 28,
            borderBottom: '1px solid #2a2a3a',
          }}>
            {/* Label */}
            <div style={{
              width: 160, flexShrink: 0, padding: '0 8px',
              fontSize: 11, color: '#ccc', fontWeight: 500,
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              cursor: 'pointer',
            }}
              onClick={() => window.open(`/project?search=${encodeURIComponent(p.name)}`, '_blank')}
              title={`${p.name} — ${fmtDateFull(start)} to ${fmtDateFull(end)}`}
            >
              {p.name}
            </div>

            {/* Bar area */}
            <div style={{ flex: 1, position: 'relative', height: '100%' }}>
              {/* Today line extends through rows */}
              {todayPct > 0 && todayPct < 100 && (
                <div style={{
                  position: 'absolute', left: `${todayPct}%`,
                  width: 1, height: '100%', background: '#ef444433',
                }} />
              )}

              {/* Project bar */}
              <div
                style={{
                  position: 'absolute',
                  left: `${Math.max(leftPct, 0)}%`,
                  width: `${Math.max(widthPct, 0.5)}%`,
                  top: 4, height: 20, borderRadius: 4,
                  background: `${color}33`,
                  border: `1px solid ${color}66`,
                  opacity,
                  cursor: 'pointer',
                  overflow: 'hidden',
                }}
                onClick={() => window.open(`/project?search=${encodeURIComponent(p.name)}`, '_blank')}
                title={`${p.name}: ${p.percent_complete}% — ${fmtDate(start)} to ${fmtDate(end)}`}
              >
                {/* Progress fill */}
                <div style={{
                  width: `${p.percent_complete}%`,
                  height: '100%',
                  background: color,
                  borderRadius: '3px 0 0 3px',
                  transition: 'width 0.3s',
                }} />
                {/* Label inside bar */}
                <span style={{
                  position: 'absolute', left: 4, top: 3,
                  fontSize: 9, color: '#fff', fontWeight: 600,
                  textShadow: '0 0 3px rgba(0,0,0,0.6)',
                  whiteSpace: 'nowrap',
                }}>
                  {p.percent_complete > 0 ? `${p.percent_complete}%` : ''}
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

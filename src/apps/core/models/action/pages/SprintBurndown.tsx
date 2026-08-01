/**
 * SprintBurndown — Compact burndown chart for a sprint project.
 * Shows ideal vs actual remaining work points.
 *
 * Points = difficulty × (100 - percent_complete) per action.
 * Ideal = linear from total to 0 over sprint duration.
 */
import { useEffect, useState } from "react";
import apiClient from "../../../../../api/axios";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

interface BurndownData {
  project_id: number;
  sprint: string;
  dt_start: string | null;
  dt_end: string | null;
  total_points: number;
  remaining_points: number;
  percent_complete: number;
  action_count: number;
  ideal: { dt: string; points: number }[];
  actions: {
    id: number;
    ida: string;
    action: string;
    difficulty: number;
    percent_complete: number;
    duration: number | null;
    points_total: number;
    points_remaining: number;
    status: string;
    assigned_to: string;
  }[];
}

interface SprintBurndownProps {
  projectId: string | number;
  compact?: boolean;
}

function SprintBurndown({ projectId, compact = false }: SprintBurndownProps) {
  const [data, setData] = useState<BurndownData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    apiClient.get(`/wcapi/burndown/${projectId}/`)
      .then((resp) => {
        const d = resp.data?.data || resp.data;
        if (d?.error) {
          setError(d.error);
        } else {
          setData(d);
        }
      })
      .catch((e) => setError(e.message || "Failed to load burndown"));
  }, [projectId]);

  if (error) return <div className="text-xs text-red-500 py-2">{error}</div>;
  if (!data) return <div className="text-xs text-gray-400 py-2">Loading burndown...</div>;

  const { total_points, remaining_points, percent_complete, ideal, actions, sprint } = data;

  // Calculate where "today" falls on the ideal line
  const today = new Date().toISOString().split('T')[0];
  const todayIdeal = ideal.find(p => p.dt === today);
  const idealToday = todayIdeal?.points ?? null;

  // Status: ahead, on track, behind
  const statusColor = idealToday === null ? "text-gray-500"
    : remaining_points <= idealToday ? "text-green-600"
    : remaining_points <= idealToday * 1.2 ? "text-amber-600"
    : "text-red-600";

  const statusLabel = idealToday === null ? "—"
    : remaining_points <= idealToday ? "Ahead"
    : remaining_points <= idealToday * 1.2 ? "On Track"
    : "Behind";

  // SVG chart dimensions
  const chartW = compact ? 280 : 360;
  const chartH = compact ? 100 : 140;
  const pad = { t: 10, r: 10, b: 20, l: 35 };
  const w = chartW - pad.l - pad.r;
  const h = chartH - pad.t - pad.b;

  // Build ideal line path
  const idealPath = ideal.length > 1 ? ideal.map((p, i) => {
    const x = pad.l + (i / (ideal.length - 1)) * w;
    const y = pad.t + (1 - p.points / total_points) * h;
    return `${i === 0 ? 'M' : 'L'}${x},${y}`;
  }).join(' ') : '';

  // Today marker position
  const todayIdx = ideal.findIndex(p => p.dt >= today);
  const todayX = todayIdx >= 0 ? pad.l + (todayIdx / (ideal.length - 1)) * w : null;
  const actualY = pad.t + (1 - remaining_points / total_points) * h;

  return (
    <div className="space-y-2">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
          {compact ? "Burndown" : sprint}
        </span>
        <span className={`text-xs font-bold ${statusColor}`}>
          {percent_complete}% · {statusLabel}
        </span>
      </div>

      {/* Chart */}
      <svg width={chartW} height={chartH} className="bg-gray-50 rounded dark:bg-gray-800/50">
        {/* Grid lines */}
        {[0, 25, 50, 75, 100].map(pct => {
          const y = pad.t + (pct / 100) * h;
          return <line key={pct} x1={pad.l} y1={y} x2={pad.l + w} y2={y}
            stroke="#e5e7eb" strokeWidth="0.5" />;
        })}

        {/* Y-axis labels */}
        <text x={pad.l - 4} y={pad.t + 3} fontSize="8" fill="#9ca3af" textAnchor="end">{total_points}</text>
        <text x={pad.l - 4} y={pad.t + h + 3} fontSize="8" fill="#9ca3af" textAnchor="end">0</text>

        {/* X-axis labels */}
        {ideal.length > 0 && (
          <>
            <text x={pad.l} y={chartH - 2} fontSize="7" fill="#9ca3af">{ideal[0]?.dt?.slice(5)}</text>
            <text x={pad.l + w} y={chartH - 2} fontSize="7" fill="#9ca3af" textAnchor="end">
              {ideal[ideal.length - 1]?.dt?.slice(5)}
            </text>
          </>
        )}

        {/* Ideal line (dashed gray) */}
        {idealPath && <path d={idealPath} fill="none" stroke="#9ca3af" strokeWidth="1.5" strokeDasharray="4 2" />}

        {/* Today vertical line */}
        {todayX && (
          <line x1={todayX} y1={pad.t} x2={todayX} y2={pad.t + h}
            stroke="#ef4444" strokeWidth="1" strokeDasharray="2 2" />
        )}

        {/* Actual remaining point (dot) */}
        {todayX && (
          <circle cx={todayX} cy={actualY} r="4"
            fill={remaining_points <= (idealToday ?? 0) ? "#22c55e" : "#ef4444"}
            stroke="white" strokeWidth="1.5" />
        )}
      </svg>

      {/* Action summary — only in non-compact mode */}
      {!compact && (
        <div className="space-y-0.5">
          <div className="text-[10px] text-gray-500 dark:text-gray-400">
            {data.action_count} actions · {total_points} total pts · {remaining_points} remaining
          </div>
          {actions.slice(0, 5).map(a => (
            <div key={a.id} className="flex items-center gap-1 text-[10px]">
              <span className={`w-1.5 h-1.5 rounded-full ${
                a.percent_complete >= 100 ? 'bg-green-500' :
                a.percent_complete > 0 ? 'bg-blue-500' : 'bg-gray-300'
              }`} />
              <span className="text-gray-600 dark:text-gray-400 truncate flex-1">{a.action}</span>
              <span className="text-gray-400 whitespace-nowrap">
                d{a.difficulty} · {a.percent_complete}%
                {a.duration ? ` · ${a.duration}d` : ''}
              </span>
            </div>
          ))}
          {actions.length > 5 && (
            <div className="text-[10px] text-gray-400">+{actions.length - 5} more</div>
          )}
        </div>
      )}
    </div>
  );
}

export default withDevIdentifier(SprintBurndown, 'SprintBurndown');

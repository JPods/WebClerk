/**
 * EnhancedGantt — Wrapper for @svar-ui/react-gantt with production controls
 *
 * Adds: A+/A- font scaling, text overflow toggle, color modes,
 * frozen header rows, meeting-friendly click behavior.
 *
 * Usage:
 *   <EnhancedGantt tasks={tasks} links={links} />
 *
 * MIT License — https://github.com/webclerk/gantt-enhancements
 */
import { FC, useState, useCallback, useMemo } from "react";
import { Gantt, Willow } from "@svar-ui/react-gantt";
import type { ITask } from "@svar-ui/react-gantt";
import "@svar-ui/react-gantt/all.css";
import { EnhancedTaskTemplate } from "./EnhancedTaskTemplate";

// ── Color mode palettes ──

const priorityBarColors: Record<string, string> = {
  low: '#e2e8f0', medium: '#93c5fd', high: '#f97316', critical: '#ef4444',
};
const statusBarColors: Record<string, string> = {
  open: '#94a3b8', in_progress: '#3b82f6', active: '#3b82f6',
  complete: '#22c55e', done: '#22c55e', blocked: '#ef4444',
  on_hold: '#9ca3af', cancelled: '#6b7280', draft: '#d1d5db',
};

type ColorMode = 'priority' | 'status' | 'assignee';

// ── Scale presets ──

const scalePresets = {
  day:     [{ unit: "month", step: 1, format: "MMM yyyy" }, { unit: "day", step: 1, format: "d" }],
  week:    [{ unit: "month", step: 1, format: "MMMM yyyy" }, { unit: "week", step: 1, format: "'W'w" }],
  month:   [{ unit: "year", step: 1, format: "yyyy" }, { unit: "month", step: 1, format: "MMM" }],
  quarter: [{ unit: "year", step: 1, format: "yyyy" }, { unit: "quarter", step: 1, format: "'Q'Q" }],
} as const;

type ScaleKey = keyof typeof scalePresets;

// ── Props ──

interface EnhancedGanttProps {
  tasks: ITask[];
  links?: any[];
  columns?: any[];
  start?: Date;
  end?: Date;
  onTaskDoubleClick?: (task: ITask) => void;
}

export const EnhancedGantt: FC<EnhancedGanttProps> = ({
  tasks,
  links = [],
  columns,
  start,
  end,
  onTaskDoubleClick,
}) => {
  const [fontScale, setFontScale] = useState(0);
  const [textOverflow, setTextOverflow] = useState(false);
  const [colorMode, setColorMode] = useState<ColorMode>('priority');
  const [scalePreset, setScalePreset] = useState<ScaleKey>('week');

  // Apply color mode to task bars
  const coloredTasks = useMemo(() => {
    return tasks.map((task) => {
      let color: string | undefined;
      if (colorMode === 'priority') {
        color = priorityBarColors[task.priority || 'medium'] || priorityBarColors.medium;
      } else if (colorMode === 'status') {
        const s = (task.status || task.columnId || 'open').toLowerCase().replace(/\s+/g, '_');
        color = statusBarColors[s] || statusBarColors.open;
      }
      // assignee mode: use task's existing color or auto-assign
      return color ? { ...task, color } : task;
    });
  }, [tasks, colorMode]);

  // Double-click handler
  const handleDoubleClick = useCallback(({ id }: { id: string | number }) => {
    const task = tasks.find(t => String(t.id) === String(id));
    if (task && onTaskDoubleClick) onTaskDoubleClick(task);
  }, [tasks, onTaskDoubleClick]);

  const cellHeight = 38 + fontScale;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* ── Toolbar ── */}
      <div style={{
        display: "flex", alignItems: "center", gap: "12px",
        padding: "8px 12px", borderBottom: "1px solid #e5e7eb",
        flexWrap: "wrap", fontSize: "12px",
      }}>
        {/* Color mode */}
        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          <span style={{ color: "#6b7280" }}>Color:</span>
          {(['priority', 'status', 'assignee'] as const).map(mode => (
            <button
              key={mode}
              onClick={() => setColorMode(mode)}
              style={{
                padding: "2px 8px", borderRadius: "4px", border: "none", cursor: "pointer",
                background: colorMode === mode ? "#e0e7ff" : "transparent",
                fontWeight: colorMode === mode ? 600 : 400,
                color: colorMode === mode ? "#3730a3" : "#6b7280",
              }}
            >
              {mode.charAt(0).toUpperCase() + mode.slice(1)}
            </button>
          ))}
        </div>

        {/* Font scale */}
        <div style={{ display: "flex", alignItems: "center", gap: "2px" }}>
          <button
            onClick={() => setFontScale(s => s - 2)}
            style={{ padding: "2px 6px", borderRadius: "4px", border: "1px solid #d1d5db", cursor: "pointer", background: "white" }}
          >A-</button>
          <button
            onClick={() => setFontScale(s => s + 2)}
            style={{ padding: "2px 6px", borderRadius: "4px", border: "1px solid #d1d5db", cursor: "pointer", background: "white" }}
          >A+</button>
        </div>

        {/* Text overflow */}
        <label style={{ display: "flex", alignItems: "center", gap: "4px", cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={textOverflow}
            onChange={e => setTextOverflow(e.target.checked)}
          />
          <span style={{ color: "#6b7280" }}>Show full text</span>
        </label>

        {/* Scale presets */}
        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          <span style={{ color: "#6b7280" }}>Scale:</span>
          {(Object.keys(scalePresets) as ScaleKey[]).map(key => (
            <button
              key={key}
              onClick={() => setScalePreset(key)}
              style={{
                padding: "2px 8px", borderRadius: "4px", border: "none", cursor: "pointer",
                background: scalePreset === key ? "#e0e7ff" : "transparent",
                fontWeight: scalePreset === key ? 600 : 400,
                color: scalePreset === key ? "#3730a3" : "#6b7280",
              }}
            >
              {key.charAt(0).toUpperCase() + key.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* ── Gantt ── */}
      <div
        style={{
          flex: 1, minHeight: 0,
          fontSize: `${12 + fontScale}px`,
          '--gantt-text-overflow': textOverflow ? 'visible' : 'hidden',
        } as React.CSSProperties}
      >
        {/* Frozen rows + sticky header CSS */}
        <style>{`
          .wx-content .wx-row:nth-child(1),
          .wx-content .wx-row:nth-child(2) {
            position: sticky !important;
            top: 0 !important;
            z-index: 5 !important;
            background: var(--wx-background, #fff) !important;
            box-shadow: 0 1px 0 rgba(0,0,0,0.08);
          }
          .wx-content .wx-row:nth-child(2) {
            top: ${cellHeight}px !important;
          }
          .wx-scale {
            position: sticky !important;
            top: 0 !important;
            z-index: 10 !important;
          }
        `}</style>

        <Willow>
          <Gantt
            key={`fs${fontScale}`}
            tasks={coloredTasks}
            links={links}
            columns={columns}
            scales={scalePresets[scalePreset] as any}
            start={start}
            end={end}
            cellHeight={cellHeight}
            taskTemplate={EnhancedTaskTemplate}
            onItemDoubleClick={handleDoubleClick}
            highlightTime={(date: Date, unit: string) => {
              if (unit !== 'day') return false;
              const today = new Date();
              return date.getFullYear() === today.getFullYear() &&
                     date.getMonth() === today.getMonth() &&
                     date.getDate() === today.getDate();
            }}
          />
        </Willow>
      </div>
    </div>
  );
};

export default EnhancedGantt;

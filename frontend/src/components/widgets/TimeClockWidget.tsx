/**
 * TimeClockWidget — renders time entries list inside a panel.
 *
 * Clock in/out button lives in the panel header (PanelSectionRenderer).
 * This widget renders the entry list with inline editing for reason/notes.
 *
 * Data shape: action.config.times (ActionTimes schema)
 *   { entries: [{ id, who, dt_in, dt_out, elapsed_ms, ... }], total_elapsed_ms, total_active_ms }
 */
import React, { useState, useEffect, useCallback, useMemo } from "react";
import type { WidgetProps } from "./types";

function formatElapsed(ms: number): string {
  if (ms < 0) ms = 0;
  const totalSec = Math.floor(ms / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  if (h > 0) return `${h}h ${String(m).padStart(2, "0")}m`;
  if (m > 0) return `${m}m ${String(s).padStart(2, "0")}s`;
  return `${s}s`;
}

function formatDtShort(epochMs: number): string {
  return new Date(epochMs).toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

interface TimeEntry {
  id: string;
  who?: number | null;
  dt_in?: number | null;
  dt_out?: number | null;
  elapsed_ms?: number | null;
  percent_active?: number;
  reason?: string;
  notes?: string;
  tags?: string[];
  issue?: string | null;
}

interface ActionTimes {
  entries: TimeEntry[];
  total_elapsed_ms?: number | null;
  total_active_ms?: number | null;
}

function ensureTimes(raw: any): ActionTimes {
  if (!raw || typeof raw !== "object") return { entries: [] };
  return {
    entries: Array.isArray(raw.entries) ? raw.entries : [],
    total_elapsed_ms: raw.total_elapsed_ms ?? null,
    total_active_ms: raw.total_active_ms ?? null,
  };
}

function getOpenEntry(times: ActionTimes): TimeEntry | null {
  return times.entries.find((e) => e.dt_in && !e.dt_out) ?? null;
}

function rollupTotals(times: ActionTimes): ActionTimes {
  let totalElapsed = 0;
  let totalActive = 0;
  for (const e of times.entries) {
    const el = e.elapsed_ms ?? 0;
    totalElapsed += el;
    totalActive += Math.round(el * ((e.percent_active ?? 100) / 100));
  }
  return { ...times, total_elapsed_ms: totalElapsed, total_active_ms: totalActive };
}

// ── Badge mode — compact pill for TaskCard ─────────────────────────────

interface TimeClockBadgeProps {
  times: any;
  onClick: (updatedTimes: ActionTimes) => void;
}

export const TimeClockBadge: React.FC<TimeClockBadgeProps> = ({ times: rawTimes, onClick }) => {
  const times = useMemo(() => ensureTimes(rawTimes), [rawTimes]);
  const openEntry = getOpenEntry(times);
  const [liveElapsed, setLiveElapsed] = useState(0);

  // Tick every second when clocked in
  useEffect(() => {
    if (!openEntry?.dt_in) return;
    const tick = () => setLiveElapsed(Date.now() - openEntry.dt_in!);
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [openEntry?.dt_in]);

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      const now = Date.now();
      let updated: ActionTimes;

      if (openEntry) {
        // Clock out
        const elapsed = now - (openEntry.dt_in ?? now);
        updated = {
          ...times,
          entries: times.entries.map((entry) =>
            entry.id === openEntry.id
              ? { ...entry, dt_out: now, elapsed_ms: elapsed }
              : entry
          ),
        };
      } else {
        // Clock in
        const newEntry: TimeEntry = {
          id: uuid4(),
          dt_in: now,
          dt_out: null,
          elapsed_ms: null,
          percent_active: 100,
          reason: "",
          notes: "",
          tags: [],
          issue: null,
        };
        updated = { ...times, entries: [...times.entries, newEntry] };
      }
      onClick(rollupTotals(updated));
    },
    [times, openEntry, onClick]
  );

  if (openEntry) {
    // Clocked in — green pulsing badge
    return (
      <button
        onClick={handleClick}
        className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold transition-colors"
        style={{
          background: "color-mix(in srgb, var(--db-accent-green) 15%, transparent)",
          color: "var(--db-accent-green)",
        }}
        title="Click to clock out"
      >
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
        </span>
        {formatElapsed(liveElapsed)}
      </button>
    );
  }

  // Not clocked in — neutral start button
  const totalMs = times.total_elapsed_ms ?? 0;
  return (
    <button
      onClick={handleClick}
      className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors"
      style={{
        background: "var(--db-surface-alt)",
        color: "var(--db-text-muted)",
      }}
      title={totalMs > 0 ? `Total: ${formatElapsed(totalMs)} — click to clock in` : "Click to start timer"}
    >
      <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      {totalMs > 0 ? formatElapsed(totalMs) : "Start"}
    </button>
  );
};

// ── Widget mode — full form/detail widget ──────────────────────────────

export const TimeClockWidget: React.FC<WidgetProps> = ({ value, onChange, disabled }) => {
  const times = useMemo(() => ensureTimes(value), [value]);
  const [editingReason, setEditingReason] = useState<string | null>(null);

  const updateEntry = useCallback(
    (entryId: string, patch: Partial<TimeEntry>) => {
      const updated = {
        ...times,
        entries: times.entries.map((e) => (e.id === entryId ? { ...e, ...patch } : e)),
      };
      onChange(rollupTotals(updated));
    },
    [times, onChange]
  );

  const removeEntry = useCallback(
    (entryId: string) => {
      const updated = {
        ...times,
        entries: times.entries.filter((e) => e.id !== entryId),
      };
      onChange(rollupTotals(updated));
    },
    [times, onChange]
  );

  return (
    <div className="space-y-3">
      {times.entries.length === 0 && (
        <p className="text-[11px] italic" style={{ color: "var(--db-text-dim)" }}>
          No time entries yet.
        </p>
      )}
      {times.entries.map((entry) => {
        const isOpen = entry.dt_in && !entry.dt_out;
        return (
          <div
            key={entry.id}
            className="rounded-lg border px-3 py-2 text-xs"
            style={{
              borderColor: isOpen ? "var(--db-accent-green)" : "var(--db-border)",
              background: isOpen
                ? "color-mix(in srgb, var(--db-accent-green) 5%, transparent)"
                : "var(--db-surface-alt)",
            }}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                {entry.dt_in && (
                  <span style={{ color: "var(--db-text-muted)" }}>
                    {formatDtShort(entry.dt_in)}
                  </span>
                )}
                {entry.dt_out && (
                  <>
                    <span style={{ color: "var(--db-text-dim)" }}>&rarr;</span>
                    <span style={{ color: "var(--db-text-muted)" }}>
                      {formatDtShort(entry.dt_out)}
                    </span>
                  </>
                )}
                {entry.elapsed_ms != null && (
                  <span className="font-semibold" style={{ color: "var(--db-text)" }}>
                    {formatElapsed(entry.elapsed_ms)}
                  </span>
                )}
                {isOpen && (
                  <span className="font-semibold" style={{ color: "var(--db-accent-green)" }}>
                    active
                  </span>
                )}
                {entry.percent_active != null && entry.percent_active < 100 && (
                  <span
                    className="rounded-full px-1.5 py-0.5"
                    style={{
                      background: "color-mix(in srgb, var(--db-accent-gold) 15%, transparent)",
                      color: "var(--db-accent-gold)",
                    }}
                  >
                    {entry.percent_active}% active
                  </span>
                )}
              </div>
              {!disabled && (
                <button
                  onClick={() => removeEntry(entry.id)}
                  className="text-[10px] px-1 rounded hover:bg-red-100"
                  style={{ color: "var(--db-text-dim)" }}
                  title="Remove entry"
                >
                  &times;
                </button>
              )}
            </div>
            {/* Reason — inline editable */}
            {!disabled && editingReason === entry.id ? (
              <input
                autoFocus
                className="mt-1 w-full rounded border px-1.5 py-0.5 text-xs"
                style={{
                  borderColor: "var(--db-border)",
                  background: "var(--db-surface)",
                  color: "var(--db-text)",
                }}
                value={entry.reason || ""}
                onChange={(e) => updateEntry(entry.id, { reason: e.target.value })}
                onBlur={() => setEditingReason(null)}
                onKeyDown={(e) => e.key === "Enter" && setEditingReason(null)}
                placeholder="What was this time for?"
              />
            ) : (
              entry.reason ? (
                <p
                  className="mt-1 cursor-pointer"
                  style={{ color: "var(--db-text-muted)" }}
                  onClick={() => !disabled && setEditingReason(entry.id)}
                >
                  {entry.reason}
                </p>
              ) : !disabled ? (
                <p
                  className="mt-1 cursor-pointer italic"
                  style={{ color: "var(--db-text-dim)" }}
                  onClick={() => setEditingReason(entry.id)}
                >
                  + add reason
                </p>
              ) : null
            )}
            {entry.issue && (
              <p className="mt-1" style={{ color: "var(--db-accent-red)" }}>
                {entry.issue}
              </p>
            )}
            {entry.tags && entry.tags.length > 0 && (
              <div className="mt-1 flex flex-wrap gap-1">
                {entry.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full px-1.5 py-0.5 text-[10px]"
                    style={{ background: "var(--db-surface)", color: "var(--db-text-muted)" }}
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default TimeClockWidget;

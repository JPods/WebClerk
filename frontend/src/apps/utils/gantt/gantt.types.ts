/* LastChecked: 2026-08-09 | WhereUsed: All Gantt components | WhoCreated: Bill+Claude */
/**
 * Native Gantt types — JSON-configurable Gantt chart.
 * Part of the Data-Driven UI architecture.
 */
import React from "react";

// ── Task ──

export interface GanttTask {
  id: string | number;
  text: string;
  start: Date;
  end: Date;
  duration?: number;
  progress?: number;
  type?: "task" | "milestone";
  parent?: string | number;
  open?: boolean;
  // Pixel positions computed by the timeline renderer
  $x?: number;
  $y?: number;
  $w?: number;
  $h?: number;
}

// ── Link (dependency arrow) ──

export type LinkType = "e2s" | "s2s" | "e2e" | "s2e";

export interface GanttLink {
  id: string | number;
  source: string | number;
  target: string | number;
  type: LinkType;
}

// ── Column (left-side grid) ──

export interface GanttColumn {
  id: string;
  header: string;
  width: number;
  align?: "left" | "center" | "right";
  template?: (value: unknown, task: any, column: GanttColumn) => React.ReactNode;
}

// ── Scale (timeline header row) ──

export interface GanttScaleConfig {
  unit: "day" | "week" | "month" | "quarter" | "year";
  step: number;
  format: (date: Date) => string;
}

// ── JSON-driven configuration ──

export interface GanttConfig {
  cellHeight: number;
  cellWidth: number;
  colors: {
    today: string;
    gridLine: string;
    weekendBg: string;
    barDefault: string;
  };
  scales: Record<string, GanttScaleConfig[]>;
}

// ── Default configuration ──

export const DEFAULT_GANTT_CONFIG: GanttConfig = {
  cellHeight: 38,
  cellWidth: 40,
  colors: {
    today: "#ef4444",
    gridLine: "#e5e7eb",
    weekendBg: "#f9fafb",
    barDefault: "#3b82f6",
  },
  scales: {},
};

// ── Drag interaction state ──

export interface DragState {
  taskId: string | number;
  mode: "move" | "resize-left" | "resize-right";
  startX: number;
  originalStart: Date;
  originalEnd: Date;
}

/* LastChecked: 2026-08-09 | WhereUsed: UnifiedGantt | WhoCreated: Bill+Claude */
/**
 * GanttTimeline — Core timeline renderer.
 *
 * Renders the date axis headers, vertical grid lines, weekend shading,
 * today line, sprint boundaries, and positions task bars.
 * Replaces SVAR's <Gantt> rendering engine.
 *
 * Data-Driven UI: configuration (cellHeight, cellWidth, scales) comes from
 * props that can be sourced from JSON.
 */
import {
  type FC,
  type ReactNode,
  type RefObject,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  addDays,
  addWeeks,
  addMonths,
  addYears,
  startOfDay,
  startOfWeek,
  startOfMonth,
  startOfYear,
  differenceInCalendarDays,
  format as dateFnsFormat,
  isWeekend,
  isSameDay,
} from "date-fns";
import type { GanttScaleConfig, DragState } from "./gantt.types";
import type { GanttMappedTask } from "./ganttDataMapper";

// ── Props ──

export interface GanttTimelineProps {
  tasks: GanttMappedTask[];
  scales: GanttScaleConfig[];
  start: Date;
  end: Date;
  cellHeight: number;
  cellWidth?: number;
  taskTemplate: FC<{ data: GanttMappedTask }>;
  sprintEndDates?: Set<string>;
  onUpdateTask?: (id: string | number, updates: { start?: Date; end?: Date }) => void;
  onTaskClick?: (task: GanttMappedTask) => void;
  onTaskDoubleClick?: (task: GanttMappedTask) => void;
  scrollYRef?: RefObject<{ value: number }>;
  onScrollY?: (top: number) => void;
  onScrollX?: (left: number) => void;
  children?: ReactNode; // GanttLinks overlay
  colorMap?: Map<string | number, { bg: string; border: string; text: string }>;
}

// ── Helpers ──

const MS_PER_DAY = 86_400_000;

/** Advance a date by one scale unit × step */
const advanceDate = (date: Date, unit: string, step: number): Date => {
  switch (unit) {
    case "day": return addDays(date, step);
    case "week": return addWeeks(date, step);
    case "month": return addMonths(date, step);
    case "quarter": return addMonths(date, step * 3);
    case "year": return addYears(date, step);
    default: return addDays(date, step);
  }
};

/** Get the start of a scale unit */
const startOfUnit = (date: Date, unit: string): Date => {
  switch (unit) {
    case "day": return startOfDay(date);
    case "week": return startOfWeek(date, { weekStartsOn: 1 });
    case "month": return startOfMonth(date);
    case "quarter": {
      const m = date.getMonth();
      const qStart = m - (m % 3);
      return new Date(date.getFullYear(), qStart, 1);
    }
    case "year": return startOfYear(date);
    default: return startOfDay(date);
  }
};

/** Generate cells for a scale row */
const generateScaleCells = (
  scale: GanttScaleConfig,
  chartStart: Date,
  chartEnd: Date,
  pxPerDay: number,
): Array<{ label: string; x: number; width: number; date: Date }> => {
  const cells: Array<{ label: string; x: number; width: number; date: Date }> = [];
  let current = startOfUnit(chartStart, scale.unit);

  while (current < chartEnd) {
    const next = advanceDate(current, scale.unit, scale.step);
    const cellStart = current < chartStart ? chartStart : current;
    const cellEnd = next > chartEnd ? chartEnd : next;
    const x = differenceInCalendarDays(cellStart, chartStart) * pxPerDay;
    const width = differenceInCalendarDays(cellEnd, cellStart) * pxPerDay;

    if (width > 0) {
      cells.push({ label: scale.format(current), x, width, date: current });
    }
    current = next;
  }
  return cells;
};

// ── Component ──

export const GanttTimeline: FC<GanttTimelineProps> = ({
  tasks,
  scales,
  start,
  end,
  cellHeight,
  cellWidth = 40,
  taskTemplate: TaskTemplate,
  sprintEndDates,
  onUpdateTask,
  onTaskClick,
  onTaskDoubleClick,
  scrollYRef,
  onScrollY,
  onScrollX,
  children,
  colorMap,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dragState, setDragState] = useState<DragState | null>(null);

  // Chart dimensions
  const totalDays = Math.max(1, differenceInCalendarDays(end, start));
  const pxPerDay = cellWidth;
  const chartWidth = totalDays * pxPerDay;
  const scaleHeaderHeight = scales.length * 28;
  const chartContentHeight = tasks.length * cellHeight;

  // Compute task pixel positions
  const positionedTasks = useMemo(() => {
    return tasks.map((task, index) => {
      const taskStart = task.start instanceof Date ? task.start : new Date(task.start);
      const taskEnd = task.end instanceof Date ? task.end : new Date(task.end);
      const x = differenceInCalendarDays(taskStart, start) * pxPerDay;
      const w = Math.max(pxPerDay * 0.5, differenceInCalendarDays(taskEnd, taskStart) * pxPerDay);
      const y = index * cellHeight;
      return { ...task, $x: x, $y: y, $w: w, $h: cellHeight - 4 } as GanttMappedTask & {
        $x: number; $y: number; $w: number; $h: number;
      };
    });
  }, [tasks, start, pxPerDay, cellHeight]);

  // Scale header cells
  const scaleCells = useMemo(
    () => scales.map((s) => generateScaleCells(s, start, end, pxPerDay)),
    [scales, start, end, pxPerDay],
  );

  // Today line position
  const today = new Date();
  const todayX = differenceInCalendarDays(startOfDay(today), start) * pxPerDay;
  const showTodayLine = todayX >= 0 && todayX <= chartWidth;

  // Weekend columns
  const weekendColumns = useMemo(() => {
    const cols: Array<{ x: number }> = [];
    let d = startOfDay(start);
    while (d <= end) {
      if (isWeekend(d)) {
        cols.push({ x: differenceInCalendarDays(d, start) * pxPerDay });
      }
      d = addDays(d, 1);
    }
    return cols;
  }, [start, end, pxPerDay]);

  // Sprint boundary lines
  const sprintLines = useMemo(() => {
    if (!sprintEndDates || sprintEndDates.size === 0) return [];
    const lines: number[] = [];
    let d = startOfDay(start);
    while (d <= end) {
      const key = dateFnsFormat(d, "yyyy-MM-dd");
      if (sprintEndDates.has(key)) {
        lines.push(differenceInCalendarDays(d, start) * pxPerDay);
      }
      d = addDays(d, 1);
    }
    return lines;
  }, [start, end, pxPerDay, sprintEndDates]);

  // ── Scroll sync ──
  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    onScrollY?.(el.scrollTop);
    onScrollX?.(el.scrollLeft);
    if (scrollYRef?.current) {
      scrollYRef.current.value = el.scrollTop;
    }
  }, [onScrollY, onScrollX, scrollYRef]);

  // Sync incoming scrollTop from grid
  useEffect(() => {
    if (!scrollYRef?.current) return;
    const el = containerRef.current;
    if (!el) return;
    const syncId = setInterval(() => {
      const target = scrollYRef.current?.value ?? 0;
      if (Math.abs(el.scrollTop - target) > 1) {
        el.scrollTop = target;
      }
    }, 16);
    return () => clearInterval(syncId);
  }, [scrollYRef]);

  // ── Drag interactions ──
  const handleBarMouseDown = useCallback(
    (e: React.MouseEvent, task: GanttMappedTask & { $x: number; $w: number }) => {
      if (!onUpdateTask) return;
      e.preventDefault();
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;

      const localX = e.clientX - rect.left + (containerRef.current?.scrollLeft || 0);
      const barLeft = task.$x;
      const barRight = task.$x + task.$w;
      const edgeZone = 8;

      let mode: DragState["mode"] = "move";
      if (localX < barLeft + edgeZone) mode = "resize-left";
      else if (localX > barRight - edgeZone) mode = "resize-right";

      setDragState({
        taskId: task.id,
        mode,
        startX: e.clientX,
        originalStart: task.start instanceof Date ? task.start : new Date(task.start),
        originalEnd: task.end instanceof Date ? task.end : new Date(task.end),
      });
    },
    [onUpdateTask],
  );

  useEffect(() => {
    if (!dragState) return;

    const handleMouseMove = (e: MouseEvent) => {
      const dx = e.clientX - dragState.startX;
      const daysDelta = Math.round(dx / pxPerDay);
      if (daysDelta === 0) return;

      let newStart = dragState.originalStart;
      let newEnd = dragState.originalEnd;

      if (dragState.mode === "move") {
        newStart = addDays(dragState.originalStart, daysDelta);
        newEnd = addDays(dragState.originalEnd, daysDelta);
      } else if (dragState.mode === "resize-left") {
        newStart = addDays(dragState.originalStart, daysDelta);
        if (newStart >= newEnd) return;
      } else if (dragState.mode === "resize-right") {
        newEnd = addDays(dragState.originalEnd, daysDelta);
        if (newEnd <= newStart) return;
      }

      onUpdateTask?.(dragState.taskId, { start: newStart, end: newEnd });
    };

    const handleMouseUp = () => setDragState(null);

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [dragState, pxPerDay, onUpdateTask]);

  // Cursor style during drag
  const dragCursor = dragState
    ? dragState.mode === "move" ? "grabbing" : "ew-resize"
    : undefined;

  return (
    <div
      ref={containerRef}
      className="relative flex-1 overflow-auto bg-white dark:bg-gray-900"
      onScroll={handleScroll}
      style={{ cursor: dragCursor }}
      data-wc="GanttTimeline"
    >
      {/* ── Scale headers (sticky top) ── */}
      <div
        className="sticky top-0 z-10 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700"
        style={{ width: chartWidth, minWidth: "100%" }}
      >
        {scaleCells.map((row, ri) => (
          <div key={ri} className="flex h-7 border-b border-gray-100 dark:border-gray-700">
            {row.map((cell, ci) => (
              <div
                key={ci}
                className="text-xs text-gray-600 dark:text-gray-400 font-medium flex items-center justify-center border-r border-gray-100 dark:border-gray-700 whitespace-nowrap overflow-hidden"
                style={{ position: "absolute", left: cell.x, width: cell.width }}
              >
                {cell.label}
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* ── Chart body ── */}
      <div
        className="relative"
        style={{ width: chartWidth, height: chartContentHeight, minWidth: "100%" }}
      >
        {/* Weekend shading */}
        {weekendColumns.map((col, i) => (
          <div
            key={`we-${i}`}
            className="absolute top-0 bottom-0 bg-gray-50 dark:bg-gray-800/40"
            style={{ left: col.x, width: pxPerDay }}
          />
        ))}

        {/* Horizontal row lines */}
        {tasks.map((_, i) => (
          <div
            key={`row-${i}`}
            className="absolute left-0 right-0 border-b border-gray-100 dark:border-gray-800"
            style={{ top: i * cellHeight + cellHeight }}
          />
        ))}

        {/* Sprint boundary lines */}
        {sprintLines.map((x, i) => (
          <div
            key={`sprint-${i}`}
            className="absolute top-0 bottom-0 border-l-2 border-dashed border-blue-300 dark:border-blue-700"
            style={{ left: x }}
          />
        ))}

        {/* Today line */}
        {showTodayLine && (
          <div
            className="absolute top-0 bottom-0 z-[5]"
            style={{ left: todayX }}
          >
            <div className="w-0.5 h-full bg-red-500 dark:bg-red-400" />
            <div className="absolute -top-5 -left-3 text-[10px] font-bold text-red-500 dark:text-red-400 select-none">
              Today
            </div>
          </div>
        )}

        {/* Task bars */}
        {positionedTasks.map((task) => {
          const colors = colorMap?.get(task.id);
          return (
            <div
              key={task.id}
              className="absolute rounded"
              style={{
                left: task.$x,
                top: task.$y + 2,
                width: task.$w,
                height: task.$h,
                backgroundColor: colors?.bg || "#dbeafe",
                borderLeft: `3px solid ${colors?.border || "#3b82f6"}`,
                color: colors?.text || "#111827",
                cursor: onUpdateTask ? "grab" : "pointer",
                minWidth: 4,
              }}
              onMouseDown={(e) => handleBarMouseDown(e, task)}
              onClick={() => onTaskClick?.(task)}
              onDoubleClick={() => onTaskDoubleClick?.(task)}
            >
              <TaskTemplate data={task} />
            </div>
          );
        })}

        {/* SVG overlay for dependency arrows */}
        {children && (
          <div
            className="absolute inset-0 pointer-events-none z-[3]"
            style={{ width: chartWidth, height: chartContentHeight }}
          >
            {children}
          </div>
        )}
      </div>
    </div>
  );
};

export default GanttTimeline;

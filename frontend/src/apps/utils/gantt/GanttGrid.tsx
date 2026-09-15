/* LastChecked: 2026-08-09 | WhereUsed: UnifiedGantt | WhoCreated: Bill+Claude */
/**
 * GanttGrid — Left-side task list columns.
 *
 * Renders a scrollable table of task metadata (ida, dates, progress, etc.)
 * with synchronized vertical scrolling to GanttTimeline.
 */
import {
  type FC,
  type RefObject,
  useCallback,
  useRef,
  useEffect,
} from "react";
import type { GanttColumn } from "./gantt.types";
import type { GanttMappedTask } from "./ganttDataMapper";

export interface GanttGridProps {
  columns: GanttColumn[];
  tasks: GanttMappedTask[];
  cellHeight: number;
  scaleHeaderHeight: number;
  scrollYRef?: RefObject<{ value: number }>;
  onScrollY?: (top: number) => void;
  onTaskClick?: (task: GanttMappedTask) => void;
  onTaskDoubleClick?: (task: GanttMappedTask) => void;
  onMoveTask?: (taskId: string, direction: "up" | "down") => void;
}

export const GanttGrid: FC<GanttGridProps> = ({
  columns,
  tasks,
  cellHeight,
  scaleHeaderHeight,
  scrollYRef,
  onScrollY,
  onTaskClick,
  onTaskDoubleClick,
  onMoveTask,
}) => {
  const bodyRef = useRef<HTMLDivElement>(null);
  const totalWidth = columns.reduce((sum, c) => sum + c.width, 0);

  // ── Scroll sync ──
  const handleScroll = useCallback(() => {
    const el = bodyRef.current;
    if (!el) return;
    onScrollY?.(el.scrollTop);
    if (scrollYRef?.current) {
      scrollYRef.current.value = el.scrollTop;
    }
  }, [onScrollY, scrollYRef]);

  // Sync incoming scrollTop from timeline
  useEffect(() => {
    if (!scrollYRef?.current) return;
    const el = bodyRef.current;
    if (!el) return;
    const syncId = setInterval(() => {
      const target = scrollYRef.current?.value ?? 0;
      if (Math.abs(el.scrollTop - target) > 1) {
        el.scrollTop = target;
      }
    }, 16);
    return () => clearInterval(syncId);
  }, [scrollYRef]);

  return (
    <div
      className="flex flex-col select-none"
      style={{ width: totalWidth, minWidth: totalWidth, flexShrink: 0, borderRight: '1px solid var(--db-border)', background: 'var(--db-surface)' }}
      data-wc="GanttGrid"
    >
      {/* ── Column headers ── */}
      <div
        className="flex"
        style={{ height: scaleHeaderHeight, minHeight: scaleHeaderHeight, borderBottom: '1px solid var(--db-border)', background: 'var(--db-surface-alt)' }}
      >
        {columns.map((col) => (
          <div
            key={col.id}
            className="flex items-end justify-center pb-1 text-[11px] font-semibold whitespace-nowrap overflow-hidden"
            style={{ width: col.width, textAlign: col.align || "center", color: 'var(--db-text-muted)', borderRight: '1px solid var(--db-border-light)' }}
            title={col.header}
          >
            {col.header}
          </div>
        ))}
      </div>

      {/* ── Task rows ── */}
      <div
        ref={bodyRef}
        className="overflow-y-auto overflow-x-hidden flex-1"
        onScroll={handleScroll}
      >
        {tasks.map((task, rowIndex) => (
          <div
            key={task.id}
            className="flex items-center cursor-pointer"
            style={{
              height: cellHeight,
              borderBottom: '1px solid var(--db-border-light)',
              background: rowIndex % 2 === 0 ? undefined : 'var(--db-surface-alt)',
            }}
            onClick={() => onTaskClick?.(task)}
            onDoubleClick={() => onTaskDoubleClick?.(task)}
          >
            {columns.map((col) => {
              // Reorder column renders move buttons
              if (col.id === "reorder" && onMoveTask) {
                return (
                  <div
                    key={col.id}
                    className="flex items-center justify-center gap-0.5"
                    style={{ width: col.width }}
                  >
                    <button
                      className="text-xs leading-none p-0.5"
                      style={{ color: 'var(--db-text-dim)' }}
                      onClick={(e) => { e.stopPropagation(); onMoveTask(String(task.id), "up"); }}
                      title="Move up"
                    >
                      ▲
                    </button>
                    <button
                      className="text-xs leading-none p-0.5"
                      style={{ color: 'var(--db-text-dim)' }}
                      onClick={(e) => { e.stopPropagation(); onMoveTask(String(task.id), "down"); }}
                      title="Move down"
                    >
                      ▼
                    </button>
                  </div>
                );
              }

              // Template-driven cell
              const cellContent = col.template
                ? col.template(undefined, task, col)
                : "-";

              return (
                <div
                  key={col.id}
                  className="text-xs overflow-hidden whitespace-nowrap px-1"
                  style={{
                    width: col.width,
                    textAlign: col.align || "left",
                    color: 'var(--db-text)',
                  }}
                >
                  {cellContent}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
};

export default GanttGrid;

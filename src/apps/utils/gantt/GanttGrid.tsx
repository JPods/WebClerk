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
      className="flex flex-col border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 select-none"
      style={{ width: totalWidth, minWidth: totalWidth, flexShrink: 0 }}
      data-wc="GanttGrid"
    >
      {/* ── Column headers ── */}
      <div
        className="flex border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800"
        style={{ height: scaleHeaderHeight, minHeight: scaleHeaderHeight }}
      >
        {columns.map((col) => (
          <div
            key={col.id}
            className="flex items-end justify-center pb-1 text-[11px] font-semibold text-gray-500 dark:text-gray-400 border-r border-gray-100 dark:border-gray-700 whitespace-nowrap overflow-hidden"
            style={{ width: col.width, textAlign: col.align || "center" }}
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
            className={`flex items-center border-b border-gray-50 dark:border-gray-800 hover:bg-blue-50/40 dark:hover:bg-blue-900/20 cursor-pointer ${
              rowIndex % 2 === 0 ? "" : "bg-gray-50/30 dark:bg-gray-800/20"
            }`}
            style={{ height: cellHeight }}
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
                      className="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 text-xs leading-none p-0.5"
                      onClick={(e) => { e.stopPropagation(); onMoveTask(String(task.id), "up"); }}
                      title="Move up"
                    >
                      ▲
                    </button>
                    <button
                      className="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 text-xs leading-none p-0.5"
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
                  className="text-xs text-gray-700 dark:text-gray-300 overflow-hidden whitespace-nowrap px-1"
                  style={{
                    width: col.width,
                    textAlign: col.align || "left",
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

/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { memo, useEffect, useMemo, useRef } from "react";
import { useDrag, useDrop } from "react-dnd";
import { getEmptyImage } from "react-dnd-html5-backend";
import clsx from "clsx";
import type { KanbanTask, TaskPriority } from "./type/kanban";
import { DRAG_TYPE_TASK, type DragItem, type DropResult } from "./dndTypes";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

const priorityStyles: Record<TaskPriority, string> = {
  low: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-200",
  medium: "bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-200",
  high: "bg-orange-100 text-orange-700 dark:bg-orange-500/10 dark:text-orange-200",
  critical: "bg-rose-100 text-rose-700 dark:bg-rose-500/10 dark:text-rose-200",
};

const priorityLabel: Record<TaskPriority, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

const getInitials = (value?: string) => {
  if (!value) return "?";
  const [first = "", second = ""] = value.split(" ");
  return `${first.charAt(0)}${second.charAt(0)}`.toUpperCase();
};

interface TaskCardProps {
  task: KanbanTask;
  columnId: string;
  index: number;
  onDragEnd: (item: DragItem, dropResult: DropResult | null) => void;
  onTaskClick?: (task: KanbanTask) => void;
  isSubtask?: boolean;
}

const TaskCardComponent: React.FC<TaskCardProps> = ({ task, columnId, index, onDragEnd, onTaskClick, isSubtask = false }) => {
  const ref = useRef<HTMLDivElement | null>(null);

  const [{ isDragging }, drag, preview] = useDrag(
    () => ({
      type: DRAG_TYPE_TASK,
      item: { type: DRAG_TYPE_TASK, taskId: task.id, sourceColumnId: columnId, index },
      end: (item: DragItem, monitor) => {
        const dropResult = monitor.getDropResult<DropResult | null>();
        if (item) {
          onDragEnd(item, dropResult ?? null);
        }
      },
      collect: (monitor) => ({
        isDragging: monitor.isDragging(),
      }),
    }),
    [task.id, columnId, index, onDragEnd]
  );

  useEffect(() => {
    // Disable the default browser drag preview so only the custom layer is shown
    preview(getEmptyImage(), { captureDraggingState: true });
  }, [preview]);

  const [{ isOver, canDrop }, drop] = useDrop<DragItem, DropResult, { isOver: boolean; canDrop: boolean }>(
    () => ({
      accept: DRAG_TYPE_TASK,
      drop: () => ({ columnId, index, dropType: "column" as const }),
      collect: (monitor) => ({
        isOver: monitor.isOver({ shallow: true }),
        canDrop: monitor.canDrop(),
      }),
    }),
    [columnId, index]
  );

  drag(drop(ref));

  const wc3PriorityRaw = task.priority_value;
  const wc3Priority: TaskPriority = wc3PriorityRaw >= 4 ? "critical" : wc3PriorityRaw >= 3 ? "high" : wc3PriorityRaw >= 2 ? "medium" : "low";
  const priorityClass = priorityStyles[wc3Priority];
  const priorityText = priorityLabel[wc3Priority];

  const progressLabel = useMemo(() => {
    const pct = task.percent_complete;
    if (typeof pct !== "number") return null;
    const clamped = Math.max(0, Math.min(100, Math.round(pct)));
    return `${clamped}%`;
  }, [task.percent_complete]);

  return (
    <div
      ref={ref}
      onClick={() => onTaskClick?.(task)}
      className={clsx(
        "group relative rounded-xl border border-transparent p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-lg cursor-pointer",
        {
          // Hide the original card while dragging so only the drag preview shows
          "opacity-0": isDragging,
          "ring-2 ring-indigo-400": isOver && canDrop,
          // Subtask styling
          "bg-indigo-50/80 border-indigo-100 dark:bg-indigo-500/5 dark:border-indigo-500/20": isSubtask,
          // Regular task styling
          "bg-white/80 dark:bg-white/5": !isSubtask,
        }
      )}
    >
        <div className="flex items-start justify-between gap-4">
          {task.ida && (
            <span className="text-xs text-gray-400">{task.ida}</span>
          )}
        <div className="flex items-start gap-2">
          {isSubtask && (
            <div className="mt-1 flex-shrink-0">
              <svg 
                className="h-3 w-3 text-indigo-400 dark:text-indigo-300" 
                viewBox="0 0 12 12" 
                fill="none" 
                xmlns="http://www.w3.org/2000/svg"
              >
                <path 
                  d="M3 6h6M6 3v6" 
                  stroke="currentColor" 
                  strokeWidth={1.5} 
                  strokeLinecap="round" 
                />
              </svg>
            </div>
          )}
          <div>
            <div className="mb-2 flex items-center gap-2">
              <span className="rounded-md bg-gray-100 px-2 py-0.5 text-[10px] font-mono font-semibold text-gray-600 dark:bg-gray-700/60 dark:text-gray-300">
                #{task.id}
              </span>
              {task.project_name && (
                <p className="text-xs text-gray-600 rounded-full bg-indigo-100 px-2.5 py-0.5 dark:text-white">{task.project_name}</p>
              )}
            </div>
            <p className="text-sm font-semibold text-gray-900 dark:text-white">{task.title_translations?.en ?? Object.values(task.title_translations ?? {})[0]}</p>
            {task.description_translations && (
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-300 line-clamp-2">{task.description_translations.en ?? Object.values(task.description_translations)[0]}</p>
            )}
          </div>
        </div>
        <span className={clsx("rounded-full px-3 py-1 text-xs font-semibold", priorityClass)}>{priorityText}</span>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
        {task.properties?.dates?.start?.dt && (
          <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-1 text-[11px] font-medium text-gray-600 dark:bg-gray-700/60 dark:text-gray-200">
            Start:
             {new Date(task.properties.dates.start.dt).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
          </span>
        )}

        {task.properties?.dates?.expected?.dt && (
          <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-1 text-[11px] font-medium text-gray-600 dark:bg-gray-700/60 dark:text-gray-200">
            Expected:
             {new Date(task.properties.dates.expected.dt).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
          </span>
        )}

        {task.properties?.dates?.due?.dt && (
          <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-1 text-[11px] font-medium text-gray-600 dark:bg-gray-700/60 dark:text-gray-200">
            Due:
             {new Date(task.properties.dates.due.dt).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
          </span>
        )}

        {/* Duration display */}
        {(task.duration != null || (task.dt_start && task.dt_deadline)) && (
          <span className="inline-flex items-center gap-1 rounded-full bg-purple-100 px-2 py-1 text-[11px] font-medium text-purple-600 dark:bg-purple-500/10 dark:text-purple-200">
            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {task.duration != null 
              ? `${task.duration}d`
              : (() => {
                  const start = new Date(task.dt_start!);
                  const end = new Date(task.dt_deadline!);
                  const days = Math.max(1, Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)));
                  return `${days}d`;
                })()
            }
          </span>
        )}

        {task.properties?.dates?.completed?.dt && (
          <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-1 text-[11px] font-medium text-gray-600 dark:bg-gray-700/60 dark:text-gray-200">
            Completed:
             {new Date(task.properties.dates.completed.dt).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
          </span>
        )}
        {progressLabel && (
          <span className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2 py-1 text-[11px] font-semibold text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-200">
            <span className="h-2 w-2 rounded-full bg-indigo-400" />
            {progressLabel}
          </span>
        )}
      </div>

      <div className="mt-4 flex items-center justify-between">
        <div className="flex flex-wrap items-center gap-2">
          {task.tags?.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center rounded-full bg-gray-100 px-2 py-1 text-[11px] font-medium text-gray-600 dark:bg-gray-700/60 dark:text-gray-200"
            >
              {tag}
            </span>
          ))}
        </div>
        {Array.isArray(task.assigned_to) && task.assigned_to.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
              {task.assigned_to.map((a:any) => a.name).join(', ')}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export const TaskCard = memo(TaskCardComponent);
export default withDevIdentifier(TaskCard, 'TaskCard', 'amber', 'apps/utils/kanban/TaskCard.tsx');
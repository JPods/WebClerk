/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { memo, useMemo, useRef } from "react";
import { useDrop } from "react-dnd";
import clsx from "clsx";
import type { KanbanColumn as KanbanColumnType, KanbanTask } from "./type/kanban";
import { DRAG_TYPE_TASK, type DragItem, type DropResult } from "./dndTypes";
import { TaskCard, type MoveToProjectOption } from "./TaskCard";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

interface KanbanColumnProps {
  column: KanbanColumnType;
  tasks: KanbanTask[];
  onDragEnd: (item: DragItem, dropResult: DropResult | null) => void;
  onTaskClick?: (task: KanbanTask) => void;
  className?: string;
  moveToOptions?: MoveToProjectOption[];
  onMoveToProject?: (taskId: string | number, projectId: string, projectName: string) => void;
}

const KanbanColumnComponent: React.FC<KanbanColumnProps> = ({ column, tasks, onDragEnd, onTaskClick, className, moveToOptions, onMoveToProject }) => {
  const columnRef = useRef<HTMLDivElement | null>(null);

  const [{ isOver, canDrop }, drop] = useDrop<DragItem, DropResult, { isOver: boolean; canDrop: boolean }>(
    () => ({
      accept: DRAG_TYPE_TASK,
      drop: (_item, monitor) => {
        if (!monitor.didDrop()) {
          return { columnId: column.id, index: tasks.length, dropType: "column" as const };
        }
        return undefined;
      },
      collect: (monitor) => ({
        isOver: monitor.isOver({ shallow: true }),
        canDrop: monitor.canDrop(),
      }),
    }),
    [column.id, tasks.length]
  );

  drop(columnRef);

  const progress = useMemo(() => {
    if (tasks.length === 0) return 0;
    const withProgress = tasks.filter((task) => typeof task.percent_complete === "number");
    if (withProgress.length === 0) return 0;
    const total = withProgress.reduce((acc, task) => acc + (task.percent_complete ?? 0), 0);
    return Math.round(total / withProgress.length);
  }, [tasks]);


  return (
    <section
      ref={columnRef}
      className={clsx(
        "flex h-full min-h-[420px] w-full flex-col rounded-3xl p-4 shadow-sm transition",
        {
          "ring-2 ring-indigo-400/70": isOver && canDrop,
        },
        className
      )}
      style={{ border: '1px solid var(--db-border)', background: 'var(--db-surface-alt)' }}
    >
      <header className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h3 className="db-font-sm font-semibold uppercase tracking-wide" style={{ color: 'var(--db-text-muted)' }}>{column.title}</h3>
          <p className="db-font-xs" style={{ color: 'var(--db-text-dim)' }}>
            {tasks.length} task{tasks.length === 1 ? "" : "s"}
            {typeof column.wip_limit === "number" && (
              <span className="ml-2 inline-flex items-center rounded-full bg-amber-500/10 px-2 py-0.5 db-font-xs font-semibold text-amber-600">
                WIP {tasks.length}/{column.wip_limit}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2 db-font-xs" style={{ color: 'var(--db-text-dim)' }}>
          <span className="inline-flex h-2 w-2 rounded-full bg-indigo-400" />
          {progress}% avg. percent_complete
        </div>
      </header>

      <div className="flex-1 space-y-3">
        {tasks.map((task, index) => (
          <TaskCard
            key={task.id}
            task={task}
            columnId={column.id}
            index={index}
            onDragEnd={onDragEnd}
            onTaskClick={onTaskClick}
            moveToOptions={moveToOptions}
            onMoveToProject={onMoveToProject}
          />
        ))}
        {tasks.length === 0 && (
          <div className="flex h-full min-h-[140px] items-center justify-center rounded-xl border border-dashed db-font-xs" style={{ borderColor: 'var(--db-border)', color: 'var(--db-text-dim)' }}>
            Drop tasks here
          </div>
        )}
      </div>
    </section>
  );
};

export const KanbanColumn = memo(KanbanColumnComponent);
export default withDevIdentifier(KanbanColumn, 'KanbanColumn', 'rose', 'apps/utils/kanban/KanbanColumn.tsx');
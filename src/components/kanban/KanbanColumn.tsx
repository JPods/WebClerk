import { memo, useMemo, useRef } from "react";
import { useDrop } from "react-dnd";
import clsx from "clsx";
import type { KanbanColumn as KanbanColumnType, KanbanTask } from "../../type/kanban";
import { DRAG_TYPE_TASK, type DragItem, type DropResult } from "./dndTypes";
import { TaskCard } from "./TaskCard";

interface TaskWithIndent {
  task: KanbanTask;
  indent: number;
  isSubtask: boolean;
}

interface KanbanColumnProps {
  column: KanbanColumnType;
  tasks: KanbanTask[];
  onDragEnd: (item: DragItem, dropResult: DropResult | null) => void;
  onTaskClick?: (task: KanbanTask) => void;
  className?: string;
}

const organizeTasksHierarchically = (tasks: KanbanTask[]): TaskWithIndent[] => {
  const organized: TaskWithIndent[] = [];
  const taskMap = new Map(tasks.map(task => [task.id, task]));
  
  // Find all parent tasks (tasks that have children but are not children themselves)
  const parentTasks = tasks.filter(task => 
    task.children && task.children.length > 0 && 
    !tasks.some(otherTask => 
      otherTask.children?.some(child => child.id === task.id)
    )
  );
  
  // Find all standalone tasks (no children and not a child of any task)
  const standaloneTasks = tasks.filter(task => 
    (!task.children || task.children.length === 0) &&
    !tasks.some(otherTask => 
      otherTask.children?.some(child => child.id === task.id)
    )
  );
  
  // Add standalone tasks first
  standaloneTasks.forEach(task => {
    organized.push({ task, indent: 0, isSubtask: false });
  });
  
  // Add parent tasks and their children
  parentTasks.forEach(parentTask => {
    // Add parent task
    organized.push({ task: parentTask, indent: 0, isSubtask: false });
    
    // Add children with indentation
    parentTask.children?.forEach(child => {
      const childTask = taskMap.get(child.id.toString());
      if (childTask) {
        organized.push({ task: childTask, indent: 1, isSubtask: true });
      }
    });
  });
  
  return organized;
};

const KanbanColumnComponent: React.FC<KanbanColumnProps> = ({ column, tasks, onDragEnd, onTaskClick, className }) => {
  const columnRef = useRef<HTMLDivElement | null>(null);

  const [{ isOver, canDrop }, drop] = useDrop<DragItem, DropResult, { isOver: boolean; canDrop: boolean }>(
    () => ({
      accept: DRAG_TYPE_TASK,
      drop: (_item, monitor) => {
        if (!monitor.didDrop()) {
          return { columnId: column.id, index: tasks.length };
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
    const withProgress = tasks.filter((task) => typeof task.progress === "number");
    if (withProgress.length === 0) return 0;
    const total = withProgress.reduce((acc, task) => acc + (task.progress ?? 0), 0);
    return Math.round(total / withProgress.length);
  }, [tasks]);

  const organizedTasks = useMemo(() => organizeTasksHierarchically(tasks), [tasks]);

  return (
    <section
      ref={columnRef}
      className={clsx(
        "flex h-full min-h-[420px] w-full flex-col rounded-3xl border border-gray-200 bg-gray-50/60 p-4 shadow-sm transition dark:border-gray-700 dark:bg-gray-900/40",
        {
          "ring-2 ring-indigo-400/70": isOver && canDrop,
        },
        className
      )}
    >
      <header className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">{column.title}</h3>
          <p className="text-xs text-gray-400 dark:text-gray-500">
            {tasks.length} task{tasks.length === 1 ? "" : "s"}
            {typeof column.wipLimit === "number" && (
              <span className="ml-2 inline-flex items-center rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold text-amber-600 dark:text-amber-200">
                WIP {tasks.length}/{column.wipLimit}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
          <span className="inline-flex h-2 w-2 rounded-full bg-indigo-400" />
          {progress}% avg. progress
        </div>
      </header>

      <div className="flex-1 space-y-3">
        {organizedTasks.map(({ task, isSubtask }, index) => (
          <div
            key={task.id}
            className={clsx(
              "transition-all duration-200",
              {
                "ml-4 border-l-2 border-l-indigo-200 pl-3 dark:border-l-indigo-800": isSubtask,
              }
            )}
          >
            <TaskCard 
              key={task.id} 
              task={task} 
              columnId={column.id} 
              index={index} 
              onDragEnd={onDragEnd}
              onTaskClick={onTaskClick}
              isSubtask={isSubtask}
            />
          </div>
        ))}
        {tasks.length === 0 && (
          <div className="flex h-full min-h-[140px] items-center justify-center rounded-xl border border-dashed border-gray-300 text-xs text-gray-400 dark:border-gray-700 dark:text-gray-500">
            Drop tasks here
          </div>
        )}
      </div>
    </section>
  );
};

export const KanbanColumn = memo(KanbanColumnComponent);
export default KanbanColumn;

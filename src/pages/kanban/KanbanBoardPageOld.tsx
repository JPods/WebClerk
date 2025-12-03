import { CSSProperties, FormEvent, useCallback, useMemo, useState } from "react";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import { KanbanColumn } from "../../components/kanban/KanbanColumn";
import type { BoardData, KanbanColumn as KanbanColumnType, KanbanTask, TaskPriority } from "../../type/kanban";
import type { DragItem, DropResult } from "../../components/kanban/dndTypes";
import { DRAG_TYPE_TASK } from "../../components/kanban/dndTypes";
import clsx from "clsx";

const seedBoard: BoardData = {
  tasks: {
    "task-1": {
      id: "task-1",
      title: "Persona maps & discovery notes",
      description: "Synthesize user interviews into actionable personas for the growth epic.",
      priority: "high",
      assignee: "Maya Patel",
      dueDate: new Date().toISOString(),
      tags: ["Discovery", "Research"],
      progress: 35,
    },
    "task-2": {
      id: "task-2",
      title: "Backend contract for v2 API",
      description: "Define request/response schema and agree on pagination strategy with backend team.",
      priority: "critical",
      assignee: "Colin Rivera",
      dueDate: new Date(Date.now() + 4 * 24 * 60 * 60 * 1000).toISOString(),
      tags: ["API", "Backend"],
      progress: 10,
    },
    "task-3": {
      id: "task-3",
      title: "Visual design refresh",
      description: "Update typography scale and audit existing color usage to match new design tokens.",
      priority: "medium",
      assignee: "Akari Watanabe",
      dueDate: new Date(Date.now() + 9 * 24 * 60 * 60 * 1000).toISOString(),
      tags: ["Design", "UI"],
      progress: 55,
    },
    "task-4": {
      id: "task-4",
      title: "QA regression suite",
      description: "Automate the top ten revenue-critical flows in Playwright.",
      priority: "high",
      assignee: "Enzo García",
      dueDate: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(),
      tags: ["QA", "Automation"],
      progress: 20,
    },
    "task-5": {
      id: "task-5",
      title: "Stakeholder review",
      description: "Run through the latest build and collect sign-off notes from revenue ops.",
      priority: "medium",
      assignee: "Selena Cho",
      dueDate: new Date(Date.now() + 6 * 24 * 60 * 60 * 1000).toISOString(),
      tags: ["Review"],
      progress: 80,
    },
    "task-6": {
      id: "task-6",
      title: "Release checklist",
      description: "Consolidate rollout plan, metrics tracking, and comms templates for launch.",
      priority: "low",
      assignee: "Samir Lang",
      dueDate: new Date(Date.now() + 11 * 24 * 60 * 60 * 1000).toISOString(),
      tags: ["Operations"],
      progress: 15,
    },
    "task-7": {
      id: "task-7",
      title: "Ship analytics instrumentation",
      description: "Add success metrics to the experiment funnel and document dashboards.",
      priority: "high",
      assignee: "Maya Patel",
      dueDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      tags: ["Analytics"],
      progress: 65,
    },
  },
  columns: {
    "column-backlog": {
      id: "column-backlog",
      title: "Backlog",
      taskIds: ["task-6"],
    },
    "column-planning": {
      id: "column-planning",
      title: "Planning",
      taskIds: ["task-1", "task-2"],
      wipLimit: 4,
    },
    "column-in-progress": {
      id: "column-in-progress",
      title: "In Progress",
      taskIds: ["task-3", "task-4", "task-7"],
      wipLimit: 5,
    },
    "column-review": {
      id: "column-review",
      title: "Review",
      taskIds: ["task-5"],
      wipLimit: 3,
    },
    "column-done": {
      id: "column-done",
      title: "Done",
      taskIds: [],
    },
  },
  columnOrder: ["column-backlog", "column-planning", "column-in-progress", "column-review", "column-done"],
};

const priorityPalette: Record<TaskPriority, string> = {
  low: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-300",
  medium: "bg-amber-500/10 text-amber-600 dark:text-amber-300",
  high: "bg-orange-500/10 text-orange-600 dark:text-orange-300",
  critical: "bg-rose-500/10 text-rose-600 dark:text-rose-300",
};

interface OnDragEndArgs {
  item: DragItem;
  result: DropResult | null;
}

type CreateTaskFormState = {
  title: string;
  description: string;
  columnId: string;
  priority: TaskPriority;
  dueDate: string;
  assignee: string;
};

const priorityOptions: TaskPriority[] = ["low", "medium", "high", "critical"];

const createTaskId = () => {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `task-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
};

const handleBoardMove = (prev: BoardData, { item, result }: OnDragEndArgs): BoardData => {
  if (!result) return prev;

  const sourceColumn = prev.columns[item.sourceColumnId];
  const destinationColumn = prev.columns[result.columnId];

  if (!sourceColumn || !destinationColumn) return prev;

  const sourceIndex = sourceColumn.taskIds.indexOf(item.taskId);
  if (sourceIndex === -1) return prev;

  const destinationColumnId = result.columnId;
  const rawDestinationIndex = result.index;

  if (item.sourceColumnId === destinationColumnId && sourceIndex === rawDestinationIndex) {
    return prev;
  }

  const nextColumns: Record<string, KanbanColumnType> = { ...prev.columns };

  const removeFromSource = () => {
    const updated = [...sourceColumn.taskIds];
    updated.splice(sourceIndex, 1);
    nextColumns[sourceColumn.id] = { ...sourceColumn, taskIds: updated };
    return updated;
  };

  if (item.sourceColumnId === destinationColumnId) {
  const withoutTask = removeFromSource();
  let insertIndex = rawDestinationIndex;
    if (insertIndex > sourceIndex) {
      insertIndex -= 1;
    }
    const clampedIndex = Math.max(0, Math.min(insertIndex, withoutTask.length));
    const reordered = [...withoutTask];
    reordered.splice(clampedIndex, 0, item.taskId);

    if (sourceColumn.taskIds.join() === reordered.join()) {
      return prev;
    }

    nextColumns[sourceColumn.id] = { ...sourceColumn, taskIds: reordered };
    return { ...prev, columns: nextColumns };
  }

  removeFromSource();
  const destinationTaskIds = [...destinationColumn.taskIds];
  const clampedIndex = Math.max(0, Math.min(rawDestinationIndex, destinationTaskIds.length));
  destinationTaskIds.splice(clampedIndex, 0, item.taskId);

  nextColumns[destinationColumn.id] = { ...destinationColumn, taskIds: destinationTaskIds };

  return {
    ...prev,
    columns: nextColumns,
  };
};

const KanbanBoardPage: React.FC = () => {
  const [board, setBoard] = useState<BoardData>(() => seedBoard);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const defaultColumnId = seedBoard.columnOrder[0] ?? "column-backlog";
  const [createTaskState, setCreateTaskState] = useState<CreateTaskFormState>({
    title: "",
    description: "",
    columnId: defaultColumnId,
    priority: "medium",
    dueDate: "",
    assignee: "",
  });
  const [columnsPerRow, setColumnsPerRow] = useState<number>(5);

  const handleDragEnd = useCallback(
    (item: DragItem, dropResult: DropResult | null) => {
      if (item.type !== DRAG_TYPE_TASK) return;
      setBoard((prev) => handleBoardMove(prev, { item, result: dropResult }));
    },
    []
  );

  const columns = useMemo(
    () =>
      board.columnOrder
        .map((columnId) => board.columns[columnId])
        .filter((column): column is KanbanColumnType => Boolean(column)),
    [board]
  );

  const columnOptions = useMemo(() => columns.map((column) => ({ id: column.id, title: column.title })), [columns]);

  const columnDensityOptions = useMemo(() => {
    const maxOption = Math.max(5, columns.length);
    const options: number[] = [];
    for (let count = 2; count <= Math.min(8, maxOption); count += 1) {
      options.push(count);
    }
    if (!options.includes(5)) {
      options.push(5);
    }
    return Array.from(new Set(options)).sort((a, b) => a - b);
  }, [columns.length]);

  const prioritySummary = useMemo(() => {
    const base: Record<TaskPriority, number> = {
      low: 0,
      medium: 0,
      high: 0,
      critical: 0,
    };

    Object.values(board.tasks).forEach((task) => {
      base[task.priority] += 1;
    });

    return base;
  }, [board.tasks]);

  const totalTasks = useMemo(() => Object.keys(board.tasks).length, [board.tasks]);

  const resetCreateState = useCallback(() => {
    const firstColumn = board.columnOrder[0] ?? defaultColumnId;
    setCreateTaskState({
      title: "",
      description: "",
      columnId: firstColumn,
      priority: "medium",
      dueDate: "",
      assignee: "",
    });
  }, [board.columnOrder, defaultColumnId]);

  const handleOpenCreateModal = () => {
    resetCreateState();
    setIsCreateModalOpen(true);
  };

  const handleCloseCreateModal = () => {
    setIsCreateModalOpen(false);
  };

  const handleCreateTaskChange = (field: keyof CreateTaskFormState, value: string) => {
    setCreateTaskState((prev) => ({ ...prev, [field]: value }));
  };

  const handleCreateTaskSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedTitle = createTaskState.title.trim();
    if (!trimmedTitle) {
      return;
    }

    setBoard((prev) => {
      const column = prev.columns[createTaskState.columnId];
      if (!column) return prev;
      const taskId = createTaskId();
      const payload: KanbanTask = {
        id: taskId,
        title: trimmedTitle,
        description: createTaskState.description.trim() || undefined,
        priority: createTaskState.priority,
        assignee: createTaskState.assignee.trim() || undefined,
        dueDate: createTaskState.dueDate || undefined,
        progress: 0,
        tags: [],
      };

      return {
        ...prev,
        tasks: {
          ...prev.tasks,
          [taskId]: payload,
        },
        columns: {
          ...prev.columns,
          [column.id]: {
            ...column,
            taskIds: [...column.taskIds, taskId],
          },
        },
      };
    });

    handleCloseCreateModal();
  };

  const gridStyle = useMemo<CSSProperties>(() => ({
    gridTemplateColumns: `repeat(${Math.max(1, columnsPerRow)}, minmax(0, 1fr))`,
  }), [columnsPerRow]);

  return (
    <div className="space-y-6">
      <PageBreadcrumb pageTitle="Kanban Board" />

      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Keep work flowing</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Drag tasks across columns to reshuffle priorities, track progress, and visualize throughput in real time.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-500 shadow-sm dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300">
            <span>Columns</span>
            <select
              value={columnsPerRow}
              onChange={(event) => setColumnsPerRow(Number(event.target.value))}
              className="rounded-md border border-gray-200 bg-transparent px-2 py-1 text-xs font-semibold text-gray-700 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 dark:border-gray-700 dark:text-gray-200"
            >
              {columnDensityOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <button
            onClick={handleOpenCreateModal}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 5v14m7-7H5" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            New Task
          </button>
          <button className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 8v8m-4-4h8" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
              <path d="M6.5 4h11a2.5 2.5 0 012.5 2.5v11a2.5 2.5 0 01-2.5 2.5h-11A2.5 2.5 0 014 17.5v-11A2.5 2.5 0 016.5 4z" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Manage Columns
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {(Object.keys(prioritySummary) as TaskPriority[]).map((priority) => (
          <div
            key={priority}
            className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900/40"
          >
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">{priority}</p>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-3xl font-semibold text-gray-900 dark:text-white">{prioritySummary[priority]}</span>
              <span className="text-xs font-medium text-gray-400">/ {totalTasks} tasks</span>
            </div>
            <span className={clsx("mt-4 inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold", priorityPalette[priority])}>
              Priority lane
            </span>
          </div>
        ))}
      </div>

      <DndProvider backend={HTML5Backend}>
        <div className="grid gap-5 pb-6" style={gridStyle}>
          {columns.map((column) => {
            const tasks: KanbanTask[] = column.taskIds
              .map((taskId) => board.tasks[taskId])
              .filter((task): task is KanbanTask => Boolean(task));

            return (
              <KanbanColumn
                key={column.id}
                column={column}
                tasks={tasks}
                onDragEnd={handleDragEnd}
                className="h-full"
              />
            );
          })}
        </div>
      </DndProvider>

      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4 py-6 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-3xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-800 dark:bg-gray-900">
            <div className="mb-4 flex items-start justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Create new task</h2>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Add the essentials and drop it in the right column.</p>
              </div>
              <button
                onClick={handleCloseCreateModal}
                className="rounded-full p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800"
                aria-label="Close"
              >
                <svg className="h-5 w-5" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M6 6l8 8M14 6l-8 8" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>

            <form className="space-y-4" onSubmit={handleCreateTaskSubmit}>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">task_title</label>
                <input
                  className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                  value={createTaskState.title}
                  onChange={(event) => handleCreateTaskChange("title", event.target.value)}
                  placeholder="task_title"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">description</label>
                <textarea
                  className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                  rows={3}
                  value={createTaskState.description}
                  onChange={(event) => handleCreateTaskChange("description", event.target.value)}
                  placeholder="description"
                />
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">column</label>
                  <select
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={createTaskState.columnId}
                    onChange={(event) => handleCreateTaskChange("columnId", event.target.value)}
                  >
                    {columnOptions.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.title}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">priority</label>
                  <select
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={createTaskState.priority}
                    onChange={(event) => handleCreateTaskChange("priority", event.target.value as TaskPriority)}
                  >
                    {priorityOptions.map((priority) => (
                      <option key={priority} value={priority}>
                        {priority.charAt(0).toUpperCase() + priority.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">due_date</label>
                  <input
                    type="date"
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={createTaskState.dueDate}
                    onChange={(event) => handleCreateTaskChange("dueDate", event.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">assignee</label>
                  <input
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={createTaskState.assignee}
                    onChange={(event) => handleCreateTaskChange("assignee", event.target.value)}
                    placeholder="assignee"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleCloseCreateModal}
                  className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500"
                >
                  Add task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default KanbanBoardPage;
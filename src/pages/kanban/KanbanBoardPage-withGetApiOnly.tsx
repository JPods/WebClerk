import { CSSProperties, FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import { KanbanColumn } from "../../components/kanban/KanbanColumn";
import type { BoardData, KanbanColumn as KanbanColumnType, KanbanTask, TaskPriority } from "../../type/kanban";
import type { DragItem, DropResult } from "../../components/kanban/dndTypes";
import { DRAG_TYPE_TASK } from "../../components/kanban/dndTypes";
import clsx from "clsx";
import { Actions } from "../../api/userProfile";
import { createBoardDataFromApi, createEmptyBoardData, extractKanbanItems } from "./kanbanDataMapper";

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

const FALLBACK_COLUMN_ID = "column-uncategorized";

const KanbanBoardPage: React.FC = () => {
  const [board, setBoard] = useState<BoardData>(() => createEmptyBoardData());
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<KanbanTask | null>(null);
  const [createTaskState, setCreateTaskState] = useState<CreateTaskFormState>(() => ({
    title: "",
    description: "",
    columnId: FALLBACK_COLUMN_ID,
    priority: "medium",
    dueDate: "",
    assignee: "",
  }));
  const [editTaskState, setEditTaskState] = useState<CreateTaskFormState>(() => ({
    title: "",
    description: "",
    columnId: FALLBACK_COLUMN_ID,
    priority: "medium",
    dueDate: "",
    assignee: "",
  }));
  const [columnsPerRow, setColumnsPerRow] = useState<number>(5);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const resolveDefaultColumnId = useCallback(
    () => board.columnOrder[0] ?? FALLBACK_COLUMN_ID,
    [board.columnOrder]
  );

  const handleDragEnd = useCallback(
    (item: DragItem, dropResult: DropResult | null) => {
      if (item.type !== DRAG_TYPE_TASK) return;
      setBoard((prev) => handleBoardMove(prev, { item, result: dropResult }));
    },
    []
  );

  const fetchActions = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const response = await Actions();
      if (!response || response.status !== 200) {
        throw new Error("Request failed");
      }

      const items = extractKanbanItems(response);
      if (items.length === 0) {
        setBoard(createEmptyBoardData());
      } else {
        setBoard(createBoardDataFromApi(items));
      }
    } catch (error) {
      console.error("Failed to fetch kanban actions", error);
      setFetchError("Unable to load kanban data. Displaying local state only.");
      setBoard(createEmptyBoardData());
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchActions();
  }, [fetchActions]);

  useEffect(() => {
    if (board.columnOrder.length === 0) {
      setColumnsPerRow(1);
      return;
    }
    setColumnsPerRow((prev) => {
      const clamped = Math.min(Math.max(prev, 1), Math.max(board.columnOrder.length, 1));
      return clamped;
    });
  }, [board.columnOrder]);

  useEffect(() => {
    const firstColumnId = resolveDefaultColumnId();
    setCreateTaskState((prev) => {
      if (board.columns[prev.columnId]) {
        return prev;
      }
      return {
        ...prev,
        columnId: firstColumnId,
      };
    });
  }, [board.columns, resolveDefaultColumnId]);

  const columns = useMemo(() =>
      board.columnOrder
        .map((columnId) => board.columns[columnId])
        .filter((column): column is KanbanColumnType => Boolean(column)),
    [board]
  );

  const columnOptions = useMemo(() => columns.map((column) => ({ id: column.id, title: column.title })), [columns]);
  const columnDensityOptions = useMemo(() => {
    const maxOption = Math.max(5, columns.length || 1);
    const options: number[] = [];
    for (let count = 1; count <= Math.min(8, maxOption); count += 1) {
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
    const firstColumn = resolveDefaultColumnId();
    setCreateTaskState({
      title: "",
      description: "",
      columnId: firstColumn,
      priority: "medium",
      dueDate: "",
      assignee: "",
    });
  }, [resolveDefaultColumnId]);

  const handleOpenCreateModal = () => {
    resetCreateState();
    setIsCreateModalOpen(true);
  };

  const handleCloseCreateModal = () => {
    setIsCreateModalOpen(false);
  };

  const handleOpenEditModal = (task: KanbanTask) => {
    setEditingTask(task);
    
    // Find the column that contains this task
    const taskColumn = Object.values(board.columns).find(column => 
      column.taskIds.includes(task.id)
    );
    
    setEditTaskState({
      title: task.title,
      description: task.description || "",
      columnId: taskColumn?.id || resolveDefaultColumnId(),
      priority: task.priority,
      dueDate: task.dueDate ? new Date(task.dueDate).toISOString().split('T')[0] : "",
      assignee: task.assignee || "",
    });
    setIsEditModalOpen(true);
  };

  const handleCloseEditModal = () => {
    setIsEditModalOpen(false);
    setEditingTask(null);
  };

  const handleCreateTaskChange = (field: keyof CreateTaskFormState, value: string) => {
    setCreateTaskState((prev) => ({ ...prev, [field]: value }));
  };

  const handleEditTaskChange = (field: keyof CreateTaskFormState, value: string) => {
    setEditTaskState((prev) => ({ ...prev, [field]: value }));
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

  const handleEditTaskSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedTitle = editTaskState.title.trim();
    if (!trimmedTitle || !editingTask) {
      return;
    }

    setBoard((prev) => {
      const currentColumn = Object.values(prev.columns).find(column => 
        column.taskIds.includes(editingTask.id)
      );
      const newColumn = prev.columns[editTaskState.columnId];
      
      if (!currentColumn || !newColumn) return prev;

      // Update task data
      const updatedTask: KanbanTask = {
        ...editingTask,
        title: trimmedTitle,
        description: editTaskState.description.trim() || undefined,
        priority: editTaskState.priority,
        assignee: editTaskState.assignee.trim() || undefined,
        dueDate: editTaskState.dueDate || undefined,
      };

      // Handle column change if needed
      let updatedColumns = { ...prev.columns };
      
      if (currentColumn.id !== newColumn.id) {
        // Remove from current column
        updatedColumns[currentColumn.id] = {
          ...currentColumn,
          taskIds: currentColumn.taskIds.filter(id => id !== editingTask.id)
        };
        
        // Add to new column
        updatedColumns[newColumn.id] = {
          ...newColumn,
          taskIds: [...newColumn.taskIds, editingTask.id]
        };
      }

      return {
        ...prev,
        tasks: {
          ...prev.tasks,
          [editingTask.id]: updatedTask,
        },
        columns: updatedColumns
      };
    });

    handleCloseEditModal();
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
          <a href="/kanban-gantt" className="inline-flex items-center gap-2 rounded-lg border border-indigo-300 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-100 dark:border-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400 dark:hover:bg-indigo-500/20">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
              <path d="M9 22V12h6v10" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            View Gantt Chart
          </a>
        </div>
      </div>

      {fetchError && (
        <div className="flex items-center justify-between rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/30 dark:text-rose-200">
          <span>{fetchError}</span>
          <button
            type="button"
            onClick={() => fetchActions()}
            className="rounded-md border border-rose-300 px-3 py-1 text-xs font-semibold text-rose-700 transition hover:bg-rose-100 dark:border-rose-700 dark:text-rose-200 dark:hover:bg-rose-900/50"
          >
            Retry
          </button>
        </div>
      )}

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
        {isLoading ? (
          <div className="flex h-56 items-center justify-center rounded-3xl border border-dashed border-gray-200 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
            Loading kanban data…
          </div>
        ) : columns.length === 0 ? (
          <div className="flex h-56 flex-col items-center justify-center gap-3 rounded-3xl border border-dashed border-gray-200 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
            <span>No tasks found. Create a new card or refresh from the API.</span>
            <button
              type="button"
              onClick={() => fetchActions()}
              className="rounded-lg border border-gray-300 px-3 py-1 text-xs font-semibold text-gray-600 transition hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
            >
              Refresh
            </button>
          </div>
        ) : (
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
                  onTaskClick={handleOpenEditModal}
                  className="h-full"
                />
              );
            })}
          </div>
        )}
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

      {/* Edit Task Modal */}
      {isEditModalOpen && editingTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4 py-6 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-3xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-800 dark:bg-gray-900">
            <div className="mb-4 flex items-start justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Edit task</h2>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Update task details and move between columns.</p>
              </div>
              <button
                onClick={handleCloseEditModal}
                className="rounded-full p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800"
                aria-label="Close"
              >
                <svg className="h-5 w-5" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M6 6l8 8M14 6l-8 8" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>

            <form className="space-y-4" onSubmit={handleEditTaskSubmit}>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Task title</label>
                <input
                  className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                  value={editTaskState.title}
                  onChange={(event) => handleEditTaskChange("title", event.target.value)}
                  placeholder="e.g. Finalize onboarding flow"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Description</label>
                <textarea
                  className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                  rows={3}
                  value={editTaskState.description}
                  onChange={(event) => handleEditTaskChange("description", event.target.value)}
                  placeholder="Context, acceptance criteria, or notes"
                />
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Column</label>
                  <select
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={editTaskState.columnId}
                    onChange={(event) => handleEditTaskChange("columnId", event.target.value)}
                  >
                    {columnOptions.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.title}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Priority</label>
                  <select
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={editTaskState.priority}
                    onChange={(event) => handleEditTaskChange("priority", event.target.value as TaskPriority)}
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
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Due date</label>
                  <input
                    type="date"
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={editTaskState.dueDate}
                    onChange={(event) => handleEditTaskChange("dueDate", event.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Assignee</label>
                  <input
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={editTaskState.assignee}
                    onChange={(event) => handleEditTaskChange("assignee", event.target.value)}
                    placeholder="Who owns this?"
                  />
                </div>
              </div>

              {/* Current Task Info */}
              <div className="rounded-xl bg-gray-50 p-4 dark:bg-gray-800/50">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Current Task Status</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Progress:</span>
                    <span className="ml-1 font-medium text-gray-900 dark:text-white">{editingTask.progress || 0}%</span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Tags:</span>
                    <span className="ml-1 font-medium text-gray-900 dark:text-white">
                      {editingTask.tags?.join(", ") || "None"}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleCloseEditModal}
                  className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500"
                >
                  Update task
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
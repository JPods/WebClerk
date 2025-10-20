import { FormEvent, useCallback, useMemo, useState } from "react";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import { KanbanColumn } from "../../components/kanban/KanbanColumn";
import type { BoardData, KanbanColumn as KanbanColumnType, KanbanTask, TaskPriority } from "../../type/kanban";
import type { DragItem, DropResult } from "../../components/kanban/dndTypes";
import { DRAG_TYPE_TASK } from "../../components/kanban/dndTypes";
import clsx from "clsx";
import { useEffect } from "react";
import {
  createKanbanTask,
  fetchKanbanBoard,
  persistKanbanOrder,
  updateKanbanTaskStatus,
} from "../../api/kanban";
import type {
  CreateKanbanTaskRequest,
  KanbanApiTask,
  LocalizedTextMap,
} from "../../type/kanban";

// Transform API task to board format
const transformApiTaskToBoard = (apiTask: KanbanApiTask): KanbanTask => {
  const englishTitle = apiTask.properties.action.en || Object.values(apiTask.properties.action)[0] || "Untitled";
  const englishDescription = apiTask.properties.description?.en || Object.values(apiTask.properties.description || {})[0] || "";
  
  // Map priority number to string
  const priorityMap: Record<number, TaskPriority> = {
    1: "critical",
    2: "high", 
    3: "medium",
    4: "low"
  };
  
  const priority = priorityMap[apiTask.properties.priority] || "medium";
  const assignee = apiTask.properties.assigned_to?.[0]?.name;
  const dueDate = apiTask.properties.dates?.due?.dt;
  const progress = apiTask.properties.difficulty || 0;
  
  // Extract language tags (excluding English)
  const languageTags = apiTask.properties.lang.filter(lang => lang !== "en");
  const childTags = apiTask.properties.children?.map(child => child.name) || [];
  
  return {
    id: apiTask.id,
    title: englishTitle,
    description: englishDescription,
    priority,
    assignee,
    dueDate,
    tags: [...languageTags, ...childTags],
    progress,
    // Store additional API data for later use
    backendId: apiTask.id,
    titleTranslations: apiTask.properties.action,
    descriptionTranslations: apiTask.properties.description,
    remarks: apiTask.properties.remarks,
    priorityValue: apiTask.properties.priority,
    difficulty: apiTask.properties.difficulty,
    linkage: apiTask.properties.linkage,
    assignedTo: apiTask.properties.assigned_to,
    dates: apiTask.properties.dates,
    children: apiTask.properties.children,
    languageCodes: apiTask.properties.lang,
    status: apiTask.properties.status,
  };
};

// Sample API task based on provided structure
const sampleApiTask: KanbanApiTask = {
  id: "task-sample-001",
  parent: {
    id: "YOUR_DATABASE_ID", 
    zzz: "parent_action_id" 
  },
  properties: {
    lang: ["en", "ar", "bn", "es"],
    action: {
      en: "My New Page Title",
      ar: "عنوان صفحتي الجديدة",
      bn: "আমার নতুন পৃষ্ঠা শিরোনাম",
      es: "Mi Nuevo Título de Página"
    },
    status: "InProgress", 
    priority: 1,
    difficulty: 50, 
    dates: {
      created: { dt: "2023-10-10T12:00:00Z", who: { id: "USER_ID_1", name: "name" }},
      updated: { dt: "2023-10-10T12:00:00Z", who: { id: "USER_ID_1", name: "name" }},
      expected: { dt: "2023-11-15T12:00:00Z", who: { id: "USER_ID_1", name: "name" }},
      due: { dt: "2023-12-31T23:59:59Z", who: { id: "USER_ID_1", name: "name" }},
      completed: { dt: "2023-12-31T23:59:59Z", who: { id: "USER_ID_1", name: "name" }},
      start: { dt: "2023-12-31T23:59:59Z", who: { id: "USER_ID_1", name: "name" }},
      end: { dt: "2023-12-31T23:59:59Z", who: { id: "USER_ID_1", name: "name" }}
    },
    assigned_to: [
      { id: "USER_ID_1", name: "name" }
    ],
    linkage: 25,
    description: {
      en: "This is a detailed description of the new page.",
      ar: "هذا وصف تفصيلي للصفحة الجديدة.",
      bn: "এটি নতুন পৃষ্ঠার একটি বিস্তারিত বিবরণ।",
      es: "Esta es una descripción detallada de la nueva página."
    },
    children: [
      { id: 11, name: "other name" },
      { id: 12, name: "another name" },
      { id: 13, name: "third name" }
    ],
    remarks: ""
  }
};

// Transform API tasks to board structure
const transformApiTasksToBoard = (apiTasks: KanbanApiTask[]): BoardData => {
  const tasks: Record<string, KanbanTask> = {};
  const statusGroups: Record<string, string[]> = {};
  
  apiTasks.forEach(apiTask => {
    const task = transformApiTaskToBoard(apiTask);
    tasks[task.id] = task;
    
    const status = apiTask.properties.status || "Backlog";
    if (!statusGroups[status]) {
      statusGroups[status] = [];
    }
    statusGroups[status].push(task.id);
  });
  
  // Define column structure based on status
  const statusOrder = ["Backlog", "Planning", "InProgress", "Review", "Done"];
  const columns: Record<string, KanbanColumnType> = {};
  const columnOrder: string[] = [];
  
  statusOrder.forEach(status => {
    const columnId = `column-${status.toLowerCase()}`;
    const title = status === "InProgress" ? "In Progress" : status;
    
    columns[columnId] = {
      id: columnId,
      title,
      taskIds: statusGroups[status] || [],
    };
    columnOrder.push(columnId);
  });
  
  return {
    tasks,
    columns,
    columnOrder,
  };
};

// Initialize seed board from sample API task
const seedBoard: BoardData = transformApiTasksToBoard([sampleApiTask]);

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
  action: LocalizedTextMap;
  description: LocalizedTextMap;
  columnId: string;
  priority: TaskPriority;
  priorityValue: number;
  difficulty: number;
  dueDate: string;
  assignee: string;
  remarks: string;
  linkage: number;
  languageCodes: string[];
};

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
  const [, setApiTasks] = useState<KanbanApiTask[]>([sampleApiTask]);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newLanguageCode, setNewLanguageCode] = useState("");
  const defaultColumnId = seedBoard.columnOrder[0] ?? "column-backlog";
  
  const [createTaskState, setCreateTaskState] = useState<CreateTaskFormState>({
    action: { en: "" },
    description: { en: "" },
    columnId: defaultColumnId,
    priority: "medium",
    priorityValue: 2,
    difficulty: 50,
    dueDate: "",
    assignee: "",
    remarks: "",
    linkage: 0,
    languageCodes: ["en"],
  });

  // Load kanban data from API
  const loadKanbanData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchKanbanBoard();
      if (response && response.length > 0) {
        setApiTasks(response);
        const boardData = transformApiTasksToBoard(response);
        setBoard(boardData);
      }
    } catch (err) {
      console.error('Failed to load kanban data:', err);
      setError('Failed to load kanban data. Using sample data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadKanbanData();
  }, [loadKanbanData]);

  const handleDragEnd = useCallback(
    async (item: DragItem, dropResult: DropResult | null) => {
      if (item.type !== DRAG_TYPE_TASK || !dropResult) return;
      
      // Optimistically update the UI
      const previousBoard = board;
      const newBoard = handleBoardMove(board, { item, result: dropResult });
      setBoard(newBoard);
      
      // Determine new status from column ID
      const newStatus = dropResult.columnId.replace('column-', '');
      const statusMap: Record<string, string> = {
        'backlog': 'Backlog',
        'planning': 'Planning', 
        'in-progress': 'InProgress',
        'review': 'Review',
        'done': 'Done'
      };
      const mappedStatus = statusMap[newStatus] || 'Backlog';
      
      try {
        // Call API to update task status
        await updateKanbanTaskStatus(item.taskId, {
          status: mappedStatus,
          columnId: dropResult.columnId,
        });
        
        // Update API tasks state
        setApiTasks(prev => prev.map(task => 
          task.id === item.taskId 
            ? { ...task, properties: { ...task.properties, status: mappedStatus }}
            : task
        ));
        
        // Persist column order
        const columnOrder = newBoard.columnOrder.map(columnId => ({
          columnId,
          taskIds: newBoard.columns[columnId]?.taskIds || [],
        }));
        await persistKanbanOrder(columnOrder);
        
      } catch (err) {
        console.error('Failed to update task status:', err);
        // Revert optimistic update on error
        setBoard(previousBoard);
        setError('Failed to update task status. Please try again.');
      }
    },
    [board]
  );

  const columns = useMemo(
    () =>
      board.columnOrder
        .map((columnId) => board.columns[columnId])
        .filter((column): column is KanbanColumnType => Boolean(column)),
    [board]
  );

  const columnOptions = useMemo(() => columns.map((column) => ({ id: column.id, title: column.title })), [columns]);

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
      action: { en: "" },
      description: { en: "" },
      columnId: firstColumn,
      priority: "medium",
      priorityValue: 2,
      difficulty: 50,
      dueDate: "",
      assignee: "",
      remarks: "",
      linkage: 0,
      languageCodes: ["en"],
    });
    setNewLanguageCode("");
  }, [board.columnOrder, defaultColumnId]);

  const handleOpenCreateModal = () => {
    resetCreateState();
    setIsCreateModalOpen(true);
  };

  const handleCloseCreateModal = () => {
    setIsCreateModalOpen(false);
  };

  const handleCreateTaskChange = (field: keyof CreateTaskFormState, value: string | number | LocalizedTextMap | string[]) => {
    setCreateTaskState((prev) => ({ ...prev, [field]: value }));
  };

  const handleLocalizedTextChange = (field: 'action' | 'description', language: string, value: string) => {
    setCreateTaskState((prev) => ({
      ...prev,
      [field]: {
        ...prev[field],
        [language]: value,
      },
    }));
  };

  const addLanguage = () => {
    const trimmedCode = newLanguageCode.trim().toLowerCase();
    if (!trimmedCode || createTaskState.languageCodes.includes(trimmedCode)) return;
    
    setCreateTaskState((prev) => ({
      ...prev,
      languageCodes: [...prev.languageCodes, trimmedCode],
      action: { ...prev.action, [trimmedCode]: '' },
      description: { ...prev.description, [trimmedCode]: '' },
    }));
    setNewLanguageCode('');
  };

  const removeLanguage = (languageCode: string) => {
    if (languageCode === 'en') return; // Don't allow removing English
    
    setCreateTaskState((prev) => {
      const newLanguageCodes = prev.languageCodes.filter(code => code !== languageCode);
      const { [languageCode]: removedAction, ...restAction } = prev.action;
      const { [languageCode]: removedDesc, ...restDescription } = prev.description;
      
      return {
        ...prev,
        languageCodes: newLanguageCodes,
        action: restAction,
        description: restDescription,
      };
    });
  };

  const handleCreateTaskSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    
    // Validate required fields
    const englishTitle = createTaskState.action.en?.trim();
    if (!englishTitle) {
      setError('English title is required');
      return;
    }

    // Prepare API payload
    const statusMap: Record<string, string> = {
      'column-backlog': 'Backlog',
      'column-planning': 'Planning',
      'column-in-progress': 'InProgress', 
      'column-review': 'Review',
      'column-done': 'Done'
    };
    
    const apiPayload: CreateKanbanTaskRequest = {
      parentId: sampleApiTask.parent.id,
      lang: createTaskState.languageCodes,
      action: createTaskState.action,
      description: createTaskState.description,
      status: statusMap[createTaskState.columnId] || 'Backlog',
      priority: createTaskState.priorityValue,
      difficulty: createTaskState.difficulty,
      assigned_to: createTaskState.assignee.trim() ? [{ id: createTaskId(), name: createTaskState.assignee.trim() }] : [],
      linkage: createTaskState.linkage,
      remarks: createTaskState.remarks.trim() || undefined,
      dates: createTaskState.dueDate ? {
        due: { 
          dt: new Date(createTaskState.dueDate).toISOString(), 
          who: { id: "USER_ID_1", name: "System" }
        }
      } : undefined,
    };

    try {
      // Create task via API
      const newApiTask = await createKanbanTask(apiPayload);
      
      // Update local state
      setApiTasks(prev => [...prev, newApiTask]);
      const newBoardTask = transformApiTaskToBoard(newApiTask);
      
      setBoard((prev) => {
        const column = prev.columns[createTaskState.columnId];
        if (!column) return prev;

        return {
          ...prev,
          tasks: {
            ...prev.tasks,
            [newBoardTask.id]: newBoardTask,
          },
          columns: {
            ...prev.columns,
            [column.id]: {
              ...column,
              taskIds: [...column.taskIds, newBoardTask.id],
            },
          },
        };
      });

      handleCloseCreateModal();
      setError(null);
    } catch (err) {
      console.error('Failed to create task:', err);
      setError('Failed to create task. Please try again.');
    }
  };

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
        <div className="flex flex-wrap gap-3">
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

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-500/40 dark:bg-red-500/10 dark:text-red-100">
          <div className="flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              className="ml-4 text-red-500 hover:text-red-700"
            >
              ×
            </button>
          </div>
        </div>
      )}

      <DndProvider backend={HTML5Backend}>
        {loading ? (
          <div className="grid gap-5 pb-6 [grid-template-columns:repeat(auto-fit,minmax(280px,1fr))]">
            {[1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                className="h-96 animate-pulse rounded-3xl border border-gray-200 bg-gray-100 dark:border-gray-700 dark:bg-gray-800"
              />
            ))}
          </div>
        ) : (
          <div className="grid gap-5 pb-6 [grid-template-columns:repeat(auto-fit,minmax(280px,1fr))]">
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
        )}
      </DndProvider>

      {isCreateModalOpen && (
        <div className="fixed inset-0 z-100 flex items-center justify-center bg-black/30 px-4 py-6 backdrop-blur-sm">
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
              {error && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-500/40 dark:bg-red-500/10 dark:text-red-100">
                  {error}
                </div>
              )}

              {/* Multi-language fields */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Multi-language content</h3>
                  <div className="flex items-center gap-2">
                    <input
                      className="w-20 rounded-md border border-gray-300 px-2 py-1 text-xs dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                      placeholder="Lang"
                      value={newLanguageCode}
                      onChange={(e) => setNewLanguageCode(e.target.value)}
                    />
                    <button
                      type="button"
                      onClick={addLanguage}
                      className="rounded-md bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                    >
                      Add
                    </button>
                  </div>
                </div>

                {createTaskState.languageCodes.map((langCode) => (
                  <div key={langCode} className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">{langCode}</span>
                      {langCode !== 'en' && (
                        <button
                          type="button"
                          onClick={() => removeLanguage(langCode)}
                          className="text-xs text-red-500 hover:text-red-700"
                        >
                          Remove
                        </button>
                      )}
                    </div>
                    <div className="space-y-2">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400">Title</label>
                        <input
                          className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                          value={createTaskState.action[langCode] || ''}
                          onChange={(event) => handleLocalizedTextChange('action', langCode, event.target.value)}
                          placeholder={`Title in ${langCode}`}
                          required={langCode === 'en'}
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400">Description</label>
                        <textarea
                          className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                          rows={2}
                          value={createTaskState.description[langCode] || ''}
                          onChange={(event) => handleLocalizedTextChange('description', langCode, event.target.value)}
                          placeholder={`Description in ${langCode}`}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Column</label>
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
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Priority</label>
                  <select
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={createTaskState.priorityValue}
                    onChange={(event) => {
                      const value = parseInt(event.target.value);
                      const priorityMap: Record<number, TaskPriority> = { 1: "critical", 2: "high", 3: "medium", 4: "low" };
                      handleCreateTaskChange("priorityValue", value);
                      handleCreateTaskChange("priority", priorityMap[value] || "medium");
                    }}
                  >
                    <option value={1}>Critical (1)</option>
                    <option value={2}>High (2)</option>
                    <option value={3}>Medium (3)</option>
                    <option value={4}>Low (4)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Difficulty (0-100)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={createTaskState.difficulty}
                    onChange={(event) => handleCreateTaskChange("difficulty", parseInt(event.target.value))}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Linkage</label>
                  <input
                    type="number"
                    min="0"
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={createTaskState.linkage}
                    onChange={(event) => handleCreateTaskChange("linkage", parseInt(event.target.value))}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Due date</label>
                  <input
                    type="date"
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={createTaskState.dueDate}
                    onChange={(event) => handleCreateTaskChange("dueDate", event.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Assignee</label>
                  <input
                    className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                    value={createTaskState.assignee}
                    onChange={(event) => handleCreateTaskChange("assignee", event.target.value)}
                    placeholder="Who owns this?"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Remarks</label>
                <textarea
                  className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                  rows={3}
                  value={createTaskState.remarks}
                  onChange={(event) => handleCreateTaskChange("remarks", event.target.value)}
                  placeholder="Additional notes, blockers, or context"
                />
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

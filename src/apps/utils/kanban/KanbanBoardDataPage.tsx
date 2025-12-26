import { CSSProperties, useCallback, useMemo, useState } from "react";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import PageBreadcrumb from "../../../components/common/PageBreadCrumb";
import { KanbanColumn } from "../../../components/kanban/KanbanColumn";
import type {
  BoardData,
  KanbanColumn as KanbanColumnType,
  KanbanTask,
  TaskPriority,
} from "../../../type/kanban";
import type { DragItem, DropResult } from "../../../components/kanban/dndTypes";
import { DRAG_TYPE_TASK } from "../../../components/kanban/dndTypes";
import { ApiKanbanItem, createBoardDataFromApi } from "./kanbanDataMapper";

const rawKanbanData: ApiKanbanItem[] = [
  {
    id: "f9f2c38c-994b-4bed-9d9f-7e613864c143",
    uuid: null,
    ida: "",
    dt_modified: 0,
    version: 1,
    is_active: true,
    security_level: 0,
    is_deleted: false,
    is_archived: false,
    metadata: {
      flow: {},
      access: {
        edit: [],
        view: [],
      },
      health: {
        rating: 0,
        accuracy: 0,
        freshness: 0,
        consistency: 0,
        completeness: 0,
      },
      source: {},
      history: {
        synced: {
          dt: 0,
          contact_id: 0,
        },
        created: {
          dt: 1761660741519,
          contact_id: 0,
        },
        accessed: {
          dt: 1761660741519,
          contact_id: 0,
        },
        modified: {
          dt: 1761660741519,
          contact_id: 0,
        },
        verified: {
          dt: 0,
          contact_id: 0,
        },
      },
      publish: "",
      version: "1.0",
      priority: "",
      security: "",
      resources: {
        required: {},
        allocated: {},
      },
      undefined: {},
    },
    refs: {
      tags: [],
      links: {
        items: [],
        contacts: [],
      },
      keywords: [],
      categories: [],
      depends_on: {},
      related_ids: [],
    },
    prefs: {
      userdefined: {},
    },
    actions: {},
    comments: {
      notes: [],
      public: "",
      partner: "",
      process: "",
    },
    health_rating: 0,
    action_en: "Profile support by type of customer",
    action_ar: null,
    action_bn: null,
    action_es: null,
    description_en: null,
    description_ar: null,
    description_bn: null,
    description_es: null,
    languages: ["en"],
    kanban_column: "Backlog",
    priority: 1,
    difficulty: 10,
    status: "On hold",
    dt_created: "2025-10-28T14:12:21.519752Z",
    dt_updated: "2025-10-28T14:12:25.190219Z",
    dt_expected: null,
    dt_due: null,
    dt_completed: null,
    dt_start: null,
    dt_end: null,
    created_by: null,
    updated_by: null,
    expected_by: null,
    due_by: null,
    completed_by: null,
    start_by: null,
    end_by: null,
    assigned_to: [],
    linkage: 0,
    kanban_meta: null,
    parent: null,
  },
  {
    id: "f85e73b9-285d-4fdd-84fc-56b09c11fca7",
    uuid: null,
    ida: "",
    dt_modified: 0,
    version: 1,
    is_active: true,
    security_level: 0,
    is_deleted: false,
    is_archived: false,
    metadata: {
      flow: {},
      access: {
        edit: [],
        view: [],
      },
      health: {
        rating: 0,
        accuracy: 0,
        freshness: 0,
        consistency: 0,
        completeness: 0,
      },
      source: {},
      history: {
        synced: {
          dt: 0,
          contact_id: 0,
        },
        created: {
          dt: 1761660741521,
          contact_id: 0,
        },
        accessed: {
          dt: 1761660741521,
          contact_id: 0,
        },
        modified: {
          dt: 1761660741521,
          contact_id: 0,
        },
        verified: {
          dt: 0,
          contact_id: 0,
        },
      },
      publish: "",
      version: "1.0",
      priority: "",
      security: "",
      resources: {
        required: {},
        allocated: {},
      },
      undefined: {},
    },
    refs: {
      tags: [],
      links: {
        items: [],
        contacts: [],
      },
      keywords: [],
      categories: [],
      depends_on: {},
      related_ids: [],
    },
    prefs: {
      userdefined: {},
    },
    actions: {},
    comments: {
      notes: [],
      public: "",
      partner: "",
      process: "",
    },
    health_rating: 0,
    action_en: "calender react",
    action_ar: null,
    action_bn: null,
    action_es: null,
    description_en: null,
    description_ar: null,
    description_bn: null,
    description_es: null,
    languages: ["en"],
    kanban_column: "InProcess",
    priority: 1,
    difficulty: 10,
    status: "In progress",
    dt_created: "2025-10-28T14:12:21.521577Z",
    dt_updated: "2025-10-28T14:12:26.955174Z",
    dt_expected: null,
    dt_due: null,
    dt_completed: null,
    dt_start: null,
    dt_end: null,
    created_by: null,
    updated_by: null,
    expected_by: null,
    due_by: null,
    completed_by: null,
    start_by: null,
    end_by: null,
    assigned_to: [
      {
        name: "techno riju",
      },
    ],
    linkage: 0,
    kanban_meta: null,
    parent: null,
  },
];

const initialBoardState = createBoardDataFromApi(rawKanbanData);

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

const KanbanBoardDataPage: React.FC = () => {
  const [board, setBoard] = useState<BoardData>(() => initialBoardState);
  const [columnsPerRow, setColumnsPerRow] = useState<number>(() =>
    Math.min(4, Math.max(1, initialBoardState.columnOrder.length || 1))
  );

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

  const columnDensityOptions = useMemo(() => {
    const maxOption = Math.max(4, columns.length);
    const options: number[] = [];
    for (let count = 1; count <= Math.min(6, maxOption); count += 1) {
      options.push(count);
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

  const statusSummary = useMemo(() => {
    const summary: Record<string, number> = {};
    Object.values(board.tasks).forEach((task) => {
      const statusKey = task.status || "Unspecified";
      summary[statusKey] = (summary[statusKey] ?? 0) + 1;
    });
    return summary;
  }, [board.tasks]);

  const languageSummary = useMemo(() => {
    const languages = new Set<string>();
    Object.values(board.tasks).forEach((task) => {
      task.languageCodes?.forEach((code) => languages.add(code));
    });
    return Array.from(languages);
  }, [board.tasks]);

  const totalTasks = useMemo(() => Object.keys(board.tasks).length, [board.tasks]);

  const gridStyle = useMemo<CSSProperties>(
    () => ({
      gridTemplateColumns: `repeat(${Math.max(1, columnsPerRow)}, minmax(0, 1fr))`,
    }),
    [columnsPerRow]
  );

  return (
    <div className="space-y-6">
      <PageBreadcrumb pageTitle="Kanban Board (API Dataset)" />

      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Synced kanban overview</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Tasks below originate from the provided dataset and stay fully draggable inside this workspace snapshot.
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
          <div className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200">
            <span className="text-xs uppercase tracking-wide text-gray-400 dark:text-gray-500">Records</span>
            <div className="text-lg font-semibold text-gray-900 dark:text-white">{totalTasks}</div>
          </div>
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
            <span
              className={`mt-4 inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
                priorityPalette[priority]
              }`}
            >
              Priority lane
            </span>
          </div>
        ))}
        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">Statuses</p>
          <div className="mt-3 space-y-2 text-sm">
            {Object.entries(statusSummary).map(([status, count]) => (
              <div key={status} className="flex items-center justify-between text-gray-600 dark:text-gray-300">
                <span>{status}</span>
                <span className="text-xs font-semibold text-gray-400 dark:text-gray-500">{count} task{count === 1 ? "" : "s"}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">Languages</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {languageSummary.length ? (
              languageSummary.map((code) => (
                <span
                  key={code}
                  className="inline-flex items-center rounded-full bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-600 dark:bg-indigo-500/20 dark:text-indigo-300"
                >
                  {code.toUpperCase()}
                </span>
              ))
            ) : (
              <span className="text-sm text-gray-400 dark:text-gray-500">No language codes detected</span>
            )}
          </div>
        </div>
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
    </div>
  );
};

export default KanbanBoardDataPage;

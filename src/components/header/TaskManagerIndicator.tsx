import React, { useMemo, useState } from "react";
import clsx from "clsx";
import { useRequestQueue } from "../../context/RequestQueueContext";
import { useSaveQueue } from "../../context/SaveQueueContext";

const statusColor = (status: string) => {
  if (status === "running" || status === "queued") return "bg-indigo-500";
  if (status === "error") return "bg-rose-500";
  if (status === "canceled") return "bg-amber-500";
  return "bg-gray-400";
};

const Chip: React.FC<{ label: string; count: number }> = ({ label, count }) => (
  <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700 dark:border-slate-800 dark:bg-slate-900/40 dark:text-slate-100">
    <span className="h-1.5 w-1.5 rounded-full bg-current mr-2" />
    {label}
    <span className="rounded-full bg-white/70 px-1 text-[11px] text-slate-700 dark:bg-black/30 dark:text-slate-100">{count}</span>
  </span>
);

export const TaskManagerIndicator: React.FC = () => {
  const { active: activeRequests, cancel: cancelRequest } = useRequestQueue();
  const { queued, active: activeSave, cancel: cancelSave } = useSaveQueue();
  const [open, setOpen] = useState(false);

  type TaskItem = { id: string; label: string; status: string; method: string; onCancel?: () => void };

  const items = useMemo<TaskItem[]>(() => {
    const mappedRequests: TaskItem[] = activeRequests.map((req) => ({
      id: req.id,
      label: req.label,
      status: req.status,
      method: (req.method || "GET").toUpperCase(),
      onCancel: () => cancelRequest(req.id),
    }));

    const mappedSaves: TaskItem[] = [];
    if (activeSave) {
      mappedSaves.push({
        id: activeSave.id,
        label: activeSave.label || "Save",
        status: activeSave.status,
        method: "POST",
        onCancel: () => cancelSave(activeSave.id),
      });
    }

    queued.forEach((item) => {
      mappedSaves.push({
        id: item.id,
        label: item.label || "Save",
        status: item.status,
        method: "POST",
        onCancel: () => cancelSave(item.id),
      });
    });

    return [...mappedRequests, ...mappedSaves];
  }, [activeRequests, activeSave, queued, cancelRequest, cancelSave]);

  const total = items.length;
  const methodCounts = useMemo(() => {
    const counts: Record<string, number> = { GET: 0, POST: 0, DELETE: 0, OTHER: 0 };
    items.forEach((item) => {
      const method = (item.method || "OTHER").toUpperCase();
      if (method === "GET" || method === "POST" || method === "DELETE") {
        counts[method] += 1;
      } else {
        counts.OTHER += 1;
      }
    });
    return counts;
  }, [items]);

  return (
    <div className="relative">
      <button
        className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100"
        type="button"
        onClick={() => setOpen((v) => !v)}
      >
        <span className={clsx("h-2.5 w-2.5 rounded-full", total > 0 ? "bg-indigo-500" : "bg-gray-400")} />
        {total > 0 ? `${total} in progress` : "No pending operations"}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-96 rounded-xl border border-gray-200 bg-white p-3 text-xs shadow-lg dark:border-gray-700 dark:bg-gray-900">
          <div className="mb-3 flex flex-col items-start justify-between gap-2">
            <p className="text-[11px] font-semibold text-gray-700 dark:text-gray-200">Background Operations</p>
            <div className="flex items-center gap-2">
              <Chip label="GET" count={methodCounts.GET} />
              <Chip label="POST" count={methodCounts.POST} />
              <Chip label="DELETE" count={methodCounts.DELETE} />
              {methodCounts.OTHER > 0 && <Chip label="OTHER" count={methodCounts.OTHER} />}
            </div>
          </div>
          {items.length === 0 ? (
            <div className="rounded-md border border-dashed border-gray-200 p-3 text-[11px] text-gray-500 dark:border-gray-700 dark:text-gray-400">
              All caught up
            </div>
          ) : (
            <div className="max-h-72 space-y-2 overflow-auto">
              {items.map((item) => (
                <div
                  key={item.id}
                  className="flex items-start gap-3 rounded-lg border border-gray-100 p-2.5 dark:border-gray-800"
                >
                  <span className={clsx("mt-1 h-2.5 w-2.5 rounded-full", statusColor(item.status))} />
                  <div className="flex-1">
                    <p className="text-[11px] font-semibold text-gray-800 dark:text-gray-100 line-clamp-2">
                      {item.label}
                    </p>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400">
                      {item.method} · {item.status}
                    </p>
                  </div>
                  {(item.status === "running" || item.status === "queued") && item.onCancel && (
                    <button
                      onClick={item.onCancel}
                      className="rounded-md border border-rose-200 px-2 py-1 text-[11px] font-semibold text-rose-600 transition hover:bg-rose-50 dark:border-rose-700 dark:text-rose-300 dark:hover:bg-rose-900/40"
                    >
                      Cancel
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TaskManagerIndicator;

/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import React, { useMemo, useState } from "react";
import { useSaveQueue } from "../../context/SaveQueueContext";
import clsx from "clsx";

const statusColor = (status: string) => {
  if (status === "running") return "bg-indigo-500";
  if (status === "queued") return "bg-amber-500";
  if (status === "error") return "bg-rose-500";
  return "bg-gray-400";
};

export const SaveQueueIndicator: React.FC = () => {
  const { pendingCount, queued, active, cancel } = useSaveQueue();
  const [open, setOpen] = useState(false);

  const items = useMemo(() => {
    const list = [];
    if (active) list.push(active);
    return list.concat(queued);
  }, [active, queued]);

  if (pendingCount === 0) {
    return (
      <div
        className="relative"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
      >
        <div className="inline-flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-xs font-medium text-gray-500 dark:border-gray-700 dark:text-gray-400">
          <span className="h-2 w-2 rounded-full bg-gray-300" />
          No saves
        </div>
        {open && (
          <div className="absolute right-0 mt-2 w-72 rounded-xl border border-gray-200 bg-white p-3 text-xs shadow-lg dark:border-gray-700 dark:bg-gray-900">
            All caught up
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      className="relative"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-xs font-semibold text-indigo-700 shadow-sm transition hover:bg-indigo-100 dark:border-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-200"
        type="button"
      >
        <span className={clsx("h-2.5 w-2.5 rounded-full", statusColor(active ? active.status : "queued"))} />
        {pendingCount} save{pendingCount === 1 ? "" : "s"}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-80 rounded-xl border border-gray-200 bg-white p-3 text-xs shadow-lg dark:border-gray-700 dark:bg-gray-900">
          <p className="mb-2 text-[11px] font-semibold text-gray-600 dark:text-gray-200">Pending saves</p>
          <div className="max-h-64 space-y-2 overflow-auto">
            {items.map((item) => (
              <div
                key={item.id}
                className="flex items-start gap-2 rounded-lg border border-gray-100 p-2 dark:border-gray-800"
              >
                <span className={clsx("mt-1 h-2 w-2 rounded-full", statusColor(item.status))} />
                <div className="flex-1">
                  <p className="text-[11px] font-semibold text-gray-800 dark:text-gray-100 line-clamp-2">
                    {item.label || "Save"}
                  </p>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400">{item.status}</p>
                </div>
                {(item.status === "queued" || item.status === "running") && (
                  <button
                    onClick={() => cancel(item.id)}
                    className="rounded-md border border-rose-200 px-2 py-1 text-[11px] font-semibold text-rose-600 transition hover:bg-rose-50 dark:border-rose-700 dark:text-rose-300 dark:hover:bg-rose-900/40"
                  >
                    Cancel
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default SaveQueueIndicator;

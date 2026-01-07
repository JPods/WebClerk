import { useMemo, useState } from "react";
import { useAdminWorkspace } from "../AdminWorkspaceProvider";

export const AppTableColumn = () => {
  const {
    apps,
    selectedAppId,
    selectedTableId,
    setSelectedAppId,
    setSelectedTableId,
    list,
  } = useAdminWorkspace();

  const [tableFilter, setTableFilter] = useState("");

  const filteredApps = useMemo(() => {
    if (!tableFilter.trim()) {
      return apps;
    }
    const needle = tableFilter.trim().toLowerCase();
    return apps
      .map((app) => {
        const matchingTables = app.tables.filter((table) =>
          table.label.toLowerCase().includes(needle) || table.id.toLowerCase().includes(needle)
        );
        if (matchingTables.length === 0) {
          return null;
        }
        return { ...app, tables: matchingTables };
      })
      .filter((app): app is typeof apps[number] => Boolean(app));
  }, [apps, tableFilter]);

  return (
    <aside className="flex h-full w-full flex-col border-r border-slate-200 bg-slate-100 dark:border-slate-800 dark:bg-slate-950">
      <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-800">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Applications
        </p>
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Data sources</h2>
        <div className="mt-3">
          <label className="sr-only" htmlFor="table-search">
            Search tables
          </label>
          <div className="relative">
            <input
              id="table-search"
              type="search"
              placeholder="Filter tables"
              value={tableFilter}
              onChange={(event) => setTableFilter(event.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 pr-8 py-2 text-sm text-slate-900 shadow-sm transition focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
            />
            {tableFilter && (
              <button
                type="button"
                onClick={() => setTableFilter("")}
                className="absolute inset-y-0 right-3 flex items-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                aria-label="Clear table filter"
              >
                X
              </button>
            )}
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-2 py-3">
        {filteredApps.map((app) => (
          <div key={app.id} className="mb-4 rounded-md border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <button
              type="button"
              onClick={() => setSelectedAppId(app.id)}
              className={`flex w-full items-center justify-between gap-3 border-b border-slate-200 px-4 py-3 text-left transition dark:border-slate-800 ${
                selectedAppId === app.id ? "bg-slate-100 dark:bg-slate-800/70" : "hover:bg-slate-50 dark:hover:bg-slate-800/30"
              }`}
            >
              <div>
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{app.label}</p>
                {app.description && (
                  <p className="text-xs text-slate-500 dark:text-slate-400">{app.description}</p>
                )}
              </div>
              <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {app.tables.length}
              </span>
            </button>
            <ul className="divide-y divide-slate-200 dark:divide-slate-800">
              {app.tables.map((table) => {
                const isSelected = selectedAppId === app.id && selectedTableId === table.id;
                return (
                  <li key={table.id}>
                    <button
                      type="button"
                      onClick={() => {
                        if (selectedAppId !== app.id) {
                          setSelectedAppId(app.id);
                        }
                        setSelectedTableId(table.id);
                      }}
                      className={`flex w-full items-center justify-between gap-3 px-4 py-2 text-left text-sm transition ${
                        isSelected
                          ? "bg-sky-50 font-semibold text-sky-700 ring-1 ring-inset ring-sky-200 dark:bg-sky-900/40 dark:text-sky-200 dark:ring-sky-800"
                          : "text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800/30"
                      }`}
                    >
                      <span>{table.label}</span>
                      {isSelected && (
                        <span className="text-xs font-medium text-slate-500 dark:text-slate-300">
                          {list.total.toLocaleString()} records
                        </span>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
        {!filteredApps.length && (
          <div className="rounded-md border border-dashed border-slate-300 px-4 py-6 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
            No tables match your search.
          </div>
        )}
      </div>
    </aside>
  );
};

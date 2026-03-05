import React, { useMemo } from "react";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

// Dev mode: return raw field names for alignment
const formatLabel = (value: string) => value;

const isObjectValue = (value: unknown) =>
  typeof value === "object" && value !== null;

const renderScalarValue = (value: unknown) => {
  if (value === null || value === undefined || value === "") {
    return <span className="text-slate-400">—</span>;
  }
  return <span className="text-slate-800 dark:text-slate-200">{String(value)}</span>;
};

export function CustomerDataPanel({ data, showScalars = true, grouped = false, onSelectCategory, }: { data: any; showScalars?: boolean; grouped?: boolean; onSelectCategory?: (tabId: string) => void }) {
  const entries = useMemo(() => Object.entries(data || {}), [data]);
  const [scalarEntries, objectEntries] = useMemo(() => {
    const scalars: Array<[string, unknown]> = [];
    const objects: Array<[string, unknown]> = [];
    entries.forEach(([key, value]) => {
      if (Array.isArray(value) || isObjectValue(value)) {
        objects.push([key, value]);
      } else {
        scalars.push([key, value]);
      }
    });
    return [scalars, objects];
  }, [entries]);

  if (!entries.length) {
    return (
      <section className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900/40">
        No customer data available.
      </section>
    );
  }
  if (grouped) {
    const GROUPS: Array<{ id: string; label: string; keys: string[] }> = [
      { id: "communication", label: "Communication", keys: ["contacts", "addresses", "domains", "phones", "emails"] },
      { id: "documents", label: "Documents", keys: ["docs"] },
      { id: "financial", label: "Financial", keys: ["financial"] },
      { id: "relations", label: "Relations", keys: ["relations"] },
      { id: "connections", label: "Connections", keys: ["connections"] },
      { id: "data", label: "Data", keys: ["data"] },
      { id: "metrics", label: "Metrics", keys: ["metrics"] },
      { id: "gl_accounts", label: "GL Accounts", keys: ["gl_accounts"] },
    ];

    const getCountForKey = (val: any) => {
      if (val === undefined || val === null) return 0;
      if (typeof val === "string") {
        try {
          const parsed = JSON.parse(val);
          if (Array.isArray(parsed)) return parsed.length;
          if (typeof parsed === "object") return Object.keys(parsed).length;
          return 1;
        } catch {
          return 1;
        }
      }
      if (Array.isArray(val)) return val.length;
      if (typeof val === "object") return Object.keys(val).length;
      return 1;
    };

    return (
      <section className="grid gap-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <h3 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Apps</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {GROUPS.map((g) => {
              const total = g.keys.reduce((sum, k) => sum + getCountForKey((data || {})[k]), 0);
              return (
                <button
                  key={g.id}
                  type="button"
                  onClick={() => onSelectCategory && onSelectCategory(g.id)}
                  className="flex items-center justify-between gap-3 p-3 rounded-lg border border-slate-100 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-950"
                >
                  <div className="text-sm font-medium text-slate-700 dark:text-slate-200">{g.label}</div>
                  <div className="text-xs text-slate-400">{total}</div>
                </button>
              );
            })}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="grid gap-4">
      {showScalars && (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Scalar Fields</h3>
            <span className="text-xs text-slate-400">{scalarEntries.length}</span>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {scalarEntries.map(([key, value]) => (
              <div key={key} className="rounded-xl border border-slate-100 bg-slate-50 p-3 shadow-sm dark:border-slate-800 dark:bg-slate-950">
                <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{formatLabel(key)}</div>
                <div className="mt-1 text-sm">{renderScalarValue(value)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Object & List Fields</h3>
          <span className="text-xs text-slate-400">{objectEntries.length}</span>
        </div>
        <div className="space-y-3">
          {objectEntries.map(([key, value]) => (
            <details key={key} className="rounded-xl border border-slate-100 bg-slate-50 p-3 shadow-sm dark:border-slate-800 dark:bg-slate-950">
              <summary className="cursor-pointer text-sm font-semibold text-slate-700 dark:text-slate-200">{formatLabel(key)}</summary>
              <pre className="mt-2 max-h-60 overflow-auto rounded-lg bg-white p-3 text-xs text-slate-600 shadow-inner dark:bg-slate-900 dark:text-slate-300">{JSON.stringify(value, null, 2)}</pre>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

export default withDevIdentifier(CustomerDataPanel, 'CustomerDataPanel', 'teal');
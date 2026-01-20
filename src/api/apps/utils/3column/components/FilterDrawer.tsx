import { ChangeEvent, useEffect, useMemo, useState } from "react";
import type { AdminFilterDefinition } from "../types";

type FilterDrawerProps = {
  open: boolean;
  onClose: () => void;
  definitions?: AdminFilterDefinition[];
  values: Record<string, unknown>;
  onApply: (values: Record<string, unknown>) => void;
  onClear: () => void;
};

type RangeValue = {
  from?: string | number | null;
  to?: string | number | null;
};

type DraftValues = Record<string, unknown>;

const ensureArray = (value: unknown): string[] => {
  if (Array.isArray(value)) {
    return value.map(String).filter(Boolean);
  }
  if (typeof value === "string" && value.length > 0) {
    return [value];
  }
  return [];
};

const normalizeRangeValue = (value: unknown): RangeValue => {
  if (!value || typeof value !== "object") {
    return {};
  }
  const maybeRange = value as RangeValue;
  return {
    from: maybeRange.from ?? undefined,
    to: maybeRange.to ?? undefined,
  };
};

const getInitialDraftValues = (
  definitions?: AdminFilterDefinition[],
  values?: Record<string, unknown>
): DraftValues => {
  if (!definitions?.length || !values) {
    return {};
  }
  const draft: DraftValues = {};
  definitions.forEach((definition) => {
    const currentValue = values[definition.id];
    if (currentValue === undefined || currentValue === null || (typeof currentValue === "string" && currentValue.length === 0)) {
      return;
    }
    if (definition.type === "multi-select") {
      draft[definition.id] = ensureArray(currentValue);
      return;
    }
    if (definition.type === "select") {
      draft[definition.id] = Array.isArray(currentValue) ? ensureArray(currentValue)[0] : currentValue;
      return;
    }
    if (definition.type === "date-range" || definition.type === "number-range") {
      draft[definition.id] = normalizeRangeValue(currentValue);
      return;
    }
    draft[definition.id] = currentValue;
  });
  return draft;
};

export const FilterDrawer = ({
  open,
  onClose,
  definitions,
  values,
  onApply,
  onClear,
}: FilterDrawerProps) => {
  const [draftValues, setDraftValues] = useState<DraftValues>({});

  useEffect(() => {
    if (!open) {
      return;
    }
    setDraftValues(getInitialDraftValues(definitions, values));
  }, [open, definitions, values]);

  const hasActiveFilters = useMemo(() => Object.keys(values ?? {}).length > 0, [values]);

  if (!open) {
    return null;
  }

  const handleTextChange = (definitionId: string) => (event: ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    setDraftValues((current) => ({ ...current, [definitionId]: value }));
  };

  const handleSelectChange = (definitionId: string) => (event: ChangeEvent<HTMLSelectElement>) => {
    const { options, value, multiple } = event.target;
    if (multiple) {
      const selected: string[] = [];
      for (let index = 0; index < options.length; index += 1) {
        const option = options.item(index);
        if (option?.selected) {
          selected.push(option.value);
        }
      }
      setDraftValues((current) => ({ ...current, [definitionId]: selected }));
    } else {
      setDraftValues((current) => ({ ...current, [definitionId]: value || undefined }));
    }
  };

  const handleBooleanChange = (definitionId: string) => (event: ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    if (value === "true") {
      setDraftValues((current) => ({ ...current, [definitionId]: true }));
      return;
    }
    if (value === "false") {
      setDraftValues((current) => ({ ...current, [definitionId]: false }));
      return;
    }
    setDraftValues((current) => {
      const next = { ...current };
      delete next[definitionId];
      return next;
    });
  };

  const handleRangeChange = (definitionId: string, boundary: "from" | "to") =>
    (event: ChangeEvent<HTMLInputElement>) => {
      const value = event.target.value;
      setDraftValues((current) => {
        const existing = normalizeRangeValue(current[definitionId]);
        const next: RangeValue = {
          ...existing,
          [boundary]: value || undefined,
        };
        return { ...current, [definitionId]: next };
      });
    };

  const handleClear = () => {
    setDraftValues({});
    onClear();
    onClose();
  };

  const handleApply = () => {
    const filtered: Record<string, unknown> = {};
    Object.entries(draftValues).forEach(([key, value]) => {
      if (value === undefined || value === null) {
        return;
      }
      if (typeof value === "string" && value.trim().length === 0) {
        return;
      }
      if (Array.isArray(value) && value.length === 0) {
        return;
      }
      if (typeof value === "object" && value !== null) {
        const rangeValue = normalizeRangeValue(value);
        if (!rangeValue.from && !rangeValue.to) {
          return;
        }
        filtered[key] = rangeValue;
        return;
      }
      filtered[key] = value;
    });
    onApply(filtered);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-40 flex items-stretch justify-end bg-slate-900/40">
      <div className="flex w-full max-w-lg flex-col bg-white shadow-2xl dark:bg-slate-900">
        <header className="flex items-start justify-between border-b border-slate-200 px-6 py-5 dark:border-slate-800">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Filters
            </p>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Refine results</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Narrow down the record list using the available filter controls.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 dark:hover:bg-slate-800"
            aria-label="Close filters"
          >
            X
          </button>
        </header>
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {!definitions?.length && (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              No filters are available for this resource yet.
            </p>
          )}
          {definitions?.map((definition) => {
            const fieldId = definition.id;
            const currentValue = draftValues[fieldId];
            return (
              <div key={definition.id} className="mb-6 last:mb-0">
                <label className="mb-1 block text-sm font-semibold text-slate-700 dark:text-slate-200">
                  {definition.label}
                </label>
                {definition.helperText && (
                  <p className="mb-2 text-xs text-slate-500 dark:text-slate-400">{definition.helperText}</p>
                )}
                {definition.type === "text" || definition.type === "search" ? (
                  <input
                    type="text"
                    value={(currentValue as string) ?? ""}
                    onChange={handleTextChange(fieldId)}
                    placeholder={definition.placeholder ?? "Type to filter"}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm transition focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                  />
                ) : null}
                {(definition.type === "select" || definition.type === "multi-select") && (
                  <select
                    multiple={definition.type === "multi-select"}
                    value={
                      definition.type === "multi-select"
                        ? ensureArray(currentValue)
                        : String(currentValue ?? "")
                    }
                    onChange={handleSelectChange(fieldId)}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm transition focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                  >
                    {definition.type === "select" && <option value="">Any</option>}
                    {definition.options?.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                        {option.count !== undefined ? ` (${option.count})` : ""}
                      </option>
                    ))}
                  </select>
                )}
                {definition.type === "boolean" && (
                  <select
                    value={
                      currentValue === true
                        ? "true"
                        : currentValue === false
                        ? "false"
                        : ""
                    }
                    onChange={handleBooleanChange(fieldId)}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm transition focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                  >
                    <option value="">Any</option>
                    <option value="true">{definition.trueLabel ?? "Yes"}</option>
                    <option value="false">{definition.falseLabel ?? "No"}</option>
                  </select>
                )}
                {(definition.type === "date" || definition.type === "datetime") && (
                  <input
                    type={definition.type === "datetime" ? "datetime-local" : "date"}
                    value={(currentValue as string) ?? ""}
                    onChange={handleTextChange(fieldId)}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm transition focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                  />
                )}
                {(definition.type === "date-range" || definition.type === "number-range") && (
                  <div className="grid grid-cols-2 gap-3">
                    <input
                      type={definition.type === "number-range" ? "number" : "date"}
                      value={
                        typeof (currentValue as RangeValue | undefined)?.from === "number"
                          ? String((currentValue as RangeValue).from ?? "")
                          : ((currentValue as RangeValue | undefined)?.from as string) ?? ""
                      }
                      onChange={handleRangeChange(fieldId, "from")}
                      placeholder="From"
                      className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm transition focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                    />
                    <input
                      type={definition.type === "number-range" ? "number" : "date"}
                      value={
                        typeof (currentValue as RangeValue | undefined)?.to === "number"
                          ? String((currentValue as RangeValue).to ?? "")
                          : ((currentValue as RangeValue | undefined)?.to as string) ?? ""
                      }
                      onChange={handleRangeChange(fieldId, "to")}
                      placeholder="To"
                      className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm transition focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
        <footer className="flex flex-col gap-3 border-t border-slate-200 px-6 py-4 text-sm dark:border-slate-800 md:flex-row md:items-center md:justify-between">
          <button
            type="button"
            onClick={handleClear}
            disabled={!hasActiveFilters && Object.keys(draftValues).length === 0}
            className="inline-flex items-center justify-center rounded-md border border-slate-300 px-4 py-2 font-medium text-slate-700 transition hover:bg-slate-100 disabled:opacity-60 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            Clear filters
          </button>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md px-4 py-2 font-medium text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleApply}
              className="rounded-md bg-emerald-600 px-4 py-2 font-medium text-white transition hover:bg-emerald-700"
            >
              Apply filters
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
};

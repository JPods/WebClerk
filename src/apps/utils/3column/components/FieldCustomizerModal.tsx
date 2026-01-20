import { useEffect, useMemo, useState } from "react";
import type { AdminFieldDescriptor, LayoutPreference } from "../types";

type FieldCustomizerModalProps = {
  title: string;
  open: boolean;
  view: "list" | "detail";
  onClose: () => void;
  onSave: (preference: LayoutPreference) => void;
  onReset: () => void;
  availableFields: AdminFieldDescriptor[];
  visibleFieldIds: string[];
  hiddenFieldIds: string[];
};

const unique = (values: string[]): string[] => Array.from(new Set(values));

const sanitizeInitialState = (
  availableFields: AdminFieldDescriptor[],
  visibleFieldIds: string[],
  hiddenFieldIds: string[]
) => {
  const availableIds = availableFields.map((field) => field.id);
  const availableSet = new Set(availableIds);

  const visible = unique(
    visibleFieldIds.filter((fieldId) => availableSet.has(fieldId))
  );

  const defaultHidden = availableIds.filter((fieldId) => !visible.includes(fieldId));

  const hidden = unique([
    ...hiddenFieldIds.filter((fieldId) => availableSet.has(fieldId)),
    ...defaultHidden,
  ]);

  const sanitizedVisible = visible.filter((fieldId) => !hidden.includes(fieldId));
  const sanitizedHidden = hidden.filter((fieldId) => !sanitizedVisible.includes(fieldId));

  return { visible: sanitizedVisible, hidden: sanitizedHidden };
};

const getFieldById = (fields: AdminFieldDescriptor[], fieldId: string) =>
  fields.find((field) => field.id === fieldId);

export const FieldCustomizerModal = ({
  title,
  open,
  view,
  onClose,
  onSave,
  onReset,
  availableFields,
  visibleFieldIds,
  hiddenFieldIds,
}: FieldCustomizerModalProps) => {
  const [visibleIds, setVisibleIds] = useState<string[]>([]);
  const [hiddenIds, setHiddenIds] = useState<string[]>([]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const { visible, hidden } = sanitizeInitialState(
      availableFields,
      visibleFieldIds,
      hiddenFieldIds
    );
    setVisibleIds(visible);
    setHiddenIds(hidden);
  }, [open, availableFields, visibleFieldIds, hiddenFieldIds]);

  const hasChanges = useMemo(() => {
    const { visible, hidden } = sanitizeInitialState(
      availableFields,
      visibleFieldIds,
      hiddenFieldIds
    );
    if (visible.length !== visibleIds.length || hidden.length !== hiddenIds.length) {
      return true;
    }
    return (
      visible.some((fieldId, index) => fieldId !== visibleIds[index]) ||
      hidden.some((fieldId, index) => fieldId !== hiddenIds[index])
    );
  }, [availableFields, visibleFieldIds, hiddenFieldIds, visibleIds, hiddenIds]);

  if (!open) {
    return null;
  }

  const moveVisibleItem = (fieldId: string, direction: "up" | "down") => {
    setVisibleIds((current) => {
      const index = current.indexOf(fieldId);
      if (index === -1) {
        return current;
      }
      const targetIndex = direction === "up" ? index - 1 : index + 1;
      if (targetIndex < 0 || targetIndex >= current.length) {
        return current;
      }
      const next = [...current];
      const temp = next[targetIndex];
      next[targetIndex] = next[index];
      next[index] = temp;
      return next;
    });
  };

  const hideField = (fieldId: string) => {
    setVisibleIds((current) => current.filter((id) => id !== fieldId));
    setHiddenIds((current) => unique([...current, fieldId]));
  };

  const showField = (fieldId: string) => {
    setHiddenIds((current) => current.filter((id) => id !== fieldId));
    setVisibleIds((current) => unique([...current, fieldId]));
  };

  const handleSave = () => {
    onSave({ order: visibleIds, hidden: hiddenIds });
    onClose();
  };

  const handleReset = () => {
    onReset();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="w-full max-w-4xl rounded-lg bg-white shadow-2xl dark:bg-slate-900">
        <header className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-800">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Customize {view === "list" ? "List" : "Detail"} View
            </p>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 dark:hover:bg-slate-800"
            aria-label="Close customization dialog"
          >
            X
          </button>
        </header>
        <div className="grid gap-6 px-6 py-6 lg:grid-cols-2">
          <section>
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Visible fields</h3>
            <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
              Arrange the order using the arrows. You can hide a field using the minus button.
            </p>
            <div className="rounded-md border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900/40">
              <ul className="divide-y divide-slate-200 dark:divide-slate-800">
                {visibleIds.length === 0 && (
                  <li className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">
                    No fields selected. Move fields from the hidden list.
                  </li>
                )}
                {visibleIds.map((fieldId) => {
                  const field = getFieldById(availableFields, fieldId);
                  if (!field) {
                    return null;
                  }
                  const index = visibleIds.indexOf(fieldId);
                  const isFirst = index === 0;
                  const isLast = index === visibleIds.length - 1;
                  return (
                    <li key={fieldId} className="flex items-center justify-between px-4 py-2 text-sm">
                      <div>
                        <p className="font-medium text-slate-800 dark:text-slate-200">{field.label}</p>
                        {field.description && (
                          <p className="text-xs text-slate-500 dark:text-slate-400">{field.description}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          disabled={isFirst}
                          onClick={() => moveVisibleItem(fieldId, "up")}
                          className="rounded-md border border-slate-200 px-2 py-1 text-xs text-slate-600 transition hover:bg-slate-100 disabled:opacity-40 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                        >
                          Up
                        </button>
                        <button
                          type="button"
                          disabled={isLast}
                          onClick={() => moveVisibleItem(fieldId, "down")}
                          className="rounded-md border border-slate-200 px-2 py-1 text-xs text-slate-600 transition hover:bg-slate-100 disabled:opacity-40 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                        >
                          Down
                        </button>
                        <button
                          type="button"
                          onClick={() => hideField(fieldId)}
                          className="rounded-md border border-red-200 px-2 py-1 text-xs text-red-600 transition hover:bg-red-50 dark:border-red-500/40 dark:text-red-300 dark:hover:bg-red-500/10"
                        >
                          -
                        </button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          </section>
          <section>
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Hidden fields</h3>
            <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
              Hidden fields remain available for customization. Add them back to the visible list when needed.
            </p>
            <div className="rounded-md border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/60">
              <ul className="divide-y divide-slate-200 dark:divide-slate-800">
                {hiddenIds.length === 0 && (
                  <li className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">
                    Everything is visible right now.
                  </li>
                )}
                {hiddenIds.map((fieldId) => {
                  const field = getFieldById(availableFields, fieldId);
                  if (!field) {
                    return null;
                  }
                  return (
                    <li key={fieldId} className="flex items-center justify-between px-4 py-2 text-sm">
                      <div>
                        <p className="font-medium text-slate-800 dark:text-slate-200">{field.label}</p>
                        {field.description && (
                          <p className="text-xs text-slate-500 dark:text-slate-400">{field.description}</p>
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={() => showField(fieldId)}
                        className="rounded-md border border-emerald-200 px-3 py-1 text-xs font-medium text-emerald-600 transition hover:bg-emerald-50 dark:border-emerald-500/40 dark:text-emerald-300 dark:hover:bg-emerald-500/10"
                      >
                        +
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          </section>
        </div>
        <footer className="flex flex-col gap-3 border-t border-slate-200 px-6 py-4 text-sm dark:border-slate-800 md:flex-row md:items-center md:justify-between">
          <button
            type="button"
            onClick={handleReset}
            className="inline-flex items-center justify-center rounded-md border border-slate-300 px-4 py-2 font-medium text-slate-700 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            Reset to defaults
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
              onClick={handleSave}
              disabled={!hasChanges}
              className="rounded-md bg-sky-600 px-4 py-2 font-medium text-white transition hover:bg-sky-700 disabled:opacity-50"
            >
              Save changes
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
};

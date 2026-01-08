import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import type { ChangeEvent, ReactNode } from "react";
import { useAdminWorkspace } from "../AdminWorkspaceProvider";
import type { AdminFieldDescriptor } from "../types";
import { FieldCustomizerModal } from "./FieldCustomizerModal";

const isBoolean = (value: unknown): value is boolean => typeof value === "boolean";

const formatDetailValue = (
  value: unknown,
  field: AdminFieldDescriptor,
  record: Record<string, unknown> | null
): ReactNode => {
  if (field.renderDetail) {
    return field.renderDetail(value, record as never);
  }
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  if (Array.isArray(value)) {
    return value.map((entry) => String(entry));
  }
  if (value instanceof Date) {
    return field.kind === "datetime"
      ? `${value.toLocaleDateString()} ${value.toLocaleTimeString()}`
      : value.toLocaleDateString();
  }
  switch (field.kind) {
    case "datetime":
      return new Date(String(value)).toLocaleString();
    case "date":
      return new Date(String(value)).toLocaleDateString();
    case "currency":
      if (typeof value === "number") {
        return value.toLocaleString(undefined, { style: "currency", currency: "USD" });
      }
      if (typeof value === "string" && !Number.isNaN(Number(value))) {
        return Number(value).toLocaleString(undefined, { style: "currency", currency: "USD" });
      }
      return String(value);
    default:
      return String(value);
  }
};

type FieldSection = {
  id: string;
  label?: string;
  description?: string;
  fields: AdminFieldDescriptor[];
};

const buildSections = (
  visibleFields: AdminFieldDescriptor[],
  sections?: Array<{ id: string; label?: string; description?: string; fieldIds: string[] }>
): FieldSection[] => {
  if (!sections?.length) {
    return [
      {
        id: "default",
        label: "Details",
        fields: visibleFields,
      },
    ];
  }
  const fieldMap = new Map(visibleFields.map((field) => [field.id, field] as const));
  const included = new Set<string>();
  const computed: FieldSection[] = [];
  sections.forEach((section) => {
    const sectionFields = section.fieldIds
      .map((fieldId) => fieldMap.get(fieldId))
      .filter((field): field is AdminFieldDescriptor => Boolean(field));
    sectionFields.forEach((field) => included.add(field.id));
    if (sectionFields.length > 0) {
      computed.push({ id: section.id, label: section.label, description: section.description, fields: sectionFields });
    }
  });
  const leftover = visibleFields.filter((field) => !included.has(field.id));
  if (leftover.length) {
    computed.push({ id: "additional", label: "Additional Fields", fields: leftover });
  }
  if (!computed.length) {
    return [
      {
        id: "default",
        label: "Details",
        fields: visibleFields,
      },
    ];
  }
  return computed;
};

const getInitialFormState = (fields: AdminFieldDescriptor[], record: Record<string, unknown> | null) => {
  if (!record) {
    return {} as Record<string, unknown>;
  }
  const draft: Record<string, unknown> = {};
  fields.forEach((field) => {
    draft[field.id] = record[field.id];
  });
  return draft;
};

export const RecordDetailColumn = () => {
  const {
    selectedTable,
    selectedRecordId,
    detail,
    detailFields,
    hiddenDetailFields,
    updateCurrentRecord,
    refreshRecord,
    updateDetailLayout,
    resetDetailLayout,
  } = useAdminWorkspace();

  const [isEditing, setIsEditing] = useState(false);
  const [formValues, setFormValues] = useState<Record<string, unknown>>({});
  const [isDirty, setIsDirty] = useState(false);
  const [showCustomizer, setShowCustomizer] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    setFormValues(getInitialFormState(selectedTable?.fields ?? [], detail.record ?? null));
    setIsEditing(false);
    setIsDirty(false);
    setLocalError(null);
  }, [detail.record?.id, selectedTable?.id]);

  const sections = useMemo(
    () => buildSections(detailFields, selectedTable?.detailSections),
    [detailFields, selectedTable?.detailSections]
  );

  const handleInputChange = useCallback(
    (field: AdminFieldDescriptor, nextValue: unknown) => {
      setFormValues((current) => ({ ...current, [field.id]: nextValue }));
      setIsDirty(true);
    },
    []
  );

  const handleTextChange = useCallback(
    (field: AdminFieldDescriptor) => (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      handleInputChange(field, event.target.value);
    },
    [handleInputChange]
  );

  const handleBooleanToggle = useCallback(
    (field: AdminFieldDescriptor) => (event: ChangeEvent<HTMLSelectElement>) => {
      if (event.target.value === "true") {
        handleInputChange(field, true);
        return;
      }
      if (event.target.value === "false") {
        handleInputChange(field, false);
        return;
      }
      handleInputChange(field, null);
    },
    [handleInputChange]
  );

  const handleArrayChange = useCallback(
    (field: AdminFieldDescriptor) => (event: ChangeEvent<HTMLInputElement>) => {
      const raw = event.target.value;
      const values = raw
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
      handleInputChange(field, values);
    },
    [handleInputChange]
  );

  const handleNumberChange = useCallback(
    (field: AdminFieldDescriptor) => (event: ChangeEvent<HTMLInputElement>) => {
      const raw = event.target.value;
      if (raw === "") {
        handleInputChange(field, null);
        return;
      }
      const numericValue = Number(raw);
      handleInputChange(field, Number.isNaN(numericValue) ? raw : numericValue);
    },
    [handleInputChange]
  );

  const handleCancel = () => {
    setIsEditing(false);
    setFormValues(getInitialFormState(selectedTable?.fields ?? [], detail.record ?? null));
    setIsDirty(false);
    setLocalError(null);
  };

  const handleSave = async () => {
    if (!isDirty) {
      setIsEditing(false);
      return;
    }
    try {
      await updateCurrentRecord(formValues);
      setIsEditing(false);
      setIsDirty(false);
      setLocalError(null);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to save record";
      setLocalError(message);
    }
  };

  const canEdit = Boolean(selectedTable?.dataSource.update);

  if (!selectedRecordId) {
    return (
      <section className="flex h-full flex-col bg-slate-50 p-6 text-sm text-slate-500 dark:bg-slate-900 dark:text-slate-400">
        Select a record from the list to view its details.
      </section>
    );
  }

  const renderFieldInput = (field: AdminFieldDescriptor) => {
    const value = formValues[field.id];
    if (field.renderDetail) {
      const custom = field.renderDetail(value, formValues as never);
      if (custom) {
        return custom;
      }
    }
    if (field.kind === "boolean") {
      return (
        <select
          value={isBoolean(value) ? String(value) : ""}
          onChange={handleBooleanToggle(field)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
        >
          <option value="">Unset</option>
          <option value="true">True</option>
          <option value="false">False</option>
        </select>
      );
    }
    if (field.kind === "date" || field.kind === "datetime") {
      return (
        <input
          type={field.kind === "datetime" ? "datetime-local" : "date"}
          value={typeof value === "string" ? value : ""}
          onChange={handleTextChange(field)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
        />
      );
    }
    if (field.kind === "number" || field.kind === "integer" || field.kind === "currency") {
      return (
        <input
          type="number"
          value={value === undefined || value === null || value === "" ? "" : Number(value)}
          onChange={handleNumberChange(field)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
        />
      );
    }
    if (field.kind === "tag") {
      return (
        <input
          type="text"
          value={Array.isArray(value) ? value.join(", ") : value ? String(value) : ""}
          onChange={handleArrayChange(field)}
          placeholder="tag-one, tag-two"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
        />
      );
    }
    if (field.kind === "json") {
      return (
        <textarea
          rows={6}
          value={typeof value === "string" ? value : JSON.stringify(value ?? {}, null, 2)}
          onChange={handleTextChange(field)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
        />
      );
    }
    if ((field.kind === "text" || !field.kind) && (field.description?.length ?? 0) > 120) {
      return (
        <textarea
          rows={4}
          value={value ? String(value) : ""}
          onChange={handleTextChange(field)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
        />
      );
    }
    return (
      <input
        type="text"
        value={value ? String(value) : ""}
        onChange={handleTextChange(field)}
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
      />
    );
  };

  return (
    <section className="flex h-full flex-col bg-slate-50 dark:bg-slate-950/80">
      <div className="border-b border-slate-200 px-6 py-4 dark:border-slate-800">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              {selectedTable?.label ?? "Detail"}
            </p>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Record #{String(selectedRecordId)}
            </h2>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setShowCustomizer(true)}
              className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Detail layout
            </button>
            {canEdit && (
              <>
                {isEditing ? (
                  <>
                    <button
                      type="button"
                      onClick={handleCancel}
                      className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={handleSave}
                      disabled={!isDirty || detail.saving}
                      className="rounded-md bg-emerald-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-60"
                    >
                      {detail.saving ? "Saving..." : "Save"}
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    onClick={() => setIsEditing(true)}
                    className="rounded-md bg-sky-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-sky-700"
                  >
                    Edit
                  </button>
                )}
              </>
            )}
            <button
              type="button"
              onClick={() => refreshRecord()}
              className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Refresh
            </button>
          </div>
        </div>
        {(detail.error || localError) && (
          <div className="mt-3 rounded-md border border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-700 dark:border-rose-500/40 dark:bg-rose-950/40 dark:text-rose-200">
            {detail.error || localError}
          </div>
        )}
      </div>
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {detail.loading ? (
          <div className="rounded-lg border border-slate-200 bg-white p-6 text-center text-sm text-slate-500 shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
            Loading record details...
          </div>
        ) : detail.record ? (
          <div className="space-y-6">
            {sections.map((section) => (
              <section
                key={section.id}
                className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900"
              >
                <header className="border-b border-slate-200 px-4 py-3 dark:border-slate-800">
                  <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                    {section.label ?? "Section"}
                  </h3>
                  {section.description && (
                    <p className="text-xs text-slate-500 dark:text-slate-400">{section.description}</p>
                  )}
                </header>
                <dl className="grid grid-cols-1 gap-x-6 gap-y-4 px-4 py-4 sm:grid-cols-2">
                  {section.fields.map((field) => {
                    const rawValue = detail.record?.[field.id];
                    const formatted = formatDetailValue(rawValue, field, detail.record ?? null);
                    const formattedArray = Array.isArray(formatted) ? formatted : null;
                    const isRequired = field.required === true;
                    const isSelectField =
                      field.hasChoices === true || field.kind === "status" || field.kind === "badge" || field.kind === "relation";
                    const isLocked = field.locked === true || field.editable === false || field.readOnly === true;
                    const labelClasses = [
                      "text-xs font-semibold uppercase tracking-wide",
                      isRequired ? "text-rose-600 dark:text-rose-300" : "text-slate-500 dark:text-slate-400",
                    ];
                    if (isSelectField) {
                      labelClasses.push("underline decoration-dotted decoration-slate-400 underline-offset-4");
                    }
                    if (isLocked) {
                      labelClasses.push("italic");
                    }
                    const labelTitleDetails: string[] = [];
                    if (isRequired) {
                      labelTitleDetails.push("required");
                    }
                    if (isSelectField) {
                      labelTitleDetails.push("selectable");
                    }
                    if (isLocked) {
                      labelTitleDetails.push("locked");
                    }
                    const labelTitle = labelTitleDetails.length
                      ? `${field.label} (${labelTitleDetails.join(", ")})`
                      : field.label;
                    return (
                      <Fragment key={field.id}>
                        <dt className={labelClasses.join(" ")} title={labelTitle}>
                          {field.label}
                          {isRequired && (
                            <>
                              <span aria-hidden="true" className="ml-1 text-rose-500 dark:text-rose-300">
                                *
                              </span>
                              <span className="sr-only">required</span>
                            </>
                          )}
                          {isSelectField && (
                            <>
                              <span className="sr-only">select field</span>
                              <span className="ml-2 rounded bg-sky-50 px-1.5 py-0.5 text-[10px] font-semibold normal-case text-sky-600 dark:bg-sky-500/10 dark:text-sky-300">
                                Select
                              </span>
                            </>
                          )}
                          {isLocked && (
                            <>
                              <span className="sr-only">locked</span>
                              <span className="ml-1 rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-semibold normal-case text-slate-600 dark:bg-slate-700 dark:text-slate-200">
                                Locked
                              </span>
                            </>
                          )}
                        </dt>
                        <dd className="text-sm text-slate-800 dark:text-slate-100">
                          {isEditing && field.editable !== false && selectedTable?.dataSource.update
                            ? renderFieldInput(field)
                            : formattedArray
                            ? (
                                <ul className="flex flex-wrap gap-1">
                                  {formattedArray.map((entry) => (
                                    <li
                                      key={entry}
                                      className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                                    >
                                      {entry}
                                    </li>
                                  ))}
                                </ul>
                              )
                            : formatted}
                        </dd>
                      </Fragment>
                    );
                  })}
                </dl>
              </section>
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-6 text-sm text-amber-700 shadow-sm dark:border-amber-500/40 dark:bg-amber-950/40 dark:text-amber-200">
            No record details available. Try selecting a different item.
          </div>
        )}
      </div>
      <FieldCustomizerModal
        open={showCustomizer}
        onClose={() => setShowCustomizer(false)}
        onSave={updateDetailLayout}
        onReset={resetDetailLayout}
        availableFields={selectedTable?.fields ?? []}
        visibleFieldIds={detailFields.map((field) => field.id)}
        hiddenFieldIds={hiddenDetailFields.map((field) => field.id)}
        title={`${selectedTable?.label ?? "Record"} detail`}
        view="detail"
      />
    </section>
  );
};

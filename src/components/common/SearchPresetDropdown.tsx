import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { FaArrowLeft, FaBookmark, FaChevronDown, FaEdit, FaPlay, FaSync } from "react-icons/fa";
import { useNavigate } from "react-router-dom";
import {
  getSearchPresets,
  type SearchPresetInputValue,
  type SearchPresetRecord,
} from "@/api/wcapi";
import { PageRoutes } from "@/routes/Routes";

export interface SearchPresetDropdownProps {
  modelKey: string;
  onApplyPreset: (
    preset: SearchPresetRecord,
    values?: Record<string, SearchPresetInputValue>,
  ) => Promise<void> | void;
  className?: string;
  compact?: boolean;
  disabled?: boolean;
  activePresetId?: number;
}

type InputDescriptor = {
  key: string;
  label: string;
  inputType: "text" | "number" | "date" | "boolean";
  placeholder?: string;
};

function labelize(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function buildInputDescriptors(preset: SearchPresetRecord): InputDescriptor[] {
  const inputs: InputDescriptor[] = [];

  if (preset.request_keyword) {
    inputs.push({
      key: preset.request_keyword,
      label: labelize(preset.request_keyword),
      inputType: "text",
      placeholder: `Enter ${labelize(preset.request_keyword).toLowerCase()}`,
    });
  }

  Object.entries(preset.request_filters || {}).forEach(([paramName, spec]) => {
    const fieldName = spec?.field || paramName;
    let inputType: InputDescriptor["inputType"] = "text";

    if (fieldName.startsWith("dt_") || ["begin", "end", "date"].includes(paramName)) {
      inputType = "date";
    } else if (fieldName.startsWith("is_") || paramName.startsWith("is_")) {
      inputType = "boolean";
    } else if (fieldName.includes("priority") || paramName.includes("priority")) {
      inputType = "number";
    }

    inputs.push({
      key: paramName,
      label: labelize(paramName),
      inputType,
      placeholder: `Enter ${labelize(paramName).toLowerCase()}`,
    });
  });

  return inputs;
}

function formatFilterKey(rawKey: string): string {
  const [field, lookup = "exact"] = rawKey.split("__");
  const fieldLabel = labelize(field);

  if (lookup === "exact") {
    return fieldLabel;
  }

  return `${fieldLabel} ${labelize(lookup).toLowerCase()}`;
}

function formatFilterValue(value: unknown): string {
  if (value == null) {
    return "null";
  }

  if (Array.isArray(value)) {
    return value.join(", ");
  }

  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

function buildPresetSummaryParts(preset: SearchPresetRecord): string[] {
  const parts: string[] = [];

  if (preset.relative_period?.preset) {
    const label = labelize(preset.relative_period.preset);
    const fieldLabel = preset.relative_period.field
      ? ` on ${labelize(preset.relative_period.field)}`
      : "";
    parts.push(`${label}${fieldLabel}`);
  }

  if (preset.keyword) {
    parts.push(`Keyword: ${preset.keyword}`);
  }

  if (preset.search_fields?.length) {
    parts.push(`Fields: ${preset.search_fields.map(labelize).join(", ")}`);
  }

  const filterEntries = Object.entries(preset.filters || {});
  if (filterEntries.length) {
    const preview = filterEntries
      .slice(0, 2)
      .map(([key, value]) => `${formatFilterKey(key)}=${formatFilterValue(value)}`)
      .join("; ");
    const extra = filterEntries.length > 2 ? ` +${filterEntries.length - 2} more` : "";
    parts.push(`Filters: ${preview}${extra}`);
  }

  if (preset.request_keyword) {
    parts.push(`Keyword input: ${labelize(preset.request_keyword)}`);
  }

  const requestFilterEntries = Object.entries(preset.request_filters || {});
  if (requestFilterEntries.length) {
    parts.push(
      `Inputs: ${requestFilterEntries
        .map(([paramName, spec]) => `${labelize(paramName)} -> ${labelize(spec.field || paramName)}`)
        .join("; ")}`,
    );
  }

  if (preset.ordering) {
    const descending = preset.ordering.startsWith("-");
    const fieldName = descending ? preset.ordering.slice(1) : preset.ordering;
    parts.push(`Sort: ${labelize(fieldName)} ${descending ? "desc" : "asc"}`);
  }

  return parts.filter(Boolean);
}

function buildPresetSummary(preset: SearchPresetRecord): string {
  const parts = buildPresetSummaryParts(preset);
  return parts[0] || "Stored query";
}

function buildPresetDetailSummary(preset: SearchPresetRecord): string[] {
  return buildPresetSummaryParts(preset).slice(0, 4);
}

function toSettingData(modelKey: string, preset: SearchPresetRecord) {
  return {
    id: preset.id,
    name: preset.name,
    purpose: "search",
    role: preset.role || "all",
    parent_model: preset.model_name || modelKey,
    is_active: true,
    data: {
      keyword: preset.keyword || "",
      search_fields: preset.search_fields || [],
      filters: preset.filters || {},
      ordering: preset.ordering || "",
      pagination: preset.pagination || {},
      request_keyword: preset.request_keyword || "",
      request_filters: preset.request_filters || {},
      relative_period: preset.relative_period || undefined,
    },
  };
}

const SearchPresetDropdown: React.FC<SearchPresetDropdownProps> = ({
  modelKey,
  onApplyPreset,
  className,
  compact = true,
  disabled = false,
  activePresetId,
}) => {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [presets, setPresets] = useState<SearchPresetRecord[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<SearchPresetRecord | null>(null);
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);
  const [values, setValues] = useState<Record<string, SearchPresetInputValue>>({});

  const btnRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const loadPresets = useCallback(async () => {
    if (!modelKey) {
      setPresets([]);
      return;
    }

    setLoading(true);
    try {
      const results = await getSearchPresets(modelKey);
      setPresets(results);
    } catch {
      setPresets([]);
    } finally {
      setLoading(false);
    }
  }, [modelKey]);

  useEffect(() => {
    if (!modelKey) {
      setPresets([]);
      return;
    }

    loadPresets().catch(() => undefined);
  }, [loadPresets, modelKey]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        !btnRef.current?.contains(target) &&
        !panelRef.current?.contains(target)
      ) {
        setOpen(false);
        setSelectedPreset(null);
        setValues({});
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const inputDescriptors = useMemo(
    () => (selectedPreset ? buildInputDescriptors(selectedPreset) : []),
    [selectedPreset],
  );

  const toggle = useCallback(() => {
    if (!open && btnRef.current) {
      const rect = btnRef.current.getBoundingClientRect();
      const panelWidth = 320;
      let left = rect.left;
      if (left + panelWidth > window.innerWidth - 16) {
        left = window.innerWidth - panelWidth - 16;
      }
      setPosition({ top: rect.bottom + 6, left: Math.max(8, left) });
    }
    setOpen((prev) => !prev);
    if (open) {
      setSelectedPreset(null);
      setValues({});
    }
  }, [open]);

  const handlePresetClick = useCallback(
    async (preset: SearchPresetRecord) => {
      const requiresValues = buildInputDescriptors(preset).length > 0;
      if (requiresValues) {
        setSelectedPreset(preset);
        setValues({});
        return;
      }

      setApplying(true);
      try {
        await onApplyPreset(preset, {});
        setOpen(false);
      } finally {
        setApplying(false);
      }
    },
    [onApplyPreset],
  );

  const handleApply = useCallback(async () => {
    if (!selectedPreset) return;
    setApplying(true);
    try {
      await onApplyPreset(selectedPreset, values);
      setOpen(false);
      setSelectedPreset(null);
      setValues({});
    } finally {
      setApplying(false);
    }
  }, [onApplyPreset, selectedPreset, values]);

  const searchDefaults = useMemo(
    () => ({
      purpose: "search",
      parent_model: modelKey,
      role: "all",
      data: {
        keyword: "",
        filters: {},
        ordering: "-dt_created",
        pagination: { limit: 50, offset: 0 },
      },
    }),
    [modelKey],
  );

  if (!loading && presets.length === 0) {
    return null;
  }

  const triggerCls =
    className ??
    (compact
      ? `flex items-center justify-center gap-1 w-9 h-9 rounded-md text-white disabled:opacity-50 ${
          activePresetId != null
            ? "bg-indigo-700 ring-2 ring-indigo-300"
            : "bg-indigo-600 hover:bg-indigo-700"
        }`
      : `flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-md text-white disabled:opacity-50 ${
          activePresetId != null
            ? "bg-indigo-700 ring-2 ring-indigo-300"
            : "bg-indigo-600 hover:bg-indigo-700"
        }`);

  return (
    <>
      <button
        ref={btnRef}
        type="button"
        onClick={toggle}
        disabled={disabled || loading}
        title="Saved Searches"
        className={triggerCls}
      >
        <FaBookmark className={compact ? "w-4 h-4" : "w-3.5 h-3.5"} />
        {!compact && <span>Searches</span>}
        <FaChevronDown className={compact ? "w-2 h-2 ml-px" : "w-2.5 h-2.5"} />
      </button>

      {open &&
        position &&
        createPortal(
          <div
            ref={panelRef}
            className="fixed z-[9999] w-80 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 max-h-[32rem] overflow-y-auto"
            style={{ top: position.top, left: position.left }}
          >
            <div className="py-2">
              {!selectedPreset ? (
                <>
                  <div className="px-4 py-1.5 flex items-center justify-between gap-3">
                    <div className="text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
                      Saved Searches
                    </div>
                    <button
                      type="button"
                      onClick={() => loadPresets()}
                      disabled={loading || applying}
                      className="inline-flex items-center gap-1 text-[10px] font-medium text-indigo-600 hover:text-indigo-700 disabled:opacity-50 dark:text-indigo-300 dark:hover:text-indigo-200"
                      title="Refresh saved searches"
                    >
                      <FaSync className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
                      Refresh
                    </button>
                  </div>
                  {loading ? (
                    <div className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400">
                      Loading saved searches...
                    </div>
                  ) : null}
                  <div className="px-4 pb-2 flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setOpen(false);
                        navigate(PageRoutes.coreSettingDetail.replace(":id?", ""), {
                          state: { mode: "add", data: searchDefaults },
                        });
                      }}
                      className="flex-1 px-3 py-2 text-xs font-medium rounded-md bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-900/30 dark:text-indigo-200 dark:hover:bg-indigo-900/50"
                    >
                      New Search
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setOpen(false);
                        navigate(PageRoutes.coreSettingList, {
                          state: {
                            filterValues: {
                              purpose: "search",
                              parent_model: modelKey,
                            },
                            filtersOpen: true,
                            addDefaults: searchDefaults,
                          },
                        });
                      }}
                      className="flex-1 px-3 py-2 text-xs font-medium rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
                    >
                      Manage Searches
                    </button>
                  </div>
                  {presets.map((preset) => {
                    const paramCount = buildInputDescriptors(preset).length;
                    const detailSummary = buildPresetDetailSummary(preset);
                    const isActive = activePresetId != null && activePresetId === preset.id;
                    return (
                      <div
                        key={preset.id}
                        className={`flex items-start justify-between gap-3 px-4 py-2 text-xs text-gray-700 dark:text-gray-300 ${
                          isActive
                            ? "bg-indigo-50 dark:bg-indigo-900/20"
                            : "hover:bg-gray-100 dark:hover:bg-gray-700"
                        }`}
                      >
                        <button
                          type="button"
                          onClick={() => handlePresetClick(preset)}
                          disabled={applying}
                          className="flex-1 min-w-0 text-left"
                        >
                          <div className="font-medium leading-snug">{preset.name}</div>
                          <div className="mt-1 text-[11px] text-gray-500 dark:text-gray-400 leading-snug">
                            {buildPresetSummary(preset)}
                          </div>
                          {detailSummary.length > 1 && (
                            <div className="mt-1 text-[10px] text-gray-400 dark:text-gray-500 leading-snug">
                              {detailSummary.slice(1).join(" | ")}
                            </div>
                          )}
                        </button>
                        <div className="flex items-center gap-2 shrink-0">
                          {isActive && (
                            <span className="px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-200 text-[10px]">
                              Active
                            </span>
                          )}
                          {paramCount > 0 && (
                            <span className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-300 text-[10px]">
                              {paramCount} input{paramCount === 1 ? "" : "s"}
                            </span>
                          )}
                          <button
                            type="button"
                            onClick={() => {
                              setOpen(false);
                              navigate(
                                PageRoutes.coreSettingDetail.replace(":id?", String(preset.id)),
                                {
                                  state: {
                                    mode: "edit",
                                    data: toSettingData(modelKey, preset),
                                  },
                                },
                              );
                            }}
                            className="text-indigo-600 hover:text-indigo-700 dark:text-indigo-300 dark:hover:text-indigo-200"
                            title="Edit search"
                          >
                            <FaEdit className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </>
              ) : (
                <div className="px-4 py-2">
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedPreset(null);
                      setValues({});
                    }}
                    className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                  >
                    <FaArrowLeft className="w-3 h-3" />
                    Back
                  </button>

                  <div className="mt-3 mb-3">
                    <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                      {selectedPreset.name}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 space-y-1">
                      {buildPresetDetailSummary(selectedPreset).map((line) => (
                        <div key={line}>{line}</div>
                      ))}
                      {buildPresetDetailSummary(selectedPreset).length === 0 && (
                        <div>Enter the values needed to run this saved search.</div>
                      )}
                    </div>
                  </div>

                  <div className="space-y-3">
                    {inputDescriptors.map((input) => (
                      <label key={input.key} className="block">
                        <span className="block mb-1 text-xs font-medium text-gray-700 dark:text-gray-300">
                          {input.label}
                        </span>
                        {input.inputType === "boolean" ? (
                          <select
                            value={String(values[input.key] ?? "")}
                            onChange={(e) =>
                              setValues((prev) => ({
                                ...prev,
                                [input.key]: e.target.value,
                              }))
                            }
                            className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                          >
                            <option value="">Any</option>
                            <option value="true">True</option>
                            <option value="false">False</option>
                          </select>
                        ) : (
                          <input
                            type={input.inputType}
                            value={String(values[input.key] ?? "")}
                            onChange={(e) =>
                              setValues((prev) => ({
                                ...prev,
                                [input.key]: e.target.value,
                              }))
                            }
                            placeholder={input.placeholder}
                            className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                          />
                        )}
                      </label>
                    ))}
                  </div>

                  <button
                    type="button"
                    onClick={handleApply}
                    disabled={applying}
                    className="mt-4 w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
                  >
                    <FaPlay className="w-3 h-3" />
                    Run Search
                  </button>
                </div>
              )}
            </div>
          </div>,
          document.body,
        )}
    </>
  );
};

export default SearchPresetDropdown;
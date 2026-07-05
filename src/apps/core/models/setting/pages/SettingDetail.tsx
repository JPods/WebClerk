/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Type, Target, Shield, Box, Database } from "lucide-react";

import ComponentCard from "../../../../../components/common/ComponentCard";
import HorizontalField from "../../../../../components/form/HorizontalField";
import { useColumnCount, ColumnSelector, getGridClassName } from "../../../../../components/form/useColumnCount";
import { Input, DropDown } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createSetting, updateSetting } from "../services/settingApi";
import { getModelDetail, getModelNames } from "@/api/wcapi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router";
import { settingSchema } from "../utils/settingSchema";
import { SettingAddProps } from "../types/settingType";
import { SimpleDetailHeader } from "../../../../../components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "../../../../../components/common/SimpleDetailToolbar";

// Tab navigation
import { DetailTabs, useDetailTabs } from "@/components/common/DetailTabs";
import { ScalarCard, BaseModelCards } from "@/apps/common/components/detail";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

const STORAGE_KEY = "settingDetail_columnCount";

const DEFAULT_SEARCH_DATA = {
  keyword: "",
  search_fields: [],
  filters: {},
  ordering: "-dt_created",
  pagination: { limit: 50, offset: 0 },
  request_keyword: "",
  request_filters: {},
};

const LOOKUP_OPTIONS = [
  { value: "exact", label: "Exact" },
  { value: "icontains", label: "Contains" },
  { value: "istartswith", label: "Starts With" },
  { value: "startswith", label: "Starts With (Case)" },
  { value: "gte", label: ">=" },
  { value: "lte", label: "<=" },
  { value: "gt", label: ">" },
  { value: "lt", label: "<" },
  { value: "in", label: "In" },
  { value: "ne", label: "Not Equal" },
];

const TEXT_FIELD_TYPES = [
  "CharField",
  "TextField",
  "EmailField",
  "URLField",
  "SlugField",
  "UUIDField",
];

const DATE_FIELD_TYPES = ["DateField", "DateTimeField"];

const BOOLEAN_FIELD_TYPES = ["BooleanField"];

const NUMERIC_FIELD_TYPES = [
  "IntegerField",
  "BigIntegerField",
  "SmallIntegerField",
  "PositiveIntegerField",
  "PositiveSmallIntegerField",
  "FloatField",
  "DecimalField",
];

const BOOLEAN_VALUE_OPTIONS = [
  { value: "true", label: "True" },
  { value: "false", label: "False" },
  { value: "null", label: "Null" },
];

type FilterRow = {
  id: string;
  field: string;
  lookup: string;
  value: string;
};

type RequestFilterRow = {
  id: string;
  param: string;
  field: string;
  lookup: string;
};

type SearchFieldRow = {
  id: string;
  field: string;
};

function nextRowId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

function filtersObjectToRows(filters: Record<string, unknown>): FilterRow[] {
  return Object.entries(filters || {}).map(([rawKey, rawValue]) => {
    const [field, lookup = "exact"] = rawKey.split("__");
    return {
      id: nextRowId("filter"),
      field,
      lookup,
      value:
        typeof rawValue === "string"
          ? rawValue
          : JSON.stringify(rawValue ?? ""),
    };
  });
}

function filterRowsToObject(rows: FilterRow[]): Record<string, unknown> {
  const output: Record<string, unknown> = {};
  rows.forEach((row) => {
    if (!row.field.trim()) return;
    const key = row.lookup && row.lookup !== "exact"
      ? `${row.field.trim()}__${row.lookup.trim()}`
      : row.field.trim();
    const rawValue = row.value.trim();
    if (!rawValue) return;
    if (rawValue === "true") {
      output[key] = true;
      return;
    }
    if (rawValue === "false") {
      output[key] = false;
      return;
    }
    if (rawValue === "null") {
      output[key] = null;
      return;
    }
    if (!Number.isNaN(Number(rawValue)) && rawValue !== "") {
      output[key] = Number(rawValue);
      return;
    }
    try {
      output[key] = JSON.parse(rawValue);
    } catch {
      output[key] = rawValue;
    }
  });
  return output;
}

function requestFiltersObjectToRows(
  requestFilters: Record<string, { field?: string; lookup?: string }>,
): RequestFilterRow[] {
  return Object.entries(requestFilters || {}).map(([param, spec]) => ({
    id: nextRowId("request-filter"),
    param,
    field: spec?.field || "",
    lookup: spec?.lookup || "exact",
  }));
}

function requestFilterRowsToObject(
  rows: RequestFilterRow[],
): Record<string, { field: string; lookup: string }> {
  const output: Record<string, { field: string; lookup: string }> = {};
  rows.forEach((row) => {
    const param = row.param.trim();
    const field = row.field.trim();
    if (!param || !field) return;
    output[param] = {
      field,
      lookup: row.lookup || "exact",
    };
  });
  return output;
}

function searchFieldsToRows(fields: string[]): SearchFieldRow[] {
  return (fields || []).map((field) => ({
    id: nextRowId("search-field"),
    field,
  }));
}

function searchFieldRowsToArray(rows: SearchFieldRow[]): string[] {
  return rows
    .map((row) => row.field.trim())
    .filter(Boolean);
}

function getLookupOptionsForFieldType(fieldType?: string) {
  if (fieldType && TEXT_FIELD_TYPES.includes(fieldType)) {
    return LOOKUP_OPTIONS.filter((option) =>
      ["exact", "icontains", "istartswith", "startswith", "in", "ne"].includes(option.value),
    );
  }

  if (fieldType && DATE_FIELD_TYPES.includes(fieldType)) {
    return LOOKUP_OPTIONS.filter((option) =>
      ["exact", "gte", "lte", "gt", "lt", "in", "ne"].includes(option.value),
    );
  }

  if (fieldType && BOOLEAN_FIELD_TYPES.includes(fieldType)) {
    return LOOKUP_OPTIONS.filter((option) =>
      ["exact", "ne"].includes(option.value),
    );
  }

  if (fieldType && NUMERIC_FIELD_TYPES.includes(fieldType)) {
    return LOOKUP_OPTIONS.filter((option) =>
      ["exact", "gte", "lte", "gt", "lt", "in", "ne"].includes(option.value),
    );
  }

  return LOOKUP_OPTIONS;
}

function getDefaultLookupForFieldType(fieldType?: string) {
  if (fieldType && TEXT_FIELD_TYPES.includes(fieldType)) {
    return "icontains";
  }

  return "exact";
}

function getDefaultValueForFieldType(fieldType?: string) {
  if (fieldType && BOOLEAN_FIELD_TYPES.includes(fieldType)) {
    return "true";
  }

  return "";
}

function safeParseSettingData(raw: unknown): { value: any; isValid: boolean } {
  if (raw == null || raw === "") {
    return { value: {}, isValid: true };
  }
  if (typeof raw === "string") {
    try {
      return { value: JSON.parse(raw), isValid: true };
    } catch {
      return { value: null, isValid: false };
    }
  }
  if (typeof raw === "object") {
    return { value: raw, isValid: true };
  }
  return { value: {}, isValid: true };
}

function stringifyData(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2);
}

function SettingDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: SettingAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
  } = useForm<z.infer<typeof settingSchema>>({
    resolver: zodResolver(settingSchema),
  });

  const location = useLocation();
  const navigate = useNavigate();
  const routeState = (location.state as any) || {};
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);
  const [isSaving, setIsSaving] = useState(false);
  const data = dataProp || routeState.data || null;
  const purposeValue = watch("purpose");
  const rawDataValue = watch("config");
  const parentModelValue = watch("parent_model");

  const parsedData = useMemo(
    () => safeParseSettingData(rawDataValue),
    [rawDataValue],
  );

  const searchData = useMemo(() => {
    if (purposeValue !== "search" || !parsedData.isValid) {
      return null;
    }
    return {
      ...DEFAULT_SEARCH_DATA,
      ...(parsedData.value || {}),
      pagination: {
        ...DEFAULT_SEARCH_DATA.pagination,
        ...((parsedData.value || {}).pagination || {}),
      },
    };
  }, [parsedData.isValid, parsedData.value, purposeValue]);

  // Full record data for panels
  const [recordData, setRecordData] = useState<any>(data || {});
  const [filtersText, setFiltersText] = useState("{}");
  const [requestFiltersText, setRequestFiltersText] = useState("{}");
  const [filterRows, setFilterRows] = useState<FilterRow[]>([]);
  const [requestFilterRows, setRequestFilterRows] = useState<RequestFilterRow[]>([]);
  const [searchFieldRows, setSearchFieldRows] = useState<SearchFieldRow[]>([]);
  const [modelOptions, setModelOptions] = useState<Array<{ value: string; label: string }>>([]);
  const [modelFieldOptions, setModelFieldOptions] = useState<Array<{ value: string; label: string; type?: string }>>([]);

  useEffect(() => {
    register("purpose");
    register("config");
    register("parent_model");
  }, [register]);

  // Tab navigation
  const { activeTab, setActiveTab } = useDetailTabs("setting_detail", "actions", [
    "actions", "comments", "documents", "raw",
  ]);

  useEffect(() => {
    if (initialMode === "add") {
      const initialData = data || {};
      reset(initialData);
      Object.keys(initialData).forEach((key: any) => {
        if (initialData[key] !== undefined) {
          setValue(key, initialData[key]);
        }
      });
      setRecordData(initialData);
    } else if (data) {
      Object.keys(data).forEach((key: any) => {
        if (data[key] !== undefined) {
          setValue(key, data[key]);
        }
      });
      setRecordData(data);
    } else {
      reset({});
      setRecordData({});
    }
  }, [data, reset, setValue, initialMode]);

  useEffect(() => {
    let cancelled = false;
    getModelNames()
      .then((result) => {
        if (cancelled) return;
        const names = Array.isArray(result?.model_names) ? result.model_names : [];
        setModelOptions(
          names.map((name) => ({
            value: name,
            label: name,
          })),
        );
      })
      .catch(() => {
        if (!cancelled) {
          setModelOptions([]);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (purposeValue === "search" && (rawDataValue == null || rawDataValue === "")) {
      setValue("config", stringifyData(DEFAULT_SEARCH_DATA));
    }
  }, [purposeValue, rawDataValue, setValue]);

  useEffect(() => {
    let cancelled = false;

    if (!parentModelValue) {
      setModelFieldOptions([]);
      return;
    }

    getModelDetail(parentModelValue)
      .then((result) => {
        if (cancelled) return;
        const fields = Array.isArray(result?.model?.fields) ? result.model.fields : [];
        setModelFieldOptions(
          fields
            .filter((field) => field?.name)
            .map((field) => ({
              value: field.name,
              label: field.type ? `${field.name} (${field.type})` : field.name,
              type: field.type,
            })),
        );
      })
      .catch(() => {
        if (!cancelled) {
          setModelFieldOptions([]);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [parentModelValue]);

  useEffect(() => {
    if (!searchData) {
      setFiltersText("{}");
      setRequestFiltersText("{}");
      setFilterRows([]);
      setRequestFilterRows([]);
      return;
    }
    setFiltersText(stringifyData(searchData.filters || {}));
    setRequestFiltersText(stringifyData(searchData.request_filters || {}));
    setFilterRows(filtersObjectToRows(searchData.filters || {}));
    setRequestFilterRows(
      requestFiltersObjectToRows(searchData.request_filters || {}),
    );
    setSearchFieldRows(searchFieldsToRows(searchData.search_fields || []));
  }, [searchData]);

  const updateSearchData = (updater: (current: any) => any) => {
    const current = searchData || DEFAULT_SEARCH_DATA;
    const next = updater(current);
    setValue("config", stringifyData(next), { shouldDirty: true });
  };

  const onSubmit = async (formData: z.infer<typeof settingSchema>) => {
    setIsSaving(true);
    try {
      const payload = { ...formData } as any;
      if (typeof payload.config === "string") {
        const trimmed = payload.config.trim();
        payload.config = trimmed ? JSON.parse(trimmed) : {};
      }
      const res =
        currentMode === "add"
          ? await createSetting(payload)
          : await updateSetting({ ...payload, id: data && data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Setting ${
              currentMode === "add" ? "created" : "updated"
            } successfully`,
            type: "success",
          })
        );
        if (onSaved) {
          onSaved();
        }
      }
    } catch (error: any) {
      const message =
        error instanceof SyntaxError
          ? "Data must be valid JSON"
          : error.message;
      dispatch(showToast({ message, type: "error" }));
    } finally {
      setIsSaving(false);
    }
  };

  const handleEdit = () => {
    setCurrentMode("edit");
  };

  const handleCancel = () => {
    if (inline && onCancelInline) {
      onCancelInline();
    } else if (initialMode === "add") {
      navigate(-1);
    } else {
      if (data) {
        Object.keys(data).forEach((key: any) => {
          if (data[key] !== undefined) {
            setValue(key, data[key]);
          }
        });
      }
      setCurrentMode("view");
    }
  };

  const purposes = [
    { value: "view_edit", label: "View Edit" },
    { value: "constants", label: "Constants" },
    { value: "db_defaults", label: "DB Defaults" },
    { value: "sales_defaults", label: "Sales Defaults" },
    { value: "purchase_defaults", label: "Purchase Defaults" },
    { value: "accounting_defaults", label: "Accounting Defaults" },
    { value: "search", label: "Search" },
  ];

  const handlePurposeChange = (value: string) => {
    setValue("purpose", value, { shouldDirty: true });
  };

  const textSearchFieldOptions = useMemo(
    () =>
      modelFieldOptions.filter((field) =>
        TEXT_FIELD_TYPES.includes(field.type || ""),
      ),
    [modelFieldOptions],
  );

  const relativePeriodFieldOptions = useMemo(
    () => modelFieldOptions.filter((field) => DATE_FIELD_TYPES.includes(field.type || "")),
    [modelFieldOptions],
  );

  const getFieldType = (fieldName: string) =>
    modelFieldOptions.find((field) => field.value === fieldName)?.type;

  const handleFilterValueChange = (rowId: string, value: string) => {
    const next = filterRows.map((item) =>
      item.id === rowId ? { ...item, value } : item,
    );
    setFilterRows(next);
    updateSearchData((current) => ({
      ...current,
      filters: filterRowsToObject(next),
    }));
  };

  const [columnCount, setColumnCount] = useColumnCount(STORAGE_KEY, 3);

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            currentMode === "edit"
              ? "Edit Setting"
              : currentMode === "view"
              ? "View Setting"
              : "Setting Detail"
          }
        />
      )}

      {!inline && (
        <SimpleDetailHeader
          entityName="Setting"
          recordId={data?.id}
          recordName={data?.name}
          mode={currentMode}
          backUrl="/core/settings"
        />
      )}

      {!inline && (
        <SimpleDetailToolbar
          mode={currentMode}
          isSaving={isSaving}
          onSave={handleSubmit(onSubmit)}
          onCancel={handleCancel}
          onEdit={handleEdit}
        />
      )}

      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {currentMode === "edit"
                ? "Edit Setting"
                : currentMode === "view"
                ? "View Setting"
                : "Add New Setting"}
            </h3>
            {onCancelInline && (
              <button
                type="button"
                onClick={onCancelInline}
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                &times;
              </button>
            )}
          </div>
        )}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="flex justify-end mb-4">
            <ColumnSelector value={columnCount} onChange={setColumnCount} />
          </div>
          <div className={getGridClassName(columnCount)}>
            <HorizontalField label="Name" htmlFor="name" error={errors.name?.message} icon={Type}>
              <Input
                type="text"
                id="name"
                placeholder="Name"
                {...register("name")}
                error={errors.name && errors.name.message ? true : false}
                hint={errors.name && errors.name.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Purpose" htmlFor="purpose" icon={Target}>
              <DropDown
                id="purpose"
                options={purposes}
                placeholder="Select Purpose"
                value={watch("purpose")}
                onChange={handlePurposeChange}
                className="dark:bg-dark-900"
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Role" htmlFor="role" error={errors.role?.message} icon={Shield}>
              <Input
                type="text"
                id="role"
                placeholder="Role"
                {...register("role")}
                error={errors.role && errors.role.message ? true : false}
                hint={errors.role && errors.role.message}
                disabled={currentMode === "view"}
              />
            </HorizontalField>
            <HorizontalField label="Parent Model" htmlFor="parent_model" error={errors.parent_model?.message} icon={Box}>
              <DropDown
                id="parent_model"
                options={modelOptions}
                placeholder="Select Model"
                value={String(parentModelValue || "")}
                onChange={(value: string) =>
                  setValue("parent_model", value, { shouldDirty: true })
                }
                className="dark:bg-dark-900"
                disabled={currentMode === "view"}
                error={errors.parent_model ? true : false}
              />
            </HorizontalField>
            {purposeValue === "search" && searchData && (
              <>
                <HorizontalField label="Keyword" htmlFor="search_keyword" icon={Database}>
                  <Input
                    type="text"
                    id="search_keyword"
                    placeholder="acme,@west"
                    value={searchData.keyword || ""}
                    onChange={(e: any) =>
                      updateSearchData((current) => ({
                        ...current,
                        keyword: e.target.value,
                      }))
                    }
                    disabled={currentMode === "view"}
                  />
                </HorizontalField>
                <HorizontalField label="Search Fields" htmlFor="search_fields" icon={Database}>
                  <div className="space-y-2 w-full">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {textSearchFieldOptions.length > 0
                          ? "Text-searchable fields from the selected model"
                          : "Select a model to load searchable fields"}
                      </span>
                      {currentMode !== "view" && textSearchFieldOptions.length > 0 && (
                        <button
                          type="button"
                          onClick={() => {
                            const next = [
                              ...searchFieldRows,
                              { id: nextRowId("search-field"), field: "" },
                            ];
                            setSearchFieldRows(next);
                          }}
                          className="px-2 py-1 text-xs rounded bg-brand-50 text-brand-700 hover:bg-brand-100 dark:bg-brand-500/10 dark:text-brand-300"
                        >
                          Add Search Field
                        </button>
                      )}
                    </div>
                    {searchFieldRows.length === 0 ? (
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        No search fields configured.
                      </div>
                    ) : (
                      searchFieldRows.map((row) => (
                        <div key={row.id} className="grid grid-cols-12 gap-2 items-center">
                          <div className="col-span-11">
                            <DropDown
                              id={`search-field-${row.id}`}
                              options={textSearchFieldOptions}
                              placeholder="Select field"
                              value={row.field}
                              onChange={(value: string) => {
                                const next = searchFieldRows.map((item) =>
                                  item.id === row.id ? { ...item, field: value } : item,
                                );
                                setSearchFieldRows(next);
                                updateSearchData((current) => ({
                                  ...current,
                                  search_fields: searchFieldRowsToArray(next),
                                }));
                              }}
                              disabled={currentMode === "view" || textSearchFieldOptions.length === 0}
                            />
                          </div>
                          <div className="col-span-1">
                            {currentMode !== "view" && (
                              <button
                                type="button"
                                onClick={() => {
                                  const next = searchFieldRows.filter((item) => item.id !== row.id);
                                  setSearchFieldRows(next);
                                  updateSearchData((current) => ({
                                    ...current,
                                    search_fields: searchFieldRowsToArray(next),
                                  }));
                                }}
                                className="w-full px-2 py-2 text-xs rounded bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-500/10 dark:text-red-300"
                              >
                                X
                              </button>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </HorizontalField>
                <HorizontalField label="Ordering" htmlFor="ordering" icon={Database}>
                  <Input
                    type="text"
                    id="ordering"
                    placeholder="-dt_created"
                    value={searchData.ordering || ""}
                    onChange={(e: any) =>
                      updateSearchData((current) => ({
                        ...current,
                        ordering: e.target.value,
                      }))
                    }
                    disabled={currentMode === "view"}
                  />
                </HorizontalField>
                <HorizontalField label="Request Keyword Param" htmlFor="request_keyword" icon={Database}>
                  <Input
                    type="text"
                    id="request_keyword"
                    placeholder="assigned_to"
                    value={searchData.request_keyword || ""}
                    onChange={(e: any) =>
                      updateSearchData((current) => ({
                        ...current,
                        request_keyword: e.target.value,
                      }))
                    }
                    disabled={currentMode === "view"}
                  />
                </HorizontalField>
                <HorizontalField label="Limit" htmlFor="search_limit" icon={Database}>
                  <Input
                    type="number"
                    id="search_limit"
                    placeholder="50"
                    value={String(searchData.pagination?.limit ?? 50)}
                    onChange={(e: any) =>
                      updateSearchData((current) => ({
                        ...current,
                        pagination: {
                          ...(current.pagination || {}),
                          limit: Number(e.target.value || 0) || 0,
                        },
                      }))
                    }
                    disabled={currentMode === "view"}
                  />
                </HorizontalField>
                <HorizontalField label="Offset" htmlFor="search_offset" icon={Database}>
                  <Input
                    type="number"
                    id="search_offset"
                    placeholder="0"
                    value={String(searchData.pagination?.offset ?? 0)}
                    onChange={(e: any) =>
                      updateSearchData((current) => ({
                        ...current,
                        pagination: {
                          ...(current.pagination || {}),
                          offset: Number(e.target.value || 0) || 0,
                        },
                      }))
                    }
                    disabled={currentMode === "view"}
                  />
                </HorizontalField>
                <HorizontalField label="Relative Period Field" htmlFor="relative_period_field" icon={Database}>
                  <DropDown
                    id="relative_period_field"
                    options={relativePeriodFieldOptions}
                    placeholder="Select date field"
                    value={searchData.relative_period?.field || ""}
                    onChange={(value: string) =>
                      updateSearchData((current) => ({
                        ...current,
                        relative_period: {
                          ...(current.relative_period || {}),
                          field: value,
                        },
                      }))
                    }
                    disabled={currentMode === "view" || relativePeriodFieldOptions.length === 0}
                  />
                </HorizontalField>
                <HorizontalField label="Relative Period Preset" htmlFor="relative_period_preset" icon={Database}>
                  <DropDown
                    id="relative_period_preset"
                    options={[
                      { value: "", label: "None" },
                      { value: "current_month", label: "Current Month" },
                      { value: "current_quarter", label: "Current Quarter" },
                    ]}
                    placeholder="Select Period"
                    value={searchData.relative_period?.preset || ""}
                    onChange={(value: string) =>
                      updateSearchData((current) => ({
                        ...current,
                        relative_period: value
                          ? {
                              field:
                                current.relative_period?.field || "dt_created",
                              preset: value,
                            }
                          : undefined,
                      }))
                    }
                    className="dark:bg-dark-900"
                    disabled={currentMode === "view"}
                  />
                </HorizontalField>
              </>
            )}
            <HorizontalField label="Config" htmlFor="config" error={errors.config?.message} icon={Database}>
              <div className="space-y-3 w-full">
                {purposeValue === "search" && searchData ? (
                  <>
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
                          Filters
                        </label>
                        {currentMode !== "view" && (
                          <button
                            type="button"
                            onClick={() =>
                              setFilterRows((prev) => [
                                ...prev,
                                {
                                  id: nextRowId("filter"),
                                  field: "",
                                  lookup: "exact",
                                  value: "",
                                },
                              ])
                            }
                            className="px-2 py-1 text-xs rounded bg-brand-50 text-brand-700 hover:bg-brand-100 dark:bg-brand-500/10 dark:text-brand-300"
                          >
                            Add Filter
                          </button>
                        )}
                      </div>
                      <div className="space-y-2">
                        {filterRows.length === 0 ? (
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            No filters configured.
                          </div>
                        ) : (
                          filterRows.map((row) => (
                            <div key={row.id} className="grid grid-cols-12 gap-2 items-center">
                              <div className="col-span-4">
                                <DropDown
                                  id={`filter-field-${row.id}`}
                                  options={modelFieldOptions}
                                  placeholder="Select field"
                                  value={row.field}
                                  onChange={(value: string) => {
                                    const nextLookup = getDefaultLookupForFieldType(getFieldType(value));
                                    const nextValue = getDefaultValueForFieldType(getFieldType(value));
                                    const next = filterRows.map((item) =>
                                      item.id === row.id
                                        ? { ...item, field: value, lookup: nextLookup, value: nextValue }
                                        : item,
                                    );
                                    setFilterRows(next);
                                    updateSearchData((current) => ({
                                      ...current,
                                      filters: filterRowsToObject(next),
                                    }));
                                  }}
                                  disabled={currentMode === "view" || modelFieldOptions.length === 0}
                                />
                              </div>
                              <div className="col-span-3">
                                <DropDown
                                  id={`filter-lookup-${row.id}`}
                                  options={getLookupOptionsForFieldType(getFieldType(row.field))}
                                  placeholder="Lookup"
                                  value={row.lookup}
                                  onChange={(value: string) => {
                                    const next = filterRows.map((item) =>
                                      item.id === row.id ? { ...item, lookup: value } : item,
                                    );
                                    setFilterRows(next);
                                    updateSearchData((current) => ({
                                      ...current,
                                      filters: filterRowsToObject(next),
                                    }));
                                  }}
                                  disabled={currentMode === "view"}
                                />
                              </div>
                              <div className="col-span-4">
                                {(() => {
                                  const fieldType = getFieldType(row.field);

                                  if (fieldType && BOOLEAN_FIELD_TYPES.includes(fieldType)) {
                                    return (
                                      <DropDown
                                        id={`filter-value-${row.id}`}
                                        options={BOOLEAN_VALUE_OPTIONS}
                                        placeholder="Select value"
                                        value={row.value}
                                        onChange={(value: string) =>
                                          handleFilterValueChange(row.id, value)
                                        }
                                        disabled={currentMode === "view"}
                                      />
                                    );
                                  }

                                  if (fieldType === "DateField") {
                                    return (
                                      <Input
                                        type="date"
                                        placeholder="value"
                                        value={row.value}
                                        onChange={(e: any) =>
                                          handleFilterValueChange(row.id, e.target.value)
                                        }
                                        disabled={currentMode === "view"}
                                      />
                                    );
                                  }

                                  if (fieldType === "DateTimeField") {
                                    return (
                                      <Input
                                        type="datetime-local"
                                        placeholder="value"
                                        value={row.value}
                                        onChange={(e: any) =>
                                          handleFilterValueChange(row.id, e.target.value)
                                        }
                                        disabled={currentMode === "view"}
                                      />
                                    );
                                  }

                                  if (fieldType && NUMERIC_FIELD_TYPES.includes(fieldType)) {
                                    return (
                                      <Input
                                        type="number"
                                        placeholder="value"
                                        value={row.value}
                                        onChange={(e: any) =>
                                          handleFilterValueChange(row.id, e.target.value)
                                        }
                                        disabled={currentMode === "view"}
                                      />
                                    );
                                  }

                                  return (
                                    <Input
                                      type="text"
                                      placeholder="value"
                                      value={row.value}
                                      onChange={(e: any) =>
                                        handleFilterValueChange(row.id, e.target.value)
                                      }
                                      disabled={currentMode === "view"}
                                    />
                                  );
                                })()}
                              </div>
                              <div className="col-span-1">
                                {currentMode !== "view" && (
                                  <button
                                    type="button"
                                    onClick={() => {
                                      const next = filterRows.filter((item) => item.id !== row.id);
                                      setFilterRows(next);
                                      updateSearchData((current) => ({
                                        ...current,
                                        filters: filterRowsToObject(next),
                                      }));
                                    }}
                                    className="w-full px-2 py-2 text-xs rounded bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-500/10 dark:text-red-300"
                                  >
                                    X
                                  </button>
                                )}
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
                          Request Filters
                        </label>
                        {currentMode !== "view" && (
                          <button
                            type="button"
                            onClick={() =>
                              setRequestFilterRows((prev) => [
                                ...prev,
                                {
                                  id: nextRowId("request-filter"),
                                  param: "",
                                  field: "",
                                  lookup: "exact",
                                },
                              ])
                            }
                            className="px-2 py-1 text-xs rounded bg-brand-50 text-brand-700 hover:bg-brand-100 dark:bg-brand-500/10 dark:text-brand-300"
                          >
                            Add Request Filter
                          </button>
                        )}
                      </div>
                      <div className="space-y-2">
                        {requestFilterRows.length === 0 ? (
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            No request filters configured.
                          </div>
                        ) : (
                          requestFilterRows.map((row) => (
                            <div key={row.id} className="grid grid-cols-12 gap-2 items-center">
                              <div className="col-span-3">
                                <Input
                                  type="text"
                                  placeholder="param"
                                  value={row.param}
                                  onChange={(e: any) => {
                                    const next = requestFilterRows.map((item) =>
                                      item.id === row.id ? { ...item, param: e.target.value } : item,
                                    );
                                    setRequestFilterRows(next);
                                    updateSearchData((current) => ({
                                      ...current,
                                      request_filters: requestFilterRowsToObject(next),
                                    }));
                                  }}
                                  disabled={currentMode === "view"}
                                />
                              </div>
                              <div className="col-span-4">
                                <DropDown
                                  id={`request-filter-field-${row.id}`}
                                  options={modelFieldOptions}
                                  placeholder="Select field"
                                  value={row.field}
                                  onChange={(value: string) => {
                                    const nextLookup = getDefaultLookupForFieldType(getFieldType(value));
                                    const next = requestFilterRows.map((item) =>
                                      item.id === row.id ? { ...item, field: value, lookup: nextLookup } : item,
                                    );
                                    setRequestFilterRows(next);
                                    updateSearchData((current) => ({
                                      ...current,
                                      request_filters: requestFilterRowsToObject(next),
                                    }));
                                  }}
                                  disabled={currentMode === "view" || modelFieldOptions.length === 0}
                                />
                              </div>
                              <div className="col-span-4">
                                <DropDown
                                  id={`request-filter-lookup-${row.id}`}
                                  options={getLookupOptionsForFieldType(getFieldType(row.field))}
                                  placeholder="Lookup"
                                  value={row.lookup}
                                  onChange={(value: string) => {
                                    const next = requestFilterRows.map((item) =>
                                      item.id === row.id ? { ...item, lookup: value } : item,
                                    );
                                    setRequestFilterRows(next);
                                    updateSearchData((current) => ({
                                      ...current,
                                      request_filters: requestFilterRowsToObject(next),
                                    }));
                                  }}
                                  disabled={currentMode === "view"}
                                />
                              </div>
                              <div className="col-span-1">
                                {currentMode !== "view" && (
                                  <button
                                    type="button"
                                    onClick={() => {
                                      const next = requestFilterRows.filter((item) => item.id !== row.id);
                                      setRequestFilterRows(next);
                                      updateSearchData((current) => ({
                                        ...current,
                                        request_filters: requestFilterRowsToObject(next),
                                      }));
                                    }}
                                    className="w-full px-2 py-2 text-xs rounded bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-500/10 dark:text-red-300"
                                  >
                                    X
                                  </button>
                                )}
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                    {!parsedData.isValid ? (
                      <div className="text-xs text-red-600 dark:text-red-400">
                        Structured editor is disabled until raw JSON is valid.
                      </div>
                    ) : null}
                    <div className="border-t border-gray-200 dark:border-gray-700 pt-3">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                        <div>
                          <label className="block mb-1 text-xs font-medium text-gray-700 dark:text-gray-300">
                            Filters JSON
                          </label>
                          <textarea
                            value={filtersText}
                            onChange={(e) => setFiltersText(e.target.value)}
                            onBlur={() => {
                              try {
                                const parsed = JSON.parse(filtersText || "{}");
                                setFilterRows(filtersObjectToRows(parsed));
                                updateSearchData((current) => ({
                                  ...current,
                                  filters: parsed,
                                }));
                              } catch {
                                dispatch(showToast({ message: "Filters JSON is invalid", type: "error" }));
                              }
                            }}
                            rows={6}
                            className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-3 text-sm text-gray-800 outline-none transition placeholder:text-gray-400 focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-white/30"
                            disabled={currentMode === "view"}
                          />
                        </div>
                        <div>
                          <label className="block mb-1 text-xs font-medium text-gray-700 dark:text-gray-300">
                            Request Filters JSON
                          </label>
                          <textarea
                            value={requestFiltersText}
                            onChange={(e) => setRequestFiltersText(e.target.value)}
                            onBlur={() => {
                              try {
                                const parsed = JSON.parse(requestFiltersText || "{}");
                                setRequestFilterRows(requestFiltersObjectToRows(parsed));
                                updateSearchData((current) => ({
                                  ...current,
                                  request_filters: parsed,
                                }));
                              } catch {
                                dispatch(showToast({ message: "Request filters JSON is invalid", type: "error" }));
                              }
                            }}
                            rows={6}
                            className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-3 text-sm text-gray-800 outline-none transition placeholder:text-gray-400 focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-white/30"
                            disabled={currentMode === "view"}
                          />
                        </div>
                      </div>
                      <label className="block mb-1 text-xs font-medium text-gray-700 dark:text-gray-300">
                        Raw Data JSON (Advanced)
                      </label>
                      <textarea
                        id="config"
                        value={
                          typeof rawDataValue === "string"
                            ? rawDataValue
                            : stringifyData(rawDataValue || {})
                        }
                        onChange={(e) => setValue("config", e.target.value, { shouldDirty: true })}
                        rows={10}
                        className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-3 text-sm text-gray-800 outline-none transition placeholder:text-gray-400 focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-white/30"
                        disabled={currentMode === "view"}
                      />
                    </div>
                  </>
                ) : (
                  <textarea
                    id="config"
                    value={
                      typeof rawDataValue === "string"
                        ? rawDataValue
                        : stringifyData(rawDataValue || {})
                    }
                    onChange={(e) => setValue("config", e.target.value, { shouldDirty: true })}
                    rows={currentMode === "view" ? 10 : 12}
                    className="w-full rounded-lg border border-gray-300 bg-transparent px-4 py-3 text-sm text-gray-800 outline-none transition placeholder:text-gray-400 focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-white/30"
                    disabled={currentMode === "view"}
                  />
                )}
              </div>
            </HorizontalField>
          </div>
          {currentMode !== "view" && (
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4 flex items-center gap-2">
              <button
                type="submit"
                className="flex items-center px-4 py-2 text-white bg-brand-500 rounded-md hover:bg-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
              >
                {currentMode === "edit" ? "Update" : "Submit"}
              </button>
              {inline && onCancelInline && (
                <button
                  type="button"
                  onClick={onCancelInline}
                  className="flex items-center px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
                >
                  Cancel
                </button>
              )}
            </div>
          )}
        </form>
      </ComponentCard>

      {currentMode === "view" && data && (
        <div className="mt-4 space-y-0">
          <ScalarCard
            title="Setting Fields"
            icon={<Database size={14} />}
            fields={[
              { label: "name", value: data.name },
              { label: "purpose", value: data.purpose },
              { label: "role", value: data.role },
              { label: "model_name", value: data.model_name },
              { label: "is_active", value: data.is_active },
              { label: "config", value: data.config },
            ]}
            columns={2}
          />
          <BaseModelCards data={data as Record<string, unknown>} />
        </div>
      )}

      {/* Tab Navigation - only show when viewing/editing existing record */}
      {recordData?.id && (
        <>
          <DetailTabs
            entityType="setting_detail"
            activeTab={activeTab}
            onTabChange={setActiveTab}
            standardTabs={["actions", "comments", "documents", "raw"]}
            badges={{
              comments: recordData?.comments?.length,
              documents: recordData?.refs?.links?.document?.length,
            }}
            panelEntityType="setting"
            entityId={recordData.id}
            recordData={recordData}
            isEditing={currentMode !== "view"}
            onRecordChange={setRecordData}
          />
        </>
      )}
    </>
  );
}

export default withDevIdentifier(SettingDetail, 'SettingDetail');

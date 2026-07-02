/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import DataGrid from "@/components/common/DataGrid";
import { useCallback, useEffect, useMemo, useState } from "react";
import { FaPlus, FaEdit, FaEye, FaTrash, FaSyncAlt, FaSave } from "react-icons/fa";
import ComponentCard from "../../../components/common/ComponentCard";
import PageBreadcrumb from "../../../components/common/PageBreadCrumb";
import Input from "../../../components/form/input/InputField";
import Label from "../../../components/form/Label";
import Checkbox from "../../../components/form/input/Checkbox";
import { useDispatch } from "react-redux";
import {
  getModelDetail,
  getRecords,
  getRecord,
  saveRecord,
  deleteRecord,
  getWorkbenchFieldsSetting,
  saveWorkbenchFieldsSetting,
} from "../../../api/wcapi";
import { showToast } from "../../../store/slices/toastSlice";
import { kebabCaseToTitle, safeString } from "./scaffoldUtils";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

export type FieldPreference = {
  list: string[];
  detail: string[];
};

export type ModelScaffoldProps = {
  modelName: string;
  title?: string;
  defaultFields?: FieldPreference;
  hideBreadcrumb?: boolean;
};

type RecordLike = Record<string, any>;

type ModelField = { name: string };

type ModelDetailResponse = {
  model?: {
    fields?: Array<ModelField> | Record<string, any>;
  };
};

const defaultPrefs: FieldPreference = { list: ["id", "name", "code", "status"], detail: [] };

const renderCell = (value: unknown) => {
  if (value === true) {
    return <span className="text-green-600 font-semibold">Yes</span>;
  }
  if (value === false) {
    return <span className="text-red-500 font-semibold">No</span>;
  }
  if (Array.isArray(value)) {
    return <span className="text-xs text-gray-500">[{value.length} items]</span>;
  }
  if (value == null) return "--";
  if (typeof value === "object") {
    return <span className="text-xs text-gray-500">{JSON.stringify(value)}</span>;
  }
  return value as any;
};

const guessFieldType = (field: string, value: unknown): "boolean" | "number" | "json" | "string" => {
  if (typeof value === "boolean") return "boolean";
  if (typeof value === "number") return "number";
  if (Array.isArray(value) || typeof value === "object") return "json";
  if (field.startsWith("is_") || field.startsWith("has_")) return "boolean";
  return "string";
};

function ModelScaffold({
  modelName,
  title,
  defaultFields = defaultPrefs,
  hideBreadcrumb = false,
}: ModelScaffoldProps) {
  const dispatch = useDispatch();

  const [records, setRecords] = useState<RecordLike[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [allFields, setAllFields] = useState<string[]>([]);
  const [fieldPrefs, setFieldPrefs] = useState<FieldPreference>(defaultFields);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [draft, setDraft] = useState<RecordLike>({});
  const [mode, setMode] = useState<"list" | "add" | "edit" | "view">("list");
  const [error, setError] = useState<string | null>(null);

  const pageTitle = title || kebabCaseToTitle(modelName);

  const visibleListFields = useMemo(() => {
    if (fieldPrefs.list.length) {
      return fieldPrefs.list.filter((f) => allFields.includes(f) || f === "id");
    }
    const fallback = allFields.length ? allFields.slice(0, 6) : defaultFields.list;
    return fallback;
  }, [fieldPrefs.list, allFields]);

  const visibleDetailFields = useMemo(() => {
    if (fieldPrefs.detail.length) {
      return fieldPrefs.detail.filter((f) => allFields.includes(f) || f === "id");
    }
    return allFields.length ? allFields : fieldPrefs.list;
  }, [fieldPrefs.detail, allFields, fieldPrefs.list]);

  const loadModel = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const detail = (await getModelDetail(modelName)) as ModelDetailResponse;
      const fieldsRaw = detail?.model?.fields;
      let fields: string[] = [];
      if (Array.isArray(fieldsRaw)) {
        fields = fieldsRaw
          .map((f) => (typeof f === "string" ? f : f?.name))
          .filter((x): x is string => Boolean(x));
      } else if (fieldsRaw && typeof fieldsRaw === "object") {
        fields = Object.keys(fieldsRaw);
      }
      setAllFields(fields);

      const prefs = await getWorkbenchFieldsSetting(modelName);
      if (prefs?.data) {
        setFieldPrefs({
          list: prefs.data.list || defaultFields.list,
          detail: prefs.data.detail || defaultFields.detail,
        });
      } else {
        setFieldPrefs(defaultFields);
      }

      const listResp = await getRecords(modelName);
      const results = Array.isArray((listResp as any)?.results)
        ? (listResp as any).results
        : [];
      setRecords(results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load model");
    } finally {
      setLoading(false);
    }
  }, [modelName, defaultFields]);

  useEffect(() => {
    loadModel();
  }, [loadModel]);

  const refreshRecord = useCallback(
    async (id: number) => {
      try {
        const res = await getRecord(modelName, id);
        const rec = (res as any)?.record || null;
        if (rec) {
          setDraft(rec);
          setSelectedId(id);
        }
      } catch (err) {
        dispatch(
          showToast({
            message: err instanceof Error ? err.message : "Failed to fetch record",
            type: "error",
          })
        );
      }
    },
    [modelName, dispatch]
  );

  const handleRowClick = useCallback(
    (row: RecordLike) => {
      const id = row?.id ?? null;
      setDraft(row);
      setSelectedId(typeof id === "number" ? id : null);
      setMode("view");
    },
    []
  );

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const payload = { ...draft, id: selectedId ?? draft.id };
      const res = await saveRecord(modelName, payload);
      const newId = res?.id || selectedId;
      dispatch(showToast({ message: "Saved successfully", type: "success" }));
      await loadModel();
      if (newId) {
        await refreshRecord(newId);
        setMode("view");
      } else {
        setMode("list");
      }
    } catch (err) {
      dispatch(
        showToast({
          message: err instanceof Error ? err.message : "Save failed",
          type: "error",
        })
      );
    } finally {
      setSaving(false);
    }
  }, [draft, modelName, selectedId, dispatch, loadModel, refreshRecord]);

  const handleDelete = useCallback(async () => {
    if (!selectedId) return;
    try {
      await deleteRecord(modelName, selectedId);
      dispatch(showToast({ message: "Deleted", type: "success" }));
      setMode("list");
      setDraft({});
      setSelectedId(null);
      await loadModel();
    } catch (err) {
      dispatch(
        showToast({
          message: err instanceof Error ? err.message : "Delete failed",
          type: "error",
        })
      );
    }
  }, [modelName, selectedId, dispatch, loadModel]);

  const toggleFieldPref = useCallback(
    async (kind: "list" | "detail", field: string) => {
      const next = {
        ...fieldPrefs,
        [kind]: fieldPrefs[kind].includes(field)
          ? fieldPrefs[kind].filter((f) => f !== field)
          : [...fieldPrefs[kind], field],
      };
      setFieldPrefs(next);
      try {
        await saveWorkbenchFieldsSetting({
          model_name: modelName,
          purpose: "workbench_fields",
          data: next,
        } as any);
      } catch (err) {
        dispatch(
          showToast({
            message: err instanceof Error ? err.message : "Field prefs save failed",
            type: "error",
          })
        );
      }
    },
    [fieldPrefs, modelName, dispatch]
  );

  const columns = useMemo<any[]>(() => {
    const base = visibleListFields.map((field) => ({
      name: kebabCaseToTitle(field),
      selector: (row: RecordLike) => row?.[field],
      sortable: true,
      cell: (row: RecordLike) => renderCell(row?.[field]),
    }));

    base.push({
      name: "Action",
      cell: (row) => (
        <div className="flex gap-3">
          <button onClick={() => handleRowClick(row)} title="View">
            <FaEye className="text-blue-600 hover:scale-110 transition" />
          </button>
          <button
            onClick={() => {
              setDraft(row);
              setSelectedId(typeof row.id === "number" ? row.id : null);
              setMode("edit");
            }}
            title="Edit"
          >
            <FaEdit className="text-green-600 hover:scale-110 transition" />
          </button>
        </div>
      ),
      ignoreRowClick: true,
      allowOverflow: true,
      button: true,
    });

    return base;
  }, [visibleListFields, handleRowClick]);

  const renderFieldInput = (field: string) => {
    const value = draft?.[field];
    const type = guessFieldType(field, value);
    const disabled = mode === "view" || field === "id";

    if (type === "boolean") {
      return (
        <Checkbox
          id={`${field}`}
          label={field}
          checked={!!value}
          disabled={disabled}
          onChange={(val: boolean) =>
            setDraft((prev) => ({ ...prev, [field]: val }))
          }
        />
      );
    }

    if (type === "number") {
      return (
        <Input
          type="number"
          id={field}
          value={value ?? ""}
          disabled={disabled}
          onChange={(e) =>
            setDraft((prev) => ({ ...prev, [field]: Number(e.target.value) }))
          }
        />
      );
    }

    if (type === "json") {
      return (
        <textarea
          id={field}
          className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm dark:bg-dark-900"
          rows={3}
          disabled={disabled}
          value={value ? JSON.stringify(value, null, 2) : ""}
          onChange={(e) => {
            let parsed: any = e.target.value;
            try {
              parsed = JSON.parse(e.target.value || "null");
            } catch {
              parsed = e.target.value;
            }
            setDraft((prev) => ({ ...prev, [field]: parsed }));
          }}
        />
      );
    }

    return (
      <Input
        type="text"
        id={field}
        value={value ?? ""}
        disabled={disabled}
        onChange={(e) => setDraft((prev) => ({ ...prev, [field]: e.target.value }))}
      />
    );
  };

  const listSection = (
    <ComponentCard>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">{pageTitle} List</h3>
          <p className="text-xs text-gray-500">Model: {modelName}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => {
              setMode("add");
              setSelectedId(null);
              setDraft({});
            }}
            className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600"
          >
            <FaPlus />
            Add
          </button>
          <button
            onClick={loadModel}
            className="flex items-center gap-2 px-3 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
            title="Refresh"
          >
            <FaSyncAlt />
          </button>
        </div>
      </div>
      {error && <div className="mb-2 text-sm text-red-600">{error}</div>}
      <DataGrid
        data={records}
        columns={columns}
        loading={loading}
        onRowClicked={handleRowClick}
        title={`${pageTitle} Records`}
        exportFileName={modelName}
        searchPlaceholder={`Search ${pageTitle}...`}
        noDataMessage={`No ${pageTitle} records`}
        enableSelection
        customActions={
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-500">Visible fields:</span>
            <div className="flex flex-wrap gap-2">
              {visibleListFields.map((f) => (
                <span key={f} className="rounded bg-gray-100 px-2 py-1 text-xs text-gray-700">
                  {f}
                </span>
              ))}
            </div>
          </div>
        }
      />
    </ComponentCard>
  );

  const detailSection = (
    <ComponentCard>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">{mode === "add" ? "Add" : mode === "edit" ? "Edit" : "View"} {pageTitle}</h3>
          {selectedId && <p className="text-xs text-gray-500">ID: {selectedId}</p>}
        </div>
        <div className="flex gap-2">
          {mode !== "view" && (
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-60"
            >
              <FaSave />
              {saving ? "Saving..." : "Save"}
            </button>
          )}
          {mode === "view" && (
            <button
              onClick={() => setMode("edit")}
              className="flex items-center gap-2 px-3 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
            >
              <FaEdit />
              Edit
            </button>
          )}
          {selectedId && (
            <button
              onClick={handleDelete}
              className="flex items-center gap-2 px-3 py-2 text-white bg-red-500 rounded-md hover:bg-red-600"
            >
              <FaTrash />
              Delete
            </button>
          )}
          <button
            onClick={() => {
              setMode("list");
              setDraft({});
              setSelectedId(null);
            }}
            className="flex items-center gap-2 px-3 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
          >
            Back
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {visibleDetailFields.map((field) => (
          <div key={field} className="flex flex-col gap-1">
            <Label htmlFor={field}>{field}</Label>
            {renderFieldInput(field)}
          </div>
        ))}
      </div>

      <div className="mt-6">
        <h4 className="text-sm font-semibold mb-2">Field visibility</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded border p-3">
            <p className="text-xs font-semibold mb-2">List fields</p>
            <div className="flex flex-wrap gap-2">
              {allFields.map((f) => (
                <button
                  key={`list-${f}`}
                  type="button"
                  onClick={() => toggleFieldPref("list", f)}
                  className={`px-2 py-1 rounded text-xs ${
                    fieldPrefs.list.includes(f)
                      ? "bg-blue-100 text-blue-700"
                      : "bg-gray-100 text-gray-600"
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>
          <div className="rounded border p-3">
            <p className="text-xs font-semibold mb-2">Detail fields</p>
            <div className="flex flex-wrap gap-2">
              {allFields.map((f) => (
                <button
                  key={`detail-${f}`}
                  type="button"
                  onClick={() => toggleFieldPref("detail", f)}
                  className={`px-2 py-1 rounded text-xs ${
                    fieldPrefs.detail.includes(f)
                      ? "bg-green-100 text-green-700"
                      : "bg-gray-100 text-gray-600"
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </ComponentCard>
  );

  return (
    <div className="space-y-6">
      {!hideBreadcrumb && <PageBreadcrumb pageTitle={`${pageTitle} Scaffold`} />}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {mode === "list" ? listSection : detailSection}
        {mode === "list" ? (
          <ComponentCard>
            <h4 className="text-sm font-semibold mb-2">Detail preview</h4>
            <div className="space-y-2 text-sm">
              {visibleDetailFields.slice(0, 12).map((f) => (
                <div key={`preview-${f}`} className="flex items-center justify-between border-b pb-1">
                  <span className="text-gray-600">{f}</span>
                  <span className="text-gray-800 font-medium">{safeString(draft?.[f])}</span>
                </div>
              ))}
            </div>
          </ComponentCard>
        ) : (
          <div className="hidden lg:block">{listSection}</div>
        )}
      </div>
    </div>
  );
}

export default withDevIdentifier(ModelScaffold, 'ModelScaffold');

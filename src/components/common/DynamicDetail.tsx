/**
 * DynamicDetail — Data-driven form renderer.
 *
 * Reads a layout definition (JSON) and renders a form.
 * Users can toggle into "arrange" mode to drag rows, add/remove fields.
 * Layout saves to project.metadata or a Setting record.
 *
 * Layout format:
 * {
 *   rows: [
 *     { fields: ["action"], cols: 1 },
 *     { fields: ["assigned_to", "status"], cols: 2 },
 *     { fields: ["priority", "difficulty", "percent_complete"], cols: 3 },
 *     { fields: ["dt_start", "dt_deadline", "dt_completed"], cols: 3 },
 *   ]
 * }
 */
import { useState, useCallback, useEffect, useRef } from "react";
import { getRecord, saveRecord } from "../../api/wcapi";
import { patchAction } from "../../api/userProfile";
import { showToast } from "../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

// ── Field type registry ─────────────────────────────────────────────
// Maps field names to their widget config. Extend as needed.

interface FieldConfig {
  type: "text" | "select" | "date" | "number" | "readonly" | "json-text";
  label?: string;
  options?: { value: string | number; label: string }[];
  min?: number;
  max?: number;
}

const ACTION_FIELDS: Record<string, FieldConfig> = {
  action: { type: "json-text", label: "action" },
  description: { type: "json-text", label: "description" },
  assigned_to: { type: "text", label: "assigned_to" },
  status: {
    type: "select", label: "status",
    options: [
      { value: "", label: "—" },
      { value: "open", label: "Open" },
      { value: "In progress", label: "In Progress" },
      { value: "active", label: "Active" },
      { value: "completed", label: "Completed" },
      { value: "on hold", label: "On Hold" },
      { value: "blocked", label: "Blocked" },
      { value: "cancelled", label: "Cancelled" },
    ],
  },
  priority: {
    type: "select", label: "priority",
    options: [
      { value: 1, label: "Low (1)" },
      { value: 2, label: "Medium (2)" },
      { value: 3, label: "High (3)" },
      { value: 4, label: "Critical (4)" },
    ],
  },
  difficulty: {
    type: "select", label: "difficulty",
    options: [
      { value: 1, label: "Easy (1)" },
      { value: 4, label: "Average (4)" },
      { value: 8, label: "Hard (8)" },
      { value: 13, label: "Complex (13)" },
      { value: 21, label: "Expert (21)" },
    ],
  },
  percent_complete: {
    type: "select", label: "% complete",
    options: [
      { value: 0, label: "0%" },
      { value: 20, label: "20%" },
      { value: 50, label: "50%" },
      { value: 70, label: "70%" },
      { value: 100, label: "100%" },
    ],
  },
  dt_start: { type: "date", label: "dt_start" },
  dt_deadline: { type: "date", label: "dt_deadline" },
  dt_completed: { type: "date", label: "dt_completed" },
  project_name: { type: "readonly", label: "project" },
  kanban_column: { type: "text", label: "kanban_column" },
  ida: { type: "readonly", label: "ida" },
};

// Default layout for actions
const DEFAULT_ACTION_LAYOUT = {
  rows: [
    { fields: ["action"], cols: 1 },
    { fields: ["description"], cols: 1 },
    { fields: ["assigned_to", "status"], cols: 2 },
    { fields: ["priority", "difficulty", "percent_complete"], cols: 3 },
    { fields: ["dt_start", "dt_deadline", "dt_completed"], cols: 3 },
    { fields: ["project_name"], cols: 1 },
  ],
};

// Model field registries — add more models here
const FIELD_REGISTRIES: Record<string, Record<string, FieldConfig>> = {
  action: ACTION_FIELDS,
};

const DEFAULT_LAYOUTS: Record<string, typeof DEFAULT_ACTION_LAYOUT> = {
  action: DEFAULT_ACTION_LAYOUT,
};

// ── Styles ──────────────────────────────────────────────────────────

const iClass = "w-full px-1.5 py-0.5 text-xs border border-gray-300 rounded bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-60";
const lClass = "text-[11px] text-gray-500 dark:text-gray-400 font-mono mb-0.5";

// ── Component ───────────────────────────────────────────────────────

interface DynamicDetailProps {
  modelName: string;
  recordId: string | number;
  layout?: any;
  onLayoutChange?: (layout: any) => void;
  onClose?: () => void;
  onSaved?: () => void;
}

function DynamicDetail({
  modelName,
  recordId,
  layout: layoutProp,
  onLayoutChange,
  onClose,
  onSaved,
}: DynamicDetailProps) {
  const dispatch = useDispatch();
  const fieldRegistry = FIELD_REGISTRIES[modelName] || {};
  const defaultLayout = DEFAULT_LAYOUTS[modelName] || { rows: [] };

  const [data, setData] = useState<Record<string, any> | null>(null);
  const [values, setValues] = useState<Record<string, any>>({});
  const [editing, setEditing] = useState(false);
  const [arranging, setArranging] = useState(false);
  const [saving, setSaving] = useState(false);
  const [layout, setLayout] = useState(layoutProp || defaultLayout);
  const [layoutReportId, setLayoutReportId] = useState<number | null>(null);
  const [fontScale, setFontScale] = useState(0);
  const [dragRow, setDragRow] = useState<number | null>(null);

  const fontSize = 12 + fontScale;

  // Load form layout from Report record (output_type=screen, category=form)
  useEffect(() => {
    if (layoutProp) return; // prop overrides server layout
    const cacheKey = `form_layout_${modelName}`;
    const cached = sessionStorage.getItem(cacheKey);
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        setLayout(parsed.config);
        setLayoutReportId(parsed.id);
        return;
      } catch {}
    }
    // Fetch from server
    import("../../api/wcapi").then(({ getRecords }) => {
      getRecords("report", {
        model_name: modelName,
        output_type: "screen",
        category: "form",
        is_active: true,
        limit: 1,
      }).then((resp: any) => {
        const records = resp?.data || resp?.records || [];
        const arr = Array.isArray(records) ? records : [];
        if (arr.length > 0 && arr[0].config?.rows) {
          setLayout(arr[0].config);
          setLayoutReportId(arr[0].id);
          sessionStorage.setItem(cacheKey, JSON.stringify({
            id: arr[0].id,
            version: arr[0].version,
            config: arr[0].config,
          }));
        }
      }).catch(() => {});
    });
  }, [modelName, layoutProp]);

  // Load record
  useEffect(() => {
    if (!recordId) return;
    getRecord(modelName, Number(recordId)).then((resp: any) => {
      const r = resp?.record || resp;
      if (!r) return;
      setData(r);
      // Extract form values
      const v: Record<string, any> = {};
      for (const key of Object.keys(fieldRegistry)) {
        const cfg = fieldRegistry[key];
        if (cfg.type === "json-text") {
          v[key] = r[key]?.en || "";
        } else if (cfg.type === "date") {
          const ms = r[key];
          if (ms && typeof ms === "number") {
            try { v[key] = new Date(ms).toISOString().split("T")[0]; } catch { v[key] = ""; }
          } else { v[key] = ""; }
        } else if (key === "assigned_to") {
          const at = r[key];
          v[key] = typeof at === "string" ? at :
            Array.isArray(at) ? (at[0]?.name || "") :
            at?.lead || "";
        } else {
          v[key] = r[key] ?? "";
        }
      }
      setValues(v);
    }).catch(() => {});
  }, [modelName, recordId]);

  // Save handler
  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const payload: Record<string, any> = { model_name: modelName, id: String(recordId) };
      for (const [key, cfg] of Object.entries(fieldRegistry)) {
        if (cfg.type === "readonly") continue;
        const val = values[key];
        if (cfg.type === "json-text") {
          payload[key] = { mode: "update", value: { en: val } };
        } else if (cfg.type === "date" && val) {
          payload[key] = { mode: "update", value: new Date(val).getTime() };
        } else if (cfg.type === "select" || cfg.type === "number") {
          payload[key] = { mode: "update", value: typeof val === "string" ? (isNaN(Number(val)) ? val : Number(val)) : val };
        } else {
          payload[key] = { mode: "update", value: val };
        }
      }
      await patchAction(payload);
      dispatch(showToast({ message: "Saved", type: "success" }));
      setEditing(false);
      onSaved?.();
    } catch (e: any) {
      dispatch(showToast({ message: e.message || "Save failed", type: "error" }));
    } finally {
      setSaving(false);
    }
  }, [modelName, recordId, values, fieldRegistry, dispatch, onSaved]);

  // Arrange mode handlers
  const handleDragStart = (idx: number) => setDragRow(idx);
  const handleDragOver = (e: React.DragEvent, idx: number) => {
    e.preventDefault();
    if (dragRow === null || dragRow === idx) return;
    const rows = [...layout.rows];
    const [moved] = rows.splice(dragRow, 1);
    rows.splice(idx, 0, moved);
    setLayout({ ...layout, rows });
    setDragRow(idx);
  };
  const handleDragEnd = () => {
    setDragRow(null);
    onLayoutChange?.(layout);
  };

  const addFieldRow = (fieldName: string) => {
    setLayout((prev: any) => ({
      ...prev,
      rows: [...prev.rows, { fields: [fieldName], cols: 1 }],
    }));
  };

  const removeRow = (idx: number) => {
    setLayout((prev: any) => ({
      ...prev,
      rows: prev.rows.filter((_: any, i: number) => i !== idx),
    }));
  };

  // Field renderer
  const renderField = (fieldName: string, disabled: boolean) => {
    const cfg = fieldRegistry[fieldName];
    if (!cfg) return <span className="text-xs text-red-400">{fieldName}?</span>;

    const val = values[fieldName] ?? "";

    if (cfg.type === "readonly") {
      return <span className="text-xs text-gray-600 dark:text-gray-300">{String(val || "—")}</span>;
    }
    if (cfg.type === "select" && cfg.options) {
      return (
        <select value={val} onChange={e => setValues(v => ({ ...v, [fieldName]: e.target.value }))}
          disabled={disabled} className={iClass}>
          {cfg.options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      );
    }
    if (cfg.type === "date") {
      return <input type="date" value={val} onChange={e => setValues(v => ({ ...v, [fieldName]: e.target.value }))}
        disabled={disabled} className={iClass} />;
    }
    if (cfg.type === "number") {
      return <input type="number" value={val} min={cfg.min} max={cfg.max}
        onChange={e => setValues(v => ({ ...v, [fieldName]: Number(e.target.value) }))}
        disabled={disabled} className={iClass} />;
    }
    // text / json-text
    return <input type="text" value={val} onChange={e => setValues(v => ({ ...v, [fieldName]: e.target.value }))}
      disabled={disabled} className={iClass} />;
  };

  if (!data) return <div className="py-4 text-center text-xs text-gray-400">Loading...</div>;

  const disabled = !editing;
  const usedFields = new Set(layout.rows.flatMap((r: any) => r.fields));
  const availableFields = Object.keys(fieldRegistry).filter(f => !usedFields.has(f));

  return (
    <div className="space-y-1.5" style={{ fontSize: `${fontSize}px` }}>
      {/* Toolbar */}
      <div className="flex items-center justify-between pb-1 border-b border-gray-200 dark:border-gray-700">
        <span className="font-mono text-gray-400" style={{ fontSize: "11px" }}>
          {data.ida || `${modelName}:${recordId}`}
        </span>
        <div className="flex items-center gap-1">
          <button onClick={() => setFontScale(s => s - 1)}
            className="rounded border border-gray-300 px-1 py-0.5 text-[10px] text-gray-500 hover:bg-gray-100 dark:border-gray-600">A-</button>
          <button onClick={() => setFontScale(s => s + 1)}
            className="rounded border border-gray-300 px-1 py-0.5 text-[10px] text-gray-500 hover:bg-gray-100 dark:border-gray-600">A+</button>
          <button onClick={() => {
              if (arranging) {
                // Save layout back to Report record
                if (layoutReportId) {
                  saveRecord("report", {
                    model_name: "report",
                    id: String(layoutReportId),
                    config: { mode: "update", value: layout },
                  }).then(() => {
                    sessionStorage.removeItem(`form_layout_${modelName}`);
                    dispatch(showToast({ message: "Layout saved", type: "success" }));
                  }).catch(() => {});
                }
              }
              setArranging(!arranging);
            }}
            className={`rounded border px-1.5 py-0.5 text-[10px] ${
              arranging ? "border-amber-400 bg-amber-50 text-amber-700" : "border-gray-300 text-gray-500 hover:bg-gray-100 dark:border-gray-600"
            }`}
            title={arranging ? "Save layout and exit arrange mode" : "Arrange form layout"}
          >{arranging ? "Done" : "⚙"}</button>
          {editing ? (
            <>
              <button onClick={handleSave} disabled={saving}
                className="rounded bg-blue-600 px-2 py-0.5 text-[11px] text-white hover:bg-blue-700 disabled:opacity-50">
                {saving ? "..." : "Save"}</button>
              <button onClick={() => setEditing(false)}
                className="rounded border border-gray-300 px-2 py-0.5 text-[11px] dark:border-gray-600">Cancel</button>
            </>
          ) : (
            <button onClick={() => setEditing(true)}
              className="rounded border border-gray-300 px-2 py-0.5 text-[11px] dark:border-gray-600">Edit</button>
          )}
        </div>
      </div>

      {/* Dynamic rows */}
      {layout.rows.map((row: any, idx: number) => (
        <div
          key={idx}
          draggable={arranging}
          onDragStart={() => handleDragStart(idx)}
          onDragOver={(e) => handleDragOver(e, idx)}
          onDragEnd={handleDragEnd}
          className={`${arranging ? "border border-dashed border-amber-300 rounded px-1 py-0.5 cursor-move" : ""} ${
            dragRow === idx ? "opacity-50" : ""
          }`}
        >
          {arranging && (
            <div className="flex items-center justify-between mb-0.5">
              <span className="text-[9px] text-amber-500">{row.fields.join(" · ")}</span>
              <button onClick={() => removeRow(idx)} className="text-[9px] text-red-400 hover:text-red-600">✕</button>
            </div>
          )}
          <div className={`grid gap-1.5 ${
            row.cols === 3 ? "grid-cols-3" :
            row.cols === 2 ? "grid-cols-2" :
            "grid-cols-1"
          }`}>
            {row.fields.map((fieldName: string) => (
              <div key={fieldName}>
                <div className={lClass}>{fieldRegistry[fieldName]?.label || fieldName}</div>
                {renderField(fieldName, disabled)}
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Add field (arrange mode) */}
      {arranging && availableFields.length > 0 && (
        <div className="border-t border-amber-200 pt-1.5">
          <div className="text-[9px] text-amber-500 mb-1">Add field:</div>
          <div className="flex flex-wrap gap-1">
            {availableFields.map(f => (
              <button key={f} onClick={() => addFieldRow(f)}
                className="rounded border border-amber-300 bg-amber-50 px-1.5 py-0.5 text-[10px] text-amber-700 hover:bg-amber-100">
                + {f}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Open full detail */}
      <div className="border-t border-gray-200 pt-1.5 dark:border-gray-700">
        <button
          onClick={() => window.open(`/core/${modelName}s/detail/${recordId}`, '_blank')}
          className="w-full rounded border border-gray-300 py-1 text-[11px] text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
        >
          Open Full Detail
        </button>
      </div>
    </div>
  );
}

export default withDevIdentifier(DynamicDetail, 'DynamicDetail');
export { DynamicDetail, DEFAULT_ACTION_LAYOUT, FIELD_REGISTRIES, DEFAULT_LAYOUTS };
export type { FieldConfig };

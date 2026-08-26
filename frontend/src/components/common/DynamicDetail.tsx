/**
 * DynamicDetail — Data-driven form renderer.
 *
 * Reads a layout definition (JSON) from a Report record and renders a form.
 * Users can toggle into "arrange" mode to drag rows, add/remove fields.
 * Layout saves back to the Report record.
 *
 * Report config format:
 * {
 *   fields: {
 *     "ida":           { type: "readonly", label: "ID" },
 *     "name":          { type: "text", label: "Name" },
 *     "config.po_num": { type: "text", label: "PO #" },    // dot-notation into JSON
 *     "refs.links.customer": { type: "readonly", label: "Customer" },
 *   },
 *   rows: [
 *     { fields: ["ida", "name"], cols: 2 },
 *     { fields: ["config.po_num", "refs.links.customer"], cols: 2 },
 *   ]
 * }
 *
 * Field configs can come from: Report config.fields (data-driven, preferred),
 * hardcoded FIELD_REGISTRIES (legacy), or auto-inferred from record data.
 */
import { useState, useCallback, useEffect, useMemo } from "react";
import { getRecord, saveRecord } from "../../api/wcapi";
import { getWidget } from "../widgets";
import { showToast } from "../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import { FileUploadPanel } from './FileUploadPanel';
import { ContactPanel, normalizeRefsLinksContact } from '@/apps/common/components/panels/ContactPanel';
import type { RefContact } from '@/apps/common/components/panels/ContactPanel';
import { LinkedRecordsPanel } from '@/apps/common/components/panels/LinkedRecordsPanel';
import { getModelNames } from '@/api/wcapi';

// ── Field type registry ─────────────────────────────────────────────

interface FieldConfig {
  type: "text" | "select" | "date" | "number" | "readonly" | "json-text" | "currency" | "checkbox" | "textarea";
  label?: string;
  options?: { value: string | number; label: string }[];
  min?: number;
  max?: number;
  path?: string; // dot-notation path into record (e.g. "config.po_num")
}

// ── Dot-notation helpers ────────────────────────────────────────────

function getNestedValue(obj: any, path: string): any {
  if (!obj || !path) return undefined;
  const parts = path.split(".");
  let cur = obj;
  for (const p of parts) {
    if (cur == null || typeof cur !== "object") return undefined;
    cur = cur[p];
  }
  return cur;
}

function setNestedValue(obj: any, path: string, value: any): any {
  const parts = path.split(".");
  const result = { ...obj };
  let cur = result;
  for (let i = 0; i < parts.length - 1; i++) {
    const p = parts[i];
    cur[p] = cur[p] != null && typeof cur[p] === "object" ? { ...cur[p] } : {};
    cur = cur[p];
  }
  cur[parts[parts.length - 1]] = value;
  return result;
}

// Auto-infer field type from a data value
function inferFieldType(value: any): FieldConfig["type"] {
  if (value == null) return "text";
  if (typeof value === "boolean") return "checkbox";
  if (typeof value === "number") {
    // Large integers are likely epoch timestamps
    if (value > 1_000_000_000_000 && value < 2_000_000_000_000) return "date";
    return "number";
  }
  if (typeof value === "object" && value.en !== undefined) return "json-text";
  if (typeof value === "object") return "readonly";
  if (typeof value === "string" && value.length > 200) return "textarea";
  return "text";
}

// ── Hardcoded field registries ──────────

const ACTION_FIELDS: Record<string, FieldConfig> = {
  action: { type: "json-text", label: "action" },
  description: { type: "json-text", label: "description" },
  assigned_to: { type: "contact-select", label: "assigned_to" },
  status: {
    type: "select", label: "status",
    options: [
      { value: "", label: "—" },
      { value: "open", label: "Open" },
      { value: "in_progress", label: "In Progress" },
      { value: "complete", label: "Complete" },
      { value: "on_hold", label: "On Hold" },
      { value: "cancelled", label: "Cancelled" },
    ],
  },
  priority: {
    type: "select", label: "priority",
    options: [
      { value: 1, label: "1 - Highest" },
      { value: 2, label: "2 - High" },
      { value: 3, label: "3 - Medium" },
      { value: 4, label: "4 - Normal" },
      { value: 5, label: "5 - Low" },
      { value: 6, label: "6 - Lowest" },
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
    type: "select", label: "%_complete",
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
  project_name: { type: "readonly", label: "project_name" },
  kanban_column: { type: "text", label: "kanban_column" },
  ida: { type: "readonly", label: "ida" },
};

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

// Legacy hardcoded registries — Report config.fields takes precedence
const FIELD_REGISTRIES: Record<string, Record<string, FieldConfig>> = {
  action: ACTION_FIELDS,
};

const DEFAULT_LAYOUTS: Record<string, typeof DEFAULT_ACTION_LAYOUT> = {
  action: DEFAULT_ACTION_LAYOUT,
};

// ── Styles ──────────────────────────────────────────────────────────

const iClass = "w-full px-1.5 py-0.5 border border-gray-300 rounded bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-60 text-[inherit]";
const lClass = "text-gray-500 dark:text-gray-400 font-mono mb-0.5 text-[0.85em]";

// ── Component ───────────────────────────────────────────────────────

export interface DynamicDetailActions {
  save: () => void;
  cancel: () => void;
  startEdit: () => void;
  fontUp: () => void;
  fontDown: () => void;
  setFontSize: (size: number) => void;
  fontSize: number;
  editing: boolean;
  saving: boolean;
  ida: string;
}

interface DynamicDetailProps {
  modelName: string;
  recordId: string | number;
  layout?: any;
  onLayoutChange?: (layout: any) => void;
  onClose?: () => void;
  onSaved?: () => void;
  hideToolbar?: boolean;
  actionsRef?: React.MutableRefObject<DynamicDetailActions | null>;
  onActionsReady?: () => void;
}

function DynamicDetail({
  modelName,
  recordId,
  layout: layoutProp,
  onLayoutChange,
  onClose,
  onSaved,
  hideToolbar,
  actionsRef,
  onActionsReady,
}: DynamicDetailProps) {
  const dispatch = useDispatch();
  const legacyRegistry = FIELD_REGISTRIES[modelName] || {};
  const defaultLayout = DEFAULT_LAYOUTS[modelName] || { rows: [] };

  const [data, setData] = useState<Record<string, any> | null>(null);
  const [values, setValues] = useState<Record<string, any>>({});
  const [editing, setEditing] = useState(!!hideToolbar);
  const [arranging, setArranging] = useState(false);
  const [saving, setSaving] = useState(false);
  const [reportConfig, setReportConfig] = useState<any>(null);
  const [layout, setLayout] = useState(layoutProp || defaultLayout);
  const [layoutReportId, setLayoutReportId] = useState<number | null>(null);
  const [fontScale, setFontScale] = useState(0);
  const [dragRow, setDragRow] = useState<number | null>(null);
  const [linkedContacts, setLinkedContacts] = useState<RefContact[]>([]);
  const [linkedPanelModels, setLinkedPanelModels] = useState<string[]>([]);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [showModelPicker, setShowModelPicker] = useState(false);

  const fontSize = 12 + fontScale;

  // Standard panels always shown (even if empty) — besides contacts which uses ContactPanel
  const STANDARD_PANELS = ['action', 'touch', 'document'];

  // Models that use specialized panels (ContactPanel handles contacts)
  const SPECIALIZED = ['contact'];

  // Load available model names for "+ Link..." selector
  useEffect(() => {
    getModelNames().then((res: any) => {
      const names: string[] = Array.isArray(res?.model_names) ? res.model_names : [];
      setAvailableModels(names.sort());
    }).catch(() => {});
  }, []);

  // Self-discover panels from refs.links keys + standard panels
  useEffect(() => {
    if (!data) return;
    const refsLinks = data?.refs?.links || {};
    const discoveredKeys = Object.keys(refsLinks).filter(k =>
      !SPECIALIZED.includes(k)
    );
    // Merge: standard panels + discovered keys (deduplicated, standard first)
    const merged = [...STANDARD_PANELS];
    for (const k of discoveredKeys) {
      if (!merged.includes(k)) merged.push(k);
    }
    setLinkedPanelModels(merged);
  }, [data, modelName]);

  // Merged field registry: Report config.fields > legacy hardcoded > auto-inferred
  const fieldRegistry = useMemo(() => {
    const serverFields: Record<string, FieldConfig> = reportConfig?.fields || {};
    const merged = { ...legacyRegistry, ...serverFields };
    // Auto-infer any fields referenced in layout rows but missing from registry
    if (data && layout?.rows) {
      for (const row of layout.rows) {
        for (const fieldName of (row.fields || [])) {
          if (!merged[fieldName]) {
            const val = fieldName.includes(".")
              ? getNestedValue(data, fieldName)
              : data[fieldName];
            merged[fieldName] = {
              type: inferFieldType(val),
              label: fieldName.split(".").pop() || fieldName,
            };
          }
        }
      }
    }
    return merged;
  }, [legacyRegistry, reportConfig, data, layout]);

  // Load form layout from Report record (output_type=screen, category=form)
  useEffect(() => {
    if (layoutProp) return;
    const cacheKey = `form_layout_${modelName}`;
    const cached = sessionStorage.getItem(cacheKey);
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        setReportConfig(parsed.config);
        if (parsed.config?.rows) setLayout(parsed.config);
        setLayoutReportId(parsed.id);
        return;
      } catch {}
    }
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
        if (arr.length > 0 && arr[0].config) {
          const cfg = arr[0].config;
          setReportConfig(cfg);
          if (cfg.rows) setLayout(cfg);
          setLayoutReportId(arr[0].id);
          sessionStorage.setItem(cacheKey, JSON.stringify({
            id: arr[0].id,
            version: arr[0].version,
            config: cfg,
          }));
        }
      }).catch(() => {});
    });
  }, [modelName, layoutProp]);

  // Extract a form value from record data using field config
  const extractValue = useCallback((fieldName: string, cfg: FieldConfig, record: any): any => {
    const path = cfg.path || fieldName;
    const raw = path.includes(".") ? getNestedValue(record, path) : record[path];
    if (cfg.type === "json-text") return raw?.en || "";
    if (cfg.type === "date") {
      if (raw && typeof raw === "number" && raw > 0) {
        try {
          // Convert epoch ms to local date for input[type=date]
          const d = new Date(raw < 1e12 ? raw * 1000 : raw);
          const y = d.getFullYear();
          const m = String(d.getMonth() + 1).padStart(2, '0');
          const day = String(d.getDate()).padStart(2, '0');
          return `${y}-${m}-${day}`;
        } catch { return ""; }
      }
      return "";
    }
    if (cfg.type === "checkbox") return !!raw;
    if (cfg.type === "readonly" && typeof raw === "object" && raw !== null) {
      return JSON.stringify(raw);
    }
    return raw ?? "";
  }, []);

  // Load record
  useEffect(() => {
    if (!recordId) return;
    getRecord(modelName, Number(recordId)).then((resp: any) => {
      const r = resp?.record || resp;
      if (!r) return;
      setData(r);
      const contacts = r?.refs?.links?.contact || [];
      setLinkedContacts(normalizeRefsLinksContact(contacts));
    }).catch(() => {});
  }, [modelName, recordId]);

  // Extract form values when data or field registry changes
  useEffect(() => {
    if (!data) return;
    const v: Record<string, any> = {};
    for (const [key, cfg] of Object.entries(fieldRegistry)) {
      v[key] = extractValue(key, cfg, data);
    }
    setValues(v);
  }, [data, fieldRegistry, extractValue]);

  // Save handler — uses generic saveRecord for all models
  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const payload: Record<string, any> = { model_name: modelName, id: String(recordId) };
      for (const [key, cfg] of Object.entries(fieldRegistry)) {
        if (cfg.type === "readonly") continue;
        const val = values[key];
        const path = cfg.path || key;
        if (path.includes(".")) {
          // Nested JSON field — build atomic update for the top-level key
          const parts = path.split(".");
          const topKey = parts[0];
          const subPath = parts.slice(1).join(".");
          if (!payload[topKey] || typeof payload[topKey] !== "object" || !payload[topKey].mode) {
            payload[topKey] = { mode: "update", value: data?.[topKey] || {} };
          }
          payload[topKey].value = setNestedValue(payload[topKey].value, subPath,
            cfg.type === "date" && val ? new Date(val).getTime() : val);
        } else if (cfg.type === "json-text") {
          payload[key] = { mode: "update", value: { en: val } };
        } else if (cfg.type === "date" && val) {
          payload[key] = { mode: "update", value: new Date(val).getTime() };
        } else if (cfg.type === "contact-select") {
          // assigned_to is an array of {id, name} — send as-is
          payload[key] = { mode: "update", value: Array.isArray(val) ? val : [] };
        } else if (cfg.type === "select" || cfg.type === "number" || cfg.type === "currency") {
          payload[key] = { mode: "update", value: typeof val === "string" ? (isNaN(Number(val)) ? val : Number(val)) : val };
        } else if (cfg.type === "checkbox") {
          payload[key] = { mode: "update", value: !!val };
        } else {
          payload[key] = { mode: "update", value: val };
        }
      }
      await saveRecord(modelName, payload);
      dispatch(showToast({ message: "Saved", type: "success" }));
      setEditing(false);
      onSaved?.();
    } catch (e: any) {
      dispatch(showToast({ message: e.message || "Save failed", type: "error" }));
    } finally {
      setSaving(false);
    }
  }, [modelName, recordId, values, fieldRegistry, data, dispatch, onSaved]);

  // Expose actions to parent via ref
  useEffect(() => {
    if (!actionsRef) return;
    actionsRef.current = {
      save: () => { void handleSave(); },
      cancel: () => setEditing(false),
      startEdit: () => setEditing(true),
      fontUp: () => setFontScale(s => s + 1),
      fontDown: () => setFontScale(s => s - 1),
      setFontSize: (size: number) => setFontScale(size - 12),
      fontSize,
      editing,
      saving,
      ida: data?.ida || `${modelName}:${recordId}`,
    };
    onActionsReady?.();
  }, [actionsRef, handleSave, editing, saving, data, modelName, recordId, onActionsReady, fontSize]);

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

  // Field renderer — uses merged registry (server + legacy + auto-inferred)
  const renderField = (fieldName: string, disabled: boolean) => {
    const cfg = fieldRegistry[fieldName];
    if (!cfg) {
      // Last resort: show raw value as readonly
      const raw = data ? (fieldName.includes(".") ? getNestedValue(data, fieldName) : data[fieldName]) : undefined;
      return <span className="text-xs text-gray-500">{raw != null ? String(raw) : "—"}</span>;
    }

    const Widget = getWidget(cfg.type);
    return (
      <Widget
        name={fieldName}
        value={values[fieldName] ?? ""}
        onChange={(v: any) => setValues(prev => ({ ...prev, [fieldName]: v }))}
        disabled={disabled}
        options={cfg.options}
        min={cfg.min}
        max={cfg.max}
        record={data || undefined}
      />
    );
  };

  if (!data) return <div className="py-4 text-center text-xs text-gray-400">Loading...</div>;

  const disabled = !editing;
  const usedFields = new Set(layout.rows.flatMap((r: any) => r.fields));
  const availableFields = Object.keys(fieldRegistry).filter(f => !usedFields.has(f));

  return (
    <div className="space-y-1.5" style={{ fontSize: `${fontSize}px` }}>
      {/* Toolbar — hidden when parent controls it via actionsRef */}
      {!hideToolbar && (
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
      )}

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
            {row.fields.map((fieldName: string) => {
              const cfg = fieldRegistry[fieldName];
              const isSelect = cfg?.type === 'select' && cfg?.options?.length;
              const isContactSelect = cfg?.type === 'contact-select';
              const label = cfg?.label || fieldName;

              // Select fields: colored label left, select control right
              if (isSelect) {
                const currentOpt = cfg.options.find((o: any) => String(o.value) === String(values[fieldName]));
                const displayText = currentOpt?.label || values[fieldName] || '—';
                return (
                  <div key={fieldName}>
                    <div className="font-mono text-[0.85em] mb-0.5 text-indigo-600 dark:text-indigo-400 font-semibold">{label}</div>
                    {editing ? (
                      <select
                        value={values[fieldName] ?? ''}
                        onChange={(e) => setValues(prev => ({ ...prev, [fieldName]: e.target.value }))}
                        className="w-full text-xs px-1 py-0.5 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 dark:text-white"
                        style={{ fontSize: 'inherit' }}
                      >
                        <option value="">—</option>
                        {cfg.options.map((o: any) => (
                          <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                      </select>
                    ) : (
                      <div className="text-xs text-gray-900 dark:text-white">{displayText}</div>
                    )}
                  </div>
                );
              }

              // Contact-select: label IS the add-select, chips below
              if (isContactSelect) {
                return (
                  <div key={fieldName}>
                    {renderField(fieldName, disabled)}
                  </div>
                );
              }

              // Other fields: label + widget
              const isInteractive = cfg?.type === 'search' || cfg?.type === 'action';
              return (
                <div key={fieldName}>
                  <div className={isInteractive ? "font-mono text-[0.85em] mb-0.5 text-indigo-600 dark:text-indigo-400 font-semibold" : lClass}>{label}</div>
                  {renderField(fieldName, disabled)}
                </div>
              );
            })}
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

      {/* ── Standard panels — every record type ─────────────────── */}

      {/* Contacts — uses ContactPanel (specialized for refs.links.contact) */}
      <ContactPanel
        contacts={linkedContacts}
        isEditing={editing}
        parent_model={modelName}
        parentId={Number(recordId)}
        onChange={async (updated: RefContact[]) => {
          setLinkedContacts(updated);
          try {
            const contactLinks = updated.map(c => ({
              id: c.contact_id,
              purpose: c.purpose || 'primary',
              attention: c.attention,
              email: c.email,
              phone: c.phone,
            }));
            await saveRecord(modelName, {
              id: Number(recordId),
              'refs.links.contact': contactLinks,
            });
          } catch (err) {
            console.error('Failed to save contacts:', err);
          }
        }}
        title="Contacts"
        defaultCollapsed={true}
      />

      {/* ── Self-discovered panels — from refs.links keys + standards ── */}
      {linkedPanelModels.map(panel => (
        <LinkedRecordsPanel
          key={panel}
          linkedModel={panel}
          parentModel={modelName}
          parentId={Number(recordId)}
          defaultCollapsed={true}
          editable={editing}
        />
      ))}

      {/* ── "+ Link..." — add a panel for any model ────────────── */}
      {editing && (
        <div style={{ padding: '4px 12px' }}>
          {showModelPicker ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <select
                className="db-input"
                style={{ fontSize: 11, flex: 1, padding: '2px 6px' }}
                value=""
                onChange={(e) => {
                  const model = e.target.value;
                  if (model && !linkedPanelModels.includes(model) && !SPECIALIZED.includes(model)) {
                    // Adding a model panel creates an empty refs.links entry so the panel persists
                    saveRecord(modelName, {
                      id: Number(recordId),
                      [`refs.links.${model}`]: [],
                    }).catch(() => {});
                    setLinkedPanelModels(prev => [...prev, model]);
                  }
                  setShowModelPicker(false);
                }}
              >
                <option value="">Select model to link...</option>
                {availableModels
                  .filter(m => !SPECIALIZED.includes(m) && !linkedPanelModels.includes(m))
                  .map(m => <option key={m} value={m}>{m}</option>)
                }
              </select>
              <button onClick={() => setShowModelPicker(false)} className="db-text-dim" style={{ fontSize: 11 }}>Cancel</button>
            </div>
          ) : (
            <button
              onClick={() => setShowModelPicker(true)}
              className="w-full rounded border border-dashed py-1 text-[10px] transition-colors"
              style={{ borderColor: 'var(--db-border)', color: 'var(--db-text-dim)' }}
            >
              + Link...
            </button>
          )}
        </div>
      )}

      {/* File upload — every upload creates a Document record */}
      <FileUploadPanel
        modelName={modelName}
        recordId={recordId}
        recordIda={data?.ida}
        compact={hideToolbar}
        className="border-t border-gray-200 pt-1.5 dark:border-gray-700"
      />

      {/* Open db.page — primary record in full page layout */}
      <div className="border-t border-gray-200 pt-1.5 dark:border-gray-700">
        <button
          onClick={() => window.open(`/${modelName}/${recordId}`, '_blank')}
          className="w-full rounded border border-gray-300 py-1 text-[11px] text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
        >
          {modelName}/{recordId}
        </button>
      </div>
    </div>
  );
}

export default withDevIdentifier(DynamicDetail, 'DynamicDetail', 'indigo', 'components/common/DynamicDetail.tsx');
export { DynamicDetail, DEFAULT_ACTION_LAYOUT, FIELD_REGISTRIES, DEFAULT_LAYOUTS };
export type { FieldConfig, DynamicDetailActions };

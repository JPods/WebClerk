/**
 * LayoutWorkbench — browse and preview all layout types across models.
 *
 * Select a layout type (form, detail, list, panel, card, print) from the dropdown.
 * Left panel shows all models with that layout type.
 * Right panel renders a live preview with sample data.
 *
 * URL: /layout-workbench
 *
 * LastChecked: 2026-09-14 | WhereUsed: /layout-workbench | WhoCreated: Bill+Claude
 */
import { useEffect, useState, useCallback, useRef } from "react";
import PageMeta from "@/components/common/PageMeta";
import apiClient from "../../api/axios";
import {
  LayoutItem,
  ParadeData,
  LayoutPreview,
  itemSummary,
  settingPath,
} from "./LayoutPreviewRenderers";
import "./SettingParade.css";

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const LAYOUT_TYPES = [
  { value: "form", label: "form" },
  { value: "detail", label: "detail" },
  { value: "list", label: "list" },
  { value: "panel", label: "panel" },
  { value: "card", label: "card" },
  { value: "print", label: "print" },
];

const TYPE_DESCRIPTIONS: Record<string, string> = {
  form: "App view — curated business forms with header cards, tabs, line items",
  detail: "Admin view — all fields, grouped by section",
  list: "Grid columns — field order, widths, alignment for list views",
  panel: "Linked record panels — compact column layouts",
  card: "Card layouts — reusable field blocks for forms and Kanban",
  print: "Print layouts — report and document templates",
};

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface SelectedItem {
  type: string;
  model: string;
  singular: string;
  item: LayoutItem;
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function LayoutWorkbench() {
  const [layoutType, setLayoutType] = useState("form");
  const [cache, setCache] = useState<Record<string, ParadeData>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<SelectedItem | null>(null);
  const [previewRecords, setPreviewRecords] = useState<any[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const fetchedTypes = useRef<Set<string>>(new Set());

  // Load manifest for current type (with caching)
  useEffect(() => {
    if (cache[layoutType]) return; // already cached
    if (fetchedTypes.current.has(layoutType)) return; // already fetching
    fetchedTypes.current.add(layoutType);

    setLoading(true);
    setError(null);
    apiClient
      .get(`/wcapi/_component_parade/?type=${layoutType}`)
      .then((res) => {
        const d: ParadeData = res.data?.data ?? res.data;
        setCache((prev) => ({ ...prev, [layoutType]: d }));
      })
      .catch((err) => {
        const msg = err?.response?.data?.error;
        setError(typeof msg === "string" ? msg : `Failed to load ${layoutType} layouts`);
        fetchedTypes.current.delete(layoutType);
      })
      .finally(() => setLoading(false));
  }, [layoutType, cache]);

  // Load preview records when selection changes
  const loadPreview = useCallback(
    (type: string, model: string, singular: string, item: LayoutItem) => {
      stickyModel.current = model;
      setSelected({ type, model, singular, item });
      setPreviewLoading(true);
      const limit =
        item.kind === "panel" || item.kind === "list" || item.kind === "column"
          ? 10
          : 1;
      apiClient
        .get(`/wcapi/_component_parade_preview/?model=${model}&limit=${limit}`)
        .then((res) => {
          const d = res.data?.data ?? res.data;
          setPreviewRecords(d.records || []);
        })
        .catch(() => setPreviewRecords([]))
        .finally(() => setPreviewLoading(false));
    },
    []
  );

  // Track the sticky model — persists across type changes
  const stickyModel = useRef<string | null>(null);
  const stickyAppliedFor = useRef<string | null>(null);

  // When type changes, try to re-select the same model in the new type
  useEffect(() => {
    if (!stickyModel.current) return;
    if (stickyAppliedFor.current === layoutType) return; // already applied
    const typeData = cache[layoutType];
    if (!typeData) return; // still loading — will retry when cache updates
    stickyAppliedFor.current = layoutType;
    const mg = typeData.models.find((m) => m.model === stickyModel.current);
    if (mg && mg.items.length > 0) {
      loadPreview(layoutType, mg.model, mg.singular, mg.items[0]);
    } else {
      // Model doesn't have this layout type — clear selection
      setSelected(null);
      setPreviewRecords([]);
    }
  }, [layoutType, cache, loadPreview]);

  const handleTypeChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    if (selected) {
      stickyModel.current = selected.model;
    }
    stickyAppliedFor.current = null; // reset so effect fires for new type
    setLayoutType(e.target.value);
  }, [selected]);

  const data = cache[layoutType] || null;
  const isLoading = loading && !data;

  return (
    <>
      <PageMeta title="Layout Workbench" />
      <div className="sp-container" style={{ "--sp-fs": "13px" } as any}>
        {/* Header */}
        <div className="sp-header">
          <h1>Layout Workbench</h1>
          <div className="sp-header-stats">
            <select
              className="sp-type-select"
              value={layoutType}
              onChange={handleTypeChange}
            >
              {LAYOUT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            {data && (
              <span style={{ marginLeft: 12 }}>
                {data.total_items} layout{data.total_items !== 1 ? "s" : ""} across{" "}
                {data.total_models} model{data.total_models !== 1 ? "s" : ""}
              </span>
            )}
          </div>
        </div>

        {/* Main split */}
        <div className="sp-main">
          {/* Left panel — model list */}
          <div className="sp-left">
            {isLoading && (
              <div className="sp-empty">
                <p className="small">loading {layoutType} layouts...</p>
              </div>
            )}
            {error && !data && (
              <div className="sp-empty">
                <p className="small">{error}</p>
              </div>
            )}
            {data && data.models.length === 0 && (
              <div className="sp-empty">
                <p className="small">no {layoutType} layouts found</p>
              </div>
            )}
            {data &&
              data.models.map((mg) => (
                <div key={mg.model}>
                  {mg.items.length === 1 ? (
                    /* Single layout — model name IS the clickable item */
                    <button
                      className={`sp-item${
                        selected?.model === mg.model &&
                        selected?.item.name === mg.items[0].name
                          ? " selected"
                          : ""
                      }`}
                      onClick={() =>
                        loadPreview(layoutType, mg.model, mg.singular, mg.items[0])
                      }
                    >
                      <div className="sp-item-row">
                        <span className="sp-item-name">{mg.singular}</span>
                        <span className="sp-item-count">
                          {itemSummary(mg.items[0])}
                        </span>
                      </div>
                      <div className="sp-item-meta">
                        <span className="sp-item-purpose">
                          {mg.model} · {mg.items[0].name}
                        </span>
                      </div>
                    </button>
                  ) : (
                    /* Multiple layouts — show model header + items */
                    <>
                      <div className="sp-group-header">
                        <p className="sp-group-title">
                          {mg.singular}
                          <span style={{ fontWeight: 400, marginLeft: 6 }}>
                            ({mg.items.length})
                          </span>
                        </p>
                        <p className="sp-group-desc">{mg.model} · {mg.kind}</p>
                      </div>
                      {mg.items.map((item, idx) => {
                        const isSelected =
                          selected?.model === mg.model &&
                          selected?.item.name === item.name &&
                          selected?.item.kind === item.kind;
                        return (
                          <button
                            key={`${item.kind}-${item.name}-${idx}`}
                            className={`sp-item${isSelected ? " selected" : ""}`}
                            onClick={() =>
                              loadPreview(layoutType, mg.model, mg.singular, item)
                            }
                          >
                            <div className="sp-item-row">
                              <span className="sp-item-name">{item.name}</span>
                              <span className="sp-item-count">
                                {itemSummary(item)}
                              </span>
                            </div>
                            <div className="sp-item-meta">
                              <span className="sp-item-purpose">{item.kind}</span>
                            </div>
                          </button>
                        );
                      })}
                    </>
                  )}
                </div>
              ))}
          </div>

          {/* Right panel — preview */}
          <div className="sp-right">
            {!selected ? (
              <div className="sp-empty">
                <div>
                  <p className="big">{layoutType} layouts</p>
                  <p className="small">
                    {TYPE_DESCRIPTIONS[layoutType] || ""}
                  </p>
                  <p className="small">
                    Select a model on the left to preview its layout with live data
                  </p>
                </div>
              </div>
            ) : (
              <>
                {/* Toolbar */}
                <div className="sp-toolbar">
                  <span className="sp-toolbar-name">
                    {selected.singular} — {selected.item.name}
                  </span>
                  <div className="sp-toolbar-divider" />
                  <span className="sp-toolbar-status">
                    {selected.item.kind} · {itemSummary(selected.item)}
                  </span>
                  {previewLoading && (
                    <span className="sp-toolbar-status">loading...</span>
                  )}
                  {!previewLoading && previewRecords.length > 0 && (
                    <span className="sp-toolbar-status">
                      {previewRecords.length} record
                      {previewRecords.length !== 1 ? "s" : ""}
                    </span>
                  )}
                </div>

                {/* Preview content */}
                <div className="sp-preview">
                  <div className="sp-preview-content">
                    <LayoutPreview
                      item={selected.item}
                      records={previewRecords}
                    />

                    {/* Path + spec toggle */}
                    <details className="sp-raw-spec">
                      <summary className="sp-raw-spec-summary">
                        {settingPath(selected.model, selected.item)}
                      </summary>
                      <pre className="sp-raw-spec-content">
                        {JSON.stringify(selected.item.spec, null, 2)}
                      </pre>
                    </details>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

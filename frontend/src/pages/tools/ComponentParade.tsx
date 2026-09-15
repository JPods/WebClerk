/**
 * ComponentParade — browse all layout components extracted from wc:model Settings.
 *
 * Left panel: models with their layout entries (panels, lists, details, cards, forms).
 * Right panel: live rendered preview with sample data from the database.
 *
 * URL: /component-parade?type=panel (or list, detail, card, form)
 *
 * LastChecked: 2026-09-14 | WhereUsed: /component-parade | WhoCreated: Bill+Claude
 */
import { useEffect, useState, useCallback } from "react";
import PageMeta from "@/components/common/PageMeta";
import apiClient from "../../api/axios";
import {
  LayoutItem,
  ModelGroup,
  ParadeData,
  LayoutPreview,
  itemSummary,
  settingPath,
} from "./LayoutPreviewRenderers";
import "./SettingParade.css";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface SelectedItem {
  model: string;
  singular: string;
  item: LayoutItem;
}

const TYPE_LABELS: Record<string, string> = {
  panel: "Panel Parade",
  list: "List Parade",
  detail: "Detail Parade",
  card: "Card Parade",
  form: "Form Parade",
};

const TYPE_DESCRIPTIONS: Record<string, string> = {
  panel: "db.panel columns for every linked record panel",
  list: "db.list column order for all list views",
  detail: "db.detail field layout for Admin view",
  card: "db.card layouts for Kanban and compact views",
  form: "db.form layouts — App view detail sections",
};

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function ComponentParade() {
  const params = new URLSearchParams(window.location.search);
  const layoutType = params.get("type") || "panel";

  const [data, setData] = useState<ParadeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<SelectedItem | null>(null);
  const [previewRecords, setPreviewRecords] = useState<any[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [expandedModels, setExpandedModels] = useState<Set<string>>(new Set());

  // Load manifest
  useEffect(() => {
    setLoading(true);
    setError(null);
    setSelected(null);
    setPreviewRecords([]);
    apiClient
      .get(`/wcapi/_component_parade/?type=${layoutType}`)
      .then((res) => {
        const d: ParadeData = res.data?.data ?? res.data;
        setData(d);
        // Expand all models by default
        setExpandedModels(new Set(d.models.map((m) => m.model)));
      })
      .catch((err) => {
        setError(err?.response?.data?.error ?? "Failed to load component parade");
      })
      .finally(() => setLoading(false));
  }, [layoutType]);

  // Load preview records when selection changes
  const loadPreview = useCallback(
    (model: string, singular: string, item: LayoutItem) => {
      setSelected({ model, singular, item });
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

  const toggleModel = useCallback((model: string) => {
    setExpandedModels((prev) => {
      const next = new Set(prev);
      if (next.has(model)) next.delete(model);
      else next.add(model);
      return next;
    });
  }, []);

  // Render
  if (loading) {
    return (
      <div className="sp-empty" style={{ height: "100vh" }}>
        <p className="big">loading {TYPE_LABELS[layoutType] || layoutType}...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="sp-empty" style={{ height: "100vh" }}>
        <p className="big">{error || "no data"}</p>
      </div>
    );
  }

  return (
    <>
      <PageMeta title={TYPE_LABELS[layoutType] || "Component Parade"} />
      <div className="sp-container" style={{ "--sp-fs": "13px" } as any}>
        {/* Header */}
        <div className="sp-header">
          <h1>{TYPE_LABELS[layoutType] || layoutType}</h1>
          <div className="sp-header-stats">
            {data.total_items} {layoutType}s across {data.total_models} models
          </div>
        </div>

        {/* Main split */}
        <div className="sp-main">
          {/* Left panel — model list */}
          <div className="sp-left">
            {data.models.map((mg) => (
              <div key={mg.model}>
                <div className="sp-group-header">
                  <button
                    onClick={() => toggleModel(mg.model)}
                    style={{
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      padding: 0,
                      width: "100%",
                      textAlign: "left",
                    }}
                  >
                    <p className="sp-group-title" style={{ margin: 0 }}>
                      {expandedModels.has(mg.model) ? "▼" : "▶"}{" "}
                      {mg.singular}
                      <span style={{ fontWeight: 400, marginLeft: 6 }}>
                        ({mg.items.length})
                      </span>
                    </p>
                    <p className="sp-group-desc">{mg.model} · {mg.kind}</p>
                  </button>
                </div>
                {expandedModels.has(mg.model) &&
                  mg.items.map((item, idx) => {
                    const isSelected =
                      selected?.model === mg.model &&
                      selected?.item.name === item.name &&
                      selected?.item.kind === item.kind;
                    return (
                      <button
                        key={`${item.kind}-${item.name}-${idx}`}
                        className={`sp-item${isSelected ? " selected" : ""}`}
                        onClick={() => loadPreview(mg.model, mg.singular, item)}
                      >
                        <div className="sp-item-row">
                          <span className="sp-item-name">{item.name}</span>
                          <span
                            className="sp-item-badge"
                            style={{
                              width: "auto",
                              borderRadius: 3,
                              padding: "1px 6px",
                              background: "var(--db-surface-alt)",
                              color: "var(--db-text-muted)",
                              fontSize: "calc(var(--sp-fs) - 3px)",
                            }}
                          >
                            {itemSummary(item)}
                          </span>
                        </div>
                        <div className="sp-item-meta">
                          <span className="sp-item-purpose">{item.kind}</span>
                        </div>
                      </button>
                    );
                  })}
              </div>
            ))}
          </div>

          {/* Right panel — preview */}
          <div className="sp-right">
            {!selected ? (
              <div className="sp-empty">
                <div>
                  <p className="big">
                    {TYPE_LABELS[layoutType] || layoutType}
                  </p>
                  <p className="small">
                    {TYPE_DESCRIPTIONS[layoutType] || ""}
                  </p>
                  <p className="small">
                    Click any item on the left to preview it with live data
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
                      {previewRecords.length} record{previewRecords.length !== 1 ? "s" : ""}
                    </span>
                  )}
                </div>

                {/* Preview content */}
                <div className="sp-preview">
                  <div className="sp-preview-content">
                    <LayoutPreview item={selected.item} records={previewRecords} />

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

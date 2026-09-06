/**
 * LayoutParade — audit tool showing layout coverage for every registered model.
 *
 * Fetches /wcapi/_layout_parade/ and displays a table of all models with
 * their list/detail/panel layout status. Flags gaps for Alice to address.
 *
 * LastChecked: 2026-09-05 | WhereUsed: /layout-parade | WhoCreated: Bill+Claude
 */
import { useEffect, useState } from "react";
import PageMeta from "@/components/common/PageMeta";
import apiClient from "../../api/axios";
import "./SettingParade.css";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ModelAudit {
  model: string;
  singular: string;
  kind: string;
  has_wc_model_setting: boolean;
  has_list_layout: boolean;
  has_detail_layout: boolean;
  has_panel_layout: boolean;
  has_card_layout: boolean;
  has_form_layout: boolean;
  list_column_count: number;
  detail_field_count: number;
  panel_column_count: number;
  card_count: number;
  form_tab_count: number;
  needs_attention: boolean;
  gaps: string[];
}

interface AuditSummary {
  total_models: number;
  has_wc_model_setting: number;
  has_list_layout: number;
  has_detail_layout: number;
  has_panel_layout: number;
  has_card_layout: number;
  has_form_layout: number;
  fully_covered: number;
  needs_attention: number;
}

interface AuditResponse {
  summary: AuditSummary;
  models: ModelAudit[];
}

/* ------------------------------------------------------------------ */
/*  Filter options                                                     */
/* ------------------------------------------------------------------ */

type FilterMode = "all" | "gaps" | "covered";

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

const LayoutParade: React.FC = () => {
  const [data, setData] = useState<AuditResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterMode>("all");
  const [kindFilter, setKindFilter] = useState<string>("all");
  const [selectedModel, setSelectedModel] = useState<ModelAudit | null>(null);

  useEffect(() => {
    apiClient
      .get("/wcapi/_layout_parade/")
      .then((res) => {
        const d: AuditResponse = res.data?.data ?? res.data;
        setData(d);
      })
      .catch((err) => {
        setError(err?.response?.data?.detail ?? "Failed to load layout audit");
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="sp-empty" style={{ height: "100vh" }}>
        <p className="big">loading layout audit...</p>
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

  const { summary } = data;

  // Collect unique kinds for filter
  const kinds = Array.from(new Set(data.models.map((m) => m.kind))).sort();

  // Apply filters
  let models = data.models;
  if (filter === "gaps") models = models.filter((m) => m.needs_attention);
  if (filter === "covered") models = models.filter((m) => !m.needs_attention);
  if (kindFilter !== "all") models = models.filter((m) => m.kind === kindFilter);

  const checkMark = (val: boolean, count?: number) => {
    if (val) return <span className="lp-check lp-yes">{count || "Y"}</span>;
    return <span className="lp-check lp-no">-</span>;
  };

  return (
    <>
      <PageMeta title="Layout Parade" description="Layout coverage audit" />
      <div className="sp-container">
        {/* Header */}
        <div className="sp-header">
          <h1>layout parade</h1>
          <span className="sp-header-stats">
            {summary.total_models} models |{" "}
            {summary.fully_covered} fully covered |{" "}
            {summary.needs_attention} need attention
          </span>
        </div>

        {/* Summary bar */}
        <div className="lp-summary">
          <div className="lp-stat">
            <span className="lp-stat-num">{summary.has_wc_model_setting}</span>
            <span className="lp-stat-label">wc:model settings</span>
          </div>
          <div className="lp-stat">
            <span className="lp-stat-num">{summary.has_list_layout}</span>
            <span className="lp-stat-label">list layouts</span>
          </div>
          <div className="lp-stat">
            <span className="lp-stat-num">{summary.has_detail_layout}</span>
            <span className="lp-stat-label">detail layouts</span>
          </div>
          <div className="lp-stat">
            <span className="lp-stat-num">{summary.has_panel_layout}</span>
            <span className="lp-stat-label">panel layouts</span>
          </div>
          <div className="lp-stat">
            <span className="lp-stat-num">{summary.has_card_layout}</span>
            <span className="lp-stat-label">card layouts</span>
          </div>
          <div className="lp-stat">
            <span className="lp-stat-num">{summary.has_form_layout}</span>
            <span className="lp-stat-label">form layouts</span>
          </div>
        </div>

        {/* Filters */}
        <div className="lp-filters">
          <button
            className={`lp-filter-btn${filter === "all" ? " active" : ""}`}
            onClick={() => setFilter("all")}
          >all ({data.models.length})</button>
          <button
            className={`lp-filter-btn${filter === "gaps" ? " active" : ""}`}
            onClick={() => setFilter("gaps")}
          >gaps ({summary.needs_attention})</button>
          <button
            className={`lp-filter-btn${filter === "covered" ? " active" : ""}`}
            onClick={() => setFilter("covered")}
          >covered ({summary.fully_covered})</button>
          <select
            className="lp-kind-select"
            value={kindFilter}
            onChange={(e) => setKindFilter(e.target.value)}
          >
            <option value="all">all kinds</option>
            {kinds.map((k) => (
              <option key={k} value={k}>{k}</option>
            ))}
          </select>
        </div>

        {/* Main table */}
        <div className="sp-main" style={{ flexDirection: "column" }}>
          <table className="sp-table lp-table">
            <thead>
              <tr>
                <th>model</th>
                <th>kind</th>
                <th style={{ textAlign: "center" }}>setting</th>
                <th style={{ textAlign: "center" }}>list</th>
                <th style={{ textAlign: "center" }}>detail</th>
                <th style={{ textAlign: "center" }}>panel</th>
                <th style={{ textAlign: "center" }}>card</th>
                <th style={{ textAlign: "center" }}>form</th>
                <th>gaps</th>
              </tr>
            </thead>
            <tbody>
              {models.map((m) => (
                <tr
                  key={m.model}
                  className={`lp-row${m.needs_attention ? " lp-attention" : ""}${selectedModel?.model === m.model ? " selected" : ""}`}
                  onClick={() => setSelectedModel(selectedModel?.model === m.model ? null : m)}
                >
                  <td className="sp-field-name">{m.model}</td>
                  <td><span className="lp-kind-badge">{m.kind}</span></td>
                  <td style={{ textAlign: "center" }}>{checkMark(m.has_wc_model_setting)}</td>
                  <td style={{ textAlign: "center" }}>{checkMark(m.has_list_layout, m.list_column_count)}</td>
                  <td style={{ textAlign: "center" }}>{checkMark(m.has_detail_layout, m.detail_field_count)}</td>
                  <td style={{ textAlign: "center" }}>{checkMark(m.has_panel_layout, m.panel_column_count)}</td>
                  <td style={{ textAlign: "center" }}>{checkMark(m.has_card_layout, m.card_count)}</td>
                  <td style={{ textAlign: "center" }}>{checkMark(m.has_form_layout, m.form_tab_count)}</td>
                  <td className="lp-gaps-cell">
                    {m.gaps.map((g, i) => (
                      <span key={i} className="lp-gap-tag">{g}</span>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Detail panel for selected model */}
          {selectedModel && (
            <div className="lp-detail-panel">
              <h3>{selectedModel.singular} ({selectedModel.model})</h3>
              <div className="lp-detail-grid">
                <div><strong>kind:</strong> {selectedModel.kind}</div>
                <div><strong>wc:model setting:</strong> {selectedModel.has_wc_model_setting ? "yes" : "no"}</div>
                <div><strong>list columns:</strong> {selectedModel.list_column_count || "none"}</div>
                <div><strong>detail fields:</strong> {selectedModel.detail_field_count || "none"}</div>
                <div><strong>panel columns:</strong> {selectedModel.panel_column_count || "none"}</div>
                <div><strong>card specs:</strong> {selectedModel.card_count || "none"}</div>
                <div><strong>form tabs:</strong> {selectedModel.form_tab_count || "none"}</div>
              </div>
              {selectedModel.gaps.length > 0 && (
                <div className="lp-detail-gaps">
                  <strong>needs attention:</strong>
                  <ul>
                    {selectedModel.gaps.map((g, i) => (
                      <li key={i}>{g}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <style>{`
        .lp-summary {
          display: flex;
          gap: 24px;
          padding: 12px 20px;
          border-bottom: 1px solid var(--sp-border, #333);
        }
        .lp-stat {
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        .lp-stat-num {
          font-size: 1.4em;
          font-weight: 600;
          color: var(--sp-accent, #6ca0dc);
        }
        .lp-stat-label {
          font-size: 0.8em;
          opacity: 0.7;
        }
        .lp-filters {
          display: flex;
          gap: 8px;
          padding: 8px 20px;
          align-items: center;
          border-bottom: 1px solid var(--sp-border, #333);
        }
        .lp-filter-btn {
          background: transparent;
          border: 1px solid var(--sp-border, #555);
          color: inherit;
          padding: 4px 12px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 0.85em;
        }
        .lp-filter-btn.active {
          background: var(--sp-accent, #6ca0dc);
          color: #000;
          border-color: var(--sp-accent, #6ca0dc);
        }
        .lp-kind-select {
          background: transparent;
          border: 1px solid var(--sp-border, #555);
          color: inherit;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 0.85em;
          margin-left: auto;
        }
        .lp-table {
          width: 100%;
        }
        .lp-table th {
          position: sticky;
          top: 0;
          z-index: 1;
        }
        .lp-row {
          cursor: pointer;
        }
        .lp-row:hover {
          background: rgba(255,255,255,0.04);
        }
        .lp-row.selected {
          background: rgba(108,160,220,0.12);
        }
        .lp-row.lp-attention {
          border-left: 3px solid #e5a847;
        }
        .lp-check {
          font-weight: 600;
          font-size: 0.9em;
        }
        .lp-check.lp-yes {
          color: #5cb85c;
        }
        .lp-check.lp-no {
          color: #888;
        }
        .lp-kind-badge {
          font-size: 0.8em;
          padding: 1px 6px;
          border-radius: 3px;
          background: rgba(255,255,255,0.08);
        }
        .lp-gaps-cell {
          display: flex;
          gap: 4px;
          flex-wrap: wrap;
        }
        .lp-gap-tag {
          font-size: 0.75em;
          padding: 1px 6px;
          border-radius: 3px;
          background: rgba(229,168,71,0.2);
          color: #e5a847;
        }
        .lp-detail-panel {
          padding: 16px 20px;
          border-top: 1px solid var(--sp-border, #333);
          margin-top: 8px;
        }
        .lp-detail-panel h3 {
          margin: 0 0 12px;
          font-size: 1.1em;
        }
        .lp-detail-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 8px;
          font-size: 0.9em;
        }
        .lp-detail-gaps {
          margin-top: 12px;
          font-size: 0.9em;
        }
        .lp-detail-gaps ul {
          margin: 4px 0 0 20px;
          padding: 0;
        }
      `}</style>
    </>
  );
};

export default LayoutParade;

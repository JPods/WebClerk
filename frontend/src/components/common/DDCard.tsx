/**
 * DDCard — Data-Driven Card
 *
 * Compact, information-dense summary card driven by dd_card Setting config.
 * The server computes every figure over every row the viewer may see (manage action
 * dd_card_metrics, or the card's own server_action); this component only formats and draws.
 * It never adds records up itself: summing r['total'] over 500 fetched rows said $0.00 on every
 * card, because a transaction carries totals.total (FAULT 20261103T221823; readme 105).
 * Uses --db-* CSS variables for theme consistency.
 */
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import apiClient from "@/api/axios";
import { refusedFrom } from "@/api/wcapi";

// ---------------------------------------------------------------------------
// Types — match the dd_card:base Setting config shape
// ---------------------------------------------------------------------------

interface MetricDef {
  field?: string;
  fields?: string[];
  agg: string;
  label: string;
  format?: "currency" | "percent" | "number";
  invert?: boolean;
  exclude?: Record<string, any>;   // rows the metric leaves out (a cash card's adjustments, plan 102)
}

interface DistributionDef {
  field: string;
  type?: "category";
  buckets?: number[];
  labels: string[];
}

export interface DDCardConfig {
  label: string;
  link: string;
  filters?: Record<string, any>;
  metrics: MetricDef[];
  distribution?: DistributionDef;
  server_action?: string;  // manage endpoint action — returns pre-computed { metrics: [{label, value}] }
  model_list?: string[];   // optional model selector — renders dropdown, navigates to databrowser with selected model
}

interface DDCardProps {
  model: string;
  config: DDCardConfig;
}

// ---------------------------------------------------------------------------
// Formatting — the number comes from the server
// ---------------------------------------------------------------------------

function formatValue(val: number, fmt?: string): string {
  switch (fmt) {
    case "currency":
      return val >= 1000
        ? "$" + val.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })
        : "$" + val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    case "percent":
      return val.toFixed(1) + "%";
    default:
      return val.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
}

/** A server metric is {label, value: number, format?}; an older server_action may send the text ready. */
function shown(m: { label: string; value: number | string; format?: string }): { label: string; value: string } {
  return { label: m.label, value: typeof m.value === "number" ? formatValue(m.value, m.format) : String(m.value ?? "") };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DDCard({ model, config }: DDCardProps) {
  const [metrics, setMetrics] = useState<{ label: string; value: string }[]>([]);
  const [distribution, setDistribution] = useState<{ label: string; count: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [dateRange, setDateRange] = useState<{ dateFrom: string; dateTo: string; staffId: number | null }>({ dateFrom: '', dateTo: '', staffId: null });

  // Listen for date range changes from DataBrowser header
  useEffect(() => {
    const handler = (e: Event) => {
      const d = (e as CustomEvent)?.detail;
      if (d) setDateRange({ dateFrom: d.dateFrom || '', dateTo: d.dateTo || '', staffId: d.staffId || null });
    };
    window.addEventListener('wc3-date-range-changed', handler);
    return () => window.removeEventListener('wc3-date-range-changed', handler);
  }, []);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        // Build date filters
        const dateFilters: Record<string, unknown> = {};
        if (dateRange.dateFrom) dateFilters.dt_created__gte = new Date(dateRange.dateFrom + 'T00:00:00').getTime();
        if (dateRange.dateTo) dateFilters.dt_created__lte = new Date(dateRange.dateTo + 'T23:59:59').getTime();
        if (dateRange.staffId) dateFilters.contact_id = dateRange.staffId;

        const res = await apiClient.post("/wcapi/_manage/", config.server_action
          ? { action: config.server_action, params: { ...config.filters, ...dateFilters } }
          : { action: "dd_card_metrics", params: {
              model, filters: { ...config.filters, ...dateFilters },
              metrics: config.metrics, distribution: config.distribution } });
        const data = res.data?.data ?? res.data;
        if (!mounted) return;
        setMetrics((data?.metrics ?? []).map(shown));
        setDistribution(data?.distribution ?? []);
        setError("");
      } catch (e) {
        if (!mounted) return;
        setError(refusedFrom(e)?.message || (e as Error)?.message || "Could not compute this card.");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, [model, config, dateRange]);

  const hasDistribution = distribution.length > 0;
  const hasModelList = config.model_list && config.model_list.length > 0;
  const navigate = useNavigate();

  const cardBody = (
    <>
      {/* Header */}
      <div
        style={{
          padding: "4px 8px",
          borderBottom: "1px solid var(--db-border)",
          fontSize: 13,
          fontWeight: 600,
          color: "var(--db-text)",
        }}
      >
        {config.label}
      </div>

      {/* Metrics — 2 column grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "1px 12px",
          padding: "4px 8px",
        }}
      >
        {loading
          ? <span style={{ fontSize: 10, color: "var(--db-text-dim)" }}>…</span>
          : error
          ? <span style={{ fontSize: 10, color: "var(--db-danger, #b91c1c)", gridColumn: "1 / -1" }}>{error}</span>
          : metrics.map((m) => (
              <div key={m.label} style={{ display: "flex", justifyContent: "space-between", gap: 4 }}>
                <span style={{ fontSize: 10, color: "var(--db-text-muted)" }}>{m.label}</span>
                <span style={{ fontSize: 10, fontWeight: 600, color: "var(--db-text)", fontVariantNumeric: "tabular-nums" }}>{m.value}</span>
              </div>
            ))
        }
      </div>

      {/* Distribution (optional) */}
      {hasDistribution && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "1px 12px",
            padding: "2px 8px 4px",
            borderTop: "1px solid var(--db-border)",
          }}
        >
          {distribution.map((d) => (
            <div key={d.label} style={{ display: "flex", justifyContent: "space-between", gap: 4 }}>
              <span style={{ fontSize: 9, color: "var(--db-text-dim)" }}>{d.label}</span>
              <span style={{ fontSize: 9, fontWeight: 600, color: "var(--db-text-muted)", fontVariantNumeric: "tabular-nums" }}>{d.count}</span>
            </div>
          ))}
        </div>
      )}

      {/* Model selector (optional) */}
      {hasModelList && (
        <div style={{ padding: "2px 4px 4px", borderTop: "1px solid var(--db-border)" }}>
          <select
            style={{
              width: "100%",
              fontSize: 10,
              padding: "1px 2px",
              background: "var(--db-bg)",
              color: "var(--db-text)",
              border: "1px solid var(--db-border)",
              borderRadius: 3,
              cursor: "pointer",
            }}
            defaultValue=""
            onClick={(e) => e.preventDefault()}
            onChange={(e) => {
              if (e.target.value) {
                navigate(`/databrowser?model=${e.target.value}`);
              }
            }}
          >
            <option value="" disabled>Browse model…</option>
            {config.model_list!.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>
      )}
    </>
  );

  const cardStyle = {
    background: "var(--db-surface)",
    borderColor: "var(--db-border)",
    minWidth: 160,
    boxShadow: "3px 3px 6px rgba(0,0,0,0.3)",
  };

  return (
    <Link
      to={config.link}
      className="group block rounded border transition hover:-translate-y-[1px]"
      style={cardStyle}
    >
      {cardBody}
    </Link>
  );
}

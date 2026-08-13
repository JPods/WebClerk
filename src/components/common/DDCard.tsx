/**
 * DDCard — Data-Driven Card
 *
 * Compact, information-dense summary card driven by dd_card Setting config.
 * Fetches model data via wcapi, computes metrics, renders 2-column layout.
 * Uses --db-* CSS variables for theme consistency.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getRecords } from "@/api/wcapi";
import apiClient from "@/api/axios";

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
}

interface DDCardProps {
  model: string;
  config: DDCardConfig;
}

// ---------------------------------------------------------------------------
// Metric computation
// ---------------------------------------------------------------------------

function computeMetrics(records: any[], metrics: MetricDef[]): { label: string; value: string }[] {
  return metrics.map((m) => {
    let raw: number;

    switch (m.agg) {
      case "count":
        raw = records.length;
        break;
      case "sum":
        raw = records.reduce((s, r) => s + (Number(r[m.field!]) || 0), 0);
        break;
      case "avg": {
        const vals = records.map((r) => Number(r[m.field!]) || 0);
        raw = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
        break;
      }
      case "margin_pct": {
        const [revField, costField] = m.fields || [];
        const totalRev = records.reduce((s, r) => s + (Number(r[revField]) || 0), 0);
        const totalCost = records.reduce((s, r) => s + (Number(r[costField]) || 0), 0);
        raw = totalRev > 0 ? ((totalRev - totalCost) / totalRev) * 100 : 0;
        break;
      }
      case "pct": {
        const [numField, denField] = m.fields || [];
        const num = records.reduce((s, r) => s + (Number(r[numField]) || 0), 0);
        const den = records.reduce((s, r) => s + (Number(r[denField]) || 0), 0);
        raw = den > 0 ? (num / den) * 100 : 0;
        if (m.invert) raw = 100 - raw;
        break;
      }
      default:
        raw = 0;
    }

    return { label: m.label, value: formatValue(raw, m.format) };
  });
}

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

function computeDistribution(records: any[], dist: DistributionDef): { label: string; count: number }[] {
  if (dist.type === "category") {
    return dist.labels.map((label) => ({
      label,
      count: records.filter((r) => r[dist.field] === label).length,
    }));
  }
  // Numeric buckets
  const buckets = dist.buckets || [];
  const results: { label: string; count: number }[] = [];

  // Compute the field value (margin_pct needs to be derived per record)
  const vals = records.map((r) => Number(r[dist.field]) || 0);

  for (let i = 0; i <= buckets.length; i++) {
    const lo = i === 0 ? -Infinity : buckets[i - 1];
    const hi = i < buckets.length ? buckets[i] : Infinity;
    results.push({
      label: dist.labels[i] || `${lo}-${hi}`,
      count: vals.filter((v) => v >= lo && v < hi).length,
    });
  }
  return results;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DDCard({ model, config }: DDCardProps) {
  const [metrics, setMetrics] = useState<{ label: string; value: string }[]>([]);
  const [distribution, setDistribution] = useState<{ label: string; count: number }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        if (config.server_action) {
          // Server-computed metrics via manage endpoint
          const res = await apiClient.post("/wcapi/manage/", {
            action: config.server_action,
            params: config.filters || {},
          });
          const data = res.data?.data ?? res.data;
          if (!mounted) return;
          if (data?.metrics) setMetrics(data.metrics);
        } else {
          // Client-computed metrics from fetched records
          const res = await getRecords(model, { ...config.filters, limit: 500 });
          const records = res?.results ?? [];
          if (!mounted) return;
          setMetrics(computeMetrics(records, config.metrics));
          if (config.distribution) {
            setDistribution(computeDistribution(records, config.distribution));
          }
        }
      } catch {
        // silent — card shows empty
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, [model, config]);

  const hasDistribution = distribution.length > 0;

  return (
    <Link
      to={config.link}
      className="group block rounded border transition hover:-translate-y-[1px]"
      style={{
        background: "var(--db-surface)",
        borderColor: "var(--db-border)",
        minWidth: 160,
        boxShadow: "3px 3px 6px rgba(0,0,0,0.3)",
      }}
    >
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
    </Link>
  );
}

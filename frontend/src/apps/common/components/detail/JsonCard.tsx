/* LastChecked: 2026-09-05 | WhereUsed: Detail pages (JSON fields) | WhoCreated: Unknown */
/**
 * JsonCard — Renders a collapsible card for a single JSONField.
 *
 * Given a JSON object and its field name, displays each first-level key
 * as a labelled row using the convention: `fieldName.key`.
 * First-level keys are sorted alphabetically.
 *
 * Uses --db-* CSS variables for theme-aware styling.
 */
import React, { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import InfoRow from "./InfoRow";
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import { HighlightedJson } from '../syntaxHighlightJson';

function renderJsonValue(value: unknown): React.ReactNode {
  if (value === null || value === undefined) {
    return <span style={{ color: 'var(--db-accent-red)' }}>null</span>;
  }
  if (typeof value === "string") {
    return <span style={{ color: 'var(--db-accent-green)' }}>{value}</span>;
  }
  if (typeof value === "number") {
    return <span style={{ color: 'var(--db-accent-purple)' }}>{value}</span>;
  }
  if (typeof value === "boolean") {
    return <span style={{ color: 'var(--db-accent-gold)' }}>{String(value)}</span>;
  }
  if (Array.isArray(value) || typeof value === "object") {
    const sorted = Array.isArray(value) ? value : sortKeys(value as Record<string, unknown>);
    const pretty = JSON.stringify(sorted, null, 2);
    return (
      <pre className="m-0 p-2 rounded db-font-xs font-mono whitespace-pre-wrap"
        style={{ background: 'var(--db-surface-alt)', color: 'var(--db-text)' }}>
        <HighlightedJson json={pretty} />
      </pre>
    );
  }
  return <span style={{ color: 'var(--db-text)' }}>{String(value)}</span>;
}

/** Sort object keys alphabetically (first level only) */
function sortKeys(obj: Record<string, unknown>): Record<string, unknown> {
  const sorted: Record<string, unknown> = {};
  for (const key of Object.keys(obj).sort()) {
    sorted[key] = obj[key];
  }
  return sorted;
}

export interface JsonCardProps {
  /** Card title (e.g. "Price", "Totals") */
  title: string;
  /** Optional icon */
  icon?: React.ReactNode;
  /** The parent JSON field name (e.g. "price", "totals") used as prefix */
  fieldName: string;
  /** The JSON object to render (first-level keys only) */
  data: Record<string, unknown> | null | undefined;
  /** Start expanded (default: true) */
  defaultExpanded?: boolean;
  /** Number of grid columns (default: 2) */
  columns?: 1 | 2 | 3;
  /** Keys to skip (e.g. "history" if rendered separately) */
  skipKeys?: string[];
}

const gridClasses: Record<number, string> = {
  1: "grid-cols-1",
  2: "grid-cols-1 sm:grid-cols-2",
  3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
};

const JsonCard: React.FC<JsonCardProps> = ({
  title,
  icon,
  fieldName,
  data,
  defaultExpanded = false,
  columns = 2,
  skipKeys = [],
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  if (!data || typeof data !== "object" || Array.isArray(data)) return null;

  const skipSet = new Set(skipKeys);
  const keys = Object.keys(data).filter((k) => !skipSet.has(k)).sort();
  if (keys.length === 0) return null;

  return (
    <div className="mb-4 rounded-lg overflow-hidden"
      style={{ border: '1px solid var(--db-border)' }}>
      <button
        type="button"
        className="w-full flex items-center justify-between px-4 py-2.5 transition-colors"
        style={{ background: 'var(--db-surface-alt)', color: 'var(--db-text)' }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronDown className="w-3 h-3" style={{ color: 'var(--db-text-muted)' }} />
          ) : (
            <ChevronRight className="w-3 h-3" style={{ color: 'var(--db-text-muted)' }} />
          )}
          {icon && <span style={{ color: 'var(--db-text-muted)' }}>{icon}</span>}
          <span className="font-semibold db-font-sm" style={{ color: 'var(--db-text)' }}>
            {title}
          </span>
          <span className="db-font-xs ml-1" style={{ color: 'var(--db-text-dim)' }}>({keys.length})</span>
        </div>
      </button>
      {isExpanded && (
        <div className="px-4 py-3" style={{ background: 'var(--db-surface)' }}>
          <dl className={`grid gap-x-6 gap-y-0 ${gridClasses[columns]}`}>
            {keys.map((key) => (
              <InfoRow
                key={key}
                label={`${fieldName}.${key}`}
                value={renderJsonValue(data[key])}
              />
            ))}
          </dl>
        </div>
      )}
    </div>
  );
};

export default withDevIdentifier(JsonCard, 'JsonCard', 'amber', 'apps/common/components/detail/JsonCard.tsx');

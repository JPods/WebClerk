/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * JsonCard — Renders a collapsible card for a single JSONField.
 *
 * Given a JSON object and its field name, displays each first-level key
 * as a labelled row using the convention: `fieldName.key`.
 *
 * Nested objects / arrays are displayed as stringified previews.
 */
import React, { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import InfoRow from "./InfoRow";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

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
  const keys = Object.keys(data).filter((k) => !skipSet.has(k));
  if (keys.length === 0) return null;

  return (
    <div className="mb-4 border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
      <button
        type="button"
        className="w-full flex items-center justify-between px-4 py-2.5 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronDown className="text-slate-400 w-3 h-3" />
          ) : (
            <ChevronRight className="text-slate-400 w-3 h-3" />
          )}
          {icon && <span className="text-slate-500">{icon}</span>}
          <span className="font-semibold text-sm text-slate-700 dark:text-slate-200">
            {title}
          </span>
          <span className="text-xs text-slate-400 ml-1">({keys.length})</span>
        </div>
      </button>
      {isExpanded && (
        <div className="px-4 py-3 bg-white dark:bg-slate-900">
          <dl className={`grid gap-x-6 gap-y-0 ${gridClasses[columns]}`}>
            {keys.map((key) => (
              <InfoRow
                key={key}
                label={`${fieldName}.${key}`}
                value={data[key] as React.ReactNode}
              />
            ))}
          </dl>
        </div>
      )}
    </div>
  );
};

export default withDevIdentifier(JsonCard, 'JsonCard', 'amber');
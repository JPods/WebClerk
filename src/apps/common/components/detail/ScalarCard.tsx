/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * ScalarCard — Renders a collapsible card containing scalar field rows.
 *
 * Takes a title, optional icon, and an array of {label, value} pairs.
 * Each pair renders as an InfoRow inside the card.
 */
import React, { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import InfoRow from "./InfoRow";
import { withDevIdentifier } from "@/components/common/DevIdentifier";

export interface ScalarField {
  /** Label — should match schema field name exactly */
  label: string;
  /** Display value */
  value: unknown;
  /** Highlight the value */
  highlight?: boolean;
  /** Format as currency */
  isCurrency?: boolean;
  /** Number of grid columns this field should span (default: 1) */
  colSpan?: 1 | 2 | 3;
}

export interface ScalarCardProps {
  /** Card title */
  title: string;
  /** Optional icon (Lucide or react-icons) */
  icon?: React.ReactNode;
  /** Fields to display */
  fields: ScalarField[];
  /** Start expanded (default: true) */
  defaultExpanded?: boolean;
  /** Number of columns for the grid (default: 2) */
  columns?: 1 | 2 | 3;
}

const gridClasses: Record<number, string> = {
  1: "grid-cols-1",
  2: "grid-cols-1 sm:grid-cols-2",
  3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
};

const ScalarCard: React.FC<ScalarCardProps> = ({
  title,
  icon,
  fields,
  defaultExpanded = true,
  columns = 2,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  if (fields.length === 0) return null;

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
          <span className="text-xs text-slate-400 ml-1">({fields.length})</span>
        </div>
      </button>
      {isExpanded && (
        <div className="px-4 py-3 bg-white dark:bg-slate-900">
          <dl className={`grid gap-x-6 gap-y-0 ${gridClasses[columns]}`}>
            {fields.map((f) => {
              const span =
                f.colSpan && f.colSpan > 1
                  ? f.colSpan === 3
                    ? "col-span-3"
                    : "col-span-2"
                  : undefined;
              return span ? (
                <div key={f.label} className={span}>
                  <InfoRow
                    label={f.label}
                    value={f.value as React.ReactNode}
                    highlight={f.highlight}
                    isCurrency={f.isCurrency}
                  />
                </div>
              ) : (
                <InfoRow
                  key={f.label}
                  label={f.label}
                  value={f.value as React.ReactNode}
                  highlight={f.highlight}
                  isCurrency={f.isCurrency}
                />
              );
            })}
          </dl>
        </div>
      )}
    </div>
  );
};

export default withDevIdentifier(ScalarCard, "ScalarCard", "amber");

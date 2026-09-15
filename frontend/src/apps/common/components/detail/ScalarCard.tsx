/* LastChecked: 2026-09-05 | WhereUsed: Detail pages (scalar field groups) | WhoCreated: Unknown */
/**
 * ScalarCard — Renders a collapsible card containing scalar field rows.
 * Uses --db-* CSS variables for theme-aware styling.
 */
import React, { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import InfoRow from "./InfoRow";
import { withDevIdentifier } from "@/components/common/DevIdentifier";

/** Field names that auto-detect linkType for click-to-dial, mailto, and map links */
const LINK_TYPE_MAP: Record<string, "phone" | "email" | "address"> = {
  phone: "phone",
  fax: "phone",
  phone_cell: "phone",
  phoneCell: "phone",
  email: "email",
  address_full: "address",
};

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
  /** Make the value a clickable link: email→mailto, phone→tel, address→Google Maps.
   *  Auto-detected from field name if not set. */
  linkType?: "email" | "phone" | "address";
  /** Original field name from the data model (used for auto-detecting linkType) */
  fieldName?: string;
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
          <span className="db-font-xs ml-1" style={{ color: 'var(--db-text-dim)' }}>({fields.length})</span>
        </div>
      </button>
      {isExpanded && (
        <div className="px-4 py-3" style={{ background: 'var(--db-surface)' }}>
          <dl className={`grid gap-x-6 gap-y-0 ${gridClasses[columns]}`}>
            {fields.map((f) => {
              const span =
                f.colSpan && f.colSpan > 1
                  ? f.colSpan === 3
                    ? "col-span-3"
                    : "col-span-2"
                  : undefined;
              const linkType = f.linkType
                || LINK_TYPE_MAP[f.fieldName || ""]
                || LINK_TYPE_MAP[f.label.toLowerCase().replace(/\s+/g, "_")];
              return span ? (
                <div key={f.label} className={span}>
                  <InfoRow
                    label={f.label}
                    value={f.value as React.ReactNode}
                    highlight={f.highlight}
                    isCurrency={f.isCurrency}
                    linkType={linkType}
                  />
                </div>
              ) : (
                <InfoRow
                  key={f.label}
                  label={f.label}
                  value={f.value as React.ReactNode}
                  highlight={f.highlight}
                  isCurrency={f.isCurrency}
                  linkType={linkType}
                />
              );
            })}
          </dl>
        </div>
      )}
    </div>
  );
};

export default withDevIdentifier(ScalarCard, "ScalarCard", "amber", 'apps/common/components/detail/ScalarCard.tsx');

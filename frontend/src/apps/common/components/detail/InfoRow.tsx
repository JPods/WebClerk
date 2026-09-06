/* LastChecked: 2026-09-05 | WhereUsed: JsonCard, ScalarCard, all Detail pages | WhoCreated: Unknown */
/**
 * InfoRow — Shared read-only horizontal label/value pair for view mode.
 *
 * Used across all Detail pages for consistent read-only field display.
 * Label on left (fixed width), value on right.
 * Uses --db-* CSS variables for theme-aware styling.
 */
import React from "react";
import { formatCurrency } from "@/utils/stringUtils";

export interface InfoRowProps {
  /** Field label — should match schema name exactly */
  label: string;
  /** Display value */
  value: React.ReactNode;
  /** Highlight the value (blue, bold) */
  highlight?: boolean;
  /** Format as currency */
  isCurrency?: boolean;
  /** Make the value a clickable link: email→mailto, phone→tel, address→Google Maps */
  linkType?: "email" | "phone" | "address";
  /** If true, apply the link to the label instead of the value */
  linkOnLabel?: boolean;
}

export function formatDisplayValue(val: unknown, isCurrency = false): string {
  if (val === null || val === undefined) return "—";
  if (typeof val === "boolean") return val ? "Yes" : "No";
  if (typeof val === "number") {
    if (isCurrency) return formatCurrency(val);
    return val.toLocaleString();
  }
  if (Array.isArray(val)) {
    if (val.length === 0) return "[]";
    return JSON.stringify(val);
  }
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}

const InfoRow: React.FC<InfoRowProps> = ({
  label,
  value,
  highlight = false,
  isCurrency = false,
  linkType,
  linkOnLabel = true,
}) => {
  const isElement = React.isValidElement(value);
  const displayVal = isElement ? value : formatDisplayValue(value, isCurrency);

  /** Wrap content in an <a> tag when linkType is set and value is a non-empty string */
  const renderLinked = (content: React.ReactNode) => {
    if (!linkType || typeof value !== "string" || !value) return content;
    const telValue = value.replace(/[^+\d]/g, "");
    const href =
      linkType === "email"
        ? `mailto:${value}`
        : linkType === "phone"
        ? `tel:${telValue}`
        : `https://maps.google.com/?q=${encodeURIComponent(value)}`;
    const title =
      linkType === "email"
        ? `Email ${value}`
        : linkType === "phone"
        ? `Call ${value}`
        : "Open in Maps";
    const extraProps =
      linkType === "address"
        ? { target: "_blank", rel: "noopener noreferrer" }
        : {};
    return (
      <a href={href}
        style={{ color: 'var(--db-accent)', textDecoration: 'underline dotted', cursor: 'pointer' }}
        title={title} {...extraProps}>
        {content}
      </a>
    );
  };

  const labelNode = (
    <dt className="w-36 shrink-0 text-right db-font-xs font-mono"
      style={{ color: 'var(--db-text-muted)' }}>
      {linkOnLabel ? renderLinked(label) : label}
    </dt>
  );

  return (
    <div className="flex items-baseline gap-2 py-1">
      {labelNode}
      <dd
        className={`db-font-sm break-all ${highlight ? 'font-semibold' : ''}`}
        style={{ color: highlight ? 'var(--db-accent)' : 'var(--db-text)' }}
      >
        {linkOnLabel
          ? typeof displayVal === "string"
            ? displayVal
            : displayVal ?? "—"
          : renderLinked(
              typeof displayVal === "string" ? displayVal : displayVal ?? "—",
            )}
      </dd>
    </div>
  );
};

export default InfoRow;

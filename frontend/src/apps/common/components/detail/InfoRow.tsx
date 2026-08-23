/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * InfoRow — Shared read-only horizontal label/value pair for view mode.
 *
 * Used across all Detail pages for consistent read-only field display.
 * Label on left (fixed width), value on right.
 */
import React from "react";

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
    if (isCurrency) return `$${val.toFixed(2)}`;
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
    const linkClasses =
      "underline decoration-dotted hover:decoration-solid hover:text-blue-600 dark:hover:text-blue-400 cursor-pointer";
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
      <a href={href} className={linkClasses} title={title} {...extraProps}>
        {content}
      </a>
    );
  };

  const labelNode = (
    <dt className="w-36 shrink-0 text-right text-xs font-mono text-gray-500 dark:text-gray-400">
      {linkOnLabel ? renderLinked(label) : label}
    </dt>
  );

  return (
    <div className="flex items-baseline gap-2 py-1">
      {labelNode}
      <dd
        className={`text-sm break-all ${
          highlight
            ? "font-semibold text-blue-600 dark:text-blue-400"
            : "text-gray-900 dark:text-white"
        }`}
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

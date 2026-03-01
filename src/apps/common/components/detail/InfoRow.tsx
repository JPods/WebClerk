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
}) => {
  const isElement = React.isValidElement(value);
  const displayVal = isElement ? value : formatDisplayValue(value, isCurrency);

  /** Wrap the rendered value in an <a> tag when linkType is set and value is a non-empty string */
  const renderLinkedValue = (content: React.ReactNode) => {
    if (!linkType || typeof value !== "string" || !value) return content;
    const linkClasses =
      "underline decoration-dotted hover:decoration-solid hover:text-blue-600 dark:hover:text-blue-400 cursor-pointer";
    switch (linkType) {
      case "email":
        return (
          <a
            href={`mailto:${value}`}
            className={linkClasses}
            title={`Email ${value}`}
          >
            {content}
          </a>
        );
      case "phone":
        return (
          <a
            href={`tel:${value.replace(/[^+\d]/g, "")}`}
            className={linkClasses}
            title={`Call ${value}`}
          >
            {content}
          </a>
        );
      case "address":
        return (
          <a
            href={`https://maps.google.com/?q=${encodeURIComponent(value)}`}
            target="_blank"
            rel="noopener noreferrer"
            className={linkClasses}
            title="Open in Maps"
          >
            {content}
          </a>
        );
      default:
        return content;
    }
  };

  return (
    <div className="flex items-baseline gap-2 py-1">
      <dt className="w-36 shrink-0 text-right text-xs font-mono text-gray-500 dark:text-gray-400">
        {label}
      </dt>
      <dd
        className={`text-sm break-all ${
          highlight
            ? "font-semibold text-blue-600 dark:text-blue-400"
            : "text-gray-900 dark:text-white"
        }`}
      >
        {renderLinkedValue(
          typeof displayVal === "string" ? displayVal : displayVal ?? "—",
        )}
      </dd>
    </div>
  );
};

export default InfoRow;

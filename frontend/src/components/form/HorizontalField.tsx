/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import React from "react";
import Label from "./Label";

/**
 * HorizontalField - Enterprise standard label-left field layout
 *
 * Used for data-dense enterprise apps where users become experts.
 * Label on left, input on right - scannable once learned.
 *
 * @see readmes/ui-form-layout-research.md
 */

export interface HorizontalFieldProps {
  /** Field label text */
  label: React.ReactNode;
  /** HTML for attribute linking label to input */
  htmlFor: string;
  /** Field input element(s) */
  children: React.ReactNode;
  /** Validation error message */
  error?: string;
  /** Show required indicator */
  required?: boolean;
  /** Optional icon (Lucide icon element) */
  icon?: React.ReactNode;
  /** Optional inline content to render after the label (e.g., tel link) */
  labelAddon?: React.ReactNode;
  /** If set, label text becomes a clickable link */
  labelHref?: string;
  /** Label width class (default: w-28) */
  labelWidth?: string;
  /** Additional className for the container */
  className?: string;
}

export function HorizontalField({
  label,
  htmlFor,
  children,
  error,
  required,
  icon,
  labelAddon,
  labelHref,
  labelWidth = "w-28",
  className = "",
}: HorizontalFieldProps) {
  const labelContent = labelHref
    ? <a href={labelHref} target="_blank" rel="noopener noreferrer" className="hover:underline text-indigo-400">{label}</a>
    : label;
  return (
    <div className={`flex items-center gap-2 py-2 ${className}`}>
      <Label
        htmlFor={htmlFor}
        className={`${labelWidth} shrink-0 text-right text-sm font-medium text-slate-600 dark:text-slate-400 flex items-center justify-end gap-1`}
      >
        {icon && <span className="text-slate-400">{icon}</span>}
        {labelContent}
        {required && <span className="text-red-500 ml-0.5">*</span>}
        {labelAddon}
      </Label>
      <div className="flex-1 min-w-0">
        {children}
        {error && <p className="mt-0.5 text-xs text-red-500">{error}</p>}
      </div>
    </div>
  );
}

export default HorizontalField;

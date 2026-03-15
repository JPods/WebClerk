/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * RawJsonCard — Renders a collapsible card for a single JSONField.
 *
 * Given a JSON object and its field name, displays each first-level key
 * as a labelled row using the convention: `fieldName.key`.
 *
 * Nested objects / arrays are displayed as stringified previews.
 */
import React, { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { FaCode } from "react-icons/fa";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

export interface RawJsonCardProps {
  /** The JSON object to render */
  data: Record<string, unknown> | null | undefined;
  /** Start expanded (default: true) */
  defaultExpanded?: boolean;
  /** Keys to skip (e.g. "history" if rendered separately) */
  skipKeys?: string[];
}

const RawJsonCard: React.FC<RawJsonCardProps> = ({
  data,
  defaultExpanded = true,
  skipKeys = [],
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  if (!data || typeof data !== "object" || Array.isArray(data)) return null;

  const skipSet = new Set(skipKeys);
  const filteredData = Object.fromEntries(
    Object.entries(data).filter(([k]) => !skipSet.has(k)),
  );
  if (Object.keys(filteredData).length === 0) return null;

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
          <span className="text-slate-500">
            <FaCode size={14} />
          </span>
          <span className="font-semibold text-sm text-slate-700 dark:text-slate-200">
            Raw
          </span>
        </div>
      </button>
      {isExpanded && (
        <div className="px-4 py-3 bg-white dark:bg-slate-900">
          <pre className="text-xs text-slate-700 dark:text-slate-300 overflow-auto max-h-96 whitespace-pre-wrap">
            {JSON.stringify(filteredData, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

export default withDevIdentifier(RawJsonCard, 'RawJsonCard', 'amber');
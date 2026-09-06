/* LastChecked: 2026-09-05 | WhereUsed: Detail pages (raw JSON view) | WhoCreated: Unknown */
/**
 * RawJsonCard — Renders a collapsible card showing raw JSON.
 * First-level keys sorted alphabetically.
 * Uses --db-* CSS variables for theme-aware styling.
 */
import React, { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { FaCode } from "react-icons/fa";
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import { HighlightedJson } from '../syntaxHighlightJson';

export interface RawJsonCardProps {
  /** The JSON object to render */
  data: Record<string, unknown> | null | undefined;
  /** Start expanded (default: true) */
  defaultExpanded?: boolean;
  /** Keys to skip (e.g. "history" if rendered separately) */
  skipKeys?: string[];
}

/** Sort object keys alphabetically (first level only) */
function sortFirstLevel(obj: Record<string, unknown>): Record<string, unknown> {
  const sorted: Record<string, unknown> = {};
  for (const key of Object.keys(obj).sort()) {
    sorted[key] = obj[key];
  }
  return sorted;
}

const RawJsonCard: React.FC<RawJsonCardProps> = ({
  data,
  defaultExpanded = true,
  skipKeys = [],
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  if (!data || typeof data !== "object" || Array.isArray(data)) return null;

  const skipSet = new Set(skipKeys);
  const filteredData = sortFirstLevel(
    Object.fromEntries(Object.entries(data).filter(([k]) => !skipSet.has(k)))
  );
  if (Object.keys(filteredData).length === 0) return null;

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
          <span style={{ color: 'var(--db-text-muted)' }}>
            <FaCode size={14} />
          </span>
          <span className="font-semibold db-font-sm" style={{ color: 'var(--db-text)' }}>
            Raw
          </span>
        </div>
      </button>
      {isExpanded && (
        <div className="px-4 py-3" style={{ background: 'var(--db-surface)' }}>
          <pre className="db-font-xs font-mono overflow-auto max-h-96 whitespace-pre-wrap"
            style={{ color: 'var(--db-text)' }}>
            <HighlightedJson json={JSON.stringify(filteredData, null, 2)} />
          </pre>
        </div>
      )}
    </div>
  );
};

export default withDevIdentifier(RawJsonCard, 'RawJsonCard', 'amber', 'apps/common/components/detail/RawJsonCard.tsx');

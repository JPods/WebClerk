/**
 * JsonLeafSelector — browse a JSON tree and select leaf paths as fields.
 *
 * Two modes:
 *   - Selector: checkboxes to pick which dot-paths become columns/fields
 *   - Display:  label + formatted value for each selected leaf
 *
 * Formatting and labels come from fieldBehaviors (Pydantic-enforced).
 * This component only handles tree browsing, path resolution, and selection.
 *
 * Used by:
 *   - FieldOrderDialog (selector mode — picking columns from JSON envelopes)
 *   - DataBrowser detail, DynamicDetail (display mode — showing leaf values)
 *   - DataGrid (display mode — rendering dot-path cell values)
 */
import React, { useState, useCallback } from 'react';
import './JsonLeafSelector.css';

// ── Helpers ──────────────────────────────────────────────────────────

function isContainer(v: any): boolean {
  return v !== null && typeof v === 'object';
}

/** Resolve a dot-path to a value in a record. */
export function resolveLeaf(record: any, path: string): any {
  return path.split('.').reduce((o: any, k: string) => o?.[k], record);
}

// ── Selector mode ────────────────────────────────────────────────────

interface SelectorProps {
  /** The JSON data to browse */
  data: Record<string, any>;
  /** Parent field name (e.g., "totals", "price") */
  parentField: string;
  /** Currently selected dot-paths */
  selected: Set<string>;
  /** Called when a leaf is toggled — path and new selected state */
  onToggle: (path: string, isSelected: boolean) => void;
  /** fieldBehaviors for format/label lookup on leaf paths */
  fieldBehaviors?: Record<string, any>;
  /** Max tree depth */
  maxDepth?: number;
}

/** Selector tree — checkboxes to pick leaf paths from a JSON object.
 *  Labels and format badges come from fieldBehaviors when available.
 */
export function JsonLeafSelectorTree({
  data, parentField, selected, onToggle, fieldBehaviors, maxDepth = 5,
}: SelectorProps) {
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set([parentField]));

  const toggleExpand = useCallback((path: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      next.has(path) ? next.delete(path) : next.add(path);
      return next;
    });
  }, []);

  const renderNode = (key: string, value: any, path: string, depth: number): React.ReactNode => {
    const isObj = isContainer(value) && !Array.isArray(value);
    const isArr = Array.isArray(value);
    const isLeaf = !isObj && !isArr;
    const isExpanded = expanded.has(path);
    const isSelected = selected.has(path);
    const beh = fieldBehaviors?.[path];

    if (depth > maxDepth) return null;

    // Label: fieldBehaviors label if available, otherwise the key
    const label = beh?.label || key;

    // Value display: use fieldBehaviors format if available
    let valueDisplay = '';
    if (isLeaf) {
      if (value === null || value === undefined) {
        valueDisplay = '—';
      } else {
        valueDisplay = String(value);
      }
    }

    return (
      <React.Fragment key={path}>
        <div
          className={`jls-row ${isSelected ? 'jls-row--selected' : ''} ${isLeaf ? 'jls-row--leaf' : ''}`}
          style={{ paddingLeft: depth * 16 }}
        >
          {isObj ? (
            <button className="jls-chevron" onClick={() => toggleExpand(path)}>
              {isExpanded ? '▼' : '▶'}
            </button>
          ) : (
            <span className="jls-chevron-spacer" />
          )}

          {isLeaf ? (
            <input
              type="checkbox"
              className="jls-check"
              checked={isSelected}
              onChange={() => onToggle(path, !isSelected)}
            />
          ) : (
            <span className="jls-check-spacer" />
          )}

          <span className={`jls-key ${isLeaf ? '' : 'jls-key--parent'}`}>
            {label}
          </span>

          {isLeaf && (
            <span className="jls-value">
              {valueDisplay}
            </span>
          )}

          {isObj && (
            <span className="jls-type">{`{${Object.keys(value).length}}`}</span>
          )}
          {isArr && (
            <span className="jls-type">{`[${value.length}]`}</span>
          )}
        </div>

        {isObj && isExpanded && Object.entries(value).map(([k, v]) =>
          renderNode(k, v, `${path}.${k}`, depth + 1)
        )}
      </React.Fragment>
    );
  };

  return (
    <div className="jls-tree">
      {Object.entries(data).map(([k, v]) =>
        renderNode(k, v, `${parentField}.${k}`, 1)
      )}
    </div>
  );
}

// ── Display mode ─────────────────────────────────────────────────────

interface DisplayProps {
  /** The record containing JSON data */
  record: Record<string, any>;
  /** Dot-path to resolve (e.g., "totals.total") */
  path: string;
  /** fieldBehaviors for format/label */
  fieldBehaviors?: Record<string, any>;
}

/** Display a single leaf value with label.
 *  Label and format come from fieldBehaviors (Pydantic-enforced).
 *  Used in db.detail, ui.json, and DataGrid cells.
 */
export function JsonLeafDisplay({ record, path, fieldBehaviors }: DisplayProps) {
  const value = resolveLeaf(record, path);
  const beh = fieldBehaviors?.[path];
  const label = beh?.label || path.split('.').pop() || path;

  return (
    <span className="jls-display">
      <span className="jls-display-label">{label}</span>
      <span className="jls-display-value">
        {value === null || value === undefined ? '—' : String(value)}
      </span>
    </span>
  );
}

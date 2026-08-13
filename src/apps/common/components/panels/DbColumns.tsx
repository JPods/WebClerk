/**
 * DbColumns — base list component for all tabular displays.
 *
 * Every list in the application inherits from this: DataBrowser grid,
 * panel tables, comm lists, transaction lines. One source of truth for
 * column headers, row rendering, hover/selection, and column config.
 *
 * All styling via --db-* CSS variables (DataBrowser.css).
 * No Tailwind dark: classes. No hard-coded colors.
 *
 * DbList (DataBrowser) extends this by adding toolbar + pagination.
 *
 * Usage:
 *   <DbColumns
 *     storageKey="panel:contact:emails"
 *     columns={EMAIL_COLUMNS}
 *     data={emails}
 *     rowKey={(r) => r.id}
 *   />
 *
 *   // With section header:
 *   <DbColumns
 *     storageKey="panel:contact:emails"
 *     columns={EMAIL_COLUMNS}
 *     data={emails}
 *     rowKey={(r) => r.id}
 *     sectionLabel="Email"
 *     sectionIcon="✉"
 *     onAdd={() => setAdding(true)}
 *   />
 *
 *   // With custom row rendering (card style):
 *   <DbColumns
 *     storageKey="panel:contact:emails"
 *     columns={EMAIL_COLUMNS}
 *     data={emails}
 *     rowKey={(r) => r.id}
 *     renderRow={(record, columns) => <CommCard ... />}
 *   />
 */
import React, { useMemo, useState } from "react";
import { FaSlidersH } from "react-icons/fa";
import FieldOrderDialog from "@/components/common/FieldOrderDialog";
import { useListFieldConfig } from "@/hooks/useListFieldConfig";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface DbColumnDef<T = Record<string, unknown>> {
  /** Unique column key */
  key: string;
  /** Header label */
  label: string;
  /** Render a cell value */
  render: (record: T) => React.ReactNode;
  /** Start visible? (default true) */
  defaultVisible?: boolean;
  /** Flex basis or fixed width */
  width?: string;
  /** Extra CSS class on header + body cells */
  className?: string;
}

export interface DbColumnsProps<T = Record<string, unknown>> {
  /** localStorage / Setting persistence key */
  storageKey: string;
  /** Column definitions */
  columns: DbColumnDef<T>[];
  /** Row data */
  data: T[];
  /** Unique key per row */
  rowKey: (record: T) => string | number;
  /** Optional: currently selected row key */
  selectedKey?: string | number | null;
  /** Optional: row click handler */
  onSelectRow?: (record: T) => void;
  /** Optional: row action button (e.g. open in new window) */
  onRowAction?: (record: T) => void;
  /** Optional: section header label (e.g. "Email") */
  sectionLabel?: string;
  /** Optional: section icon */
  sectionIcon?: string;
  /** Optional: add button callback — shows "+ add" in section header */
  onAdd?: () => void;
  /** Optional: collapsible section (default true if sectionLabel provided) */
  collapsible?: boolean;
  /** Optional: start collapsed */
  defaultCollapsed?: boolean;
  /** Optional: custom row renderer — overrides default columnar rendering */
  renderRow?: (record: T, columns: DbColumnDef<T>[]) => React.ReactNode;
  /** Optional: content to render after the list (e.g. an "adding" form) */
  children?: React.ReactNode;
  /** Optional: compact row padding */
  compact?: boolean;
  /** Optional: hide column headers (for card-style rendering) */
  hideHeaders?: boolean;
  /** Optional: empty state message */
  emptyMessage?: string;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function DbColumns<T extends Record<string, unknown>>({
  storageKey,
  columns,
  data,
  rowKey,
  selectedKey = null,
  onSelectRow,
  onRowAction,
  sectionLabel,
  sectionIcon,
  onAdd,
  collapsible = true,
  defaultCollapsed = false,
  renderRow,
  children,
  compact = false,
  hideHeaders = false,
  emptyMessage,
}: DbColumnsProps<T>) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  // Column config persistence
  const tableColumns = useMemo(
    () => columns.map((c) => ({ id: c.key, name: c.label })),
    [columns],
  );
  const fc = useListFieldConfig(storageKey, tableColumns);

  // Visible columns in configured order
  const visibleColumns = useMemo(() => {
    const colMap = new Map(columns.map((c) => [c.key, c]));
    return fc.effectiveKeys
      .map((k) => colMap.get(k))
      .filter((c): c is DbColumnDef<T> => !!c);
  }, [fc.effectiveKeys, columns]);

  const hasSectionHeader = !!sectionLabel;
  const showContent = !hasSectionHeader || !collapsible || !collapsed;

  return (
    <div>
      {/* ── Section header ─────────────────────────────────────────── */}
      {hasSectionHeader && (
        <div
          className="db-section-header"
          onClick={() => collapsible && setCollapsed((c) => !c)}
        >
          {collapsible && (
            <span style={{ fontSize: 9, color: 'var(--db-text-dim)' }}>
              {collapsed ? '▶' : '▼'}
            </span>
          )}
          {sectionIcon && (
            <span style={{ fontSize: 10 }}>{sectionIcon}</span>
          )}
          <span className="db-section-header__label">{sectionLabel}</span>
          <span className="db-section-header__count">({data.length})</span>
          {onAdd && (
            <button
              className="db-section-header__action"
              onClick={(e) => { e.stopPropagation(); onAdd(); }}
            >
              + add
            </button>
          )}
        </div>
      )}

      {showContent && (
        <>
          {/* ── Column headers ────────────────────────────────────── */}
          {!hideHeaders && visibleColumns.length > 0 && (
            <div className="db-list-header">
              {visibleColumns.map((col) => (
                <span
                  key={col.key}
                  className={`db-list-header__cell ${col.className ?? ""}`}
                  style={col.width ? { width: col.width, flexShrink: 0 } : { flex: 1 }}
                >
                  {col.label}
                </span>
              ))}
              <button
                type="button"
                title="Configure columns"
                className="db-list-header__action"
                onClick={(e) => {
                  e.stopPropagation();
                  fc.toggleDialog();
                }}
              >
                <FaSlidersH size={10} />
              </button>
            </div>
          )}

          {/* ── Data rows ─────────────────────────────────────────── */}
          {data.map((record) => {
            const rk = rowKey(record);
            const isSelected = selectedKey != null && rk === selectedKey;

            // Custom row renderer
            if (renderRow) {
              return (
                <div key={rk} className={isSelected ? 'db-list-row--checked' : ''}>
                  {renderRow(record, visibleColumns)}
                </div>
              );
            }

            // Default columnar row
            return (
              <div
                key={rk}
                className={`db-list-row ${isSelected ? 'db-list-row--checked' : ''}`}
                style={{ padding: compact ? '3px 12px' : '6px 12px' }}
                onClick={() => onSelectRow?.(record)}
              >
                <div className="db-list-row__indicator" />
                {visibleColumns.map((col) => (
                  <span
                    key={col.key}
                    className={col.className ?? ""}
                    style={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      ...(col.width ? { width: col.width, flexShrink: 0 } : { flex: 1 }),
                    }}
                  >
                    {col.render(record)}
                  </span>
                ))}
                {onRowAction && (
                  <button
                    type="button"
                    title="Open"
                    className="db-list-header__action"
                    style={{ marginLeft: 'auto' }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onRowAction(record);
                    }}
                  >
                    &#8599;
                  </button>
                )}
              </div>
            );
          })}

          {/* ── Empty state ───────────────────────────────────────── */}
          {data.length === 0 && !children && (
            <div className="db-list-empty">
              {emptyMessage ?? `No ${sectionLabel?.toLowerCase() ?? 'records'}`}
            </div>
          )}

          {/* ── Extra content (e.g. "adding" form) ───────────────── */}
          {children}
        </>
      )}

      {/* ── Column config dialog ───────────────────────────────── */}
      <FieldOrderDialog {...fc.fieldOrderDialogProps} />
    </div>
  );
}

// Re-export types for backward compatibility
export type PanelColumnDef<T = Record<string, unknown>> = DbColumnDef<T>;
export type PanelTableProps<T = Record<string, unknown>> = DbColumnsProps<T>;

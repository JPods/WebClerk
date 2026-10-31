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
import React, { useMemo } from "react";
import { PanelFrame } from "@/apps/common/components/CollapsiblePanel";
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
  /** The WC List Standard (Bill, 2026-10-31): given, a click selects (Shift range, Cmd toggle,
   *  ↑↓ move), double-click or Enter opens the row — its card beside the row, or its window —
   *  and Option-double-click opens it in a browser window of its own. */
  onOpenRow?: (record: T, anchor: HTMLElement) => void;
  onOpenWindow?: (record: T) => void;
  /** A plain click or arrow went to this row: an open card follows it. */
  onMoveRow?: (record: T, anchor: HTMLElement) => void;
  /** The row whose card is open: outlined apart from the selection. */
  openKey?: string | number | null;
  /** Optional: section header label (e.g. "Email") */
  sectionLabel?: string;
  /** Optional: section icon */
  sectionIcon?: string;
  /** "+ add" in the panel's header: the button is the anchor its card opens beside
   *  (usePanelAdd — Bill, 2026-10-30). */
  onAdd?: (anchor: HTMLElement) => void;
  /** Optional: assign existing record — shows "assign" in section header */
  onAssign?: () => void;
  /** Optional: remove panel — Option+Cmd/Ctrl+click on header */
  onRemove?: () => void;
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
  /** Optional: the rows are being read / could not be read — shown by the panel frame. */
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function DbColumns<T extends object>({
  storageKey,
  columns,
  data,
  rowKey,
  selectedKey = null,
  onSelectRow,
  onRowAction,
  onOpenRow,
  onOpenWindow,
  onMoveRow,
  openKey = null,
  sectionLabel,
  sectionIcon,
  onAdd,
  onAssign,
  onRemove,
  collapsible = true,
  defaultCollapsed = false,
  renderRow,
  children,
  compact = false,
  hideHeaders = false,
  emptyMessage,
  loading,
  error,
  onRetry,
}: DbColumnsProps<T>) {

  // Column config persistence — pass default-visible columns as initial set
  // so useListFieldConfig only shows those when no saved config exists
  const tableColumns = useMemo(
    () => columns.filter((c) => c.defaultVisible !== false).map((c) => ({ id: c.key, name: c.key })),
    [columns],
  );
  const allTableColumns = useMemo(
    () => columns.map((c) => ({ id: c.key, name: c.key })),
    [columns],
  );
  const fc = useListFieldConfig(storageKey, tableColumns);

  // Visible columns in configured order
  const visibleColumns = useMemo(() => {
    const colMap = new Map(columns.map((c) => [c.key, c]));
    const result = fc.effectiveKeys
      .map((k) => colMap.get(k))
      .filter((c): c is DbColumnDef<T> => !!c);
    if (result.length === 0 && columns.length > 0) {
      console.warn(`[DbColumns] ${storageKey}: 0 visible from ${columns.length} columns. effectiveKeys:`, fc.effectiveKeys, 'colMap keys:', Array.from(colMap.keys()));
    }
    return result;
  }, [fc.effectiveKeys, columns, storageKey]);

  const hasSectionHeader = !!sectionLabel;

  // ── Selection (the WC List Standard) ──
  const standard = !!onOpenRow;
  const [picked, setPicked] = React.useState<Set<string | number>>(new Set());
  const anchorKey = React.useRef<string | number | null>(null);
  const cursorKey = React.useRef<string | number | null>(null);
  const listRef = React.useRef<HTMLDivElement>(null);
  const keys = data.map(rowKey);
  const rowEl = (k: string | number) =>
    listRef.current?.querySelector<HTMLElement>(`[data-row-key="${CSS.escape(String(k))}"]`) ?? null;
  const go = (k: string | number, extend: boolean) => {
    const to = keys.indexOf(k);
    if (extend && anchorKey.current != null && keys.includes(anchorKey.current)) {
      const from = keys.indexOf(anchorKey.current);
      setPicked(new Set(keys.slice(Math.min(from, to), Math.max(from, to) + 1)));
    } else {
      setPicked(new Set([k]));
      anchorKey.current = k;
      const el = rowEl(k);
      if (el) onMoveRow?.(data[to], el);
    }
    cursorKey.current = k;
  };
  const rowGestures = (record: T, k: string | number) => standard ? {
    'data-row-key': String(k),
    onMouseDown: (e: React.MouseEvent) => { if (e.shiftKey || e.detail > 1) e.preventDefault(); },
    onClick: (e: React.MouseEvent) => {
      if (e.metaKey || e.ctrlKey) {
        setPicked((p) => { const n = new Set(p); if (n.has(k)) n.delete(k); else n.add(k); return n; });
        anchorKey.current = k; cursorKey.current = k;
      } else go(k, e.shiftKey);
      listRef.current?.focus({ preventScroll: true });
    },
    onDoubleClick: (e: React.MouseEvent) => {
      if (e.altKey) onOpenWindow?.(record);
      else onOpenRow!(record, e.currentTarget as HTMLElement);
    },
  } : {};
  const onListKey = (e: React.KeyboardEvent) => {
    if (!standard || !['ArrowUp', 'ArrowDown', 'Enter'].includes(e.key) || !keys.length) return;
    if ((e.target as HTMLElement).closest('input, select, textarea')) return;
    e.preventDefault();
    const at = cursorKey.current != null ? keys.indexOf(cursorKey.current) : -1;
    if (e.key === 'Enter') {
      const el = at >= 0 ? rowEl(keys[at]) : null;
      if (el) onOpenRow!(data[at], el);
      return;
    }
    const to = at < 0 ? 0 : Math.max(0, Math.min(keys.length - 1, at + (e.key === 'ArrowDown' ? 1 : -1)));
    go(keys[to], e.shiftKey);
    rowEl(keys[to])?.scrollIntoView({ block: 'nearest' });
  };
  // Real extra content only: a caller's {cond && <X/>} hands over false, not nothing.
  const hasChildren = React.Children.toArray(children).length > 0;

  const table = (
    <>
      {/* ── Column headers: they stay in view while the rows scroll (TFTS 2026-10-27); no rows,
           no labels — the empty message stands alone ── */}
      {!hideHeaders && visibleColumns.length > 0 && data.length > 0 && (
        <div className="db-list-header"
             style={{ position: 'sticky', top: 0, zIndex: 1, background: 'var(--db-surface-alt, var(--db-surface, #fff))' }}>
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
        const isSelected = standard ? picked.has(rk) : selectedKey != null && rk === selectedKey;
        const isOpen = standard && openKey != null && rk === openKey;
        const openStyle = isOpen ? { outline: '2px solid var(--db-accent, #0d6efd)', outlineOffset: -2 } : undefined;

        // Custom row renderer
        if (renderRow) {
          return (
            <div key={rk} className={isSelected ? 'db-list-row--checked' : ''} style={openStyle} {...rowGestures(record, rk)}>
              {renderRow(record, visibleColumns)}
            </div>
          );
        }

        // Default columnar row
        return (
          <div
            key={rk}
            className={`db-list-row ${isSelected ? 'db-list-row--checked' : ''}`}
            style={{ padding: compact ? '3px 12px' : '6px 12px', ...openStyle }}
            onClick={standard ? undefined : () => onSelectRow?.(record)}
            {...rowGestures(record, rk)}
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

      {/* ── Empty state: a bare table says it; a framed one lets the frame say it ── */}
      {!hasSectionHeader && data.length === 0 && !hasChildren && (
        <div className="db-list-empty">{emptyMessage ?? 'No records'}</div>
      )}

      {/* ── Extra content (e.g. "adding" form) ───────────────── */}
      {children}

      {/* ── Column config dialog ───────────────────────────────── */}
      <FieldOrderDialog {...fc.fieldOrderDialogProps} allFields={allTableColumns.map(c => String(c.name))} />
    </>
  );

  const headerActions = React.useMemo(() => (onAdd || onAssign) ? (
    <>
      {onAdd && (
        <button type="button" className="db-section-header__action" data-wc="panel-add"
          onClick={(e) => { e.stopPropagation(); onAdd(e.currentTarget); }}>+ add</button>
      )}
      {onAssign && <button type="button" className="db-section-header__action" onClick={onAssign}>assign</button>}
    </>
  ) : undefined, [onAdd, onAssign]);

  const list = standard
    ? <div ref={listRef} tabIndex={0} onKeyDown={onListKey} style={{ outline: 'none' }}
        data-help="Click selects; Shift-click or Shift+arrow extends; Cmd-click toggles; ↑↓ move. Double-click or Enter opens the record; Option-double-click opens it in its own window. With a card open, a click or arrow shows that row.">{table}</div>
    : table;

  if (!hasSectionHeader) return <div>{list}</div>;

  // A labelled table is a panel: the one frame draws its header, count, collapse and status —
  // its own frame standing alone, the frame around it when it sits in one (a record's tab).
  return (
    <PanelFrame
      label={sectionLabel!}
      icon={sectionIcon}
      storageKey={`${storageKey}:collapsed`}
      defaultCollapsed={defaultCollapsed}
      collapsible={collapsible}
      keepMounted
      badge={data.length}
      onRemove={onRemove}
      headerActions={headerActions}
      status={{ loading: !!loading && data.length === 0, error: error ?? null, onRetry,
                empty: !loading && !error && data.length === 0 && !hasChildren,
                emptyText: emptyMessage ?? `No ${sectionLabel!.toLowerCase()}` }}
    >
      {list}
    </PanelFrame>
  );
}

// Re-export types under panel naming convention
export type PanelColumnDef<T = Record<string, unknown>> = DbColumnDef<T>;
export type PanelTableProps<T = Record<string, unknown>> = DbColumnsProps<T>;

/**
 * DbColumns — the base of every list of rows (Bill, 2026-11-01: "DbColumn is the parent that
 * DataGrid inherits and expands on … relatively simple list displays in panels and more complex
 * in db.lists"; "cascade or tree list might inherit but not be part of DbColumn").
 *
 *   DbColumnsTable  the one table: header labels, rows, cell format and alignment, group
 *                   headings, and the slots an extension fills (header cells and rows, row and
 *                   cell props, a cell's prefix, the footer). Nothing about selection or data.
 *   DbColumns       DbColumnsTable + the column dialog (storageKey) + the WC List Standard
 *                   gestures + the panel frame. Every panel list.
 *   DataGrid        DbColumnsTable + filters, sort, edit-in-list, Σ totals, dupes, color rules,
 *                   column menu. The record lists and transaction lines (components/common).
 *   TreeList        DbColumns + parent/child collapse and indent (./TreeList).
 *
 * Cells format through cellFormat — one look for a value in every list. All styling is the
 * --db-* CSS variables (DbColumns.css).
 *
 *   <DbColumns storageKey="panel:contact:emails" columns={EMAIL_COLUMNS} data={emails}
 *              rowKey={(r) => r.id} sectionLabel="Email" onAdd={(el) => add(el)} />
 */
import React, { useMemo } from "react";
import { PanelFrame } from "@/apps/common/components/CollapsiblePanel";
import { FaSlidersH } from "react-icons/fa";
import FieldOrderDialog from "@/components/common/FieldOrderDialog";
import { useListFieldConfig } from "@/hooks/useListFieldConfig";
import { useListGestures } from "@/hooks/useListGestures";
import "./DbColumns.css";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface DbColumnDef<T = Record<string, unknown>> {
  /** Unique column key (the field, for a field column) */
  key: string;
  /** Header label */
  label: React.ReactNode;
  /** A cell's content */
  render: (record: T) => React.ReactNode;
  /** Start visible? (default true) */
  defaultVisible?: boolean;
  /** Width: px number or a CSS length */
  width?: number | string;
  /** Where values sit (cellAlign decides when not given) */
  align?: 'left' | 'right' | 'center';
  /** Extra CSS class on the body cells */
  className?: string;
  /** The header label's look (cellFormat.headerStyle) */
  headerStyle?: React.CSSProperties;
  /** A value the server calculated: shown italic */
  calculated?: boolean;
}

type Key = string | number;
/** A row's attributes: classes, style, handlers, data-* and aria-* (the gestures' rowProps). */
type RowProps = React.HTMLAttributes<HTMLTableRowElement> & Record<string, unknown>;

export interface DbColumnsTableProps<T> {
  columns: DbColumnDef<T>[];
  rows: T[];
  rowKey: (record: T) => Key;
  compact?: boolean;
  /** Explicit column widths and a table as wide as their sum (scrolls sideways); otherwise the
   *  table fills its container. */
  fixedWidths?: boolean;
  /** Show the column labels with no rows (a filter row needs them). Default: hidden when empty. */
  headerWhenEmpty?: boolean;
  /** An extension's own header cell: its props and content (sort, drag, resize, menu). */
  headerCell?: (col: DbColumnDef<T>, index: number) => { props?: React.ThHTMLAttributes<HTMLTableCellElement>; content?: React.ReactNode } | undefined;
  /** Something at the right end of the label row (the column dialog's button). */
  headerTrailer?: React.ReactNode;
  /** More header rows under the labels (a filter row). */
  headerRows?: React.ReactNode;
  /** Footer rows (Σ totals). */
  footer?: React.ReactNode;
  /** A row's props: classes, style, gestures. */
  rowProps?: (record: T, index: number) => RowProps | undefined;
  /** The left bar that marks a selected row. */
  marked?: (record: T) => boolean;
  /** A cell's props: classes, handlers, title. */
  cellProps?: (record: T, col: DbColumnDef<T>) => React.TdHTMLAttributes<HTMLTableCellElement> | undefined;
  /** A cell's content instead of col.render (an editor while editing). */
  renderCell?: (record: T, col: DbColumnDef<T>) => React.ReactNode | undefined;
  /** Before a cell's content (a tree's indent and chevron). */
  cellPrefix?: (record: T, col: DbColumnDef<T>, index: number) => React.ReactNode;
  /** Rows under a heading per group, groups in the order first met. */
  groupBy?: (record: T) => string;
  groupLabel?: (group: string, records: T[]) => React.ReactNode;
  groupSummary?: (records: T[]) => React.ReactNode;
  /** A heading click folds its group. */
  collapsibleGroups?: boolean;
  /** The marking column sticks at the left (a pinned first column). */
  pinnedIndicator?: boolean;
  /** Shown when there are no rows. */
  empty?: React.ReactNode;
  /** The scrolling container's props and ref (gestures' list props, drag-scroll). */
  scroll?: boolean;
  containerProps?: React.HTMLAttributes<HTMLDivElement>;
  containerRef?: React.Ref<HTMLDivElement>;
}

// ── The one table ─────────────────────────────────────────────────────────────

const px = (w: number | string | undefined) => (typeof w === 'number' ? `${w}px` : w);

export function DbColumnsTable<T>({
  columns, rows, rowKey, compact, fixedWidths, headerWhenEmpty, headerCell, headerTrailer,
  headerRows, footer, rowProps, marked, cellProps, renderCell, cellPrefix, groupBy, groupLabel,
  groupSummary, collapsibleGroups, pinnedIndicator, empty, scroll, containerProps, containerRef,
}: DbColumnsTableProps<T>) {
  const [folded, setFolded] = React.useState<Set<string>>(new Set());

  const groups = useMemo(() => {
    if (!groupBy) return null;
    const m = new Map<string, T[]>();
    rows.forEach((r) => {
      const g = groupBy(r);
      if (!m.has(g)) m.set(g, []);
      m.get(g)!.push(r);
    });
    return m;
  }, [rows, groupBy]);

  const tableWidth = fixedWidths
    ? 8 + columns.reduce((s, c) => s + (typeof c.width === 'number' ? c.width : 120), 0)
    : undefined;

  const row = (record: T, index: number) => {
    const key = rowKey(record);
    const given = rowProps?.(record, index) ?? {};
    return (
      <tr key={key} role="row" {...given}
          className={['dg-row', compact ? 'dg-row--compact' : '', given.className ?? ''].join(' ').trim()}>
        <td className={`dg-td-indicator${pinnedIndicator ? ' dg-td-indicator--pinned' : ''}`} role="gridcell">{marked?.(record) && <div className="dg-check-bar" />}</td>
        {columns.map((col) => {
          const cp = cellProps?.(record, col) ?? {};
          const content = renderCell?.(record, col);
          return (
            <td key={col.key} role="gridcell" {...cp}
                className={['dg-td', col.calculated ? 'dg-td--calculated' : '', col.className ?? '', cp.className ?? ''].join(' ').trim()}
                style={{ textAlign: col.align, width: px(col.width), minWidth: px(col.width), ...cp.style }}>
              {cellPrefix?.(record, col, index)}
              {content !== undefined ? content : col.render(record)}
            </td>
          );
        })}
      </tr>
    );
  };

  const showHeader = columns.length > 0 && (rows.length > 0 || headerWhenEmpty);
  const table = (
    <table className={`dg-table${fixedWidths ? '' : ' dg-table--fluid'}`} style={tableWidth ? { width: tableWidth } : undefined}>
      {showHeader && (
        <thead>
          <tr className="dg-thead-row" role="row">
            <th className={`dg-th-indicator${pinnedIndicator ? ' dg-th-indicator--pinned' : ''}`} role="columnheader" />
            {columns.map((col, i) => {
              const own = headerCell?.(col, i);
              const last = i === columns.length - 1;
              return (
                <th key={col.key} role="columnheader" {...own?.props}
                    className={['dg-th', col.calculated ? 'dg-th--calculated' : '', own?.props?.className ?? ''].join(' ').trim()}
                    style={{ textAlign: col.align, width: px(col.width), minWidth: px(col.width), ...own?.props?.style }}>
                  {own?.content ?? <span style={col.headerStyle}>{col.label}</span>}
                  {last && headerTrailer}
                </th>
              );
            })}
          </tr>
          {headerRows}
        </thead>
      )}
      <tbody>
        {groups
          ? Array.from(groups.entries()).map(([g, recs]) => (
              <React.Fragment key={`group:${g}`}>
                <tr className="dg-group-row" role="row"
                    onClick={collapsibleGroups ? () => setFolded((p) => { const n = new Set(p); if (n.has(g)) n.delete(g); else n.add(g); return n; }) : undefined}>
                  <td colSpan={columns.length + 1} className="dg-group-label">
                    {collapsibleGroups && (folded.has(g) ? '▶ ' : '▼ ')}
                    {groupLabel ? groupLabel(g, recs) : g}
                    {groupSummary && <span className="dg-group-summary">{groupSummary(recs)}</span>}
                  </td>
                </tr>
                {!folded.has(g) && recs.map((r) => row(r, rows.indexOf(r)))}
              </React.Fragment>
            ))
          : rows.map(row)}
      </tbody>
      {footer && <tfoot>{footer}</tfoot>}
    </table>
  );

  return (
    <div ref={containerRef} {...containerProps}
         className={[scroll ? 'dg-scroll' : 'dg-flow', containerProps?.className ?? ''].join(' ').trim()}>
      {table}
      {rows.length === 0 && empty}
    </div>
  );
}

// ── DbColumns: a panel's list ─────────────────────────────────────────────────

export interface DbColumnsProps<T = Record<string, unknown>> {
  /** localStorage / Setting persistence key for the column dialog */
  storageKey: string;
  columns: DbColumnDef<T>[];
  data: T[];
  rowKey: (record: T) => Key;
  /** The WC List Standard (Bill, 2026-10-31): given, a click selects (Shift range, Cmd toggle,
   *  ↑↓ move), double-click or Enter opens the row — its card beside the row, or its window —
   *  and Option-double-click opens it in a browser window of its own. */
  onOpenRow?: (record: T, anchor: HTMLElement) => void;
  onOpenWindow?: (record: T) => void;
  /** A plain click or arrow went to this row: an open card follows it. */
  onMoveRow?: (record: T, anchor: HTMLElement) => void;
  /** The row whose card is open: outlined apart from the selection. */
  openKey?: Key | null;
  /** A button at the end of each row (CommPanel's delete). */
  onRowAction?: (record: T) => void;
  /** A panel: its frame's label, icon and header buttons */
  sectionLabel?: string;
  sectionIcon?: string;
  /** "+ add" in the panel's header: the button is the anchor its card opens beside. */
  onAdd?: (anchor: HTMLElement) => void;
  onAssign?: () => void;
  /** Remove panel — Option+Cmd/Ctrl+click on header */
  onRemove?: () => void;
  /** A panel's own buttons beside "+ add" (Build from BOM, upload). */
  extraActions?: React.ReactNode;
  /** Rows under a heading per group (layers by warehouse); the heading carries their sum. */
  groupBy?: (record: T) => string;
  groupSummary?: (records: T[]) => React.ReactNode;
  /** Rows shown faint (lines outside the selection a margin total is for). */
  dimmed?: (record: T) => boolean;
  /** Before a cell's content — TreeList's indent and chevron. */
  cellPrefix?: (record: T, col: DbColumnDef<T>, index: number) => React.ReactNode;
  collapsible?: boolean;
  defaultCollapsed?: boolean;
  /** Content after the list (an "adding" form, an upload) */
  children?: React.ReactNode;
  compact?: boolean;
  emptyMessage?: string;
  /** The rows are being read / could not be read — shown by the panel frame. */
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

export function DbColumns<T extends object>({
  storageKey, columns, data, rowKey, onOpenRow, onOpenWindow, onMoveRow, openKey = null,
  onRowAction, sectionLabel, sectionIcon, onAdd, onAssign, onRemove, extraActions, groupBy,
  groupSummary, dimmed, cellPrefix, collapsible = true, defaultCollapsed = false, children,
  compact = false, emptyMessage, loading, error, onRetry,
}: DbColumnsProps<T>) {
  // The column dialog: which columns show, in what order — saved under storageKey.
  const initial = useMemo(
    () => columns.filter((c) => c.defaultVisible !== false).map((c) => ({ id: c.key, name: c.key })),
    [columns],
  );
  const fc = useListFieldConfig(storageKey, initial);
  const visible = useMemo(() => {
    const byKey = new Map(columns.map((c) => [c.key, c]));
    const shown = fc.effectiveKeys.map((k) => byKey.get(k)).filter((c): c is DbColumnDef<T> => !!c);
    if (!onRowAction) return shown;
    return [...shown, {
      key: '_row_action', label: '', width: 28, align: 'center' as const,
      render: (r: T) => (
        <button type="button" title="Open" className="db-list-header__action"
          onClick={(e) => { e.stopPropagation(); onRowAction(r); }}>&#8599;</button>
      ),
    }];
  }, [fc.effectiveKeys, columns, onRowAction]);

  // ── Selection: the WC List Standard, the same code as the record list (useListGestures) ──
  const standard = !!onOpenRow;
  const [picked, setPicked] = React.useState<Set<Key>>(new Set());
  const byKey = (k: Key) => data.find((r) => rowKey(r) === k);
  const gestures = useListGestures<Key>({
    enabled: standard,
    keys: () => data.map(rowKey),
    selected: picked,
    select: (next, moved) => {
      setPicked(next);
      const record = moved != null ? byKey(moved) : undefined;
      const el = moved != null ? gestures.rowEl(moved) : null;
      if (record && el) onMoveRow?.(record, el);
    },
    open: (k, el) => { const r = byKey(k); if (r) onOpenRow!(r, el); },
    openWindow: (k) => { const r = byKey(k); if (r) onOpenWindow?.(r); },
  });
  // Real extra content only: a caller's {cond && <X/>} hands over false, not nothing.
  const hasChildren = React.Children.toArray(children).length > 0;
  const framed = !!sectionLabel;

  const list = (
    <>
      <DbColumnsTable<T>
        columns={visible}
        rows={data}
        rowKey={rowKey}
        compact={compact}
        groupBy={groupBy}
        groupSummary={groupSummary}
        marked={(r) => standard && picked.has(rowKey(r))}
        rowProps={(r) => {
          const k = rowKey(r);
          const classes = [
            standard && picked.has(k) ? 'dg-row--checked' : '',
            standard && openKey != null && k === openKey ? 'dg-row--open' : '',
            dimmed?.(r) ? 'dg-row--dimmed' : '',
          ].filter(Boolean).join(' ');
          return { ...(standard ? gestures.rowProps(k) : {}), className: classes };
        }}
        cellPrefix={cellPrefix}
        headerTrailer={
          <button type="button" title="Configure columns" className="dg-th-trailer"
            onClick={(e) => { e.stopPropagation(); fc.toggleDialog(); }}>
            <FaSlidersH size={10} />
          </button>
        }
        containerProps={standard ? { ...gestures.listProps, style: { outline: 'none' } } : undefined}
        // A bare list says it is empty; a framed one lets the frame say it.
        empty={!framed && !hasChildren ? <div className="dg-empty">{emptyMessage ?? 'No records'}</div> : undefined}
      />
      {children}
      <FieldOrderDialog {...fc.fieldOrderDialogProps} allFields={columns.map((c) => c.key)} />
    </>
  );

  const headerActions = React.useMemo(() => (onAdd || onAssign || extraActions) ? (
    <>
      {extraActions}
      {onAdd && (
        <button type="button" className="db-section-header__action" data-wc="panel-add"
          onClick={(e) => { e.stopPropagation(); onAdd(e.currentTarget); }}>+ add</button>
      )}
      {onAssign && <button type="button" className="db-section-header__action" onClick={onAssign}>assign</button>}
    </>
  ) : undefined, [onAdd, onAssign, extraActions]);

  if (!framed) return <div>{list}</div>;

  // A labelled list is a panel: the one frame draws its header, count, collapse and status —
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

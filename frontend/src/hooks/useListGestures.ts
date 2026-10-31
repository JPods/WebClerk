/**
 * useListGestures — the WC List Standard's gestures, one code for every list (Bill, 2026-10-31:
 * "all panels and lists have the same inherited code and only very rare specialty behaviors").
 *
 *   Click            selects that row (never opens); with a record open, it follows (moved)
 *   Shift+click / ↑↓ range from the anchor;   Cmd/Ctrl+click toggles one row
 *   ↑ / ↓            moves the selection;     Enter or double-click opens;  Option+double-click
 *                    opens a browser window of its own
 *
 * The list owns its selection and what "open" shows (db.list: the form; a panel: the card or
 * the record's window). Rows carry rowProps(key); the scrolling element carries listProps.
 * Docs: webclerk-site docs/architecture/list-selection-standard.md
 *
 * LastChecked: 2026-10-31 | WhereUsed: DataGrid, DbColumns | WhoCreated: Bill+Claude
 */
import React, { useCallback, useRef } from 'react';

type Key = string | number;

/** Shift+hover on a list (the Shift-for-Help standard): what its gestures do. */
export const LIST_HELP = 'Click selects; Shift-click or Shift+arrow extends; Cmd-click toggles; ↑↓ move. '
  + 'Double-click or Enter opens the record; Option-double-click opens it in its own window. '
  + 'With the record open, a click or arrow shows that row (unsaved changes can be undone).';
/** …and while edit-in-list is on. */
export const EDIT_IN_LIST_HELP = ' Editing in list: double-click a cell to edit; it saves when you leave it '
  + '(Enter down, Tab right, Esc cancels).';

interface Options<K extends Key> {
  /** The rows' keys in the order shown. */
  keys: () => K[];
  selected: Set<K>;
  /** The new selection; `moved` is the one row a plain click or arrow went to. */
  select: (next: Set<K>, moved?: K) => void;
  open: (key: K, row: HTMLElement) => void;
  openWindow?: (key: K) => void;
  /** Off: the list keeps its own handling (a picker, a grid with no record to open). */
  enabled?: boolean;
  /** The keyboard belongs to something else for now (a cell being edited). */
  busy?: () => boolean;
  /** The list's own scrolling element, when it already has a ref. */
  listRef?: React.RefObject<HTMLDivElement | null>;
  /** Shift+hover text, when the list says more than LIST_HELP. */
  help?: string;
}

export function useListGestures<K extends Key>({ keys, selected, select, open, openWindow, enabled = true, busy, listRef: given, help = LIST_HELP }: Options<K>) {
  const own = useRef<HTMLDivElement>(null);
  const listRef = given ?? own;
  const anchor = useRef<K | null>(null);
  const cursor = useRef<K | null>(null);

  const rowEl = useCallback((k: K) =>
    listRef.current?.querySelector<HTMLElement>(`[data-row-key="${CSS.escape(String(k))}"]`) ?? null, []);

  const go = useCallback((k: K, extend: boolean) => {
    const all = keys();
    if (extend && anchor.current != null && all.includes(anchor.current)) {
      const from = all.indexOf(anchor.current), to = all.indexOf(k);
      select(new Set(all.slice(Math.min(from, to), Math.max(from, to) + 1)));
    } else {
      select(new Set([k]), k);
      anchor.current = k;
    }
    cursor.current = k;
  }, [keys, select]);

  const rowProps = (k: K) => enabled ? {
    'data-row-key': String(k),
    // Shift-click and double-click are list gestures: they must not select the page's text.
    onMouseDown: (e: React.MouseEvent) => { if (e.shiftKey || e.detail > 1) e.preventDefault(); },
    onClick: (e: React.MouseEvent) => {
      if (e.metaKey || e.ctrlKey) {
        const next = new Set(selected);
        if (next.has(k)) next.delete(k); else next.add(k);
        select(next);
        anchor.current = k; cursor.current = k;
      } else go(k, e.shiftKey);
      // Clicking puts the keyboard in the list, so the arrows move from here.
      listRef.current?.focus({ preventScroll: true });
    },
    onDoubleClick: (e: React.MouseEvent) => {
      if (e.altKey) openWindow?.(k);
      else open(k, e.currentTarget as HTMLElement);
    },
  } : {};

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!['ArrowUp', 'ArrowDown', 'Enter'].includes(e.key) || busy?.()) return;
    if ((e.target as HTMLElement).closest('input, select, textarea')) return;
    const all = keys();
    if (!all.length) return;
    e.preventDefault();
    const at = cursor.current != null ? all.indexOf(cursor.current) : -1;
    if (e.key === 'Enter') {
      const el = at >= 0 ? rowEl(all[at]) : null;
      if (el) open(all[at], el);
      return;
    }
    const to = at < 0 ? 0 : Math.max(0, Math.min(all.length - 1, at + (e.key === 'ArrowDown' ? 1 : -1)));
    go(all[to], e.shiftKey);
    rowEl(all[to])?.scrollIntoView({ block: 'nearest' });
  };

  const listProps = enabled ? { ref: listRef, tabIndex: 0, onKeyDown, 'data-help': help } : { ref: listRef };

  return { rowProps, listProps, rowEl };
}

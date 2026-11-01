/**
 * TreeList — DbColumns with parent/child rows: a chevron folds a row's children, the tree column
 * indents by level (Bill, 2026-11-01: "cascade or tree list might inherit but not be part of
 * DbColumn"). A BOM's components, an action's sub-tasks, a project's tasks.
 *
 * The rows come depth-first — each parent followed by its children — with their level, as the
 * server sends them (bom_ops.expand_tree). What a parent sums to is the server's too.
 */
import { useMemo, useState } from "react";
import { DbColumns, type DbColumnsProps } from "./DbColumns";

export interface TreeListProps<T> extends Omit<DbColumnsProps<T>, 'cellPrefix'> {
  /** The column that carries the indent and the chevron */
  treeColumn: string;
  /** A row's depth (1 = a top row's children start at 1) */
  level: (record: T) => number;
  /** The row has children to fold */
  hasChildren: (record: T) => boolean;
  /** px per level */
  indent?: number;
}

export function TreeList<T extends object>({ treeColumn, level, hasChildren, indent = 16, data, rowKey, ...rest }: TreeListProps<T>) {
  const [folded, setFolded] = useState<Set<string | number>>(new Set());

  // A folded row hides the rows under it: every following row deeper than it.
  const shown = useMemo(() => {
    const out: T[] = [];
    let hideBelow: number | null = null;
    for (const r of data) {
      const lv = level(r);
      if (hideBelow != null && lv > hideBelow) continue;
      hideBelow = null;
      out.push(r);
      if (folded.has(rowKey(r)) && hasChildren(r)) hideBelow = lv;
    }
    return out;
  }, [data, level, hasChildren, folded, rowKey]);

  const toggle = (k: string | number) => setFolded((p) => {
    const n = new Set(p);
    if (n.has(k)) n.delete(k); else n.add(k);
    return n;
  });

  return (
    <DbColumns<T>
      {...rest}
      data={shown}
      rowKey={rowKey}
      cellPrefix={(r, col) => {
        if (col.key !== treeColumn) return null;
        const k = rowKey(r);
        return (
          <span className="dg-tree-cell" style={{ paddingLeft: Math.max(0, level(r) - 1) * indent }}>
            {hasChildren(r)
              ? <span className="dg-tree-chevron" onClick={(e) => { e.stopPropagation(); toggle(k); }}>
                  {folded.has(k) ? '▶' : '▼'}</span>
              : <span className="dg-tree-leaf">·</span>}
          </span>
        );
      }}
    />
  );
}

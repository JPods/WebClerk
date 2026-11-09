/**
 * lineItemService — which lines of a document are live, removed, or saved.
 *
 * Nothing here computes money. A line's totals while editing come from totalsCompute.ts, the
 * browser's mirror of the server's compute_totals (readme 107); the LineItemService class
 * that once mirrored an earlier rule here had no caller and was deleted on 2026-11-08.
 *
 * A removed line stays in the array marked `_removed` until the save, so a saved line can
 * ride in the payload with `_delete: true` (useRecordForm.save).
 */
import type { TransactionLine } from '../types/transactionTypes';

/** The lines still part of the document on screen. */
export function getActiveLines(lines: TransactionLine[]): TransactionLine[] {
  return lines.filter(line => !line._removed);
}

/**
 * The lines the user removed since the last save.
 * Those with a database id ride along in the payload marked `_delete: true`
 * for the backend to delete; the rest (new, never saved) simply disappear.
 */
export function getRemovedLines(lines: TransactionLine[]): TransactionLine[] {
  return lines.filter(line => line._removed === true);
}

/** A line the database holds: it has an id and was not born on this screen. */
export function isPersistedLine(line: TransactionLine): boolean {
  return line.id != null && line.id > 0 && !line._new;
}

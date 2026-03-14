/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Line identity helpers for transaction line management.
 *
 * line_number is the stable, user-visible sequence number for a line.
 * It is auto-assigned by the backend (from parent.line_increment) on first
 * save, but the frontend must assign a temporary value for unsaved lines
 * so that delete / update / duplicate handlers can uniquely identify a line
 * before the first round-trip.
 */

import type { TransactionLine } from "../types/transactionTypes";

/** Default gap between line numbers (matches backend default). */
const LINE_INCREMENT = 10;

/**
 * Return the stable identity key for a line.
 *
 * Priority: line_number  →  id  →  array index.
 * All three are numbers so the handler comparisons stay type-safe.
 */
export function lineKey(line: TransactionLine, idx: number): number {
  return line.line_number ?? line.id ?? idx;
}

/**
 * Compute the next line_number to assign to a newly created line.
 *
 * Takes the max existing line_number across all lines and adds 10.
 * If no lines exist yet, returns 10 (first line).
 */
export function getNextLineNumber(lines: TransactionLine[]): number {
  const max = Math.max(0, ...lines.map((l) => l.line_number ?? 0));
  return max + LINE_INCREMENT;
}

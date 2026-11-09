/**
 * closedDrafts — the edits a window held when it was closed, kept for one Undo.
 *
 * Bill, 2026-11-08 (readme 107): closing a window with unsaved edits is not refused (guide,
 * not barriers); the edits are set aside and a toast offers Undo. Undo reopens the record and
 * useRecordForm takes the draft back from here on its first load. Nothing persists past the
 * page: a reload prompts (beforeunload) instead.
 */
const drafts = new Map<string, Record<string, any>>();

const key = (model: string, id: number) => `${model}/${id}`;

export function stashClosedDraft(model: string, id: number, draft: Record<string, any>): void {
  drafts.set(key(model, id), structuredClone(draft));
}

/** The stashed draft for this record, removed as it is taken; null when there is none. */
export function takeClosedDraft(model: string, id: number): Record<string, any> | null {
  const k = key(model, id);
  const d = drafts.get(k) ?? null;
  drafts.delete(k);
  return d;
}

export function dropClosedDraft(model: string, id: number): void {
  drafts.delete(key(model, id));
}

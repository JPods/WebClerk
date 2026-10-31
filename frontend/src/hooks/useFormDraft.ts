/**
 * useFormDraft — a form's unsaved edits, handed to the list that holds it (Bill, 2026-10-31).
 *
 * In a list, a click or arrow key moves the open form to another row and its unsaved edits
 * are dropped. The list asks the form for them first (onRegisterDraft) and offers Undo; Undo
 * reopens the record with the edits (`draft`), put back once the record has loaded.
 *
 * LastChecked: 2026-10-31 | WhereUsed: ModelDetailPage, TransactionDetail | WhoCreated: Bill+Claude
 */
import { useEffect, useRef } from 'react';

/** The edits a form would lose, or null when it holds none. */
export type DraftGetter = () => Record<string, any> | null;

interface Options {
  recordId?: number | null;
  data: any;
  editData: any;
  setEditData: (d: any) => void;
  setIsEditing: (on: boolean) => void;
  /** Edits to put back once this record has loaded (from the list's Undo). */
  draft?: Record<string, any> | null;
  onRegisterDraft?: (get: DraftGetter) => void;
}

export function useFormDraft({ recordId, data, editData, setEditData, setIsEditing, draft, onRegisterDraft }: Options) {
  // The edit copy as the record loaded — a form may fill it on load (a transaction takes its
  // customer's price level), and that is not an edit.
  const loaded = useRef<string | null>(null);
  useEffect(() => { loaded.current = null; }, [data]);
  useEffect(() => {
    if (data && editData && loaded.current === null) loaded.current = JSON.stringify(editData);
  }, [data, editData]);

  const current = useRef(editData);
  current.current = editData;

  useEffect(() => {
    onRegisterDraft?.(() => {
      const e = current.current;
      if (!e || loaded.current === null || JSON.stringify(e) === loaded.current) return null;
      return structuredClone(e);
    });
  }, [onRegisterDraft]);

  // Put the edits back on the record they came from, after its own read has landed.
  const applied = useRef<Record<string, any> | null>(null);
  useEffect(() => {
    if (!draft || applied.current === draft || !data || data.id !== recordId || draft.id !== recordId) return;
    applied.current = draft;
    setEditData(structuredClone(draft));
    setIsEditing(true);
  }, [draft, data, recordId, setEditData, setIsEditing]);
}

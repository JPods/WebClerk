/**
 * useEditHold — one person edits a record at a time (Bill, 2026-11-02). Opening a record takes its
 * hold (POST /wcapi/<model>/<id>/hold/); working in it extends the hold (at most once a minute);
 * leaving it gives it back. If someone else holds it, `heldBy` says who and until when — the form
 * shows the notice and stays read-only — and the hook asks again every 30 seconds, so the record
 * opens when they leave it or their hold runs out. The server refuses their save anyway (423);
 * this is the notice. Service: backend/apps/core/services/edit_hold.py.
 *
 * LastChecked: 2026-11-02 | WhereUsed: DbForm | WhoCreated: Bill+Claude
 */
import { useCallback, useEffect, useRef, useState } from "react";
import apiClient from "@/api/axios";

export interface HeldBy { name: string; until: string }

interface HoldAnswer { mine: boolean; held_by: string; until: string; minutes: number }

const ASK_AGAIN_MS = 30_000;
const EXTEND_EVERY_MS = 60_000;

export function useEditHold(modelName: string | undefined, recordId: number | string | undefined | null) {
  const [heldBy, setHeldBy] = useState<HeldBy | null>(null);
  const lastTaken = useRef(0);
  const target = modelName && recordId ? `/wcapi/${modelName}/${recordId}` : null;

  const take = useCallback(async () => {
    if (!target) return;
    try {
      const res = await apiClient.post(`${target}/hold/`, {});
      const hold: HoldAnswer | undefined = res.data?.data?.result;
      if (!hold) return;
      lastTaken.current = hold.mine ? Date.now() : 0;
      setHeldBy(hold.mine ? null : { name: hold.held_by, until: hold.until });
    } catch {
      // No hold service, or no right to edit: the form's own rules and the server's save decide.
      setHeldBy(null);
    }
  }, [target]);

  useEffect(() => {
    if (!target) return;
    take();
    return () => {
      apiClient.post(`${target}/release/`, {}).catch(() => undefined);
    };
  }, [target, take]);

  // Someone else has it: ask again until it opens.
  useEffect(() => {
    if (!heldBy) return;
    const timer = setInterval(take, ASK_AGAIN_MS);
    return () => clearInterval(timer);
  }, [heldBy, take]);

  /** The person is working in the record: keep the hold (once a minute at most). */
  const touch = useCallback(() => {
    if (!heldBy && lastTaken.current && Date.now() - lastTaken.current > EXTEND_EVERY_MS) take();
  }, [heldBy, take]);

  return { heldBy, touch };
}

/** "Bill James is editing until 3:42 PM" — the notice, in the viewer's local time. */
export function heldNotice(h: HeldBy): string {
  const until = new Date(h.until).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  return `${h.name} is editing until ${until} — read-only until they leave it`;
}

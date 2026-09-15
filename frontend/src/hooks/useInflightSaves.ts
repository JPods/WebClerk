/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * useInflightSaves — tracks background save promises so we can delay
 * window close until all writes have landed.
 *
 * Usage:
 *   const { track, inflightCount, waitForAll } = useInflightSaves();
 *
 *   // Wrap any background save:
 *   track(saveRecord("email", payload));
 *
 *   // Before closing:
 *   await waitForAll();   // resolves when inflightCount === 0
 */

import { useCallback, useRef, useState } from "react";

export function useInflightSaves() {
  const inflightRef = useRef<Set<Promise<unknown>>>(new Set());
  const [inflightCount, setInflightCount] = useState(0);

  /** Register a promise (fire-and-forget from caller's perspective). */
  const track = useCallback(<T,>(promise: Promise<T>): Promise<T> => {
    inflightRef.current.add(promise);
    setInflightCount(inflightRef.current.size);

    const cleanup = () => {
      inflightRef.current.delete(promise);
      setInflightCount(inflightRef.current.size);
    };

    promise.then(cleanup, cleanup);
    return promise;
  }, []);

  /** Wait until every tracked promise has settled. */
  const waitForAll = useCallback(async (): Promise<void> => {
    while (inflightRef.current.size > 0) {
      await Promise.allSettled([...inflightRef.current]);
    }
  }, []);

  return { track, inflightCount, waitForAll } as const;
}

/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import React, { createContext, useContext, useMemo, useSyncExternalStore } from "react";
import {
  RequestTask,
  RequestSnapshot,
  subscribeToRequests,
  getRequestSnapshot,
  cancelTrackedRequest,
} from "../api/requestTracker";

interface RequestQueueContextValue extends RequestSnapshot {
  cancel: (id: string) => void;
}

const RequestQueueContext = createContext<RequestQueueContextValue | undefined>(undefined);

export const RequestQueueProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const snapshot = useSyncExternalStore(subscribeToRequests, getRequestSnapshot, getRequestSnapshot);

  const value = useMemo<RequestQueueContextValue>(() => {
    return {
      active: snapshot.active,
      cancel: (id: string) => cancelTrackedRequest(id),
    };
  }, [snapshot]);

  return <RequestQueueContext.Provider value={value}>{children}</RequestQueueContext.Provider>;
};

export const useRequestQueue = (): RequestQueueContextValue => {
  const ctx = useContext(RequestQueueContext);
  if (!ctx) throw new Error("useRequestQueue must be used within a RequestQueueProvider");
  return ctx;
};

/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import React, { createContext, useContext, useMemo, useSyncExternalStore } from "react";
import {
  enqueueSaveRequest,
  getSaveQueueSnapshot,
  cancelSaveRequest,
  SaveQueueItem,
  subscribeToSaveQueue,
} from "../api/saveQueue";

interface SaveQueueContextValue {
  active: SaveQueueItem | null;
  queued: SaveQueueItem[];
  pendingCount: number;
  enqueue: (payload: any, label?: string) => { id: string; promise: Promise<any>; cancel: () => void };
  cancel: (id: string) => void;
}

const SaveQueueContext = createContext<SaveQueueContextValue | undefined>(undefined);

export const SaveQueueProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const snapshot = useSyncExternalStore(subscribeToSaveQueue, getSaveQueueSnapshot, getSaveQueueSnapshot);

  const value = useMemo<SaveQueueContextValue>(() => {
    return {
      active: snapshot.active,
      queued: snapshot.queued,
      pendingCount: snapshot.queued.length + (snapshot.active ? 1 : 0),
      enqueue: (payload: any, label?: string) => enqueueSaveRequest(payload, label),
      cancel: (id: string) => cancelSaveRequest(id),
    };
  }, [snapshot]);

  return <SaveQueueContext.Provider value={value}>{children}</SaveQueueContext.Provider>;
};

export const useSaveQueue = () => {
  const context = useContext(SaveQueueContext);
  if (!context) {
    throw new Error("useSaveQueue must be used within a SaveQueueProvider");
  }
  return context;
};

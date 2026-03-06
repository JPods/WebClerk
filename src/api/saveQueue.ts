import { PostLoginURL } from "../routes/network";
import apiClient from "./axios";

export type SaveQueueStatus = "queued" | "running" | "success" | "error" | "canceled";

export interface SaveQueueItem {
  id: string;
  label: string;
  status: SaveQueueStatus;
  createdAt: number;
  payload: any;
  error?: string;
}

interface InternalSaveQueueItem extends SaveQueueItem {
  controller: AbortController;
  resolve: (value: any) => void;
  reject: (reason?: any) => void;
}

export interface SaveQueueSnapshot {
  active: SaveQueueItem | null;
  queued: SaveQueueItem[];
}

type Listener = (snapshot: SaveQueueSnapshot) => void;

const listeners = new Set<Listener>();
let queue: InternalSaveQueueItem[] = [];
let active: InternalSaveQueueItem | null = null;
const cancelMap = new Map<string, () => void>();
let currentSnapshot: SaveQueueSnapshot = { active: null, queued: [] };

const createId = () =>
  typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `sq-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

const inferLabel = (payload: any): string => {
  if (!payload || typeof payload !== "object") {
    return "Save";
  }
  const modelName = (payload.model_name as string | undefined)?.toString();
  const actionTitle =
    (payload.action && payload.action.value && payload.action.value.en) ||
    payload.action_en ||
    payload.title ||
    payload.name;
  if (actionTitle) {
    return `${modelName || "Save"}: ${actionTitle}`;
  }
  if (modelName) return `${modelName} save`;
  return "Save";
};

let notifyScheduled = false;
const notify = () => {
  if (notifyScheduled) return;
  notifyScheduled = true;
  queueMicrotask(() => {
    notifyScheduled = false;
    const toPublic = (item: InternalSaveQueueItem): SaveQueueItem => ({
      id: item.id,
      label: item.label,
      status: item.status,
      createdAt: item.createdAt,
      payload: item.payload,
      error: item.error,
    });
    currentSnapshot = {
      active: active ? toPublic(active) : null,
      queued: queue.map(toPublic),
    };
    listeners.forEach((listener) => listener(currentSnapshot));
  });
};

const startNext = () => {
  if (active || queue.length === 0) {
    return;
  }
  const next = queue.shift();
  if (!next) return;
  next.status = "running";
  active = { ...next } as InternalSaveQueueItem;
  notify();

  // Log payload for debugging save failures
  try {
    const rawPreview = JSON.stringify(next.payload);
    const preview = rawPreview.length > 1500 ? `${rawPreview.slice(0, 1500)}…` : rawPreview;
    console.debug("[saveQueue] Posting payload", { id: next.id, label: next.label, preview });
  } catch (e) {
    console.debug("[saveQueue] Posting payload", { id: next.id, label: next.label });
  }

  apiClient
    .post(PostLoginURL.allSave, { ...next.payload }, { signal: next.controller.signal })
    .then((response) => {
      if (!active) return;
      active.status = "success";
      notify();
      next.resolve(response);
    })
    .catch((error) => {
      if (!active) return;
      const wasAborted = next.controller.signal.aborted;
      active.status = wasAborted ? "canceled" : "error";
      active.error = wasAborted ? "Canceled" : error?.message ?? "Save failed";
      notify();
      next.reject(error);
    })
    .finally(() => {
      cancelMap.delete(next.id);
      active = null;
      notify();
      startNext();
    });
};

export const enqueueSaveRequest = (payload: any, label?: string) => {
  const id = createId();
  const controller = new AbortController();
  let resolve: (value: any) => void;
  let reject: (reason?: any) => void;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });

  const item: InternalSaveQueueItem = {
    id,
    label: label || inferLabel(payload),
    status: "queued",
    createdAt: Date.now(),
    payload,
    controller,
    resolve: resolve!,
    reject: reject!,
  };

  queue.push(item);
  notify();
  startNext();

  const cancel = () => {
    if (item.status === "queued") {
      queue = queue.filter((entry) => entry.id !== item.id);
      item.status = "canceled";
      item.reject(new Error("Canceled"));
      notify();
      cancelMap.delete(item.id);
      return;
    }
    if (active && active.id === item.id && active.status === "running") {
      controller.abort();
    }
  };

  cancelMap.set(id, cancel);

  return { id, promise, cancel };
};

export const cancelSaveRequest = (id: string) => {
  const cancel = cancelMap.get(id);
  if (cancel) {
    cancel();
  }
};

export const subscribeToSaveQueue = (listener: Listener) => {
  listeners.add(listener);
  // Deliver the current snapshot on the next tick to avoid render-phase updates
  queueMicrotask(() => listener(currentSnapshot));
  return () => listeners.delete(listener);
};

export const getSaveQueueSnapshot = (): SaveQueueSnapshot => currentSnapshot;

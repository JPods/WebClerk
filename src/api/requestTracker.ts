/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { AxiosRequestConfig } from "axios";

export type RequestStatus = "running" | "success" | "error" | "canceled";

export interface RequestTask {
  id: string;
  label: string;
  method: string;
  url: string;
  status: RequestStatus;
  startedAt: number;
  error?: string;
}

interface InternalRequestTask extends RequestTask {
  controller: AbortController;
}

type Listener = (snapshot: RequestSnapshot) => void;

export interface RequestSnapshot {
  active: RequestTask[];
}

const listeners = new Set<Listener>();
let activeRequests: InternalRequestTask[] = [];
let currentSnapshot: RequestSnapshot = { active: [] };

const createId = () =>
  typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `req-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

const normalizeLabel = (config: AxiosRequestConfig): string => {
  const fromConfig = (config as any).taskLabel as string | undefined;
  if (fromConfig) return fromConfig;
  const method = (config.method || "GET").toUpperCase();
  const url = config.url || "";
  // Trim query for a cleaner label
  const path = url.split("?")[0];
  return `${method} ${path || "/"}`;
};

const toPublic = (item: InternalRequestTask): RequestTask => ({
  id: item.id,
  label: item.label,
  method: item.method,
  url: item.url,
  status: item.status,
  startedAt: item.startedAt,
  error: item.error,
});

let notifyScheduled = false;
const notify = () => {
  if (notifyScheduled) return;
  notifyScheduled = true;
  queueMicrotask(() => {
    notifyScheduled = false;
    currentSnapshot = { active: activeRequests.map(toPublic) };
    listeners.forEach((listener) => listener(currentSnapshot));
  });
};

const buildSignal = (config: AxiosRequestConfig, controller: AbortController): AbortSignal => {
  const existing = config.signal;
  if (!existing) return controller.signal;
  if (existing.aborted) {
    controller.abort();
    return controller.signal;
  }
  // Mirror existing aborts into our controller
  if (typeof existing.addEventListener === "function") {
    existing.addEventListener("abort", () => controller.abort(), { once: true });
  }
  return controller.signal;
};

export const startRequestTracking = (config: AxiosRequestConfig) => {
  const controller = new AbortController();
  const task: InternalRequestTask = {
    id: createId(),
    label: normalizeLabel(config),
    method: (config.method || "GET").toUpperCase(),
    url: config.url || "",
    status: "running",
    startedAt: Date.now(),
    controller,
  };

  activeRequests = [...activeRequests, task];
  notify();

  const cancel = () => {
    if (task.status === "running") {
      controller.abort();
    }
  };

  return {
    id: task.id,
    cancel,
    signal: buildSignal(config, controller),
  };
};

export const completeRequestTracking = (id: string, status: RequestStatus, error?: string) => {
  let changed = false;
  activeRequests = activeRequests.reduce<InternalRequestTask[]>((acc, item) => {
    if (item.id !== id) return acc.concat(item);
    changed = true;
    // Drop completed tasks from the list; we only surface active ones
    return acc;
  }, []);
  if (changed) notify();
};

export const cancelTrackedRequest = (id: string) => {
  const target = activeRequests.find((item) => item.id === id);
  if (target && target.status === "running") {
    target.controller.abort();
  }
};

export const subscribeToRequests = (listener: Listener) => {
  listeners.add(listener);
  // Deliver the current state on the next tick to keep render-phase clean
  queueMicrotask(() => listener(currentSnapshot));
  return () => listeners.delete(listener);
};

export const getRequestSnapshot = (): RequestSnapshot => currentSnapshot;

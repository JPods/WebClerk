import axios, { AxiosError, AxiosInstance, AxiosResponse } from "axios";
import { AuthURL, NetworkInfo } from "../routes/network";
import { store } from "../store";
import { clearUser } from "../store/slices/authSlice";
import { onRequestStart, onResponseSuccess, onResponseError } from "./apiLogger";
import {
  startRequestTracking,
  completeRequestTracking,
  cancelTrackedRequest,
} from "./requestTracker";

// Access tokens are short-lived; keep latest in memory for fast access
// Helpers
const isValidToken = (val: any): val is string =>
  typeof val === 'string' && val.trim() !== '' && val !== 'undefined' && val !== 'null';

// Access tokens are short-lived; keep latest in memory for fast access
let accessToken: string | null = (() => {
  const raw = typeof localStorage !== "undefined" ? localStorage.getItem("accessToken") : null;
  if (!isValidToken(raw)) {
    // Clean up any bad leftovers to avoid gating UI with a bogus token
    if (typeof localStorage !== "undefined") localStorage.removeItem("accessToken");
    return null;
  }
  return raw;
})();
let isRefreshing = false;
let refreshQueue: Array<(token: string | null) => void> = [];

// Simple session-scoped cache for GET requests to reduce reloads while tab is open
type CachedEntry = {
  status: number;
  statusText: string;
  headers: any;
  data: any;
  timestamp: number;
};

const CACHE_PREFIX = "wc_cache_v1:";

// Drop cached GET responses; used when identity changes so old-user data is not reused
export const clearResponseCache = () => {
  if (typeof sessionStorage === "undefined") return;
  try {
    const keys = Object.keys(sessionStorage);
    for (const key of keys) {
      if (key.startsWith(CACHE_PREFIX)) sessionStorage.removeItem(key);
    }
  } catch {
    // ignore storage access errors
  }
};

const getCacheKey = (baseURL: string | undefined, url: string, params?: any): string => {
  const search = params ? JSON.stringify(params) : "";
  return `${CACHE_PREFIX}${baseURL ?? ""}${url}?${search}`;
};

const readCache = (key: string): AxiosResponse | null => {
  if (typeof sessionStorage === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as CachedEntry;
    return {
      status: parsed.status,
      statusText: parsed.statusText,
      headers: parsed.headers,
      data: parsed.data,
      config: {},
    } as AxiosResponse;
  } catch {
    return null;
  }
};

const writeCache = (key: string, res: AxiosResponse) => {
  if (typeof sessionStorage === "undefined") return;
  try {
    const entry: CachedEntry = {
      status: res.status,
      statusText: res.statusText,
      headers: res.headers,
      data: res.data,
      timestamp: Date.now(),
    };
    sessionStorage.setItem(key, JSON.stringify(entry));
  } catch {
    // ignore quota or serialization errors
  }
};

// CACHING STRATEGY:
// - WCAPI calls = Database actions = NEVER CACHED (inventories, orders change constantly)
// - Static data to cache → Store in JavaScript VARIABLES (React state/context/store)
// - Only non-wcapi static endpoints may be cached here
//
// If you need to cache database values that rarely change (e.g., model schemas),
// fetch them once and store in React state/context/Redux - NOT in session cache.

const NEVER_CACHE_PATTERNS = [
  '/wcapi/',      // ALL wcapi calls are database actions - never cache
  '/api/wcapi/',  // Alternate mount point - also never cache
];

const shouldNeverCache = (url: string): boolean => {
  return NEVER_CACHE_PATTERNS.some(pattern => url.includes(pattern));
};

const wrapGetWithCache = (client: AxiosInstance) => {
  const originalGet = client.get.bind(client);
  client.get = (async function patchedGet(url: any, config: any = {}) {
    // WCAPI = Database = NEVER CACHE
    // These endpoints serve live database records that can change any moment
    if (shouldNeverCache(url)) {
      return originalGet(url, config);
    }
    
    // For non-wcapi endpoints: respect explicit cache settings
    const explicitNoCache = config?.cache === false || config?.headers?.["x-skip-cache"] === true;
    const shouldCache = !explicitNoCache;
    const cacheKey = shouldCache ? getCacheKey(client.defaults.baseURL, url, config?.params) : null;

    if (cacheKey) {
      const cached = readCache(cacheKey);
      if (cached) return cached;
    }

    const res = await originalGet(url, config);
    if (cacheKey) writeCache(cacheKey, res);
    return res;
  }) as typeof client.get;
};

const updateLoading = (_delta: number) => {
  // Spinner intentionally disabled
  return;
};

// Helper to process queued requests waiting for refresh
const processQueue = (token: string | null) => {
  refreshQueue.forEach((cb) => cb(token));
  refreshQueue = [];
};

export const persistTokens = (access: string, refresh?: string | null) => {
  accessToken = access;
  if (typeof localStorage !== "undefined") {
    localStorage.setItem("accessToken", access);
    if (refresh) localStorage.setItem("refreshToken", refresh);
  }
};

export const clearTokens = () => {
  accessToken = null;
  if (typeof localStorage !== "undefined") {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
  }
  clearResponseCache();
};

// Instance for protected API calls
// Use relative URL in development so Vite proxy intercepts it
// In production, use absolute URL from NetworkInfo
export const apiClient = axios.create({
  baseURL: typeof window !== 'undefined' && window.location.protocol === 'http:' ? '' : NetworkInfo.API_URL,
});

// Separate client for Notion integration endpoints
export const notionClient = axios.create({
  baseURL: NetworkInfo.NOTION_URL,
});

// Separate instance for auth endpoints (login, signup, refresh)
export const authClient = axios.create({
  baseURL: typeof window !== 'undefined' && window.location.protocol === 'http:' ? '' : NetworkInfo.AUTH_URL,
});

const attachAuthInterceptors = (client: AxiosInstance) => {
  client.interceptors.request.use((config) => {
    updateLoading(1);
    // Add correlation ID and start time for logging
    onRequestStart(config);
    const tracking = startRequestTracking(config);
    (config as any)._requestTrackId = tracking.id;
    (config as any)._requestCancel = tracking.cancel;
    config.signal = tracking.signal;
    if (!accessToken && typeof localStorage !== "undefined") {
      accessToken = localStorage.getItem("accessToken");
    }
    if (isValidToken(accessToken)) {
      config.headers = config.headers ?? {};
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  });

  client.interceptors.response.use(
    (res) => {
      updateLoading(-1);
      // Log successful response
      onResponseSuccess(res);
      const trackId = (res.config as any)?._requestTrackId;
      if (trackId) completeRequestTracking(trackId, "success");
      return res;
    },
    async (error: AxiosError) => {
      const originalRequest: any = error.config;
      const trackId = (originalRequest as any)?._requestTrackId;

      if (error.response?.status === 401 && !originalRequest?._retry) {
        if (isRefreshing) {
          return new Promise((resolve, reject) => {
            refreshQueue.push((token) => {
              if (!token) {
                reject(error);
                return;
              }
              originalRequest.headers = originalRequest.headers ?? {};
              originalRequest.headers.Authorization = `Bearer ${token}`;
              resolve(client(originalRequest));
            });
          }).finally(() => updateLoading(-1));
        }

        originalRequest._retry = true;
        isRefreshing = true;
        try {
          const refreshToken = typeof localStorage !== "undefined" ? localStorage.getItem("refreshToken") : null;
          if (!refreshToken) throw new Error("No refresh token");

          const refreshResponse = await authClient.post(AuthURL.REFRESH_TOKEN, { refresh: refreshToken });
          // Backend wraps JSON responses in an envelope: { status, code, message, data: { access } }
          const body: any = (refreshResponse as any).data ?? {};
          const fromEnvelope = body?.data?.access;
          const fromTopLevel = body?.access; // fallback for non-enveloped
          const newToken: string | null = isValidToken(fromEnvelope)
            ? fromEnvelope
            : isValidToken(fromTopLevel)
            ? fromTopLevel
            : null;
          if (!newToken) throw new Error("Invalid refresh response: missing access token");

          accessToken = newToken;
          if (typeof localStorage !== "undefined") localStorage.setItem("accessToken", newToken);
          processQueue(newToken);
          originalRequest.headers = originalRequest.headers ?? {};
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          if (trackId) completeRequestTracking(trackId, "canceled", "retrying with refreshed token");
          return client(originalRequest);
        } catch (refreshErr) {
          processQueue(null);
          clearTokens();
          // Update global auth state so UI reacts immediately
          try {
            store.dispatch(clearUser());
          } catch {}
          // Log the error before rejecting
          onResponseError(error);
          if (trackId) completeRequestTracking(trackId, "error", (refreshErr as any)?.message);
          return Promise.reject(refreshErr);
        } finally {
          isRefreshing = false;
          updateLoading(-1);
        }
      }

      updateLoading(-1);
      // Log the error
      onResponseError(error);
      if (trackId) {
        const wasCanceled = (error as any)?.code === "ERR_CANCELED" || (error as any)?.message === "canceled";
        completeRequestTracking(trackId, wasCanceled ? "canceled" : "error", (error as any)?.message);
      }
      return Promise.reject(error);
    }
  );
};

const attachLoadingOnly = (client: AxiosInstance) => {
  client.interceptors.request.use((config) => {
    updateLoading(1);
    const tracking = startRequestTracking(config);
    (config as any)._requestTrackId = tracking.id;
    (config as any)._requestCancel = tracking.cancel;
    config.signal = tracking.signal;
    return config;
  });

  client.interceptors.response.use(
    (res) => {
      updateLoading(-1);
      const trackId = (res.config as any)?._requestTrackId;
      if (trackId) completeRequestTracking(trackId, "success");
      return res;
    },
    (error) => {
      updateLoading(-1);
      const trackId = (error.config as any)?._requestTrackId;
      if (trackId) {
        const wasCanceled = (error as any)?.code === "ERR_CANCELED" || (error as any)?.message === "canceled";
        completeRequestTracking(trackId, wasCanceled ? "canceled" : "error", (error as any)?.message);
      }
      return Promise.reject(error);
    }
  );
};

attachAuthInterceptors(apiClient);
attachAuthInterceptors(notionClient);
attachLoadingOnly(authClient);
wrapGetWithCache(apiClient);
wrapGetWithCache(notionClient);

export default apiClient;

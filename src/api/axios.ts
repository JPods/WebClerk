import axios, { AxiosError, AxiosInstance, AxiosResponse } from "axios";
import { AuthURL, NetworkInfo } from "../routes/network";
import { store } from "../store";
import { clearUser } from "../store/slices/authSlice";
import { convertRestToWcapi, isWcapiPath } from "./restToWcapi";
import {
  onRequestStart,
  onResponseSuccess,
  onResponseError,
} from "./apiLogger";
import {
  startRequestTracking,
  completeRequestTracking,
  cancelTrackedRequest,
} from "./requestTracker";

// Access tokens are short-lived; keep latest in memory for fast access
// Helpers
const isValidToken = (val: any): val is string =>
  typeof val === "string" &&
  val.trim() !== "" &&
  val !== "undefined" &&
  val !== "null";

// Access token lives in memory only — no localStorage exposure to XSS.
// On page reload, bootstrapAuth() acquires a fresh token from the httpOnly
// refresh-token cookie via /wcapi/token_refresh/.
let accessToken: string | null = null;
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

const CACHE_PREFIX = "wc_cache_v2:";

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

const getCacheKey = (
  baseURL: string | undefined,
  url: string,
  params?: any,
): string => {
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
  "/wcapi/", // ALL wcapi calls are database actions - never cache
  "/api/wcapi/", // Alternate mount point - also never cache
];

const shouldNeverCache = (url: string): boolean => {
  return NEVER_CACHE_PATTERNS.some((pattern) => url.includes(pattern));
};

const getHeaderValue = (headers: any, key: string): string | undefined => {
  if (!headers) return undefined;
  const direct = headers?.[key];
  if (typeof direct === "string") return direct;

  const lowerKey = key.toLowerCase();
  const lower = headers?.[lowerKey];
  if (typeof lower === "string") return lower;

  if (typeof headers?.get === "function") {
    const viaGet = headers.get(key) ?? headers.get(lowerKey);
    if (typeof viaGet === "string") return viaGet;
  }

  return undefined;
};

const wrapGetWithCache = (client: AxiosInstance) => {
  const originalGet = client.get.bind(client);
  client.get = async function patchedGet(url: any, config: any = {}) {
    const wcapiCacheExempt =
      getHeaderValue(config?.headers, "x-wcapi-cache-exempt") ===
      "default-company";

    // WCAPI = Database = NEVER CACHE
    // These endpoints serve live database records that can change any moment
    // Exception: allow explicit opt-in for primary organization/default company
    // reads to stabilize print branding in-session.
    if (shouldNeverCache(url) && !wcapiCacheExempt) {
      return originalGet(url, config);
    }

    // For non-wcapi endpoints: respect explicit cache settings
    const explicitNoCache =
      config?.cache === false || config?.headers?.["x-skip-cache"] === true;
    const shouldCache = !explicitNoCache;
    const cacheKey = shouldCache
      ? getCacheKey(client.defaults.baseURL, url, config?.params)
      : null;

    if (cacheKey) {
      const cached = readCache(cacheKey);
      if (cached) return cached;
    }

    const res = await originalGet(url, config);
    if (cacheKey) writeCache(cacheKey, res);
    return res;
  } as typeof client.get;
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

export const persistTokens = (access: string, _refresh?: string | null) => {
  // Access token is memory-only; refresh token is an httpOnly cookie set by the server.
  accessToken = access;
};

export const clearTokens = () => {
  accessToken = null;
  if (typeof localStorage !== "undefined") {
    // Clean up any legacy localStorage tokens from before the cookie migration
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
  }
  clearResponseCache();
};

// Instance for protected API calls
// Use relative URL in development so Vite proxy intercepts it
// In production, use absolute URL from NetworkInfo
export const apiClient = axios.create({
  baseURL:
    typeof window !== "undefined" && window.location.protocol === "http:"
      ? ""
      : NetworkInfo.API_URL,
});

// Separate client for Notion integration endpoints
export const notionClient = axios.create({
  baseURL: NetworkInfo.NOTION_URL,
});

// Auth client sends httpOnly refresh cookie via withCredentials
export const authClient = axios.create({
  baseURL:
    typeof window !== "undefined" && window.location.protocol === "http:"
      ? ""
      : NetworkInfo.AUTH_URL,
  withCredentials: true,
});

// ─── REST → WCAPI Interceptor ─────────────────────────────────────────────
// Transparently rewrites legacy /api/… REST calls to /wcapi/… before they
// leave the browser.  This eliminates the extra 301 round-trip that the
// server-side rest_redirect middleware would otherwise add.
//
// Paths already targeting /wcapi/ or non-REST endpoints (auth, kanban,
// integrations, static) pass through untouched.
// ────────────────────────────────────────────────────────────────────────────

/** Paths that should never be rewritten (already wcapi, auth, or special). */
const INTERCEPTOR_SKIP_PATTERNS = [
  '/wcapi/',          // already using wcapi
  '/admin/',          // Django admin
  '/integrations/',   // Notion etc.
  '/kanban/',         // Kanban board
  '/static/',         // static files
  '/media/',          // media files
];

const shouldSkipRewrite = (url: string): boolean => {
  const lower = url.toLowerCase();
  return INTERCEPTOR_SKIP_PATTERNS.some((p) => lower.includes(p));
};

/**
 * Detect whether a URL looks like a RESTful /api/… path that should be
 * rewritten. Matches patterns like:
 *   /api/orgs/customer/42
 *   /communications/phones/
 *   /orgs/vendor/
 * But NOT:
 *   /wcapi/get/   (already wcapi)
 *   /kanban/tasks/ (special endpoint)
 */
const REST_PATTERN = /^\/?(?:api\/)?(?:orgs|transactions|products|communications|accounts|core|docs|support|sync)\//i;

const isRestPath = (url: string): boolean => REST_PATTERN.test(url);

const attachRestToWcapiInterceptor = (client: AxiosInstance) => {
  client.interceptors.request.use((config) => {
    const url = config.url ?? '';

    // Skip if already wcapi or a non-REST path
    if (shouldSkipRewrite(url) || isWcapiPath(url) || !isRestPath(url)) {
      return config;
    }

    try {
      const method = (config.method ?? 'GET').toUpperCase();
      const converted = convertRestToWcapi(url, method, config.data);

      if (import.meta.env.DEV) {
        console.debug(
          `[REST→WCAPI] ${method} ${url}  →  ${converted.method} ${converted.endpoint}`,
          converted.params ?? converted.body ?? '',
        );
      }

      // Rewrite the request
      config.url = converted.endpoint;
      config.method = converted.method.toLowerCase();

      if (converted.params) {
        config.params = { ...config.params, ...converted.params };
      }
      if (converted.body) {
        config.data = converted.body;
      }
    } catch (err) {
      // If conversion fails (unknown model/path), let the original request
      // through — the server-side middleware will handle it or return 404.
      if (import.meta.env.DEV) {
        console.warn(`[REST→WCAPI] Could not convert ${url}:`, err);
      }
    }

    return config;
  });
};

const attachAuthInterceptors = (client: AxiosInstance) => {
  client.interceptors.request.use((config) => {
    updateLoading(1);
    // Add correlation ID and start time for logging
    onRequestStart(config);
    const tracking = startRequestTracking(config);
    (config as any)._requestTrackId = tracking.id;
    (config as any)._requestCancel = tracking.cancel;
    config.signal = tracking.signal;
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
          // Refresh token is sent automatically as httpOnly cookie via withCredentials
          const refreshResponse = await authClient.post(AuthURL.REFRESH_TOKEN, {});
          // Backend wraps JSON responses in an envelope: { status, code, message, data: { access } }
          const body: any = (refreshResponse as any).data ?? {};
          const newToken: string | null = isValidToken(body?.data?.access)
            ? body.data.access
            : isValidToken(body?.access)   // fallback for flat SimpleJWT response
            ? body.access
            : null;
          if (!newToken)
            throw new Error("Invalid refresh response: missing access token");

          accessToken = newToken;
          processQueue(newToken);
          originalRequest.headers = originalRequest.headers ?? {};
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          if (trackId)
            completeRequestTracking(
              trackId,
              "canceled",
              "retrying with refreshed token",
            );
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
          if (trackId)
            completeRequestTracking(
              trackId,
              "error",
              (refreshErr as any)?.message,
            );
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
        const wasCanceled =
          (error as any)?.code === "ERR_CANCELED" ||
          (error as any)?.message === "canceled";
        completeRequestTracking(
          trackId,
          wasCanceled ? "canceled" : "error",
          (error as any)?.message,
        );
      }
      return Promise.reject(error);
    },
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
        const wasCanceled =
          (error as any)?.code === "ERR_CANCELED" ||
          (error as any)?.message === "canceled";
        completeRequestTracking(
          trackId,
          wasCanceled ? "canceled" : "error",
          (error as any)?.message,
        );
      }
      return Promise.reject(error);
    },
  );
};

// REST→WCAPI interceptor runs FIRST (before auth) so the rewritten URL
// gets the correct Authorization header and caching behaviour.
attachRestToWcapiInterceptor(apiClient);

attachAuthInterceptors(apiClient);
attachAuthInterceptors(notionClient);
attachLoadingOnly(authClient);
wrapGetWithCache(apiClient);
wrapGetWithCache(notionClient);

/**
 * Bootstrap authentication on page load.
 *
 * Since access tokens live in memory only (not localStorage), a page reload
 * loses the token.  This function calls /wcapi/token_refresh/ (which sends
 * the httpOnly refresh cookie automatically) to obtain a fresh access token.
 *
 * Returns the access token string on success, or null if the user is not
 * authenticated (no cookie, expired, etc.).
 */
/** Return the current in-memory access token (for diagnostics / dev tools). */
export const getAccessToken = (): string | null => accessToken;

export const bootstrapAuth = async (): Promise<string | null> => {
  try {
    const res = await authClient.post(AuthURL.REFRESH_TOKEN, {});
    const body: any = res?.data ?? {};
    const token: string | null = isValidToken(body?.data?.access)
      ? body.data.access
      : isValidToken(body?.access)
      ? body.access
      : null;
    if (token) {
      accessToken = token;
    }
    return token;
  } catch {
    // No valid refresh cookie — user is not authenticated
    return null;
  }
};

export default apiClient;

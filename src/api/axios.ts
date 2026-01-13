import axios, { AxiosError, AxiosInstance } from "axios";
import { AuthURL, NetworkInfo } from "../routes/network";
import { store } from "../store";
import { clearUser } from "../store/slices/authSlice";
import { setApiLoading } from "../store/slices/loadingSlice";

// Access tokens are short-lived; keep latest in memory for fast access
// Helpers
const isValidToken = (val: any): val is string =>
  typeof val === 'string' && val.trim() !== '' && val !== 'undefined' && val !== 'null';

// Access tokens are short-lived; keep latest in memory for fast access
let accessToken: string | null = (() => {
  const raw = localStorage.getItem("accessToken");
  if (!isValidToken(raw)) {
    // Clean up any bad leftovers to avoid gating UI with a bogus token
    localStorage.removeItem("accessToken");
    return null;
  }
  return raw;
})();
let isRefreshing = false;
let refreshQueue: Array<(token: string | null) => void> = [];
let inflightRequests = 0;

const updateLoading = (delta: number) => {
  inflightRequests = Math.max(0, inflightRequests + delta);
  store.dispatch(setApiLoading(inflightRequests > 0));
};

// Helper to process queued requests waiting for refresh
const processQueue = (token: string | null) => {
  refreshQueue.forEach((cb) => cb(token));
  refreshQueue = [];
};

// Instance for protected API calls
export const apiClient = axios.create({
  baseURL: NetworkInfo.API_URL,
});

// Separate client for Notion integration endpoints
export const notionClient = axios.create({
  baseURL: NetworkInfo.NOTION_URL,
});

// Separate instance for auth endpoints (login, signup, refresh)
export const authClient = axios.create({
  baseURL: NetworkInfo.AUTH_URL,
});

const attachAuthInterceptors = (client: AxiosInstance) => {
  client.interceptors.request.use((config) => {
    updateLoading(1);
    if (!accessToken) {
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
      return res;
    },
    async (error: AxiosError) => {
      const originalRequest: any = error.config;

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
          const refreshToken = localStorage.getItem("refreshToken");
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
          localStorage.setItem("accessToken", newToken);
          processQueue(newToken);
          originalRequest.headers = originalRequest.headers ?? {};
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return client(originalRequest);
        } catch (refreshErr) {
          processQueue(null);
          // Defensive: remove bad tokens so guards don't pass with bogus strings
          localStorage.removeItem("accessToken");
          // Optionally also clear refresh on hard failures
          // localStorage.removeItem("refreshToken");
          // Update global auth state so UI reacts immediately
          try {
            store.dispatch(clearUser());
          } catch {}
          return Promise.reject(refreshErr);
        } finally {
          isRefreshing = false;
          updateLoading(-1);
        }
      }

      updateLoading(-1);
      return Promise.reject(error);
    }
  );
};

const attachLoadingOnly = (client: AxiosInstance) => {
  client.interceptors.request.use((config) => {
    updateLoading(1);
    return config;
  });

  client.interceptors.response.use(
    (res) => {
      updateLoading(-1);
      return res;
    },
    (error) => {
      updateLoading(-1);
      return Promise.reject(error);
    }
  );
};

attachAuthInterceptors(apiClient);
attachAuthInterceptors(notionClient);
attachLoadingOnly(authClient);

export default apiClient;

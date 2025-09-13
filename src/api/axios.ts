import axios, { AxiosError } from "axios";
import { AuthURL, NetworkInfo } from "../routes/network";
import { store } from "../store";
import { clearUser } from "../store/slices/authSlice";

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

// Helper to process queued requests waiting for refresh
const processQueue = (token: string | null) => {
  refreshQueue.forEach((cb) => cb(token));
  refreshQueue = [];
};

// Instance for protected API calls
export const apiClient = axios.create({
  baseURL: NetworkInfo.API_URL,
});

// Separate instance for auth endpoints (login, signup, refresh)
export const authClient = axios.create({
  baseURL: NetworkInfo.AUTH_URL,
});

apiClient.interceptors.request.use((config) => {
  if (!accessToken) {
    accessToken = localStorage.getItem("accessToken");
  }
  if (isValidToken(accessToken)) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const originalRequest: any = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve) => {
          refreshQueue.push((token) => {
            if (token) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            resolve(apiClient(originalRequest));
          });
        });
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
        const newToken: string | null = isValidToken(fromEnvelope) ? fromEnvelope : (isValidToken(fromTopLevel) ? fromTopLevel : null);
        if (!newToken) throw new Error("Invalid refresh response: missing access token");

        accessToken = newToken;
        localStorage.setItem("accessToken", newToken);
        processQueue(newToken);
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      } catch (refreshErr) {
        processQueue(null);
        // Defensive: remove bad tokens so guards don't pass with bogus strings
        localStorage.removeItem("accessToken");
        // Optionally also clear refresh on hard failures
        // localStorage.removeItem("refreshToken");
        // Update global auth state so UI reacts immediately
        try { store.dispatch(clearUser()); } catch {}
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;

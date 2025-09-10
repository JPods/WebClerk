import axios, { AxiosError } from "axios";
import { AuthURL, NetworkInfo } from "../routes/network";

// Access tokens are short-lived; keep latest in memory for fast access
let accessToken: string | null = localStorage.getItem("accessToken");
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
  if (accessToken) {
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
        const newToken = (refreshResponse as any).data.access;
        accessToken = newToken;
        localStorage.setItem("accessToken", newToken);
        processQueue(newToken);
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      } catch (refreshErr) {
        processQueue(null);
        // Optionally: localStorage.clear(); redirect to login
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;

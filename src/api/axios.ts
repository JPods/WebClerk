import axios from "axios";
import { AuthURL, NetworkInfo } from "../routes/network";

let accessToken = localStorage.getItem("accessToken");

const axiosInstance = axios.create({
  baseURL: NetworkInfo.URL,
});

// Attach token to every request
axiosInstance.interceptors.request.use(
  (config) => {
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Automatically try refresh if token fails
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = localStorage.getItem("refreshToken");
        const refreshResponse = await axios.post(NetworkInfo.URL+AuthURL.REFRESH_TOKEN, {
          refreshToken,
        }); // use plain axios
        const newToken = refreshResponse.data.access;

        // Update token
        //accessToken = newToken;
        localStorage.setItem("accessToken", newToken);

        // Update header and retry original request
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return axiosInstance(originalRequest);
      } catch (err) {
        // Redirect or handle logout
        // window.location.href = PageRoutes.login;
        return Promise.reject(err);
      }
    }

    return Promise.reject(error);
  }
);

export default axiosInstance;


import axios from "axios";
import { AuthURL, NetworkInfo } from "../routes/network";

const axiosInstance = axios.create({
  baseURL: NetworkInfo.URL,
  withCredentials: true, // IMPORTANT: send cookies!
});

// Automatically try refresh if token fails
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        // Try to refresh the token (via cookie)
        await axiosInstance.post(AuthURL.REFRESH_TOKEN);
        return axiosInstance(originalRequest); // Retry original request
      } catch (err) {
        // Redirect to login if refresh fails       
        //window.location.href = PageRoutes.login;
        return Promise.reject(err);
      }
    }

    return Promise.reject(error);
  }
);

export default axiosInstance;

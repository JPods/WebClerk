import apiClient, { authClient } from "./axios"; // separated clients
import { EmailVerifyFormData, RegisterFormData } from "../validations/auth"; // Adjust the import path as necessary
import { AuthURL, PostLoginURL } from "../routes/network"; // Adjust the import path as necessary

export const login = async (credentials:any) => {
  try {
  const res = await authClient.post(AuthURL.LOGIN, credentials);
    return res.data.data;
  }
  catch (error: any) {
    return error.response?.data || error.message
  }
};

export const signup = async (userData: RegisterFormData) => {
  const res = await authClient.post(AuthURL.SIGNUP, userData);
  return res;
};

export const logout = async () => {
  try {
        const refreshToken = localStorage.getItem("refreshToken");
  const res = await authClient.post(AuthURL.LOGOUT,{
            refresh:refreshToken,
        });
        localStorage.clear();
        return res.data;
  } catch (error:any) {
        return error.response?.status || error.message
  }
};

export const userDetails = async () => {
  try {
  const res = await apiClient.get(PostLoginURL.getUser);
    return res;
  }
  catch (error: any) {
    return error.response?.data || error.message
  }
};

export const verifyEmail = async (userData:EmailVerifyFormData) => {
  try {
  const res = await authClient.post(AuthURL.verifyEmail, userData);
    return res;
  }
  catch (error: any) {
    return error.response?.data || error.message
  }
};
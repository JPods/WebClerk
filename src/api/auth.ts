import axiosInstance from "./axios"; // or wherever your axiosInstance is
import { LoginFormData, RegisterFormData } from "../validations/auth"; // Adjust the import path as necessary
import { AuthURL, PostLoginURL } from "../routes/network"; // Adjust the import path as necessary

export const login = async (credentials:any) => {
  try {
    const res = await axiosInstance.post(AuthURL.LOGIN, credentials);
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

export const signup = async (userData: RegisterFormData) => {
  const res = await axiosInstance.post(AuthURL.SIGNUP, userData);
  return res.data;
};

export const logout = async () => {
  try {
        const refreshToken = localStorage.getItem("refreshToken");
        const res = await axiosInstance.post(AuthURL.LOGOUT,{
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
    const res = await axiosInstance.get(PostLoginURL.getUser);
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};
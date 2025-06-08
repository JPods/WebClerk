import axiosInstance from "./axios"; // or wherever your axiosInstance is
import { LoginFormData, RegisterFormData } from "../validations/auth"; // Adjust the import path as necessary
import { AuthURL, PostLoginURL } from "../routes/network"; // Adjust the import path as necessary

export const login = async (credentials:LoginFormData) => {
  try {
    const res = await axiosInstance.post(AuthURL.LOGIN, credentials);
    return res.data;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

export const register = async (userData: RegisterFormData) => {
  const res = await axiosInstance.post("/auth/register", userData);
  return res.data;
};

export const logout = async () => {
  const res = await axiosInstance.post(AuthURL.LOGOUT); // assuming it's a POST
  return res.data;
};

export const userDetails = async () => {
  try {
    const res = await axiosInstance.get(PostLoginURL.getUser);
    return res.data;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};
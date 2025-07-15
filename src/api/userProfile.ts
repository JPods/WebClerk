import axiosInstance from "./axios"; // or wherever your axiosInstance is
import { PostLoginURL } from "../routes/network"; // Adjust the import path as necessary

export const patchUserProfile = async (data:any) => {
  try {
    const res = await axiosInstance.patch(PostLoginURL.updateProfile,{...data});
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

export const postPhone = async (data:any) => {
  try {
    const res = await axiosInstance.post(PostLoginURL.addPhone,{...data});
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

export const postEmail = async (data:any) => {
  try {
    const res = await axiosInstance.post(PostLoginURL.addEmail,{...data});
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

export const postAddress = async (data:any) => {
  try {
    const res = await axiosInstance.post(PostLoginURL.addAddress,{...data});
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

export const postDomain = async (data:any) => {
  try {
    const res = await axiosInstance.post(PostLoginURL.addDomains,{...data});
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};
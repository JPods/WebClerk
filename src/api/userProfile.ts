import axiosInstance from "./axios"; // or wherever your axiosInstance is
import { PostLoginURL } from "../routes/network"; // Adjust the import path as necessary

export const patchPhone = async (id:any,data:any) => {
  try {
    const res = await axiosInstance.patch(PostLoginURL.addPhone + id,{data});
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};
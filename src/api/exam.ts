import axiosInstance from "./axios"; // or wherever your axiosInstance is
import { PostLoginURL } from "../routes/network"; // Adjust the import path as necessary

export const getExamList = async (schoolId:number) => {
  try {
    const res = await axiosInstance.get(PostLoginURL.examListing + '/' + schoolId);
    return res.data;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};
import apiClient from "./axios"; // unified protected API client
import { PostLoginURL } from "../routes/network"; // Adjust the import path as necessary

export const patchUserProfile = async (data:any) => {
  try {
  const res = await apiClient.patch(PostLoginURL.updateProfile,{...data});
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

export const postPhone = async (data:any) => {
  try {
  const res = await apiClient.post(PostLoginURL.addPhone,{...data});
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

export const getPhone = async (id:any = '') => {
  const url = (id === '') ? PostLoginURL.addPhone : PostLoginURL.addPhone + id;
  try {
  const res = await apiClient.get(url);
    return res.data;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

export const postEmail = async (data:any) => {
  try {
  const res = await apiClient.post(PostLoginURL.addEmail,{...data});
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

export const getEmail = async (id:any = '') => {
  const url = (id === '') ? PostLoginURL.addEmail : PostLoginURL.addEmail + id;
  try {
  const res = await apiClient.get(url);
    return res.data;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

export const postAddress = async (data:any) => {
  try {
  const res = await apiClient.post(PostLoginURL.addAddress,{...data});
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

export const getAddress = async (id:any='') => {
   const url = (id === '') ? PostLoginURL.addAddress : PostLoginURL.addAddress + id;
  try {
  const res = await apiClient.get(url);
    return res.data;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

export const postDomain = async (data:any) => {
  try {
  const res = await apiClient.post(PostLoginURL.addDomains,{...data});
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

export const getDomain = async (id:any='') => {
   const url = (id === '') ? PostLoginURL.addDomains : PostLoginURL.addDomains + id;
  try {
  const res = await apiClient.get(url);
    return res.data;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

export const postAction = async (data:any) => {
  try {
  const res = await apiClient.post(PostLoginURL.addActions,{...data});
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

export const getAction = async (id:any = '') => {
  const url = (id === '') ? PostLoginURL.addActions : PostLoginURL.addActions + id;
  try {
  const res = await apiClient.get(url);
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

export const patchAction = async (id:any,data:any) => {
  try {
  const res = await apiClient.patch(PostLoginURL.addActions + id +'/', {...data});
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

export const deleteAction = async (id:any) => {
  try {
  const res = await apiClient.delete(PostLoginURL.addActions + id +'/');
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};  

export const Contacts = async () => {
  try {
  const res = await apiClient.get(PostLoginURL.allTypes + 'table_name=contacts' );
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

export const Actions = async () => {
  try {
  const res = await apiClient.get(PostLoginURL.allTypes + 'table_name=actions' );
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

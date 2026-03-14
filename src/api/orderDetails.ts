/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import apiClient from "./axios"; // unified protected API client
import { PostLoginURL } from "../routes/network"; // Adjust the import path as necessary

export const getOrdersData = async (id:any = '') => {
  try {
  const res = await apiClient.get(PostLoginURL.allTypes + 'model_name=order' + (id ? `&id=${id}` : ''));
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};

export const getInvoiceData = async (id:any = '') => {
  try {
  const res = await apiClient.get(PostLoginURL.allTypes + 'model_name=invoice' + (id ? `&id=${id}` : '') );
    return res;
  }
  catch (error: any) { 
    return error.response?.data || error.message   
  }  
};
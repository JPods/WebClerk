import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import { deleteRecord } from "@/api/wcapi";
import type {
  CreateCustomerRequest,
  CustomerApiTask,
  UpdateCustomerRequest,
} from "../types/customerType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createCustomer = async (
  payload: CreateCustomerRequest
): Promise<CustomerApiTask> => {
  const model_name: string = "customer";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<CustomerApiTask>(res);
};

export const updateCustomer = async (
  payload: UpdateCustomerRequest
): Promise<CustomerApiTask> => {
  const model_name: string = "customer";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<CustomerApiTask>(res);
};

export const deleteCustomer = async (id: number) => {
  return deleteRecord("customer", id);
};

export const fetchCustomers = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=customer" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchCustomer = async (): Promise<CustomerApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=customer");
  return unwrap<CustomerApiTask[]>(res);
};
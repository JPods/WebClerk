import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateCustomerRequest,
  CustomerApiTask,
  UpdateCustomerRequest,
} from "../types/customerType";

export const createCustomer = async (
  payload: CreateCustomerRequest
): Promise<CustomerApiTask> => {
  const res = await saveRecord("customer", payload);
  return res;
};

export const updateCustomer = async (
  payload: UpdateCustomerRequest
): Promise<CustomerApiTask> => {
  const res = await saveRecord("customer", payload);
  return res;
};

export const deleteCustomer = async (id: number) => {
  return deleteRecord("customer", id);
};

export const fetchCustomers = async (params?: any) => {
  const res = await getRecords("customer", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchCustomer = async (): Promise<CustomerApiTask[]> => {
  const res = await getRecords("customer");
  return res.results || [];
};
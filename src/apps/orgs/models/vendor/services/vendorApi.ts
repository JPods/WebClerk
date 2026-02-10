import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import { deleteRecord } from "@/api/wcapi";
import type {
  CreateVendorRequest,
  VendorApiTask,
  UpdateVendorRequest,
} from "../types/vendorType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createVendor = async (
  payload: CreateVendorRequest
): Promise<VendorApiTask> => {
  const model_name: string = "vendor";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<VendorApiTask>(res);
};

export const updateVendor = async (
  payload: UpdateVendorRequest
): Promise<VendorApiTask> => {
  const model_name: string = "vendor";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<VendorApiTask>(res);
};

export const deleteVendor = async (id: number) => {
  return deleteRecord("vendor", id);
};

export const fetchVendors = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=vendor" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchVendor = async (): Promise<VendorApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=vendor");
  return unwrap<VendorApiTask[]>(res);
};
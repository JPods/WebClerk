import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import { deleteRecord } from "@/api/wcapi";
import type {
  CreateServiceRequest,
  ServiceApiTask,
  UpdateServiceRequest,
} from "../types/serviceType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createService = async (
  payload: CreateServiceRequest
): Promise<ServiceApiTask> => {
  const model_name: string = "service";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<ServiceApiTask>(res);
};

export const updateService = async (
  payload: UpdateServiceRequest
): Promise<ServiceApiTask> => {
  const model_name: string = "service";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<ServiceApiTask>(res);
};

export const deleteService = async (id: number) => {
  return deleteRecord('service', id);
};

export const fetchServices = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=service" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchService = async (): Promise<ServiceApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=service");
  return unwrap<ServiceApiTask[]>(res);
};
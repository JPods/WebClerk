import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import { deleteRecord } from "@/api/wcapi";
import type {
  CreateManufacturerRequest,
  ManufacturerApiTask,
  UpdateManufacturerRequest,
} from "../types/manufacturerType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createManufacturer = async (
  payload: CreateManufacturerRequest
): Promise<ManufacturerApiTask> => {
  const model_name: string = "manufacturer";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<ManufacturerApiTask>(res);
};

export const updateManufacturer = async (
  payload: UpdateManufacturerRequest
): Promise<ManufacturerApiTask> => {
  const model_name: string = "manufacturer";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<ManufacturerApiTask>(res);
};

export const deleteManufacturer = async (id: number) => {
  return deleteRecord("manufacturer", id);
};

export const fetchManufacturers = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=manufacturer" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchManufacturer = async (): Promise<ManufacturerApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=manufacturer");
  return unwrap<ManufacturerApiTask[]>(res);
};
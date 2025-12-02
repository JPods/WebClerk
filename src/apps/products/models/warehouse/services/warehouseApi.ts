import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import type {
  CreateWarehouseRequest,
  WarehouseApiTask,
  UpdateWarehouseRequest,
} from "../types/warehouseType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createWarehouse = async (
  payload: CreateWarehouseRequest
): Promise<WarehouseApiTask> => {
  const model_name: string = "warehouse";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<WarehouseApiTask>(res);
};

export const updateWarehouse = async (
  payload: UpdateWarehouseRequest
): Promise<WarehouseApiTask> => {
  const model_name: string = "warehouse";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<WarehouseApiTask>(res);
};

export const deleteWarehouse = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchWarehouses = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=warehouse" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchWarehouse = async (): Promise<WarehouseApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=warehouse");
  return unwrap<WarehouseApiTask[]>(res);
};
import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import type {
  CreateItemRequest,
  ItemApiTask,
  UpdateItemRequest,
} from "../types/itemType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createItem = async (
  payload: CreateItemRequest
): Promise<ItemApiTask> => {
  const model_name: string = "item";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<ItemApiTask>(res);
};

export const updateItem = async (
  payload: UpdateItemRequest
): Promise<ItemApiTask> => {
  const model_name: string = "item";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<ItemApiTask>(res);
};

export const deleteItem = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchItems = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=item" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchItem = async (): Promise<ItemApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=item");
  return unwrap<ItemApiTask[]>(res);
};
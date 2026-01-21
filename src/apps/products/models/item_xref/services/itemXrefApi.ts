import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import type {
  CreateItemXrefRequest,
  ItemXrefApiTask,
  UpdateItemXrefRequest,
} from "../types/itemXrefType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createItemXref = async (
  payload: CreateItemXrefRequest
): Promise<ItemXrefApiTask> => {
  const model_name: string = "item_xref";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<ItemXrefApiTask>(res);
};

export const updateItemXref = async (
  payload: UpdateItemXrefRequest
): Promise<ItemXrefApiTask> => {
  const model_name: string = "item_xref";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<ItemXrefApiTask>(res);
};

export const deleteItemXref = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchItemXrefs = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=item_xref" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchItemXref = async (): Promise<ItemXrefApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=item_xref");
  return unwrap<ItemXrefApiTask[]>(res);
};
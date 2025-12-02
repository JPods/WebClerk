import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import type {
  CreateOtherRequest,
  OtherApiTask,
  UpdateOtherRequest,
} from "../types/otherType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createOther = async (
  payload: CreateOtherRequest
): Promise<OtherApiTask> => {
  const model_name: string = "other";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<OtherApiTask>(res);
};

export const updateOther = async (
  payload: UpdateOtherRequest
): Promise<OtherApiTask> => {
  const model_name: string = "other";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<OtherApiTask>(res);
};

export const deleteOther = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchOthers = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=other" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchOther = async (): Promise<OtherApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=other");
  return unwrap<OtherApiTask[]>(res);
};
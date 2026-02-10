import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import { deleteRecord } from "@/api/wcapi";
import type {
  CreateRepRequest,
  RepApiTask,
  UpdateRepRequest,
} from "../types/repType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createRep = async (
  payload: CreateRepRequest
): Promise<RepApiTask> => {
  const model_name: string = "rep";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<RepApiTask>(res);
};

export const updateRep = async (
  payload: UpdateRepRequest
): Promise<RepApiTask> => {
  const model_name: string = "rep";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<RepApiTask>(res);
};

export const deleteRep = async (id: number) => {
  return deleteRecord("rep", id);
};

export const fetchReps = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=rep" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchRep = async (): Promise<RepApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=rep");
  return unwrap<RepApiTask[]>(res);
};
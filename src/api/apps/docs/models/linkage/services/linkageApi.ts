import apiClient from "../../../../../axios";
import { PostLoginURL } from "../../../../../../routes/network";
import type {
  CreateLinkageRequest,
  LinkageApiTask,
  UpdateLinkageRequest,
} from "../types/linkageType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createLinkage = async (
  payload: CreateLinkageRequest
): Promise<LinkageApiTask> => {
  const model_name: string = "linkage";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<LinkageApiTask>(res);
};

export const updateLinkage = async (
  payload: UpdateLinkageRequest
): Promise<LinkageApiTask> => {
  const model_name: string = "linkage";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<LinkageApiTask>(res);
};

export const deleteLinkage = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchLinkages = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=linkage" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchLinkage = async (): Promise<LinkageApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=linkage");
  return unwrap<LinkageApiTask[]>(res);
};
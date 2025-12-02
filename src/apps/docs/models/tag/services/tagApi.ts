import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import type {
  CreateTagRequest,
  TagApiTask,
  UpdateTagRequest,
} from "../types/tagType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createTag = async (
  payload: CreateTagRequest
): Promise<TagApiTask> => {
  const model_name: string = "tag";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<TagApiTask>(res);
};

export const updateTag = async (
  payload: UpdateTagRequest
): Promise<TagApiTask> => {
  const model_name: string = "tag";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<TagApiTask>(res);
};

export const deleteTag = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchTags = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=tag" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchTag = async (): Promise<TagApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=tag");
  return unwrap<TagApiTask[]>(res);
};
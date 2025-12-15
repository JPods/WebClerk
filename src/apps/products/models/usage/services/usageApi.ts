import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import type {
  CreateUsageRequest,
  UsageApiTask,
  UpdateUsageRequest,
} from "../types/usageType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createUsage = async (
  payload: CreateUsageRequest
): Promise<UsageApiTask> => {
  const model_name: string = "usage";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<UsageApiTask>(res);
};

export const updateUsage = async (
  payload: UpdateUsageRequest
): Promise<UsageApiTask> => {
  const model_name: string = "usage";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<UsageApiTask>(res);
};

export const deleteUsage = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchUsages = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=usage" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchUsage = async (): Promise<UsageApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=usage");
  return unwrap<UsageApiTask[]>(res);
};
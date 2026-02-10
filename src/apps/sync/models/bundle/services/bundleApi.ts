import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import { deleteRecord } from "@/api/wcapi";
import type {
  CreateBundleRequest,
  BundleApiTask,
  UpdateBundleRequest,
} from "../types/bundleType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createBundle = async (
  payload: CreateBundleRequest
): Promise<BundleApiTask> => {
  const model_name: string = "bundle";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<BundleApiTask>(res);
};

export const updateBundle = async (
  payload: UpdateBundleRequest
): Promise<BundleApiTask> => {
  const model_name: string = "bundle";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<BundleApiTask>(res);
};

export const deleteBundle = async (id: number) => {
  return deleteRecord("bundle", id);
};

export const fetchBundles = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=bundle" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchBundle = async (): Promise<BundleApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=bundle");
  return unwrap<BundleApiTask[]>(res);
};
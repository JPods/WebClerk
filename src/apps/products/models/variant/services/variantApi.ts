import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import { deleteRecord } from "@/api/wcapi";
import type {
  CreateVariantRequest,
  VariantApiTask,
  UpdateVariantRequest,
} from "../types/variantType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createVariant = async (
  payload: CreateVariantRequest
): Promise<VariantApiTask> => {
  const model_name: string = "variant";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<VariantApiTask>(res);
};

export const updateVariant = async (
  payload: UpdateVariantRequest
): Promise<VariantApiTask> => {
  const model_name: string = "variant";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<VariantApiTask>(res);
};

export const deleteVariant = async (id: number) => {
  return deleteRecord("variant", id);
};

export const fetchVariants = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=variant" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchVariant = async (): Promise<VariantApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=variant");
  return unwrap<VariantApiTask[]>(res);
};
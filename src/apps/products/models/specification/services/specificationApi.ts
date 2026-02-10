import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import { deleteRecord } from "@/api/wcapi";
import type {
  CreateSpecificationRequest,
  SpecificationApiTask,
  UpdateSpecificationRequest,
} from "../types/specificationType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createSpecification = async (
  payload: CreateSpecificationRequest
): Promise<SpecificationApiTask> => {
  const model_name: string = "specification";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<SpecificationApiTask>(res);
};

export const updateSpecification = async (
  payload: UpdateSpecificationRequest
): Promise<SpecificationApiTask> => {
  const model_name: string = "specification";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<SpecificationApiTask>(res);
};

export const deleteSpecification = async (id: number) => {
  return deleteRecord("specification", id);
};

export const fetchSpecifications = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=specification" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchSpecification = async (): Promise<SpecificationApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=specification");
  return unwrap<SpecificationApiTask[]>(res);
};
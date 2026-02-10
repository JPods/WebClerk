import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import { deleteRecord } from "@/api/wcapi";
import type {
  CreateMatricsRequest,
  MatricsApiTask,
  UpdateMatricsRequest,
} from "../types/matricsType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createMatrics = async (
  payload: CreateMatricsRequest
): Promise<MatricsApiTask> => {
  const model_name: string = "matrics";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<MatricsApiTask>(res);
};

export const updateMatrics = async (
  payload: UpdateMatricsRequest
): Promise<MatricsApiTask> => {
  const model_name: string = "matrics";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<MatricsApiTask>(res);
};

export const deleteMatrics = async (id: number) => {
  return deleteRecord("matrics", id);
};

export const fetchMatricss = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=matrics" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchMatrics = async (): Promise<MatricsApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=matrics");
  return unwrap<MatricsApiTask[]>(res);
};
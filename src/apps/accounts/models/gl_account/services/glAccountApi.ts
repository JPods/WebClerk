import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import type {
  CreateGLAccountRequest,
  GLAccountApiTask,
  UpdateGLAccountRequest,
} from "../types/glAccountType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createGLAccount = async (
  payload: CreateGLAccountRequest
): Promise<GLAccountApiTask> => {
  const model_name: string = "gl_account";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<GLAccountApiTask>(res);
};

export const updateGLAccount = async (
  payload: UpdateGLAccountRequest
): Promise<GLAccountApiTask> => {
  const model_name: string = "gl_account";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<GLAccountApiTask>(res);
};

export const deleteGLAccount = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchGLAccounts = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=gl_account" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchGLAccount = async (): Promise<GLAccountApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=gl_account");
  return unwrap<GLAccountApiTask[]>(res);
};
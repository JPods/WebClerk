import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import type {
  CreateConnectionRequest,
  ConnectionApiTask,
  UpdateConnectionRequest,
} from "../types/connectionType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createConnection = async (
  payload: CreateConnectionRequest
): Promise<ConnectionApiTask> => {
  const model_name: string = "connection";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<ConnectionApiTask>(res);
};

export const updateConnection = async (
  payload: UpdateConnectionRequest
): Promise<ConnectionApiTask> => {
  const model_name: string = "connection";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<ConnectionApiTask>(res);
};

export const deleteConnection = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchConnections = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=connection" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchConnection = async (): Promise<ConnectionApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=connection");
  return unwrap<ConnectionApiTask[]>(res);
};
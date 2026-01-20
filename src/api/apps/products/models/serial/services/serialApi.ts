import apiClient from "../../../../../axios";
import { PostLoginURL } from "../../../../../../routes/network";
import type {
  CreateSerialRequest,
  SerialApiTask,
  UpdateSerialRequest,
} from "../types/serialType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createSerial = async (
  payload: CreateSerialRequest
): Promise<SerialApiTask> => {
  const model_name: string = "serial";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<SerialApiTask>(res);
};

export const updateSerial = async (
  payload: UpdateSerialRequest
): Promise<SerialApiTask> => {
  const model_name: string = "serial";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<SerialApiTask>(res);
};

export const deleteSerial = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchSerials = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=serial" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchSerial = async (): Promise<SerialApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=serial");
  return unwrap<SerialApiTask[]>(res);
};
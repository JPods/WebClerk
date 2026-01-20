import apiClient from "../../../../../axios";
import { PostLoginURL } from "../../../../../../routes/network";
import type {
  CreatePhoneRequest,
  UpdatePhoneRequest,
  PhoneApiTask,
} from "../types/phoneType";
import { getRecords, saveRecord, deleteRecord } from "../../../../../wcapi";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createPhone = async (
  payload: CreatePhoneRequest
): Promise<PhoneApiTask> => {
  const model_name: string = "phone";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<PhoneApiTask>(res);
};

export const updatePhone = async (
  payload: UpdatePhoneRequest
): Promise<PhoneApiTask> => {
  const model_name: string = "phone";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<PhoneApiTask>(res);
};

export const deletePhone = async (id: number) => {
  return deleteRecord("phone", id);
};

export const fetchPhones = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=phone" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

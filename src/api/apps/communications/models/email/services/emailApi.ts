import apiClient from "../../../../../axios";
import { PostLoginURL } from "../../../../../../routes/network";
import {
  CreateEmailRequest,
  EmailApiTask,
  UpdateEmailRequest,
} from "../types/emailType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createEmail = async (
  payload: CreateEmailRequest
): Promise<EmailApiTask> => {
  const model_name: string = "email";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<EmailApiTask>(res);
};

export const updateEmail = async (
  payload: UpdateEmailRequest
): Promise<EmailApiTask> => {
  const model_name: string = "email";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<EmailApiTask>(res);
};

export const deleteEmail = async (model_name: string, id: number) => {
  try {
    const res = await apiClient.post(PostLoginURL.allSave, {
      model_name,
      id,
      action: { mode: "delete" },
    });
    return res;
  } catch (error) {
    const axiosError = error as any;
    return axiosError.response?.data || axiosError.message;
  }
};

export const fetchEmails = async (id?: number) => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=email" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

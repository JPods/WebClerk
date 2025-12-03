import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import type {
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

export const deleteEmail = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchEmails = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=email" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchEmail = async (): Promise<EmailApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=email");
  return unwrap<EmailApiTask[]>(res);
};
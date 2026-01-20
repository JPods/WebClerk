import apiClient from "../../../../../axios";
import { PostLoginURL } from "../../../../../../routes/network";
import type {
  CreateTemplateRequest,
  TemplateApiTask,
  UpdateTemplateRequest,
} from "../types/templateType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createTemplate = async (
  payload: CreateTemplateRequest
): Promise<TemplateApiTask> => {
  const model_name: string = "template";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<TemplateApiTask>(res);
};

export const updateTemplate = async (
  payload: UpdateTemplateRequest
): Promise<TemplateApiTask> => {
  const model_name: string = "template";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<TemplateApiTask>(res);
};

export const deleteTemplate = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchTemplates = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=template" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchTemplate = async (): Promise<TemplateApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=template");
  return unwrap<TemplateApiTask[]>(res);
};
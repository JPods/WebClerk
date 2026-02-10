import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateTemplateRequest,
  TemplateApiTask,
  UpdateTemplateRequest,
} from "../types/templateType";

export const createTemplate = async (
  payload: CreateTemplateRequest
): Promise<TemplateApiTask> => {
  const res = await saveRecord("template", payload);
  return res;
};

export const updateTemplate = async (
  payload: UpdateTemplateRequest
): Promise<TemplateApiTask> => {
  const res = await saveRecord("template", payload);
  return res;
};

export const deleteTemplate = async (id: number) => {
  return deleteRecord("template", id);
};

export const fetchTemplates = async (params?: any) => {
  const res = await getRecords("template", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchTemplate = async (): Promise<TemplateApiTask[]> => {
  const res = await getRecords("template");
  return res.results || [];
};
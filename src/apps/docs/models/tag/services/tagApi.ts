import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateTagRequest,
  TagApiTask,
  UpdateTagRequest,
} from "../types/tagType";

export const createTag = async (
  payload: CreateTagRequest
): Promise<TagApiTask> => {
  const res = await saveRecord("tag", payload);
  return res;
};

export const updateTag = async (
  payload: UpdateTagRequest
): Promise<TagApiTask> => {
  const res = await saveRecord("tag", payload);
  return res;
};

export const deleteTag = async (id: number) => {
  return deleteRecord("tag", id);
};

export const fetchTags = async (params?: any) => {
  const res = await getRecords("tag", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchTag = async (): Promise<TagApiTask[]> => {
  const res = await getRecords("tag");
  return res.results || [];
};
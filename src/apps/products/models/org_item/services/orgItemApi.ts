import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import { deleteRecord } from "@/api/wcapi";
import type {
  CreateOrgItemRequest,
  OrgItemApiTask,
  UpdateOrgItemRequest,
} from "../types/orgItemType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createOrgItem = async (
  payload: CreateOrgItemRequest
): Promise<OrgItemApiTask> => {
  const model_name: string = "org_item";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<OrgItemApiTask>(res);
};

export const updateOrgItem = async (
  payload: UpdateOrgItemRequest
): Promise<OrgItemApiTask> => {
  const model_name: string = "org_item";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<OrgItemApiTask>(res);
};

export const deleteOrgItem = async (id: number) => {
  return deleteRecord("org_item", id);
};

export const fetchOrgItems = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=org_item" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchOrgItem = async (): Promise<OrgItemApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=org_item");
  return unwrap<OrgItemApiTask[]>(res);
};
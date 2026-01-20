import apiClient from "../../../../../axios";
import { PostLoginURL } from "../../../../../../routes/network";
import type {
  CreateOrganizationRequest,
  OrganizationApiTask,
  UpdateOrganizationRequest,
} from "../types/organizationType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createOrganization = async (
  payload: CreateOrganizationRequest
): Promise<OrganizationApiTask> => {
  const model_name: string = "other";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<OrganizationApiTask>(res);
};

export const updateOrganization = async (
  payload: UpdateOrganizationRequest
): Promise<OrganizationApiTask> => {
  const model_name: string = "other";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<OrganizationApiTask>(res);
};

export const deleteOrganization = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchOrganizations = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=other" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchOrganization = async (): Promise<OrganizationApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=other");
  return unwrap<OrganizationApiTask[]>(res);
};

import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import { deleteRecord } from "@/api/wcapi";
import type {
  CreateDomainRequest,
  DomainApiTask,
  UpdateDomainRequest,
} from "../types/domainType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};
//await apiClient.get(PostLoginURL.allTypes + 'model_name=contact' + (id ? `&id=${id}` : '') );
export const createDomain = async (
  payload: CreateDomainRequest
): Promise<DomainApiTask> => {
  const model_name: string = "domain";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<DomainApiTask>(res);
};

export const updateDomain = async (
  payload: UpdateDomainRequest
): Promise<DomainApiTask> => {
  const model_name: string = "domain";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<DomainApiTask>(res);
};

export const deleteDomain = async (id: number) => {
  return deleteRecord("domain", id);
};

export const fetchDomains = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=domain" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchDomain = async (): Promise<DomainApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=domain");
  return unwrap<DomainApiTask[]>(res);
};

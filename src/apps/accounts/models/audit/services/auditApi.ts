import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import type {
  CreateAuditRequest,
  AuditApiTask,
  UpdateAuditRequest,
} from "../types/auditType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createAudit = async (
  payload: CreateAuditRequest
): Promise<AuditApiTask> => {
  const model_name: string = "audit";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<AuditApiTask>(res);
};

export const updateAudit = async (
  payload: UpdateAuditRequest
): Promise<AuditApiTask> => {
  const model_name: string = "audit";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<AuditApiTask>(res);
};

export const deleteAudit = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchAudits = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=audit" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchAudit = async (): Promise<AuditApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=audit");
  return unwrap<AuditApiTask[]>(res);
};
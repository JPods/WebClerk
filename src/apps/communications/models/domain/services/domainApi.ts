import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateDomainRequest,
  DomainApiTask,
  UpdateDomainRequest,
} from "../types/domainType";

export const createDomain = async (
  payload: CreateDomainRequest
): Promise<DomainApiTask> => {
  const res = await saveRecord("domain", payload);
  return res;
};

export const updateDomain = async (
  payload: UpdateDomainRequest
): Promise<DomainApiTask> => {
  const res = await saveRecord("domain", payload);
  return res;
};

export const deleteDomain = async (id: number) => {
  return deleteRecord("domain", id);
};

export const fetchDomains = async (params?: any) => {
  const res = await getRecords("domain", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchDomain = async (): Promise<DomainApiTask[]> => {
  const res = await getRecords("domain");
  return res.results || [];
};

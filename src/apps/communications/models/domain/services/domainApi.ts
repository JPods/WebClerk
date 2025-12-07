import { getRecords, saveRecord, deleteRecord } from "../../../../../api/wcapi";
import type {
  CreateDomainRequest,
  UpdateDomainRequest,
} from "../types/domainType";

export const createDomain = async (data: CreateDomainRequest) => {
  return saveRecord('domain', data);
};

export const updateDomain = async (data: UpdateDomainRequest) => {
  return saveRecord('domain', data);
};

export const deleteDomain = async (id: number) => {
  return deleteRecord('domain', id);
};

export const fetchDomains = async (params?: any) => {
  const res = await getRecords('domain', params);
  return { status: 200, data: { items: res.results || [] } };
};
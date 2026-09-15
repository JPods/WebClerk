/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateOrganizationRequest,
  OrganizationApiTask,
  UpdateOrganizationRequest,
} from "../types/organizationType";

export const createOrganization = async (
  payload: CreateOrganizationRequest
): Promise<OrganizationApiTask> => {
  const res = await saveRecord("other", payload);
  return res;
};

export const updateOrganization = async (
  payload: UpdateOrganizationRequest
): Promise<OrganizationApiTask> => {
  const res = await saveRecord("other", payload);
  return res;
};

export const deleteOrganization = async (id: number) => {
  return deleteRecord("other", id);
};

export const fetchOrganizations = async (params?: any) => {
  const res = await getRecords("other", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchOrganization = async (): Promise<OrganizationApiTask[]> => {
  const res = await getRecords("other");
  return res.results || [];
};

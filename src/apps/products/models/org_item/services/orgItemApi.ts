/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateOrgItemRequest,
  OrgItemApiTask,
  UpdateOrgItemRequest,
} from "../types/orgItemType";

export const createOrgItem = async (
  payload: CreateOrgItemRequest
): Promise<OrgItemApiTask> => {
  return saveRecord("org_item", payload);
};

export const updateOrgItem = async (
  payload: UpdateOrgItemRequest
): Promise<OrgItemApiTask> => {
  return saveRecord("org_item", payload);
};

export const deleteOrgItem = async (id: number) => {
  return deleteRecord("org_item", id);
};

export const fetchOrgItems = async (params?: any) => {
  const res = await getRecords("org_item", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchOrgItem = async (): Promise<OrgItemApiTask[]> => {
  const res = await getRecords("org_item");
  return res.results || [];
};
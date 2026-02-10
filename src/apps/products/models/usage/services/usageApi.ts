import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateUsageRequest,
  UsageApiTask,
  UpdateUsageRequest,
} from "../types/usageType";

export const createUsage = async (
  payload: CreateUsageRequest
): Promise<UsageApiTask> => {
  return saveRecord("usage", payload);
};

export const updateUsage = async (
  payload: UpdateUsageRequest
): Promise<UsageApiTask> => {
  return saveRecord("usage", payload);
};

export const deleteUsage = async (id: number) => {
  return deleteRecord("usage", id);
};

export const fetchUsages = async (params?: any) => {
  const res = await getRecords("usage", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchUsage = async (): Promise<UsageApiTask[]> => {
  const res = await getRecords("usage");
  return res.results || [];
};
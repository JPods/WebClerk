import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateBundleRequest,
  BundleApiTask,
  UpdateBundleRequest,
} from "../types/bundleType";

export const createBundle = async (
  payload: CreateBundleRequest
): Promise<BundleApiTask> => {
  return saveRecord("bundle", payload);
};

export const updateBundle = async (
  payload: UpdateBundleRequest
): Promise<BundleApiTask> => {
  return saveRecord("bundle", payload);
};

export const deleteBundle = async (id: number) => {
  return deleteRecord("bundle", id);
};

export const fetchBundles = async (params?: any) => {
  const res = await getRecords("bundle", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchBundle = async (): Promise<BundleApiTask[]> => {
  const res = await getRecords("bundle");
  return res.results || [];
};
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateVendorRequest,
  VendorApiTask,
  UpdateVendorRequest,
} from "../types/vendorType";

export const createVendor = async (
  payload: CreateVendorRequest
): Promise<VendorApiTask> => {
  const res = await saveRecord("vendor", payload);
  return res;
};

export const updateVendor = async (
  payload: UpdateVendorRequest
): Promise<VendorApiTask> => {
  const res = await saveRecord("vendor", payload);
  return res;
};

export const deleteVendor = async (id: number) => {
  return deleteRecord("vendor", id);
};

export const fetchVendors = async (params?: any) => {
  const res = await getRecords("vendor", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchVendor = async (): Promise<VendorApiTask[]> => {
  const res = await getRecords("vendor");
  return res.results || [];
};
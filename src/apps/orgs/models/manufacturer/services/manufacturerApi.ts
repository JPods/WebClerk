import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateManufacturerRequest,
  ManufacturerApiTask,
  UpdateManufacturerRequest,
} from "../types/manufacturerType";

export const createManufacturer = async (
  payload: CreateManufacturerRequest
): Promise<ManufacturerApiTask> => {
  const res = await saveRecord("manufacturer", payload);
  return res;
};

export const updateManufacturer = async (
  payload: UpdateManufacturerRequest
): Promise<ManufacturerApiTask> => {
  const res = await saveRecord("manufacturer", payload);
  return res;
};

export const deleteManufacturer = async (id: number) => {
  return deleteRecord("manufacturer", id);
};

export const fetchManufacturers = async (params?: any) => {
  const res = await getRecords("manufacturer", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchManufacturer = async (): Promise<ManufacturerApiTask[]> => {
  const res = await getRecords("manufacturer");
  return res.results || [];
};
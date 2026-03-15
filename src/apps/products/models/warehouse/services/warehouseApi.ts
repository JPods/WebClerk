/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateWarehouseRequest,
  WarehouseApiTask,
  UpdateWarehouseRequest,
} from "../types/warehouseType";

export const createWarehouse = async (
  payload: CreateWarehouseRequest
): Promise<WarehouseApiTask> => {
  return saveRecord("warehouse", payload);
};

export const updateWarehouse = async (
  payload: UpdateWarehouseRequest
): Promise<WarehouseApiTask> => {
  return saveRecord("warehouse", payload);
};

export const deleteWarehouse = async (id: number) => {
  return deleteRecord("warehouse", id);
};

export const fetchWarehouses = async (params?: any) => {
  const res = await getRecords("warehouse", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchWarehouse = async (): Promise<WarehouseApiTask[]> => {
  const res = await getRecords("warehouse");
  return res.results || [];
};
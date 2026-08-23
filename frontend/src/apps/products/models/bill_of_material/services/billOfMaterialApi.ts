/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateBillOfMaterialRequest,
  BillOfMaterialApiTask,
  UpdateBillOfMaterialRequest,
} from "../types/billOfMaterialType";

export const createBillOfMaterial = async (
  payload: CreateBillOfMaterialRequest
): Promise<BillOfMaterialApiTask> => {
  return saveRecord("bill_of_material", payload);
};

export const updateBillOfMaterial = async (
  payload: UpdateBillOfMaterialRequest
): Promise<BillOfMaterialApiTask> => {
  return saveRecord("bill_of_material", payload);
};

export const deleteBillOfMaterial = async (id: number) => {
  return deleteRecord("bill_of_material", id);
};

export const fetchBillOfMaterials = async (params?: any) => {
  const res = await getRecords("bill_of_material", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchBillOfMaterial = async (): Promise<BillOfMaterialApiTask[]> => {
  const res = await getRecords("bill_of_material");
  return res.results || [];
};
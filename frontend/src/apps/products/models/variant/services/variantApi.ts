/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateVariantRequest,
  VariantApiTask,
  UpdateVariantRequest,
} from "../types/variantType";

export const createVariant = async (
  payload: CreateVariantRequest
): Promise<VariantApiTask> => {
  return saveRecord("variant", payload);
};

export const updateVariant = async (
  payload: UpdateVariantRequest
): Promise<VariantApiTask> => {
  return saveRecord("variant", payload);
};

export const deleteVariant = async (id: number) => {
  return deleteRecord("variant", id);
};

export const fetchVariants = async (params?: any) => {
  const res = await getRecords("variant", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchVariant = async (): Promise<VariantApiTask[]> => {
  const res = await getRecords("variant");
  return res.results || [];
};
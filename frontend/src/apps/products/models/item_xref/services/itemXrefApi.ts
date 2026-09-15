/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateItemXrefRequest,
  ItemXrefApiTask,
  UpdateItemXrefRequest,
} from "../types/itemXrefType";

export const createItemXref = async (
  payload: CreateItemXrefRequest
): Promise<ItemXrefApiTask> => {
  return saveRecord("item_xref", payload);
};

export const updateItemXref = async (
  payload: UpdateItemXrefRequest
): Promise<ItemXrefApiTask> => {
  return saveRecord("item_xref", payload);
};

export const deleteItemXref = async (id: number) => {
  return deleteRecord("item_xref", id);
};

export const fetchItemXrefs = async (params?: any) => {
  const res = await getRecords("item_xref", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchItemXref = async (): Promise<ItemXrefApiTask[]> => {
  const res = await getRecords("item_xref");
  return res.results || [];
};
/* LastChecked: 2026-06-27 | WhereUsed: ItemList, ItemDetail | WhoCreated: Unknown */
import { getRecords, getRecord, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateItemRequest,
  ItemApiTask,
  UpdateItemRequest,
} from "../types/itemType";

export const createItem = async (
  payload: CreateItemRequest
): Promise<ItemApiTask> => {
  return saveRecord("item", payload) as Promise<ItemApiTask>;
};

export const updateItem = async (
  payload: UpdateItemRequest
): Promise<ItemApiTask> => {
  return saveRecord("item", payload) as Promise<ItemApiTask>;
};

export const deleteItem = async (id: number) => {
  return deleteRecord("item", id);
};

export const fetchItems = async (id: any = "") => {
  if (id) {
    const record = await getRecord("item", id);
    return { status: 200, data: { data: record } };
  }
  const result = await getRecords("item");
  return { status: 200, data: result };
};

export const fetchItem = async (id?: number): Promise<{ data: ItemApiTask | ItemApiTask[] }> => {
  if (id) {
    const record = await getRecord("item", id);
    return { data: record as ItemApiTask };
  }
  const result = await getRecords("item");
  return { data: result as ItemApiTask[] };
};

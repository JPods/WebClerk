/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateCatalogRequest,
  CatalogApiTask,
  UpdateCatalogRequest,
} from "../types/catalogType";

export const createCatalog = async (
  payload: CreateCatalogRequest
): Promise<CatalogApiTask> => {
  return saveRecord("catalog", payload);
};

export const updateCatalog = async (
  payload: UpdateCatalogRequest
): Promise<CatalogApiTask> => {
  return saveRecord("catalog", payload);
};

export const deleteCatalog = async (id: number) => {
  return deleteRecord("catalog", id);
};

export const fetchCatalogs = async (params?: any) => {
  const res = await getRecords("catalog", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchCatalog = async (): Promise<CatalogApiTask[]> => {
  const res = await getRecords("catalog");
  return res.results || [];
};
import apiClient from "../../../../../axios";
import { PostLoginURL } from "../../../../../../routes/network";
import type {
  CreateCatalogRequest,
  CatalogApiTask,
  UpdateCatalogRequest,
} from "../types/catalogType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createCatalog = async (
  payload: CreateCatalogRequest
): Promise<CatalogApiTask> => {
  const model_name: string = "catalog";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<CatalogApiTask>(res);
};

export const updateCatalog = async (
  payload: UpdateCatalogRequest
): Promise<CatalogApiTask> => {
  const model_name: string = "catalog";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<CatalogApiTask>(res);
};

export const deleteCatalog = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchCatalogs = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=catalog" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchCatalog = async (): Promise<CatalogApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=catalog");
  return unwrap<CatalogApiTask[]>(res);
};
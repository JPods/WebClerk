import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import { deleteRecord } from "@/api/wcapi";
import type {
  CreateDocumentRequest,
  DocumentApiTask,
  UpdateDocumentRequest,
} from "../types/documentType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createDocument = async (
  payload: CreateDocumentRequest
): Promise<DocumentApiTask> => {
  const model_name: string = "document";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<DocumentApiTask>(res);
};

export const updateDocument = async (
  payload: UpdateDocumentRequest
): Promise<DocumentApiTask> => {
  const model_name: string = "document";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<DocumentApiTask>(res);
};

export const deleteDocument = async (id: number) => {
  return deleteRecord("document", id);
};

export const fetchDocuments = async () => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=document"
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

/**
 * Fetch a single document by ID
 * API: wcapi/get/?model_name=document&id=X
 */
export const fetchDocumentById = async (id: number | string) => {
  try {
    const res = await apiClient.get(
      `${PostLoginURL.allTypes}model_name=document&id=${id}`
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchDocument = async (): Promise<DocumentApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=document");
  return unwrap<DocumentApiTask[]>(res);
};
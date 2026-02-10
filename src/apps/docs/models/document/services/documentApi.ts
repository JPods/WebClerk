import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateDocumentRequest,
  DocumentApiTask,
  UpdateDocumentRequest,
} from "../types/documentType";

export const createDocument = async (
  payload: CreateDocumentRequest
): Promise<DocumentApiTask> => {
  const res = await saveRecord("document", payload);
  return res;
};

export const updateDocument = async (
  payload: UpdateDocumentRequest
): Promise<DocumentApiTask> => {
  const res = await saveRecord("document", payload);
  return res;
};

export const deleteDocument = async (id: number) => {
  return deleteRecord("document", id);
};

export const fetchDocuments = async (params?: any) => {
  const res = await getRecords("document", params);
  return { status: 200, data: { items: res.results || [] } };
};

/**
 * Fetch a single document by ID
 * API: wcapi/get/?model_name=document&id=X
 */
export const fetchDocumentById = async (id: number | string) => {
  const res = await getRecords("document", { id });
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchDocument = async (): Promise<DocumentApiTask[]> => {
  const res = await getRecords("document");
  return res.results || [];
};
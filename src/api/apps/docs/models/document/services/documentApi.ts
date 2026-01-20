import apiClient from "../../../../../axios";
import { PostLoginURL } from "../../../../../../routes/network";
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

export const deleteDocument = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchDocuments = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=document" + (id ? `&id=${id}` : "")
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
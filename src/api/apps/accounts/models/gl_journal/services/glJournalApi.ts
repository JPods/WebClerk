import apiClient from "../../../../../axios";
import { PostLoginURL } from "../../../../../../routes/network";
import type {
  CreateGLJournalRequest,
  GLJournalApiTask,
  UpdateGLJournalRequest,
} from "../types/glJournalType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createGLJournal = async (
  payload: CreateGLJournalRequest
): Promise<GLJournalApiTask> => {
  const model_name: string = "gl_journal";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<GLJournalApiTask>(res);
};

export const updateGLJournal = async (
  payload: UpdateGLJournalRequest
): Promise<GLJournalApiTask> => {
  const model_name: string = "gl_journal";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<GLJournalApiTask>(res);
};

export const deleteGLJournal = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchGLJournals = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=gl_journal" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchGLJournal = async (): Promise<GLJournalApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=gl_journal");
  return unwrap<GLJournalApiTask[]>(res);
};
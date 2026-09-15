/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateGLJournalRequest,
  GLJournalApiTask,
  UpdateGLJournalRequest,
} from "../types/glJournalType";

export const createGLJournal = async (
  payload: CreateGLJournalRequest
): Promise<GLJournalApiTask> => {
  return saveRecord("gl_journal", payload);
};

export const updateGLJournal = async (
  payload: UpdateGLJournalRequest
): Promise<GLJournalApiTask> => {
  return saveRecord("gl_journal", payload);
};

export const deleteGLJournal = async (id: number) => {
  return deleteRecord("gl_journal", id);
};

export const fetchGLJournals = async (params?: any) => {
  const res = await getRecords("gl_journal", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchGLJournal = async (): Promise<GLJournalApiTask[]> => {
  const res = await getRecords("gl_journal");
  return res.results || [];
};
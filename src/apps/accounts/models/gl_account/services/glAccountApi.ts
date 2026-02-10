import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateGLAccountRequest,
  GLAccountApiTask,
  UpdateGLAccountRequest,
} from "../types/glAccountType";

export const createGLAccount = async (
  payload: CreateGLAccountRequest
): Promise<GLAccountApiTask> => {
  return saveRecord("gl_account", payload);
};

export const updateGLAccount = async (
  payload: UpdateGLAccountRequest
): Promise<GLAccountApiTask> => {
  return saveRecord("gl_account", payload);
};

export const deleteGLAccount = async (id: number) => {
  return deleteRecord("gl_account", id);
};

export const fetchGLAccounts = async (params?: any) => {
  const res = await getRecords("gl_account", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchGLAccount = async (): Promise<GLAccountApiTask[]> => {
  const res = await getRecords("gl_account");
  return res.results || [];
};
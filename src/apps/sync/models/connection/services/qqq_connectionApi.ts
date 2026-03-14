/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateConnectionRequest,
  ConnectionApiTask,
  UpdateConnectionRequest,
} from "../types/connectionType";

export const createConnection = async (
  payload: CreateConnectionRequest
): Promise<ConnectionApiTask> => {
  return saveRecord("connection", payload);
};

export const updateConnection = async (
  payload: UpdateConnectionRequest
): Promise<ConnectionApiTask> => {
  return saveRecord("connection", payload);
};

export const deleteConnection = async (id: number) => {
  return deleteRecord("connection", id);
};

export const fetchConnections = async (params?: any) => {
  const res = await getRecords("connection", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchConnection = async (): Promise<ConnectionApiTask[]> => {
  const res = await getRecords("connection");
  return res.results || [];
};
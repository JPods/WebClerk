/**
 * Connection API - Uses centralized wcapi endpoints
 */
import { getRecords, getRecord, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateConnectionRequest,
  ConnectionApiTask,
  UpdateConnectionRequest,
} from "../types/connectionType";

const MODEL_NAME = "connection";

export const createConnection = async (
  payload: CreateConnectionRequest
): Promise<ConnectionApiTask> => {
  return saveRecord(MODEL_NAME, payload);
};

export const updateConnection = async (
  payload: UpdateConnectionRequest
): Promise<ConnectionApiTask> => {
  return saveRecord(MODEL_NAME, payload);
};

export const deleteConnection = async (id: number) => {
  return deleteRecord(MODEL_NAME, id);
};

export const fetchConnections = async (id?: number | string) => {
  if (id) {
    return getRecord(MODEL_NAME, Number(id));
  }
  return getRecords(MODEL_NAME);
};

export const fetchConnection = async (): Promise<ConnectionApiTask[]> => {
  const result = await getRecords(MODEL_NAME);
  return result.results as ConnectionApiTask[];
};
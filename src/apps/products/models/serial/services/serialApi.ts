import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateSerialRequest,
  SerialApiTask,
  UpdateSerialRequest,
} from "../types/serialType";

export const createSerial = async (
  payload: CreateSerialRequest
): Promise<SerialApiTask> => {
  return saveRecord("serial", payload);
};

export const updateSerial = async (
  payload: UpdateSerialRequest
): Promise<SerialApiTask> => {
  return saveRecord("serial", payload);
};

export const deleteSerial = async (id: number) => {
  return deleteRecord("serial", id);
};

export const fetchSerials = async (params?: any) => {
  const res = await getRecords("serial", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchSerial = async (): Promise<SerialApiTask[]> => {
  const res = await getRecords("serial");
  return res.results || [];
};
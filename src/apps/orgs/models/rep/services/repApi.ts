import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateRepRequest,
  RepApiTask,
  UpdateRepRequest,
} from "../types/repType";

export const createRep = async (
  payload: CreateRepRequest
): Promise<RepApiTask> => {
  const res = await saveRecord("rep", payload);
  return res;
};

export const updateRep = async (
  payload: UpdateRepRequest
): Promise<RepApiTask> => {
  const res = await saveRecord("rep", payload);
  return res;
};

export const deleteRep = async (id: number) => {
  return deleteRecord("rep", id);
};

export const fetchReps = async (params?: any) => {
  const res = await getRecords("rep", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchRep = async (): Promise<RepApiTask[]> => {
  const res = await getRecords("rep");
  return res.results || [];
};
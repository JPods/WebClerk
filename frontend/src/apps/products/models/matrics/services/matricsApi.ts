/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateMatricsRequest,
  MatricsApiTask,
  UpdateMatricsRequest,
} from "../types/matricsType";

export const createMatrics = async (
  payload: CreateMatricsRequest
): Promise<MatricsApiTask> => {
  return saveRecord("matrics", payload);
};

export const updateMatrics = async (
  payload: UpdateMatricsRequest
): Promise<MatricsApiTask> => {
  return saveRecord("matrics", payload);
};

export const deleteMatrics = async (id: number) => {
  return deleteRecord("matrics", id);
};

export const fetchMatricss = async (params?: any) => {
  const res = await getRecords("matrics", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchMatrics = async (): Promise<MatricsApiTask[]> => {
  const res = await getRecords("matrics");
  return res.results || [];
};
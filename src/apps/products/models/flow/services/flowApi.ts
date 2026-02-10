import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateFlowRequest,
  FlowApiTask,
  UpdateFlowRequest,
} from "../types/flowType";

export const createFlow = async (
  payload: CreateFlowRequest
): Promise<FlowApiTask> => {
  return saveRecord("flow", payload);
};

export const updateFlow = async (
  payload: UpdateFlowRequest
): Promise<FlowApiTask> => {
  return saveRecord("flow", payload);
};

export const deleteFlow = async (id: number) => {
  return deleteRecord("flow", id);
};

export const fetchFlows = async (params?: any) => {
  const res = await getRecords("flow", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchFlow = async (): Promise<FlowApiTask[]> => {
  const res = await getRecords("flow");
  return res.results || [];
};
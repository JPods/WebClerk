import apiClient from "../../../../../axios";
import { PostLoginURL } from "../../../../../../routes/network";
import type {
  CreateFlowRequest,
  FlowApiTask,
  UpdateFlowRequest,
} from "../types/flowType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createFlow = async (
  payload: CreateFlowRequest
): Promise<FlowApiTask> => {
  const model_name: string = "flow";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<FlowApiTask>(res);
};

export const updateFlow = async (
  payload: UpdateFlowRequest
): Promise<FlowApiTask> => {
  const model_name: string = "flow";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<FlowApiTask>(res);
};

export const deleteFlow = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchFlows = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=flow" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchFlow = async (): Promise<FlowApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=flow");
  return unwrap<FlowApiTask[]>(res);
};
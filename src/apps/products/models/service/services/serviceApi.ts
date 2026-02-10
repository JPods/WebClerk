import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateServiceRequest,
  ServiceApiTask,
  UpdateServiceRequest,
} from "../types/serviceType";

export const createService = async (
  payload: CreateServiceRequest
): Promise<ServiceApiTask> => {
  return saveRecord("service", payload);
};

export const updateService = async (
  payload: UpdateServiceRequest
): Promise<ServiceApiTask> => {
  return saveRecord("service", payload);
};

export const deleteService = async (id: number) => {
  return deleteRecord("service", id);
};

export const fetchServices = async (params?: any) => {
  const res = await getRecords("service", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchService = async (): Promise<ServiceApiTask[]> => {
  const res = await getRecords("service");
  return res.results || [];
};
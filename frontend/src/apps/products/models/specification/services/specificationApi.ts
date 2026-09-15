/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateSpecificationRequest,
  SpecificationApiTask,
  UpdateSpecificationRequest,
} from "../types/specificationType";

export const createSpecification = async (
  payload: CreateSpecificationRequest
): Promise<SpecificationApiTask> => {
  return saveRecord("specification", payload);
};

export const updateSpecification = async (
  payload: UpdateSpecificationRequest
): Promise<SpecificationApiTask> => {
  return saveRecord("specification", payload);
};

export const deleteSpecification = async (id: number) => {
  return deleteRecord("specification", id);
};

export const fetchSpecifications = async (params?: any) => {
  const res = await getRecords("specification", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchSpecification = async (): Promise<SpecificationApiTask[]> => {
  const res = await getRecords("specification");
  return res.results || [];
};
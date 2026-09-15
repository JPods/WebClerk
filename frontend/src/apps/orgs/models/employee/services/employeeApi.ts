/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateEmployeeRequest,
  EmployeeApiTask,
  UpdateEmployeeRequest,
} from "../types/employeeType";

export const createEmployee = async (
  payload: CreateEmployeeRequest
): Promise<EmployeeApiTask> => {
  const res = await saveRecord("employee", payload);
  return res;
};

export const updateEmployee = async (
  payload: UpdateEmployeeRequest
): Promise<EmployeeApiTask> => {
  const res = await saveRecord("employee", payload);
  return res;
};

export const deleteEmployee = async (id: number) => {
  return deleteRecord("employee", id);
};

export const fetchEmployees = async (params?: any) => {
  const res = await getRecords("employee", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchEmployee = async (): Promise<EmployeeApiTask[]> => {
  const res = await getRecords("employee");
  return res.results || [];
};
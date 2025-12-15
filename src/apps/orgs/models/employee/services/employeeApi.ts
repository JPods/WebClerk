import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import type {
  CreateEmployeeRequest,
  EmployeeApiTask,
  UpdateEmployeeRequest,
} from "../types/employeeType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createEmployee = async (
  payload: CreateEmployeeRequest
): Promise<EmployeeApiTask> => {
  const model_name: string = "employee";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<EmployeeApiTask>(res);
};

export const updateEmployee = async (
  payload: UpdateEmployeeRequest
): Promise<EmployeeApiTask> => {
  const model_name: string = "employee";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<EmployeeApiTask>(res);
};

export const deleteEmployee = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchEmployees = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=employee" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchEmployee = async (): Promise<EmployeeApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=employee");
  return unwrap<EmployeeApiTask[]>(res);
};
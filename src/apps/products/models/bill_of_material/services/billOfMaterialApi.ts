import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import { deleteRecord } from "@/api/wcapi";
import type {
  CreateBillOfMaterialRequest,
  BillOfMaterialApiTask,
  UpdateBillOfMaterialRequest,
} from "../types/billOfMaterialType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createBillOfMaterial = async (
  payload: CreateBillOfMaterialRequest
): Promise<BillOfMaterialApiTask> => {
  const model_name: string = "bill_of_material";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<BillOfMaterialApiTask>(res);
};

export const updateBillOfMaterial = async (
  payload: UpdateBillOfMaterialRequest
): Promise<BillOfMaterialApiTask> => {
  const model_name: string = "bill_of_material";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<BillOfMaterialApiTask>(res);
};

export const deleteBillOfMaterial = async (id: number) => {
  return deleteRecord("bill_of_material", id);
};

export const fetchBillOfMaterials = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=bill_of_material" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchBillOfMaterial = async (): Promise<BillOfMaterialApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=bill_of_material");
  return unwrap<BillOfMaterialApiTask[]>(res);
};
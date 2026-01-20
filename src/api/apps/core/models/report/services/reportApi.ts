import apiClient from "../../../../../axios";
import { PostLoginURL } from "../../../../../../routes/network";
import type {
  CreateReportRequest,
  ReportApiTask,
  UpdateReportRequest,
} from "../types/reportType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createReport = async (
  payload: CreateReportRequest
): Promise<ReportApiTask> => {
  const model_name: string = "report";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<ReportApiTask>(res);
};

export const updateReport = async (
  payload: UpdateReportRequest
): Promise<ReportApiTask> => {
  const model_name: string = "report";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<ReportApiTask>(res);
};

export const deleteReport = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchReports = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=report" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchReport = async (): Promise<ReportApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=report");
  return unwrap<ReportApiTask[]>(res);
};
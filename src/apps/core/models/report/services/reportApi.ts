import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateReportRequest,
  ReportApiTask,
  UpdateReportRequest,
} from "../types/reportType";

export const createReport = async (
  payload: CreateReportRequest
): Promise<ReportApiTask> => {
  const res = await saveRecord("report", payload);
  return res;
};

export const updateReport = async (
  payload: UpdateReportRequest
): Promise<ReportApiTask> => {
  const res = await saveRecord("report", payload);
  return res;
};

export const deleteReport = async (id: number) => {
  return deleteRecord("report", id);
};

export const fetchReports = async (params?: any) => {
  const res = await getRecords("report", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchReport = async (): Promise<ReportApiTask[]> => {
  const res = await getRecords("report");
  return res.results || [];
};
/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateNotificationRequest,
  NotificationApiTask,
  UpdateNotificationRequest,
} from "../types/notificationType";

export const createNotification = async (
  payload: CreateNotificationRequest
): Promise<NotificationApiTask> => {
  const res = await saveRecord("notification", payload);
  return res;
};

export const updateNotification = async (
  payload: UpdateNotificationRequest
): Promise<NotificationApiTask> => {
  const res = await saveRecord("notification", payload);
  return res;
};

export const deleteNotification = async (id: number) => {
  return deleteRecord("notification", id);
};

export const fetchNotifications = async (params?: any) => {
  const res = await getRecords("notification", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchNotification = async (): Promise<NotificationApiTask[]> => {
  const res = await getRecords("notification");
  return res.results || [];
};
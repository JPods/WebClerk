import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import { deleteRecord } from "@/api/wcapi";
import type {
  CreateNotificationRequest,
  NotificationApiTask,
  UpdateNotificationRequest,
} from "../types/notificationType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createNotification = async (
  payload: CreateNotificationRequest
): Promise<NotificationApiTask> => {
  const model_name: string = "notification";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<NotificationApiTask>(res);
};

export const updateNotification = async (
  payload: UpdateNotificationRequest
): Promise<NotificationApiTask> => {
  const model_name: string = "notification";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<NotificationApiTask>(res);
};

export const deleteNotification = async (id: number) => {
  return deleteRecord("notification", id);
};

export const fetchNotifications = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=notification" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchNotification = async (): Promise<NotificationApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=notification");
  return unwrap<NotificationApiTask[]>(res);
};
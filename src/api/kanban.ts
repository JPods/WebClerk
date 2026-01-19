import apiClient from "./axios";
import { PostLoginURL } from "../routes/network";
import type {
  CreateKanbanTaskRequest,
  KanbanApiTask,
  UpdateKanbanTaskStatusRequest,
} from "../apps/utils/kanban/type/kanban";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const fetchKanbanBoard = async (): Promise<KanbanApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.kanbanTasks);
  return unwrap<KanbanApiTask[]>(res);
};

export const updateKanbanTaskStatus = async (
  taskId: string,
  payload: UpdateKanbanTaskStatusRequest
): Promise<KanbanApiTask> => {
  const res = await apiClient.patch(`${PostLoginURL.kanbanTasks}${taskId}/`, payload);
  return unwrap<KanbanApiTask>(res);
};

export const createKanbanTask = async (
  payload: CreateKanbanTaskRequest
): Promise<KanbanApiTask> => {
  const res = await apiClient.post(PostLoginURL.kanbanTasks, payload);
  return unwrap<KanbanApiTask>(res);
};

export const persistKanbanOrder = async (
  payload: Array<{ columnId: string; taskIds: string[] }>
): Promise<void> => {
  await apiClient.post(PostLoginURL.kanbanOrder, { columns: payload });
};

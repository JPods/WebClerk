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
  const mapped = { ...payload };
  if ((mapped as any).dueDate) {
    (mapped as any).dt_due = (mapped as any).dueDate;
    delete (mapped as any).dueDate;
  }
  const res = await apiClient.patch(`${PostLoginURL.kanbanTasks}${taskId}/`, mapped);
  return unwrap<KanbanApiTask>(res);
};

export const createKanbanTask = async (
  payload: CreateKanbanTaskRequest
): Promise<KanbanApiTask> => {
  const mapped = { ...payload } as any;
  if (mapped.dueDate) {
    mapped.dt_due = mapped.dueDate;
    delete mapped.dueDate;
  }
  const res = await apiClient.post(PostLoginURL.kanbanTasks, mapped);
  return unwrap<KanbanApiTask>(res);
};

export const persistKanbanOrder = async (
  payload: Array<{ columnId: string; taskIds: string[] }>
): Promise<void> => {
  await apiClient.post(PostLoginURL.kanbanOrder, { columns: payload });
};

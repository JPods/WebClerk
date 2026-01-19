import type { TaskPriority } from "./type/kanban";

export type TranslationFormEntry = {
  id: string;
  language: string;
  title: string;
  description: string;
};

export type TaskFormState = {
  translations: TranslationFormEntry[];
  columnId: string;
  projectId?: string;
  priority: TaskPriority;
  dt_start: string;
  dt_due: string;
  dt_completed: string;
  assignee: string;
  difficulty: string;
  progress: string;
  percent_complete: string;
  is_active?: string;
};

export type TaskFormEditableField = Exclude<keyof TaskFormState, "translations">;

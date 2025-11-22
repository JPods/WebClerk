import type { TaskPriority } from "../../type/kanban";

export type TranslationFormEntry = {
  id: string;
  language: string;
  title: string;
  description: string;
};

export type TaskFormState = {
  translations: TranslationFormEntry[];
  columnId: string;
  priority: TaskPriority;
  dueDate: string;
  startDate: string;
  endDate: string;
  assignee: string;
  difficulty: string;
  progress: string;
};

export type TaskFormEditableField = Exclude<keyof TaskFormState, "translations">;

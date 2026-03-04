// Removed TaskPriority import; WC3 uses numeric priority
export type TaskPriority = number;

export type TranslationFormEntry = {
  id: string;
  language: string;
  title: string;
  description: string;
};

export type CoreModelFields = {
  id: number | null;
  uuid: string | null;
  ida: string;
  dt_created: number;
  dt_modified: number;
  version: number;
  is_active?: boolean;
};

export type BaseModelFields = CoreModelFields & {
  metadata?: Record<string, any>;
  refs?: Record<string, any>;
  prefs?: Record<string, any>;
  comments?: Record<string, any>;
  health_rating?: number;
};

export type ActionModelFields = {
  actions?: Record<string, any>;
};

export type TaskFormState = BaseModelFields &
  ActionModelFields & {
    translations: TranslationFormEntry[];
    columnId: string;
    assigned_to?: Array<{ id: string; name: string }>;
    projectId?: string;
    priority_value: TaskPriority;
    dt_start: string;
    dt_deadline: string;
    dt_completed: string;
    dt_expected: string;
    actor_id: string;
    difficulty_value: string;
    progress_value: string;
    status_code: string;
    is_active?: boolean;
    attachments?: TaskAttachment[];
  };

export type TaskFormEditableField = Exclude<keyof TaskFormState, "translations">;

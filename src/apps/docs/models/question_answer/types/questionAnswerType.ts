export interface QuestionAnswerAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateQuestionAnswerRequest {
  question: string;
  answer: string;
  category?: string;
  tags?: unknown;
}

export interface QuestionAnswerApiTask {
  id: number;
  uuid: string | null;
  question: string;
  answer: string;
  category?: string;
  tags?: unknown;
  metadata?: unknown;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
}

export interface UpdateQuestionAnswerRequest {
  id: number;
  question: string;
  answer: string;
  category?: string;
  tags?: unknown;
}
export interface DocumentAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateDocumentRequest {
  name: string;
  slug: string;
  content: string;
  summary: string;
  category: string;
  status: string;
  parent_id?: number | null;
  doc_type?: string;
  author_id?: number;
}

export interface DocumentApiTask {
  id: number;
  uuid: string | null;
  name: string;
  slug: string;
  content: string;
  summary: string;
  category: string;
  status: string;
  refs?: unknown;
  prefs?: unknown;
  metadata?: unknown;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  security_level?: number;
  is_deleted?: boolean;
  is_archived?: boolean;
  comments?: unknown;
  health_rating?: number;
  attachments?: unknown;
  history?: unknown;
  search_index?: unknown;
  search_vector?: unknown;
  path?: string;
  parent_id?: number | null;
  sort_order?: number;
  doc_type?: string;
  reading_time?: number;
  word_count?: number;
  char_count?: number;
  dt_last_viewed?: number;
  view_count?: number;
  edit_count?: number;
  author_id?: number;
  last_editor_id?: number;
}

export interface UpdateDocumentRequest {
  id: number;
  name: string;
  slug: string;
  content: string;
  summary: string;
  category: string;
  status: string;
  parent_id?: number | null;
  doc_type?: string;
  author_id?: number;
}
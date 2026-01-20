// TypeScript interface for Document model
export interface Document {
  id: number;
  name?: string;
  slug?: string;
  status?: string;
  description?: string;
  body?: string;
  comment?: string;
  data?: any;
  confidential?: string;
  copyright?: any;
  count_accessed?: number;
  model_name?: string;
  // Add other fields as needed for strict alignment
}

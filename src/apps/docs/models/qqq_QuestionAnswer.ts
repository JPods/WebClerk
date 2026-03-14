/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
// TypeScript interface for QuestionAnswer model
export interface QuestionAnswer {
  id: number;
  question?: string;
  answer?: string;
  setting_id?: number;
  contact_id?: number;
  answered_by_name?: string;
  status?: string;
  sequence?: number;
  count_accessed?: number;
  // Add other fields as needed for strict alignment
}

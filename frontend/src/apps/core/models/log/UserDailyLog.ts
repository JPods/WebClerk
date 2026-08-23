/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * UserDailyLog — TypeScript interface aligned with wc3 model.
 *
 * One record per user per calendar day. Aggregated nightly from APILog.
 */

export interface CallCounts {
  total: number;
  by_method: Record<string, number>;
  by_endpoint: Record<string, number>;
  by_model: Record<string, number>;
  by_source: Record<string, number>;
}

export interface ResponseSummary {
  success_count: number;
  error_count: number;
  error_rate: number;
  avg_duration_ms: number;
  max_duration_ms: number;
  status_codes: Record<string, number>;
  slowest_endpoints: { endpoint: string; duration_ms: number; model?: string }[];
}

export interface DailyHint {
  level: "info" | "warning" | "error";
  category: string;
  message: string;
  count: number;
}

export interface ErrorDetail {
  endpoint: string;
  status_code: number;
  count: number;
  error_message: string;
  first_at: number;
  last_at: number;
  model?: string;
}

export interface UserDailyLog {
  id: number;
  uuid?: string;
  ida?: string;
  dt_created?: number;
  dt_modified?: number;
  version?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  is_archived?: boolean;

  user_id: number;
  log_date: string; // "YYYY-MM-DD"

  call_counts: CallCounts;
  response_summary: ResponseSummary;
  hints: DailyHint[];
  error_details: ErrorDetail[];

  total_calls: number;
  total_errors: number;
  avg_duration_ms: number;

  metadata?: Record<string, any>;
  refs?: Record<string, any>;
}

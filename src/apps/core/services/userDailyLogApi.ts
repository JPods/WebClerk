/**
 * userDailyLogApi.ts — Service for fetching UserDailyLog records.
 *
 * Uses the wcapi SDK (/wcapi/get/) since the model auto-discovers
 * through the registry like any other BaseModel.
 */
import { getRecords } from "@/api/wcapi";
import type { UserDailyLog } from "../models/log/UserDailyLog";

const MODEL = "userdailylog";

/**
 * Fetch daily logs for a specific user, optionally filtered by date range.
 */
export async function fetchUserDailyLogs(params?: {
  user_id?: number;
  log_date?: string;
  log_date__gte?: string;
  log_date__lte?: string;
  ordering?: string;
  limit?: number;
  offset?: number;
}): Promise<{ results: UserDailyLog[]; total: number }> {
  const resp = await getRecords(MODEL, {
    ...params,
    ordering: params?.ordering ?? "-log_date",
    limit: params?.limit ?? 30,
  });
  return {
    results: (resp?.results ?? []) as UserDailyLog[],
    total: resp?.total ?? 0,
  };
}

/**
 * Fetch last N days of logs for the current user.
 */
export async function fetchRecentDailyLogs(
  userId: number,
  days = 14,
): Promise<UserDailyLog[]> {
  const since = new Date();
  since.setDate(since.getDate() - days);
  const dateStr = since.toISOString().split("T")[0];

  const resp = await fetchUserDailyLogs({
    user_id: userId,
    log_date__gte: dateStr,
    ordering: "-log_date",
    limit: days,
  });
  return resp.results;
}

/**
 * Fetch all users' logs for a specific date (admin overview).
 */
export async function fetchDailyLogsByDate(
  date: string,
): Promise<UserDailyLog[]> {
  const resp = await fetchUserDailyLogs({
    log_date: date,
    ordering: "-total_calls",
    limit: 100,
  });
  return resp.results;
}

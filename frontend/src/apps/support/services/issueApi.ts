/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * issueApi.ts — Service for creating issue Action records.
 *
 * Both the user help-desk reporter and the developer bug reporter
 * call saveRecord('action', ...) under the hood, so every issue
 * lands in the existing Action list / Kanban board.
 *
 * Two project buckets keep them separate:
 *   project_name: "User Support"   → end-user feedback / issues
 *   project_name: "Dev Issues"     → developer bug reports
 */
import { saveRecord, getRecords } from "@/api/wcapi";

/* ------------------------------------------------------------------ */
/*  Shared types                                                       */
/* ------------------------------------------------------------------ */

export type IssuePriority = 1 | 2 | 3 | 4; // Low, Medium, High, Critical

export type IssueCategory =
  | "bug"
  | "feature_request"
  | "question"
  | "performance"
  | "ui_ux"
  | "data"
  | "other";

export const ISSUE_CATEGORIES: { value: IssueCategory; label: string }[] = [
  { value: "bug", label: "Bug / Error" },
  { value: "feature_request", label: "Feature Request" },
  { value: "question", label: "Question" },
  { value: "performance", label: "Performance" },
  { value: "ui_ux", label: "UI / UX" },
  { value: "data", label: "Data Issue" },
  { value: "other", label: "Other" },
];

export const PRIORITY_OPTIONS: { value: IssuePriority; label: string; color: string }[] = [
  { value: 1, label: "Low", color: "text-green-600" },
  { value: 2, label: "Medium", color: "text-yellow-600" },
  { value: 3, label: "High", color: "text-orange-600" },
  { value: 4, label: "Critical", color: "text-red-600" },
];

/* ------------------------------------------------------------------ */
/*  User Issue (simple help-desk report)                               */
/* ------------------------------------------------------------------ */

export interface UserIssuePayload {
  title: string;
  description: string;
  category: IssueCategory;
  priority?: IssuePriority;
  /** Auto-captured context */
  pageUrl?: string;
  userAgent?: string;
  screenSize?: string;
  /** Optional file attachment as base64 data URL */
  screenshot?: string;
}

export async function submitUserIssue(payload: UserIssuePayload) {
  const now = Date.now();

  const actionPayload: Record<string, unknown> = {
    action: { en: payload.title },
    description: { en: payload.description },
    project_name: "User Support",
    kanban_column: "Backlog",
    priority: payload.priority ?? 2,
    status: "Open",
    dt_start: now,
    refs: {
      tags: [payload.category],
      keywords: ["user-issue", payload.category],
    },
    metadata: {
      issue_type: "user",
      category: payload.category,
      context: {
        page_url: payload.pageUrl ?? window.location.href,
        user_agent: payload.userAgent ?? navigator.userAgent,
        screen_size: payload.screenSize ?? `${window.innerWidth}x${window.innerHeight}`,
        submitted_at: new Date().toISOString(),
      },
      ...(payload.screenshot ? { screenshot: payload.screenshot } : {}),
    },
  };

  return saveRecord("action", actionPayload);
}

/* ------------------------------------------------------------------ */
/*  Developer Issue (rich bug report)                                  */
/* ------------------------------------------------------------------ */

export type DevSeverity = "cosmetic" | "minor" | "major" | "blocker";

export const SEVERITY_OPTIONS: { value: DevSeverity; label: string; color: string }[] = [
  { value: "cosmetic", label: "Cosmetic", color: "text-slate-500" },
  { value: "minor", label: "Minor", color: "text-yellow-600" },
  { value: "major", label: "Major", color: "text-orange-600" },
  { value: "blocker", label: "Blocker", color: "text-red-600" },
];

export interface DevIssuePayload {
  title: string;
  description: string;
  severity: DevSeverity;
  category: IssueCategory;
  component?: string;         // e.g. "OrderDetail", "InvoiceSave"
  stepsToReproduce?: string;
  expectedBehavior?: string;
  actualBehavior?: string;
  /** Auto-captured */
  consoleErrors?: string[];
  pageUrl?: string;
  environment?: Record<string, string>;
}

const SEVERITY_TO_PRIORITY: Record<DevSeverity, IssuePriority> = {
  cosmetic: 1,
  minor: 2,
  major: 3,
  blocker: 4,
};

export async function submitDevIssue(payload: DevIssuePayload) {
  const now = Date.now();

  const actionPayload: Record<string, unknown> = {
    action: { en: payload.title },
    description: {
      en: [
        payload.description,
        payload.stepsToReproduce ? `\n**Steps to Reproduce:**\n${payload.stepsToReproduce}` : "",
        payload.expectedBehavior ? `\n**Expected:** ${payload.expectedBehavior}` : "",
        payload.actualBehavior ? `\n**Actual:** ${payload.actualBehavior}` : "",
      ]
        .filter(Boolean)
        .join("\n"),
    },
    project_name: "Dev Issues",
    kanban_column: "Backlog",
    priority: SEVERITY_TO_PRIORITY[payload.severity],
    status: "Open",
    dt_start: now,
    refs: {
      tags: [payload.category, payload.severity, ...(payload.component ? [payload.component] : [])],
      keywords: ["dev-issue", payload.category, payload.severity],
    },
    metadata: {
      issue_type: "developer",
      category: payload.category,
      severity: payload.severity,
      component: payload.component ?? "",
      context: {
        page_url: payload.pageUrl ?? window.location.href,
        environment: payload.environment ?? {
          app: "WebClerk",
          node_env: import.meta.env.MODE,
          vite_api: import.meta.env.VITE_API_URL ?? "localhost:8000",
        },
        console_errors: payload.consoleErrors ?? [],
        submitted_at: new Date().toISOString(),
      },
    },
  };

  return saveRecord("action", actionPayload);
}

/* ------------------------------------------------------------------ */
/*  Fetch issues (for admin dashboards)                                */
/* ------------------------------------------------------------------ */

export async function fetchUserIssues() {
  return getRecords("action", { project_name: "User Support" });
}

export async function fetchDevIssues() {
  return getRecords("action", { project_name: "Dev Issues" });
}

export async function fetchAllIssues() {
  return getRecords("action", {
    project_name__in: "User Support,Dev Issues",
  });
}

/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * issueApi.ts — the issue categories and priorities the IssueReporter offers.
 * The issue itself is an Action (IssueReporter creates it with createRecord).
 */

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

import type { TaskPriority } from "../../../type/kanban";
import type { TranslationFormEntry, TaskFormState } from "../kanban/taskFormTypes";

export const DEFAULT_LANGUAGE_ORDER = ["en", "ar", "bn", "es"] as const;
export const DIFFICULTY_OPTIONS = [1, 2, 3, 5, 8, 13, 21, 34, 55, 101] as const;
export const PROGRESS_OPTIONS = [0, 5, 30, 50, 70, 90, 100] as const;

export const DEFAULT_DIFFICULTY = DIFFICULTY_OPTIONS[2];
export const DEFAULT_PROGRESS = PROGRESS_OPTIONS[0];
export const FALLBACK_COLUMN_ID = "column-uncategorized";

export const priorityOptions: TaskPriority[] = [
  "low",
  "medium",
  "high",
  "critical",
];

export const PRIORITY_TO_VALUE: Record<TaskPriority, number> = {
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
};

export const getLanguageLabel = (code: string): string => {
  const labels: Record<string, string> = {
    en: "English",
    ar: "Arabic",
    bn: "Bengali",
    es: "Spanish",
  };
  return labels[code.toLowerCase()] ?? code;
};

export const normalizeLanguageCode = (code: string): string => code.trim().toLowerCase();

export const extendNumericOptionStrings = (
  options: readonly number[],
  current: string
): string[] => {
  const base = options.map(String);
  return current && !base.includes(current) ? [...base, current] : base;
};

export const toTimestampMilliseconds = (value: string): number | null => {
  const d = new Date(value);
  return isNaN(d.getTime()) ? null : d.getTime();
};

export const normalizeNumericSelectValue = (
  value: unknown,
  fallback: number
): string => {
  if (value === null || value === undefined) return String(fallback);
  const n = Number(value);
  return isNaN(n) ? String(fallback) : String(n);
};

export const calculateDueDate = (start: string, end: string): string => {
  const endDate = new Date(end);
  if (!isNaN(endDate.getTime())) return endDate.toISOString().slice(0, 16);
  const startDate = new Date(start);
  if (!isNaN(startDate.getTime())) {
    const d = new Date(startDate);
    d.setDate(d.getDate() + 1);
    return d.toISOString().slice(0, 16);
  }
  return "";
};

export const createTranslationEntry = (
  language: string,
  title = "",
  description = ""
): TranslationFormEntry => ({
  id: crypto.randomUUID(),
  language,
  title,
  description,
});

export const createTranslationEntriesFromTask = (task: any): TranslationFormEntry[] => {
  const codes = new Set<string>();
  task.languageCodes?.forEach((c: string) => codes.add(normalizeLanguageCode(c)));
  if (codes.size === 0) codes.add("en");
  return [...codes].map((code) =>
    createTranslationEntry(code, task.title || "", task.description || "")
  );
};

export const createInitialTaskFormState = (
  columnId: string
): TaskFormState => ({
  translations: [createTranslationEntry("en")],
  columnId,
  priority: "medium",
  dueDate: "",
  startDate: "",
  endDate: "",
  assignee: "",
  difficulty: String(DEFAULT_DIFFICULTY),
  progress: String(DEFAULT_PROGRESS),
  percent_complete: "0",
});

export const findNextLanguageCode = (
  used: Set<string>,
  options: Array<{ value: string }>
): string => {
  for (const code of DEFAULT_LANGUAGE_ORDER) {
    if (!used.has(code)) return code;
  }
  for (const opt of options) {
    if (!used.has(opt.value)) return opt.value;
  }
  return "";
};

export const normalizeIncomingDateValue = (value: unknown): string => {
  const d = new Date(String(value));
  return isNaN(d.getTime()) ? "" : d.toISOString().slice(0, 16);
};

export const updateTaskFormState = (
  prev: TaskFormState,
  field: keyof TaskFormState,
  value: string
): TaskFormState => ({ ...prev, [field]: value });

/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * ActionsModal - Task/Action modal for transaction contexts
 *
 * Replicates KanbanTaskModal design exactly:
 * - Translation entries (title/description per language)
 * - Priority slider (1-4: low, medium, high, critical)
 * - Difficulty slider (10-100)
 * - Progress slider (0-100)
 * - Status button group
 * - Datetime pickers (dt_start, dt_deadline, dt_completed)
 * - Assignee dropdown with chips
 * - Project selector
 * - Language picker
 * - is_active toggle
 */
import React, { FormEvent, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { FaSpinner } from "react-icons/fa";
import { SearchableSelect } from "@/components/ui/dropdown/SearchableSelect";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

// ------------------------------------
// Types
// ------------------------------------

export type TaskPriority = "low" | "medium" | "high" | "critical";

export interface TranslationFormEntry {
  id: string;
  language: string;
  title: string;
  description: string;
}

export interface AssigneeOption {
  id: string;
  label: string;
}

export interface ProjectOption {
  id: string;
  name?: string;
  intent?: string;
}

export interface ActionFormState {
  translations: TranslationFormEntry[];
  columnId: string;
  projectId: string;
  priority: TaskPriority;
  dt_deadline: string;
  dt_start: string;
  dt_completed: string;
  dt_expected: string;
  assigned_to: Array<{ id: string; name: string }>;
  difficulty: string;
  progress: string;
  percent_complete: string;
  is_active: string;
}

export type ActionFormEditableField = Exclude<
  keyof ActionFormState,
  "translations"
>;

interface LanguageOption {
  value: string;
  label: string;
}

interface LanguagePickerState {
  isOpen: boolean;
  selection: string;
  customValue: string;
  error: string | null;
}

export interface ActionsModalProps {
  mode: "create" | "edit";
  isOpen: boolean;
  title?: string;
  description?: string;
  isSaving?: boolean;
  submitLabel?: string;
  onClose: () => void;
  onSubmit?: (event: FormEvent<HTMLFormElement>) => void;
  /** Called with form data when Save/Create is clicked - use this to save the action */
  onSave?: (formData: ActionFormState) => void | Promise<void>;
  modalError?: string | null;
  formState?: ActionFormState;
  onFieldChange?: (field: ActionFormEditableField, value: unknown) => void;
  columnOptions?: Array<{ id: string; title: string }>;
  projectOptions?: ProjectOption[];
  priorityOptions?: TaskPriority[];
  difficultyOptions?: string[];
  progressOptions?: string[];
  assigneeOptions?: AssigneeOption[];
  translations?: TranslationFormEntry[];
  onTranslationFieldChange?: (
    entryId: string,
    field: keyof TranslationFormEntry,
    value: string,
  ) => void;
  onRemoveTranslation?: (entryId: string) => void;
  languagePickerOptions?: LanguageOption[];
  languagePickerState?: LanguagePickerState;
  onLanguagePickerToggle?: () => void;
  onLanguageSelectionChange?: (value: string) => void;
  onLanguageCustomChange?: (value: string) => void;
  onLanguagePickerSubmit?: () => void;
  onLanguagePickerCancel?: () => void;
  extraContent?: React.ReactNode;
  onRemoveFromKanban?: () => void;
  isRemoving?: boolean;
}

// ------------------------------------
// Helper Functions
// ------------------------------------

const createLocalId = (): string => {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID();
  }
  return `local-${Date.now().toString(36)}-${Math.random()
    .toString(36)
    .slice(2, 8)}`;
};

const DEFAULT_LANGUAGE_ORDER = ["en", "ar", "bn", "es"];

export const createDefaultTranslationEntry = (
  language: string,
  title = "",
  description = "",
): TranslationFormEntry => ({
  id: createLocalId(),
  language,
  title,
  description,
});

export const createInitialActionFormState = (
  columnId = "",
): ActionFormState => ({
  translations: [createDefaultTranslationEntry(DEFAULT_LANGUAGE_ORDER[0])],
  columnId,
  projectId: "",
  priority: "medium",
  dt_deadline: "",
  dt_start: "",
  dt_completed: "",
  dt_expected: "",
  assigned_to: [],
  difficulty: "30",
  progress: "0",
  percent_complete: "0",
  is_active: "true",
});

// ------------------------------------
// Main Component
// ------------------------------------

const ActionsModal: React.FC<ActionsModalProps> = ({
  mode,
  isOpen,
  title = mode === "edit" ? "Edit Action" : "Create Action",
  description = "",
  isSaving = false,
  submitLabel = mode === "edit" ? "Save" : "Create",
  onClose,
  onSubmit,
  onSave,
  modalError,
  formState: formStateProp,
  onFieldChange: onFieldChangeProp,
  assigneeOptions = [],
  projectOptions = [],
  translations: translationsProp,
  onTranslationFieldChange: onTranslationFieldChangeProp,
  onRemoveTranslation: onRemoveTranslationProp,
  languagePickerOptions = [],
  languagePickerState = {
    isOpen: false,
    selection: "",
    customValue: "",
    error: null,
  },
  onLanguagePickerToggle = () => {},
  onLanguageSelectionChange = () => {},
  onLanguageCustomChange = () => {},
  onLanguagePickerSubmit = () => {},
  onLanguagePickerCancel = () => {},
  onRemoveFromKanban: _onRemoveFromKanban,
  isRemoving: _isRemoving = false,
}) => {
  // Internal state for when parent doesn't provide controlled state
  const [internalFormState, setInternalFormState] = useState<ActionFormState>(
    () => formStateProp ?? createInitialActionFormState(),
  );

  // Internal saving state for when parent doesn't provide isSaving prop
  const [internalSaving, setInternalSaving] = useState(false);
  const isCurrentlySaving = isSaving || internalSaving;

  // Track if we've initialized from formStateProp for this modal open
  const [hasInitialized, setHasInitialized] = useState(false);

  // Sync internal state with provided formState ONLY when modal opens
  useEffect(() => {
    if (isOpen && formStateProp && !hasInitialized) {
      setInternalFormState(formStateProp);
      setHasInitialized(true);
    }
  }, [isOpen, formStateProp, hasInitialized]);

  // Reset when modal closes
  useEffect(() => {
    if (!isOpen) {
      setHasInitialized(false);
      if (!formStateProp) {
        setInternalFormState(createInitialActionFormState());
      }
    }
  }, [isOpen, formStateProp]);

  // Use internal state (which may be synced from formStateProp)
  const formState = internalFormState;
  const translations = translationsProp ?? formState.translations;

  // Field change handler always updates internal state
  const onFieldChange =
    onFieldChangeProp ??
    ((field: ActionFormEditableField, value: unknown) => {
      setInternalFormState((prev) => ({ ...prev, [field]: value }));
    });

  // Default translation field change handler
  const onTranslationFieldChange =
    onTranslationFieldChangeProp ??
    ((entryId: string, field: keyof TranslationFormEntry, value: string) => {
      setInternalFormState((prev) => ({
        ...prev,
        translations: prev.translations.map((t) =>
          t.id === entryId ? { ...t, [field]: value } : t,
        ),
      }));
    });

  // Default remove translation handler
  const onRemoveTranslation =
    onRemoveTranslationProp ??
    ((entryId: string) => {
      setInternalFormState((prev) => ({
        ...prev,
        translations: prev.translations.filter((t) => t.id !== entryId),
      }));
    });

  const [assigneeSelection, setAssigneeSelection] = useState<string>("");

  useEffect(() => {
    setAssigneeSelection("");
  }, [isOpen]);

  const statusOptions = useMemo(
    () => [
      { value: "0", label: "Backlog" },
      { value: "5", label: "On hold" },
      { value: "30", label: "In progress" },
      { value: "review", label: "Review" },
      { value: "100", label: "Completed" },
    ],
    [],
  );

  const statusToProgress: Record<string, number> = useMemo(
    () => ({
      "0": 0,
      "5": 5,
      "30": 20,
      review: 70,
      "100": 100,
    }),
    [],
  );

  const difficultyStops = useMemo(
    () => [10, 20, 30, 40, 50, 60, 70, 75, 80, 85, 90, 95, 100],
    [],
  );

  const visibleTranslations = translations.filter((entry, index) => {
    if (index === 0) return true;
    const hasContent = Boolean(
      entry.title?.trim() || entry.description?.trim(),
    );
    return hasContent;
  });

  const [activeTranslationId, setActiveTranslationId] = useState<string>(
    () => visibleTranslations[0]?.id ?? "",
  );

  useEffect(() => {
    if (!visibleTranslations.length) {
      setActiveTranslationId("");
      return;
    }
    const exists = visibleTranslations.some(
      (entry) => entry.id === activeTranslationId,
    );
    if (!exists) {
      setActiveTranslationId(visibleTranslations[0].id);
    }
  }, [activeTranslationId, visibleTranslations]);

  const activeTranslation = useMemo(() => {
    if (!activeTranslationId) return visibleTranslations[0];
    return (
      visibleTranslations.find((entry) => entry.id === activeTranslationId) ??
      visibleTranslations[0]
    );
  }, [activeTranslationId, visibleTranslations]);

  const progressValue = useMemo(() => {
    const statusProgress = statusToProgress[formState.percent_complete];
    if (statusProgress !== undefined) {
      return statusProgress;
    }
    return Math.max(0, Math.min(100, Number(formState.progress) || 0));
  }, [formState.percent_complete, formState.progress, statusToProgress]);

  // Early return AFTER all hooks
  if (!isOpen) return null;

  const priorityToNumeric: Record<TaskPriority, number> = {
    low: 1,
    medium: 2,
    high: 3,
    critical: 4,
  };

  const numericToPriority: Record<number, TaskPriority> = {
    1: "low",
    2: "medium",
    3: "high",
    4: "critical",
  };

  const currentPriorityNumeric = priorityToNumeric[formState.priority] ?? 2;
  const snapToDifficultyStop = (value: number) => {
    const bounded = Math.max(10, Math.min(100, value));
    let closest = difficultyStops[0];
    let smallestDiff = Math.abs(bounded - closest);
    for (const stop of difficultyStops) {
      const diff = Math.abs(bounded - stop);
      if (diff < smallestDiff) {
        smallestDiff = diff;
        closest = stop;
      }
    }
    return closest;
  };

  const difficultyValue = snapToDifficultyStop(
    Number(formState.difficulty) || 10,
  );

  const formId = `actions-modal-form-${mode}`;
  const canRemoveTranslation = translations.length > 1;

  const controlBaseClass =
    "w-full h-10 rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white";
  const controlClass = `mt-1 ${controlBaseClass}`;
  const textareaClass = `${controlBaseClass} mt-1 h-5 min-h-[1.5rem] resize-y`;

  const modal = (
    <div className="pointer-events-none fixed inset-0 z-[200000] flex items-stretch justify-end">
      <div className="pointer-events-auto ml-auto flex h-full w-full max-h-screen flex-col overflow-hidden border-l border-gray-200 bg-white shadow-2xl no-scrollbar dark:border-gray-800 dark:bg-gray-900 sm:w-[480px] lg:w-[33vw] lg:min-w-[360px]">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-gray-200 px-5 py-4 dark:border-gray-800">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {title}
            </h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {description}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800"
            aria-label="Close modal"
            disabled={isCurrentlySaving}
          >
            <svg
              className="h-5 w-5"
              viewBox="0 0 20 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M6 6l8 8M14 6l-8 8"
                stroke="currentColor"
                strokeWidth={1.6}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form
          id={formId}
          className="flex-1 space-y-3 overflow-y-auto px-5 py-4 no-scrollbar"
          onSubmit={async (e) => {
            e.preventDefault();
            // Call onSubmit if provided (for custom handling)
            onSubmit?.(e);
            // Call onSave with form data and track saving state
            if (onSave) {
              setInternalSaving(true);
              try {
                await onSave(formState);
              } finally {
                setInternalSaving(false);
              }
            }
          }}
        >
          {modalError && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/40 dark:text-rose-200">
              {modalError}
            </div>
          )}

          {/* Translation Entry */}
          {activeTranslation && (
            <div className="space-y-2">
              <div>
                <label className="text-xs font-medium tracking-wide text-gray-500 dark:text-gray-400">
                  action
                </label>
                <input
                  className={controlClass}
                  value={activeTranslation.title}
                  onChange={(event) =>
                    onTranslationFieldChange(
                      activeTranslation.id,
                      "title",
                      event.target.value,
                    )
                  }
                  placeholder="Localized task title"
                  required
                  disabled={isCurrentlySaving}
                  data-testid={`${
                    mode === "create" ? "create" : "edit"
                  }-translation-title`}
                />
              </div>

              <div>
                <label className="text-xs font-medium tracking-wide text-gray-500 dark:text-gray-400">
                  description
                </label>
                <textarea
                  className={textareaClass}
                  rows={2}
                  value={activeTranslation.description}
                  onChange={(event) =>
                    onTranslationFieldChange(
                      activeTranslation.id,
                      "description",
                      event.target.value,
                    )
                  }
                  placeholder="Localized context, acceptance criteria, or notes"
                  disabled={isCurrentlySaving}
                />
              </div>

              {/* Assigned To Chips */}
              <div className="space-y-2">
                <div className="flex flex-wrap gap-2">
                  {(formState.assigned_to || []).map((a) => (
                    <span
                      key={a.id}
                      className="inline-flex items-center rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700 ring-1 ring-indigo-200 dark:bg-indigo-500/10 dark:text-indigo-100 dark:ring-indigo-500/40"
                    >
                      {a.name}
                      <button
                        type="button"
                        className="ml-2 text-indigo-500 hover:text-rose-500"
                        onClick={() => {
                          const next = (formState.assigned_to || []).filter(
                            (x) => x.id !== a.id,
                          );
                          onFieldChange("assigned_to", next);
                        }}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
                <SearchableSelect
                  options={assigneeOptions.map((opt) => ({
                    value: opt.id,
                    label: opt.label,
                  }))}
                  value={assigneeSelection || null}
                  onChange={(val) => {
                    if (!val) return;
                    const selectedId = String(val);
                    const option = assigneeOptions.find(
                      (opt) => opt.id === selectedId,
                    );
                    const label = option?.label ?? selectedId;
                    const existing = (formState.assigned_to || []).some(
                      (assignee) => assignee.id === selectedId,
                    );
                    if (!existing) {
                      onFieldChange("assigned_to", [
                        ...(formState.assigned_to || []),
                        { id: selectedId, name: label },
                      ]);
                    }
                    setAssigneeSelection("");
                  }}
                  placeholder="Select assignee..."
                  searchPlaceholder="Search assignees..."
                  disabled={isCurrentlySaving}
                  clearable={false}
                />
              </div>
            </div>
          )}

          {/* Priority & Difficulty Sliders */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-gray-300">
                <span>priority</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {formState.priority}
                </span>
              </div>
              <input
                type="range"
                min={1}
                max={4}
                step={1}
                value={currentPriorityNumeric}
                onChange={(e) => {
                  const next = Number(e.target.value) || currentPriorityNumeric;
                  const mapped = numericToPriority[next] ?? formState.priority;
                  onFieldChange("priority", mapped as TaskPriority);
                }}
                disabled={isCurrentlySaving}
                className="w-full accent-indigo-600"
              />
              <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                <span>Low</span>
                <span>Medium</span>
                <span>High</span>
                <span>Critical</span>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-gray-300">
                <span>difficulty</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {difficultyValue}
                </span>
              </div>
              <input
                type="range"
                min={10}
                max={100}
                step={5}
                value={difficultyValue}
                onChange={(e) => {
                  const next = snapToDifficultyStop(
                    Number(e.target.value) || difficultyValue,
                  );
                  onFieldChange("difficulty", String(next));
                }}
                disabled={isCurrentlySaving}
                className="w-full accent-indigo-600"
              />
              <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                <span>Easy</span>
                <span>Hard</span>
              </div>
            </div>
          </div>

          {/* Progress Slider */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              progress
            </label>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={progressValue}
              onChange={(e) =>
                onFieldChange(
                  "progress",
                  String(
                    Math.max(0, Math.min(100, Number(e.target.value) || 0)),
                  ),
                )
              }
              disabled={isCurrentlySaving}
              className="w-full accent-indigo-600"
            />
            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>0%</span>
              <span>50%</span>
              <span>100%</span>
            </div>
          </div>

          {/* Date Pickers & Project */}
          <div className="space-y-2">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-2">
              <div className="space-y-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    dt_start
                  </label>
                  <input
                    type="datetime-local"
                    step={60}
                    value={formState.dt_start}
                    onChange={(e) => onFieldChange("dt_start", e.target.value)}
                    disabled={isCurrentlySaving}
                    className={controlClass}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    dt_deadline
                  </label>
                  <input
                    type="datetime-local"
                    step={60}
                    value={formState.dt_deadline}
                    onChange={(e) =>
                      onFieldChange("dt_deadline", e.target.value)
                    }
                    disabled={isCurrentlySaving}
                    className={controlClass}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    dt_completed
                  </label>
                  <input
                    type="datetime-local"
                    step={60}
                    value={formState.dt_completed}
                    onChange={(e) =>
                      onFieldChange("dt_completed", e.target.value)
                    }
                    disabled={isCurrentlySaving}
                    className={controlClass}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Project
                  </label>
                  <select
                    className={controlClass}
                    value={formState.projectId ?? ""}
                    onChange={(event) =>
                      onFieldChange("projectId", event.target.value)
                    }
                    disabled={isCurrentlySaving}
                  >
                    <option value="">Select project...</option>
                    {projectOptions.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.name || option.intent || option.id}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* Status Button Group */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                status
              </label>
              <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
                {statusOptions.map((option) => {
                  const active = formState.percent_complete === option.value;
                  const base =
                    "flex-1 min-w-[96px] rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition sm:flex-none";
                  const activeClass =
                    "border-indigo-500 bg-indigo-600 text-white shadow";
                  const inactiveClass =
                    "border-gray-300 text-gray-700 hover:border-indigo-400 hover:text-indigo-600 dark:border-gray-700 dark:text-gray-200";
                  // Map status values to kanban column names
                  const statusToKanbanColumn: Record<string, string> = {
                    "0": "Backlog",
                    "5": "On Hold",
                    "30": "In Progress",
                    review: "Review",
                    "100": "Done",
                  };
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => {
                        onFieldChange("percent_complete", option.value);
                        // Sync progress with status
                        const mappedProgress = statusToProgress[option.value];
                        if (mappedProgress !== undefined) {
                          onFieldChange("progress", String(mappedProgress));
                        }
                        // Sync kanban_column with status
                        const kanbanColumn =
                          statusToKanbanColumn[option.value] || option.label;
                        onFieldChange("columnId", kanbanColumn);
                      }}
                      className={`${base} ${
                        active ? activeClass : inactiveClass
                      }`}
                      disabled={isCurrentlySaving}
                    >
                      {option.label}
                    </button>
                  );
                })}
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Selecting a status updates the kanban column automatically.
              </p>
            </div>

            {/* Language Picker */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Language
              </label>
              <div className="flex flex-wrap items-end gap-3">
                <div className="flex-1 min-w-[180px] space-y-1">
                  <select
                    className={controlClass}
                    value={activeTranslation?.id || ""}
                    onChange={(event) =>
                      setActiveTranslationId(event.target.value)
                    }
                    disabled={isSaving || visibleTranslations.length <= 1}
                  >
                    {visibleTranslations.map((entry, idx) => (
                      <option key={entry.id} value={entry.id}>
                        {entry.language || `Language ${idx + 1}`}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={onLanguagePickerToggle}
                    className="rounded-xl border border-dashed border-gray-300 px-3 py-2 text-sm font-semibold text-gray-600 transition hover:border-indigo-400 hover:text-indigo-500 disabled:cursor-not-allowed disabled:text-gray-400 dark:border-gray-700 dark:text-gray-300 dark:hover:border-indigo-500/40 dark:hover:text-indigo-300"
                    disabled={isCurrentlySaving}
                  >
                    {languagePickerState.isOpen
                      ? "Hide language"
                      : "Add language"}
                  </button>
                  {activeTranslation && (
                    <button
                      type="button"
                      onClick={() => onRemoveTranslation(activeTranslation.id)}
                      disabled={!canRemoveTranslation || isCurrentlySaving}
                      className="rounded-xl border border-rose-200 px-3 py-2 text-sm font-semibold text-rose-600 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:border-rose-100 disabled:text-rose-300 dark:border-rose-800 dark:text-rose-300 dark:hover:bg-rose-900/40"
                    >
                      Remove
                    </button>
                  )}
                </div>
              </div>

              {/* Language Picker Expanded */}
              {languagePickerState.isOpen && (
                <div className="col-span-1 sm:col-span-2 lg:col-span-2">
                  <div className="rounded-2xl border border-gray-200 bg-white/80 p-4 text-sm shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                      <div className="flex-1 space-y-1">
                        <label className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                          selection
                        </label>
                        <select
                          className={controlBaseClass}
                          value={languagePickerState.selection}
                          onChange={(event) =>
                            onLanguageSelectionChange(event.target.value)
                          }
                          disabled={isCurrentlySaving}
                        >
                          <option value="">Select a language…</option>
                          {languagePickerOptions.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                          <option value="__custom">Custom code…</option>
                        </select>
                      </div>

                      {languagePickerState.selection === "__custom" && (
                        <div className="flex-1 space-y-1">
                          <label className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            customValue
                          </label>
                          <input
                            className={controlBaseClass}
                            value={languagePickerState.customValue}
                            onChange={(event) =>
                              onLanguageCustomChange(event.target.value)
                            }
                            placeholder="e.g. fr"
                            disabled={isCurrentlySaving}
                          />
                        </div>
                      )}

                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={onLanguagePickerSubmit}
                          className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-indigo-400"
                          disabled={isCurrentlySaving}
                        >
                          Add
                        </button>
                        <button
                          type="button"
                          onClick={onLanguagePickerCancel}
                          className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                          disabled={isCurrentlySaving}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                    {languagePickerState.error && (
                      <p className="mt-2 text-xs font-semibold text-rose-600 dark:text-rose-300">
                        {languagePickerState.error}
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </form>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-gray-200 bg-white/95 px-5 py-3 backdrop-blur dark:border-gray-800">
          <div className="mr-auto flex items-center gap-3 rounded-xl border border-gray-200 px-3 py-2 text-sm dark:border-gray-800">
            <label className="inline-flex items-center gap-2 text-xs font-semibold text-gray-600 dark:text-gray-300">
              <span>
                {formState.is_active === "false" ? "Inactive" : "Active"}
              </span>
              <input
                type="checkbox"
                className="h-4 w-8 cursor-pointer accent-indigo-600"
                checked={formState.is_active !== "false"}
                onChange={(event) =>
                  onFieldChange(
                    "is_active",
                    event.target.checked ? "true" : "false",
                  )
                }
                disabled={isCurrentlySaving}
              />
            </label>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isCurrentlySaving}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:text-gray-400 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            Cancel
          </button>
          <button
            type="submit"
            form={formId}
            disabled={isCurrentlySaving}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-indigo-400"
          >
            {isCurrentlySaving && (
              <FaSpinner className="animate-spin w-4 h-4" />
            )}
            {submitLabel}
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modal, document.body);
};

export default withDevIdentifier(ActionsModal, 'ActionsModal', 'rose');
// Re-export types for consumers
export type { ActionsModalProps as ActionModalProps };

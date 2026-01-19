import { FormEvent, ReactNode } from "react";
import { createPortal } from "react-dom";
import type { KanbanTask } from "../kanban/type/kanban";
import type { TaskPriority } from "../kanban/type/kanban";
import type {
  TaskFormEditableField,
  TaskFormState,
  TranslationFormEntry,
} from "../kanban/taskFormTypes";

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

interface AssigneeOption {
  id: string;
  label: string;
}

interface KanbanTaskModalProps {
  mode: "create" | "edit";
  isOpen: boolean;
  title: string;
  description: string;
  isSaving: boolean;
  submitLabel: string;
  onClose: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  modalError?: string | null;
  formState: TaskFormState;
  onFieldChange: (field: TaskFormEditableField, value: string) => void;
  columnOptions: Array<{ id: string; title: string }>;
  priorityOptions: TaskPriority[];
  difficultyOptions: string[];
  progressOptions: string[];
  assigneeOptions?: AssigneeOption[];
  translations: TranslationFormEntry[];
  onTranslationFieldChange: (entryId: string, field: keyof TranslationFormEntry, value: string) => void;
  onRemoveTranslation: (entryId: string) => void;
  languageOptions: LanguageOption[];
  languagePickerOptions: LanguageOption[];
  languagePickerState: LanguagePickerState;
  onLanguagePickerToggle: () => void;
  onLanguageSelectionChange: (value: string) => void;
  onLanguageCustomChange: (value: string) => void;
  onLanguagePickerSubmit: () => void;
  onLanguagePickerCancel: () => void;
  extraContent?: ReactNode;
  currentTask?: KanbanTask | null;
}

export const KanbanActionEdit: React.FC<KanbanTaskModalProps> = ({
  mode,
  isOpen,
  title,
  description,
  isSaving,
  submitLabel,
  onClose,
  onSubmit,
  modalError,
  formState,
  onFieldChange,
  columnOptions,
  priorityOptions,
  difficultyOptions,
  progressOptions,
  assigneeOptions = [],
  translations,
  onTranslationFieldChange,
  onRemoveTranslation,
  languageOptions,
  languagePickerOptions,
  languagePickerState,
  onLanguagePickerToggle,
  onLanguageSelectionChange,
  onLanguageCustomChange,
  onLanguagePickerSubmit,
  onLanguagePickerCancel,
  extraContent,
  currentTask,
}) => {
  if (!isOpen) {
    return null;
  }

  const datalistId = `language-options-${mode}`;
  const canRemoveTranslation = translations.length > 1;

  const modal = (
    <div className="fixed inset-0 z-[200000] flex items-center justify-center bg-black/30 px-4 py-6 backdrop-blur-sm">
      <div className="w-full max-w-lg max-h-[calc(100vh-4rem)] overflow-y-auto rounded-3xl border border-gray-200 bg-white p-6 shadow-xl no-scrollbar dark:border-gray-800 dark:bg-gray-900">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{description}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800"
            aria-label="Close modal"
            disabled={isSaving}
          >
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M6 6l8 8M14 6l-8 8" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

        <form className="space-y-5" onSubmit={onSubmit}>
          {modalError && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/40 dark:text-rose-200">
              {modalError}
            </div>
          )}

          <datalist id={datalistId}>
            {languageOptions.map((option) => (
              <option key={option.value} value={option.value} label={option.label} />
            ))}
          </datalist>

          <div className="space-y-4">
            {/* Status */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">status</label>
              <select
                className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                value={formState.percent_complete}
                onChange={(e)=>onFieldChange("percent_complete", e.target.value)}
                disabled={isSaving}
              >
                <option value="0">Backlog</option>
                <option value="5">On hold</option>
                <option value="30">In progress</option>
                <option value="100">Completed</option>
                <option value="101">Canceled</option>
              </select>
            </div>
            {/* Priority */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">priority</label>
              <select
                className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                value={formState.priority}
                onChange={(e)=>onFieldChange("priority", e.target.value)}
                disabled={isSaving}
              >
                {priorityOptions.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            {/* Assignee */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Assignee</label>
              <input
                className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                value={formState.assignee}
                onChange={(e)=>onFieldChange("assignee", e.target.value)}
                disabled={isSaving}
              />
            </div>
            {/* Difficulty */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">difficulty</label>
              <select
                className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                value={formState.difficulty}
                onChange={(e)=>onFieldChange("difficulty", e.target.value)}
                disabled={isSaving}
              >
                {difficultyOptions.map(o=> <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
            {/* Progress */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">progress</label>
              <select
                className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                value={formState.progress}
                onChange={(e)=>onFieldChange("progress", e.target.value)}
                disabled={isSaving}
              >
                {progressOptions.map(o=> <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
            {/* Dates */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">dt_start</label>
                <input type="datetime-local" step={60} value={formState.dt_start} onChange={(e)=>onFieldChange("dt_start", e.target.value)} disabled={isSaving} className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">dt_end</label>
                <input type="datetime-local" step={60} value={formState.dt_expected} onChange={(e)=>onFieldChange("dt_expected", e.target.value)} disabled={isSaving} className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">dt_deadline</label>
                <input type="datetime-local" step={60} value={formState.dt_deadline} onChange={(e)=>onFieldChange("dt_deadline", e.target.value)} disabled={isSaving} className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">status</label>
              <select
                className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                value={formState.percent_complete}
                onChange={(e)=>onFieldChange("percent_complete", e.target.value)}
                disabled={isSaving}
              >
                <option value="0">Backlog</option>
                <option value="5">On hold</option>
                <option value="30">In progress</option>
                <option value="100">Completed</option>
                <option value="101">Canceled</option>
              </select>
            </div>
            {translations.map((translation, index) => {
              const canRemove = canRemoveTranslation;
              const modePrefix = mode === "create" ? "create" : "edit";

              return (
                <div
                  key={translation.id}
                  className="rounded-2xl border border-gray-200 bg-gray-50/80 p-4 shadow-sm dark:border-gray-800 dark:bg-gray-800/40"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-gray-900 dark:text-white">Language {index + 1}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {translation.language ? languageOptions.find((option) => option.value === translation.language)?.label ?? translation.language.toUpperCase() : "Set the language code"}
                      </p>
                    </div>
                    <div className="inline-flex items-center gap-2">
                      <span className="text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                        {translation.language || "—"}
                      </span>
                      <button
                        type="button"
                        onClick={() => onRemoveTranslation(translation.id)}
                        disabled={!canRemove || isSaving}
                        className="rounded-lg px-2 py-1 text-xs font-semibold text-rose-600 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:text-rose-300 dark:text-rose-300 dark:hover:bg-rose-900/40"
                      >
                        Remove
                      </button>
                    </div>
                  </div>

                  <div className="mt-4 space-y-3">
                    <div>
                      <label className="text-xs font-medium tracking-wide text-gray-500 dark:text-gray-400">
                        language
                      </label>
                      <input
                        className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-900/30 dark:text-white"
                        value={translation.language}
                        onChange={(event) => onTranslationFieldChange(translation.id, "language", event.target.value)}
                        placeholder="e.g. en"
                        list={datalistId}
                        disabled={isSaving}
                      />
                    </div>

                    <div>
                      <label className="text-xs font-medium tracking-wide text-gray-500 dark:text-gray-400">
                        action
                      </label>
                      <input
                        className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-900/30 dark:text-white"
                        value={translation.title}
                        onChange={(event) => onTranslationFieldChange(translation.id, "title", event.target.value)}
                        placeholder="Localized task title"
                        required={index === 0}
                        disabled={isSaving}
                        data-testid={`${modePrefix}-translation-title-${index}`}
                      />
                    </div>

                    <div>
                      <label className="text-xs font-medium tracking-wide text-gray-500 dark:text-gray-400">
                        description
                      </label>
                      <textarea
                        className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-900/30 dark:text-white"
                        rows={3}
                        value={translation.description}
                        onChange={(event) => onTranslationFieldChange(translation.id, "description", event.target.value)}
                        placeholder="Localized context, acceptance criteria, or notes"
                        disabled={isSaving}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="space-y-2">
            <button
              type="button"
              onClick={onLanguagePickerToggle}
              className="inline-flex items-center gap-2 rounded-xl border border-dashed border-gray-300 px-3 py-2 text-sm font-semibold text-gray-600 transition hover:border-indigo-400 hover:text-indigo-500 disabled:cursor-not-allowed disabled:text-gray-400 dark:border-gray-700 dark:text-gray-300 dark:hover:border-indigo-500/40 dark:hover:text-indigo-300"
              disabled={isSaving}
            >
              <svg className="h-4 w-4" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 4v12m6-6H4" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              {languagePickerState.isOpen ? "Hide language picker" : "Add language"}
            </button>

            {languagePickerState.isOpen && (
              <div className="rounded-2xl border border-gray-200 bg-white/80 p-4 text-sm shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                  <div className="flex-1 space-y-1">
                    <label className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                      selection
                    </label>
                    <select
                      className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-black dark:text-white"
                      value={languagePickerState.selection}
                      onChange={(event) => onLanguageSelectionChange(event.target.value)}
                      disabled={isSaving}
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
                        className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-900/30 dark:text-white"
                        value={languagePickerState.customValue}
                        onChange={(event) => onLanguageCustomChange(event.target.value)}
                        placeholder="e.g. fr"
                        disabled={isSaving}
                      />
                    </div>
                  )}

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={onLanguagePickerSubmit}
                      className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-indigo-400"
                      disabled={isSaving}
                    >
                      Add
                    </button>
                    <button
                      type="button"
                      onClick={onLanguagePickerCancel}
                      className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                      disabled={isSaving}
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
            )}
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">kanban_column</label>
              <select
                className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                value={formState.columnId}
                onChange={(event) => onFieldChange("columnId", event.target.value)}
                disabled={isSaving}
              >
                {columnOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.title}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">priority</label>
              <select
                className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                value={formState.priority}
                onChange={(event) => onFieldChange("priority", event.target.value)}
                disabled={isSaving}
              >
                {priorityOptions.map((priority) => (
                  <option key={priority} value={priority}>
                    {priority.charAt(0).toUpperCase() + priority.slice(1)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">difficulty</label>
              <select
                className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                value={formState.difficulty}
                onChange={(event) => onFieldChange("difficulty", event.target.value)}
                disabled={isSaving}
              >
                {difficultyOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">progress</label>
              <select
                className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                value={formState.progress}
                onChange={(event) => onFieldChange("progress", event.target.value)}
                disabled={isSaving}
              >
                {progressOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">dt_start</label>
              <input
                type="datetime-local"
                step={60}
                className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                 value={formState.dt_start}
                 onChange={(event) => onFieldChange("dt_start", event.target.value)}
                disabled={isSaving}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">dt_end</label>
              <input
                type="datetime-local"
                step={60}
                 min={formState.dt_start || undefined}
                className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                 value={formState.dt_expected}
                 onChange={(event) => onFieldChange("dt_expected", event.target.value)}
                disabled={isSaving}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">dt_deadline</label>
              <input
                type="datetime-local"
                step={60}
                 min={formState.dt_expected || formState.dt_start || undefined}
                className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                 value={formState.dt_deadline}
                 onChange={(event) => onFieldChange("dt_deadline", event.target.value)}
                disabled={isSaving}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Assignee</label>
              {assigneeOptions.length > 0 ? (
                <select
                  className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                  value={formState.assignee}
                  onChange={(event) => onFieldChange("assignee", event.target.value)}
                  disabled={isSaving}
                >
                  <option value="">Select assignee...</option>
                  {assigneeOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                  value={formState.assignee}
                  onChange={(event) => onFieldChange("assignee", event.target.value)}
                  placeholder="Select a project to see contacts"
                  disabled={isSaving}
                />
              )}
            </div>
          </div>

          {extraContent}

          {currentTask && mode === "edit" && (
            <div className="rounded-xl bg-gray-50 p-4 dark:bg-gray-800/50">
              <h4 className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">Current Task Status</h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Progress:</span>
                  <span className="ml-1 font-medium text-gray-900 dark:text-white">{currentTask.progress || 0}%</span>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Tags:</span>
                  <span className="ml-1 font-medium text-gray-900 dark:text-white">
                    {currentTask.tags?.join(", ") || "None"}
                  </span>
                </div>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:text-gray-400 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-indigo-400"
            >
              {submitLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  );

  return createPortal(modal, document.body);
};

export default KanbanActionEdit;

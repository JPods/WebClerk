import { FormEvent, ReactNode } from "react";
import { createPortal } from "react-dom";
import type { KanbanTask, TaskPriority } from "../../type/kanban";
import type { TaskFormEditableField, TaskFormState, TranslationFormEntry } from "./taskFormTypes";

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
  onRemoveFromKanban?: () => void;
  isRemoving?: boolean;
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
  onRemoveFromKanban,
  isRemoving = false,
}) => {
  if (!isOpen) return null;

  const datalistId = `language-options-${mode}`;
  const formId = `kanban-task-form-${mode}`;
  const canRemoveTranslation = translations.length > 1;

  const controlBaseClass =
    "w-full h-10 rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white";
  const controlClass = `mt-1 ${controlBaseClass}`;
  const textareaClass = `${controlBaseClass} mt-1 h-10 min-h-[2.5rem] resize-y`;

  const modal = (
    <div className="fixed inset-0 z-[200000] flex items-center justify-center bg-black/30 px-4 py-6 backdrop-blur-sm">
      <div className="w-full max-w-6xl max-h-[calc(100vh-3rem)] overflow-hidden rounded-3xl border border-gray-200 bg-white p-6 shadow-xl no-scrollbar dark:border-gray-800 dark:bg-gray-900 lg:p-8 flex flex-col">
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

        <form
          id={formId}
          className="grid flex-1 grid-cols-1 gap-6 overflow-y-auto pb-6"
          onSubmit={onSubmit}
        >
          {modalError && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/40 dark:text-rose-200 lg:col-span-2">
              {modalError}
            </div>
          )}

          <datalist id={datalistId}>
            {languageOptions.map((option) => (
              <option key={option.value} value={option.value} label={option.label} />
            ))}
          </datalist>

          {/* Translations & language picker */}
          <div className="space-y-3">
            <div
              className={
                translations.length > 1
                  ? "grid grid-cols-1 gap-4 md:grid-cols-2"
                  : "grid grid-cols-1 gap-4"
              }
            >
              {translations.map((translation, index) => {
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
                        {translation.language
                          ? languageOptions.find((option) => option.value === translation.language)?.label ?? translation.language.toUpperCase()
                          : "Set the language code"}
                      </p>
                    </div>
                    <div className="inline-flex items-center gap-2">
                      <span className="text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                        {translation.language || "—"}
                      </span>
                      <button
                        type="button"
                        onClick={() => onRemoveTranslation(translation.id)}
                        disabled={!canRemoveTranslation || isSaving}
                        className="rounded-lg px-2 py-1 text-xs font-semibold text-rose-600 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:text-rose-300 dark:text-rose-300 dark:hover:bg-rose-900/40"
                      >
                        Remove
                      </button>
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                    {/* <div>
                      <label className="text-xs font-medium tracking-wide text-gray-500 dark:text-gray-400">language</label>
                      <input
                        className={controlClass}
                        value={translation.language}
                        onChange={(event) => onTranslationFieldChange(translation.id, "language", event.target.value)}
                        placeholder="e.g. en"
                        list={datalistId}
                        disabled={isSaving}
                      />
                    </div> */}

                    <div className="sm:col-span-2">
                      <label className="text-xs font-medium tracking-wide text-gray-500 dark:text-gray-400">action</label>
                      <input
                        className={controlClass}
                        value={translation.title}
                        onChange={(event) => onTranslationFieldChange(translation.id, "title", event.target.value)}
                        placeholder="Localized task title"
                        required={index === 0}
                        disabled={isSaving}
                        data-testid={`${modePrefix}-translation-title-${index}`}
                      />
                    </div>

                    <div className="sm:col-span-2">
                      <label className="text-xs font-medium tracking-wide text-gray-500 dark:text-gray-400">description</label>
                      <textarea
                        className={textareaClass}
                        rows={1}
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
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">status</label>
                <select
                  className={controlClass}
                  value={formState.percent_complete}
                  onChange={(e) => onFieldChange("percent_complete", e.target.value)}
                  disabled={isSaving}
                >
                  <option value="0">Backlog</option>
                  <option value="5">On hold</option>
                  <option value="30">In progress</option>
                  <option value="100">Completed</option>
                  <option value="101">Canceled</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">progress</label>
                <select
                  className={controlClass}
                  value={formState.progress}
                  onChange={(e) => onFieldChange("progress", e.target.value)}
                  disabled={isSaving}
                >
                  {progressOptions.map((o) => (
                    <option key={o} value={o}>
                      {o}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">dt_start</label>
                <input
                  type="datetime-local"
                  step={60}
                  value={formState.startDate}
                  onChange={(e) => onFieldChange("startDate", e.target.value)}
                  disabled={isSaving}
                  className={controlClass}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">dt_end</label>
                <input
                  type="datetime-local"
                  step={60}
                  value={formState.endDate}
                  onChange={(e) => onFieldChange("endDate", e.target.value)}
                  disabled={isSaving}
                  className={controlClass}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">dt_due</label>
                <input
                  type="datetime-local"
                  step={60}
                  value={formState.dueDate}
                  onChange={(e) => onFieldChange("dueDate", e.target.value)}
                  disabled={isSaving}
                  className={controlClass}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">kanban_column</label>
                <select
                  className={controlClass}
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
                  className={controlClass}
                  value={formState.priority}
                  onChange={(e) => onFieldChange("priority", e.target.value)}
                  disabled={isSaving}
                >
                  {priorityOptions.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">difficulty</label>
                <select
                  className={controlClass}
                  value={formState.difficulty}
                  onChange={(e) => onFieldChange("difficulty", e.target.value)}
                  disabled={isSaving}
                >
                  {difficultyOptions.map((o) => (
                    <option key={o} value={o}>
                      {o}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Assign</label>

                {assigneeOptions.length > 0 ? (
                  <select
                    className={controlClass}
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
                    className={controlClass}
                    value={formState.assignee}
                    onChange={(event) => onFieldChange("assignee", event.target.value)}
                    placeholder="Select a project to see contacts"
                    disabled={isSaving}
                  />
                )}

              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Add language</label>
                <button
                  type="button"
                  onClick={onLanguagePickerToggle}
                  className={`${controlClass} flex items-center justify-center gap-2 border-dashed text-gray-600 font-semibold hover:border-indigo-400 hover:text-indigo-500 disabled:cursor-not-allowed disabled:text-gray-400 dark:text-gray-300 dark:hover:border-indigo-500/40 dark:hover:text-indigo-300`}
                  disabled={isSaving}
                >
                  {languagePickerState.isOpen ? "Hide language picker" : "Add language"}
                </button>
              </div>

              {languagePickerState.isOpen && (
                <div className="col-span-1 sm:col-span-2 lg:col-span-4">
                  <div className="rounded-2xl border border-gray-200 bg-white/80 p-4 text-sm shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                      <div className="flex-1 space-y-1">
                        <label className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">selection</label>
                        <select
                          className={controlBaseClass}
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
                          <label className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">customValue</label>
                          <input
                            className={controlBaseClass}
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
                      <p className="mt-2 text-xs font-semibold text-rose-600 dark:text-rose-300">{languagePickerState.error}</p>
                    )}
                  </div>
                </div>
              )}
              
            </div>

          </div>

          {/* Core fields */}
          <div className="space-y-6">
            

            {/* {extraContent && <div>{extraContent}</div>} */}

            {/* {currentTask && mode === "edit" && (
              <div className="rounded-xl bg-gray-50 p-4 dark:bg-gray-800/50">
                <h4 className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">Current Task Status</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Progress:</span>
                    <span className="ml-1 font-medium text-gray-900 dark:text-white">{currentTask.progress || 0}%</span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Tags:</span>
                    <span className="ml-1 font-medium text-gray-900 dark:text-white">{currentTask.tags?.join(", ") || "None"}</span>
                  </div>
                </div>
              </div>
            )} */}
          </div>

        </form>

        <div className="mt-4 flex items-center justify-end gap-3 border-t border-gray-200 bg-white/95 py-3 backdrop-blur dark:border-gray-800 lg:mt-6">
          {mode === "edit" && onRemoveFromKanban && (
            <button
              type="button"
              onClick={onRemoveFromKanban}
              disabled={isSaving || isRemoving}
              className="mr-auto inline-flex items-center gap-2 rounded-lg border border-rose-200 px-3 py-2 text-sm font-semibold text-rose-700 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:border-rose-100 disabled:text-rose-300 dark:border-rose-800 dark:text-rose-200 dark:hover:bg-rose-900/40"
            >
              {isRemoving ? "Removing..." : "Remove from Kanban"}
            </button>
          )}
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
            form={formId}
            disabled={isSaving}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-indigo-400"
          >
            {submitLabel}
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modal, document.body);
};

export default KanbanActionEdit;

import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
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

type AssigneeUIMode = 'dropdown' | 'chips';

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
  projectOptions?: Array<{ id: string; name?: string; intent?: string }>;
  priorityOptions: TaskPriority[];
  difficultyOptions: string[];
  progressOptions: string[];
  assigneeOptions?: AssigneeOption[];
  assigneeUIMode?: AssigneeUIMode;
  onAssigneeUIModeChange?: (mode: AssigneeUIMode) => void;
  translations: TranslationFormEntry[];
  onTranslationFieldChange: (entryId: string, field: keyof TranslationFormEntry, value: string) => void;
  onRemoveTranslation: (entryId: string) => void;
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

export const KanbanTaskModal: React.FC<KanbanTaskModalProps> = ({
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
  assigneeOptions = [],
  projectOptions = [],
  translations,
  onTranslationFieldChange,
  onRemoveTranslation,
  languagePickerOptions,
  languagePickerState,
  onLanguagePickerToggle,
  onLanguageSelectionChange,
  onLanguageCustomChange,
  onLanguagePickerSubmit,
  onLanguagePickerCancel,
  onRemoveFromKanban: _onRemoveFromKanban,
  isRemoving: _isRemoving = false,
}) => {
  if (!isOpen) return null;

  const statusOptions = useMemo(
    () => [
      { value: "0", label: "Backlog" },
      { value: "5", label: "On hold" },
      { value: "30", label: "In progress" },
      { value: "review", label: "Review" },
      { value: "100", label: "Completed" },
      { value: "101", label: "Canceled" },
    ],
    []
  );

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
  const difficultyStops = useMemo(() => [10, 20, 30, 40, 50, 60, 70, 75, 80, 85, 90, 95, 100], []);
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

  const difficultyValue = snapToDifficultyStop(Number(formState.difficulty) || 10);
  const progressValue = Math.max(0, Math.min(100, Number(formState.progress) || 0));

  const visibleTranslations = translations.filter((entry, index) => {
    if (index === 0) return true;
    const hasContent = Boolean(entry.title?.trim() || entry.description?.trim());
    return hasContent;
  });

  const [activeTranslationId, setActiveTranslationId] = useState<string>(() => visibleTranslations[0]?.id ?? "");

  useEffect(() => {
    if (!visibleTranslations.length) {
      setActiveTranslationId("");
      return;
    }
    const exists = visibleTranslations.some((entry) => entry.id === activeTranslationId);
    if (!exists) {
      setActiveTranslationId(visibleTranslations[0].id);
    }
  }, [activeTranslationId, visibleTranslations]);

  const activeTranslation = useMemo(() => {
    if (!activeTranslationId) return visibleTranslations[0];
    return visibleTranslations.find((entry) => entry.id === activeTranslationId) ?? visibleTranslations[0];
  }, [activeTranslationId, visibleTranslations]);

  const formId = `kanban-task-form-${mode}`;
  const canRemoveTranslation = translations.length > 1;

  const controlBaseClass =
    "w-full h-10 rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white";
  const controlClass = `mt-1 ${controlBaseClass}`;
  const textareaClass = `${controlBaseClass} mt-1 h-10 min-h-[2.5rem] resize-y`;

  const modal = (
    <div className="pointer-events-none fixed inset-0 z-200000 flex items-stretch justify-end">
      <div className="pointer-events-auto ml-auto flex h-full w-full max-h-screen flex-col overflow-hidden border-l border-gray-200 bg-white shadow-2xl no-scrollbar dark:border-gray-800 dark:bg-gray-900 sm:w-[480px] lg:w-[33vw] lg:min-w-[360px]">
        <div className="flex items-start justify-between border-b border-gray-200 px-5 py-4 dark:border-gray-800">
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

        <form id={formId} className="flex-1 space-y-6 overflow-y-auto px-5 py-5 no-scrollbar" onSubmit={onSubmit}>
          {modalError && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/40 dark:text-rose-200">
              {modalError}
            </div>
          )}

          {activeTranslation && (
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium tracking-wide text-gray-500 dark:text-gray-400">action</label>
                <input
                  className={controlClass}
                  value={activeTranslation.title}
                  onChange={(event) => onTranslationFieldChange(activeTranslation.id, "title", event.target.value)}
                  placeholder="Localized task title"
                  required
                  disabled={isSaving}
                  data-testid={`${mode === "create" ? "create" : "edit"}-translation-title`}
                />
              </div>

              <div>
                <label className="text-xs font-medium tracking-wide text-gray-500 dark:text-gray-400">description</label>
                <textarea
                  className={textareaClass + " min-h-64 h-full"}
                  rows={6}
                  value={activeTranslation.description}
                  onChange={(event) => onTranslationFieldChange(activeTranslation.id, "description", event.target.value)}
                  placeholder="Localized context, acceptance criteria, or notes"
                  disabled={isSaving}
                />
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Assignees</label>
              {/* UI mode toggle for dev/testing */}
              <div className="mb-2 flex gap-2">
                <span className="text-xs text-gray-500">UI:</span>
                <button type="button" className={`px-2 py-1 rounded ${assigneeUIMode==='dropdown'?'bg-indigo-100':'bg-gray-100'}`} onClick={()=>onAssigneeUIModeChange?.('dropdown')}>Dropdown</button>
                <button type="button" className={`px-2 py-1 rounded ${assigneeUIMode==='chips'?'bg-indigo-100':'bg-gray-100'}`} onClick={()=>onAssigneeUIModeChange?.('chips')}>Chips</button>
              </div>
              {assigneeUIMode === 'dropdown' ? (
                <select
                  className={controlClass}
                  multiple
                  value={formState.assigned_to?.map((a:any)=>a.id)||[]}
                  onChange={e => {
                    const selected = Array.from(e.target.selectedOptions).map(opt => ({id: opt.value, name: opt.text}));
                    onFieldChange('assigned_to', selected);
                  }}
                  disabled={isSaving}
                  size={Math.min(assigneeOptions.length, 6)}
                >
                  {assigneeOptions.map(option => (
                    <option key={option.id} value={option.id}>{option.label}</option>
                  ))}
                </select>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {(formState.assigned_to||[]).map((a:any) => (
                    <span key={a.id} className="inline-flex items-center bg-indigo-100 text-indigo-800 rounded px-2 py-1 text-xs">
                      {a.name}
                      <button type="button" className="ml-1 text-xs text-red-500" onClick={()=>{
                        const next = (formState.assigned_to||[]).filter((x:any)=>x.id!==a.id);
                        onFieldChange('assigned_to', next);
                      }}>×</button>
                    </span>
                  ))}
                  <select
                    className={controlClass+" w-auto"}
                    value=""
                    onChange={e => {
                      const opt = assigneeOptions.find(o=>o.id===e.target.value);
                      if(opt){
                        const next = [...(formState.assigned_to||[]), {id: opt.id, name: opt.label}];
                        onFieldChange('assigned_to', next);
                      }
                    }}
                    disabled={isSaving}
                  >
                    <option value="">Add assignee…</option>
                    {assigneeOptions.filter(opt=>!(formState.assigned_to||[]).some((a:any)=>a.id===opt.id)).map(opt=>(
                      <option key={opt.id} value={opt.id}>{opt.label}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-gray-300">
                <span>difficulty</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">{difficultyValue}</span>
              </div>
              <input
                type="range"
                min={10}
                max={100}
                step={5}
                value={difficultyValue}
                onChange={(e) => {
                  const next = snapToDifficultyStop(Number(e.target.value) || difficultyValue);
                  onFieldChange("difficulty", String(next));
                }}
                disabled={isSaving}
                className="w-full accent-indigo-600"
              />
              <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                <span>Easy</span>
                <span>Hard</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-gray-300">
                <span>priority</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">{formState.priority}</span>
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
                disabled={isSaving}
                className="w-full accent-indigo-600"
              />
              <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                <span>Low</span>
                <span>Medium</span>
                <span>High</span>
                <span>Critical</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">progress</label>
              <div className="space-y-1">
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={5}
                  value={progressValue}
                  onChange={(e) => onFieldChange("progress", String(Math.max(0, Math.min(100, Number(e.target.value) || 0))))}
                  disabled={isSaving}
                  className="w-full accent-indigo-600"
                />
                <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span>0%</span>
                  <span>50%</span>
                  <span>100%</span>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-2">
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">dt_start</label>
                  <input
                    type="datetime-local"
                    step={60}
                    value={formState.dt_start}
                    onChange={(e) => onFieldChange("dt_start", e.target.value)}
                    disabled={isSaving}
                    className={controlClass}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">dt_deadline</label>
                  <input
                    type="datetime-local"
                    step={60}
                    value={formState.dt_deadline}
                    onChange={(e) => onFieldChange("dt_deadline", e.target.value)}
                    disabled={isSaving}
                    className={controlClass}
                  />
                </div>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">dt_completed</label>
                  <input
                    type="datetime-local"
                    step={60}
  value={formState.dt_completed}
  onChange={(e) => onFieldChange("dt_completed", e.target.value)}
                    disabled={isSaving}
                    className={controlClass}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Project</label>
                  <select
                    className={controlClass}
                    value={formState.projectId ?? ""}
                    onChange={(event) => onFieldChange("projectId", event.target.value)}
                    disabled={isSaving}
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

            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">status</label>
              <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
                {statusOptions.map((option) => {
                  const active = formState.percent_complete === option.value;
                  const base =
                    "flex-1 min-w-[96px] rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition sm:flex-none";
                  const activeClass = "border-indigo-500 bg-indigo-600 text-white shadow";
                  const inactiveClass = "border-gray-300 text-gray-700 hover:border-indigo-400 hover:text-indigo-600 dark:border-gray-700 dark:text-gray-200";
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => onFieldChange("percent_complete", option.value)}
                      className={`${base} ${active ? activeClass : inactiveClass}`}
                      disabled={isSaving}
                    >
                      {option.label}
                    </button>
                  );
                })}
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Selecting a status updates the kanban column automatically.</p>
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Language</label>
              <div className="flex flex-wrap items-end gap-3">
                <div className="flex-1 min-w-[180px] space-y-1">
                  <select
                    className={controlClass}
                    value={activeTranslation?.id || ""}
                    onChange={(event) => setActiveTranslationId(event.target.value)}
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
                    disabled={isSaving}
                  >
                    {languagePickerState.isOpen ? "Hide language" : "Add language"}
                  </button>
                  {activeTranslation && (
                    <button
                      type="button"
                      onClick={() => onRemoveTranslation(activeTranslation.id)}
                      disabled={!canRemoveTranslation || isSaving}
                      className="rounded-xl border border-rose-200 px-3 py-2 text-sm font-semibold text-rose-600 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:border-rose-100 disabled:text-rose-300 dark:border-rose-800 dark:text-rose-300 dark:hover:bg-rose-900/40"
                    >
                      Remove
                    </button>
                  )}
                </div>
              </div>

              {languagePickerState.isOpen && (
                <div className="col-span-1 sm:col-span-2 lg:col-span-2">
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
        </form>

        <div className="flex items-center justify-end gap-3 border-t border-gray-200 bg-white/95 px-5 py-3 backdrop-blur dark:border-gray-800">
          <div className="mr-auto flex items-center gap-3 rounded-xl border border-gray-200 px-3 py-2 text-sm dark:border-gray-800">
            <label className="inline-flex items-center gap-2 text-xs font-semibold text-gray-600 dark:text-gray-300">
              <span>{formState.is_active === "false" ? "Inactive" : "Active"}</span>
              <input
                type="checkbox"
                className="h-4 w-8 cursor-pointer accent-indigo-600"
                checked={formState.is_active !== "false"}
                onChange={(event) => onFieldChange("is_active", event.target.checked ? "true" : "false")}
                disabled={isSaving}
              />
            </label>
          </div>
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

export default KanbanTaskModal;

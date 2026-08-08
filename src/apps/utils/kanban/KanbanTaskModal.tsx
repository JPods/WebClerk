/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { ChangeEvent, FormEvent, ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import type { KanbanTask, TaskPriority } from "./type/kanban";
import type { TaskFormEditableField, TaskFormState, TranslationFormEntry, TaskAttachment, TaskFormFieldValue } from "./taskFormTypes";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

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
  onFieldChange: (field: TaskFormEditableField, value: TaskFormFieldValue) => void;
  columnOptions: Array<{ id: string; title: string }>;
  projectOptions?: Array<{ id: string; name?: string; intent?: string }>;
  priorityOptions: TaskPriority[];
  difficultyOptions: string[];
  progressOptions: string[];
  assigneeOptions?: AssigneeOption[];
  translations: TranslationFormEntry[];
  onTranslationFieldChange: (
    entryId: string,
    field: keyof TranslationFormEntry,
    value: string,
  ) => void;
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
  columnOptions,
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
  const [assigneeSelection, setAssigneeSelection] = useState<string>("");
  const [modalSide, setModalSide] = useState<"left" | "right">("right");
  const [fullscreenPreviewUrl, setFullscreenPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    setAssigneeSelection("");
    setModalSide("right");
    setFullscreenPreviewUrl(null);
  }, [isOpen]);

  const isBlobPreview = useCallback((url?: string) => typeof url === "string" && url.startsWith("blob:"), []);

  const appendAttachments = useCallback((files: FileList | File[]) => {
    const incoming = Array.from(files);
    if (!incoming.length) return;

    const nextAttachments: TaskAttachment[] = incoming.map((file) => {
      const attachment: TaskAttachment = {
        id: `attachment-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`,
        file,
        type: file.type,
        name: file.name,
        size: file.size,
      };

      if (file.type.startsWith("image/")) {
        attachment.previewUrl = URL.createObjectURL(file);
      }

      return attachment;
    });

    onFieldChange("attachments", [...(formState.attachments || []), ...nextAttachments]);
  }, [formState.attachments, onFieldChange]);

  // File upload handling
  const handleFileSelect = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files) return;

    appendAttachments(files);
  }, [appendAttachments]);

  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
  }, []);

  const handleDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();

    const files = event.dataTransfer.files;
    if (!files) return;

    appendAttachments(files);
  }, [appendAttachments]);

  const handlePaste = useCallback((event: React.ClipboardEvent<HTMLElement>) => {
    const clipboardFiles = Array.from(event.clipboardData?.items || [])
      .map((item) => (item.kind === "file" ? item.getAsFile() : null))
      .filter((file): file is File => !!file && file.type.startsWith("image/"));

    if (!clipboardFiles.length) {
      return;
    }

    event.preventDefault();
    appendAttachments(clipboardFiles);
  }, [appendAttachments]);

  const removeAttachment = useCallback((attachmentId: string) => {
    const currentAttachments = formState.attachments || [];
    const updatedAttachments = currentAttachments.filter(att => {
      if (att.id === attachmentId && isBlobPreview(att.previewUrl)) {
        const previewUrl = att.previewUrl;
        if (previewUrl) {
          URL.revokeObjectURL(previewUrl);
        }
      }
      return att.id !== attachmentId;
    });
    onFieldChange("attachments", updatedAttachments);
  }, [formState.attachments, isBlobPreview, onFieldChange]);

  const getFileIcon = (fileType: string) => {
    if (fileType.includes('pdf')) return '📄';
    if (fileType.includes('word') || fileType.includes('document')) return '📝';
    if (fileType.includes('excel') || fileType.includes('spreadsheet')) return '📊';
    if (fileType.includes('powerpoint') || fileType.includes('presentation')) return '📽️';
    if (fileType.includes('zip') || fileType.includes('archive')) return '📦';
    return '📎';
  };

  const closeFullscreenPreview = useCallback((event?: React.MouseEvent) => {
    event?.preventDefault();
    event?.stopPropagation();
    setFullscreenPreviewUrl(null);
  }, []);

  useEffect(() => {
    if (!fullscreenPreviewUrl) {
      return;
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      setFullscreenPreviewUrl(null);
    };

    window.addEventListener("keydown", handleEscape, true);
    return () => {
      window.removeEventListener("keydown", handleEscape, true);
    };
  }, [fullscreenPreviewUrl]);

  const handleAssigneeSelect = (event: ChangeEvent<HTMLSelectElement>) => {
    const selectedId = event.target.value;
    if (!selectedId) return;

    const option = assigneeOptions.find((opt) => opt.id === selectedId);
    const label = option?.label ?? selectedId;
    const existing = (formState.assigned_to || []).some(
      (assignee: any) => assignee.id === selectedId,
    );
    if (!existing) {
      onFieldChange("assigned_to", [
        ...(formState.assigned_to || []),
        { id: selectedId, name: label },
      ]);
    }
    setAssigneeSelection("");
  };

  const statusOptions = useMemo(
    () => [
      { value: "0", label: "Backlog" },
      { value: "5", label: "On hold" },
      { value: "30", label: "In progress" },
      { value: "review", label: "Review" },
      { value: "100", label: "Completed" },
      // { value: "101", label: "Canceled" },
    ],
    [],
  );

  const statusToProgress: Record<string, number> = {
    "0": 0,
    "5": 5,
    "30": 20,
    review: 70,
    "100": 100,
  };

  const normalizeKey = (input: string) => input.trim().toLowerCase().replace(/[^a-z0-9]+/g, "");

  const derivedStatusFromColumn = useMemo(() => {
    const raw = typeof formState.columnId === "string" ? formState.columnId : "";
    const normalized = normalizeKey(raw.replace(/^column-/, ""));
    if (!normalized) {
      return null;
    }

    if (["backlog", "todo", "uncategorized", "icebox"].some((k) => normalized.includes(k))) return "0";
    if (["hold", "onhold", "paused", "waiting"].some((k) => normalized.includes(k))) return "5";
    if (["progress", "inprogress", "inprocess", "doing", "wip"].some((k) => normalized.includes(k))) return "30";
    if (["review", "qa", "verify", "verification", "testing"].some((k) => normalized.includes(k))) return "review";
    if (["complete", "completed", "done", "finished"].some((k) => normalized.includes(k))) return "100";
    return null;
  }, [formState.columnId]);

  const pickColumnIdForStatus = useCallback(
    (statusKey: string): string | undefined => {
      const keywords: Record<string, string[]> = {
        "0": ["backlog", "todo", "uncategorized", "icebox"],
        "5": ["hold", "onhold", "paused", "waiting"],
        "30": ["inprogress", "progress", "doing", "wip", "inprocess"],
        review: ["review", "qa", "verify", "verification", "testing"],
        "100": ["complete", "completed", "done", "finished"],
      };

      const list = keywords[statusKey] ?? [];
      if (!list.length) {
        return undefined;
      }

      const normalizedColumns = (columnOptions ?? []).map((column) => ({
        id: column.id,
        idKey: normalizeKey(column.id.replace(/^column-/, "")),
        titleKey: normalizeKey(column.title),
      }));

      for (const word of list) {
        const key = normalizeKey(word);
        const match = normalizedColumns.find((column) => column.idKey.includes(key) || column.titleKey.includes(key));
        if (match) {
          return match.id;
        }
      }

      return undefined;
    },
    [columnOptions]
  );

  const normalizedPercentComplete = useMemo(() => {
    const raw = formState.percent_complete;
    const numeric = Number(raw);
    if (Number.isFinite(numeric)) {
      return String(Math.max(0, Math.min(100, numeric)));
    }
    const mapped = statusToProgress[raw];
    if (mapped !== undefined) {
      return String(mapped);
    }
    return "0";
  }, [formState.percent_complete, statusToProgress]);

  const derivedStatusKey = useMemo(() => {
    if (derivedStatusFromColumn) {
      return derivedStatusFromColumn;
    }
    const numeric = Number(normalizedPercentComplete);
    if (!Number.isFinite(numeric)) {
      return "0";
    }
    if (numeric >= 100) return "100";
    if (numeric >= 70) return "review";
    if (numeric <= 0) return "0";
    if (numeric <= 5) return "5";
    return "30";
  }, [derivedStatusFromColumn, normalizedPercentComplete]);

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
  const difficultyStops = useMemo(
    () => [10, 20, 30, 40, 50, 60, 70, 75, 80, 85, 90, 95, 100],
    [],
  );
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
  const progressValue = Math.max(
    0,
    Math.min(100, Number(formState.percent_complete) || 0),
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

  const formId = `kanban-task-form-${mode}`;
  const canRemoveTranslation = translations.length > 1;

  const controlBaseClass =
    "w-full h-10 rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 dark:border-gray-700 dark:bg-gray-800 dark:text-white";
  const controlClass = `mt-1 ${controlBaseClass}`;
  const textareaClass = `${controlBaseClass} mt-1 h-5 min-h-[1.5rem] resize-y`;

  const isLeftSide = modalSide === "left";

  const modal = (
    <div
      className={`pointer-events-none fixed inset-0 z-200000 flex items-stretch ${
        isLeftSide ? "justify-start" : "justify-end"
      }`}
    >
      <div className="pointer-events-auto flex h-full items-stretch">
        {!isLeftSide && (
          <button
            type="button"
            onClick={() => setModalSide("left")}
            disabled={isSaving}
            aria-label="Move modal to left side"
            className="flex h-full w-6 items-center justify-center border-x border-gray-200 bg-white/95 text-gray-500 transition hover:bg-gray-100 hover:text-indigo-600 disabled:cursor-not-allowed disabled:text-gray-400 dark:border-gray-800 dark:bg-gray-900/95 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            <svg
              className="h-5 w-5"
              viewBox="0 0 20 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M12.5 4.5L7 10l5.5 5.5"
                stroke="currentColor"
                strokeWidth={1.8}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        )}

        <div
          className={`flex h-full w-full max-h-screen flex-col overflow-hidden bg-white no-scrollbar dark:bg-gray-900 sm:w-[480px] lg:w-[33vw] lg:min-w-[360px] ${
            isLeftSide
              ? "border-r border-gray-200 dark:border-gray-800"
              : "border-l border-gray-200 dark:border-gray-800"
          }`}
        >
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
            disabled={isSaving}
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

        <form
          id={formId}
          className="flex-1 space-y-3 overflow-y-auto px-5 py-4 no-scrollbar"
          onSubmit={onSubmit}
          onPaste={handlePaste}
        >
          {modalError && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/40 dark:text-rose-200">
              {modalError}
            </div>
          )}

          {activeTranslation && (
            <div className="space-y-2">
              {/* Translation section */}
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
                  disabled={isSaving}
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
                  rows={3}
                  value={activeTranslation.description}
                  onPaste={handlePaste}
                  onChange={(event) =>
                    onTranslationFieldChange(
                      activeTranslation.id,
                      "description",
                      event.target.value,
                    )
                  }
                  placeholder="Localized context, acceptance criteria, or notes"
                  disabled={isSaving}
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium tracking-wide text-gray-500 dark:text-gray-400">
                    Attachments ({formState.attachments?.length || 0})
                  </label>
                  <span className="text-[11px] text-gray-400 dark:text-gray-500">drag / paste / upload</span>
                </div>

                <div
                  className="relative rounded-lg border border-dashed border-gray-300 bg-gray-50 px-3 py-2 transition hover:border-indigo-400 hover:bg-indigo-50/50 dark:border-gray-700 dark:bg-gray-800/50 dark:hover:border-indigo-500/40 dark:hover:bg-indigo-900/20"
                  onDragOver={handleDragOver}
                  onDrop={handleDrop}
                  onPaste={handlePaste}
                >
                  <div className="flex items-center justify-center gap-2 text-xs text-gray-600 dark:text-gray-400">
                    <span className="font-semibold">Add files</span>
                    <span>•</span>
                    <span>images, docs, sheets</span>
                  </div>
                  <input
                    id="dropzone-file"
                    type="file"
                    className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                    multiple
                    accept=".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.gif"
                    onChange={handleFileSelect}
                    disabled={isSaving}
                  />
                </div>

                {formState.attachments && formState.attachments.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {formState.attachments.map((attachment) => (
                      <div
                        key={attachment.id}
                        className="group relative flex items-center gap-1 rounded-md border border-gray-200 bg-gray-50 px-1.5 py-1 dark:border-gray-700 dark:bg-gray-800"
                      >
                        {attachment.previewUrl ? (
                          <button
                            type="button"
                            onClick={() => setFullscreenPreviewUrl(attachment.previewUrl || null)}
                            className="rounded"
                            title={attachment.name}
                          >
                            <img
                              src={attachment.previewUrl}
                              alt={attachment.name}
                              className="h-8 w-8 rounded object-cover"
                            />
                          </button>
                        ) : (
                          <div className="flex h-8 w-8 items-center justify-center rounded bg-gray-200 text-sm dark:bg-gray-700">
                            {getFileIcon(attachment.type)}
                          </div>
                        )}

                        <button
                          type="button"
                          onClick={() => removeAttachment(attachment.id)}
                          className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] text-white opacity-0 transition-opacity group-hover:opacity-100"
                          disabled={isSaving}
                          aria-label={`Remove ${attachment.name}`}
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <div className="flex flex-wrap gap-2">
                  {(formState.assigned_to || []).map((a: any) => (
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
                            (x: any) => x.id !== a.id,
                          );
                          onFieldChange("assigned_to", next);
                        }}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
                <select
                  className="font-mono text-[0.85em] bg-transparent border-none cursor-pointer text-indigo-600 dark:text-indigo-400 font-semibold outline-none"
                  style={{ fontSize: 'inherit', padding: 0 }}
                  value={assigneeSelection}
                  onChange={handleAssigneeSelect}
                  disabled={isSaving}
                >
                  <option value="">Assignee</option>
                  {assigneeOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

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
                disabled={isSaving}
                className="w-full accent-indigo-600"
              />
              <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                <span>Easy</span>
                <span>Hard</span>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              percent_complete
            </label>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={progressValue}
              onChange={(e) =>
                onFieldChange(
                  "percent_complete",
                  String(
                    Math.max(0, Math.min(100, Number(e.target.value) || 0)),
                  ),
                )
              }
              disabled={isSaving}
              className="w-full accent-indigo-600"
            />
            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>0%</span>
              <span>50%</span>
              <span>100%</span>
            </div>
          </div>

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
                    disabled={isSaving}
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
                    disabled={isSaving}
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
                    disabled={isSaving}
                    className={controlClass}
                  />
                </div>
                <div>
                  <select
                    className="font-mono text-[0.85em] bg-transparent border-none cursor-pointer text-indigo-600 dark:text-indigo-400 font-semibold outline-none"
                    style={{ fontSize: 'inherit', padding: 0 }}
                    value={formState.projectId ?? ""}
                    onChange={(event) =>
                      onFieldChange("projectId", event.target.value)
                    }
                    disabled={isSaving}
                  >
                    <option value="">Project</option>
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
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                status
              </label>
              <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
                {statusOptions.map((option) => {
                  const active = derivedStatusKey === option.value;
                  const base =
                    "flex-1 min-w-[96px] rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition sm:flex-none";
                  const activeClass =
                    "border-indigo-500 bg-indigo-600 text-white shadow";
                  const inactiveClass =
                    "border-gray-300 text-gray-700 hover:border-indigo-400 hover:text-indigo-600 dark:border-gray-700 dark:text-gray-200";
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => {
                        const mappedProgress = statusToProgress[option.value];
                        onFieldChange("percent_complete", String(mappedProgress ?? 0));

                        const nextColumnId = pickColumnIdForStatus(option.value);
                        if (nextColumnId) {
                          onFieldChange("columnId", nextColumnId);
                        }
                      }}
                      className={`${base} ${
                        active ? activeClass : inactiveClass
                      }`}
                      disabled={isSaving}
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

            <div className="space-y-2">
              <div className="flex flex-wrap items-end gap-3">
                <div className="flex-1 min-w-[180px] space-y-1">
                  <select
                    className="font-mono text-[0.85em] bg-transparent border-none cursor-pointer text-indigo-600 dark:text-indigo-400 font-semibold outline-none"
                    style={{ fontSize: 'inherit', padding: 0 }}
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
                    disabled={isSaving}
                  >
                    {languagePickerState.isOpen
                      ? "Hide language"
                      : "Add language"}
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
                        <label className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                          selection
                        </label>
                        <select
                          className={controlBaseClass}
                          value={languagePickerState.selection}
                          onChange={(event) =>
                            onLanguageSelectionChange(event.target.value)
                          }
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
                            className={controlBaseClass}
                            value={languagePickerState.customValue}
                            onChange={(event) =>
                              onLanguageCustomChange(event.target.value)
                            }
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
                </div>
              )}
            </div>

          </div>
        </form>

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

        {isLeftSide && (
          <button
            type="button"
            onClick={() => setModalSide("right")}
            disabled={isSaving}
            aria-label="Move modal to right side"
            className="flex h-full w-6 items-center justify-center border-x border-gray-200 bg-white/95 text-gray-500 transition hover:bg-gray-100 hover:text-indigo-600 disabled:cursor-not-allowed disabled:text-gray-400 dark:border-gray-800 dark:bg-gray-900/95 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            <svg
              className="h-5 w-5"
              viewBox="0 0 20 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M7.5 4.5L13 10l-5.5 5.5"
                stroke="currentColor"
                strokeWidth={1.8}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        )}
      </div>

      {fullscreenPreviewUrl && (
        <div
          className="pointer-events-auto fixed inset-0 z-200000 flex items-center justify-center bg-black/90 p-4"
          onClick={closeFullscreenPreview}
          onMouseDown={(event) => event.stopPropagation()}
        >
          <img
            src={fullscreenPreviewUrl}
            alt="Attachment preview"
            className="max-h-full max-w-full rounded-lg object-contain"
            onClick={(event) => event.stopPropagation()}
            onMouseDown={(event) => event.stopPropagation()}
          />
        </div>
      )}
    </div>
  );

  if (!isOpen) {
    return null;
  }

  return createPortal(modal, document.body);
};

export default withDevIdentifier(KanbanTaskModal, 'KanbanTaskModal', 'rose', 'apps/utils/kanban/KanbanTaskModal.tsx');
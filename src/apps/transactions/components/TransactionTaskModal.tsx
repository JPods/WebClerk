/**
 * TransactionTaskModal - Generic task/action modal for transaction contexts
 *
 * Provides create/edit functionality for tasks linked to transactions.
 * Styled as a slide-out panel matching existing modal patterns.
 */
import React, { useState, useEffect, useMemo, useCallback } from "react";
import { createPortal } from "react-dom";
import {
  FaTimes,
  FaSpinner,
  FaTrash,
  FaPlus,
  FaCalendarAlt,
  FaUser,
  FaFlag,
  FaTasks,
  FaProjectDiagram,
} from "react-icons/fa";

import type {
  TransactionTaskModalProps,
  TransactionTaskFormState,
  TaskKind,
  TaskPriority,
  TaskStatus,
  AssigneeInfo,
} from "./TransactionTaskModal.types";

import {
  createDefaultTaskState,
  TASK_KIND_OPTIONS,
  PRIORITY_OPTIONS,
  STATUS_OPTIONS,
  PROGRESS_OPTIONS,
  STATUS_CONFIG,
} from "./TransactionTaskModal.types";

// ------------------------------------
// Helper Functions
// ------------------------------------

const formatDateForInput = (dateValue?: string | number): string => {
  if (!dateValue) return "";
  try {
    const date =
      typeof dateValue === "number"
        ? new Date(dateValue > 1e12 ? dateValue : dateValue * 1000)
        : new Date(dateValue);
    if (isNaN(date.getTime())) return "";
    return date.toISOString().slice(0, 16); // Format: YYYY-MM-DDTHH:mm
  } catch {
    return "";
  }
};

const getPriorityColor = (priority: TaskPriority): string => {
  switch (priority) {
    case "critical":
      return "text-rose-600 dark:text-rose-400";
    case "high":
      return "text-orange-600 dark:text-orange-400";
    case "medium":
      return "text-amber-600 dark:text-amber-400";
    case "low":
      return "text-slate-500 dark:text-slate-400";
    default:
      return "text-slate-600 dark:text-slate-300";
  }
};

// ------------------------------------
// Sub-Components
// ------------------------------------

interface FieldLabelProps {
  label: string;
  required?: boolean;
  icon?: React.ReactNode;
}

const FieldLabel: React.FC<FieldLabelProps> = ({ label, required, icon }) => (
  <label className="flex items-center gap-1.5 text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
    {icon}
    {label}
    {required && <span className="text-red-500">*</span>}
  </label>
);

interface AssigneeBadgeProps {
  assignee: AssigneeInfo;
  onRemove: () => void;
  disabled?: boolean;
}

const AssigneeBadge: React.FC<AssigneeBadgeProps> = ({
  assignee,
  onRemove,
  disabled,
}) => (
  <span className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 rounded-full">
    <FaUser size={10} />
    {assignee.name}
    {!disabled && (
      <button
        type="button"
        onClick={onRemove}
        className="ml-1 hover:text-red-600 dark:hover:text-red-400"
      >
        <FaTimes size={10} />
      </button>
    )}
  </span>
);

// ------------------------------------
// Main Component
// ------------------------------------

export const TransactionTaskModal: React.FC<TransactionTaskModalProps> = ({
  mode,
  isOpen,
  onClose,
  onSubmit,
  onDelete,
  initialData,
  isSaving = false,
  isDeleting = false,
  error,
  transactionType,
  transactionId,
  projectOptions = [],
  contactOptions = [],
  title: customTitle,
}) => {
  // Form state
  const [formState, setFormState] = useState<TransactionTaskFormState>(() =>
    createDefaultTaskState(transactionType, transactionId),
  );
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [assigneeDropdownOpen, setAssigneeDropdownOpen] = useState(false);
  const [assigneeSearch, setAssigneeSearch] = useState("");

  // Initialize form state when modal opens or initialData changes
  useEffect(() => {
    if (isOpen) {
      if (mode === "edit" && initialData) {
        setFormState({
          ...createDefaultTaskState(transactionType, transactionId),
          ...initialData,
          dt_start: formatDateForInput(initialData.dt_start),
          dt_deadline: formatDateForInput(initialData.dt_deadline),
          dt_completed: formatDateForInput(initialData.dt_completed),
        });
      } else {
        setFormState(createDefaultTaskState(transactionType, transactionId));
      }
      setShowDeleteConfirm(false);
      setAssigneeSearch("");
    }
  }, [isOpen, mode, initialData, transactionType, transactionId]);

  // Filtered contact options based on search
  const filteredContacts = useMemo(() => {
    const search = assigneeSearch.toLowerCase().trim();
    if (!search) return contactOptions.slice(0, 10);
    return contactOptions
      .filter(
        (c) =>
          c.label.toLowerCase().includes(search) ||
          c.email?.toLowerCase().includes(search),
      )
      .slice(0, 10);
  }, [contactOptions, assigneeSearch]);

  // Handle field changes
  const handleFieldChange = useCallback(
    <K extends keyof TransactionTaskFormState>(
      field: K,
      value: TransactionTaskFormState[K],
    ) => {
      setFormState((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  // Handle adding assignee
  const handleAddAssignee = useCallback(
    (contact: { id: number | string; label: string; email?: string }) => {
      const exists = formState.assigned_to.some(
        (a) => String(a.id) === String(contact.id),
      );
      if (!exists) {
        handleFieldChange("assigned_to", [
          ...formState.assigned_to,
          { id: contact.id, name: contact.label, email: contact.email },
        ]);
      }
      setAssigneeDropdownOpen(false);
      setAssigneeSearch("");
    },
    [formState.assigned_to, handleFieldChange],
  );

  // Handle removing assignee
  const handleRemoveAssignee = useCallback(
    (assigneeId: string | number) => {
      handleFieldChange(
        "assigned_to",
        formState.assigned_to.filter(
          (a) => String(a.id) !== String(assigneeId),
        ),
      );
    },
    [formState.assigned_to, handleFieldChange],
  );

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSaving) return;

    // Validate required fields
    if (!formState.title.trim()) {
      return;
    }

    await onSubmit(formState);
  };

  // Handle delete
  const handleDelete = async () => {
    if (!onDelete || isDeleting) return;
    if (!showDeleteConfirm) {
      setShowDeleteConfirm(true);
      setTimeout(() => setShowDeleteConfirm(false), 3000);
      return;
    }
    await onDelete();
  };

  // Modal title
  const modalTitle =
    customTitle || (mode === "edit" ? "Edit Task" : "Create Task");

  if (!isOpen) return null;

  const modalContent = (
    <div className="pointer-events-none fixed inset-0 z-[200000] flex items-stretch justify-end">
      {/* Backdrop */}
      <div
        className="pointer-events-auto absolute inset-0 bg-black/20 dark:bg-black/40"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="pointer-events-auto relative ml-auto flex h-full w-full max-h-screen flex-col overflow-hidden border-l border-blue-200 dark:border-blue-800 bg-white dark:bg-slate-900 shadow-2xl sm:w-[480px] lg:w-[500px]">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-200 dark:border-slate-700 px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <FaTasks className="text-blue-500" />
              {modalTitle}
            </h2>
            {transactionType && transactionId && (
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Linked to {transactionType} #{transactionId}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSaving}
            className="rounded-full p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 transition-colors"
            aria-label="Close panel"
          >
            <FaTimes size={16} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto">
          <div className="px-5 py-4 space-y-4">
            {/* Error Message */}
            {error && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/40 dark:text-rose-200">
                {error}
              </div>
            )}

            {/* Title */}
            <div>
              <FieldLabel label="Title" required icon={<FaTasks size={12} />} />
              <input
                type="text"
                value={formState.title}
                onChange={(e) => handleFieldChange("title", e.target.value)}
                placeholder="What needs to be done..."
                className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                required
                disabled={isSaving}
                autoFocus
              />
            </div>

            {/* Description */}
            <div>
              <FieldLabel label="Description" />
              <textarea
                value={formState.description}
                onChange={(e) =>
                  handleFieldChange("description", e.target.value)
                }
                placeholder="Additional details..."
                rows={3}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none"
                disabled={isSaving}
              />
            </div>

            {/* Type, Priority, Status - Row */}
            <div className="grid grid-cols-3 gap-3">
              {/* Task Type */}
              <div>
                <FieldLabel label="Type" />
                <select
                  value={formState.kind}
                  onChange={(e) =>
                    handleFieldChange("kind", e.target.value as TaskKind)
                  }
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  disabled={isSaving}
                >
                  {TASK_KIND_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Priority */}
              <div>
                <FieldLabel
                  label="Priority"
                  icon={
                    <FaFlag
                      size={10}
                      className={getPriorityColor(formState.priority)}
                    />
                  }
                />
                <select
                  value={formState.priority}
                  onChange={(e) =>
                    handleFieldChange(
                      "priority",
                      e.target.value as TaskPriority,
                    )
                  }
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  disabled={isSaving}
                >
                  {PRIORITY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Status */}
              <div>
                <FieldLabel label="Status" />
                <select
                  value={formState.status}
                  onChange={(e) =>
                    handleFieldChange("status", e.target.value as TaskStatus)
                  }
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  disabled={isSaving}
                >
                  {STATUS_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Dates Row */}
            <div className="grid grid-cols-2 gap-3">
              {/* Start Date */}
              <div>
                <FieldLabel
                  label="Start Date"
                  icon={<FaCalendarAlt size={10} />}
                />
                <input
                  type="datetime-local"
                  value={formState.dt_start}
                  onChange={(e) =>
                    handleFieldChange("dt_start", e.target.value)
                  }
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  disabled={isSaving}
                />
              </div>

              {/* Due Date */}
              <div>
                <FieldLabel
                  label="Due Date"
                  icon={<FaCalendarAlt size={10} />}
                />
                <input
                  type="datetime-local"
                  value={formState.dt_deadline}
                  onChange={(e) =>
                    handleFieldChange("dt_deadline", e.target.value)
                  }
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  disabled={isSaving}
                />
              </div>
            </div>

            {/* Progress */}
            <div>
              <FieldLabel label={`Progress: ${formState.progress}%`} />
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={formState.progress}
                  onChange={(e) =>
                    handleFieldChange("progress", parseInt(e.target.value, 10))
                  }
                  className="flex-1 h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer"
                  disabled={isSaving}
                />
                <span className="text-xs font-medium text-slate-600 dark:text-slate-300 w-10 text-right">
                  {formState.progress}%
                </span>
              </div>
              <div className="flex justify-between mt-1 px-1">
                {PROGRESS_OPTIONS.map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => handleFieldChange("progress", p)}
                    className={`text-xs px-1.5 py-0.5 rounded ${
                      formState.progress === p
                        ? "bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300"
                        : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                    }`}
                    disabled={isSaving}
                  >
                    {p}%
                  </button>
                ))}
              </div>
            </div>

            {/* Assigned To */}
            <div>
              <FieldLabel label="Assigned To" icon={<FaUser size={10} />} />

              {/* Current Assignees */}
              {formState.assigned_to.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-2">
                  {formState.assigned_to.map((assignee) => (
                    <AssigneeBadge
                      key={String(assignee.id)}
                      assignee={assignee}
                      onRemove={() => handleRemoveAssignee(assignee.id)}
                      disabled={isSaving}
                    />
                  ))}
                </div>
              )}

              {/* Add Assignee Dropdown */}
              <div className="relative">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={assigneeSearch}
                    onChange={(e) => {
                      setAssigneeSearch(e.target.value);
                      if (!assigneeDropdownOpen) setAssigneeDropdownOpen(true);
                    }}
                    onFocus={() => setAssigneeDropdownOpen(true)}
                    placeholder="Search contacts..."
                    className="flex-1 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    disabled={isSaving}
                  />
                  <button
                    type="button"
                    onClick={() =>
                      setAssigneeDropdownOpen(!assigneeDropdownOpen)
                    }
                    className="px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                    disabled={isSaving}
                  >
                    <FaPlus size={12} />
                  </button>
                </div>

                {/* Dropdown */}
                {assigneeDropdownOpen && filteredContacts.length > 0 && (
                  <>
                    <div
                      className="fixed inset-0 z-10"
                      onClick={() => setAssigneeDropdownOpen(false)}
                    />
                    <div className="absolute z-20 mt-1 w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                      {filteredContacts.map((contact) => {
                        const isSelected = formState.assigned_to.some(
                          (a) => String(a.id) === String(contact.id),
                        );
                        return (
                          <button
                            key={String(contact.id)}
                            type="button"
                            onClick={() => handleAddAssignee(contact)}
                            disabled={isSelected}
                            className={`w-full px-3 py-2 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-700 ${
                              isSelected ? "opacity-50 cursor-not-allowed" : ""
                            }`}
                          >
                            <div className="font-medium text-slate-900 dark:text-white">
                              {contact.label}
                            </div>
                            {contact.email && (
                              <div className="text-xs text-slate-500 dark:text-slate-400">
                                {contact.email}
                              </div>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Project */}
            {projectOptions.length > 0 && (
              <div>
                <FieldLabel
                  label="Project"
                  icon={<FaProjectDiagram size={10} />}
                />
                <select
                  value={formState.project_id ?? ""}
                  onChange={(e) => {
                    const id = e.target.value
                      ? parseInt(e.target.value, 10)
                      : undefined;
                    const project = projectOptions.find(
                      (p) => String(p.id) === e.target.value,
                    );
                    handleFieldChange("project_id", id);
                    handleFieldChange(
                      "project_name",
                      project?.name || project?.intent || "",
                    );
                  }}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  disabled={isSaving}
                >
                  <option value="">-- Select Project --</option>
                  {projectOptions.map((proj) => (
                    <option key={String(proj.id)} value={String(proj.id)}>
                      {proj.name ||
                        proj.intent ||
                        proj.slug ||
                        `Project #${proj.id}`}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </form>

        {/* Footer */}
        <div className="border-t border-slate-200 dark:border-slate-700 px-5 py-4 flex items-center justify-between">
          {/* Delete button (edit mode only) */}
          <div>
            {mode === "edit" && onDelete && (
              <button
                type="button"
                onClick={handleDelete}
                disabled={isSaving || isDeleting}
                className={`flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                  showDeleteConfirm
                    ? "bg-red-600 text-white hover:bg-red-700"
                    : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                }`}
              >
                {isDeleting ? (
                  <FaSpinner className="animate-spin" size={14} />
                ) : (
                  <FaTrash size={14} />
                )}
                {showDeleteConfirm ? "Confirm Delete?" : "Delete"}
              </button>
            )}
          </div>

          {/* Cancel & Save buttons */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              onClick={handleSubmit}
              disabled={isSaving || !formState.title.trim()}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed rounded-lg transition-colors"
            >
              {isSaving && <FaSpinner className="animate-spin" size={14} />}
              {mode === "edit" ? "Save Changes" : "Create Task"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
};

export default TransactionTaskModal;

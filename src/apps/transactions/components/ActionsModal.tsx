import React, { useState } from "react";
import { createPortal } from "react-dom";
import type { TransactionActions } from "../types/transactionTypes";
import FieldLabel from "./FieldLabel";

interface ActionsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (actions: TransactionActions) => void;
  initialActions?: TransactionActions;
  mode?: "add" | "edit";
}

const ActionsModal: React.FC<ActionsModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  initialActions = {},
  mode = "add",
}) => {
  const [actions, setActions] = useState<TransactionActions>(initialActions);

  const handleChange = (field: keyof TransactionActions, value: unknown) => {
    setActions((prev) => ({ ...prev, [field]: value }));
  };

  const handleActionNextChange = (
    field: "who" | "when" | "what",
    value: string | number,
  ) => {
    setActions((prev) => ({
      ...prev,
      action_next: { ...prev.action_next, [field]: value },
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(actions);
  };

  if (!isOpen) return null;

  return createPortal(
    <div className="pointer-events-none fixed inset-0 z-[200000] flex items-stretch justify-end">
      <div className="pointer-events-auto ml-auto flex h-full w-full max-h-screen flex-col overflow-hidden border-l border-blue-200 dark:border-blue-800 bg-white dark:bg-slate-800 shadow-2xl no-scrollbar sm:w-[480px] lg:w-[33vw] lg:min-w-[360px]">
        <div className="flex items-start justify-between border-b border-blue-200 dark:border-blue-800 px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              {mode === "edit" ? "Edit Action" : "Add Action"}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
            aria-label="Close panel"
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
          onSubmit={handleSubmit}
          className="flex-1 overflow-y-auto px-5 pb-6 pt-4 space-y-4"
        >
          <div>
            <FieldLabel label="Action Type" />
            <select
              value={actions.kind || "task"}
              onChange={(e) => handleChange("kind", e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-800"
              required
            >
              <option value="task">Task</option>
              <option value="followup">Follow Up</option>
              <option value="call">Call</option>
              <option value="email">Email</option>
              <option value="review">Review</option>
              <option value="approve">Approve</option>
              <option value="ship">Ship</option>
            </select>
          </div>
          <div>
            <FieldLabel label="Priority" />
            <select
              value={actions.priority || "normal"}
              onChange={(e) =>
                handleChange(
                  "priority" as keyof TransactionActions,
                  e.target.value,
                )
              }
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-800"
              required
            >
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </select>
          </div>
          <div>
            <FieldLabel label="Description" />
            <textarea
              value={actions.what || ""}
              onChange={(e) => handleChange("what", e.target.value)}
              rows={2}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-800"
              placeholder="What needs to be done..."
              required
            />
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <FieldLabel label="Assigned To" />
              <input
                type="text"
                value={actions.action_next?.who || ""}
                onChange={(e) => handleActionNextChange("who", e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-800"
                placeholder="Name or ID"
              />
            </div>
            <div>
              <FieldLabel label="Due Date" />
              <input
                type="date"
                value={
                  actions.action_next?.when
                    ? new Date(actions.action_next.when as number)
                        .toISOString()
                        .split("T")[0]
                    : ""
                }
                onChange={(e) => handleActionNextChange("when", e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-800"
              />
            </div>
            <div>
              <FieldLabel label="Task" />
              <input
                type="text"
                value={actions.action_next?.what || ""}
                onChange={(e) => handleActionNextChange("what", e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-800"
                placeholder="Task description"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            >
              {mode === "edit" ? "Save" : "Add"}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body,
  );
};

export default ActionsModal;

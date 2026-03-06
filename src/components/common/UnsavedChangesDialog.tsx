/**
 * UnsavedChangesDialog - Confirmation dialog for unsaved changes
 *
 * Shows a modal dialog when:
 * - User attempts to navigate away with unsaved changes
 * - User triggers a guarded action (print, load new record) with unsaved changes
 */

import React from 'react';
import { FaExclamationTriangle, FaSave, FaTimes } from 'react-icons/fa';

export interface UnsavedChangesDialogProps {
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Type of action being blocked */
  type: 'navigation' | 'action';
  /** Name of the action (e.g., 'print', 'load record') */
  actionName?: string;
  /** Callback when user confirms (discard changes) */
  onConfirm: () => void;
  /** Callback when user cancels (stay and keep editing) */
  onCancel: () => void;
  /** Optional callback to save before proceeding */
  onSaveFirst?: () => Promise<void> | void;
  /** Whether save is in progress */
  isSaving?: boolean;
}

const UnsavedChangesDialog: React.FC<UnsavedChangesDialogProps> = ({
  isOpen,
  type,
  actionName,
  onConfirm,
  onCancel,
  onSaveFirst,
  isSaving = false,
}) => {
  if (!isOpen) return null;

  const title =
    type === 'navigation'
      ? 'Unsaved Changes'
      : `Unsaved Changes - ${actionName || 'Action'}`;

  const message =
    type === 'navigation'
      ? 'You have unsaved changes. If you leave this page, your changes will be lost.'
      : `You have unsaved changes. Would you like to save before ${actionName?.toLowerCase() || 'continuing'}?`;

  const handleSaveFirst = async () => {
    if (onSaveFirst) {
      await onSaveFirst();
      onConfirm();
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
        onClick={onCancel}
      />

      {/* Dialog */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-md transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 shadow-xl transition-all">
          {/* Header */}
          <div className="flex items-center gap-3 border-b border-gray-200 dark:border-gray-700 bg-amber-50 dark:bg-amber-900/20 px-4 py-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-100 dark:bg-amber-900/40">
              <FaExclamationTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {title}
            </h3>
          </div>

          {/* Body */}
          <div className="px-4 py-4">
            <p className="text-sm text-gray-600 dark:text-gray-300">{message}</p>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 px-4 py-3">
            {/* Cancel - Stay on page */}
            <button
              type="button"
              onClick={onCancel}
              disabled={isSaving}
              className="inline-flex items-center gap-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
            >
              <FaTimes className="h-4 w-4" />
              {type === 'navigation' ? 'Stay on Page' : 'Cancel'}
            </button>

            {/* Save First (optional) */}
            {onSaveFirst && (
              <button
                type="button"
                onClick={handleSaveFirst}
                disabled={isSaving}
                className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
              >
                {isSaving ? (
                  <>
                    <svg
                      className="h-4 w-4 animate-spin"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Saving...
                  </>
                ) : (
                  <>
                    <FaSave className="h-4 w-4" />
                    Save First
                  </>
                )}
              </button>
            )}

            {/* Confirm - Discard changes */}
            <button
              type="button"
              onClick={onConfirm}
              disabled={isSaving}
              className="inline-flex items-center gap-2 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50"
            >
              {type === 'navigation' ? 'Leave Page' : 'Discard & Continue'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UnsavedChangesDialog;

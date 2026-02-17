/**
 * TransactionToolbar - Action toolbar for transaction detail pages
 *
 * Provides common actions:
 * - Save & Close
 * - Save
 * - Clone (same type, same customer/contacts)
 * - Transfer (copy lines to different transaction type)
 * - Print
 * - Email
 * - Delete
 */
import React, { useState } from "react";
import {
  FaSave,
  FaSignOutAlt,
  FaCopy,
  FaExchangeAlt,
  FaPrint,
  FaEnvelope,
  FaTrash,
  FaSpinner,
  FaChevronDown,
  FaTasks,
} from "react-icons/fa";

// Transaction types for transfer dropdown
const TRANSACTION_TYPES = [
  { value: "invoice", label: "Invoice" },
  { value: "order", label: "Order" },
  { value: "proposal", label: "Proposal" },
  { value: "purchase", label: "Purchase" },
  { value: "workorder", label: "Work Order" },
] as const;

type TransactionType = (typeof TRANSACTION_TYPES)[number]["value"];

interface TransactionToolbarProps {
  /** Current transaction type */
  transactionType: TransactionType;
  /** Transaction ID (for existing records) */
  transactionId?: number;
  /** Whether form has unsaved changes */
  isDirty?: boolean;
  /** Whether currently saving */
  isSaving?: boolean;
  /** Whether in edit mode */
  isEditing?: boolean;
  /** Callback for Save action */
  onSave?: () => Promise<void> | void;
  /** Callback for Save & Close action */
  onSaveAndClose?: () => Promise<void> | void;
  /** Callback for Clone action */
  onClone?: () => Promise<void> | void;
  /** Callback for Transfer action (receives target type) */
  onTransfer?: (targetType: TransactionType) => Promise<void> | void;
  /** Callback for Print action */
  onPrint?: () => void;
  /** Callback for Email action */
  onEmail?: () => void;
  /** Callback for Delete action */
  onDelete?: () => Promise<void> | void;
  /** Callback for Cancel/Close without saving */
  onCancel?: () => void;
  /** Whether delete is allowed */
  canDelete?: boolean;
  /** Whether clone is allowed */
  canClone?: boolean;
  /** Whether transfer is allowed */
  canTransfer?: boolean;
  /** Callback for Add Task action */
  onAddTask?: () => void;
  /** Whether to show Add Task button */
  showTaskButton?: boolean;
  /** Number of pending tasks (for badge) */
  taskCount?: number;
  /** Custom class name */
  className?: string;
}

const TransactionToolbar: React.FC<TransactionToolbarProps> = ({
  transactionType,
  transactionId,
  isDirty = false,
  isSaving = false,
  isEditing = false,
  onSave,
  onSaveAndClose,
  onClone,
  onTransfer,
  onPrint,
  onEmail,
  onDelete,
  onCancel,
  canDelete = true,
  canClone = true,
  canTransfer = true,
  onAddTask,
  showTaskButton = true,
  taskCount,
  className = "",
}) => {
  const [showTransferMenu, setShowTransferMenu] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  const isNewRecord = !transactionId;

  // Wrapper to handle async actions with loading state
  const handleAction = async (
    actionName: string,
    action?: () => Promise<void> | void,
  ) => {
    if (!action || actionInProgress) return;
    setActionInProgress(actionName);
    try {
      await action();
    } catch (error) {
      console.error(`${actionName} failed:`, error);
    } finally {
      setActionInProgress(null);
    }
  };

  // Handle transfer to specific type
  const handleTransfer = async (targetType: TransactionType) => {
    setShowTransferMenu(false);
    if (onTransfer) {
      await handleAction("transfer", () => onTransfer(targetType));
    }
  };

  // Handle delete with confirmation
  const handleDeleteClick = () => {
    if (showDeleteConfirm) {
      handleAction("delete", onDelete);
      setShowDeleteConfirm(false);
    } else {
      setShowDeleteConfirm(true);
      // Auto-hide confirmation after 3 seconds
      setTimeout(() => setShowDeleteConfirm(false), 3000);
    }
  };

  // Filter transfer options (exclude current type)
  const transferOptions = TRANSACTION_TYPES.filter(
    (t) => t.value !== transactionType,
  );

  // Common button styles
  const buttonBase =
    "flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2";
  const primaryButton = `${buttonBase} bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500 disabled:bg-blue-400 disabled:cursor-not-allowed`;
  const secondaryButton = `${buttonBase} bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-200 dark:border-gray-600 dark:hover:bg-gray-700`;
  const dangerButton = `${buttonBase} bg-red-600 text-white hover:bg-red-700 focus:ring-red-500`;

  return (
    <div
      className={`flex items-center justify-between gap-2 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm ${className}`}
    >
      {/* Left side: Primary actions */}
      <div className="flex items-center gap-2">
        {/* Save & Close */}
        {isEditing && onSaveAndClose && (
          <button
            type="button"
            onClick={() => handleAction("saveAndClose", onSaveAndClose)}
            disabled={isSaving || actionInProgress !== null}
            className={`${primaryButton} text-xs`}
            title="Save and close"
          >
            {actionInProgress === "saveAndClose" ? (
              <FaSpinner className="animate-spin" size={14} />
            ) : (
              <>
                <FaSave size={14} />
                <FaSignOutAlt size={12} />
              </>
            )}
            <span className="hidden xs:inline">Save & Close</span>
          </button>
        )}

        {/* Save */}
        {isEditing && onSave && (
          <button
            type="button"
            onClick={() => handleAction("save", onSave)}
            disabled={isSaving || actionInProgress !== null || !isDirty}
            className={`${secondaryButton} text-xs`}
            title="Save"
          >
            {actionInProgress === "save" || isSaving ? (
              <FaSpinner className="animate-spin" size={14} />
            ) : (
              <FaSave size={14} />
            )}
            <span className="hidden sm:inline">Save</span>
          </button>
        )}

        {/* Cancel (in edit mode) */}
        {isEditing && onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={isSaving || actionInProgress !== null}
            className={`${secondaryButton} text-xs`}
            title="Cancel"
          >
            Cancel
          </button>
        )}
      </div>

      {/* Divider */}
      {isEditing && <div className="h-6 w-px bg-gray-300 dark:bg-gray-600" />}

      {/* Middle: Secondary actions */}
      <div className="flex items-center gap-2">
        {/* Add Task */}
        {!isNewRecord && showTaskButton && onAddTask && (
          <button
            type="button"
            onClick={onAddTask}
            disabled={actionInProgress !== null}
            className={`${secondaryButton} text-xs relative`}
            title="Add Task"
          >
            <FaTasks size={14} />
            <span className="hidden md:inline">Task</span>
            {taskCount !== undefined && taskCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 flex items-center justify-center w-4 h-4 text-[10px] font-bold text-white bg-blue-500 rounded-full">
                {taskCount > 9 ? "9+" : taskCount}
              </span>
            )}
          </button>
        )}

        {/* Clone */}
        {!isNewRecord && canClone && onClone && (
          <button
            type="button"
            onClick={() => handleAction("clone", onClone)}
            disabled={actionInProgress !== null}
            className={`${secondaryButton} text-xs`}
            title="Clone this transaction"
          >
            {actionInProgress === "clone" ? (
              <FaSpinner className="animate-spin" size={14} />
            ) : (
              <FaCopy size={14} />
            )}
            <span className="hidden md:inline">Clone</span>
          </button>
        )}

        {/* Transfer dropdown */}
        {!isNewRecord && canTransfer && onTransfer && (
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowTransferMenu(!showTransferMenu)}
              disabled={actionInProgress !== null}
              className={`${secondaryButton} text-xs`}
              title="Transfer lines to another transaction type"
            >
              {actionInProgress === "transfer" ? (
                <FaSpinner className="animate-spin" size={14} />
              ) : (
                <FaExchangeAlt size={14} />
              )}
              <span className="hidden md:inline">Transfer</span>
              <FaChevronDown size={10} />
            </button>

            {/* Transfer dropdown menu */}
            {showTransferMenu && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowTransferMenu(false)}
                />
                <div className="absolute right-0 z-20 mt-1 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg">
                  <div className="py-1">
                    <div className="px-3 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Transfer to...
                    </div>
                    {transferOptions.map((option) => (
                      <button
                        type="button"
                        key={option.value}
                        onClick={() => handleTransfer(option.value)}
                        className="w-full px-3 py-2 text-left text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* Print */}
        {!isNewRecord && onPrint && (
          <button
            type="button"
            onClick={onPrint}
            disabled={actionInProgress !== null}
            className={`${secondaryButton} text-xs`}
            title="Print"
          >
            <FaPrint size={14} />
            <span className="hidden md:inline">Print</span>
          </button>
        )}

        {/* Email */}
        {!isNewRecord && onEmail && (
          <button
            type="button"
            onClick={onEmail}
            disabled={actionInProgress !== null}
            className={`${secondaryButton} text-xs`}
            title="Email"
          >
            <FaEnvelope size={14} />
            <span className="hidden md:inline">Email</span>
          </button>
        )}
      </div>

      {/* Right side: Danger zone */}
      <div className="flex items-center gap-2">
        {/* Delete */}
        {!isNewRecord && canDelete && onDelete && (
          <button
            type="button"
            onClick={handleDeleteClick}
            disabled={actionInProgress !== null}
            className={
              showDeleteConfirm
                ? `${dangerButton} text-xs`
                : `${secondaryButton} text-xs`
            }
            title={
              showDeleteConfirm ? "Click again to confirm delete" : "Delete"
            }
          >
            {actionInProgress === "delete" ? (
              <FaSpinner className="animate-spin" size={14} />
            ) : (
              <FaTrash size={14} />
            )}
            <span className={showDeleteConfirm ? "inline" : "hidden md:inline"}>
              {showDeleteConfirm ? "Confirm?" : "Delete"}
            </span>
          </button>
        )}
      </div>
    </div>
  );
};

export default TransactionToolbar;

// Export types for consumers
export type { TransactionToolbarProps, TransactionType };

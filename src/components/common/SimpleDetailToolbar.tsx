/**
 * SimpleDetailToolbar - Lightweight action toolbar for simple Detail pages
 * 
 * Provides standard actions for lookup table / simple entity forms:
 * - Edit (view mode)
 * - Save (edit/add mode)
 * - Cancel (edit/add mode)
 * - Delete (edit mode, optional)
 */
import { Save, X, Pencil, Trash2 } from "lucide-react";

interface SimpleDetailToolbarProps {
  /** Current mode */
  mode: "add" | "edit" | "view";
  /** Whether currently saving */
  isSaving?: boolean;
  /** Callback for Save action */
  onSave?: () => void;
  /** Callback for Cancel action */
  onCancel?: () => void;
  /** Callback for Edit action (view mode) */
  onEdit?: () => void;
  /** Callback for Delete action */
  onDelete?: () => void;
  /** Whether delete is allowed */
  canDelete?: boolean;
  /** Custom class name */
  className?: string;
}

export function SimpleDetailToolbar({
  mode,
  isSaving = false,
  onSave,
  onCancel,
  onEdit,
  onDelete,
  canDelete = false,
  className = "",
}: SimpleDetailToolbarProps) {
  return (
    <div className={`flex items-center gap-2 py-2 px-4 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 ${className}`}>
      {mode === "view" ? (
        // View mode: Edit button
        <>
          {onEdit && (
            <button
              type="button"
              onClick={onEdit}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-brand-500 rounded-md hover:bg-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 transition-colors"
            >
              <Pencil className="w-4 h-4" />
              Edit
            </button>
          )}
          {canDelete && onDelete && (
            <button
              type="button"
              onClick={onDelete}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-red-600 bg-white border border-red-300 rounded-md hover:bg-red-50 dark:bg-gray-700 dark:text-red-400 dark:border-red-700 dark:hover:bg-red-900/20 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              Delete
            </button>
          )}
        </>
      ) : (
        // Edit/Add mode: Save and Cancel buttons
        <>
          <button
            type="submit"
            disabled={isSaving}
            onClick={onSave}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-brand-500 rounded-md hover:bg-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSaving ? (
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            {mode === "add" ? "Create" : "Save"}
          </button>
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-200 dark:border-gray-600 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 transition-colors"
            >
              <X className="w-4 h-4" />
              Cancel
            </button>
          )}
          {mode === "edit" && canDelete && onDelete && (
            <button
              type="button"
              onClick={onDelete}
              className="ml-auto inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-red-600 bg-white border border-red-300 rounded-md hover:bg-red-50 dark:bg-gray-700 dark:text-red-400 dark:border-red-700 dark:hover:bg-red-900/20 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              Delete
            </button>
          )}
        </>
      )}
    </div>
  );
}

export default SimpleDetailToolbar;

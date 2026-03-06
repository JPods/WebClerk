/**
 * useUnsavedChangesGuard - Hook to prevent data loss from unsaved changes
 *
 * Features:
 * - Shows browser warning on page close/refresh
 * - Provides wrapper for guarding actions (print, load new record)
 * - Exposes dialog state for custom UI
 *
 * Note: This app uses a custom window management system rather than standard
 * React Router navigation, so in-app navigation blocking is handled via
 * the guardAction wrapper rather than useBlocker.
 *
 * Usage:
 * ```tsx
 * const { isDirty, formState } = useForm();
 * const {
 *   guardAction,
 *   isActionPending,
 *   confirmAction,
 *   cancelAction,
 *   showDialog,
 * } = useUnsavedChangesGuard(isDirty);
 *
 * // Guard print action
 * const handlePrint = guardAction(() => window.print(), 'print');
 *
 * // Render dialog when action is pending
 * {showDialog && (
 *   <UnsavedChangesDialog
 *     type="action"
 *     onConfirm={confirmAction}
 *     onCancel={cancelAction}
 *   />
 * )}
 * ```
 */

import { useCallback, useEffect, useState } from 'react';

export interface UnsavedChangesGuardResult {
  /** Whether a guarded action is pending confirmation */
  isActionPending: boolean;
  /** Details about the pending action */
  pendingAction: { name: string; callback: () => void } | null;
  /** Confirm and proceed with pending action */
  confirmAction: () => void;
  /** Cancel pending action */
  cancelAction: () => void;
  /** Wrap an action to guard it with unsaved changes check */
  guardAction: <T extends (...args: any[]) => any>(
    action: T,
    actionName?: string
  ) => (...args: Parameters<T>) => void;
  /** Whether the dialog should be shown */
  showDialog: boolean;
}

/**
 * Hook to guard against losing unsaved changes
 *
 * @param isDirty - Whether the form has unsaved changes
 * @param options - Configuration options
 * @returns Guard utilities and state
 */
export function useUnsavedChangesGuard(
  isDirty: boolean,
  options: {
    /** Custom message for browser beforeunload (browser may ignore) */
    message?: string;
    /** Whether to enable beforeunload browser warning */
    enableBeforeUnload?: boolean;
  } = {}
): UnsavedChangesGuardResult {
  const {
    message = 'You have unsaved changes. Are you sure you want to leave?',
    enableBeforeUnload = true,
  } = options;

  // State for guarded actions (print, etc.)
  const [pendingAction, setPendingAction] = useState<{
    name: string;
    callback: () => void;
  } | null>(null);

  // Browser beforeunload handler for close/refresh
  useEffect(() => {
    if (!enableBeforeUnload || !isDirty) return;

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      // Modern browsers ignore custom messages but still show a generic warning
      e.returnValue = message;
      return message;
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isDirty, enableBeforeUnload, message]);

  // Action confirmation handlers
  const confirmAction = useCallback(() => {
    if (pendingAction) {
      pendingAction.callback();
      setPendingAction(null);
    }
  }, [pendingAction]);

  const cancelAction = useCallback(() => {
    setPendingAction(null);
  }, []);

  // Guard wrapper for actions
  const guardAction = useCallback(
    <T extends (...args: any[]) => any>(action: T, actionName = 'action') => {
      return (...args: Parameters<T>) => {
        if (isDirty) {
          // Queue the action for confirmation
          setPendingAction({
            name: actionName,
            callback: () => action(...args),
          });
        } else {
          // No unsaved changes, execute immediately
          action(...args);
        }
      };
    },
    [isDirty]
  );

  // Derived state for dialog display
  const isActionPending = pendingAction !== null;
  const showDialog = isActionPending;

  return {
    isActionPending,
    pendingAction,
    confirmAction,
    cancelAction,
    guardAction,
    showDialog,
  };
}

export default useUnsavedChangesGuard;

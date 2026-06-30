/**
 * ConfirmDialog — standard confirmation dialog for wc3.
 * Replaces all window.confirm() calls. Themed dark/light.
 *
 * Usage:
 *   const [confirm, ConfirmDialog] = useConfirm();
 *   const ok = await confirm('Delete this record?', 'This cannot be undone.');
 *   if (ok) { ... }
 */
import React, { useCallback, useRef, useState } from 'react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'default';
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({ open, title, message, confirmLabel = 'Confirm', cancelLabel = 'Cancel', variant = 'default', onConfirm, onCancel }: ConfirmDialogProps) {
  if (!open) return null;
  const btnClass = variant === 'danger'
    ? 'bg-red-600 text-white hover:bg-red-700'
    : 'bg-blue-600 text-white hover:bg-blue-700';

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.4)' }} onClick={onCancel}>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl w-96 overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="p-5">
          <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-2">{title}</h3>
          {message && <p className="text-xs text-gray-600 dark:text-gray-400">{message}</p>}
        </div>
        <div className="flex justify-end gap-2 px-5 py-3 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
          <button onClick={onCancel} className="px-4 py-1.5 text-xs font-medium rounded border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700">{cancelLabel}</button>
          <button onClick={onConfirm} className={`px-4 py-1.5 text-xs font-medium rounded ${btnClass}`} autoFocus>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}

/** Hook for imperative confirm — returns [confirm(title, message?), DialogElement] */
export function useConfirm(): [(title: string, message?: string, variant?: 'danger' | 'default') => Promise<boolean>, React.ReactElement] {
  const [state, setState] = useState<{ title: string; message?: string; variant?: 'danger' | 'default' } | null>(null);
  const resolveRef = useRef<(v: boolean) => void>();

  const confirm = useCallback((title: string, message?: string, variant?: 'danger' | 'default') => {
    return new Promise<boolean>((resolve) => {
      resolveRef.current = resolve;
      setState({ title, message, variant });
    });
  }, []);

  const dialog = (
    <ConfirmDialog
      open={state !== null}
      title={state?.title || ''}
      message={state?.message}
      variant={state?.variant}
      confirmLabel={state?.variant === 'danger' ? 'Delete' : 'Confirm'}
      onConfirm={() => { resolveRef.current?.(true); setState(null); }}
      onCancel={() => { resolveRef.current?.(false); setState(null); }}
    />
  );

  return [confirm, dialog];
}

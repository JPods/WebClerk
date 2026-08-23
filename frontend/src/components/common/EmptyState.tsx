/**
 * EmptyState — standard "no data" display for wc3.
 * Shows icon, message, and optional action button.
 *
 * Usage:
 *   <EmptyState message="No customers found" action="Create Customer" onAction={() => ...} />
 *   <EmptyState message="No records match your filter" />
 */
import React from 'react';

interface EmptyStateProps {
  message: string;
  description?: string;
  action?: string;
  onAction?: () => void;
  icon?: string;
}

export default function EmptyState({ message, description, action, onAction, icon = '📋' }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="text-3xl mb-3">{icon}</div>
      <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">{message}</div>
      {description && <div className="text-xs text-gray-400 dark:text-gray-500 mb-3 text-center max-w-xs">{description}</div>}
      {action && onAction && (
        <button onClick={onAction}
          className="px-4 py-1.5 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition mt-2">
          {action}
        </button>
      )}
    </div>
  );
}

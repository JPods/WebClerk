import { useState, useCallback } from 'react';

export type InvoiceStatus = 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled';

// Explicit order for status workflow visualization
export const STATUS_ORDER: InvoiceStatus[] = ['draft', 'sent', 'paid', 'overdue', 'cancelled'];

export interface StatusTransition {
  from: InvoiceStatus;
  to: InvoiceStatus;
  label: string;
  description: string;
  requiresConfirmation?: boolean;
}

export interface StatusConfig {
  label: string;
  color: string;
  bgColor: string;
  description: string;
  transitions: StatusTransition[];
  isFinal: boolean;
}

// Status configuration
const STATUS_CONFIG: Record<InvoiceStatus, StatusConfig> = {
  draft: {
    label: 'Draft',
    color: 'text-gray-600 dark:text-gray-400',
    bgColor: 'bg-gray-100 dark:bg-gray-700',
    description: 'Invoice is being prepared',
    transitions: [
      {
        from: 'draft',
        to: 'sent',
        label: 'Send Invoice',
        description: 'Mark invoice as sent'
      },
      {
        from: 'draft',
        to: 'cancelled',
        label: 'Cancel',
        description: 'Cancel this invoice',
        requiresConfirmation: true
      }
    ],
    isFinal: false
  },
  sent: {
    label: 'Sent',
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-100 dark:bg-blue-900',
    description: 'Invoice has been sent to customer',
    transitions: [
      {
        from: 'sent',
        to: 'paid',
        label: 'Mark Paid',
        description: 'Mark invoice as paid'
      },
      {
        from: 'sent',
        to: 'overdue',
        label: 'Mark Overdue',
        description: 'Mark invoice as overdue'
      },
      {
        from: 'sent',
        to: 'cancelled',
        label: 'Cancel',
        description: 'Cancel this invoice',
        requiresConfirmation: true
      }
    ],
    isFinal: false
  },
  paid: {
    label: 'Paid',
    color: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-100 dark:bg-green-900',
    description: 'Invoice has been paid',
    transitions: [], // Final state
    isFinal: true
  },
  overdue: {
    label: 'Overdue',
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-100 dark:bg-red-900',
    description: 'Invoice is overdue',
    transitions: [], // Final state - cannot mark as paid if overdue
    isFinal: true
  },
  cancelled: {
    label: 'Cancelled',
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-100 dark:bg-red-900',
    description: 'Invoice has been cancelled',
    transitions: [], // Final state
    isFinal: true
  }
};

export const isInvoiceStatus = (value: unknown): value is InvoiceStatus => {
  return typeof value === 'string' && STATUS_ORDER.includes(value as InvoiceStatus);
};

export const normalizeInvoiceStatus = (value: unknown): InvoiceStatus => {
  return isInvoiceStatus(value) ? (value as InvoiceStatus) : 'draft';
};

export function useInvoiceStatus(initialStatus: InvoiceStatus | string | null | undefined = 'draft') {
  const normalizedInitial = normalizeInvoiceStatus(initialStatus);
  const [currentStatus, setCurrentStatus] = useState<InvoiceStatus>(normalizedInitial);

  const getStatusConfig = useCallback((status: InvoiceStatus | string | null | undefined) => {
    const safeStatus = normalizeInvoiceStatus(status);
    return STATUS_CONFIG[safeStatus];
  }, []);

  const getAvailableTransitions = useCallback((status: InvoiceStatus | string | null | undefined) => {
    const safeStatus = normalizeInvoiceStatus(status);
    return STATUS_CONFIG[safeStatus].transitions;
  }, []);

  const canTransitionTo = useCallback((fromStatus: InvoiceStatus | string | null | undefined, toStatus: InvoiceStatus | string | null | undefined) => {
    const safeFrom = normalizeInvoiceStatus(fromStatus);
    const safeTo = normalizeInvoiceStatus(toStatus);
    const transitions = getAvailableTransitions(safeFrom);
    return transitions.some(t => t.to === safeTo);
  }, [getAvailableTransitions]);

  const transitionTo = useCallback((newStatus: InvoiceStatus | string | null | undefined) => {
    const safeStatus = normalizeInvoiceStatus(newStatus);
    if (canTransitionTo(currentStatus, safeStatus)) {
      setCurrentStatus(safeStatus);
      return true;
    }
    return false;
  }, [currentStatus, canTransitionTo]);

  const getStatusHistory = useCallback(() => {
    // In a real app, this would come from the backend
    // For now, return mock history
    return [
      {
        status: 'draft',
        timestamp: new Date(Date.now() - 86400000), // 1 day ago
        user: 'System'
      },
      {
        status: currentStatus,
        timestamp: new Date(),
        user: 'Current User'
      }
    ];
  }, [currentStatus]);

  return {
    currentStatus,
    setCurrentStatus,
    getStatusConfig,
    getAvailableTransitions,
    canTransitionTo,
    transitionTo,
    getStatusHistory
  };
}

// Export STATUS_CONFIG separately
export { STATUS_CONFIG };
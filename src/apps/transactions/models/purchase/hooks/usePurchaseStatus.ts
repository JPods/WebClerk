import { useState, useCallback } from 'react';

export type PurchaseStatus = 'draft' | 'approved' | 'rejected' | 'received' | 'closed';

export interface StatusTransition {
  from: PurchaseStatus;
  to: PurchaseStatus;
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

// Status configuration for Purchase Orders
const STATUS_CONFIG: Record<PurchaseStatus, StatusConfig> = {
  draft: {
    label: 'Draft',
    color: 'text-gray-600 dark:text-gray-400',
    bgColor: 'bg-gray-100 dark:bg-gray-700',
    description: 'Purchase order is being prepared',
    transitions: [
      {
        from: 'draft',
        to: 'approved',
        label: 'Approve',
        description: 'Approve this purchase order'
      },
      {
        from: 'draft',
        to: 'rejected',
        label: 'Reject',
        description: 'Reject this purchase order',
        requiresConfirmation: true
      }
    ],
    isFinal: false
  },
  approved: {
    label: 'Approved',
    color: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-100 dark:bg-green-900',
    description: 'Purchase order has been approved',
    transitions: [
      {
        from: 'approved',
        to: 'received',
        label: 'Mark Received',
        description: 'Mark items as received'
      },
      {
        from: 'approved',
        to: 'rejected',
        label: 'Reject',
        description: 'Reject this purchase order',
        requiresConfirmation: true
      }
    ],
    isFinal: false
  },
  rejected: {
    label: 'Rejected',
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-100 dark:bg-red-900',
    description: 'Purchase order has been rejected',
    transitions: [], // Final state
    isFinal: true
  },
  received: {
    label: 'Received',
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-100 dark:bg-blue-900',
    description: 'Items have been received',
    transitions: [
      {
        from: 'received',
        to: 'closed',
        label: 'Close Order',
        description: 'Close this purchase order'
      }
    ],
    isFinal: false
  },
  closed: {
    label: 'Closed',
    color: 'text-purple-600 dark:text-purple-400',
    bgColor: 'bg-purple-100 dark:bg-purple-900',
    description: 'Purchase order has been closed',
    transitions: [], // Final state
    isFinal: true
  }
};

const PURCHASE_STATUSES: PurchaseStatus[] = ['draft', 'approved', 'rejected', 'received', 'closed'];

export const isPurchaseStatus = (value: unknown): value is PurchaseStatus => {
  return typeof value === 'string' && PURCHASE_STATUSES.includes(value as PurchaseStatus);
};

export const normalizePurchaseStatus = (value: unknown): PurchaseStatus => {
  return isPurchaseStatus(value) ? (value as PurchaseStatus) : 'draft';
};

export function usePurchaseStatus(initialStatus: PurchaseStatus | string | null | undefined = 'draft') {
  const normalizedInitial = normalizePurchaseStatus(initialStatus);
  const [currentStatus, setCurrentStatus] = useState<PurchaseStatus>(normalizedInitial);

  const getStatusConfig = useCallback((status: PurchaseStatus | string | null | undefined) => {
    const safeStatus = normalizePurchaseStatus(status);
    return STATUS_CONFIG[safeStatus];
  }, []);

  const getAvailableTransitions = useCallback((status: PurchaseStatus | string | null | undefined) => {
    const safeStatus = normalizePurchaseStatus(status);
    return STATUS_CONFIG[safeStatus].transitions;
  }, []);

  const canTransitionTo = useCallback((fromStatus: PurchaseStatus | string | null | undefined, toStatus: PurchaseStatus | string | null | undefined) => {
    const safeFrom = normalizePurchaseStatus(fromStatus);
    const safeTo = normalizePurchaseStatus(toStatus);
    const transitions = getAvailableTransitions(safeFrom);
    return transitions.some(t => t.to === safeTo);
  }, [getAvailableTransitions]);

  const transitionTo = useCallback((newStatus: PurchaseStatus | string | null | undefined) => {
    const safeStatus = normalizePurchaseStatus(newStatus);
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
export { STATUS_CONFIG, PURCHASE_STATUSES };
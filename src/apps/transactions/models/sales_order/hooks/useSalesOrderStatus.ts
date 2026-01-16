import { useState, useCallback } from 'react';

// Backend uses these statuses
export type SalesOrderStatus = 'planned' | 'released' | 'in_progress' | 'hold' | 'complete' | 'canceled' | 'draft' | 'confirmed' | 'shipped' | 'delivered' | 'cancelled';

export interface StatusTransition {
  from: SalesOrderStatus;
  to: SalesOrderStatus;
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

// Status configuration - includes both legacy and new status values
export const STATUS_CONFIG: Record<string, StatusConfig> = {
  // Backend statuses (from TransactionBaseModel)
  planned: {
    label: 'Planned',
    color: 'text-gray-600 dark:text-gray-400',
    bgColor: 'bg-gray-100 dark:bg-gray-700',
    description: 'Sales order is being planned',
    transitions: [
      { from: 'planned', to: 'released', label: 'Release', description: 'Release order for processing' },
      { from: 'planned', to: 'canceled', label: 'Cancel', description: 'Cancel this order', requiresConfirmation: true }
    ],
    isFinal: false
  },
  released: {
    label: 'Released',
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-100 dark:bg-blue-900',
    description: 'Sales order has been released',
    transitions: [
      { from: 'released', to: 'in_progress', label: 'Start Processing', description: 'Begin processing this order' },
      { from: 'released', to: 'hold', label: 'Hold', description: 'Put order on hold' },
      { from: 'released', to: 'canceled', label: 'Cancel', description: 'Cancel this order', requiresConfirmation: true }
    ],
    isFinal: false
  },
  in_progress: {
    label: 'In Progress',
    color: 'text-yellow-600 dark:text-yellow-400',
    bgColor: 'bg-yellow-100 dark:bg-yellow-900',
    description: 'Sales order is being processed',
    transitions: [
      { from: 'in_progress', to: 'complete', label: 'Complete', description: 'Mark as complete' },
      { from: 'in_progress', to: 'hold', label: 'Hold', description: 'Put order on hold' },
      { from: 'in_progress', to: 'canceled', label: 'Cancel', description: 'Cancel this order', requiresConfirmation: true }
    ],
    isFinal: false
  },
  hold: {
    label: 'On Hold',
    color: 'text-orange-600 dark:text-orange-400',
    bgColor: 'bg-orange-100 dark:bg-orange-900',
    description: 'Sales order is on hold',
    transitions: [
      { from: 'hold', to: 'released', label: 'Release', description: 'Release from hold' },
      { from: 'hold', to: 'canceled', label: 'Cancel', description: 'Cancel this order', requiresConfirmation: true }
    ],
    isFinal: false
  },
  complete: {
    label: 'Complete',
    color: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-100 dark:bg-green-900',
    description: 'Sales order has been completed',
    transitions: [],
    isFinal: true
  },
  canceled: {
    label: 'Canceled',
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-100 dark:bg-red-900',
    description: 'Sales order has been canceled',
    transitions: [],
    isFinal: true
  },
  // Legacy statuses (for backwards compatibility)
  draft: {
    label: 'Draft',
    color: 'text-gray-600 dark:text-gray-400',
    bgColor: 'bg-gray-100 dark:bg-gray-700',
    description: 'Sales order is being prepared',
    transitions: [
      { from: 'draft', to: 'confirmed', label: 'Confirm Order', description: 'Mark sales order as confirmed' },
      { from: 'draft', to: 'cancelled', label: 'Cancel', description: 'Cancel this sales order', requiresConfirmation: true }
    ],
    isFinal: false
  },
  confirmed: {
    label: 'Confirmed',
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-100 dark:bg-blue-900',
    description: 'Sales order has been confirmed',
    transitions: [
      { from: 'confirmed', to: 'shipped', label: 'Mark Shipped', description: 'Mark sales order as shipped' },
      { from: 'confirmed', to: 'cancelled', label: 'Cancel', description: 'Cancel this sales order', requiresConfirmation: true }
    ],
    isFinal: false
  },
  shipped: {
    label: 'Shipped',
    color: 'text-yellow-600 dark:text-yellow-400',
    bgColor: 'bg-yellow-100 dark:bg-yellow-900',
    description: 'Sales order has been shipped',
    transitions: [
      { from: 'shipped', to: 'delivered', label: 'Mark Delivered', description: 'Mark sales order as delivered' },
      { from: 'shipped', to: 'cancelled', label: 'Cancel', description: 'Cancel this sales order', requiresConfirmation: true }
    ],
    isFinal: false
  },
  delivered: {
    label: 'Delivered',
    color: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-100 dark:bg-green-900',
    description: 'Sales order has been delivered',
    transitions: [],
    isFinal: true
  },
  cancelled: {
    label: 'Cancelled',
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-100 dark:bg-red-900',
    description: 'Sales order has been cancelled',
    transitions: [],
    isFinal: true
  }
};

// Default config for unknown statuses
const DEFAULT_STATUS_CONFIG: StatusConfig = {
  label: 'Unknown',
  color: 'text-gray-600 dark:text-gray-400',
  bgColor: 'bg-gray-100 dark:bg-gray-700',
  description: 'Unknown status',
  transitions: [],
  isFinal: false
};

export function useSalesOrderStatus(initialStatus: SalesOrderStatus = 'planned') {
  const [currentStatus, setCurrentStatus] = useState<SalesOrderStatus>(initialStatus);

  const getStatusConfig = useCallback((status: SalesOrderStatus): StatusConfig => {
    return STATUS_CONFIG[status] ?? DEFAULT_STATUS_CONFIG;
  }, []);

  const getAvailableTransitions = useCallback((status: SalesOrderStatus) => {
    const config = STATUS_CONFIG[status];
    return config?.transitions ?? [];
  }, []);

  const canTransitionTo = useCallback((fromStatus: SalesOrderStatus, toStatus: SalesOrderStatus) => {
    const transitions = getAvailableTransitions(fromStatus);
    return transitions.some(t => t.to === toStatus);
  }, [getAvailableTransitions]);

  const transitionTo = useCallback((newStatus: SalesOrderStatus) => {
    if (canTransitionTo(currentStatus, newStatus)) {
      setCurrentStatus(newStatus);
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
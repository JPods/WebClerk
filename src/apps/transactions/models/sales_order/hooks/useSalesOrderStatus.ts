import { useState, useCallback } from 'react';

export type SalesOrderStatus = 'draft' | 'confirmed' | 'shipped' | 'delivered' | 'cancelled';

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

// Status configuration
const STATUS_CONFIG: Record<SalesOrderStatus, StatusConfig> = {
  draft: {
    label: 'Draft',
    color: 'text-gray-600 dark:text-gray-400',
    bgColor: 'bg-gray-100 dark:bg-gray-700',
    description: 'Sales order is being prepared',
    transitions: [
      {
        from: 'draft',
        to: 'confirmed',
        label: 'Confirm Order',
        description: 'Mark sales order as confirmed'
      },
      {
        from: 'draft',
        to: 'cancelled',
        label: 'Cancel',
        description: 'Cancel this sales order',
        requiresConfirmation: true
      }
    ],
    isFinal: false
  },
  confirmed: {
    label: 'Confirmed',
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-100 dark:bg-blue-900',
    description: 'Sales order has been confirmed',
    transitions: [
      {
        from: 'confirmed',
        to: 'shipped',
        label: 'Mark Shipped',
        description: 'Mark sales order as shipped'
      },
      {
        from: 'confirmed',
        to: 'cancelled',
        label: 'Cancel',
        description: 'Cancel this sales order',
        requiresConfirmation: true
      }
    ],
    isFinal: false
  },
  shipped: {
    label: 'Shipped',
    color: 'text-yellow-600 dark:text-yellow-400',
    bgColor: 'bg-yellow-100 dark:bg-yellow-900',
    description: 'Sales order has been shipped',
    transitions: [
      {
        from: 'shipped',
        to: 'delivered',
        label: 'Mark Delivered',
        description: 'Mark sales order as delivered'
      },
      {
        from: 'shipped',
        to: 'cancelled',
        label: 'Cancel',
        description: 'Cancel this sales order',
        requiresConfirmation: true
      }
    ],
    isFinal: false
  },
  delivered: {
    label: 'Delivered',
    color: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-100 dark:bg-green-900',
    description: 'Sales order has been delivered',
    transitions: [], // Final state
    isFinal: true
  },
  cancelled: {
    label: 'Cancelled',
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-100 dark:bg-red-900',
    description: 'Sales order has been cancelled',
    transitions: [], // Final state
    isFinal: true
  }
};

export function useSalesOrderStatus(initialStatus: SalesOrderStatus = 'draft') {
  const [currentStatus, setCurrentStatus] = useState<SalesOrderStatus>(initialStatus);

  const getStatusConfig = useCallback((status: SalesOrderStatus) => {
    return STATUS_CONFIG[status];
  }, []);

  const getAvailableTransitions = useCallback((status: SalesOrderStatus) => {
    return STATUS_CONFIG[status].transitions;
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

// Export STATUS_CONFIG separately
export { STATUS_CONFIG };
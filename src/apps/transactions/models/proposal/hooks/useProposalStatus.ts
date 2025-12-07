import { useState, useCallback } from 'react';

export type ProposalStatus = 'planned' | 'sent' | 'accepted' | 'rejected' | 'cancelled';

export interface StatusTransition {
  from: ProposalStatus;
  to: ProposalStatus;
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
const STATUS_CONFIG: Record<ProposalStatus, StatusConfig> = {
  planned: {
    label: 'Planned',
    color: 'text-yellow-600 dark:text-yellow-400',
    bgColor: 'bg-yellow-100 dark:bg-yellow-900',
    description: 'Proposal is being prepared',
    transitions: [
      {
        from: 'planned',
        to: 'sent',
        label: 'Send Proposal',
        description: 'Mark proposal as sent to customer'
      },
      {
        from: 'planned',
        to: 'cancelled',
        label: 'Cancel',
        description: 'Cancel this proposal',
        requiresConfirmation: true
      }
    ],
    isFinal: false
  },
  sent: {
    label: 'Sent',
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-100 dark:bg-blue-900',
    description: 'Proposal has been sent to customer',
    transitions: [
      {
        from: 'sent',
        to: 'accepted',
        label: 'Mark Accepted',
        description: 'Customer has accepted the proposal'
      },
      {
        from: 'sent',
        to: 'rejected',
        label: 'Mark Rejected',
        description: 'Customer has rejected the proposal',
        requiresConfirmation: true
      },
      {
        from: 'sent',
        to: 'cancelled',
        label: 'Cancel',
        description: 'Cancel this proposal',
        requiresConfirmation: true
      }
    ],
    isFinal: false
  },
  accepted: {
    label: 'Accepted',
    color: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-100 dark:bg-green-900',
    description: 'Proposal has been accepted by customer',
    transitions: [], // Final state
    isFinal: true
  },
  rejected: {
    label: 'Rejected',
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-100 dark:bg-red-900',
    description: 'Proposal has been rejected by customer',
    transitions: [
      {
        from: 'rejected',
        to: 'sent',
        label: 'Resend',
        description: 'Send a revised proposal'
      }
    ],
    isFinal: false
  },
  cancelled: {
    label: 'Cancelled',
    color: 'text-gray-600 dark:text-gray-400',
    bgColor: 'bg-gray-100 dark:bg-gray-700',
    description: 'Proposal has been cancelled',
    transitions: [], // Final state
    isFinal: true
  }
};

export function useProposalStatus(initialStatus: ProposalStatus = 'planned') {
  const [currentStatus, setCurrentStatus] = useState<ProposalStatus>(initialStatus);

  const getStatusConfig = useCallback((status: ProposalStatus) => {
    return STATUS_CONFIG[status];
  }, []);

  const getAvailableTransitions = useCallback((status: ProposalStatus) => {
    return STATUS_CONFIG[status].transitions;
  }, []);

  const canTransitionTo = useCallback((fromStatus: ProposalStatus, toStatus: ProposalStatus) => {
    const transitions = getAvailableTransitions(fromStatus);
    return transitions.some(t => t.to === toStatus);
  }, [getAvailableTransitions]);

  const transitionTo = useCallback((newStatus: ProposalStatus) => {
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
        status: 'planned',
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
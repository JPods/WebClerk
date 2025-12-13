import { FaChevronRight, FaClock, FaCheck, FaTruck, FaArchive, FaBan } from 'react-icons/fa';
import { usePurchaseOrderStatus, STATUS_CONFIG } from '../hooks/usePurchaseOrderStatus';
import type { PurchaseOrderStatus, StatusTransition } from '../hooks/usePurchaseOrderStatus';

interface PurchaseOrderStatusProps {
  currentStatus: PurchaseOrderStatus;
  onStatusChange?: (newStatus: PurchaseOrderStatus) => void;
  readonly?: boolean;
  showHistory?: boolean;
}

export default function PurchaseOrderStatus({
  currentStatus,
  onStatusChange,
  readonly = false,
  showHistory = false
}: PurchaseOrderStatusProps) {
  const { getStatusConfig, getAvailableTransitions, getStatusHistory } = usePurchaseOrderStatus(currentStatus);

  const config = getStatusConfig(currentStatus);
  const transitions = getAvailableTransitions(currentStatus);
  const history = getStatusHistory();

  const getStatusIcon = (status: PurchaseOrderStatus) => {
    switch (status) {
      case 'draft':
        return <FaClock className="text-gray-500" />;
      case 'approved':
        return <FaCheck className="text-green-500" />;
      case 'rejected':
        return <FaBan className="text-red-500" />;
      case 'received':
        return <FaTruck className="text-blue-500" />;
      case 'closed':
        return <FaArchive className="text-purple-500" />;
      default:
        return <FaClock className="text-gray-500" />;
    }
  };

  const handleTransition = (transition: StatusTransition) => {
    if (transition.requiresConfirmation) {
      if (!window.confirm(`Are you sure you want to ${transition.label.toLowerCase()}?`)) {
        return;
      }
    }
    if (onStatusChange) {
      onStatusChange(transition.to);
    }
  };

  return (
    <div className="space-y-4">
      {/* Current Status Display */}
      <div className="flex items-center space-x-3">
        <div className={`flex items-center space-x-2 px-3 py-2 rounded-lg ${config.bgColor}`}>
          {getStatusIcon(currentStatus)}
          <span className={`font-medium ${config.color}`}>
            {config.label}
          </span>
        </div>
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {config.description}
        </span>
      </div>

      {/* Status Workflow Visualization */}
      <div className="flex items-center space-x-2 text-sm">
        {Object.keys(STATUS_CONFIG).map((status, index) => {
          const statusConfig = STATUS_CONFIG[status as PurchaseOrderStatus];
          const isActive = status === currentStatus;
          const isPast = Object.keys(STATUS_CONFIG).indexOf(status) < Object.keys(STATUS_CONFIG).indexOf(currentStatus);

          return (
            <div key={status} className="flex items-center space-x-2">
              <div className={`flex items-center space-x-1 px-2 py-1 rounded ${
                isActive ? statusConfig.bgColor :
                isPast ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300' :
                'bg-gray-100 dark:bg-gray-700 text-gray-500'
              }`}>
                {getStatusIcon(status as PurchaseOrderStatus)}
                <span className="text-xs font-medium">{statusConfig.label}</span>
              </div>
              {index < Object.keys(STATUS_CONFIG).length - 1 && (
                <FaChevronRight className={`text-xs ${
                  isPast ? 'text-green-500' : 'text-gray-400'
                }`} />
              )}
            </div>
          );
        })}
      </div>

      {/* Available Transitions */}
      {!readonly && transitions.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-900 dark:text-white">Available Actions</h4>
          <div className="flex flex-wrap gap-2">
            {transitions.map((transition) => (
              <button
                key={transition.to}
                onClick={() => handleTransition(transition)}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  transition.to === 'approved' ? 'bg-green-500 hover:bg-green-600 text-white' :
                  transition.to === 'received' ? 'bg-blue-500 hover:bg-blue-600 text-white' :
                  transition.to === 'closed' ? 'bg-purple-500 hover:bg-purple-600 text-white' :
                  transition.to === 'rejected' ? 'bg-red-500 hover:bg-red-600 text-white' :
                  'bg-gray-500 hover:bg-gray-600 text-white'
                }`}
                title={transition.description}
              >
                {transition.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Status History */}
      {showHistory && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-900 dark:text-white">Status History</h4>
          <div className="space-y-1">
            {history.map((entry, index) => (
              <div key={index} className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
                <div className={`w-2 h-2 rounded-full ${
                  entry.status === 'approved' ? 'bg-green-500' :
                  entry.status === 'received' ? 'bg-blue-500' :
                  entry.status === 'closed' ? 'bg-purple-500' :
                  entry.status === 'rejected' ? 'bg-red-500' :
                  'bg-gray-500'
                }`} />
                <span className="capitalize">{entry.status}</span>
                <span>by {entry.user}</span>
                <span>on {entry.timestamp.toLocaleDateString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
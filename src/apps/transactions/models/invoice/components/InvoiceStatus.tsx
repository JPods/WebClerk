import { FaChevronRight, FaClock, FaCheck, FaDollarSign, FaExclamationTriangle, FaBan } from 'react-icons/fa';
import { useInvoiceStatus, STATUS_CONFIG, STATUS_ORDER, normalizeInvoiceStatus } from '../hooks/useInvoiceStatus';
import type { InvoiceStatus } from '../hooks/useInvoiceStatus';

interface InvoiceStatusProps {
  currentStatus?: string | null;
  onStatusChange?: (newStatus: InvoiceStatus) => void;
  readonly?: boolean;
  showHistory?: boolean;
}

export default function InvoiceStatus({
  currentStatus,
  onStatusChange,
  readonly = false,
  showHistory = false
}: InvoiceStatusProps) {
  const safeStatus = normalizeInvoiceStatus(currentStatus);
  const { getStatusConfig, getAvailableTransitions, getStatusHistory } = useInvoiceStatus(safeStatus);

  const config = getStatusConfig(safeStatus);
  const transitions = getAvailableTransitions(safeStatus);
  const history = getStatusHistory();

  const getStatusIcon = (status: InvoiceStatus) => {
    switch (status) {
      case 'draft':
        return <FaClock className="text-gray-500" />;
      case 'sent':
        return <FaCheck className="text-blue-500" />;
      case 'paid':
        return <FaDollarSign className="text-green-500" />;
      case 'overdue':
        return <FaExclamationTriangle className="text-red-500" />;
      case 'cancelled':
        return <FaBan className="text-red-500" />;
      default:
        return <FaClock className="text-gray-500" />;
    }
  };

  const handleTransition = (transition: any) => {
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
          {getStatusIcon(safeStatus)}
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
          {STATUS_ORDER.map((status, index) => {
          const statusConfig = STATUS_CONFIG[status];
            const isActive = status === safeStatus;
            const isPast = STATUS_ORDER.indexOf(status) < STATUS_ORDER.indexOf(safeStatus);

          return (
            <div key={status} className="flex items-center space-x-2">
                <div className={`flex items-center space-x-1 px-2 py-1 rounded ${
                  isActive ? statusConfig.bgColor :
                  isPast ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300' :
                  'bg-gray-100 dark:bg-gray-700 text-gray-500'
                }`}>
                {getStatusIcon(status as InvoiceStatus)}
                <span className="text-xs font-medium">{statusConfig.label}</span>
              </div>
              {index < STATUS_ORDER.length - 1 && (
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
                  transition.to === 'sent' ? 'bg-blue-500 hover:bg-blue-600 text-white' :
                  transition.to === 'paid' ? 'bg-green-500 hover:bg-green-600 text-white' :
                  transition.to === 'overdue' ? 'bg-red-500 hover:bg-red-600 text-white' :
                  transition.to === 'cancelled' ? 'bg-red-500 hover:bg-red-600 text-white' :
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
                  entry.status === 'paid' ? 'bg-green-500' :
                  entry.status === 'sent' ? 'bg-blue-500' :
                  entry.status === 'overdue' ? 'bg-red-500' :
                  entry.status === 'cancelled' ? 'bg-red-500' :
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
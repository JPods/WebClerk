import {
  FaChevronRight,
  FaClock,
  FaCheck,
  FaTruck,
  FaBox,
  FaBan,
  FaPlay,
  FaPause,
  FaCheckCircle,
} from "react-icons/fa";
import {
  useOrderStatus,
  STATUS_CONFIG,
} from "../hooks/useOrderStatus";
import type { OrderStatus as OrderStatusType } from "../hooks/useOrderStatus";

interface OrderStatusProps {
  currentStatus: OrderStatusType;
  onStatusChange?: (newStatus: OrderStatusType) => void;
  readonly?: boolean;
  showHistory?: boolean;
}

export default function OrderStatus({
  currentStatus,
  onStatusChange,
  readonly = false,
  showHistory = false,
}: OrderStatusProps) {
  const { getStatusConfig, getAvailableTransitions, getStatusHistory } =
    useOrderStatus(currentStatus);

  const config = getStatusConfig(currentStatus);
  const transitions = getAvailableTransitions(currentStatus);
  const history = getStatusHistory();

  const getStatusIcon = (status: OrderStatusType) => {
    switch (status) {
      // Backend statuses
      case "planned":
        return <FaClock className="text-gray-500" />;
      case "released":
        return <FaPlay className="text-blue-500" />;
      case "in_progress":
        return <FaTruck className="text-yellow-500" />;
      case "hold":
        return <FaPause className="text-orange-500" />;
      case "complete":
        return <FaCheckCircle className="text-green-500" />;
      case "canceled":
        return <FaBan className="text-red-500" />;
      // Legacy statuses
      case "draft":
        return <FaClock className="text-gray-500" />;
      case "confirmed":
        return <FaCheck className="text-blue-500" />;
      case "shipped":
        return <FaTruck className="text-yellow-500" />;
      case "delivered":
        return <FaBox className="text-green-500" />;
      case "cancelled":
        return <FaBan className="text-red-500" />;
      default:
        return <FaClock className="text-gray-500" />;
    }
  };

  const handleTransition = (transition: any) => {
    if (transition.requiresConfirmation) {
      if (
        !window.confirm(
          `Are you sure you want to ${transition.label.toLowerCase()}?`,
        )
      ) {
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
        <div
          className={`flex items-center space-x-2 px-3 py-2 text-xs  rounded-lg ${config.bgColor}`}
        >
          {getStatusIcon(currentStatus)}
          <span className={`${config.color}`}>{config.label}</span>
        </div>
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {config.description}
        </span>
      </div>

      {/* Status Workflow Visualization */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {Object.keys(STATUS_CONFIG).map((status, index) => {
          const statusConfig = STATUS_CONFIG[status as OrderStatusType];
          const isActive = status === currentStatus;
          const isPast =
            Object.keys(STATUS_CONFIG).indexOf(status) <
            Object.keys(STATUS_CONFIG).indexOf(currentStatus);

          return (
            <div key={status} className="flex items-center space-x-2">
              <div
                className={`flex items-center space-x-1 px-2 py-1 rounded ${
                  isActive
                    ? statusConfig.bgColor
                    : isPast
                    ? "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300"
                    : "bg-gray-100 dark:bg-gray-700 text-gray-500"
                }`}
              >
                {getStatusIcon(status as OrderStatusType)}
                <span className="text-xs font-medium">
                  {statusConfig.label}
                </span>
              </div>
              {index < Object.keys(STATUS_CONFIG).length - 1 && (
                <FaChevronRight
                  className={`text-xs ${
                    isPast ? "text-green-500" : "text-gray-400"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Available Transitions */}
      {!readonly && transitions.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-900 dark:text-white">
            Available Actions
          </h4>
          <div className="flex flex-wrap gap-2">
            {transitions.map((transition) => (
              <button
                key={transition.to}
                onClick={() => handleTransition(transition)}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  transition.to === "confirmed"
                    ? "bg-blue-500 hover:bg-blue-600 text-white"
                    : transition.to === "shipped"
                    ? "bg-yellow-500 hover:bg-yellow-600 text-white"
                    : transition.to === "delivered"
                    ? "bg-green-500 hover:bg-green-600 text-white"
                    : transition.to === "cancelled"
                    ? "bg-red-500 hover:bg-red-600 text-white"
                    : "bg-gray-500 hover:bg-gray-600 text-white"
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
          <h4 className="text-sm font-medium text-gray-900 dark:text-white">
            Status History
          </h4>
          <div className="space-y-1">
            {history.map((entry, index) => (
              <div
                key={index}
                className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400"
              >
                <div
                  className={`w-2 h-2 rounded-full ${
                    entry.status === "delivered"
                      ? "bg-green-500"
                      : entry.status === "shipped"
                      ? "bg-yellow-500"
                      : entry.status === "confirmed"
                      ? "bg-blue-500"
                      : entry.status === "cancelled"
                      ? "bg-red-500"
                      : "bg-gray-500"
                  }`}
                />
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

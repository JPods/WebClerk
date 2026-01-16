/**
 * ActivityLogTab - Shows transaction history and audit log
 * Displays timeline of changes, actions, and events
 */
import React, { useState } from 'react';
import { 
  FaHistory, 
  FaUser, 
  FaEdit, 
  FaPrint, 
  FaEnvelope, 
  FaShoppingCart,
  FaTruck,
  FaCheck,
  FaPlus,
  FaTrash,
  FaFilter,
  FaClock,
  FaExclamationTriangle
} from 'react-icons/fa';

// Activity types
type ActivityType = 
  | 'created' 
  | 'updated' 
  | 'line_added' 
  | 'line_removed' 
  | 'line_modified'
  | 'status_changed' 
  | 'printed' 
  | 'emailed' 
  | 'shipped'
  | 'payment_received'
  | 'note_added'
  | 'contact_added';

interface ActivityLogEntry {
  id: number;
  type: ActivityType;
  timestamp: string;
  user: string;
  description: string;
  details?: Record<string, unknown>;
  changes?: {
    field: string;
    from: string | number;
    to: string | number;
  }[];
}

interface ActivityLogTabProps {
  transactionId?: number;
  activities?: ActivityLogEntry[];
  isLoading?: boolean;
}

// Icon mapping for activity types
const activityIcons: Record<ActivityType, React.ElementType> = {
  created: FaPlus,
  updated: FaEdit,
  line_added: FaShoppingCart,
  line_removed: FaTrash,
  line_modified: FaEdit,
  status_changed: FaCheck,
  printed: FaPrint,
  emailed: FaEnvelope,
  shipped: FaTruck,
  payment_received: FaCheck,
  note_added: FaEdit,
  contact_added: FaUser,
};

// Color mapping for activity types
const activityColors: Record<ActivityType, string> = {
  created: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
  updated: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
  line_added: 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400',
  line_removed: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
  line_modified: 'bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400',
  status_changed: 'bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400',
  printed: 'bg-slate-100 text-slate-600 dark:bg-slate-900/30 dark:text-slate-400',
  emailed: 'bg-cyan-100 text-cyan-600 dark:bg-cyan-900/30 dark:text-cyan-400',
  shipped: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400',
  payment_received: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
  note_added: 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400',
  contact_added: 'bg-pink-100 text-pink-600 dark:bg-pink-900/30 dark:text-pink-400',
};

// Demo activities for display
const demoActivities: ActivityLogEntry[] = [
  {
    id: 1,
    type: 'created',
    timestamp: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    user: 'John Smith',
    description: 'Order created',
  },
  {
    id: 2,
    type: 'line_added',
    timestamp: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000 + 300000).toISOString(),
    user: 'John Smith',
    description: 'Added line item: WIDGET-001 x 10',
  },
  {
    id: 3,
    type: 'line_added',
    timestamp: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000 + 600000).toISOString(),
    user: 'John Smith',
    description: 'Added line item: GADGET-002 x 5',
  },
  {
    id: 4,
    type: 'emailed',
    timestamp: new Date(Date.now() - 6 * 24 * 60 * 60 * 1000).toISOString(),
    user: 'System',
    description: 'Quote emailed to customer@example.com',
  },
  {
    id: 5,
    type: 'status_changed',
    timestamp: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    user: 'Jane Doe',
    description: 'Status changed from Quote to Order',
    changes: [{ field: 'status', from: 'Quote', to: 'Order' }],
  },
  {
    id: 6,
    type: 'line_modified',
    timestamp: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    user: 'Jane Doe',
    description: 'Modified line item: WIDGET-001',
    changes: [{ field: 'quantity', from: 10, to: 15 }],
  },
  {
    id: 7,
    type: 'printed',
    timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    user: 'Jane Doe',
    description: 'Order confirmation printed',
  },
  {
    id: 8,
    type: 'shipped',
    timestamp: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
    user: 'Warehouse',
    description: 'Partial shipment: Tracking #12345',
    details: { tracking: '12345', carrier: 'UPS' },
  },
];

const ActivityLogTab: React.FC<ActivityLogTabProps> = ({
  transactionId: _transactionId, // For future API integration
  activities = demoActivities,
  isLoading = false,
}) => {
  const [filter, setFilter] = useState<ActivityType | 'all'>('all');
  const [expandedEntries, setExpandedEntries] = useState<Set<number>>(new Set());

  // Filter activities
  const filteredActivities = filter === 'all' 
    ? activities 
    : activities.filter(a => a.type === filter);

  // Group by date
  const groupedByDate = filteredActivities.reduce<Record<string, ActivityLogEntry[]>>((acc, activity) => {
    const date = new Date(activity.timestamp).toLocaleDateString();
    if (!acc[date]) acc[date] = [];
    acc[date].push(activity);
    return acc;
  }, {});

  // Format timestamp
  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // Format relative time
  const formatRelativeTime = (timestamp: string) => {
    const diff = Date.now() - new Date(timestamp).getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return 'Just now';
  };

  // Toggle entry expansion
  const toggleExpand = (id: number) => {
    const newExpanded = new Set(expandedEntries);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedEntries(newExpanded);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-slate-500 dark:text-slate-400">Loading activity log...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with filter */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FaHistory className="text-slate-400" />
          <h3 className="text-lg font-medium text-slate-900 dark:text-white">Activity Log</h3>
          <span className="px-2 py-0.5 text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-full">
            {activities.length} entries
          </span>
        </div>
        
        {/* Filter dropdown */}
        <div className="flex items-center gap-2">
          <FaFilter className="text-slate-400" size={12} />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as ActivityType | 'all')}
            className="text-sm px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Activities</option>
            <optgroup label="Document">
              <option value="created">Created</option>
              <option value="updated">Updated</option>
              <option value="status_changed">Status Changed</option>
            </optgroup>
            <optgroup label="Lines">
              <option value="line_added">Line Added</option>
              <option value="line_removed">Line Removed</option>
              <option value="line_modified">Line Modified</option>
            </optgroup>
            <optgroup label="Communication">
              <option value="printed">Printed</option>
              <option value="emailed">Emailed</option>
            </optgroup>
            <optgroup label="Fulfillment">
              <option value="shipped">Shipped</option>
              <option value="payment_received">Payment</option>
            </optgroup>
          </select>
        </div>
      </div>

      {/* Empty state */}
      {filteredActivities.length === 0 && (
        <div className="text-center py-12 bg-slate-50 dark:bg-slate-900/50 rounded-lg">
          <FaExclamationTriangle className="mx-auto text-slate-300 dark:text-slate-600 mb-3" size={32} />
          <p className="text-slate-500 dark:text-slate-400">No activities found</p>
          {filter !== 'all' && (
            <button
              onClick={() => setFilter('all')}
              className="mt-2 text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400"
            >
              Clear filter
            </button>
          )}
        </div>
      )}

      {/* Timeline */}
      <div className="space-y-6">
        {Object.entries(groupedByDate).map(([date, dayActivities]) => (
          <div key={date}>
            {/* Date header */}
            <div className="flex items-center gap-3 mb-3">
              <div className="flex items-center gap-2 px-3 py-1 bg-slate-100 dark:bg-slate-800 rounded-full">
                <FaClock className="text-slate-400" size={12} />
                <span className="text-sm font-medium text-slate-600 dark:text-slate-300">{date}</span>
              </div>
              <div className="flex-1 h-px bg-slate-200 dark:bg-slate-700"></div>
            </div>

            {/* Day's activities */}
            <div className="relative pl-6 space-y-4">
              {/* Vertical line */}
              <div className="absolute left-3 top-2 bottom-2 w-px bg-slate-200 dark:bg-slate-700"></div>

              {dayActivities.map((activity) => {
                const Icon = activityIcons[activity.type];
                const colorClass = activityColors[activity.type];
                const isExpanded = expandedEntries.has(activity.id);
                const hasDetails = activity.changes || activity.details;

                return (
                  <div 
                    key={activity.id} 
                    className="relative flex items-start gap-4"
                  >
                    {/* Icon */}
                    <div className={`absolute -left-3 p-2 rounded-full ${colorClass}`}>
                      <Icon size={12} />
                    </div>

                    {/* Content */}
                    <div 
                      className={`flex-1 ml-4 p-3 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 ${hasDetails ? 'cursor-pointer hover:border-blue-300 dark:hover:border-blue-600' : ''}`}
                      onClick={() => hasDetails && toggleExpand(activity.id)}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="text-sm font-medium text-slate-900 dark:text-white">
                            {activity.description}
                          </p>
                          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                            by {activity.user}
                          </p>
                        </div>
                        <div className="text-right">
                          <span className="text-xs text-slate-500 dark:text-slate-400">
                            {formatTime(activity.timestamp)}
                          </span>
                          <span className="block text-xs text-slate-400 dark:text-slate-500">
                            {formatRelativeTime(activity.timestamp)}
                          </span>
                        </div>
                      </div>

                      {/* Expanded details */}
                      {isExpanded && activity.changes && (
                        <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700">
                          <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2">Changes:</p>
                          <div className="space-y-1">
                            {activity.changes.map((change, idx) => (
                              <div key={idx} className="text-xs flex items-center gap-2">
                                <span className="text-slate-500 dark:text-slate-400">{change.field}:</span>
                                <span className="text-red-500 line-through">{String(change.from)}</span>
                                <span className="text-slate-400">→</span>
                                <span className="text-green-600 dark:text-green-400">{String(change.to)}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {isExpanded && activity.details && (
                        <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700">
                          <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2">Details:</p>
                          <pre className="text-xs text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-900/50 p-2 rounded overflow-auto">
                            {JSON.stringify(activity.details, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ActivityLogTab;

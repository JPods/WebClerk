import React, { useState } from 'react';
import { useAuditTrail } from '../../../hooks/useAuditTrail';

export interface AuditTrailProps {
  transactionId: number;
  model: string;
  className?: string;
}

export const AuditTrail: React.FC<AuditTrailProps> = ({
  transactionId,
  model,
  className = '',
}) => {
  const { trail, loading } = useAuditTrail(transactionId, model);
  const [showAll, setShowAll] = useState(false);

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const getActionColor = (action: string) => {
    switch (action.toLowerCase()) {
      case 'created':
        return 'text-green-600 bg-green-100';
      case 'updated':
        return 'text-blue-600 bg-blue-100';
      case 'deleted':
        return 'text-red-600 bg-red-100';
      case 'status_changed':
        return 'text-yellow-600 bg-yellow-100';
      case 'converted':
        return 'text-purple-600 bg-purple-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const displayedTrail = showAll ? trail : trail.slice(0, 5);

  if (loading) {
    return (
      <div className={`audit-trail ${className}`}>
        <div className="flex items-center justify-center p-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-gray-600">Loading audit trail...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`audit-trail bg-white border rounded-lg ${className}`}>
      <div className="p-4 border-b bg-gray-50">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-800">Audit Trail</h3>
          <button
            onClick={() => setShowAll(!showAll)}
            className="text-sm text-blue-600 hover:text-blue-800 underline"
          >
            {showAll ? 'Show Less' : `Show All (${trail.length})`}
          </button>
        </div>
      </div>

      <div className="max-h-96 overflow-y-auto">
        {displayedTrail.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            No audit entries found
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {displayedTrail.map((entry) => (
              <div key={entry.id} className="p-4 hover:bg-gray-50">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getActionColor(entry.action)}`}>
                        {entry.action.replace('_', ' ').toUpperCase()}
                      </span>
                      <span className="text-sm text-gray-500">
                        {formatTimestamp(entry.timestamp)}
                      </span>
                    </div>

                    {entry.user_name && (
                      <div className="text-sm text-gray-600 mb-2">
                        by {entry.user_name}
                      </div>
                    )}

                    {entry.details && Object.keys(entry.details).length > 0 && (
                      <div className="bg-gray-50 p-3 rounded text-sm">
                        <div className="font-medium text-gray-700 mb-1">Changes:</div>
                        <div className="space-y-1">
                          {Object.entries(entry.details).map(([key, value]) => (
                            <div key={key} className="flex justify-between">
                              <span className="text-gray-600">{key.replace(/([A-Z])/g, ' $1').toLowerCase()}:</span>
                              <span className="font-medium text-gray-800">
                                {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {entry.ip_address && (
                    <div className="text-xs text-gray-400 ml-4">
                      {entry.ip_address}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {trail.length > 5 && !showAll && (
        <div className="p-3 bg-gray-50 border-t text-center">
          <button
            onClick={() => setShowAll(true)}
            className="text-sm text-blue-600 hover:text-blue-800 underline"
          >
            View {trail.length - 5} more entries
          </button>
        </div>
      )}
    </div>
  );
};
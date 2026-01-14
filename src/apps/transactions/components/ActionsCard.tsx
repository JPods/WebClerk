/**
 * ActionsCard - Display and manage transaction action/next-action
 */
import React from 'react';
import { FaUser, FaClock, FaCheck, FaExclamationTriangle, FaBan, FaEdit } from 'react-icons/fa';
import type { TransactionActions } from '../types/transactionTypes';
import FieldLabel from './FieldLabel';

interface ActionsCardProps {
  actions: TransactionActions | undefined;
  isEditing?: boolean;
  onChange?: (actions: TransactionActions) => void;
}

const statusConfig = {
  pending: { label: 'Pending', icon: FaClock, color: 'text-amber-500', bg: 'bg-amber-100 dark:bg-amber-900/30' },
  done: { label: 'Done', icon: FaCheck, color: 'text-green-500', bg: 'bg-green-100 dark:bg-green-900/30' },
  blocked: { label: 'Blocked', icon: FaBan, color: 'text-red-500', bg: 'bg-red-100 dark:bg-red-900/30' },
};

const ActionsCard: React.FC<ActionsCardProps> = ({
  actions = {},
  isEditing = false,
  onChange,
}) => {
  const status = actions?.status || 'pending';
  const config = statusConfig[status] || statusConfig.pending;
  const StatusIcon = config.icon;

  const handleChange = (field: keyof TransactionActions, value: unknown) => {
    if (onChange) {
      onChange({ ...actions, [field]: value });
    }
  };

  const handleActionNextChange = (field: 'who' | 'when' | 'what', value: string | number) => {
    if (onChange) {
      const actionNext = actions?.action_next || {};
      onChange({
        ...actions,
        action_next: { ...actionNext, [field]: value },
      });
    }
  };

  const formatDate = (timestamp?: number): string => {
    if (!timestamp) return '';
    return new Date(timestamp).toLocaleDateString();
  };

  const parseDate = (dateStr: string): number => {
    const date = new Date(dateStr);
    return isNaN(date.getTime()) ? 0 : date.getTime();
  };

  return (
    <div className="space-y-4">
      {/* Status Badge */}
      <div className="flex items-center gap-3">
        <FieldLabel label="Status" />
        {isEditing ? (
          <select
            value={status}
            onChange={(e) => handleChange('status', e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-800"
          >
            <option value="pending">Pending</option>
            <option value="done">Done</option>
            <option value="blocked">Blocked</option>
          </select>
        ) : (
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.bg} ${config.color}`}>
            <StatusIcon size={12} />
            {config.label}
          </span>
        )}
      </div>

      {/* Required Flag */}
      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={actions?.required || false}
            onChange={(e) => handleChange('required', e.target.checked)}
            disabled={!isEditing}
            className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
          />
          <span className="text-sm text-slate-700 dark:text-slate-300">
            Action Required
            {actions?.required && <FaExclamationTriangle className="inline ml-1 text-amber-500" size={12} />}
          </span>
        </label>
      </div>

      {/* Action Kind */}
      <div>
        <FieldLabel label="Action Type" />
        {isEditing ? (
          <select
            value={actions?.kind || ''}
            onChange={(e) => handleChange('kind', e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-800"
          >
            <option value="">-- Select --</option>
            <option value="followup">Follow Up</option>
            <option value="review">Review</option>
            <option value="ship">Ship</option>
            <option value="approve">Approve</option>
            <option value="call">Call</option>
            <option value="email">Email</option>
          </select>
        ) : (
          <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">
            {actions?.kind ? actions.kind.charAt(0).toUpperCase() + actions.kind.slice(1) : '--'}
          </p>
        )}
      </div>

      {/* What */}
      <div>
        <FieldLabel label="Description" />
        {isEditing ? (
          <textarea
            value={actions?.what || ''}
            onChange={(e) => handleChange('what', e.target.value)}
            rows={2}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-800"
            placeholder="What needs to be done..."
          />
        ) : (
          <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">
            {actions?.what || '--'}
          </p>
        )}
      </div>

      {/* Next Action Section */}
      <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
          Next Action
        </h4>
        
        <div className="grid gap-4 md:grid-cols-3">
          {/* Who */}
          <div>
            <FieldLabel label="Assigned To" />
            {isEditing ? (
              <div className="relative mt-1">
                <FaUser className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={12} />
                <input
                  type="text"
                  value={actions?.action_next?.who || ''}
                  onChange={(e) => handleActionNextChange('who', e.target.value)}
                  className="w-full rounded-lg border border-slate-300 pl-8 pr-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-800"
                  placeholder="Name or ID"
                />
              </div>
            ) : (
              <p className="mt-1 text-sm text-slate-700 dark:text-slate-300 flex items-center gap-2">
                <FaUser size={12} className="text-slate-400" />
                {actions?.action_next?.who || '--'}
              </p>
            )}
          </div>

          {/* When */}
          <div>
            <FieldLabel label="Due Date" />
            {isEditing ? (
              <div className="relative mt-1">
                <FaClock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={12} />
                <input
                  type="date"
                  value={actions?.action_next?.when ? new Date(actions.action_next.when).toISOString().split('T')[0] : ''}
                  onChange={(e) => handleActionNextChange('when', parseDate(e.target.value))}
                  className="w-full rounded-lg border border-slate-300 pl-8 pr-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-800"
                />
              </div>
            ) : (
              <p className="mt-1 text-sm text-slate-700 dark:text-slate-300 flex items-center gap-2">
                <FaClock size={12} className="text-slate-400" />
                {actions?.action_next?.when ? formatDate(actions.action_next.when) : '--'}
              </p>
            )}
          </div>

          {/* What */}
          <div>
            <FieldLabel label="Task" />
            {isEditing ? (
              <input
                type="text"
                value={actions?.action_next?.what || ''}
                onChange={(e) => handleActionNextChange('what', e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-800"
                placeholder="Task description"
              />
            ) : (
              <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">
                {actions?.action_next?.what || '--'}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ActionsCard;

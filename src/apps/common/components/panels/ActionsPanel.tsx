/**
 * ActionsPanel - Display and manage entity .actions (next steps / tasks)
 * 
 * Based on Django ActionsMixin schema:
 * {
 *   required: boolean,
 *   status: "pending" | "done" | "blocked",
 *   who: number | string,
 *   when: number (ms epoch),
 *   what: string,
 *   kind: "followup" | "review" | "ship" | "approve" | etc.,
 *   extra: { ... }
 * }
 * 
 * Role-based access:
 * - View: All roles (default)
 * - Edit: User+ roles (default)
 */
import React, { useState } from 'react';
import { 
  FaTasks, FaChevronDown, FaChevronUp, FaPlus, FaEdit, FaTrash, 
  FaCheck, FaClock, FaBan, FaExclamationTriangle,
  FaPhone, FaEnvelope, FaClipboardCheck, FaTruck, FaThumbsUp
} from 'react-icons/fa';
import { usePermissions } from './usePermissions';
import type { BasePanelProps, ActionEntry, ActionStatus, ActionKind } from './types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ActionsPanelProps extends Omit<BasePanelProps<ActionEntry | ActionEntry[]>, 'data'> {
  /** Actions data - single action or array */
  data?: ActionEntry | ActionEntry[];
  /** Whether to show as list (multiple) or single action card */
  mode?: 'single' | 'list';
}

// ---------------------------------------------------------------------------
// Status & Kind Helpers
// ---------------------------------------------------------------------------

const STATUS_CONFIG: Record<ActionStatus, { icon: React.ReactNode; color: string; bg: string }> = {
  pending: { icon: <FaClock size={12} />, color: 'text-amber-600', bg: 'bg-amber-100 dark:bg-amber-900/30' },
  in_progress: { icon: <FaTasks size={12} />, color: 'text-blue-600', bg: 'bg-blue-100 dark:bg-blue-900/30' },
  completed: { icon: <FaCheck size={12} />, color: 'text-green-600', bg: 'bg-green-100 dark:bg-green-900/30' },
  cancelled: { icon: <FaBan size={12} />, color: 'text-slate-500', bg: 'bg-slate-100 dark:bg-slate-700' },
  on_hold: { icon: <FaExclamationTriangle size={12} />, color: 'text-orange-600', bg: 'bg-orange-100 dark:bg-orange-900/30' },
};

const KIND_ICONS: Record<ActionKind, React.ReactNode> = {
  task: <FaTasks size={12} />,
  followup: <FaClock size={12} />,
  call: <FaPhone size={12} />,
  email: <FaEnvelope size={12} />,
  review: <FaClipboardCheck size={12} />,
  approve: <FaThumbsUp size={12} />,
  ship: <FaTruck size={12} />,
  other: <FaTasks size={12} />,
};

const formatDate = (ts: number | string | undefined): string => {
  if (!ts) return '--';
  const date = typeof ts === 'number' ? new Date(ts) : new Date(ts);
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
};

// ---------------------------------------------------------------------------
// Action Card Component
// ---------------------------------------------------------------------------

interface ActionCardProps {
  action: ActionEntry;
  canEdit: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
  onStatusChange?: (status: ActionStatus) => void;
  compact?: boolean;
}

const ActionCard: React.FC<ActionCardProps> = ({ 
  action, 
  canEdit, 
  onEdit, 
  onDelete,
  onStatusChange,
  compact = false 
}) => {
  const status = action.status || 'pending';
  const kind = action.kind || 'task';
  const statusConfig = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  const kindIcon = KIND_ICONS[kind] || KIND_ICONS.task;

  const isOverdue = action.when && new Date(action.when) < new Date() && status !== 'completed';

  return (
    <div className={`border rounded-lg ${statusConfig.bg} border-slate-200 dark:border-slate-600 ${compact ? 'p-2' : 'p-3'}`}>
      <div className="flex items-start gap-3">
        {/* Kind icon */}
        <div className={`p-2 rounded ${statusConfig.color}`}>
          {kindIcon}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Header row */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`px-2 py-0.5 text-xs rounded font-medium ${statusConfig.color} ${statusConfig.bg}`}>
              {statusConfig.icon}
              <span className="ml-1 capitalize">{status.replace('_', ' ')}</span>
            </span>
            <span className="text-xs text-slate-500 capitalize">{kind}</span>
            {action.priority && action.priority !== 'normal' && (
              <span className={`px-1.5 py-0.5 text-xs rounded ${
                action.priority === 'urgent' ? 'bg-red-100 text-red-700' :
                action.priority === 'high' ? 'bg-orange-100 text-orange-700' :
                'bg-slate-100 text-slate-600'
              }`}>
                {action.priority}
              </span>
            )}
          </div>

          {/* Description */}
          <p className={`text-sm text-slate-700 dark:text-slate-300 mt-1 ${compact ? 'line-clamp-1' : ''}`}>
            {action.what || 'No description'}
          </p>

          {/* Meta row */}
          <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
            {action.who && (
              <span>Assigned: {action.who}</span>
            )}
            {action.when && (
              <span className={isOverdue ? 'text-red-600 font-medium' : ''}>
                Due: {formatDate(action.when)}
                {isOverdue && ' (overdue)'}
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        {canEdit && (
          <div className="flex items-center gap-1">
            {status !== 'completed' && onStatusChange && (
              <button
                onClick={() => onStatusChange('completed')}
                className="p-1.5 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded"
                title="Mark complete"
              >
                <FaCheck size={12} />
              </button>
            )}
            {onEdit && (
              <button
                onClick={onEdit}
                className="p-1.5 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
                title="Edit"
              >
                <FaEdit size={12} />
              </button>
            )}
            {onDelete && (
              <button
                onClick={onDelete}
                className="p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                title="Delete"
              >
                <FaTrash size={12} />
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Action Edit Modal
// ---------------------------------------------------------------------------

interface ActionEditModalProps {
  isOpen: boolean;
  action?: ActionEntry;
  onClose: () => void;
  onSave: (action: ActionEntry) => void;
}

const ActionEditModal: React.FC<ActionEditModalProps> = ({ isOpen, action, onClose, onSave }) => {
  const [formData, setFormData] = useState<ActionEntry>(action || {
    kind: 'task',
    status: 'pending',
    priority: 'normal',
    what: '',
    who: '',
  });

  React.useEffect(() => {
    if (action) {
      setFormData(action);
    } else {
      setFormData({
        kind: 'task',
        status: 'pending',
        priority: 'normal',
        what: '',
        who: '',
      });
    }
  }, [action, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-800 rounded-lg p-4 w-96 max-w-full mx-4">
        <h3 className="text-sm font-semibold mb-4 text-slate-700 dark:text-slate-200">
          {action ? 'Edit Action' : 'Add Action'}
        </h3>
        
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Type</label>
            <select
              value={formData.kind || 'task'}
              onChange={(e) => setFormData({ ...formData, kind: e.target.value as ActionKind })}
              className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
            >
              <option value="task">Task</option>
              <option value="followup">Follow Up</option>
              <option value="call">Call</option>
              <option value="email">Email</option>
              <option value="review">Review</option>
              <option value="approve">Approve</option>
              <option value="ship">Ship</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div>
            <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Description</label>
            <textarea
              value={formData.what || ''}
              onChange={(e) => setFormData({ ...formData, what: e.target.value })}
              className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
              rows={2}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Assigned To</label>
              <input
                type="text"
                value={formData.who || ''}
                onChange={(e) => setFormData({ ...formData, who: e.target.value })}
                className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Due Date</label>
              <input
                type="date"
                value={formData.when ? new Date(formData.when).toISOString().split('T')[0] : ''}
                onChange={(e) => setFormData({ ...formData, when: e.target.value ? new Date(e.target.value).getTime() : undefined })}
                className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Status</label>
              <select
                value={formData.status || 'pending'}
                onChange={(e) => setFormData({ ...formData, status: e.target.value as ActionStatus })}
                className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
              >
                <option value="pending">Pending</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="on_hold">On Hold</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Priority</label>
              <select
                value={formData.priority || 'normal'}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value as ActionEntry['priority'] })}
                className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
              >
                <option value="low">Low</option>
                <option value="normal">Normal</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-2 mt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700 rounded"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main ActionsPanel Component
// ---------------------------------------------------------------------------

const ActionsPanel: React.FC<ActionsPanelProps> = ({
  entityType: _entityType,
  entityId: _entityId,
  data,
  onChange,
  readOnly = false,
  viewRoles,
  editRoles,
  className = '',
  compact = false,
  title = 'Actions',
  defaultCollapsed = false,
  mode = 'list',
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [showModal, setShowModal] = useState(false);
  const [editingAction, setEditingAction] = useState<ActionEntry | undefined>();

  // Check permissions
  const { canView, canEdit: permCanEdit } = usePermissions({
    panelType: 'actions',
    viewRoles,
    editRoles,
    forceReadOnly: readOnly,
  });

  const canEdit = permCanEdit && !!onChange;

  if (!canView) return null;

  // Normalize to array
  const actions: ActionEntry[] = Array.isArray(data) 
    ? data 
    : (data && Object.keys(data).length > 0 ? [data] : []);

  const pendingCount = actions.filter(a => a.status === 'pending' || !a.status).length;
  const hasRequired = actions.some(a => (a as ActionEntry & { required?: boolean }).required);

  const handleAdd = () => {
    setEditingAction(undefined);
    setShowModal(true);
  };

  const handleEdit = (action: ActionEntry, index: number) => {
    setEditingAction({ ...action, id: action.id || index });
    setShowModal(true);
  };

  const handleDelete = (index: number) => {
    if (!onChange) return;
    const newActions = actions.filter((_, i) => i !== index);
    onChange(mode === 'single' ? (newActions[0] || {}) : newActions);
  };

  const handleStatusChange = (index: number, status: ActionStatus) => {
    if (!onChange) return;
    const newActions = [...actions];
    newActions[index] = { ...newActions[index], status };
    if (status === 'completed') {
      newActions[index].completed_at = new Date().toISOString();
    }
    onChange(mode === 'single' ? newActions[0] : newActions);
  };

  const handleSave = (action: ActionEntry) => {
    if (!onChange) return;
    
    if (editingAction?.id !== undefined) {
      // Update existing
      const index = typeof editingAction.id === 'number' ? editingAction.id : actions.findIndex(a => a.id === editingAction.id);
      const newActions = [...actions];
      newActions[index] = { ...action, id: editingAction.id };
      onChange(mode === 'single' ? newActions[0] : newActions);
    } else {
      // Add new
      const newAction = { ...action, id: Date.now(), created_at: new Date().toISOString() };
      onChange(mode === 'single' ? newAction : [...actions, newAction]);
    }
  };

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-lg border border-emerald-200 dark:border-emerald-800 ${className}`}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-emerald-50 dark:bg-emerald-900/20 border-b border-emerald-200 dark:border-emerald-800 cursor-pointer rounded-t-lg"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaTasks className="text-emerald-500" size={14} />
          <h3 className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">{title}</h3>
          {pendingCount > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 rounded-full">
              {pendingCount} pending
            </span>
          )}
          {hasRequired && (
            <span className="px-1.5 py-0.5 text-xs bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded">
              Required
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {canEdit && !isCollapsed && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleAdd();
              }}
              className="p-1 text-emerald-600 hover:bg-emerald-100 dark:hover:bg-emerald-800 rounded"
              title="Add action"
            >
              <FaPlus size={12} />
            </button>
          )}
          {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
        </div>
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className={`${compact ? 'p-2' : 'p-4'} space-y-2`}>
          {actions.length === 0 ? (
            <div className="text-center py-4 text-slate-400 text-sm">
              <FaTasks size={24} className="mx-auto mb-2 opacity-50" />
              <p>No actions defined</p>
              {canEdit && (
                <button
                  onClick={handleAdd}
                  className="mt-2 text-emerald-600 hover:underline text-xs"
                >
                  + Add first action
                </button>
              )}
            </div>
          ) : (
            actions.map((action, index) => (
              <ActionCard
                key={action.id || index}
                action={action}
                canEdit={canEdit}
                compact={compact}
                onEdit={() => handleEdit(action, index)}
                onDelete={() => handleDelete(index)}
                onStatusChange={(status) => handleStatusChange(index, status)}
              />
            ))
          )}
        </div>
      )}

      {/* Edit Modal */}
      <ActionEditModal
        isOpen={showModal}
        action={editingAction}
        onClose={() => setShowModal(false)}
        onSave={handleSave}
      />
    </div>
  );
};

export default ActionsPanel;

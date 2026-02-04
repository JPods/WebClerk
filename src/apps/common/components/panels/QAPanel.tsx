/**
 * QAPanel - Display and manage Q&A entries
 * 
 * Role-based access:
 * - View: All roles (default)
 * - Edit: User+ roles (default)
 */
import React, { useState } from 'react';
import { 
  FaQuestionCircle, FaChevronDown, FaChevronUp, FaPlus, 
  FaEdit, FaTrash, FaCheck, FaClock
} from 'react-icons/fa';
import { usePermissions } from './usePermissions';
import type { BasePanelProps, QAEntry } from './types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface QAPanelProps extends Omit<BasePanelProps<QAEntry[]>, 'data'> {
  /** Q&A entries array */
  data?: QAEntry[];
}

// ---------------------------------------------------------------------------
// Q&A Item Component
// ---------------------------------------------------------------------------

interface QAItemProps {
  entry: QAEntry;
  canEdit: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
  onAnswer?: (answer: string) => void;
  compact?: boolean;
}

const QAItem: React.FC<QAItemProps> = ({ 
  entry, 
  canEdit, 
  onEdit, 
  onDelete, 
  onAnswer,
  compact = false 
}) => {
  const [isExpanded, setIsExpanded] = useState(!entry.answer);
  const [answerText, setAnswerText] = useState('');
  const [showAnswerInput, setShowAnswerInput] = useState(false);

  const status = entry.status || (entry.answer ? 'answered' : 'open');
  const statusColor = {
    open: 'text-amber-600 bg-amber-100 dark:bg-amber-900/30',
    answered: 'text-green-600 bg-green-100 dark:bg-green-900/30',
    closed: 'text-slate-500 bg-slate-100 dark:bg-slate-700',
  }[status];

  const handleSubmitAnswer = () => {
    if (answerText.trim() && onAnswer) {
      onAnswer(answerText.trim());
      setAnswerText('');
      setShowAnswerInput(false);
    }
  };

  return (
    <div className={`border rounded-lg border-slate-200 dark:border-slate-600 ${compact ? 'p-2' : 'p-3'}`}>
      {/* Question header */}
      <div 
        className="flex items-start gap-2 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <FaQuestionCircle className="text-blue-500 mt-0.5 flex-shrink-0" size={14} />
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-medium text-slate-700 dark:text-slate-300 ${!isExpanded && 'line-clamp-1'}`}>
            {entry.question}
          </p>
          <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
            <span className={`px-1.5 py-0.5 rounded ${statusColor}`}>
              {status === 'answered' ? <FaCheck size={8} className="inline mr-1" /> : <FaClock size={8} className="inline mr-1" />}
              {status}
            </span>
            {entry.asked_by && <span>by {entry.asked_by}</span>}
            {entry.asked_at && <span>{new Date(entry.asked_at).toLocaleDateString()}</span>}
          </div>
        </div>
        <div className="flex items-center gap-1">
          {canEdit && onEdit && (
            <button
              onClick={(e) => { e.stopPropagation(); onEdit(); }}
              className="p-1 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
            >
              <FaEdit size={12} />
            </button>
          )}
          {canEdit && onDelete && (
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(); }}
              className="p-1 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
            >
              <FaTrash size={12} />
            </button>
          )}
          {isExpanded ? <FaChevronUp size={12} /> : <FaChevronDown size={12} />}
        </div>
      </div>

      {/* Answer section */}
      {isExpanded && (
        <div className="mt-3 ml-6 pl-3 border-l-2 border-green-200 dark:border-green-800">
          {entry.answer ? (
            <div>
              <p className="text-sm text-slate-600 dark:text-slate-400">{entry.answer}</p>
              {(entry.answered_by || entry.answered_at) && (
                <p className="text-xs text-slate-400 mt-1">
                  {entry.answered_by && `Answered by ${entry.answered_by}`}
                  {entry.answered_at && ` on ${new Date(entry.answered_at).toLocaleDateString()}`}
                </p>
              )}
            </div>
          ) : showAnswerInput ? (
            <div className="space-y-2">
              <textarea
                value={answerText}
                onChange={(e) => setAnswerText(e.target.value)}
                placeholder="Type your answer..."
                className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                rows={2}
                autoFocus
              />
              <div className="flex gap-2">
                <button
                  onClick={handleSubmitAnswer}
                  disabled={!answerText.trim()}
                  className="px-2 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
                >
                  Submit Answer
                </button>
                <button
                  onClick={() => setShowAnswerInput(false)}
                  className="px-2 py-1 text-xs text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 rounded"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="text-sm text-slate-400 italic">
              No answer yet
              {canEdit && onAnswer && (
                <button
                  onClick={() => setShowAnswerInput(true)}
                  className="ml-2 text-blue-600 hover:underline"
                >
                  Add answer
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Add Question Modal
// ---------------------------------------------------------------------------

interface AddQuestionModalProps {
  isOpen: boolean;
  entry?: QAEntry;
  onClose: () => void;
  onSave: (entry: QAEntry) => void;
}

const AddQuestionModal: React.FC<AddQuestionModalProps> = ({ isOpen, entry, onClose, onSave }) => {
  const [question, setQuestion] = useState(entry?.question || '');
  const [answer, setAnswer] = useState(entry?.answer || '');

  React.useEffect(() => {
    setQuestion(entry?.question || '');
    setAnswer(entry?.answer || '');
  }, [entry, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      ...entry,
      question,
      answer: answer || undefined,
      asked_at: entry?.asked_at || new Date().toISOString(),
      asked_by: entry?.asked_by || 'current_user',
      status: answer ? 'answered' : 'open',
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-800 rounded-lg p-4 w-96 max-w-full mx-4">
        <h3 className="text-sm font-semibold mb-4 text-slate-700 dark:text-slate-200">
          {entry ? 'Edit Q&A' : 'Add Question'}
        </h3>
        
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Question</label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
              rows={2}
              required
              autoFocus
            />
          </div>

          <div>
            <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Answer (optional)</label>
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
              rows={2}
            />
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
// Main QAPanel Component
// ---------------------------------------------------------------------------

const QAPanel: React.FC<QAPanelProps> = ({
  entityType: _entityType,
  entityId: _entityId,
  data = [],
  onChange,
  readOnly = false,
  viewRoles,
  editRoles,
  className = '',
  compact = false,
  title = 'Q&A',
  defaultCollapsed = false,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [showModal, setShowModal] = useState(false);
  const [editingEntry, setEditingEntry] = useState<QAEntry | undefined>();

  // Check permissions
  const { canView, canEdit: permCanEdit } = usePermissions({
    panelType: 'qa',
    viewRoles,
    editRoles,
    forceReadOnly: readOnly,
  });

  const canEdit = permCanEdit && !!onChange;

  if (!canView) return null;

  const openCount = data.filter(e => e.status === 'open' || (!e.status && !e.answer)).length;

  const handleAdd = () => {
    setEditingEntry(undefined);
    setShowModal(true);
  };

  const handleEdit = (entry: QAEntry, index: number) => {
    setEditingEntry({ ...entry, id: entry.id || index });
    setShowModal(true);
  };

  const handleDelete = (index: number) => {
    if (!onChange) return;
    onChange(data.filter((_, i) => i !== index));
  };

  const handleAnswer = (index: number, answer: string) => {
    if (!onChange) return;
    const newData = [...data];
    newData[index] = {
      ...newData[index],
      answer,
      answered_at: new Date().toISOString(),
      answered_by: 'current_user',
      status: 'answered',
    };
    onChange(newData);
  };

  const handleSave = (entry: QAEntry) => {
    if (!onChange) return;
    
    if (editingEntry?.id !== undefined) {
      const index = typeof editingEntry.id === 'number' ? editingEntry.id : data.findIndex(e => e.id === editingEntry.id);
      const newData = [...data];
      newData[index] = { ...entry, id: editingEntry.id };
      onChange(newData);
    } else {
      onChange([...data, { ...entry, id: Date.now() }]);
    }
  };

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-lg border border-indigo-200 dark:border-indigo-800 ${className}`}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-indigo-50 dark:bg-indigo-900/20 border-b border-indigo-200 dark:border-indigo-800 cursor-pointer rounded-t-lg"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaQuestionCircle className="text-indigo-500" size={14} />
          <h3 className="text-sm font-semibold text-indigo-700 dark:text-indigo-300">{title}</h3>
          {data.length > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-300 rounded-full">
              {data.length}
            </span>
          )}
          {openCount > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 rounded">
              {openCount} open
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
              className="p-1 text-indigo-600 hover:bg-indigo-100 dark:hover:bg-indigo-800 rounded"
              title="Add question"
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
          {data.length === 0 ? (
            <div className="text-center py-4 text-slate-400 text-sm">
              <FaQuestionCircle size={24} className="mx-auto mb-2 opacity-50" />
              <p>No questions yet</p>
              {canEdit && (
                <button
                  onClick={handleAdd}
                  className="mt-2 text-indigo-600 hover:underline text-xs"
                >
                  + Add first question
                </button>
              )}
            </div>
          ) : (
            data.map((entry, index) => (
              <QAItem
                key={entry.id || index}
                entry={entry}
                canEdit={canEdit}
                compact={compact}
                onEdit={() => handleEdit(entry, index)}
                onDelete={() => handleDelete(index)}
                onAnswer={canEdit ? (answer) => handleAnswer(index, answer) : undefined}
              />
            ))
          )}
        </div>
      )}

      {/* Modal */}
      <AddQuestionModal
        isOpen={showModal}
        entry={editingEntry}
        onClose={() => setShowModal(false)}
        onSave={handleSave}
      />
    </div>
  );
};

export default QAPanel;

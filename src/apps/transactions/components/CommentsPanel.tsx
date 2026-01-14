/**
 * CommentsPanel - Display and edit transaction comments
 * Tabs: Public | Process | Partner | History (notes)
 */
import React, { useState } from 'react';
import { FaComment, FaCog, FaHandshake, FaHistory, FaPlus } from 'react-icons/fa';
import type { TransactionComments, CommentEntry } from '../types/transactionTypes';

interface CommentsPanelProps {
  comments: TransactionComments | undefined;
  isEditing?: boolean;
  onChange?: (comments: TransactionComments) => void;
}

type TabKey = 'public' | 'process' | 'partner' | 'notes';

const TabButton: React.FC<{
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  count?: number;
}> = ({ active, onClick, icon, label, count }) => (
  <button
    onClick={onClick}
    className={`flex items-center gap-2 px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
      active
        ? 'border-blue-500 text-blue-600 dark:text-blue-400'
        : 'border-transparent text-slate-600 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
    }`}
  >
    {icon}
    {label}
    {count !== undefined && count > 0 && (
      <span className="ml-1 px-1.5 py-0.5 text-xs bg-slate-200 dark:bg-slate-700 rounded-full">
        {count}
      </span>
    )}
  </button>
);

const CommentTextArea: React.FC<{
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
  placeholder: string;
  label: string;
}> = ({ value, onChange, disabled, placeholder, label }) => (
  <div>
    <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
      {label}
    </label>
    <textarea
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      placeholder={placeholder}
      rows={4}
      className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-700"
    />
  </div>
);

const NotesHistory: React.FC<{
  notes: CommentEntry[];
  isEditing: boolean;
  onAdd?: () => void;
}> = ({ notes, isEditing, onAdd }) => {
  if (notes.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500 dark:text-slate-400">
        <FaHistory size={24} className="mx-auto mb-2 opacity-50" />
        <p className="text-sm">No notes recorded</p>
        {isEditing && onAdd && (
          <button
            onClick={onAdd}
            className="mt-2 text-blue-500 hover:text-blue-600 text-sm flex items-center gap-1 mx-auto"
          >
            <FaPlus size={10} /> Add Note
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {isEditing && onAdd && (
        <button
          onClick={onAdd}
          className="text-blue-500 hover:text-blue-600 text-sm flex items-center gap-1"
        >
          <FaPlus size={10} /> Add Note
        </button>
      )}
      {notes.map((note, idx) => (
        <div
          key={idx}
          className="border-l-2 border-slate-300 dark:border-slate-600 pl-3 py-1"
        >
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <span>{note.ts ? new Date(note.ts).toLocaleString() : 'Unknown date'}</span>
            <span>•</span>
            <span>{note.by || 'Unknown'}</span>
            {note.source && (
              <>
                <span>•</span>
                <span className="italic">{note.source}</span>
              </>
            )}
          </div>
          <p className="text-sm text-slate-700 dark:text-slate-300 mt-1">
            {note.text}
          </p>
        </div>
      ))}
    </div>
  );
};

const CommentsPanel: React.FC<CommentsPanelProps> = ({
  comments = {},
  isEditing = false,
  onChange,
}) => {
  const [activeTab, setActiveTab] = useState<TabKey>('public');

  const handleFieldChange = (field: 'public' | 'process' | 'partner', value: string) => {
    if (onChange) {
      onChange({ ...comments, [field]: value });
    }
  };

  const handleAddNote = () => {
    if (onChange) {
      const newNote: CommentEntry = {
        ts: new Date().toISOString(),
        by: 'current_user', // TODO: Get from auth context
        text: '',
      };
      const currentNotes = comments?.notes || [];
      onChange({ ...comments, notes: [...currentNotes, newNote] });
    }
  };

  const notesCount = comments?.notes?.length || 0;

  return (
    <div className="space-y-4">
      {/* Tab Navigation */}
      <div className="flex border-b border-slate-200 dark:border-slate-700">
        <TabButton
          active={activeTab === 'public'}
          onClick={() => setActiveTab('public')}
          icon={<FaComment size={12} />}
          label="Public"
        />
        <TabButton
          active={activeTab === 'process'}
          onClick={() => setActiveTab('process')}
          icon={<FaCog size={12} />}
          label="Process"
        />
        <TabButton
          active={activeTab === 'partner'}
          onClick={() => setActiveTab('partner')}
          icon={<FaHandshake size={12} />}
          label="Partner"
        />
        <TabButton
          active={activeTab === 'notes'}
          onClick={() => setActiveTab('notes')}
          icon={<FaHistory size={12} />}
          label="History"
          count={notesCount}
        />
      </div>

      {/* Tab Content */}
      <div className="min-h-[150px]">
        {activeTab === 'public' && (
          <CommentTextArea
            value={comments?.public || ''}
            onChange={(v) => handleFieldChange('public', v)}
            disabled={!isEditing}
            placeholder="Customer-visible notes..."
            label="Public Comment (visible to customer)"
          />
        )}
        {activeTab === 'process' && (
          <CommentTextArea
            value={comments?.process || ''}
            onChange={(v) => handleFieldChange('process', v)}
            disabled={!isEditing}
            placeholder="Internal process notes..."
            label="Process Notes (internal only)"
          />
        )}
        {activeTab === 'partner' && (
          <CommentTextArea
            value={comments?.partner || ''}
            onChange={(v) => handleFieldChange('partner', v)}
            disabled={!isEditing}
            placeholder="Partner/vendor notes..."
            label="Partner Notes (shared with vendors)"
          />
        )}
        {activeTab === 'notes' && (
          <NotesHistory
            notes={comments?.notes || []}
            isEditing={isEditing}
            onAdd={isEditing ? handleAddNote : undefined}
          />
        )}
      </div>
    </div>
  );
};

export default CommentsPanel;

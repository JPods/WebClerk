/**
 * CommentsPanel - Generic comments panel with tabs (Public | Process | Partner | History)
 * 
 * Role-based access:
 * - View: All roles (default)
 * - Edit: User+ roles (default), Admin can override
 * 
 * @example
 * <CommentsPanel
 *   entityType="contact"
 *   entityId={123}
 *   data={contact.comments}
 *   onChange={(comments) => setContact({ ...contact, comments })}
 * />
 */
import React, { useState, useRef, useEffect } from 'react';
import { FaComment, FaCog, FaHandshake, FaHistory, FaChevronDown, FaChevronUp } from 'react-icons/fa';
import { Input } from '@/components/wrapper';
import { usePermissions } from './usePermissions';
import type { BasePanelProps, EntityComments, CommentEntry } from './types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CommentsPanelProps extends Omit<BasePanelProps<EntityComments>, 'data'> {
  /** Comments data structure */
  data?: EntityComments;
  /** Message to display (e.g., save status) */
  message?: string;
}

type TabKey = 'public' | 'process' | 'partner' | 'notes';

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  count?: number;
}

const TabButton: React.FC<TabButtonProps> = ({ active, onClick, icon, label, count }) => (
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

// ---------------------------------------------------------------------------
// Notes History Component
// ---------------------------------------------------------------------------

interface NotesHistoryProps {
  notes: CommentEntry[];
  canEdit: boolean;
  onAdd?: (noteText: string) => void;
  message?: string;
}

const NotesHistory: React.FC<NotesHistoryProps> = ({ notes, canEdit, onAdd, message }) => {
  const [inputValue, setInputValue] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [notes.length]);

  const handleSend = () => {
    if (inputValue.trim() && onAdd) {
      onAdd(inputValue.trim());
      setInputValue('');
    }
  };

  return (
    <div className="flex flex-col h-64 bg-slate-100 dark:bg-slate-900 rounded">
      {message && (
        <div className="mb-2 px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs text-center">
          {message}
        </div>
      )}
      
      <div
        ref={scrollRef}
        className="flex-1 h-64 overflow-y-auto border rounded bg-success-50 dark:bg-slate-800 mb-2 pr-1 space-y-3"
      >
        {notes.length === 0 && (
          <div className="text-center py-8 text-slate-500 dark:text-slate-400">
            <FaHistory size={24} className="mx-auto mb-2 opacity-50" />
            <p className="text-sm">No notes recorded</p>
          </div>
        )}
        {notes.map((note, idx) => (
          <div
            key={note.id || idx}
            className={`mb-2 px-2 py-1 ${
              idx !== notes.length - 1 ? 'border-b border-purple-100 dark:border-slate-700' : ''
            }`}
          >
            <div className="flex items-center gap-2 mb-1 text-xs text-slate-500 dark:text-white font-medium">
              <span>{note.by === 'current_user' ? 'You' : note.by || 'Unknown'}</span>
              <span>•</span>
              <span>
                {note.ts
                  ? new Date(note.ts).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                      year: 'numeric',
                      month: 'short',
                      day: '2-digit',
                    })
                  : 'Unknown'}
              </span>
              {note.source && (
                <>
                  <span>•</span>
                  <span
                    className={`italic ${
                      note.source === 'Public'
                        ? 'text-blue-700 dark:text-blue-300'
                        : note.source === 'Process'
                        ? 'text-green-700 dark:text-green-300'
                        : note.source === 'Partner'
                        ? 'text-purple-700 dark:text-purple-300'
                        : 'text-slate-700 dark:text-white'
                    }`}
                  >
                    {note.source}
                  </span>
                </>
              )}
            </div>
            <div
              className={`text-sm break-words font-medium ${
                note.source === 'Public'
                  ? 'text-blue-700 dark:text-blue-300'
                  : note.source === 'Process'
                  ? 'text-green-700 dark:text-green-300'
                  : note.source === 'Partner'
                  ? 'text-purple-700 dark:text-purple-300'
                  : 'text-slate-700 dark:text-white'
              }`}
            >
              {note.text}
            </div>
          </div>
        ))}
      </div>
      
      {canEdit && (
        <div className="flex gap-2 p-2 bg-purple-200 dark:bg-slate-800 border-t border-purple-200 dark:border-slate-700 rounded-b">
          <Input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Type a note..."
            className="flex-1 rounded border border-purple-300 px-3 py-2 text-sm focus:border-purple-500 focus:ring-1 focus:ring-purple-500 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && inputValue.trim()) {
                handleSend();
              }
            }}
          />
          <button
            className="px-3 py-2 rounded bg-blue-500 text-white text-sm font-semibold hover:bg-blue-600 disabled:opacity-50"
            onClick={handleSend}
            disabled={!inputValue.trim()}
          >
            Send
          </button>
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Tab With Input Component
// ---------------------------------------------------------------------------

interface TabWithInputProps {
  value: string;
  onChange: (value: string) => void;
  canEdit: boolean;
  label: string;
  placeholder: string;
  tabKey: TabKey;
  onAddHistory?: (entry: CommentEntry) => void;
}

const TabWithInput: React.FC<TabWithInputProps> = ({
  value,
  onChange,
  canEdit,
  label,
  placeholder,
  tabKey,
  onAddHistory,
}) => {
  const [inputValue, setInputValue] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  // Parse messages with timestamp delimiter
  const messages = value
    ? value
        .split(/\n/)
        .filter(Boolean)
        .map((line) => {
          const [text, ts] = line.split('|||');
          return { text, ts };
        })
    : [];

  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages.length]);

  const handleSend = () => {
    if (inputValue.trim()) {
      const now = new Date();
      const ts = now.toLocaleString([], {
        hour: '2-digit',
        minute: '2-digit',
        year: 'numeric',
        month: 'short',
        day: '2-digit',
      });
      const line = `${inputValue.trim()}|||${ts}`;
      onChange(value ? value + '\n' + line : line);
      setInputValue('');
      
      if (onAddHistory) {
        onAddHistory({
          ts: now.toISOString(),
          by: 'current_user',
          text: inputValue.trim(),
          source: (tabKey.charAt(0).toUpperCase() + tabKey.slice(1)) as CommentEntry['source'],
        });
      }
    }
  };

  const colorClass = {
    public: 'text-blue-700 dark:text-blue-300',
    process: 'text-green-700 dark:text-green-300',
    partner: 'text-purple-700 dark:text-purple-300',
    notes: 'text-slate-700 dark:text-white',
  }[tabKey];

  return (
    <div className="flex flex-col h-64">
      <label className="block text-xs font-medium text-slate-700 dark:text-slate-400 mb-1">
        {label}
      </label>
      
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto border rounded bg-purple-50 dark:bg-slate-800 mb-2 pr-1"
      >
        <div className={`text-sm px-2 py-1 ${colorClass}`}>
          {messages.length === 0 ? (
            <span className="text-slate-400">No messages yet.</span>
          ) : (
            messages.map((msg, idx) => (
              <div key={idx} className="mb-2">
                <span>{msg.text}</span>
                {msg.ts && <span className="ml-2 text-xs text-slate-500">{msg.ts}</span>}
              </div>
            ))
          )}
        </div>
      </div>
      
      {canEdit && (
        <div className="flex gap-2 p-2 bg-success-50 dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700 rounded-b">
          <Input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={placeholder}
            className="flex-1 rounded border border-success-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-success-500 bg-white dark:border-slate-600 dark:bg-slate-700 dark:text-white"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && inputValue.trim()) {
                handleSend();
              }
            }}
          />
          <button
            className="px-3 py-2 rounded bg-blue-500 text-white text-sm font-semibold hover:bg-blue-600 disabled:opacity-50"
            onClick={handleSend}
            disabled={!inputValue.trim()}
          >
            Send
          </button>
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main CommentsPanel Component
// ---------------------------------------------------------------------------

/**
 * CommentsPanel - Display and edit comments with tabs
 * 
 * Tabs:
 * - Public: Customer-visible notes
 * - Process: Internal process notes
 * - Partner: Vendor/partner notes
 * - History: Chronological log of all notes
 */
const CommentsPanel: React.FC<CommentsPanelProps> = ({
  entityType: _entityType,
  entityId: _entityId,
  data = {},
  onChange,
  readOnly = false,
  viewRoles,
  editRoles,
  className = '',
  compact = false,
  title = 'Comments',
  defaultCollapsed = false,
  message,
}) => {
  const [activeTab, setActiveTab] = useState<TabKey>('public');
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);

  // Check permissions
  const { canView, canEdit: permCanEdit, isAdmin } = usePermissions({
    panelType: 'comments',
    viewRoles,
    editRoles,
    forceReadOnly: readOnly,
  });

  const canEdit = permCanEdit && !!onChange;

  // Local state for tab values
  const [localTabValues, setLocalTabValues] = useState({
    public: (data?.public as unknown as string) || '',
    process: (data?.process as unknown as string) || '',
    partner: (data?.partner as unknown as string) || '',
  });

  // Sync with data prop
  useEffect(() => {
    setLocalTabValues({
      public: (data?.public as unknown as string) || '',
      process: (data?.process as unknown as string) || '',
      partner: (data?.partner as unknown as string) || '',
    });
  }, [data?.public, data?.process, data?.partner]);

  // Don't render if user can't view
  if (!canView) return null;

  const handleFieldChange = (field: 'public' | 'process' | 'partner', value: string) => {
    setLocalTabValues((prev) => ({ ...prev, [field]: value }));
    if (onChange) {
      onChange({ ...data, [field]: value } as EntityComments);
    }
  };

  const handleAddNote = (noteText: string, source?: string) => {
    if (onChange && noteText.trim()) {
      const newNote: CommentEntry = {
        ts: new Date().toISOString(),
        by: 'current_user', // TODO: Get from auth context
        text: noteText.trim(),
        source: source as CommentEntry['source'],
      };
      const currentNotes = data?.notes || [];
      onChange({ ...data, notes: [...currentNotes, newNote] });
    }
  };

  const notesCount = data?.notes?.length || 0;

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 ${className}`}>
      {/* Header with collapse toggle */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700 cursor-pointer"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaComment className="text-slate-400" size={14} />
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">{title}</h3>
          {notesCount > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded-full">
              {notesCount}
            </span>
          )}
          {isAdmin && (
            <span className="px-1.5 py-0.5 text-xs bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 rounded">
              Admin
            </span>
          )}
        </div>
        {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className={`p-4 ${compact ? 'space-y-2' : 'space-y-4'}`}>
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
          <div className={compact ? 'min-h-32' : 'min-h-40'}>
            {activeTab === 'public' && (
              <TabWithInput
                value={localTabValues.public}
                onChange={(v) => handleFieldChange('public', v)}
                canEdit={canEdit}
                label="Public Comment (visible to customer)"
                placeholder="Customer-visible notes..."
                tabKey="public"
                onAddHistory={(entry) => handleAddNote(entry.text, entry.source)}
              />
            )}
            {activeTab === 'process' && (
              <TabWithInput
                value={localTabValues.process}
                onChange={(v) => handleFieldChange('process', v)}
                canEdit={canEdit}
                label="Process Notes (internal only)"
                placeholder="Internal process notes..."
                tabKey="process"
                onAddHistory={(entry) => handleAddNote(entry.text, entry.source)}
              />
            )}
            {activeTab === 'partner' && (
              <TabWithInput
                value={localTabValues.partner}
                onChange={(v) => handleFieldChange('partner', v)}
                canEdit={canEdit}
                label="Partner Notes (shared with vendors)"
                placeholder="Partner/vendor notes..."
                tabKey="partner"
                onAddHistory={(entry) => handleAddNote(entry.text, entry.source)}
              />
            )}
            {activeTab === 'notes' && (
              <NotesHistory
                notes={data?.notes || []}
                canEdit={canEdit}
                onAdd={canEdit ? (note) => handleAddNote(note) : undefined}
                message={message}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CommentsPanel;

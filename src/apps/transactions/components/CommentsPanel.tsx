/**
 * CommentsPanel - Display and edit transaction comments
 * Tabs: Public | Process | Partner | History (notes)
 */
import React, { useState } from "react";
import { FaComment, FaCog, FaHandshake, FaHistory } from "react-icons/fa";
import type {
  TransactionComments,
  CommentEntry,
} from "../types/transactionTypes";
import { Input } from "@/components/wrapper";

interface CommentsPanelProps {
  comments: TransactionComments | undefined;
  isEditing?: boolean;
  onChange?: (comments: TransactionComments) => void;
}

type TabKey = "public" | "process" | "partner" | "notes";

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
        ? "border-blue-500 text-blue-600 dark:text-blue-400"
        : "border-transparent text-slate-600 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
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

interface MessageInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled: boolean;
  placeholder: string;
}

// MessageInput is unused, so it can be removed.

interface NotesHistoryProps {
  notes: CommentEntry[];
  isEditing: boolean;
  onAdd?: (noteText?: string) => void;
  message?: string;
}

const NotesHistory: React.FC<NotesHistoryProps> = ({
  notes,
  isEditing,
  onAdd,
  message,
}) => {
  const [inputValue, setInputValue] = React.useState("");
  const scrollRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [notes.length]);

  return (
    <div className="flex flex-col h-64">
      {/* Message display */}
      {message && (
        <div className="mb-2 px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs text-center">
          {message}
        </div>
      )}
      {/* Notes history container */}
      <div
        ref={scrollRef}
        className="flex-1 h-64 overflow-y-scroll border rounded bg-slate-50 dark:bg-slate-800 mb-2 pr-1 space-y-3"
      >
        {notes.length === 0 && (
          <div className="text-center py-8 text-slate-500 dark:text-slate-400">
            <FaHistory size={24} className="mx-auto mb-2 opacity-50" />
            <p className="text-sm">No notes recorded</p>
          </div>
        )}
        {notes.map((note, idx) => (
          <div
            key={idx}
            className="mb-2 px-2 py-1 border-b border-slate-200 dark:border-slate-700"
          >
            <div className="flex items-center gap-2 mb-1 text-xs text-slate-700 dark:text-white font-medium">
              <span>
                {note.by === "current_user" ? "You" : note.by || "Unknown"}
              </span>
              <span>•</span>
              <span>
                {note.ts
                  ? new Date(note.ts).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  : "Unknown"}
              </span>
              {note.source && (
                <>
                  <span>•</span>
                  <span
                    className={`italic ${
                      note.source === "Public"
                        ? "text-blue-700 dark:text-blue-300"
                        : note.source === "Process"
                        ? "text-green-700 dark:text-green-300"
                        : note.source === "Partner"
                        ? "text-purple-700 dark:text-purple-300"
                        : "text-slate-700 dark:text-white"
                    }`}
                  >
                    {note.source}
                  </span>
                </>
              )}
            </div>
            <div
              className={`text-sm break-words font-normal ${
                note.source === "Public"
                  ? "text-blue-700 dark:text-blue-300"
                  : note.source === "Process"
                  ? "text-green-700 dark:text-green-300"
                  : note.source === "Partner"
                  ? "text-purple-700 dark:text-purple-300"
                  : "text-slate-700 dark:text-white"
              }`}
            >
              {note.text}
            </div>
          </div>
        ))}
      </div>
      {/* Input area container */}
      {isEditing && (
        <div className="flex gap-2 p-2 bg-white dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700 rounded-b">
          <Input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Type a note..."
            className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
            onKeyDown={(e) => {
              if (e.key === "Enter" && inputValue.trim()) {
                if (onAdd) {
                  onAdd(inputValue.trim());
                  setInputValue("");
                }
              }
            }}
            disabled={!isEditing}
          />
          <button
            className="px-3 py-2 rounded bg-blue-500 text-white text-sm font-semibold hover:bg-blue-600 disabled:opacity-50"
            onClick={() => {
              if (inputValue.trim() && onAdd) {
                onAdd(inputValue.trim());
                setInputValue("");
              }
            }}
            disabled={!inputValue.trim()}
          >
            Send
          </button>
        </div>
      )}
    </div>
  );
};

// WhatsApp-like input for public, process, partner tabs
interface TabWithInputProps {
  value: string;
  onChange: (value: string) => void;
  isEditing: boolean;
  label: string;
  placeholder: string;
}

const TabWithInput: React.FC<
  TabWithInputProps & {
    tabKey: TabKey;
    onAddHistory?: (entry: CommentEntry) => void;
  }
> = ({
  value,
  onChange,
  isEditing,
  label,
  placeholder,
  tabKey,
  onAddHistory,
}) => {
  const [inputValue, setInputValue] = React.useState("");
  const scrollRef = React.useRef<HTMLDivElement>(null);

  // Always render messages from value prop
  // Store and display timestamps for each message using delimiter
  const messages = value
    ? value
        .split(/\n/)
        .filter(Boolean)
        .map((line) => {
          const [text, ts] = line.split("|||");
          return { text, ts };
        })
    : [];

  React.useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages.length]);

  const handleSend = () => {
    if (inputValue.trim()) {
      const now = new Date();
      const ts = now.toLocaleString([], {
        hour: "2-digit",
        minute: "2-digit",
        year: "numeric",
        month: "short",
        day: "2-digit",
      });
      const line = `${inputValue.trim()}|||${ts}`;
      onChange(value ? value + "\n" + line : line);
      setInputValue("");
      if (onAddHistory) {
        onAddHistory({
          ts: now.toISOString(),
          by: "current_user",
          text: inputValue.trim(),
          source: tabKey.charAt(0).toUpperCase() + tabKey.slice(1),
        });
      }
    }
  };

  return (
    <div className="flex flex-col h-64">
      <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
        {label}
      </label>
      {/* Message history container */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-scroll border rounded bg-slate-50 dark:bg-slate-800 mb-2 pr-1"
      >
        <div
          className={`text-sm px-2 py-1 ${
            tabKey === "public"
              ? "text-blue-700 dark:text-blue-300"
              : tabKey === "process"
              ? "text-green-700 dark:text-green-300"
              : tabKey === "partner"
              ? "text-purple-700 dark:text-purple-300"
              : "text-slate-700 dark:text-white"
          }`}
        >
          {messages.length === 0 ? (
            <span className="text-slate-400">No messages yet.</span>
          ) : (
            messages.map((msg, idx) => (
              <div key={idx} className="mb-2">
                <span>{msg.text}</span>
                {msg.ts && (
                  <span className="ml-2 text-xs text-slate-400">{msg.ts}</span>
                )}
              </div>
            ))
          )}
        </div>
      </div>
      {/* Input area container */}
      {isEditing && (
        <div className="flex gap-2 p-2 bg-white dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700 rounded-b">
          <Input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={placeholder}
            className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
            onKeyDown={(e) => {
              if (e.key === "Enter" && inputValue.trim()) {
                handleSend();
              }
            }}
            disabled={!isEditing}
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

interface CommentsPanelProps {
  comments: TransactionComments | undefined;
  isEditing?: boolean;
  onChange?: (comments: TransactionComments) => void;
  message?: string;
}

const CommentsPanel: React.FC<CommentsPanelProps> = ({
  comments = {},
  isEditing = false,
  onChange,
  message,
}) => {
  const [activeTab, setActiveTab] = useState<TabKey>("public");

  // Local fallback state for tab messages
  const [localTabValues, setLocalTabValues] = useState({
    public: comments?.public || "",
    process: comments?.process || "",
    partner: comments?.partner || "",
  });

  // Sync local state with comments prop if it changes
  React.useEffect(() => {
    setLocalTabValues({
      public: comments?.public || "",
      process: comments?.process || "",
      partner: comments?.partner || "",
    });
  }, [comments?.public, comments?.process, comments?.partner]);

  const handleFieldChange = (
    field: "public" | "process" | "partner",
    value: string,
  ) => {
    setLocalTabValues((prev) => ({ ...prev, [field]: value }));
    if (onChange) {
      onChange({ ...comments, [field]: value });
    }
  };

  const handleAddNote = (noteText?: string, source?: string) => {
    if (onChange && noteText && noteText.trim()) {
      const newNote: CommentEntry = {
        ts: new Date().toISOString(),
        by: "current_user", // TODO: Get from auth context
        text: noteText.trim(),
        source,
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
          active={activeTab === "public"}
          onClick={() => setActiveTab("public")}
          icon={<FaComment size={12} />}
          label="Public"
        />
        <TabButton
          active={activeTab === "process"}
          onClick={() => setActiveTab("process")}
          icon={<FaCog size={12} />}
          label="Process"
        />
        <TabButton
          active={activeTab === "partner"}
          onClick={() => setActiveTab("partner")}
          icon={<FaHandshake size={12} />}
          label="Partner"
        />
        <TabButton
          active={activeTab === "notes"}
          onClick={() => setActiveTab("notes")}
          icon={<FaHistory size={12} />}
          label="History"
          count={notesCount}
        />
      </div>

      {/* Tab Content */}
      <div className="min-h-40">
        {/* Public Tab */}
        {activeTab === "public" && (
          <TabWithInput
            value={localTabValues.public}
            onChange={(v) => handleFieldChange("public", v)}
            isEditing={isEditing}
            label="Public Comment (visible to customer)"
            placeholder="Customer-visible notes..."
            tabKey="public"
            onAddHistory={(entry) => handleAddNote(entry.text, entry.source)}
          />
        )}
        {/* Process Tab */}
        {activeTab === "process" && (
          <TabWithInput
            value={localTabValues.process}
            onChange={(v) => handleFieldChange("process", v)}
            isEditing={isEditing}
            label="Process Notes (internal only)"
            placeholder="Internal process notes..."
            tabKey="process"
            onAddHistory={(entry) => handleAddNote(entry.text, entry.source)}
          />
        )}
        {/* Partner Tab */}
        {activeTab === "partner" && (
          <TabWithInput
            value={localTabValues.partner}
            onChange={(v) => handleFieldChange("partner", v)}
            isEditing={isEditing}
            label="Partner Notes (shared with vendors)"
            placeholder="Partner/vendor notes..."
            tabKey="partner"
            onAddHistory={(entry) => handleAddNote(entry.text, entry.source)}
          />
        )}
        {/* Notes Tab */}
        {activeTab === "notes" && (
          <NotesHistory
            notes={comments?.notes || []}
            isEditing={isEditing}
            onAdd={
              isEditing ? (note) => handleAddNote(note, undefined) : undefined
            }
            message={message}
          />
        )}
      </div>
    </div>
  );
};

export default CommentsPanel;

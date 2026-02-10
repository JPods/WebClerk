/**
 * CommentsPanel - Generic comments panel with CRUD operations
 * Tabs: Public | Process | Partner | Notes
 * Structure: {notes: [], public: [], process: [], partner: []}
 * Each array contains: {user, mgs, time, user_id?}
 *
 * Role-based access:
 * - View: All roles (default)
 * - Edit: User+ roles (default), Admin can override
 *
 * @example
 * <CommentsPanel
 *   entityType="contact"
 *   entityId={123}
 *   comments={contact.comments}
 *   isEditing={true}
 *   onChange={(comments) => setContact({ ...contact, comments })}
 *   onSave={saveComments}
 *   currentUser="John Doe"
 * />
 */
import React, { useState, useRef, useEffect } from "react";
import {
  FaComment,
  FaCog,
  FaHandshake,
  FaEdit,
  FaTrash,
  FaChevronDown,
  FaChevronUp,
} from "react-icons/fa";
import { Input } from "../../../../components/wrapper";
import { usePermissions } from "./usePermissions";
import type {
  BasePanelProps,
  EntityComments,
  CommentMessage,
  RawEntityComments,
} from "./types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CommentsPanelProps
  extends Omit<BasePanelProps<EntityComments>, "data" | "onChange"> {
  /** Comments data structure (may have strings instead of arrays from API) */
  comments?: RawEntityComments;
  /** Whether editing is enabled */
  isEditing?: boolean;
  /** Callback when comments change (local state update) */
  onChange?: (comments: EntityComments) => void;
  /** Callback to persist comments to the database (auto-save) */
  onSave?: (comments: EntityComments) => Promise<void>;
  /** Current user's display name */
  currentUser?: string;
  /** Current user's ID */
  currentUserId?: number | string;
  /** Message to display (e.g., save status) */
  message?: string;
}

type TabKey = "public" | "process" | "partner" | "notes";

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

const TabButton: React.FC<TabButtonProps> = ({
  active,
  onClick,
  icon,
  label,
  count,
}) => (
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

// ---------------------------------------------------------------------------
// CommentList Component - Displays messages with CRUD operations
// ---------------------------------------------------------------------------

interface CommentListProps {
  messages: CommentMessage[];
  tabKey: TabKey;
  isEditing: boolean;
  onAdd: (message: CommentMessage) => void;
  onDelete: (index: number) => void;
  onEdit?: (index: number, message: CommentMessage) => void;
  currentUser?: string;
  currentUserId?: number | string;
}

const CommentList: React.FC<CommentListProps> = ({
  messages,
  tabKey,
  isEditing,
  onAdd,
  onDelete,
  onEdit,
  currentUser = "You",
  currentUserId,
}) => {
  const [inputValue, setInputValue] = useState("");
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length]);

  const getTabColor = () => {
    switch (tabKey) {
      case "public":
        return "text-blue-700 dark:text-blue-300";
      case "process":
        return "text-green-700 dark:text-green-300";
      case "partner":
        return "text-purple-700 dark:text-purple-300";
      case "notes":
        return "text-slate-700 dark:text-white";
      default:
        return "text-slate-700 dark:text-white";
    }
  };

  const getTabLabel = () => {
    switch (tabKey) {
      case "public":
        return "Public (visible to customer)";
      case "process":
        return "Process (internal only)";
      case "partner":
        return "Partner (shared with vendors)";
      case "notes":
        return "Notes (internal notes)";
      default:
        return tabKey;
    }
  };

  const handleSend = () => {
    if (inputValue.trim()) {
      const now = new Date();
      const timeStr = now.toLocaleString([], {
        hour: "2-digit",
        minute: "2-digit",
        year: "numeric",
        month: "short",
        day: "2-digit",
      });
      const newMessage: CommentMessage = {
        user: currentUser,
        mgs: inputValue.trim(),
        time: timeStr,
        user_id: currentUserId,
      };
      onAdd(newMessage);
      setInputValue("");
    }
  };

  const handleEditSave = (index: number) => {
    if (editValue.trim() && onEdit) {
      const updatedMsg = { ...messages[index], mgs: editValue.trim() };
      onEdit(index, updatedMsg);
      setEditingIndex(null);
      setEditValue("");
    }
  };

  const handleEditCancel = () => {
    setEditingIndex(null);
    setEditValue("");
  };

  return (
    <div className="flex flex-col h-64">
      <label className="block text-xs font-medium text-slate-700 dark:text-slate-400 mb-1">
        {getTabLabel()}
      </label>

      {/* Messages display area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto border rounded bg-slate-50 dark:bg-slate-800 mb-2 pr-1 space-y-2 p-2"
      >
        {messages.length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            <p className="text-sm">No messages yet</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className="border-l-4 border-blue-300 pl-2 py-1">
              {editingIndex === idx ? (
                <div className="space-y-1">
                  <Input
                    type="text"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    placeholder="Edit message..."
                    className="flex-1 rounded border border-blue-300 px-2 py-1 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 bg-white dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && editValue.trim()) {
                        handleEditSave(idx);
                      } else if (e.key === "Escape") {
                        handleEditCancel();
                      }
                    }}
                  />
                  <div className="flex gap-1">
                    <button
                      onClick={() => handleEditSave(idx)}
                      className="px-2 py-1 rounded bg-green-500 text-white text-xs font-semibold hover:bg-green-600"
                    >
                      Save
                    </button>
                    <button
                      onClick={handleEditCancel}
                      className="px-2 py-1 rounded bg-slate-400 text-white text-xs font-semibold hover:bg-slate-500"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between gap-2 mb-0.5">
                    <div className="flex items-center gap-2 text-xs font-medium text-slate-600 dark:text-slate-300">
                      <span>{msg.user}</span>
                      <span>•</span>
                      <span>{msg.time}</span>
                    </div>
                    {isEditing && (
                      <div className="flex gap-1">
                        {onEdit && (
                          <button
                            onClick={() => {
                              setEditingIndex(idx);
                              setEditValue(msg.mgs);
                            }}
                            className="text-blue-500 hover:text-blue-700 dark:hover:text-blue-300 text-xs"
                            title="Edit"
                          >
                            <FaEdit size={12} />
                          </button>
                        )}
                        <button
                          onClick={() => onDelete(idx)}
                          className="text-red-500 hover:text-red-700 dark:hover:text-red-300 text-xs"
                          title="Delete"
                        >
                          <FaTrash size={12} />
                        </button>
                      </div>
                    )}
                  </div>
                  <p
                    className={`text-sm font-medium wrap-break-word ${getTabColor()}`}
                  >
                    {msg.mgs}
                  </p>
                </>
              )}
            </div>
          ))
        )}
      </div>

      {/* Input area */}
      {isEditing && (
        <div className="flex gap-2 p-2 bg-slate-100 dark:bg-slate-700 border-t border-slate-200 dark:border-slate-600 rounded-b">
          <Input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={`Add ${tabKey} comment...`}
            className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 bg-white dark:border-slate-600 dark:bg-slate-700 dark:text-white"
            onKeyDown={(e) => {
              if (e.key === "Enter" && inputValue.trim()) {
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
 * Helper to ensure a tab value is always an array
 * Handles cases where backend returns "" instead of []
 */
const ensureArray = (
  value: CommentMessage[] | string | undefined | null,
): CommentMessage[] => {
  if (Array.isArray(value)) return value;
  return [];
};

/**
 * CommentsPanel - Display and edit comments with CRUD operations
 *
 * Tabs:
 * - Public: Customer-visible notes
 * - Process: Internal process notes
 * - Partner: Vendor/partner notes
 * - Notes: Internal notes
 */
const CommentsPanel: React.FC<CommentsPanelProps> = ({
  entityType: _entityType,
  entityId: _entityId,
  comments: commentsProp = {},
  isEditing: isEditingProp = false,
  onChange,
  onSave,
  currentUser,
  currentUserId,
  readOnly = false,
  viewRoles,
  editRoles,
  className = "",
  compact = false,
  title = "Comments",
  defaultCollapsed = false,
  message,
}) => {
  const [activeTab, setActiveTab] = useState<TabKey>("public");
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [isSaving, setIsSaving] = useState(false);

  // Normalize comments - ensure all tab values are arrays (backend may return "" instead of [])
  const comments: EntityComments = {
    public: ensureArray(commentsProp.public),
    process: ensureArray(commentsProp.process),
    partner: ensureArray(commentsProp.partner),
    notes: ensureArray(commentsProp.notes),
  };

  // Check permissions
  const {
    canView,
    canEdit: permCanEdit,
    isAdmin,
  } = usePermissions({
    panelType: "comments",
    viewRoles,
    editRoles,
    forceReadOnly: readOnly,
  });

  // Allow editing if isEditingProp is true and onChange is provided
  // Fall back to permCanEdit, but default to true if permissions can't be determined
  const isEditing = isEditingProp && !!onChange && permCanEdit !== false;

  // Don't render if user explicitly doesn't have view permission
  // But if canView is undefined/null, still render (permissive default)
  if (canView === false) return null;

  // ---------------------------------------------------------------------------
  // CRUD Operations - with auto-save
  // ---------------------------------------------------------------------------

  const handleAddMessage = async (tabKey: TabKey, message: CommentMessage) => {
    const current = comments[tabKey] || [];
    const updated = [...current, message];
    const newComments = { ...comments, [tabKey]: updated };

    // Update local state first
    if (onChange) {
      onChange(newComments);
    }

    // Auto-save to database
    if (onSave) {
      setIsSaving(true);
      try {
        await onSave(newComments);
      } catch (error) {
        console.error("[CommentsPanel] Auto-save failed:", error);
      } finally {
        setIsSaving(false);
      }
    }
  };

  const handleDeleteMessage = async (tabKey: TabKey, index: number) => {
    const current = comments[tabKey] || [];
    const updated = current.filter((_, i) => i !== index);
    const newComments = { ...comments, [tabKey]: updated };

    // Update local state first
    if (onChange) {
      onChange(newComments);
    }

    // Auto-save to database
    if (onSave) {
      setIsSaving(true);
      try {
        await onSave(newComments);
      } catch (error) {
        console.error("[CommentsPanel] Auto-save failed:", error);
      } finally {
        setIsSaving(false);
      }
    }
  };

  const handleEditMessage = async (
    tabKey: TabKey,
    index: number,
    message: CommentMessage,
  ) => {
    const current = comments[tabKey] || [];
    const updated = current.map((m, i) => (i === index ? message : m));
    const newComments = { ...comments, [tabKey]: updated };

    // Update local state first
    if (onChange) {
      onChange(newComments);
    }

    // Auto-save to database
    if (onSave) {
      setIsSaving(true);
      try {
        await onSave(newComments);
      } catch (error) {
        console.error("[CommentsPanel] Auto-save failed:", error);
      } finally {
        setIsSaving(false);
      }
    }
  };

  const getTabCount = (tabKey: TabKey) => {
    return comments[tabKey]?.length || 0;
  };

  const totalCount =
    getTabCount("public") +
    getTabCount("process") +
    getTabCount("partner") +
    getTabCount("notes");

  return (
    <div
      className={`bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 ${className}`}
    >
      {/* Header with collapse toggle */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700 cursor-pointer"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaComment className="text-slate-400" size={14} />
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
            {title}
          </h3>
          {totalCount > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded-full">
              {totalCount}
            </span>
          )}
          {isAdmin && (
            <span className="px-1.5 py-0.5 text-xs bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 rounded">
              Admin
            </span>
          )}
          {isSaving && (
            <span className="flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400">
              <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-500" />
              Saving...
            </span>
          )}
        </div>
        {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className={`p-4 ${compact ? "space-y-2" : "space-y-4"}`}>
          {/* Message display */}
          {message && (
            <div className="mb-2 px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs text-center">
              {message}
            </div>
          )}

          {/* Tab Navigation */}
          <div className="flex border-b border-slate-200 dark:border-slate-700">
            <TabButton
              active={activeTab === "public"}
              onClick={() => setActiveTab("public")}
              icon={<FaComment size={12} />}
              label="Public"
              count={getTabCount("public")}
            />
            <TabButton
              active={activeTab === "process"}
              onClick={() => setActiveTab("process")}
              icon={<FaCog size={12} />}
              label="Process"
              count={getTabCount("process")}
            />
            <TabButton
              active={activeTab === "partner"}
              onClick={() => setActiveTab("partner")}
              icon={<FaHandshake size={12} />}
              label="Partner"
              count={getTabCount("partner")}
            />
            <TabButton
              active={activeTab === "notes"}
              onClick={() => setActiveTab("notes")}
              icon={<FaEdit size={12} />}
              label="Notes"
              count={getTabCount("notes")}
            />
          </div>

          {/* Tab Content */}
          <div className={compact ? "min-h-32" : "min-h-40"}>
            {activeTab === "public" && (
              <CommentList
                messages={comments.public || []}
                tabKey="public"
                isEditing={isEditing}
                onAdd={(msg) => handleAddMessage("public", msg)}
                onDelete={(idx) => handleDeleteMessage("public", idx)}
                onEdit={(idx, msg) => handleEditMessage("public", idx, msg)}
                currentUser={currentUser || "You"}
                currentUserId={currentUserId}
              />
            )}
            {activeTab === "process" && (
              <CommentList
                messages={comments.process || []}
                tabKey="process"
                isEditing={isEditing}
                onAdd={(msg) => handleAddMessage("process", msg)}
                onDelete={(idx) => handleDeleteMessage("process", idx)}
                onEdit={(idx, msg) => handleEditMessage("process", idx, msg)}
                currentUser={currentUser || "You"}
                currentUserId={currentUserId}
              />
            )}
            {activeTab === "partner" && (
              <CommentList
                messages={comments.partner || []}
                tabKey="partner"
                isEditing={isEditing}
                onAdd={(msg) => handleAddMessage("partner", msg)}
                onDelete={(idx) => handleDeleteMessage("partner", idx)}
                onEdit={(idx, msg) => handleEditMessage("partner", idx, msg)}
                currentUser={currentUser || "You"}
                currentUserId={currentUserId}
              />
            )}
            {activeTab === "notes" && (
              <CommentList
                messages={comments.notes || []}
                tabKey="notes"
                isEditing={isEditing}
                onAdd={(msg) => handleAddMessage("notes", msg)}
                onDelete={(idx) => handleDeleteMessage("notes", idx)}
                onEdit={(idx, msg) => handleEditMessage("notes", idx, msg)}
                currentUser={currentUser || "You"}
                currentUserId={currentUserId}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CommentsPanel;

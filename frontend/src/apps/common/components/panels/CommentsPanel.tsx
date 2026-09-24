/* LastChecked: 2026-09-15 | WhereUsed: panelRegistry | WhoCreated: Bill+Claude */
/**
 * CommentsPanel — JSON-driven comment channels.
 *
 * Channel definitions come from the layout Setting JSON:
 *   config.layout.form.default.sections[].config.channels
 *
 * Each channel: { key, label, color }
 *   key   = data key in the comments envelope (e.g. "process", "public", "partner")
 *   label = display label (e.g. "foreign" for the partner key)
 *   color = CSS color value
 *
 * Falls back to a default set if the Setting doesn't define channels.
 *
 * Each comment entry: { user, mgs, time, user_id }
 * Entry label: "datetime — username"
 * Text is directly editable inline. No send button.
 */
import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  FaComment,
  FaTrash,
  FaChevronDown,
  FaChevronUp,
} from "react-icons/fa";
import { usePermissions } from "./usePermissions";
import { COMMENT_TEXT_MAX_LEN, COMMENT_CHANNEL_MAX_COUNT } from "../../../../constants/envelopeLimits";
import type {
  BasePanelProps,
  EntityComments,
  CommentMessage,
  RawEntityComments,
} from "./types";
import { withDevIdentifier } from "@/components/common/DevIdentifier";
import { formatDt } from '@/utils/fieldFormatters';
import { useAppSelector } from '@/store/hooks';

// ---------------------------------------------------------------------------
// Channel config — JSON-driven
// ---------------------------------------------------------------------------

export interface ChannelDef {
  key: string;   // data key in comments envelope
  label: string; // display label
  color: string; // CSS color
}

const DEFAULT_CHANNELS: ChannelDef[] = [
  { key: "process", label: "process", color: "var(--db-accent-green)" },
  { key: "public",  label: "public",  color: "var(--db-accent)" },
  { key: "partner", label: "foreign", color: "var(--db-accent-purple)" },
];

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CommentsPanelProps
  extends Omit<BasePanelProps<EntityComments>, "data" | "onChange"> {
  comments?: RawEntityComments;
  isEditing?: boolean;
  /** Channel definitions from the layout Setting JSON */
  channels?: ChannelDef[];
  onChange?: (comments: EntityComments) => void;
  onSave?: (comments: EntityComments) => Promise<void>;
  currentUser?: string;
  currentUserId?: number | string;
  message?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const ensureArray = (
  value: CommentMessage[] | string | undefined | null,
): CommentMessage[] => {
  if (Array.isArray(value)) return value;
  return [];
};

const latestTimestamp = (messages: CommentMessage[]): string | null => {
  if (messages.length === 0) return null;
  return messages[messages.length - 1]?.time || null;
};

// ---------------------------------------------------------------------------
// CommentEntry — single row: label = "datetime — user", value = editable text
// ---------------------------------------------------------------------------

interface CommentEntryProps {
  msg: CommentMessage;
  index: number;
  isEditing: boolean;
  autoFocus?: boolean;
  onEdit: (index: number, msg: CommentMessage) => void;
  onDelete: (index: number) => void;
  color: string;
}

const CommentEntry: React.FC<CommentEntryProps> = ({
  msg, index, isEditing, autoFocus, onEdit, onDelete, color,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const label = `${msg.time || '—'}  —  ${msg.user || '—'}`;

  useEffect(() => {
    if (autoFocus && textareaRef.current) {
      const ta = textareaRef.current;
      ta.focus();
      ta.setSelectionRange(ta.value.length, ta.value.length);
    }
  }, [autoFocus]);

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    if (val.length <= COMMENT_TEXT_MAX_LEN) {
      onEdit(index, { ...msg, mgs: val });
    }
  };

  return (
    <div className="mb-2">
      <div className="flex items-center justify-between mb-0.5">
        <label className="db-font-xs db-text-muted">{label}</label>
        {isEditing && (
          <button
            onClick={() => {
              if (window.confirm("Delete this comment?")) onDelete(index);
            }}
            className="db-font-xs db-text-red opacity-50 hover:opacity-100"
            title="Delete"
          >
            <FaTrash size={10} />
          </button>
        )}
      </div>
      {isEditing ? (
        <textarea
          ref={textareaRef}
          value={msg.mgs}
          onChange={handleTextChange}
          className="w-full resize-none rounded px-2 py-1.5 db-font-sm db-panel-text"
          style={{ borderLeft: `3px solid ${color}` }}
          rows={1}
          onInput={(e) => {
            const ta = e.target as HTMLTextAreaElement;
            ta.style.height = 'auto';
            ta.style.height = ta.scrollHeight + 'px';
          }}
        />
      ) : (
        <div
          className="px-2 py-1.5 db-font-sm db-text rounded"
          style={{ borderLeft: `3px solid ${color}` }}
        >
          {msg.mgs || <span className="db-text-dim italic">empty</span>}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// ChannelSection — one collapsible section per channel
// ---------------------------------------------------------------------------

interface ChannelSectionProps {
  channel: ChannelDef;
  messages: CommentMessage[];
  isEditing: boolean;
  onAdd: () => void;
  onEdit: (idx: number, msg: CommentMessage) => void;
  onDelete: (idx: number) => void;
  defaultCollapsed?: boolean;
}

const ChannelSection: React.FC<ChannelSectionProps> = ({
  channel, messages,
  isEditing, onAdd, onEdit, onDelete, defaultCollapsed = false,
}) => {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const [focusIndex, setFocusIndex] = useState<number | null>(null);
  const latest = latestTimestamp(messages);
  const count = messages.length;
  const atLimit = count >= COMMENT_CHANNEL_MAX_COUNT;

  const handleAdd = useCallback(() => {
    setCollapsed(false);
    setFocusIndex(count);
    onAdd();
  }, [count, onAdd]);

  useEffect(() => {
    if (focusIndex !== null) {
      const t = setTimeout(() => setFocusIndex(null), 100);
      return () => clearTimeout(t);
    }
  }, [focusIndex]);

  return (
    <div className="rounded-lg db-panel mb-2">
      <div
        className="flex items-center justify-between px-3 py-2 cursor-pointer db-section-bg rounded-t-lg"
        onClick={() => setCollapsed(!collapsed)}
      >
        <div className="flex items-center gap-2">
          {isEditing && !atLimit ? (
            <button
              onClick={(e) => { e.stopPropagation(); handleAdd(); }}
              className="db-font-sm font-semibold hover:opacity-80"
              style={{ color: channel.color }}
              title={`Add ${channel.label} comment`}
            >
              +.{channel.label}
            </button>
          ) : (
            <span className="db-font-sm font-semibold db-text">{channel.label}</span>
          )}
          {count > 0 && (
            <span className="px-1.5 py-0.5 db-font-xs rounded-full db-row-active-accent">
              {count}
            </span>
          )}
          {latest && (
            <span className="db-font-xs db-text-muted italic">{latest}</span>
          )}
        </div>
        {collapsed ? <FaChevronDown size={10} /> : <FaChevronUp size={10} />}
      </div>
      {!collapsed && (
        <div className="p-2">
          {messages.length === 0 ? (
            <div className="text-center py-3 db-text-dim db-font-xs">
              No comments
            </div>
          ) : (
            messages.map((msg, idx) => (
              <CommentEntry
                key={idx}
                msg={msg}
                index={idx}
                isEditing={isEditing}
                autoFocus={focusIndex === idx}
                onEdit={onEdit}
                onDelete={onDelete}
                color={channel.color}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main CommentsPanel — reads channel config from props (Setting JSON)
// ---------------------------------------------------------------------------

const CommentsPanel: React.FC<CommentsPanelProps> = ({
  comments: commentsProp = {},
  isEditing: isEditingProp = false,
  channels: channelsProp,
  onChange,
  onSave,
  currentUser,
  currentUserId,
  readOnly = false,
  viewRoles,
  editRoles,
  className = "",
  title = "Comments",
  defaultCollapsed = false,
  message,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [isSaving, setIsSaving] = useState(false);
  const authUser = useAppSelector((s) => s.auth.user);
  const displayName = currentUser
    || [authUser?.name_first, authUser?.name_last].filter(Boolean).join(' ')
    || authUser?.username
    || 'Unknown';

  // Channels from Setting JSON, or default
  const channels: ChannelDef[] = (Array.isArray(channelsProp) && channelsProp.length > 0)
    ? channelsProp
    : DEFAULT_CHANNELS;

  // Normalize all channel keys to arrays
  const comments: Record<string, CommentMessage[]> = {};
  for (const ch of channels) {
    comments[ch.key] = ensureArray((commentsProp as Record<string, any>)?.[ch.key]);
  }

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

  const isEditing = isEditingProp && !!onChange && permCanEdit !== false;

  if (canView === false) return null;

  // ---------------------------------------------------------------------------
  // Persist
  // ---------------------------------------------------------------------------

  const persistComments = async (newComments: Record<string, CommentMessage[]>) => {
    if (onChange) onChange(newComments as EntityComments);
    if (onSave) {
      setIsSaving(true);
      try {
        await onSave(newComments as EntityComments);
      } catch (error) {
        console.error("[CommentsPanel] Auto-save failed:", error);
      } finally {
        setIsSaving(false);
      }
    }
  };

  const handleAdd = (key: string) => {
    const current = comments[key] || [];
    const now = new Date();
    const newMsg: CommentMessage = {
      user: displayName,
      mgs: '',
      time: formatDt(now, 'datetime_tz'),
      user_id: currentUserId || authUser?.id,
    };
    persistComments({ ...comments, [key]: [...current, newMsg] });
  };

  const handleEdit = (key: string, index: number, msg: CommentMessage) => {
    const current = comments[key] || [];
    persistComments({ ...comments, [key]: current.map((m, i) => (i === index ? msg : m)) });
  };

  const handleDelete = (key: string, index: number) => {
    const current = comments[key] || [];
    persistComments({ ...comments, [key]: current.filter((_, i) => i !== index) });
  };

  const totalCount = channels.reduce(
    (sum, ch) => sum + (comments[ch.key]?.length || 0), 0
  );

  return (
    <div className={`rounded-lg db-panel ${className}`}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer rounded-t-lg db-section-bg"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaComment className="db-text-muted" size={14} />
          <h3 className="db-font-sm font-semibold db-text">{title}</h3>
          {totalCount > 0 && (
            <span className="px-1.5 py-0.5 db-font-xs rounded-full db-row-active-accent">
              {totalCount}
            </span>
          )}
          {isAdmin && (
            <span className="px-1.5 py-0.5 db-font-xs rounded db-text-gold">Admin</span>
          )}
          {isSaving && (
            <span className="flex items-center gap-1 db-font-xs db-text-accent">
              <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-500" />
              Saving...
            </span>
          )}
        </div>
        {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
      </div>

      {!isCollapsed && (
        <div className="p-3 space-y-1">
          {message && (
            <div className="mb-2 px-2 py-1 bg-yellow-100 text-yellow-800 rounded db-font-xs text-center">
              {message}
            </div>
          )}
          {channels.map((ch) => (
            <ChannelSection
              key={ch.key}
              channel={ch}
              messages={comments[ch.key] || []}
              isEditing={isEditing}
              onAdd={() => handleAdd(ch.key)}
              onEdit={(idx, msg) => handleEdit(ch.key, idx, msg)}
              onDelete={(idx) => handleDelete(ch.key, idx)}
              defaultCollapsed={(comments[ch.key]?.length || 0) === 0}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default withDevIdentifier(CommentsPanel, "CommentsPanel", "teal", 'apps/common/components/panels/CommentsPanel.tsx');

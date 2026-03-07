/**
 * HistoryPanel - Display and edit entity .metadata object
 *
 * Role-based access:
 * - View: Admin only (default)
 * - Edit: Admin only (default)
 *
 * @example
 * <HistoryPanel
 *   entityType="contact"
 *   entityId={123}
 *   data={contact.metadata}
 *   onChange={(metadata) => setContact({ ...contact, metadata })}
 * />
 */
import React, { useState } from "react";
import {
  FaDatabase,
  FaChevronDown,
  FaChevronUp,
  FaPlus,
  FaTrash,
  FaEdit,
  FaSave,
  FaTimes,
} from "react-icons/fa";
import { usePermissions } from "./usePermissions";
import type { BasePanelProps, EntityMetadata } from "./types";
import { withDevIdentifier } from "@/components/common/DevIdentifier";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface HistoryPanelProps
  extends Omit<BasePanelProps<EntityMetadata>, "data"> {
  /** Metadata object */
  data?: EntityMetadata;
}

// ---------------------------------------------------------------------------
// Key-Value Editor Row
// ---------------------------------------------------------------------------

interface KeyValueRowProps {
  keyName: string;
  value: unknown;
  onUpdate: (key: string, value: unknown) => void;
  onDelete: (key: string) => void;
  canEdit: boolean;
  depth?: number;
}

const KeyValueRow: React.FC<KeyValueRowProps> = ({
  keyName,
  value,
  onUpdate,
  onDelete,
  canEdit,
  depth = 0,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState("");
  const [isExpanded, setIsExpanded] = useState(false);

  const isObject =
    typeof value === "object" && value !== null && !Array.isArray(value);
  const isArray = Array.isArray(value);
  const displayValue =
    isObject || isArray ? JSON.stringify(value, null, 2) : String(value ?? "");

  const handleEdit = () => {
    setEditValue(displayValue);
    setIsEditing(true);
  };

  const handleSave = () => {
    try {
      // Try to parse as JSON first
      const parsed = JSON.parse(editValue);
      onUpdate(keyName, parsed);
    } catch {
      // If not valid JSON, save as string
      onUpdate(keyName, editValue);
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditValue("");
  };

  return (
    <div
      className={`border-b border-slate-100 dark:border-slate-700 last:border-b-0 ${
        depth > 0
          ? "ml-4 pl-2 border-l-2 border-l-slate-200 dark:border-l-slate-600"
          : ""
      }`}
    >
      <div className="flex items-start gap-2 py-2">
        {/* Key */}
        <div className="flex items-center gap-1 min-w-[120px]">
          {(isObject || isArray) && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-slate-400 hover:text-slate-600"
              type="button"
            >
              {isExpanded ? (
                <FaChevronUp size={10} />
              ) : (
                <FaChevronDown size={10} />
              )}
            </button>
          )}
          <span className="text-xs font-mono font-medium text-slate-600 dark:text-slate-300">
            {keyName}
          </span>
          <span className="text-xs text-slate-400">
            ({isArray ? "array" : typeof value})
          </span>
        </div>

        {/* Value */}
        <div className="flex-1 min-w-0">
          {isEditing ? (
            <textarea
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              className="w-full px-2 py-1 text-xs font-mono border rounded bg-white dark:bg-slate-700 dark:border-slate-600"
              rows={isObject || isArray ? 4 : 1}
              autoFocus
            />
          ) : (
            <div
              className={`text-xs font-mono text-slate-700 dark:text-slate-300 truncate ${
                isObject || isArray ? "cursor-pointer hover:text-blue-600" : ""
              }`}
              onClick={() =>
                (isObject || isArray) && setIsExpanded(!isExpanded)
              }
              title={displayValue}
            >
              {isObject || isArray
                ? isExpanded
                  ? ""
                  : `${isArray ? "[" : "{"}...${isArray ? "]" : "}"}`
                : displayValue || (
                    <span className="text-slate-400 italic">empty</span>
                  )}
            </div>
          )}
        </div>

        {/* Actions */}
        {canEdit && (
          <div className="flex items-center gap-1">
            {isEditing ? (
              <>
                <button
                  onClick={handleSave}
                  className="p-1 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded"
                  title="Save"
                >
                  <FaSave size={12} />
                </button>
                <button
                  onClick={handleCancel}
                  className="p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded"
                  title="Cancel"
                >
                  <FaTimes size={12} />
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={handleEdit}
                  className="p-1 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
                  title="Edit"
                >
                  <FaEdit size={12} />
                </button>
                <button
                  onClick={() => onDelete(keyName)}
                  className="p-1 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                  title="Delete"
                >
                  <FaTrash size={12} />
                </button>
              </>
            )}
          </div>
        )}
      </div>

      {/* Expanded object/array view */}
      {isExpanded && (isObject || isArray) && (
        <div className="pb-2">
          <pre className="text-xs font-mono bg-slate-50 dark:bg-slate-900 p-2 rounded overflow-x-auto">
            {displayValue}
          </pre>
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Add Key Modal
// ---------------------------------------------------------------------------

interface AddKeyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (key: string, value: unknown) => void;
}

const AddKeyModal: React.FC<AddKeyModalProps> = ({
  isOpen,
  onClose,
  onAdd,
}) => {
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");
  const [valueType, setValueType] = useState<
    "string" | "number" | "boolean" | "json"
  >("string");

  if (!isOpen) return null;

  const handleAdd = () => {
    if (!key.trim()) return;

    let parsedValue: unknown = value;
    try {
      switch (valueType) {
        case "number":
          parsedValue = Number(value);
          break;
        case "boolean":
          parsedValue = value.toLowerCase() === "true";
          break;
        case "json":
          parsedValue = JSON.parse(value);
          break;
      }
    } catch {
      // Keep as string if parsing fails
    }

    onAdd(key.trim(), parsedValue);
    setKey("");
    setValue("");
    setValueType("string");
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-800 rounded-lg p-4 w-96 max-w-full mx-4">
        <h3 className="text-sm font-semibold mb-4 text-slate-700 dark:text-slate-200">
          Add Metadata Key
        </h3>

        <div className="space-y-3">
          <div>
            <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
              Key
            </label>
            <input
              type="text"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
              placeholder="key_name"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
              Type
            </label>
            <select
              value={valueType}
              onChange={(e) => setValueType(e.target.value as typeof valueType)}
              className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
            >
              <option value="string">String</option>
              <option value="number">Number</option>
              <option value="boolean">Boolean</option>
              <option value="json">JSON</option>
            </select>
          </div>

          <div>
            <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">
              Value
            </label>
            {valueType === "json" ? (
              <textarea
                value={value}
                onChange={(e) => setValue(e.target.value)}
                className="w-full px-2 py-1.5 text-sm font-mono border rounded dark:bg-slate-700 dark:border-slate-600"
                rows={4}
                placeholder='{"key": "value"}'
              />
            ) : valueType === "boolean" ? (
              <select
                value={value}
                onChange={(e) => setValue(e.target.value)}
                className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
              >
                <option value="true">true</option>
                <option value="false">false</option>
              </select>
            ) : (
              <input
                type={valueType === "number" ? "number" : "text"}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                placeholder={valueType === "number" ? "0" : "value"}
              />
            )}
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-4">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700 rounded"
          >
            Cancel
          </button>
          <button
            onClick={handleAdd}
            disabled={!key.trim()}
            className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
          >
            Add
          </button>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main HistoryPanel Component
// ---------------------------------------------------------------------------

const HistoryPanel: React.FC<HistoryPanelProps> = ({
  entityType: _entityType,
  entityId: _entityId,
  data = {},
  onChange,
  readOnly = false,
  viewRoles,
  editRoles,
  className = "",
  compact = false,
  title = "History",
  defaultCollapsed = false,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [showAddModal, setShowAddModal] = useState(false);

  // Check permissions (admin only by default)
  const { canView, canEdit: permCanEdit } = usePermissions({
    panelType: "history",
    viewRoles,
    editRoles,
    forceReadOnly: readOnly,
  });

  const canEdit = permCanEdit && !!onChange;

  // Don't render if user can't view
  if (!canView) return null;

  const handleUpdate = (key: string, value: unknown) => {
    if (onChange) {
      onChange({ ...data, [key]: value });
    }
  };

  const handleDelete = (key: string) => {
    if (onChange) {
      const newData = { ...data };
      delete newData[key];
      onChange(newData);
    }
  };

  const handleAdd = (key: string, value: unknown) => {
    if (onChange) {
      onChange({ ...data, [key]: value });
    }
  };

  const entries = Object.entries(data?.history || {});

  return (
    <div
      className={`bg-white dark:bg-slate-800 rounded-lg border border-amber-200 dark:border-amber-800 ${className}`}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800 cursor-pointer rounded-t-lg"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaDatabase className="text-amber-500" size={14} />
          <h3 className="text-sm font-semibold text-amber-700 dark:text-amber-300">
            {title}
          </h3>
          <span className="px-1.5 py-0.5 text-xs bg-amber-200 dark:bg-amber-800 text-amber-700 dark:text-amber-300 rounded">
            Admin
          </span>
          <span className="text-xs text-amber-600 dark:text-amber-400">
            {entries.length} {entries.length === 1 ? "key" : "keys"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {canEdit && !isCollapsed && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowAddModal(true);
              }}
              className="p-1 text-amber-600 hover:bg-amber-100 dark:hover:bg-amber-800 rounded"
              title="Add key"
            >
              <FaPlus size={12} />
            </button>
          )}
          {isCollapsed ? (
            <FaChevronDown size={12} />
          ) : (
            <FaChevronUp size={12} />
          )}
        </div>
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className={`${compact ? "p-2" : "p-4"}`}>
          {entries.length === 0 ? (
            <div className="text-center py-4 text-slate-400 text-sm">
              No metadata keys defined
            </div>
          ) : (
            <div className="divide-y divide-slate-100 dark:divide-slate-700">
              {entries.map(([key, value]) => (
                <KeyValueRow
                  key={key}
                  keyName={key}
                  value={value}
                  onUpdate={handleUpdate}
                  onDelete={handleDelete}
                  canEdit={canEdit}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Add Key Modal */}
      <AddKeyModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onAdd={handleAdd}
      />
    </div>
  );
};

export default withDevIdentifier(HistoryPanel, "HistoryPanel", "teal");

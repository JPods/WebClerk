/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * MetadataPanel - Display and edit entity .metadata object
 *
 * Role-based access:
 * - View: Admin only (default)
 * - Edit: Admin only (default)
 *
 * @example
 * <MetadataPanel
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

interface MetadataPanelProps
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
      className={`last:border-b-0 db-border-bottom-light ${
        depth > 0
          ? "ml-4 pl-2"
          : ""
      }`}
      style={depth > 0 ? { borderLeft: '2px solid var(--db-border)' } : undefined}
    >
      <div className="flex items-start gap-2 py-2">
        {/* Key */}
        <div className="flex items-center gap-1 min-w-[120px]">
          {(isObject || isArray) && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="db-text-dim"
              type="button"
            >
              {isExpanded ? (
                <FaChevronUp size={10} />
              ) : (
                <FaChevronDown size={10} />
              )}
            </button>
          )}
          <span className="text-xs font-mono font-medium db-text">
            {keyName}
          </span>
          <span className="text-xs db-text-dim">
            ({isArray ? "array" : typeof value})
          </span>
        </div>

        {/* Value */}
        <div className="flex-1 min-w-0">
          {isEditing ? (
            <textarea
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              className="w-full px-2 py-1 text-xs font-mono rounded db-panel"
              rows={isObject || isArray ? 4 : 1}
              autoFocus
            />
          ) : (
            <div
              className={`text-xs font-mono truncate db-text ${
                isObject || isArray ? "cursor-pointer" : ""
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
                    <span className="italic db-text-dim">empty</span>
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
                  className="p-1 rounded db-text-green"
                  title="Save"
                >
                  <FaSave size={12} />
                </button>
                <button
                  onClick={handleCancel}
                  className="p-1 rounded db-text-dim"
                  title="Cancel"
                >
                  <FaTimes size={12} />
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={handleEdit}
                  className="p-1 rounded db-text-accent"
                  title="Edit"
                >
                  <FaEdit size={12} />
                </button>
                <button
                  onClick={() => onDelete(keyName)}
                  className="p-1 rounded db-text-red"
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
          <pre className="text-xs font-mono p-2 rounded overflow-x-auto db-bg-surface-alt">
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
      <div className="rounded-lg p-4 w-96 max-w-full mx-4 db-bg-surface">
        <h3 className="text-sm font-semibold mb-4 db-text">
          Add Metadata Key
        </h3>

        <div className="space-y-3">
          <div>
            <label className="block text-xs mb-1 db-text-muted">
              Key
            </label>
            <input
              type="text"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              className="w-full px-2 py-1.5 text-sm rounded db-panel-text"
              placeholder="key_name"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-xs mb-1 db-text-muted">
              Type
            </label>
            <select
              value={valueType}
              onChange={(e) => setValueType(e.target.value as typeof valueType)}
              className="w-full px-2 py-1.5 text-sm rounded db-panel-text"
            >
              <option value="string">String</option>
              <option value="number">Number</option>
              <option value="boolean">Boolean</option>
              <option value="json">JSON</option>
            </select>
          </div>

          <div>
            <label className="block text-xs mb-1 db-text-muted">
              Value
            </label>
            {valueType === "json" ? (
              <textarea
                value={value}
                onChange={(e) => setValue(e.target.value)}
                className="w-full px-2 py-1.5 text-sm font-mono rounded db-panel-text"
                rows={4}
                placeholder='{"key": "value"}'
              />
            ) : valueType === "boolean" ? (
              <select
                value={value}
                onChange={(e) => setValue(e.target.value)}
                className="w-full px-2 py-1.5 text-sm rounded db-panel-text"
              >
                <option value="true">true</option>
                <option value="false">false</option>
              </select>
            ) : (
              <input
                type={valueType === "number" ? "number" : "text"}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                className="w-full px-2 py-1.5 text-sm rounded db-panel-text"
                placeholder={valueType === "number" ? "0" : "value"}
              />
            )}
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-4">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-sm rounded db-text-muted"
          >
            Cancel
          </button>
          <button
            onClick={handleAdd}
            disabled={!key.trim()}
            className="px-3 py-1.5 text-sm rounded disabled:opacity-50 db-btn-primary-solid"
          >
            Add
          </button>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main MetadataPanel Component
// ---------------------------------------------------------------------------

const MetadataPanel: React.FC<MetadataPanelProps> = ({
  entityType: _entityType,
  entityId: _entityId,
  data = {},
  onChange,
  readOnly = false,
  viewRoles,
  editRoles,
  className = "",
  compact = false,
  title = "Metadata",
  defaultCollapsed = false,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [showAddModal, setShowAddModal] = useState(false);

  // Check permissions (admin only by default)
  const { canView, canEdit: permCanEdit } = usePermissions({
    panelType: "metadata",
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

  const entries = Object.entries(data || {});

  return (
    <div
      className={`rounded-lg db-panel ${className}`}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer rounded-t-lg db-section-bg"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaDatabase className="db-text-gold" size={14} />
          <h3 className="text-sm font-semibold db-text">
            {title}
          </h3>
          <span className="px-1.5 py-0.5 text-xs rounded db-surface-alt-gold">
            Admin
          </span>
          <span className="text-xs db-text-gold">
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
              className="p-1 rounded db-text-gold"
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
            <div className="text-center py-4 text-sm db-text-dim">
              No metadata keys defined
            </div>
          ) : (
            <div>
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

export default withDevIdentifier(MetadataPanel, "MetadataPanel", "teal", 'apps/common/components/panels/MetadataPanel.tsx');

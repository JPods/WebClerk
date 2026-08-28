/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * PrefsPanel - Display and edit entity .prefs object (user/entity preferences)
 *
 * Role-based access:
 * - View: User+ roles (default)
 * - Edit: Admin only (default), or own prefs for users
 *
 * @example
 * <PrefsPanel
 *   entityType="contact"
 *   entityId={123}
 *   data={contact.prefs}
 *   onChange={(prefs) => setContact({ ...contact, prefs })}
 * />
 */
import React, { useState } from "react";
import {
  FaCog,
  FaChevronDown,
  FaChevronUp,
  FaToggleOn,
  FaToggleOff,
} from "react-icons/fa";
import { usePermissions } from "./usePermissions";
import type { BasePanelProps, EntityPrefs } from "./types";
import { withDevIdentifier } from "@/components/common/DevIdentifier";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PrefsPanelProps extends Omit<BasePanelProps<EntityPrefs>, "data"> {
  /** Prefs object */
  data?: EntityPrefs;
}

// ---------------------------------------------------------------------------
// Preference Section Component
// ---------------------------------------------------------------------------

interface PrefSectionProps {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  defaultExpanded?: boolean;
}

const PrefSection: React.FC<PrefSectionProps> = ({
  title,
  icon,
  children,
  defaultExpanded = true,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className="border-b last:border-b-0" style={{ borderColor: 'var(--db-border-light)' }}>
      <div
        className="flex items-center gap-2 py-2 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {icon && <span style={{ color: 'var(--db-text-dim)' }}>{icon}</span>}
        <span className="text-xs font-semibold" style={{ color: 'var(--db-text)' }}>
          {title}
        </span>
        {isExpanded ? <FaChevronUp size={10} /> : <FaChevronDown size={10} />}
      </div>
      {isExpanded && <div className="pb-3 pl-6 space-y-2">{children}</div>}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Toggle Switch Component
// ---------------------------------------------------------------------------

interface ToggleSwitchProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  description?: string;
}

const ToggleSwitch: React.FC<ToggleSwitchProps> = ({
  label,
  checked,
  onChange,
  disabled = false,
  description,
}) => (
  <div className="flex items-center justify-between">
    <div>
      <span className="text-xs" style={{ color: 'var(--db-text)' }}>
        {label}
      </span>
      {description && (
        <p className="text-xs mt-0.5" style={{ color: 'var(--db-text-dim)' }}>{description}</p>
      )}
    </div>
    <button
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className={`text-xl ${
        disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"
      }`}
    >
      {checked ? (
        <FaToggleOn style={{ color: 'var(--db-accent)' }} />
      ) : (
        <FaToggleOff style={{ color: 'var(--db-text-dim)' }} />
      )}
    </button>
  </div>
);

// ---------------------------------------------------------------------------
// Select Component
// ---------------------------------------------------------------------------

interface SelectPrefProps {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
  disabled?: boolean;
}

const SelectPref: React.FC<SelectPrefProps> = ({
  label,
  value,
  options,
  onChange,
  disabled,
}) => (
  <div className="flex items-center justify-between gap-4">
    <span className="text-xs" style={{ color: 'var(--db-text)' }}>{label}</span>
    <select data-wc="select"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className="text-xs px-2 py-1 rounded disabled:opacity-50"
      style={{ background: 'var(--db-input-bg)', border: '1px solid var(--db-input-border)' }}
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  </div>
);

// ---------------------------------------------------------------------------
// Main PrefsPanel Component
// ---------------------------------------------------------------------------

const PrefsPanel: React.FC<PrefsPanelProps> = ({
  entityType: _entityType,
  entityId: _entityId,
  data = {},
  onChange,
  readOnly = false,
  viewRoles,
  editRoles,
  className = "",
  compact = false,
  title = "Preferences",
  defaultCollapsed = false,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);

  // Check permissions
  const {
    canView,
    canEdit: permCanEdit,
    isAdmin,
  } = usePermissions({
    panelType: "prefs",
    viewRoles,
    editRoles,
    forceReadOnly: readOnly,
  });

  const canEdit = permCanEdit && !!onChange;

  // Don't render if user can't view
  if (!canView) return null;

  // Helpers to update nested prefs
  const updateDisplay = (key: string, value: unknown) => {
    if (!onChange) return;
    onChange({
      ...data,
      display: { ...data.display, [key]: value },
    });
  };

  const updateNotifications = (key: string, value: unknown) => {
    if (!onChange) return;
    onChange({
      ...data,
      notifications: { ...data.notifications, [key]: value },
    });
  };

  // Future use for defaults section
  // const updateDefaults = (key: string, value: unknown) => {
  //   if (!onChange) return;
  //   onChange({
  //     ...data,
  //     defaults: { ...data.defaults, [key]: value },
  //   });
  // };

  return (
    <div
      className={`rounded-lg border ${className}`}
      style={{ background: 'var(--db-surface)', borderColor: 'var(--db-border)' }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b cursor-pointer rounded-t-lg"
        style={{ background: 'var(--db-surface-alt)', borderColor: 'var(--db-border)' }}
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaCog className="text-purple-500" size={14} />
          <h3 className="text-sm font-semibold" style={{ color: 'var(--db-text)' }}>
            {title}
          </h3>
          {isAdmin && (
            <span className="px-1.5 py-0.5 text-xs rounded" style={{ background: 'var(--db-surface-alt)', color: 'var(--db-text-muted)' }}>
              Admin
            </span>
          )}
        </div>
        {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className={`${compact ? "p-2" : "p-4"}`}>
          {/* Display Preferences */}
          <PrefSection title="Display" defaultExpanded>
            <SelectPref
              label="Layout"
              value={data.display?.layout || "grid"}
              options={[
                { value: "grid", label: "Grid" },
                { value: "list", label: "List" },
                { value: "card", label: "Card" },
                { value: "table", label: "Table" },
              ]}
              onChange={(v) => updateDisplay("layout", v)}
              disabled={!canEdit}
            />
            <SelectPref
              label="Theme"
              value={data.display?.theme || "system"}
              options={[
                { value: "light", label: "Light" },
                { value: "dark", label: "Dark" },
                { value: "system", label: "System" },
              ]}
              onChange={(v) => updateDisplay("theme", v)}
              disabled={!canEdit}
            />
          </PrefSection>

          {/* Notification Preferences */}
          <PrefSection title="Notifications" defaultExpanded>
            <ToggleSwitch
              label="Email notifications"
              checked={data.notifications?.email ?? true}
              onChange={(v) => updateNotifications("email", v)}
              disabled={!canEdit}
            />
            <ToggleSwitch
              label="SMS notifications"
              checked={data.notifications?.sms ?? false}
              onChange={(v) => updateNotifications("sms", v)}
              disabled={!canEdit}
            />
            <ToggleSwitch
              label="Push notifications"
              checked={data.notifications?.push ?? false}
              onChange={(v) => updateNotifications("push", v)}
              disabled={!canEdit}
            />
            <SelectPref
              label="Frequency"
              value={data.notifications?.frequency || "immediate"}
              options={[
                { value: "immediate", label: "Immediate" },
                { value: "daily", label: "Daily Digest" },
                { value: "weekly", label: "Weekly Digest" },
              ]}
              onChange={(v) => updateNotifications("frequency", v)}
              disabled={!canEdit}
            />
          </PrefSection>

          {/* Raw JSON for admin */}
          {isAdmin && (
            <details className="mt-4">
              <summary className="text-xs cursor-pointer" style={{ color: 'var(--db-text-dim)' }}>
                View raw JSON
              </summary>
              <pre className="mt-2 text-xs font-mono p-2 rounded overflow-x-auto max-h-48" style={{ background: 'var(--db-surface-alt)' }}>
                {JSON.stringify(data, null, 2)}
              </pre>
            </details>
          )}
        </div>
      )}
    </div>
  );
};

export default withDevIdentifier(PrefsPanel, "PrefsPanel", "teal", 'apps/common/components/panels/PrefsPanel.tsx');

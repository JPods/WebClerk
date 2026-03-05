/**
 * GanttTaskTemplate - Custom task bar template with badges
 * 
 * Renders badges for priority and assigned person to the left of the task text.
 * Staff members get unique colored badges. Users can customize their badge via
 * contact.prefs.badge: { bg_color, text_color, initials }
 * 
 * Badge prefs are loaded on app startup via StaffBadgePrefsContext.
 */
import type { FC } from "react";
import type { ITask, IApi } from "@svar-ui/react-gantt";
import type { GanttMappedTask, AssignedUser, BadgePrefs } from "./ganttDataMapper";
import { useStaffBadgePrefsOptional } from "../../../context/StaffBadgePrefsContext";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

// Priority colors matching kanban TaskCard
const priorityColors: Record<string, { bg: string; text: string }> = {
  low: { bg: "#d1fae5", text: "#047857" },      // emerald
  medium: { bg: "#fef3c7", text: "#b45309" },   // amber
  high: { bg: "#fed7aa", text: "#c2410c" },     // orange
  critical: { bg: "#fecdd3", text: "#be123c" }, // rose
};

// Badge colors for staff contacts - unique colors for each staff member
const staffBadgeColors = [
  { bg: "#dbeafe", text: "#1d4ed8" },  // blue
  { bg: "#f3e8ff", text: "#7c3aed" },  // violet
  { bg: "#cffafe", text: "#0891b2" },  // cyan
  { bg: "#fae8ff", text: "#a21caf" },  // fuchsia
  { bg: "#d9f99d", text: "#4d7c0f" },  // lime
  { bg: "#fef9c3", text: "#a16207" },  // yellow
  { bg: "#fbcfe8", text: "#be185d" },  // pink
  { bg: "#e0e7ff", text: "#4338ca" },  // indigo
];

// Non-staff contacts get a neutral badge
const defaultAssigneeBadge = { bg: "#f3f4f6", text: "#374151" }; // gray

// Cache for consistent staff colors - maps contact id to color index
const staffColorCache = new Map<string | number, number>();
let nextStaffColorIndex = 0;

/**
 * Get badge colors for an assigned user
 * Priority: user's prefs.badge settings → staff auto-color → default gray
 */
const getAssigneeBadgeColor = (user: AssignedUser): { bg: string; text: string } => {
  // User has custom badge prefs - use those
  const badge = user.prefs?.badge;
  if (badge?.bg_color && badge?.text_color) {
    return { bg: badge.bg_color, text: badge.text_color };
  }
  
  // Non-staff get default
  if (!user.is_staff) return defaultAssigneeBadge;
  
  // Staff without prefs get auto-assigned color
  const key = user.id;
  if (!staffColorCache.has(key)) {
    staffColorCache.set(key, nextStaffColorIndex % staffBadgeColors.length);
    nextStaffColorIndex++;
  }
  return staffBadgeColors[staffColorCache.get(key)!];
};

const getInitials = (name?: string) => {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
};

// Priority short labels
const priorityShortLabel: Record<string, string> = {
  low: "L",
  medium: "M",
  high: "H",
  critical: "!",
};

interface GanttTaskTemplateProps {
  data: ITask;
  api: IApi;
  onaction: (ev: { action: string; data: Record<string, any> }) => void;
}

export const GanttTaskTemplate: FC<GanttTaskTemplateProps> = ({ data }) => {
  const task = data as GanttMappedTask;
  const priority = task.priority || "medium";
  const priorityColor = priorityColors[priority] || priorityColors.medium;
  const firstAssigned = task.assignedTo?.[0];
  
  // Get cached badge prefs from context (fetched on app startup)
  const badgePrefsContext = useStaffBadgePrefsOptional();
  
  /**
   * Get merged badge prefs for a user
   * Priority: inline prefs → context prefs → auto-assigned
   */
  const getMergedBadgePrefs = (user: AssignedUser): BadgePrefs | undefined => {
    // Inline prefs take precedence (from action.assigned_to)
    if (user.prefs?.badge) {
      return user.prefs.badge;
    }
    // Fall back to context prefs (from contact.prefs.badge fetched on startup)
    const contactId = typeof user.id === "string" ? parseInt(user.id, 10) : user.id;
    if (!Number.isNaN(contactId) && badgePrefsContext) {
      return badgePrefsContext.getBadgePrefs(contactId);
    }
    return undefined;
  };

  /**
   * Get badge colors for an assigned user
   * Priority: user's prefs.badge settings → staff auto-color → default gray
   */
  const getAssigneeBadgeColorForUser = (user: AssignedUser): { bg: string; text: string } => {
    const badge = getMergedBadgePrefs(user);
    if (badge?.bg_color && badge?.text_color) {
      return { bg: badge.bg_color, text: badge.text_color };
    }
    
    // Non-staff get default
    if (!user.is_staff) return defaultAssigneeBadge;
    
    // Staff without prefs get auto-assigned color
    return getAssigneeBadgeColor(user);
  };

  /**
   * Get initials for badge display
   * Priority: user's prefs.badge.initials → auto-generated from name
   */
  const getAssigneeInitialsForUser = (user: AssignedUser): string => {
    const badge = getMergedBadgePrefs(user);
    if (badge?.initials) {
      return badge.initials;
    }
    return getInitials(user.name);
  };
  
  // Critical path styling - red left border and subtle red tint
  const isCritical = task.isCritical === true;
  
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "4px",
        height: "100%",
        paddingLeft: "8px",  // Increased padding to leave room for drag handles
        paddingRight: "8px", // Increased padding to leave room for drag handles
        overflow: "hidden",
        // Critical path: red left border
        borderLeft: isCritical ? "3px solid #dc2626" : "none",
        marginLeft: isCritical ? "-3px" : "0",
        // Subtle red background tint for critical path
        backgroundColor: isCritical ? "rgba(239, 68, 68, 0.15)" : "transparent",
        // Allow pointer events to pass through to parent for edge resizing
        pointerEvents: "none",
      }}
      title={isCritical ? "Critical Path" : undefined}
    >
      {/* Critical Path Badge */}
      {isCritical && (
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            minWidth: "18px",
            height: "18px",
            padding: "0 3px",
            borderRadius: "4px",
            fontSize: "9px",
            fontWeight: 700,
            backgroundColor: "#dc2626",
            color: "#ffffff",
            flexShrink: 0,
            pointerEvents: "auto", // Re-enable pointer events for badges
          }}
          title="Critical Path"
        >
          CP
        </span>
      )}
      
      {/* Priority Badge */}
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          minWidth: "18px",
          height: "18px",
          padding: "0 4px",
          borderRadius: "4px",
          fontSize: "10px",
          fontWeight: 600,
          backgroundColor: priorityColor.bg,
          color: priorityColor.text,
          flexShrink: 0,
          pointerEvents: "auto", // Re-enable pointer events for badges
        }}
        title={`Priority: ${priority}`}
      >
        {priorityShortLabel[priority] || "M"}
      </span>
      
      {/* Assignee Badge */}
      {firstAssigned && (
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            minWidth: "22px",
            height: "18px",
            padding: "0 4px",
            borderRadius: "4px",
            fontSize: "10px",
            fontWeight: 500,
            backgroundColor: getAssigneeBadgeColorForUser(firstAssigned).bg,
            color: getAssigneeBadgeColorForUser(firstAssigned).text,
            flexShrink: 0,
            pointerEvents: "auto", // Re-enable pointer events for badges
          }}
          title={firstAssigned.name || String(firstAssigned.id)}
        >
          {getAssigneeInitialsForUser(firstAssigned)}
        </span>
      )}
      
      {/* Task Text */}
      <span
        style={{
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          flex: 1,
          fontSize: "12px",
          pointerEvents: "auto", // Re-enable pointer events for text (double-click to edit)
        }}
      >
        {task.text}
      </span>
    </div>
  );
};

export default withDevIdentifier(GanttTaskTemplate, 'GanttTaskTemplate');
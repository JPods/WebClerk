/* LastChecked: 2026-07-29 | WhereUsed: UnifiedGantt | WhoCreated: Bill+Claude */
/**
 * GanttTaskTemplate — Layered task bar with multi-dimensional visual encoding
 *
 * Layout:
 * ┌─ top stripe: priority color ──────────────────────────────────┐
 * │ █ Task name                                        J.Smith    │
 * │ █ status                                                      │
 * └─ bottom bar: ████████░░░░░ % complete ────────────────────────┘
 *   │
 *   left stripe: status color
 *
 * Four dimensions, zero clutter:
 *   Top stripe — priority (red=critical, orange=high, yellow=medium, green=low)
 *   Left stripe — status (blue=active, green=done, red=blocked, gray=hold)
 *   Bottom bar — percent complete (filled portion of bar)
 *   Person name — right-aligned in their assigned color
 */
import { type FC, useState, useCallback } from "react";
import type { ITask, IApi } from "@svar-ui/react-gantt";
import type { GanttMappedTask, AssignedUser, BadgePrefs } from "./ganttDataMapper";
import { useStaffBadgePrefsOptional } from "../../../context/StaffBadgePrefsContext";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

// ── Priority colors (top stripe + badge) ──
// low = white/no fill, medium = light blue, high = orange, critical = red
const priorityStripeColors: Record<string, string> = {
  low:      "#e2e8f0",  // very light gray (near white)
  medium:   "#93c5fd",  // light blue
  high:     "#f97316",  // orange
  critical: "#ef4444",  // red
};

// ── Status colors (left stripe) ──
const statusStripeColors: Record<string, string> = {
  open:        "#94a3b8",  // slate gray
  in_progress: "#3b82f6",  // blue
  active:      "#3b82f6",  // blue
  complete:    "#22c55e",  // green
  done:        "#22c55e",  // green
  on_hold:     "#9ca3af",  // gray
  onhold:      "#9ca3af",  // gray
  blocked:     "#ef4444",  // red
  cancelled:   "#6b7280",  // dark gray
  canceled:    "#6b7280",  // dark gray
  draft:       "#d1d5db",  // light gray
};

// ── Staff badge colors ──
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

const defaultAssigneeBadge = { bg: "#f3f4f6", text: "#374151" };

const staffColorCache = new Map<string | number, number>();
let nextStaffColorIndex = 0;

const getAssigneeBadgeColor = (user: AssignedUser, badgePrefsContext: any): { bg: string; text: string } => {
  // Check context prefs first
  const contactId = typeof user.id === "string" ? parseInt(user.id, 10) : user.id;
  if (badgePrefsContext && !Number.isNaN(contactId)) {
    const prefs = badgePrefsContext.getBadgePrefs(contactId);
    if (prefs?.bg_color && prefs?.text_color) {
      return { bg: prefs.bg_color, text: prefs.text_color };
    }
  }
  // Inline prefs
  const badge = user.prefs?.badge;
  if (badge?.bg_color && badge?.text_color) {
    return { bg: badge.bg_color, text: badge.text_color };
  }
  if (!user.is_staff) return defaultAssigneeBadge;
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
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
};

const getAssigneeInitials = (user: AssignedUser, badgePrefsContext: any): string => {
  const contactId = typeof user.id === "string" ? parseInt(user.id, 10) : user.id;
  if (badgePrefsContext && !Number.isNaN(contactId)) {
    const prefs = badgePrefsContext.getBadgePrefs(contactId);
    if (prefs?.initials) return prefs.initials;
  }
  if (user.prefs?.badge?.initials) return user.prefs.badge.initials;
  return getInitials(user.name);
};

// Priority short labels
const priorityShortLabel: Record<string, string> = {
  low: "L", medium: "M", high: "H", critical: "!",
};

// Module-level flags readable by template instances (avoids prop drilling through SVAR)
let _criticalPathHighlight = false;
let _assigneeFilter: string | null = null;

export const setGanttCriticalPathHighlight = (v: boolean) => { _criticalPathHighlight = v; };
export const setGanttAssigneeFilter = (v: string | null) => { _assigneeFilter = v; };

interface GanttTaskTemplateProps {
  data: ITask;
  api: IApi;
  onaction: (ev: { action: string; data: Record<string, any> }) => void;
}

export const GanttTaskTemplate: FC<GanttTaskTemplateProps> = ({ data }) => {
  const task = data as GanttMappedTask;
  const priority = task.priority || "medium";
  const status = (task.columnId || "open").toLowerCase().replace(/\s+/g, '_');
  const percentComplete = task.percentComplete || task.progress || 0;
  const firstAssigned = task.assignedTo?.[0];
  const badgePrefsContext = useStaffBadgePrefsOptional();
  const [emphasized, setEmphasized] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);

  const priorityColor = priorityStripeColors[priority] || priorityStripeColors.medium;
  const statusColor = statusStripeColors[status] || statusStripeColors.open;

  const assigneeColor = firstAssigned
    ? getAssigneeBadgeColor(firstAssigned, badgePrefsContext)
    : null;

  const isCritical = task.isCritical === true;

  // Milestone detection: zero duration or start == end (within 1 day)
  const isMilestone = task.start instanceof Date && task.end instanceof Date &&
    (task.end.getTime() - task.start.getTime()) <= 86400000;

  // Baseline slippage: days slipped from original start
  // Dimming: critical path highlight or assignee filter
  const isDimmed = (_criticalPathHighlight && !isCritical) ||
    (_assigneeFilter !== null && !(task.assignedTo || []).some(
      (a: AssignedUser) => String(a.id) === _assigneeFilter || a.name === _assigneeFilter));

  const slippageDays = (() => {
    if (!task.dtStartOriginal || !(task.dtStartOriginal instanceof Date)) return 0;
    if (!task.start || !(task.start instanceof Date)) return 0;
    const diff = Math.round((task.start.getTime() - task.dtStartOriginal.getTime()) / 86400000);
    return diff; // positive = slipped later, negative = moved earlier
  })();

  // Single click = 5s emphasis border (pointing gesture in meetings)
  const handleClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setEmphasized(true);
    setTimeout(() => setEmphasized(false), 5000);
  }, []);

  // Build hover tooltip text
  const tooltipLines = [
    task.text,
    `Status: ${status.replace(/_/g, ' ')}`,
    `Priority: ${priority}`,
    percentComplete > 0 ? `Progress: ${percentComplete}%` : null,
    firstAssigned?.name ? `Assigned: ${firstAssigned.name}` : null,
    task.start instanceof Date ? `Start: ${task.start.toLocaleDateString()}` : null,
    task.end instanceof Date ? `End: ${task.end.toLocaleDateString()}` : null,
  ].filter(Boolean).join('\n');

  // Milestone: diamond marker with text
  if (isMilestone) {
    return (
      <div
        onClick={handleClick}
        title={tooltipLines}
        style={{
          position: "relative",
          display: "flex",
          alignItems: "center",
          height: "100%",
          overflow: "visible",
          pointerEvents: "auto",
          opacity: isDimmed ? 0.25 : 1,
          transition: "opacity 0.3s ease",
          outline: emphasized ? "2px solid #3b82f6" : "none",
          outlineOffset: "-1px",
          transition: "outline 0.2s ease",
          zIndex: emphasized ? 10 : undefined,
        }}
      >
        {/* Diamond */}
        <div
          style={{
            width: "14px",
            height: "14px",
            backgroundColor: priorityColor,
            transform: "rotate(45deg)",
            flexShrink: 0,
            border: isCritical ? "2px solid #dc2626" : "1px solid rgba(0,0,0,0.2)",
          }}
        />
        {/* Text */}
        <span
          style={{
            marginLeft: "6px",
            whiteSpace: "nowrap",
            fontSize: "inherit",
            color: "#111827",
            overflow: "visible",
          }}
        >
          {task.text}
        </span>
        {firstAssigned && assigneeColor && (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              minWidth: "20px",
              height: "16px",
              padding: "0 4px",
              marginLeft: "4px",
              borderRadius: "3px",
              fontSize: "0.8em",
              fontWeight: 600,
              backgroundColor: assigneeColor.bg,
              color: assigneeColor.text,
              flexShrink: 0,
            }}
          >
            {getAssigneeInitials(firstAssigned, badgePrefsContext)}
          </span>
        )}
      </div>
    );
  }

  return (
    <div
      onClick={handleClick}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      title={tooltipLines}
      style={{
        position: "relative",
        display: "flex",
        flexDirection: "column",
        height: "100%",
        overflow: "var(--gantt-text-overflow, hidden)",
        pointerEvents: "auto",
        opacity: isDimmed ? 0.25 : 1,
        outline: emphasized ? "2px solid #3b82f6" : "none",
        outlineOffset: "-1px",
        transition: "outline 0.2s ease, opacity 0.3s ease",
        zIndex: emphasized ? 10 : undefined,
      }}
    >
      {/* ── Top stripe: priority ── */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "3px",
          backgroundColor: priorityColor,
        }}
        title={`Priority: ${priority}`}
      />

      {/* ── Left stripe: status ── */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          bottom: 0,
          width: "4px",
          backgroundColor: statusColor,
        }}
        title={`Status: ${status.replace(/_/g, ' ')}`}
      />

      {/* ── Bottom bar: % complete ── */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: "3px",
          backgroundColor: "rgba(0,0,0,0.15)",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${Math.min(100, Math.max(0, percentComplete))}%`,
            backgroundColor: percentComplete >= 100 ? "#22c55e" : "#3b82f6",
            transition: "width 0.3s ease",
          }}
          title={`${percentComplete}% complete`}
        />
      </div>

      {/* ── Main content row ── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "4px",
          flex: 1,
          paddingLeft: "10px",
          paddingRight: "8px",
          paddingTop: "3px",
          paddingBottom: "3px",
        }}
      >
        {/* Critical Path Badge */}
        {isCritical && (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              minWidth: "16px",
              height: "16px",
              padding: "0 3px",
              borderRadius: "3px",
              fontSize: "0.7em",
              fontWeight: 700,
              backgroundColor: "#dc2626",
              color: "#ffffff",
              flexShrink: 0,
              pointerEvents: "auto",
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
            minWidth: "16px",
            height: "16px",
            padding: "0 3px",
            borderRadius: "3px",
            fontSize: "0.8em",
            fontWeight: 700,
            backgroundColor: priorityColor,
            color: "#fff",
            flexShrink: 0,
            pointerEvents: "auto",
            textShadow: "0 1px 1px rgba(0,0,0,0.3)",
          }}
          title={`Priority: ${priority}`}
        >
          {priorityShortLabel[priority] || "M"}
        </span>

        {/* Task Text */}
        <span
          style={{
            overflow: "var(--gantt-text-overflow, hidden)",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            flex: 1,
            fontSize: "inherit",
            color: "#111827",
            pointerEvents: "auto",
          }}
        >
          {task.text}
        </span>

        {/* Percent complete text */}
        {percentComplete > 0 && percentComplete < 100 && (
          <span
            style={{
              fontSize: "0.8em",
              color: "#374151",
              flexShrink: 0,
              pointerEvents: "auto",
            }}
          >
            {percentComplete}%
          </span>
        )}

        {/* Slippage badge — shows days slipped from baseline */}
        {slippageDays !== 0 && (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              minWidth: "16px",
              height: "14px",
              padding: "0 3px",
              borderRadius: "3px",
              fontSize: "0.7em",
              fontWeight: 600,
              backgroundColor: slippageDays > 0 ? "#fef2f2" : "#f0fdf4",
              color: slippageDays > 0 ? "#dc2626" : "#16a34a",
              flexShrink: 0,
              pointerEvents: "auto",
            }}
            title={`${slippageDays > 0 ? 'Slipped' : 'Ahead'} ${Math.abs(slippageDays)}d from baseline`}
          >
            {slippageDays > 0 ? '+' : ''}{slippageDays}d
          </span>
        )}

        {/* Assignee badge — right-aligned in their color */}
        {firstAssigned && assigneeColor && (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              minWidth: "20px",
              height: "16px",
              padding: "0 4px",
              borderRadius: "3px",
              fontSize: "0.8em",
              fontWeight: 600,
              backgroundColor: assigneeColor.bg,
              color: assigneeColor.text,
              flexShrink: 0,
              pointerEvents: "auto",
            }}
            title={firstAssigned.name || String(firstAssigned.id)}
          >
            {getAssigneeInitials(firstAssigned, badgePrefsContext)}
          </span>
        )}
      </div>
    </div>
  );
};

export default withDevIdentifier(GanttTaskTemplate, 'GanttTaskTemplate');

/**
 * EnhancedTaskTemplate — Drop-in replacement for @svar-ui/react-gantt taskTemplate
 *
 * Encodes four dimensions in a single task bar:
 *   Top stripe    — priority (red=critical, orange=high, blue=medium, gray=low)
 *   Left stripe   — status (blue=active, green=done, red=blocked, gray=hold)
 *   Bottom bar    — percent complete
 *   Right badge   — assignee initials
 *
 * Single click = 5s emphasis outline (meeting-friendly pointing)
 * Double click = handled by parent Gantt (opens detail)
 * Hover = tooltip with task data
 *
 * Reads CSS custom properties from container:
 *   --gantt-text-overflow: 'hidden' | 'visible'
 *
 * Font size inherits from container — set fontSize on the wrapper div
 * and everything inside scales proportionally.
 *
 * MIT License — https://github.com/webclerk/gantt-enhancements
 */
import { type FC, useState, useCallback } from "react";

// ── Color maps ──

const priorityColors: Record<string, string> = {
  low:      "#e2e8f0",  // light gray
  medium:   "#93c5fd",  // light blue
  high:     "#f97316",  // orange
  critical: "#ef4444",  // red
};

const statusColors: Record<string, string> = {
  open:        "#94a3b8",
  in_progress: "#3b82f6",
  active:      "#3b82f6",
  complete:    "#22c55e",
  done:        "#22c55e",
  on_hold:     "#9ca3af",
  blocked:     "#ef4444",
  cancelled:   "#6b7280",
  draft:       "#d1d5db",
};

const priorityLabel: Record<string, string> = {
  low: "L", medium: "M", high: "H", critical: "!",
};

// ── Badge colors — rotating palette for assignees ──

const badgePalette = [
  { bg: "#dbeafe", text: "#1d4ed8" },
  { bg: "#f3e8ff", text: "#7c3aed" },
  { bg: "#cffafe", text: "#0891b2" },
  { bg: "#fae8ff", text: "#a21caf" },
  { bg: "#d9f99d", text: "#4d7c0f" },
  { bg: "#fef9c3", text: "#a16207" },
  { bg: "#fbcfe8", text: "#be185d" },
  { bg: "#e0e7ff", text: "#4338ca" },
];

const badgeColorCache = new Map<string, number>();
let nextBadgeIndex = 0;

function getBadgeColor(assigneeId: string): { bg: string; text: string } {
  if (!badgeColorCache.has(assigneeId)) {
    badgeColorCache.set(assigneeId, nextBadgeIndex % badgePalette.length);
    nextBadgeIndex++;
  }
  return badgePalette[badgeColorCache.get(assigneeId)!];
}

function getInitials(name?: string): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

// ── Component ──

interface EnhancedTaskTemplateProps {
  data: any;   // ITask from @svar-ui/react-gantt
  api: any;    // IApi
  onaction: (ev: { action: string; data: Record<string, any> }) => void;
}

export const EnhancedTaskTemplate: FC<EnhancedTaskTemplateProps> = ({ data: task }) => {
  const [emphasized, setEmphasized] = useState(false);

  // Extract task properties — adapt these to your data shape
  const priority = task.priority || "medium";
  const status = (task.status || task.columnId || "open").toLowerCase().replace(/\s+/g, '_');
  const percentComplete = task.percentComplete || task.progress || 0;
  const assigneeName = task.assignee || task.assigneeName;
  const assigneeId = task.assigneeId || assigneeName || "";

  const prioColor = priorityColors[priority] || priorityColors.medium;
  const statColor = statusColors[status] || statusColors.open;
  const badge = assigneeId ? getBadgeColor(String(assigneeId)) : null;

  // Single click = 5s emphasis (pointing gesture in meetings)
  const handleClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setEmphasized(true);
    setTimeout(() => setEmphasized(false), 5000);
  }, []);

  // Tooltip
  const tooltip = [
    task.text,
    `Status: ${status.replace(/_/g, ' ')}`,
    `Priority: ${priority}`,
    percentComplete > 0 ? `Progress: ${percentComplete}%` : null,
    assigneeName ? `Assigned: ${assigneeName}` : null,
    task.start instanceof Date ? `Start: ${task.start.toLocaleDateString()}` : null,
    task.end instanceof Date ? `End: ${task.end.toLocaleDateString()}` : null,
  ].filter(Boolean).join('\n');

  return (
    <div
      onClick={handleClick}
      title={tooltip}
      style={{
        position: "relative",
        display: "flex",
        flexDirection: "column",
        height: "100%",
        overflow: "var(--gantt-text-overflow, hidden)",
        pointerEvents: "auto",
        outline: emphasized ? "2px solid #3b82f6" : "none",
        outlineOffset: "-1px",
        transition: "outline 0.2s ease",
        zIndex: emphasized ? 10 : undefined,
      }}
    >
      {/* Top stripe: priority */}
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0,
        height: "3px", backgroundColor: prioColor,
      }} />

      {/* Left stripe: status */}
      <div style={{
        position: "absolute", top: 0, left: 0, bottom: 0,
        width: "4px", backgroundColor: statColor,
      }} />

      {/* Bottom bar: % complete */}
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0,
        height: "3px", backgroundColor: "rgba(0,0,0,0.15)",
      }}>
        <div style={{
          height: "100%",
          width: `${Math.min(100, Math.max(0, percentComplete))}%`,
          backgroundColor: percentComplete >= 100 ? "#22c55e" : "#3b82f6",
          transition: "width 0.3s ease",
        }} />
      </div>

      {/* Main content row */}
      <div style={{
        display: "flex", alignItems: "center", gap: "4px",
        flex: 1, paddingLeft: "10px", paddingRight: "8px",
        paddingTop: "3px", paddingBottom: "3px",
      }}>
        {/* Priority badge */}
        <span style={{
          display: "inline-flex", alignItems: "center", justifyContent: "center",
          minWidth: "16px", height: "16px", padding: "0 3px",
          borderRadius: "3px", fontSize: "0.8em", fontWeight: 700,
          backgroundColor: prioColor, color: "#fff",
          flexShrink: 0, textShadow: "0 1px 1px rgba(0,0,0,0.3)",
        }}>
          {priorityLabel[priority] || "M"}
        </span>

        {/* Task text — inherits font size from container */}
        <span style={{
          overflow: "var(--gantt-text-overflow, hidden)",
          textOverflow: "ellipsis", whiteSpace: "nowrap",
          flex: 1, fontSize: "inherit",
        }}>
          {task.text}
        </span>

        {/* Percent text */}
        {percentComplete > 0 && percentComplete < 100 && (
          <span style={{
            fontSize: "0.8em", color: "rgba(255,255,255,0.7)", flexShrink: 0,
          }}>
            {percentComplete}%
          </span>
        )}

        {/* Assignee badge */}
        {badge && assigneeName && (
          <span style={{
            display: "inline-flex", alignItems: "center", justifyContent: "center",
            minWidth: "20px", height: "16px", padding: "0 4px",
            borderRadius: "3px", fontSize: "0.8em", fontWeight: 600,
            backgroundColor: badge.bg, color: badge.text, flexShrink: 0,
          }}>
            {getInitials(assigneeName)}
          </span>
        )}
      </div>
    </div>
  );
};

export default EnhancedTaskTemplate;

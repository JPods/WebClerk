/* LastChecked: 2026-08-09 | WhereUsed: UnifiedGantt | WhoCreated: Bill+Claude */
/**
 * GanttLinks — SVG dependency arrows between tasks.
 *
 * Renders finish-to-start (and other type) connector lines between
 * linked tasks. Overlays the GanttTimeline chart area.
 */
import { type FC, useMemo, useState, useCallback } from "react";
import type { GanttLink } from "./gantt.types";
import type { GanttMappedTask } from "./ganttDataMapper";

export interface GanttLinksProps {
  links: GanttLink[];
  tasks: (GanttMappedTask & { $x?: number; $y?: number; $w?: number; $h?: number })[];
  cellHeight: number;
  onDeleteLink?: (linkId: string | number) => void;
  criticalTaskIds?: Set<string>;
}

/** Build an SVG path for a dependency arrow */
const buildLinkPath = (
  sx: number, sy: number, // source point
  tx: number, ty: number, // target point
  type: GanttLink["type"],
): string => {
  // Determine source/target attachment points based on link type
  // e2s = end-to-start (most common): right edge of source → left edge of target
  const stubLen = 12;

  if (type === "e2s") {
    // Source exits right, target enters left
    if (tx > sx + stubLen * 2) {
      // Simple right-angle: right stub → vertical → horizontal → in
      const midX = (sx + tx) / 2;
      return `M ${sx},${sy} H ${midX} V ${ty} H ${tx}`;
    }
    // Target is left of or close to source — route around
    const detour = Math.max(sx + stubLen, tx + stubLen + 20);
    const verticalOffset = ty > sy ? stubLen : -stubLen;
    return `M ${sx},${sy} H ${detour} V ${ty} H ${tx}`;
  }

  if (type === "s2s") {
    // Both attach at left edges
    const leftMost = Math.min(sx, tx) - stubLen;
    return `M ${sx},${sy} H ${leftMost} V ${ty} H ${tx}`;
  }

  if (type === "e2e") {
    // Both attach at right edges
    const rightMost = Math.max(sx, tx) + stubLen;
    return `M ${sx},${sy} H ${rightMost} V ${ty} H ${tx}`;
  }

  if (type === "s2e") {
    // Source left → target right
    const midX = (sx + tx) / 2;
    return `M ${sx},${sy} H ${midX} V ${ty} H ${tx}`;
  }

  // Fallback: straight line
  return `M ${sx},${sy} L ${tx},${ty}`;
};

/** Get attachment point on a task bar */
const getAttachPoint = (
  task: { $x?: number; $y?: number; $w?: number; $h?: number },
  side: "start" | "end",
): { x: number; y: number } => {
  const x = task.$x ?? 0;
  const y = task.$y ?? 0;
  const w = task.$w ?? 0;
  const h = task.$h ?? 0;
  return {
    x: side === "start" ? x : x + w,
    y: y + h / 2 + 2, // +2 for the top margin on bars
  };
};

export const GanttLinks: FC<GanttLinksProps> = ({
  links,
  tasks,
  cellHeight,
  onDeleteLink,
  criticalTaskIds,
}) => {
  const [contextMenu, setContextMenu] = useState<{
    x: number; y: number; linkId: string | number;
  } | null>(null);

  // Build task lookup
  const taskMap = useMemo(() => {
    const map = new Map<string, (typeof tasks)[number]>();
    for (const t of tasks) map.set(String(t.id), t);
    return map;
  }, [tasks]);

  // Compute paths
  const paths = useMemo(() => {
    return links
      .map((link) => {
        const sourceTask = taskMap.get(String(link.source));
        const targetTask = taskMap.get(String(link.target));
        if (!sourceTask || !targetTask) return null;
        if (sourceTask.$x === undefined || targetTask.$x === undefined) return null;

        const sourceSide = link.type === "s2s" || link.type === "s2e" ? "start" : "end";
        const targetSide = link.type === "e2e" || link.type === "s2e" ? "end" : "start";

        const sp = getAttachPoint(sourceTask, sourceSide);
        const tp = getAttachPoint(targetTask, targetSide);
        const d = buildLinkPath(sp.x, sp.y, tp.x, tp.y, link.type);

        const isCritical =
          criticalTaskIds?.has(String(link.source)) &&
          criticalTaskIds?.has(String(link.target));

        return { id: link.id, d, isCritical };
      })
      .filter(Boolean) as Array<{ id: string | number; d: string; isCritical: boolean }>;
  }, [links, taskMap, criticalTaskIds]);

  const handleContextMenu = useCallback(
    (e: React.MouseEvent, linkId: string | number) => {
      e.preventDefault();
      e.stopPropagation();
      setContextMenu({ x: e.clientX, y: e.clientY, linkId });
    },
    [],
  );

  const handleDeleteClick = useCallback(() => {
    if (contextMenu && onDeleteLink) {
      onDeleteLink(contextMenu.linkId);
    }
    setContextMenu(null);
  }, [contextMenu, onDeleteLink]);

  // Close context menu on click anywhere
  const handleBackdropClick = useCallback(() => setContextMenu(null), []);

  if (paths.length === 0) return null;

  // SVG dimensions match the chart area
  const maxX = Math.max(...tasks.map((t) => (t.$x ?? 0) + (t.$w ?? 0))) + 50;
  const maxY = tasks.length * cellHeight + 20;

  return (
    <>
      <svg
        className="absolute inset-0"
        width={maxX}
        height={maxY}
        style={{ pointerEvents: "none", overflow: "visible" }}
      >
        {/* Arrowhead marker */}
        <defs>
          <marker
            id="gantt-arrow"
            viewBox="0 0 10 10"
            refX="10"
            refY="5"
            markerWidth="8"
            markerHeight="8"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#6b7280" />
          </marker>
          <marker
            id="gantt-arrow-critical"
            viewBox="0 0 10 10"
            refX="10"
            refY="5"
            markerWidth="8"
            markerHeight="8"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#dc2626" />
          </marker>
        </defs>

        {paths.map((p) => (
          <path
            key={String(p.id)}
            d={p.d}
            fill="none"
            stroke={p.isCritical ? "#dc2626" : "#9ca3af"}
            strokeWidth={p.isCritical ? 2 : 1.5}
            strokeDasharray={p.isCritical ? undefined : "none"}
            markerEnd={`url(#${p.isCritical ? "gantt-arrow-critical" : "gantt-arrow"})`}
            style={{ pointerEvents: "stroke", cursor: "pointer" }}
            onContextMenu={(e) => handleContextMenu(e, p.id)}
          />
        ))}
      </svg>

      {/* Context menu */}
      {contextMenu && (
        <>
          <div
            className="fixed inset-0 z-50"
            onClick={handleBackdropClick}
          />
          <div
            className="fixed z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded shadow-lg py-1 min-w-[140px]"
            style={{ left: contextMenu.x, top: contextMenu.y }}
          >
            <button
              className="w-full text-left px-3 py-1.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
              onClick={handleDeleteClick}
            >
              Delete Link
            </button>
          </div>
        </>
      )}
    </>
  );
};

export default GanttLinks;

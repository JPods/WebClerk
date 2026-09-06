/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import type { CSSProperties } from "react";
import { useDragLayer } from "react-dnd";
import clsx from "clsx";
import type { KanbanTask } from "../../type/kanban";
import { DRAG_TYPE_TASK, type DragItem } from "./dndTypes";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

const layerStyles: CSSProperties = {
  position: "fixed",
  pointerEvents: "none",
  zIndex: 50,
  left: 0,
  top: 0,
  width: "100%",
  height: "100%",
};

const PREVIEW_SIZE = { width: 288, height: 176 }; // approximate card size (w-72, padding)

const getItemStyles = (
  sourceOffset: { x: number; y: number } | null
) => {
  if (!sourceOffset) {
    return { display: "none" } as CSSProperties;
  }
  // Center preview around cursor by offsetting half width/height
  const x = sourceOffset.x - PREVIEW_SIZE.width / 2;
  const y = sourceOffset.y - PREVIEW_SIZE.height / 2;
  const transform = `translate(${x}px, ${y}px)`;
  return {
    transform,
    WebkitTransform: transform,
  } as CSSProperties;
};

interface KanbanDragLayerProps {
  tasks: Record<string, KanbanTask>;
}

  export const KanbanDragLayer: React.FC<KanbanDragLayerProps> = ({ tasks }) => {
    const { item, itemType, isDragging, sourceOffset } = useDragLayer((monitor) => ({
    item: monitor.getItem() as DragItem | null,
    itemType: monitor.getItemType(),
    isDragging: monitor.isDragging(),
      sourceOffset: monitor.getSourceClientOffset(),
  }));

  if (!isDragging || itemType !== DRAG_TYPE_TASK || !item) {
    return null;
  }

  const task = tasks[item.taskId];
  if (!task) {
    return null;
  }

  return (
    <div style={layerStyles}>
        <div style={getItemStyles(sourceOffset)}>
        <div className="w-72 rounded-xl border border-indigo-200 p-4 shadow-2xl ring-2 ring-indigo-200/80 backdrop-blur" style={{ background: 'var(--db-surface)' }}>
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-1">
              <p className="db-font-sm font-semibold" style={{ color: 'var(--db-text)' }}>{task.title}</p>
              {task.description && (
                <p className="db-font-xs line-clamp-2" style={{ color: 'var(--db-text-muted)' }}>{task.description}</p>
              )}
            </div>
            {task.priority && (
              <span
                className={clsx(
                  "inline-flex rounded-full px-2.5 py-1 db-font-xs font-semibold",
                  {
                    "bg-emerald-100 text-emerald-700": task.priority === "low",
                    "bg-amber-100 text-amber-700": task.priority === "medium",
                    "bg-orange-100 text-orange-700": task.priority === "high",
                    "bg-rose-100 text-rose-700": task.priority === "critical",
                  }
                )}
              >
                {task.priority}
              </span>
            )}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2 db-font-xs" style={{ color: 'var(--db-text-muted)' }}>
            {typeof task.percent_complete === "number" && (
              <span className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2 py-1 font-semibold text-indigo-600">
                <span className="h-2 w-2 rounded-full bg-indigo-400" />
                {Math.round(Math.max(0, Math.min(100, task.percent_complete)))}%
              </span>
            )}
            {task.assignee && (
              <span className="inline-flex items-center gap-1 rounded-full px-2 py-1 font-medium" style={{ background: 'var(--db-surface-alt)', color: 'var(--db-text-muted)' }}>
                {task.assignee}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default withDevIdentifier(KanbanDragLayer, 'KanbanDragLayer', 'rose', 'apps/utils/kanban/KanbanDragLayer.tsx');
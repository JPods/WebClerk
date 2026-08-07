/**
 * ActionFloatingWindow — Draggable, resizable floating window for ActionDetailCompact.
 * Used in Gantt and Kanban to view/edit actions without covering the workspace.
 * Closes on Save, Cancel, or Delete. No close × button.
 */
import { useState, useRef, useCallback } from "react";
import { DynamicDetail } from "../../../../../components/common/DynamicDetail";
import type { DynamicDetailActions } from "../../../../../components/common/DynamicDetail";
import { deleteRecord } from "../../../../../api/wcapi";

interface Props {
  actionId: string;
  onClose: () => void;
  onSaved?: () => void;
}

export const ActionFloatingWindow: React.FC<Props> = ({ actionId, onClose, onSaved }) => {
  const [pos, setPos] = useState({ x: Math.max(20, Math.min(200, window.innerWidth / 2 - 300)), y: 60 });
  const [size, setSize] = useState({ w: 600, h: 500 });
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [, forceUpdate] = useState(0);
  const dragRef = useRef<{ startX: number; startY: number; origX: number; origY: number } | null>(null);
  const resizeRef = useRef<{ startX: number; startY: number; origW: number; origH: number } | null>(null);
  const windowRef = useRef<HTMLDivElement>(null);
  const actionsRef = useRef<DynamicDetailActions | null>(null);

  const handleDelete = useCallback(async () => {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    setDeleting(true);
    try {
      await deleteRecord("action", Number(actionId));
      onSaved?.();
      onClose();
    } catch {
      setDeleting(false);
      setConfirmDelete(false);
    }
  }, [actionId, onClose, onSaved, confirmDelete]);

  const handleSave = useCallback(() => {
    actionsRef.current?.save();
    onSaved?.();
    onClose();
  }, [onClose, onSaved]);

  const handleCancel = useCallback(() => {
    actionsRef.current?.cancel();
    onClose();
  }, [onClose]);

  // Drag handlers
  const onDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragRef.current = { startX: e.clientX, startY: e.clientY, origX: pos.x, origY: pos.y };
    const onMove = (ev: MouseEvent) => {
      if (!dragRef.current) return;
      setPos({
        x: dragRef.current.origX + (ev.clientX - dragRef.current.startX),
        y: Math.max(0, dragRef.current.origY + (ev.clientY - dragRef.current.startY)),
      });
    };
    const onUp = () => {
      dragRef.current = null;
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }, [pos]);

  // Resize handlers
  const onResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    resizeRef.current = { startX: e.clientX, startY: e.clientY, origW: size.w, origH: size.h };
    const onMove = (ev: MouseEvent) => {
      if (!resizeRef.current) return;
      setSize({
        w: Math.max(280, resizeRef.current.origW + (ev.clientX - resizeRef.current.startX)),
        h: Math.max(200, resizeRef.current.origH + (ev.clientY - resizeRef.current.startY)),
      });
    };
    const onUp = () => {
      resizeRef.current = null;
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }, [size]);

  const actions = actionsRef.current;
  const btnBase = "rounded px-2 py-0.5 text-[10px] font-medium";

  return (
    <div
      ref={windowRef}
      className="fixed z-50 flex flex-col rounded-lg border border-gray-300 bg-white shadow-2xl dark:border-gray-600 dark:bg-gray-900"
      style={{
        left: pos.x,
        top: pos.y,
        width: size.w,
        height: size.h,
      }}
    >
      {/* Title bar — draggable */}
      <div
        onMouseDown={onDragStart}
        className="flex shrink-0 cursor-move items-center justify-between rounded-t-lg border-b border-gray-200 bg-gray-50 px-3 py-1.5 dark:border-gray-700 dark:bg-gray-800"
      >
        <div className="flex items-center gap-2 select-none">
          {actions?.ida && (
            <span className="font-mono text-[10px] text-gray-400">{actions.ida}</span>
          )}
          <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
            Action #{actionId}
          </span>
        </div>
        <div className="flex flex-1 items-center justify-between ml-4">
          <div className="flex items-center gap-1">
            <button onClick={handleSave} disabled={actions?.saving}
              className={`${btnBase} bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50`}>
              {actions?.saving ? "..." : "Save"}</button>
            <button onClick={handleCancel}
              className={`${btnBase} border border-gray-300 text-gray-600 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300`}>Cancel</button>
            <select
              value={actions?.fontSize ?? 12}
              onMouseDown={(e) => e.stopPropagation()}
              onChange={(e) => { actionsRef.current?.setFontSize(Number(e.target.value)); forceUpdate(n => n + 1); }}
              className={`${btnBase} border border-gray-300 text-gray-500 hover:bg-gray-100 dark:border-gray-600 cursor-pointer`}
              title="Font size"
            >
              <option value={10}>Font: 10</option>
              <option value={12}>Font: 12</option>
              <option value={14}>Font: 14</option>
              <option value={16}>Font: 16</option>
              <option value={18}>Font: 18</option>
            </select>
          </div>
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleting}
            className={`${btnBase} ${confirmDelete
              ? "bg-red-600 text-white hover:bg-red-700"
              : "border border-red-300 text-red-500 hover:bg-red-50 dark:border-red-700 dark:hover:bg-red-900/30"
            } disabled:opacity-50`}
          >
            {deleting ? "..." : confirmDelete ? "Confirm Delete" : "Delete"}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-3 py-2">
        <DynamicDetail
          modelName="action"
          recordId={actionId}
          onSaved={onSaved}
          hideToolbar
          actionsRef={actionsRef}
          onActionsReady={() => forceUpdate(n => n + 1)}
        />
      </div>

      {/* Resize handle — bottom right corner */}
      <div
        onMouseDown={onResizeStart}
        className="absolute bottom-0 right-0 h-4 w-4 cursor-se-resize"
        style={{
          background: "linear-gradient(135deg, transparent 50%, rgba(156,163,175,0.4) 50%)",
          borderRadius: "0 0 8px 0",
        }}
      />
    </div>
  );
};

export default ActionFloatingWindow;

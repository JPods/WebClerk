/**
 * ActionFloatingWindow — Draggable, resizable floating window for action detail.
 * Uses DynamicDetail with the standard DetailToolbar (same as db.detail).
 * Includes photo/video upload for job site documentation and QA.
 * Used in Gantt and Kanban to view/edit actions without covering the workspace.
 */
import { useState, useRef, useCallback } from "react";
import { DynamicDetail } from "../../../../../components/common/DynamicDetail";
import type { DynamicDetailActions } from "../../../../../components/common/DynamicDetail";
import { DetailToolbar } from "../../../../../components/common/DetailToolbar";
import { FileUploadPanel } from "../../../../../components/common/FileUploadPanel";
import { deleteRecord } from "../../../../../api/wcapi";
import { useDispatch } from "react-redux";
import { showToast } from "@/store/slices/toastSlice";

interface Props {
  actionId: string;
  onClose: () => void;
  onSaved?: () => void;
}

export const ActionFloatingWindow: React.FC<Props> = ({ actionId, onClose, onSaved }) => {
  const [pos, setPos] = useState({ x: Math.max(20, Math.min(200, window.innerWidth / 2 - 300)), y: 60 });
  const [size, setSize] = useState({ w: 640, h: 560 });
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [, forceUpdate] = useState(0);
  const dragRef = useRef<{ startX: number; startY: number; origX: number; origY: number } | null>(null);
  const resizeRef = useRef<{ startX: number; startY: number; origW: number; origH: number } | null>(null);
  const windowRef = useRef<HTMLDivElement>(null);
  const actionsRef = useRef<DynamicDetailActions | null>(null);
  const dispatch = useDispatch();

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
        className="flex shrink-0 cursor-move items-center gap-2 rounded-t-lg border-b border-gray-200 bg-gray-50 px-2 py-0.5 dark:border-gray-700 dark:bg-gray-800 select-none"
      >
        {actions?.ida && (
          <span className="font-mono text-[10px] text-gray-400">{actions.ida}</span>
        )}
        <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
          Action #{actionId}
        </span>
        <span className="flex-1" />
        <button onClick={onClose}
          className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-sm px-1"
          title="Close">×</button>
      </div>

      {/* Standard DetailToolbar — same as db.detail */}
      <DetailToolbar
        data={actions?.data}
        currentData={actions?.currentData}
        modelName="action"
        isEditing={true}
        saving={actions?.saving}
        canDelete={true}
        onSave={handleSave}
        onCancel={handleCancel}
        onDelete={handleDelete}
      />

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

        {/* File upload — creates Document record per file */}
        <FileUploadPanel
          modelName="action"
          recordId={actionId}
          recordIda={actions?.ida}
          className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700"
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

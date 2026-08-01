/**
 * ActionFloatingWindow — Draggable, resizable floating window for ActionDetailCompact.
 * Used in Gantt and Kanban to view/edit actions without covering the workspace.
 */
import { useState, useRef, useCallback, useEffect } from "react";
import ActionDetailCompact from "./ActionDetailCompact";

interface Props {
  actionId: string;
  onClose: () => void;
  onSaved?: () => void;
}

export const ActionFloatingWindow: React.FC<Props> = ({ actionId, onClose, onSaved }) => {
  const [pos, setPos] = useState({ x: Math.max(20, Math.min(200, window.innerWidth / 2 - 190)), y: 60 });
  const [size, setSize] = useState({ w: 380, h: 340 });
  const dragRef = useRef<{ startX: number; startY: number; origX: number; origY: number } | null>(null);
  const resizeRef = useRef<{ startX: number; startY: number; origW: number; origH: number } | null>(null);
  const windowRef = useRef<HTMLDivElement>(null);

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
        <span className="text-xs font-medium text-gray-600 dark:text-gray-300 select-none">
          Action #{actionId}
        </span>
        <button
          type="button"
          onClick={onClose}
          className="rounded p-0.5 text-gray-400 hover:bg-gray-200 hover:text-gray-600 dark:hover:bg-gray-700"
        >
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>

      {/* Content — scrollable */}
      <div className="flex-1 overflow-y-auto px-3 py-2">
        <ActionDetailCompact
          actionId={actionId}
          onClose={onClose}
          onSaved={onSaved}
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

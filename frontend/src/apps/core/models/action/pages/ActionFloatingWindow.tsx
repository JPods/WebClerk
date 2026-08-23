/**
 * ActionFloatingWindow — Draggable, resizable floating window for action detail.
 * Uses DynamicDetail with the standard DetailToolbar (same as db.detail).
 * Includes photo/video upload for job site documentation and QA.
 * Used in Gantt and Kanban to view/edit actions without covering the workspace.
 */
import { useState, useRef, useCallback, useEffect } from "react";
import { DynamicDetail } from "../../../../../components/common/DynamicDetail";
import type { DynamicDetailActions } from "../../../../../components/common/DynamicDetail";
import { DetailToolbar } from "../../../../../components/common/DetailToolbar";
import { deleteRecord, getRecords, saveRecord } from "@/api/wcapi";
import { formatDt } from "@/utils/fieldFormatters";
import { useDispatch } from "react-redux";
import { showToast } from "@/store/slices/toastSlice";
import { TouchForm, type TouchFormContext } from "@/pages/admin/TouchForm";

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
  const [touches, setTouches] = useState<any[]>([]);
  const [showTouches, setShowTouches] = useState(false);
  const [addingTouch, setAddingTouch] = useState<string | null>(null); // channel type or null
  const dragRef = useRef<{ startX: number; startY: number; origX: number; origY: number } | null>(null);
  const resizeRef = useRef<{ startX: number; startY: number; origW: number; origH: number } | null>(null);
  const windowRef = useRef<HTMLDivElement>(null);
  const actionsRef = useRef<DynamicDetailActions | null>(null);
  const dispatch = useDispatch();

  // Fetch touch records for this action
  useEffect(() => {
    getRecords('touch', { action: actionId }).then((res: any) => {
      setTouches(res?.records || res?.results || []);
    }).catch(() => {});
  }, [actionId]);

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
        <button
          onClick={() => setShowTouches(!showTouches)}
          className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold transition-colors ${
            touches.length > 0
              ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200 hover:bg-amber-200 dark:hover:bg-amber-800'
              : 'bg-gray-100 text-gray-400 dark:bg-gray-700 dark:text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-600'
          }`}
          title={`${touches.length} touch record${touches.length !== 1 ? 's' : ''}`}
        >
          📞 {touches.length}
        </button>
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

      {/* Touch records panel */}
      {showTouches && (
        <div className="shrink-0 max-h-64 overflow-y-auto border-b border-gray-200 dark:border-gray-700 bg-amber-50 dark:bg-amber-950/30 px-3 py-2">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-amber-800 dark:text-amber-200">
              Touches ({touches.length})
            </span>
            <div className="flex items-center gap-2">
              {/* Channel select — pick type to add */}
              <select
                value=""
                onChange={(e) => {
                  setAddingTouch(e.target.value);
                  setTouchForm({ subject: '', summary: '', direction: 'out' });
                }}
                className="text-[10px] font-semibold bg-transparent text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-700 rounded px-1 py-0.5 cursor-pointer"
                title="Add a touch record"
              >
                <option value="">+ Add Touch...</option>
                <option value="call">📞 Phone Call</option>
                <option value="email">✉️ Email</option>
                <option value="visit">🏢 Visit</option>
                <option value="text">💬 Text/SMS</option>
                <option value="meeting">🤝 Meeting</option>
              </select>
              <button
                onClick={() => { setShowTouches(false); setAddingTouch(null); }}
                className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >×</button>
            </div>
          </div>

          {/* Inline add form — unified TouchForm */}
          {addingTouch && (
            <div className="mb-2">
              <TouchForm
                mode="inline"
                ctx={{
                  model: 'action',
                  recordId: Number(actionId),
                  contactId: 0,
                  contactName: '',
                  contactPhone: '',
                  contactEmail: '',
                  orgId: 0,
                  orgModel: '',
                  defaultSubject: '',
                  defaultChannel: addingTouch as any,
                }}
                onClose={() => setAddingTouch(null)}
                onSaved={async () => {
                  const res = await getRecords('touch', { action: actionId });
                  setTouches(res?.records || res?.results || []);
                  dispatch(showToast({ message: 'Touch saved', type: 'success' }));
                }}
              />
            </div>
          )}

          {touches.length > 0 ? (
            <table className="w-full text-[11px]">
              <thead>
                <tr className="text-left text-gray-500 dark:text-gray-400 border-b border-amber-200 dark:border-amber-800">
                  <th className="py-0.5 pr-2">Date</th>
                  <th className="py-0.5 pr-2">Channel</th>
                  <th className="py-0.5 pr-2">Dir</th>
                  <th className="py-0.5">Subject</th>
                </tr>
              </thead>
              <tbody>
                {touches.map((t: any) => (
                  <tr key={t.id} className="border-b border-amber-100 dark:border-amber-900/50">
                    <td className="py-0.5 pr-2 whitespace-nowrap text-gray-600 dark:text-gray-300">
                      {t.dt_created ? formatDt(t.dt_created, 'date') : '—'}
                    </td>
                    <td className="py-0.5 pr-2 text-gray-700 dark:text-gray-200">{t.channel || '—'}</td>
                    <td className="py-0.5 pr-2 text-gray-500 dark:text-gray-400">{t.direction === 'in' ? '←' : '→'}</td>
                    <td className="py-0.5 text-gray-700 dark:text-gray-200 truncate max-w-[200px]">{t.subject || t.summary?.slice(0, 60) || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : !addingTouch ? (
            <p className="text-[11px] text-gray-400 dark:text-gray-500 py-1">No touches yet. Use the dropdown above to add one.</p>
          ) : null}
        </div>
      )}

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

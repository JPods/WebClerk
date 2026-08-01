/**
 * ActionDetailCompact — Minimal floating detail for Gantt/Kanban.
 * Labels match schema field names exactly. Expand button opens full detail.
 */
import { useEffect, useState, useCallback } from "react";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { getRecord } from "../../../../../api/wcapi";
import { patchAction } from "../../../../../api/userProfile";
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import ContactCard from "../../contact/pages/ContactCard";
import SprintBurndown from "./SprintBurndown";

interface ActionDetailCompactProps {
  actionId: string;
  onClose?: () => void;
  onSaved?: () => void;
}

const iClass = "w-full px-1.5 py-0.5 text-xs border border-gray-300 rounded bg-white dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-60";
const sClass = iClass;
const lClass = "text-[11px] text-gray-500 dark:text-gray-400 whitespace-nowrap min-w-[80px] font-mono";

function ActionDetailCompact({ actionId, onClose, onSaved }: ActionDetailCompactProps) {
  const dispatch = useDispatch();
  const [data, setData] = useState<any>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  const [action, setAction] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState(1);
  const [difficulty, setDifficulty] = useState(1);
  const [percentComplete, setPercentComplete] = useState(0);
  const [assignedTo, setAssignedTo] = useState("");
  const [dtStart, setDtStart] = useState("");
  const [dtDeadline, setDtDeadline] = useState("");
  const [fontScale, setFontScale] = useState(0);
  const [contactCard, setContactCard] = useState<{ id: string | number; x: number; y: number } | null>(null);

  useEffect(() => {
    if (!actionId) return;
    getRecord("action", Number(actionId)).then((resp: any) => {
      const r = resp?.record || resp;
      if (!r) return;
      setData(r);
      setAction(r.action?.en || "");
      setDescription(r.description?.en || "");
      setStatus(r.status || "");
      setPriority(r.priority || 1);
      setDifficulty(r.difficulty || 1);
      setPercentComplete(r.percent_complete || 0);
      const at = r.assigned_to;
      setAssignedTo(
        typeof at === 'string' ? at :
        Array.isArray(at) ? (at[0]?.name || at[0] || "") :
        at?.lead || ""
      );
      const fmt = (ms: any) => {
        if (!ms) return "";
        const d = new Date(typeof ms === 'number' ? ms : ms);
        return isNaN(d.getTime()) ? "" : d.toISOString().split('T')[0];
      };
      setDtStart(fmt(r.dt_start));
      setDtDeadline(fmt(r.dt_deadline));
    }).catch(() => {});
  }, [actionId]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const payload: Record<string, any> = {
        model_name: "action",
        id: actionId,
        action: { mode: "update", value: { en: action } },
        description: { mode: "update", value: { en: description } },
        status: { mode: "update", value: status },
        priority: { mode: "update", value: priority },
        difficulty: { mode: "update", value: difficulty },
        percent_complete: { mode: "update", value: percentComplete },
      };
      if (dtStart) payload.dt_start = { mode: "update", value: new Date(dtStart).getTime() };
      if (dtDeadline) payload.dt_deadline = { mode: "update", value: new Date(dtDeadline).getTime() };
      await patchAction(payload);
      dispatch(showToast({ message: "Saved", type: "success" }));
      setEditing(false);
      onSaved?.();
    } catch (e: any) {
      dispatch(showToast({ message: e.message || "Save failed", type: "error" }));
    } finally {
      setSaving(false);
    }
  }, [actionId, action, description, status, priority, difficulty, percentComplete, dtStart, dtDeadline, dispatch, onSaved]);

  const fontSize = 12 + fontScale;

  if (!data) return <div className="py-4 text-center text-xs text-gray-400">Loading...</div>;

  const disabled = !editing;
  const duration = dtStart && dtDeadline
    ? Math.max(1, Math.round((new Date(dtDeadline).getTime() - new Date(dtStart).getTime()) / 86400000))
    : null;

  return (
    <div className="space-y-1.5" style={{ fontSize: `${fontSize}px` }}>
      {/* Toolbar */}
      <div className="flex items-center justify-between pb-1">
        <span className="font-mono text-gray-400" style={{ fontSize: '11px' }}>{data.ida || `id:${actionId}`}</span>
        <div className="flex items-center gap-1">
          <button onClick={() => setFontScale(s => s - 1)}
            className="rounded border border-gray-300 px-1 py-0.5 text-[10px] text-gray-500 hover:bg-gray-100 dark:border-gray-600">A-</button>
          <button onClick={() => setFontScale(s => s + 1)}
            className="rounded border border-gray-300 px-1 py-0.5 text-[10px] text-gray-500 hover:bg-gray-100 dark:border-gray-600">A+</button>
          {editing ? (
            <>
              <button onClick={handleSave} disabled={saving}
                className="rounded bg-blue-600 px-2 py-0.5 text-[11px] text-white hover:bg-blue-700 disabled:opacity-50">
                {saving ? "..." : "Save"}
              </button>
              <button onClick={() => setEditing(false)}
                className="rounded border border-gray-300 px-2 py-0.5 text-[11px] dark:border-gray-600">
                Cancel
              </button>
            </>
          ) : (
            <button onClick={() => setEditing(true)}
              className="rounded border border-gray-300 px-2 py-0.5 text-[11px] dark:border-gray-600">
              Edit
            </button>
          )}
        </div>
      </div>

      {/* action */}
      <div className="flex items-center gap-1.5">
        <span className={lClass}>action</span>
        <input value={action} onChange={e => setAction(e.target.value)} disabled={disabled} className={iClass} />
      </div>

      {/* description */}
      <div className="flex items-center gap-1.5">
        <span className={lClass}>description</span>
        <input value={description} onChange={e => setDescription(e.target.value)} disabled={disabled} className={iClass} />
      </div>

      {/* assigned_to · status */}
      <div className="flex items-center gap-1.5">
        <span className={lClass}
          onClick={(e) => {
            if (data?.contact_id) {
              setContactCard({ id: data.contact_id, x: e.clientX, y: e.clientY });
            }
          }}
          style={{ cursor: data?.contact_id ? 'pointer' : undefined, textDecoration: data?.contact_id ? 'underline dotted' : undefined }}
          title={data?.contact_id ? "Click to view contact card" : undefined}
        >assigned_to</span>
        <input value={assignedTo} onChange={e => setAssignedTo(e.target.value)} disabled={disabled} className={iClass + " flex-1"} />
        <span className={lClass}>status</span>
        <select value={status} onChange={e => setStatus(e.target.value)} disabled={disabled} className={sClass + " flex-1"}>
          <option value="">—</option>
          <option value="open">Open</option>
          <option value="In progress">In Progress</option>
          <option value="active">Active</option>
          <option value="completed">Completed</option>
          <option value="on hold">On Hold</option>
          <option value="blocked">Blocked</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>
      {/* priority · difficulty · percent_complete — 3 columns */}
      <div className="grid grid-cols-3 gap-1.5">
        <div>
          <div className={lClass}>priority</div>
          <select value={priority} onChange={e => setPriority(Number(e.target.value))} disabled={disabled} className={sClass + " w-full"}>
            <option value={1}>Low</option>
            <option value={2}>Medium</option>
            <option value={3}>High</option>
            <option value={4}>Critical</option>
          </select>
        </div>
        <div>
          <div className={lClass}>difficulty</div>
          <select value={difficulty} onChange={e => setDifficulty(Number(e.target.value))} disabled={disabled} className={sClass + " w-full"}>
            <option value={1}>Easy</option>
            <option value={2}>Average</option>
            <option value={3}>Hard</option>
            <option value={4}>Complex</option>
            <option value={5}>Expert</option>
          </select>
        </div>
        <div>
          <div className={lClass}>% complete</div>
          <select value={percentComplete} onChange={e => setPercentComplete(Number(e.target.value))} disabled={disabled} className={sClass + " w-full"}>
            <option value={0}>0%</option>
            <option value={20}>20%</option>
            <option value={50}>50%</option>
            <option value={70}>70%</option>
            <option value={100}>100%</option>
          </select>
        </div>
      </div>

      {/* dt_start · dt_deadline */}
      <div className="flex items-center gap-1.5">
        <span className={lClass}>dt_start</span>
        <input type="date" value={dtStart} onChange={e => setDtStart(e.target.value)} disabled={disabled} className={iClass + " flex-1"} />
        <span className={lClass}>dt_deadline</span>
        <input type="date" value={dtDeadline} onChange={e => setDtDeadline(e.target.value)} disabled={disabled} className={iClass + " flex-1"} />
        {duration && <span className="text-[10px] text-gray-400 whitespace-nowrap">{duration}d</span>}
      </div>

      {/* project_name (read-only) */}
      {data.project_name && (
        <div className="flex items-center gap-1.5">
          <span className={lClass}>project</span>
          <span className="text-xs text-gray-600 dark:text-gray-300 truncate">{data.project_name}</span>
        </div>
      )}

      {/* Contact card popup */}
      {contactCard && (
        <ContactCard
          contactId={contactCard.id}
          position={{ x: contactCard.x, y: contactCard.y }}
          onClose={() => setContactCard(null)}
        />
      )}

      {/* Sprint burndown — shown when this is a sprint action */}
      {data.project_id && (
        <SprintBurndown projectId={data.project_id} compact />
      )}

      {/* Expand to full detail */}
      <div className="border-t border-gray-200 pt-1.5 dark:border-gray-700">
        <button
          onClick={() => {
            window.open(`/core/actions/detail/${actionId}`, '_blank');
          }}
          className="w-full rounded border border-gray-300 py-1 text-[11px] text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
        >
          Open Full Detail
        </button>
      </div>
    </div>
  );
}

export default withDevIdentifier(ActionDetailCompact, 'ActionDetailCompact');

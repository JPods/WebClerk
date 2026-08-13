/**
 * SerialActionPanel — Submit actions to serial.config.actions[]
 *
 * Displays the serial's action history (config.actions[]) and provides
 * a form to submit new actions. Action types come from Setting ida='serial'
 * config.serial_actions[]. Fields show/hide based on action definition
 * (requires_document, notes_required, captures_cost, captures_price).
 *
 * After submit: appends to config.actions[], updates serial status,
 * saves via PATCH /api/serial/{id}/.
 */
import { useEffect, useState, useMemo, useCallback } from "react";
import { getRecord, getRecords, saveRecord } from "@/api/wcapi";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import {
  Plus,
  Clock,
  FileText,
  DollarSign,
  CheckCircle,
  AlertCircle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import ComponentCard from "@/components/common/ComponentCard";
import { Input, Button, TextArea } from "@/components/wrapper";
import { formatDt as fmtDt } from '@/utils/fieldFormatters';

// -- Types ------------------------------------------------------------------

interface SerialActionDef {
  name: string;
  status_result: string;
  document_type: string;
  direction: string;
  clears_customer: boolean;
  captures_cost: boolean;
  captures_price: boolean;
  is_reversible: boolean;
  requires_document: boolean;
  notes_required: boolean;
}

interface ActionEntry {
  action: string;
  dt: number;
  status_before: string | null;
  status_after: string;
  doc_type?: string;
  doc_id?: number;
  cost?: number;
  price?: number;
  discount?: number;
  notes?: string;
  by?: string;
}

interface SerialActionPanelProps {
  serialId: number;
  serialData: any;
  onActionSubmitted?: (updatedData: any) => void;
  isEditing?: boolean;
}

// -- Component --------------------------------------------------------------

export default function SerialActionPanel({
  serialId,
  serialData,
  onActionSubmitted,
  isEditing = true,
}: SerialActionPanelProps) {
  const dispatch = useDispatch();
  const [actionDefs, setActionDefs] = useState<SerialActionDef[]>([]);
  const [selectedAction, setSelectedAction] = useState<SerialActionDef | null>(null);
  const [docType, setDocType] = useState("");
  const [docId, setDocId] = useState("");
  const [notes, setNotes] = useState("");
  const [cost, setCost] = useState("");
  const [price, setPrice] = useState("");
  const [discount, setDiscount] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [historyExpanded, setHistoryExpanded] = useState(true);

  // Load action definitions from Setting
  useEffect(() => {
    const loadActionDefs = async () => {
      try {
        const result = await getRecords("setting", { ida: "serial" });
        const settings = result?.items || result?.data?.items || [];
        if (settings.length > 0) {
          const serialSetting = settings[0];
          const defs = serialSetting?.config?.serial_actions || [];
          setActionDefs(defs);
        }
      } catch (err) {
        console.error("Failed to load serial action definitions:", err);
      }
    };
    loadActionDefs();
  }, []);

  // Current actions from config
  const actions: ActionEntry[] = useMemo(() => {
    return serialData?.config?.actions || [];
  }, [serialData]);

  // Reset form
  const resetForm = useCallback(() => {
    setSelectedAction(null);
    setDocType("");
    setDocId("");
    setNotes("");
    setCost("");
    setPrice("");
    setDiscount("");
    setShowForm(false);
  }, []);

  // Submit action
  const handleSubmit = async () => {
    if (!selectedAction) return;

    const now = Date.now();
    const newAction: ActionEntry = {
      action: selectedAction.name,
      dt: now,
      status_before: serialData?.status || null,
      status_after: selectedAction.status_result || serialData?.status,
    };

    if (docType) newAction.doc_type = docType;
    if (docId) newAction.doc_id = parseInt(docId, 10);
    if (notes) newAction.notes = notes;
    if (cost) newAction.cost = parseFloat(cost);
    if (price) newAction.price = parseFloat(price);
    if (discount) newAction.discount = parseFloat(discount);

    // Build updated config
    const updatedConfig = { ...(serialData?.config || {}) };
    const updatedActions = [...(updatedConfig.actions || []), newAction];
    updatedConfig.actions = updatedActions;

    // Build save payload
    const payload: any = {
      id: serialId,
      config: updatedConfig,
    };

    // Update status if action changes it
    if (selectedAction.status_result) {
      payload.status = selectedAction.status_result;
    }

    try {
      setSubmitting(true);
      await saveRecord("serial", payload);
      dispatch(
        showToast({
          message: `Action recorded: ${selectedAction.name}`,
          type: "success",
        })
      );
      resetForm();
      onActionSubmitted?.({ ...serialData, config: updatedConfig, status: selectedAction.status_result || serialData?.status });
    } catch (err) {
      console.error("Failed to submit action:", err);
      dispatch(
        showToast({ message: "Failed to record action", type: "error" })
      );
    } finally {
      setSubmitting(false);
    }
  };

  // Format timestamp
  const formatDtLocal = (dt: number) => {
    if (!dt) return "--";
    return fmtDt(dt, 'datetime');
  };

  return (
    <ComponentCard>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-slate-900 dark:text-white">
          Serial Actions
          <span className="ml-2 text-sm font-normal text-slate-500">
            ({actions.length} recorded)
          </span>
        </h3>
        {isEditing && !showForm && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowForm(true)}
          >
            <Plus size={14} className="mr-1" />
            Add Action
          </Button>
        )}
      </div>

      {/* New Action Form */}
      {showForm && (
        <div className="mb-6 p-4 border border-slate-200 dark:border-slate-700 rounded-lg bg-slate-50 dark:bg-slate-800">
          <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">
            Record New Action
          </h4>

          {/* Action selector */}
          <div className="mb-3">
            <label className="block text-xs text-slate-500 mb-1">Action</label>
            <select
              className="w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-sm text-slate-900 dark:text-white"
              value={selectedAction?.name || ""}
              onChange={(e) => {
                const def = actionDefs.find((a) => a.name === e.target.value);
                setSelectedAction(def || null);
                if (def?.document_type) setDocType(def.document_type);
              }}
            >
              <option value="">Select an action...</option>
              {actionDefs.map((def) => (
                <option key={def.name} value={def.name}>
                  {def.name}
                  {def.status_result ? ` → ${def.status_result}` : ""}
                </option>
              ))}
            </select>
          </div>

          {/* Conditional fields based on action definition */}
          {selectedAction && (
            <>
              {/* Document reference */}
              {(selectedAction.requires_document ||
                selectedAction.document_type) && (
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">
                      Document Type
                    </label>
                    <Input
                      type="text"
                      value={docType}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                        setDocType(e.target.value)
                      }
                      placeholder="order, invoice, purchase..."
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">
                      Document ID
                    </label>
                    <Input
                      type="number"
                      value={docId}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                        setDocId(e.target.value)
                      }
                      placeholder="ID"
                    />
                  </div>
                </div>
              )}

              {/* Cost/Price */}
              {(selectedAction.captures_cost ||
                selectedAction.captures_price) && (
                <div className="grid grid-cols-3 gap-3 mb-3">
                  {selectedAction.captures_cost && (
                    <div>
                      <label className="block text-xs text-slate-500 mb-1">
                        <DollarSign size={12} className="inline mr-1" />
                        Cost
                      </label>
                      <Input
                        type="number"
                        step="0.01"
                        value={cost}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                          setCost(e.target.value)
                        }
                        placeholder="0.00"
                      />
                    </div>
                  )}
                  {selectedAction.captures_price && (
                    <>
                      <div>
                        <label className="block text-xs text-slate-500 mb-1">
                          <DollarSign size={12} className="inline mr-1" />
                          Price
                        </label>
                        <Input
                          type="number"
                          step="0.01"
                          value={price}
                          onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                            setPrice(e.target.value)
                          }
                          placeholder="0.00"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-slate-500 mb-1">
                          Discount
                        </label>
                        <Input
                          type="number"
                          step="0.01"
                          value={discount}
                          onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                            setDiscount(e.target.value)
                          }
                          placeholder="0.00"
                        />
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Notes */}
              <div className="mb-3">
                <label className="block text-xs text-slate-500 mb-1">
                  Notes
                  {selectedAction.notes_required && (
                    <span className="text-red-500 ml-1">*</span>
                  )}
                </label>
                <TextArea
                  value={notes}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                    setNotes(e.target.value)
                  }
                  placeholder="Action notes..."
                  rows={2}
                />
              </div>

              {/* Status change indicator */}
              {selectedAction.status_result && (
                <div className="mb-3 text-sm text-slate-600 dark:text-slate-400">
                  Status will change:{" "}
                  <span className="font-medium text-slate-900 dark:text-white">
                    {serialData?.status || "—"}
                  </span>{" "}
                  →{" "}
                  <span className="font-medium text-blue-600 dark:text-blue-400">
                    {selectedAction.status_result}
                  </span>
                </div>
              )}

              {/* Submit / Cancel */}
              <div className="flex gap-2">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleSubmit}
                  disabled={
                    submitting ||
                    (selectedAction.notes_required && !notes.trim()) ||
                    (selectedAction.requires_document && !docId)
                  }
                >
                  {submitting ? "Recording..." : "Record Action"}
                </Button>
                <Button variant="outline" size="sm" onClick={resetForm}>
                  Cancel
                </Button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Action History */}
      <div>
        <button
          className="flex items-center gap-1 text-sm font-medium text-slate-700 dark:text-slate-300 mb-2"
          onClick={() => setHistoryExpanded(!historyExpanded)}
        >
          {historyExpanded ? (
            <ChevronUp size={14} />
          ) : (
            <ChevronDown size={14} />
          )}
          Action History
        </button>

        {historyExpanded && (
          <div className="space-y-2">
            {actions.length === 0 ? (
              <p className="text-sm text-slate-500">No actions recorded yet</p>
            ) : (
              [...actions].reverse().map((act, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-3 p-3 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-lg"
                >
                  <div className="mt-0.5">
                    {act.status_after === "damaged" ||
                    act.status_after === "scrapped" ? (
                      <AlertCircle
                        size={16}
                        className="text-red-500"
                      />
                    ) : (
                      <CheckCircle
                        size={16}
                        className="text-green-500"
                      />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-slate-900 dark:text-white">
                      {act.action}
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      <Clock size={10} className="inline mr-1" />
                      {formatDtLocal(act.dt)}
                      {act.by && ` · ${act.by}`}
                      {act.status_before && act.status_after && (
                        <span className="ml-2">
                          {act.status_before} → {act.status_after}
                        </span>
                      )}
                    </div>
                    {act.doc_type && (
                      <div className="text-xs text-slate-500 mt-0.5">
                        <FileText size={10} className="inline mr-1" />
                        {act.doc_type}
                        {act.doc_id && ` #${act.doc_id}`}
                      </div>
                    )}
                    {(act.cost || act.price) && (
                      <div className="text-xs text-slate-500 mt-0.5">
                        <DollarSign size={10} className="inline mr-1" />
                        {act.cost != null && `Cost: ${act.cost}`}
                        {act.cost != null && act.price != null && " · "}
                        {act.price != null && `Price: ${act.price}`}
                        {act.discount ? ` · Disc: ${act.discount}` : ""}
                      </div>
                    )}
                    {act.notes && (
                      <div className="text-xs text-slate-600 dark:text-slate-400 mt-1 italic">
                        {act.notes}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </ComponentCard>
  );
}

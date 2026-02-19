import { useEffect, useState } from "react";
import { getRecord, saveRecord } from "@/api/wcapi";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import RippleLoader from "@/components/common/RippleLoader";
import { DevBadge } from "@/components/common/DevBadge";
import { Input } from "@/components/wrapper";
import Label from "@/components/form/Label";
import { Calendar, Clock, Percent, DollarSign, User, FileText, Hash } from "lucide-react";

/* ----------------------------------
   Horizontal Field Row Component
   Label on left, input on right (Enterprise standard)
   Compact version for 3-column grid layout
---------------------------------- */
interface HorizontalFieldProps {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
  error?: string;
  required?: boolean;
  icon?: React.ReactNode;
}

function HorizontalField({ label, htmlFor, children, error, required, icon }: HorizontalFieldProps) {
  return (
    <div className="flex items-center gap-2 py-2">
      <Label htmlFor={htmlFor} className="w-24 shrink-0 text-right text-sm font-medium text-slate-600 dark:text-slate-400 flex items-center justify-end gap-1">
        {icon && <span className="text-slate-400">{icon}</span>}
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </Label>
      <div className="flex-1 min-w-0">
        {children}
        {error && <p className="mt-0.5 text-xs text-red-500">{error}</p>}
      </div>
    </div>
  );
}

// Column layout options
const COLUMN_OPTIONS = [
  { value: 2, label: "2" },
  { value: 3, label: "3" },
];

const STORAGE_KEY = "termDetail_columnCount";

interface TermDisplayProps {
  inline?: boolean;
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  onSaved?: () => void;
  onCancelInline?: () => void;
}

export default function TermDisplay({
  inline = false,
  modeProp,
  dataProp,
  onSaved,
  onCancelInline,
}: TermDisplayProps) {
  const [data, setData] = useState<any>(dataProp || {});
  const [loading, setLoading] = useState(false);
  const [columnCount, setColumnCount] = useState<number>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? parseInt(saved, 10) : 3;
  });
  const dispatch = useDispatch();

  // Persist column count preference
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(columnCount));
  }, [columnCount]);

  useEffect(() => {
    if (modeProp === "edit" && dataProp?.id) {
      const fetchData = async () => {
        try {
          setLoading(true);
          const rec = await getRecord('term', dataProp.id);
          setData(rec.record || rec);
        } catch (error) {
          console.error("Failed to fetch record", error);
        } finally {
          setLoading(false);
        }
      };
      fetchData();
    } else if (modeProp === "add") {
      setData({});
    } else if (dataProp) {
      setData(dataProp);
    }
  }, [modeProp, dataProp]);

  const handleSave = async () => {
    try {
      setLoading(true);
      await saveRecord('term', data);
      dispatch(showToast({ message: "Term saved successfully", type: "success" }));
      onSaved?.();
    } catch (error) {
      console.error("Failed to save", error);
      dispatch(showToast({ message: "Failed to save term", type: "error" }));
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    onCancelInline?.();
  };

  const handleFieldChange = (field: string, value: any) => {
    setData({ ...data, [field]: value });
  };

  const isViewMode = modeProp === "view";

  if (loading && modeProp === "edit") {
    return <RippleLoader />;
  }

  return (
    <div className="p-4 space-y-4">
      {/* Header with Title and Column Selector */}
      <div className="flex items-center justify-between border-b pb-3">
        <h2 className="text-xl font-semibold text-slate-800 dark:text-slate-200">
          <DevBadge label="TermDisplay" className="mr-2" />
          {modeProp === "add" ? "Add Term" : modeProp === "edit" ? "Edit Term" : "View Term"}
          {data.name && <span className="ml-2 text-slate-500 font-normal">— {data.name}</span>}
        </h2>
        
        {/* Column Selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Columns:</span>
          <div className="flex border rounded overflow-hidden">
            {COLUMN_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setColumnCount(opt.value)}
                className={`px-2 py-1 text-xs font-medium transition-colors ${
                  columnCount === opt.value
                    ? "bg-blue-500 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Identification Section */}
      <fieldset className="border rounded-lg p-4 bg-slate-50 dark:bg-slate-800/50">
        <legend className="text-sm font-semibold text-slate-700 dark:text-slate-300 px-2">
          Identification
        </legend>
        <div className={`grid grid-cols-1 ${columnCount === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-2'} gap-x-6 gap-y-1`}>
          <HorizontalField label="Code" htmlFor="name" required icon={<Hash size={14} />}>
            <Input
              type="text"
              id="name"
              placeholder="N30, 2%, COD"
              value={data.name || ""}
              onChange={(e) => handleFieldChange("name", e.target.value)}
              disabled={isViewMode}
              className="h-8"
            />
          </HorizontalField>

          <HorizontalField label="Description" htmlFor="description" icon={<FileText size={14} />}>
            <Input
              type="text"
              id="description"
              placeholder="Net 30 Days"
              value={data.description || ""}
              onChange={(e) => handleFieldChange("description", e.target.value)}
              disabled={isViewMode}
              className="h-8"
            />
          </HorizontalField>

          <HorizontalField label="Approved By" htmlFor="approved_by" icon={<User size={14} />}>
            <Input
              type="text"
              id="approved_by"
              placeholder="Approver name"
              value={data.approved_by || ""}
              onChange={(e) => handleFieldChange("approved_by", e.target.value)}
              disabled={isViewMode}
              className="h-8"
            />
          </HorizontalField>
        </div>
      </fieldset>

      {/* Schedule Configuration Section */}
      <fieldset className="border rounded-lg p-4 bg-slate-50 dark:bg-slate-800/50">
        <legend className="text-sm font-semibold text-slate-700 dark:text-slate-300 px-2">
          Schedule Configuration
        </legend>
        <div className={`grid grid-cols-1 ${columnCount === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-2'} gap-x-6 gap-y-1`}>
          <HorizontalField label="Periods" htmlFor="period_count" icon={<Hash size={14} />}>
            <Input
              type="number"
              id="period_count"
              placeholder="1"
              value={data.period_count ?? ""}
              onChange={(e) => handleFieldChange("period_count", e.target.value ? parseInt(e.target.value) : null)}
              disabled={isViewMode}
              className="h-8"
              min={1}
            />
          </HorizontalField>

          <HorizontalField label="Days Due" htmlFor="days_due" icon={<Clock size={14} />}>
            <Input
              type="number"
              id="days_due"
              placeholder="30"
              value={data.days_due ?? ""}
              onChange={(e) => handleFieldChange("days_due", e.target.value ? parseInt(e.target.value) : null)}
              disabled={isViewMode}
              className="h-8"
              min={0}
            />
          </HorizontalField>

          <HorizontalField label="Days/Period" htmlFor="days_in_period" icon={<Clock size={14} />}>
            <Input
              type="number"
              id="days_in_period"
              placeholder="30"
              value={data.days_in_period ?? ""}
              onChange={(e) => handleFieldChange("days_in_period", e.target.value ? parseInt(e.target.value) : null)}
              disabled={isViewMode}
              className="h-8"
              min={0}
            />
          </HorizontalField>

          <HorizontalField label="Start Date" htmlFor="dt_begin" icon={<Calendar size={14} />}>
            <Input
              type="date"
              id="dt_begin"
              value={data.dt_begin || ""}
              onChange={(e) => handleFieldChange("dt_begin", e.target.value || null)}
              disabled={isViewMode}
              className="h-8"
            />
          </HorizontalField>
        </div>
      </fieldset>

      {/* Discount Configuration Section */}
      <fieldset className="border rounded-lg p-4 bg-slate-50 dark:bg-slate-800/50">
        <legend className="text-sm font-semibold text-slate-700 dark:text-slate-300 px-2">
          Discount Configuration
        </legend>
        <div className={`grid grid-cols-1 ${columnCount === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-2'} gap-x-6 gap-y-1`}>
          <HorizontalField label="Discount %" htmlFor="discount_rate" icon={<Percent size={14} />}>
            <Input
              type="number"
              id="discount_rate"
              placeholder="2.0"
              value={data.discount_rate ?? ""}
              onChange={(e) => handleFieldChange("discount_rate", e.target.value ? parseFloat(e.target.value) : null)}
              disabled={isViewMode}
              className="h-8"
              min={0}
              step={0.1}
            />
          </HorizontalField>

          <HorizontalField label="Disc. Days" htmlFor="days_discount" icon={<Clock size={14} />}>
            <Input
              type="number"
              id="days_discount"
              placeholder="10"
              value={data.days_discount ?? ""}
              onChange={(e) => handleFieldChange("days_discount", e.target.value ? parseInt(e.target.value) : null)}
              disabled={isViewMode}
              className="h-8"
              min={0}
            />
          </HorizontalField>
        </div>
      </fieldset>

      {/* Statement Cutoffs Section */}
      <fieldset className="border rounded-lg p-4 bg-slate-50 dark:bg-slate-800/50">
        <legend className="text-sm font-semibold text-slate-700 dark:text-slate-300 px-2">
          Statement Cutoffs
        </legend>
        <div className={`grid grid-cols-1 ${columnCount === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-2'} gap-x-6 gap-y-1`}>
          <HorizontalField label="Inv. Cutoff" htmlFor="day_cut_off_invoice" icon={<DollarSign size={14} />}>
            <Input
              type="number"
              id="day_cut_off_invoice"
              placeholder="Day of month"
              value={data.day_cut_off_invoice ?? ""}
              onChange={(e) => handleFieldChange("day_cut_off_invoice", e.target.value ? parseInt(e.target.value) : null)}
              disabled={isViewMode}
              className="h-8"
              min={1}
              max={31}
            />
          </HorizontalField>

          <HorizontalField label="Due Cutoff" htmlFor="day_cut_off_due" icon={<DollarSign size={14} />}>
            <Input
              type="number"
              id="day_cut_off_due"
              placeholder="Day of month"
              value={data.day_cut_off_due ?? ""}
              onChange={(e) => handleFieldChange("day_cut_off_due", e.target.value ? parseInt(e.target.value) : null)}
              disabled={isViewMode}
              className="h-8"
              min={1}
              max={31}
            />
          </HorizontalField>
        </div>
      </fieldset>

      {/* Action Buttons */}
      <div className="flex gap-2 pt-2 border-t">
        {modeProp !== "view" && (
          <button
            onClick={handleSave}
            disabled={loading}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
          >
            {loading ? "Saving..." : "Save"}
          </button>
        )}
        {inline && (
          <button
            onClick={handleCancel}
            className="px-4 py-2 border border-slate-300 text-slate-700 rounded hover:bg-slate-100 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}
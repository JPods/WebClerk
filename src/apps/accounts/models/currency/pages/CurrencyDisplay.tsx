/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useEffect, useState } from "react";
import { getRecord, saveRecord } from "@/api/wcapi";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import RippleLoader from "@/components/common/RippleLoader";

interface CurrencyDisplayProps {
  inline?: boolean;
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  onSaved?: () => void;
  onCancelInline?: () => void;
}

export default function CurrencyDisplay({
  inline = false,
  modeProp,
  dataProp,
  onSaved,
  onCancelInline,
}: CurrencyDisplayProps) {
  const [data, setData] = useState<any>(dataProp || {});
  const [fields, setFields] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const dispatch = useDispatch();

  // Fetch fields from a sample record
  useEffect(() => {
    const fetchFields = async () => {
      try {
        const rec = await getRecord('currency', 1);
        const record = rec.record || rec;
        setFields(Object.keys(record));
      } catch (error) {
        console.error("Failed to fetch fields", error);
        setFields(['id', 'code', 'name', 'symbol']); // fallback
      }
    };
    fetchFields();
  }, []);

  useEffect(() => {
    if (modeProp === "edit" && dataProp?.id) {
      const fetchData = async () => {
        try {
          setLoading(true);
          const rec = await getRecord('currency', dataProp.id);
          setData(rec.record || rec || {});
        } catch (error) {
          console.error("Failed to fetch record", error);
        } finally {
          setLoading(false);
        }
      };
      fetchData();
    } else if (modeProp === "add") {
      setData({});
    } else {
      setData(dataProp || {});
    }
  }, [modeProp, dataProp]);

  const handleSave = async () => {
    try {
      setLoading(true);
      await saveRecord('currency', data);
      dispatch(showToast({ message: "Currency saved successfully", type: "success" }));
      onSaved?.();
    } catch (error) {
      dispatch(showToast({ message: "Failed to save currency", type: "error" }));
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    onCancelInline?.();
  };

  const handleChange = (field: string, value: any) => {
    setData({ ...data, [field]: value });
  };

  if (loading) return <RippleLoader />;

  return (
    <div className="p-4 space-y-4">
      <h3 className="text-lg font-semibold">
        {modeProp === "add" ? "Add Currency" : modeProp === "edit" ? "Edit Currency" : "View Currency"}
      </h3>
      <div className="grid grid-cols-2 gap-4">
        {fields.map((field) => (
          <div key={field} className="flex flex-col">
            <label className="text-sm font-medium mb-1">{field}</label>
            <input
              type="text"
              value={data[field] || ""}
              onChange={(e) => handleChange(field, e.target.value)}
              disabled={modeProp === "view"}
              className="border rounded px-2 py-1"
            />
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        {modeProp !== "view" && (
          <button
            onClick={handleSave}
            disabled={loading}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Save
          </button>
        )}
        {inline && (
          <button
            onClick={handleCancel}
            className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}
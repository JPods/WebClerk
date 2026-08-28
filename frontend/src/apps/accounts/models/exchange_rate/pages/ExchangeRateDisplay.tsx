/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useEffect, useState } from "react";
import { getRecord, saveRecord } from "@/api/wcapi";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import LoadingSpinner from "@/components/common/LoadingSpinner";

interface ExchangeRateDisplayProps {
  inline?: boolean;
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  onSaved?: () => void;
  onCancelInline?: () => void;
}

export default function ExchangeRateDisplay({
  inline = false,
  modeProp,
  dataProp,
  onSaved,
  onCancelInline,
}: ExchangeRateDisplayProps) {
  const [data, setData] = useState<any>(dataProp || {});
  const [fields, setFields] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const dispatch = useDispatch();

  // Fetch fields from a sample record
  useEffect(() => {
    const fetchFields = async () => {
      try {
        const rec = await getRecord('exchange_rate', 1);
        const record = rec.record || rec;
        setFields(Object.keys(record));
      } catch (error) {
        console.error("Failed to fetch fields", error);
        setFields(['id', 'from_currency', 'to_currency', 'rate', 'date']); // fallback
      }
    };
    fetchFields();
  }, []);

  useEffect(() => {
    if (modeProp === "edit" && dataProp?.id) {
      const fetchData = async () => {
        try {
          setLoading(true);
          const rec = await getRecord('exchange_rate', dataProp.id);
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
      await saveRecord('exchange_rate', data);
      dispatch(showToast({ message: "Exchange Rate saved successfully", type: "success" }));
      onSaved?.();
    } catch (error) {
      dispatch(showToast({ message: "Failed to save exchange rate", type: "error" }));
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

  if (loading) return <LoadingSpinner size="lg" label="Loading..." />;

  return (
    <div data-wc="exchange-rate-display" className="p-4 space-y-4">
      <h3 className="text-lg font-semibold">
        {modeProp === "add" ? "Add Exchange Rate" : modeProp === "edit" ? "Edit Exchange Rate" : "View Exchange Rate"}
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
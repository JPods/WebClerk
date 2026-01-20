import { useEffect, useState } from "react";
import { getRecord, saveRecord } from "@/api/wcapi";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";

interface BaseOrgModelDisplayProps {
  inline?: boolean;
  modeProp?: "add" | "edit" | "view";
  dataProp?: any;
  onSaved?: () => void;
  onCancelInline?: () => void;
}

export default function BaseOrgModelDisplay({
  inline = false,
  modeProp,
  dataProp,
  onSaved,
  onCancelInline,
}: BaseOrgModelDisplayProps) {
  const [data, setData] = useState<any>(dataProp || {});
  const [fields, setFields] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const dispatch = useDispatch();

  // Fetch fields from a sample record
  useEffect(() => {
    const fetchFields = async () => {
      try {
        const rec = await getRecord('base_org_model', 1);
        const record = rec.record || rec;
        setFields(Object.keys(record));
      } catch (error) {
        console.error("Failed to fetch fields", error);
        setFields(['id', 'name', 'type', 'status']); // fallback
      }
    };
    fetchFields();
  }, []);

  useEffect(() => {
    if (modeProp === "edit" && dataProp?.id) {
      const fetchData = async () => {
        try {
          setLoading(true);
          const rec = await getRecord('base_org_model', dataProp.id);
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
      await saveRecord('base_org_model', data);
      dispatch(showToast({ message: "Base Org Model saved successfully", type: "success" }));
      onSaved?.();
    } catch (error) {
      console.error("Failed to save", error);
      dispatch(showToast({ message: "Failed to save base org model", type: "error" }));
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    onCancelInline?.();
  };

  if (loading && modeProp === "edit") {
    return <div className="p-4">Loading...</div>;
  }

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-semibold">
        {modeProp === "add" ? "Add Base Org Model" : modeProp === "edit" ? "Edit Base Org Model" : "View Base Org Model"}
      </h2>
      <div className="grid grid-cols-2 gap-4">
        {fields
          .filter((k) => k !== "id" || modeProp !== "add")
          .map((k) => {
            const v = data?.[k];
            return (
              <label key={k} className="block">
                <div className="text-sm font-medium mb-1 capitalize">{k.replace(/_/g, " ")}</div>
                <input
                  className="w-full border rounded px-3 py-2"
                  value={typeof v === 'object' && v !== null ? JSON.stringify(v) : String(v ?? '')}
                  onChange={(e) => setData({ ...data, [k]: e.target.value })}
                  disabled={modeProp === "view"}
                />
              </label>
            );
          })}
      </div>
      <div className="flex gap-2">
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
            className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}
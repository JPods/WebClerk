import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router";

import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import ComponentCard from "../../components/common/ComponentCard";
import TaskMarkerForm from "../../components/TaskMarkerForm";
import { getRecord } from "../../api/wcapi";
import { PageRoutes } from "../../routes/Routes";
import { firstAvailableValue } from "../../utils/optionUtils";

type GenericRecord = Record<string, unknown>;

const extractId = (payload: unknown): string | null => {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  const source = payload as Record<string, unknown>;
  const directId = source.id;
  if (typeof directId === "string" || typeof directId === "number") {
    return String(directId);
  }

  const record = source.record as Record<string, unknown> | undefined;
  if (record) {
    const recordId = record.id;
    if (typeof recordId === "string" || typeof recordId === "number") {
      return String(recordId);
    }
  }

  const records = source.records;
  if (Array.isArray(records) && records.length > 0) {
    const nested = records[0] as Record<string, unknown>;
    const nestedId = nested?.id;
    if (typeof nestedId === "string" || typeof nestedId === "number") {
      return String(nestedId);
    }
  }

  const data = source.data as Record<string, unknown> | undefined;
  if (data) {
    const dataId = data.id;
    if (typeof dataId === "string" || typeof dataId === "number") {
      return String(dataId);
    }
  }

  return null;
};

const TaskMarkerDetailPage: React.FC<{ defaultMode?: "add" | "edit" | "view" }> = ({ defaultMode }) => {
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const [record, setRecord] = useState<GenericRecord | null>(null);
  const [loading, setLoading] = useState<boolean>(Boolean(id));
  const [error, setError] = useState<string | null>(null);

  const mode: "add" | "edit" | "view" = defaultMode || (id ? "edit" : "add");

  const fetchTaskMarker = useCallback(async () => {
    if (!id) {
      setRecord(null);
      setLoading(false);
      setError(null);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = (await getRecord("task_marker", Number(id))) as { record?: GenericRecord | null };
      setRecord(res?.record ?? null);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : typeof err === "object" && err && "message" in err && typeof (err as { message?: unknown }).message === "string"
          ? String((err as { message?: unknown }).message)
          : "failed to load task_marker";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (!id) {
      setLoading(false);
      setError(null);
      return;
    }
    fetchTaskMarker();
  }, [fetchTaskMarker, id]);

  const handleSaved = (result?: unknown) => {
    const nextId = extractId(result);
    if (!id && nextId) {
      navigate(PageRoutes.actionsTaskMarkerDetail.replace(":id", nextId), { replace: true });
      return;
    }
    fetchTaskMarker();
  };

  const summary = useMemo(() => {
    if (!record) {
      return [] as Array<{ label: string; value: string }>;
    }
    return [
      { label: "action_by", value: firstAvailableValue(record, ["action_by", "actionBy"]) || "n/a" },
      { label: "action", value: firstAvailableValue(record, ["action"]) || "n/a" },
      { label: "action_date", value: firstAvailableValue(record, ["action_date", "actionDate"]) || "n/a" },
      { label: "action_time", value: firstAvailableValue(record, ["action_time", "actionTime"]) || "n/a" },
    ];
  }, [record]);

  if (loading) {
    return <div className="p-4 text-sm text-gray-500">loading task_marker...</div>;
  }

  if (error) {
    return <div className="p-4 text-sm text-red-600">{error}</div>;
  }

  return (
    <div className="space-y-6">
      <PageBreadcrumb pageTitle={id ? "Task Marker Detail" : "Add Task Marker"} />
      <TaskMarkerForm modeProp={mode} dataProp={record} onSaved={handleSaved} />
      {record && (
        <ComponentCard>
          <h3 className="mb-3 text-base font-semibold text-gray-800 dark:text-gray-100">task_marker summary</h3>
          <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
            {summary.map((entry) => (
              <div key={entry.label} className="rounded border border-gray-200 p-3 dark:border-gray-700">
                <dt className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">{entry.label}</dt>
                <dd className="mt-1 font-medium text-gray-900 dark:text-gray-100">{entry.value}</dd>
              </div>
            ))}
          </dl>
        </ComponentCard>
      )}
    </div>
  );
};

export default TaskMarkerDetailPage;

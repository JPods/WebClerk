import { useEffect } from "react";
import { useDispatch } from "react-redux";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import ComponentCard from "./common/ComponentCard";
import Label from "./form/Label";
import { Input, Select } from "./wrapper";
import staticLists from "../constants/staticLists";
import { mapStaticListToOptions } from "../utils/optionUtils";
import { saveRecord } from "../api/wcapi";
import { showToast } from "../store/slices/toastSlice";

const taskMarkerSchema = z.object({
  action_by: z.string().min(1, "action_by is required"),
  action: z.string().min(1, "action is required"),
  action_date: z.string().optional(),
  action_time: z.string().optional(),
});

type TaskMarkerFormValues = z.infer<typeof taskMarkerSchema>;

const schemaKeys = Object.keys(taskMarkerSchema.shape) as Array<keyof TaskMarkerFormValues>;

const defaultFromList = (list?: unknown[]): string => {
  if (!Array.isArray(list) || list.length === 0) {
    return "";
  }
  const first = list[0];
  if (Array.isArray(first)) {
    const raw = first[0];
    return raw != null ? String(raw) : "";
  }
  return first != null ? String(first) : "";
};

const DEFAULT_VALUES: TaskMarkerFormValues = {
  action_by: defaultFromList(staticLists.aNameID),
  action: defaultFromList(staticLists.aActions),
  action_date: "",
  action_time: "",
};

interface TaskMarkerFormProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: Record<string, unknown> | null;
  inline?: boolean;
  onSaved?: (result?: unknown) => void;
  onCancelInline?: () => void;
}

export default function TaskMarkerForm({
  modeProp,
  dataProp,
  inline = false,
  onSaved,
  onCancelInline,
}: TaskMarkerFormProps) {
  const dispatch = useDispatch();
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<TaskMarkerFormValues>({
    resolver: zodResolver(taskMarkerSchema),
    defaultValues: DEFAULT_VALUES,
  });

  const mode: "add" | "edit" | "view" = modeProp || "add";
  const data = dataProp ?? null;

  useEffect(() => {
    if (!data || mode === "add") {
      reset(DEFAULT_VALUES);
      return;
    }

    const nextValues: Partial<TaskMarkerFormValues> = {};
    const record = data as Record<string, unknown>;
    schemaKeys.forEach((key) => {
      const rawValue = record[key as string];
      if (rawValue !== undefined && rawValue !== null && rawValue !== "") {
        nextValues[key] = String(rawValue) as TaskMarkerFormValues[typeof key];
      }
    });
    reset({ ...DEFAULT_VALUES, ...nextValues });
  }, [data, mode, reset]);

  const actionByOptions = mapStaticListToOptions(staticLists.aNameID);
  const actionOptions = mapStaticListToOptions(staticLists.aActions);

  const onSubmit = async (formData: TaskMarkerFormValues) => {
    try {
      const payload: Record<string, unknown> = { ...formData };
      if (data && "id" in data) {
        payload.id = (data as Record<string, unknown>).id;
      }
      const res: unknown = await saveRecord("task_marker", payload);
      dispatch(
        showToast({
          message: `task_marker ${mode === "add" ? "saved" : "updated"} successfully`,
          type: "success",
        })
      );
      if (onSaved) {
        onSaved(res);
      }
      if (mode === "add") {
        reset(DEFAULT_VALUES);
      }
      return res;
    } catch (error: unknown) {
      const fallback = "failed to save task_marker";
      const message =
        error instanceof Error
          ? error.message
          : typeof error === "object" && error && "message" in error && typeof (error as { message?: unknown }).message === "string"
          ? String((error as { message?: unknown }).message)
          : fallback;
      dispatch(showToast({ message, type: "error" }));
      return null;
    }
  };

  const selectClassName = mode === "view" ? "cursor-not-allowed opacity-50" : "";

  return (
    <ComponentCard>
      {inline && (
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold dark:text-white">
            {mode === "edit" ? "edit task_marker" : mode === "view" ? "view task_marker" : "add task_marker"}
          </h3>
          {onCancelInline && (
            <button
              type="button"
              onClick={onCancelInline}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              &times;
            </button>
          )}
        </div>
      )}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <Label htmlFor="action_by">action_by</Label>
            <Select
              options={actionByOptions}
              placeholder="action_by"
              value={watch("action_by") || ""}
              onChange={(value) => setValue("action_by", value, { shouldValidate: true })}
              disabled={mode === "view"}
              className={selectClassName}
            />
            {errors.action_by?.message && <p className="mt-1 text-xs text-error-500">{errors.action_by.message}</p>}
          </div>
          <div>
            <Label htmlFor="action_date">action_date</Label>
            <Input
              type="date"
              id="action_date"
              placeholder="action_date"
              {...register("action_date")}
              disabled={mode === "view"}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <Label htmlFor="action">action</Label>
            <Select
              options={actionOptions}
              placeholder="action"
              value={watch("action") || ""}
              onChange={(value) => setValue("action", value, { shouldValidate: true })}
              disabled={mode === "view"}
              className={selectClassName}
            />
            {errors.action?.message && <p className="mt-1 text-xs text-error-500">{errors.action.message}</p>}
          </div>
          <div>
            <Label htmlFor="action_time">action_time</Label>
            <Input
              type="time"
              id="action_time"
              placeholder="action_time"
              {...register("action_time")}
              disabled={mode === "view"}
            />
          </div>
        </div>

        {mode !== "view" && (
          <div className="flex items-center gap-4">
            <button
              type="submit"
              className="rounded-md bg-blue-500 px-4 py-2 text-white hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900"
            >
              {mode === "edit" ? "update" : "submit"}
            </button>
            {inline && onCancelInline && (
              <button
                type="button"
                onClick={onCancelInline}
                className="rounded-md bg-gray-200 px-4 py-2 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
              >
                cancel
              </button>
            )}
          </div>
        )}
      </form>
    </ComponentCard>
  );
}

import { useEffect, useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../components/common/ComponentCard";
import Label from "../../components/form/Label";
import { Input, TextArea } from "../../components/wrapper";
import PageBreadcrumb from "../../components/common/PageBreadCrumb";

import { actionSchema } from "../../validations/action";
import { patchAction } from "../../api/userProfile";
import { showToast } from "../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";

type ActionPriority = "low" | "medium" | "high" | "critical";

interface ActionAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: tighten typing once API stabilises
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
  columnOptions?: string[];
}

const PRIORITY_TO_VALUE: Record<ActionPriority, number> = {
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
};

const VALUE_TO_PRIORITY: Record<number, ActionPriority> = {
  1: "low",
  2: "medium",
  3: "high",
  4: "critical",
};

const FALLBACK_COLUMNS = ["Backlog", "Planning", "In Progress", "Review", "Done"];

const DEFAULT_VALUES: z.infer<typeof actionSchema> = {
  action_en: "",
  description_en: "",
  kanban_column: "",
  priority: "medium",
  difficulty: 2,
  status: "",
  assignee: "",
  dt_start: "",
  dt_end: "",
  dt_due: "",
};

const formatDateInput = (value?: string | null) => {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toISOString().split("T")[0];
};

const normalizePriority = (value: unknown): ActionPriority => {
  if (typeof value === "number") {
    return VALUE_TO_PRIORITY[value] ?? "medium";
  }
  if (typeof value === "string") {
    const normalised = value.toLowerCase() as ActionPriority;
    return PRIORITY_TO_VALUE[normalised] ? normalised : "medium";
  }
  return "medium";
};

const coerceDifficulty = (value: unknown, priority: ActionPriority): number => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  const parsed = Number(value);
  if (!Number.isNaN(parsed) && Number.isFinite(parsed) && parsed > 0) {
    return parsed;
  }
  return PRIORITY_TO_VALUE[priority];
};

const toColumnId = (value: string) =>
  value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/-{2,}/g, "-");

const buildPayload = (
  form: z.infer<typeof actionSchema>,
  priorityMap: Record<ActionPriority, number>
): Record<string, unknown> => {
  const columnTitle = form.kanban_column.trim();
  const derivedColumnId = columnTitle ? `column-${toColumnId(columnTitle)}` : null;

  const payload: Record<string, unknown> = {
    model_name: "action",
    languages: ["en"],
    needtoremove: "",
    action_en: form.action_en,
    description_en: form.description_en ?? "",
    kanban_column: columnTitle,
    priority: priorityMap[form.priority],
    difficulty: form.difficulty || priorityMap[form.priority],
    status: form.status || "In progress",
    dt_start: form.dt_start ? new Date(form.dt_start).toISOString() : null,
    dt_end: form.dt_end ? new Date(form.dt_end).toISOString() : null,
    dt_due: form.dt_due ? new Date(form.dt_due).toISOString() : null,
  };

  if (derivedColumnId) {
    payload.kanban_column_id = derivedColumnId;
  }

  if (form.assignee) {
    payload.assigned_to = [{ name: form.assignee }];
  }

  return payload;
};

const ActionAdd = ({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
  columnOptions,
}: ActionAddProps) => {
  const dispatch = useDispatch();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof actionSchema>>({
    resolver: zodResolver(actionSchema),
    defaultValues: DEFAULT_VALUES,
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const mode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const data = dataProp || routeState.data || null;

  const availableColumns = useMemo(() => {
    const base = columnOptions?.length ? [...columnOptions] : [...FALLBACK_COLUMNS];
    const current = data?.kanban_column ? String(data.kanban_column).trim() : "";
    if (current && !base.includes(current)) {
      base.push(current);
    }
    return base;
  }, [columnOptions, data?.kanban_column]);

  useEffect(() => {
    if (mode === "add") {
      reset(DEFAULT_VALUES);
      return;
    }

    if (!data) {
      reset(DEFAULT_VALUES);
      return;
    }

    const priority = normalizePriority(data.priority);

    reset({
      action_en:
        data.action_en ??
        data.action ??
        data.action_ar ??
        data.action_bn ??
        data.action_es ??
        "",
      description_en:
        data.description_en ??
        data.description ??
        data.description_ar ??
        data.description_bn ??
        data.description_es ??
        "",
      kanban_column: data.kanban_column ?? "",
      priority,
      difficulty: coerceDifficulty(data.difficulty, priority),
      status: data.status ?? "",
      assignee: data.assigned_to?.[0]?.name ?? data.assignee ?? "",
      dt_start: formatDateInput(data.dt_start),
      dt_end: formatDateInput(data.dt_end),
      dt_due: formatDateInput(data.dt_due),
    });
  }, [data, mode, reset]);

  const onSubmit = async (formData: z.infer<typeof actionSchema>) => {
    try {
      const payload = buildPayload(formData, PRIORITY_TO_VALUE);

      if (mode === "edit" && data?.id) {
        payload.id = data.id;
      }

      const response = await patchAction(payload);
      if (response?.status !== 200 && response?.status !== 201) {
        throw new Error("Unable to save action");
      }

      dispatch(
        showToast({
          message: `Action ${mode === "edit" ? "updated" : "saved"} successfully`,
          type: "success",
        })
      );

      if (onSaved) {
        onSaved();
      }

      if (mode === "add") {
        reset(DEFAULT_VALUES);
      }
    } catch (error: any) {
      const message = error?.response?.data?.message || error?.message || "Failed to save action";
      dispatch(showToast({ message, type: "error" }));
    }
  };

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb pageTitle={mode === "edit" ? "Edit Action" : mode === "view" ? "View Action" : "Add Action"} />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold dark:text-white">
              {mode === "edit" ? "Edit Action" : mode === "view" ? "View Action" : "Add New Action"}
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
          <div className="grid grid-cols-1 gap-4">
            <div>
              <Label htmlFor="action_en">action_en</Label>
              <Input
                type="text"
                id="action_en"
                placeholder="action_en"
                {...register("action_en")}
                error={Boolean(errors.action_en)}
                hint={errors.action_en?.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="kanban_column">kanban_column</Label>
              <select
                id="kanban_column"
                className={`h-11 w-full rounded-lg border px-4 py-2.5 text-sm shadow-theme-xs focus:outline-hidden focus:ring-3 dark:bg-gray-900 dark:text-white/90 ${
                  errors.kanban_column ? "border-error-500" : "border-gray-300 dark:border-gray-700"
                } ${mode === "view" ? "bg-gray-100 text-gray-500 cursor-not-allowed opacity-60" : "bg-white"}`}
                {...register("kanban_column")}
                disabled={mode === "view"}
              >
                <option value="" disabled>
                  kanban_column
                </option>
                {availableColumns.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              {errors.kanban_column?.message && (
                <p className="mt-1.5 text-xs text-error-500">{errors.kanban_column.message}</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <Label htmlFor="priority">priority</Label>
              <select
                id="priority"
                className={`h-11 w-full rounded-lg border px-4 py-2.5 text-sm shadow-theme-xs focus:outline-hidden focus:ring-3 dark:bg-gray-900 dark:text-white/90 ${
                  errors.priority ? "border-error-500" : "border-gray-300 dark:border-gray-700"
                } ${mode === "view" ? "bg-gray-100 text-gray-500 cursor-not-allowed opacity-60" : "bg-white"}`}
                {...register("priority")}
                disabled={mode === "view"}
              >
                <option value="" disabled>
                  priority
                </option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
              {errors.priority?.message && (
                <p className="mt-1.5 text-xs text-error-500">{errors.priority.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="difficulty">difficulty</Label>
              <Input
                type="number"
                id="difficulty"
                placeholder="difficulty"
                min={1}
                {...register("difficulty", { valueAsNumber: true })}
                error={Boolean(errors.difficulty)}
                hint={errors.difficulty?.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="status">status</Label>
              <Input
                type="text"
                id="status"
                placeholder="status"
                {...register("status")}
                error={Boolean(errors.status)}
                hint={errors.status?.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="assignee">assignee</Label>
              <Input
                type="text"
                id="assignee"
                placeholder="assignee"
                {...register("assignee")}
                error={Boolean(errors.assignee)}
                hint={errors.assignee?.message}
                disabled={mode === "view"}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div>
              <Label htmlFor="dt_start">dt_start</Label>
              <Input
                type="date"
                id="dt_start"
                {...register("dt_start")}
                error={Boolean(errors.dt_start)}
                hint={errors.dt_start?.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="dt_end">dt_end</Label>
              <Input
                type="date"
                id="dt_end"
                {...register("dt_end")}
                error={Boolean(errors.dt_end)}
                hint={errors.dt_end?.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="dt_due">dt_due</Label>
              <Input
                type="date"
                id="dt_due"
                {...register("dt_due")}
                error={Boolean(errors.dt_due)}
                hint={errors.dt_due?.message}
                disabled={mode === "view"}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4">
            <div>
              <Label htmlFor="description_en">description_en</Label>
              <TextArea
                placeholder="description_en"
                register={register("description_en")}
                error={errors.description_en}
                disabled={mode === "view"}
              />
            </div>
          </div>

          {mode !== "view" && (
            <div className="flex items-center gap-4">
              <button
                type="submit"
                className="flex items-center px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
              >
                {mode === "edit" ? "Update" : "Submit"}
              </button>
              {inline && onCancelInline && (
                <button
                  type="button"
                  onClick={onCancelInline}
                  className="flex items-center px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
                >
                  Cancel
                </button>
              )}
            </div>
          )}
        </form>
      </ComponentCard>
    </>
  );
};

export default ActionAdd;


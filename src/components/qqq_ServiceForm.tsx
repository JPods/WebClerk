import { useEffect } from "react";
import { useDispatch } from "react-redux";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import ComponentCard from "./common/ComponentCard";
import Label from "./form/Label";
import { Input, Select, TextArea } from "./wrapper";
import staticLists from "../constants/staticLists";
import { mapStaticListToOptions } from "../utils/optionUtils";
import { saveRecord } from "../api/wcapi";
import { showToast } from "../store/slices/toastSlice";

const serviceSchema = z.object({
  bad_check: z.string().min(1, "bad_check is required"),
  bad_check_date: z.string().optional(),
  individual: z.string().min(1, "individual is required"),
  action: z.string().optional(),
  dt_begin: z.string().optional(),
  dt_action: z.string().optional(),
  action_name_id: z.string().optional(),
  rep_id: z.string().optional(),
  action_created_by: z.string().optional(),
  comment: z.string().optional(),
});

type ServiceFormValues = z.infer<typeof serviceSchema>;

const schemaKeys = Object.keys(serviceSchema.shape) as Array<keyof ServiceFormValues>;

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

const DEFAULT_VALUES: ServiceFormValues = {
  bad_check: defaultFromList(staticLists.aDataCheckBox),
  bad_check_date: "",
  individual: defaultFromList(staticLists.aDataCheckBox),
  action: "",
  dt_begin: "",
  dt_action: "",
  action_name_id: "",
  rep_id: "",
  action_created_by: "",
  comment: "",
};

interface ServiceFormProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: Record<string, unknown> | null;
  inline?: boolean;
  onSaved?: (result?: unknown) => void;
  onCancelInline?: () => void;
}

export default function ServiceForm({
  modeProp,
  dataProp,
  inline = false,
  onSaved,
  onCancelInline,
}: ServiceFormProps) {
  const dispatch = useDispatch();
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<ServiceFormValues>({
    resolver: zodResolver(serviceSchema),
    defaultValues: DEFAULT_VALUES,
  });

  const mode: "add" | "edit" | "view" = modeProp || "add";
  const data = dataProp ?? null;

  useEffect(() => {
    if (!data || mode === "add") {
      reset(DEFAULT_VALUES);
      return;
    }

    const nextValues: Partial<ServiceFormValues> = {};
    const record = data as Record<string, unknown>;
    schemaKeys.forEach((key) => {
      const rawValue = record[key as string];
      if (rawValue !== undefined && rawValue !== null && rawValue !== "") {
        nextValues[key] = String(rawValue) as ServiceFormValues[typeof key];
      }
    });
    reset({ ...DEFAULT_VALUES, ...nextValues });
  }, [data, mode, reset]);

  const checkboxOptions = mapStaticListToOptions(staticLists.aDataCheckBox);

  const onSubmit = async (formData: ServiceFormValues) => {
    try {
      const payload: Record<string, unknown> = { ...formData };
      if (data && "id" in data) {
        payload.id = (data as Record<string, unknown>).id;
      }
      const res: unknown = await saveRecord("service", payload);
      dispatch(
        showToast({
          message: `service ${mode === "add" ? "saved" : "updated"} successfully`,
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
      const fallback = "failed to save service";
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
            {mode === "edit" ? "edit service" : mode === "view" ? "view service" : "add service"}
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
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          <div>
            <Label htmlFor="bad_check">bad_check</Label>
            <Select
              options={checkboxOptions}
              placeholder="bad_check"
              value={watch("bad_check") || ""}
              onChange={(value) => setValue("bad_check", value, { shouldValidate: true })}
              disabled={mode === "view"}
              className={selectClassName}
            />
            {errors.bad_check?.message && <p className="mt-1 text-xs text-error-500">{errors.bad_check.message}</p>}
          </div>
          <div>
            <Label htmlFor="bad_check_date">bad_check_date</Label>
            <Input
              type="date"
              id="bad_check_date"
              placeholder="bad_check_date"
              {...register("bad_check_date")}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="individual">individual</Label>
            <Select
              options={checkboxOptions}
              placeholder="individual"
              value={watch("individual") || ""}
              onChange={(value) => setValue("individual", value, { shouldValidate: true })}
              disabled={mode === "view"}
              className={selectClassName}
            />
            {errors.individual?.message && <p className="mt-1 text-xs text-error-500">{errors.individual.message}</p>}
          </div>
          <div>
            <Label htmlFor="action">action</Label>
            <Input
              type="text"
              id="action"
              placeholder="action"
              {...register("action")}
              disabled={mode === "view"}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          <div>
            <Label htmlFor="dt_begin">dt_begin</Label>
            <Input
              type="date"
              id="dt_begin"
              placeholder="dt_begin"
              {...register("dt_begin")}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="dt_action">dt_action</Label>
            <Input
              type="date"
              id="dt_action"
              placeholder="dt_action"
              {...register("dt_action")}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="action_name_id">action_name_id</Label>
            <Input
              type="text"
              id="action_name_id"
              placeholder="action_name_id"
              {...register("action_name_id")}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="rep_id">rep_id</Label>
            <Input
              type="text"
              id="rep_id"
              placeholder="rep_id"
              {...register("rep_id")}
              disabled={mode === "view"}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <Label htmlFor="action_created_by">action_created_by</Label>
            <Input
              type="text"
              id="action_created_by"
              placeholder="action_created_by"
              {...register("action_created_by")}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="comment">comment</Label>
            <TextArea
              placeholder="comment"
              register={register("comment")}
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

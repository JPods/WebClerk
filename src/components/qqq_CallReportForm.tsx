/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
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

const callReportSchema = z.object({
  ad_source: z.string().min(1, "ad_source is required"),
  type_sale: z.string().min(1, "type_sale is required"),
  rep_id: z.string().min(1, "rep_id is required"),
  bad_check: z.string().min(1, "bad_check is required"),
  bad_check_date: z.string().optional(),
  individual: z.string().min(1, "individual is required"),
  billable: z.string().min(1, "billable is required"),
  completed: z.string().min(1, "completed is required"),
  phone_boolean: z.string().min(1, "phone_boolean is required"),
  fax: z.string().min(1, "fax is required"),
  message: z.string().min(1, "message is required"),
  letter: z.string().min(1, "letter is required"),
  email_message: z.string().min(1, "email_message is required"),
  visit: z.string().min(1, "visit is required"),
  initiated_by: z.string().optional(),
  name_id: z.string().optional(),
  date_create: z.string().optional(),
  dt_action: z.string().optional(),
  dt_completed: z.string().optional(),
  status: z.string().optional(),
  who: z.string().optional(),
  cust_lead_id: z.string().optional(),
  table_id: z.string().optional(),
  action: z.string().min(1, "action is required"),
  subject: z.string().optional(),
  comment_text: z.string().optional(),
});

type CallReportFormValues = z.infer<typeof callReportSchema>;

const schemaKeys = Object.keys(callReportSchema.shape) as Array<keyof CallReportFormValues>;

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

const DEFAULT_VALUES: CallReportFormValues = {
  ad_source: defaultFromList(staticLists.aAdSource),
  type_sale: defaultFromList(staticLists.aTypeSale),
  rep_id: defaultFromList(staticLists.aReps),
  bad_check: defaultFromList(staticLists.aDataCheckBox),
  bad_check_date: "",
  individual: defaultFromList(staticLists.aDataCheckBox),
  billable: defaultFromList(staticLists.aDataTrueFalse),
  completed: defaultFromList(staticLists.aDataTrueFalse),
  phone_boolean: defaultFromList(staticLists.aDataTrueFalse),
  fax: defaultFromList(staticLists.aDataTrueFalse),
  message: defaultFromList(staticLists.aDataTrueFalse),
  letter: defaultFromList(staticLists.aDataTrueFalse),
  email_message: defaultFromList(staticLists.aDataTrueFalse),
  visit: defaultFromList(staticLists.aDataTrueFalse),
  initiated_by: "",
  name_id: "",
  date_create: "",
  dt_action: "",
  dt_completed: "",
  status: "",
  who: "",
  cust_lead_id: "",
  table_id: "",
  action: defaultFromList(staticLists.aActions),
  subject: "",
  comment_text: "",
};

interface CallReportFormProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: Record<string, unknown> | null;
  inline?: boolean;
  onSaved?: (result?: unknown) => void;
  onCancelInline?: () => void;
}

export default function CallReportForm({
  modeProp,
  dataProp,
  inline = false,
  onSaved,
  onCancelInline,
}: CallReportFormProps) {
  const dispatch = useDispatch();
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<CallReportFormValues>({
    resolver: zodResolver(callReportSchema),
    defaultValues: DEFAULT_VALUES,
  });

  const mode: "add" | "edit" | "view" = modeProp || "add";
  const data = dataProp ?? null;

  useEffect(() => {
    if (!data || mode === "add") {
      reset(DEFAULT_VALUES);
      return;
    }

    const nextValues: Partial<CallReportFormValues> = {};
    const record = data as Record<string, unknown>;
    schemaKeys.forEach((key) => {
      const rawValue = record[key as string];
      if (rawValue !== undefined && rawValue !== null && rawValue !== "") {
        nextValues[key] = String(rawValue) as CallReportFormValues[typeof key];
      }
    });
    reset({ ...DEFAULT_VALUES, ...nextValues });
  }, [data, mode, reset]);

  const checkboxOptions = mapStaticListToOptions(staticLists.aDataCheckBox);
  const trueFalseOptions = mapStaticListToOptions(staticLists.aDataTrueFalse);
  const actionOptions = mapStaticListToOptions(staticLists.aActions);
  const adSourceOptions = mapStaticListToOptions(staticLists.aAdSource);
  const typeSaleOptions = mapStaticListToOptions(staticLists.aTypeSale);
  const repOptions = mapStaticListToOptions(staticLists.aReps);

  const onSubmit = async (formData: CallReportFormValues) => {
    try {
      const payload: Record<string, unknown> = { ...formData };
      if (data && "id" in data) {
        payload.id = (data as Record<string, unknown>).id;
      }
      const res: unknown = await saveRecord("call_report", payload);
      dispatch(
        showToast({
          message: `call_report ${mode === "add" ? "saved" : "updated"} successfully`,
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
      const fallback = "failed to save call_report";
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
            {mode === "edit" ? "edit call_report" : mode === "view" ? "view call_report" : "add call_report"}
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
            <Label htmlFor="ad_source">ad_source</Label>
            <Select
              options={adSourceOptions}
              placeholder="ad_source"
              value={watch("ad_source") || ""}
              onChange={(value) => setValue("ad_source", value, { shouldValidate: true })}
              disabled={mode === "view"}
              className={selectClassName}
            />
            {errors.ad_source?.message && <p className="mt-1 text-xs text-error-500">{errors.ad_source.message}</p>}
          </div>
          <div>
            <Label htmlFor="type_sale">type_sale</Label>
            <Select
              options={typeSaleOptions}
              placeholder="type_sale"
              value={watch("type_sale") || ""}
              onChange={(value) => setValue("type_sale", value, { shouldValidate: true })}
              disabled={mode === "view"}
              className={selectClassName}
            />
            {errors.type_sale?.message && <p className="mt-1 text-xs text-error-500">{errors.type_sale.message}</p>}
          </div>
          <div>
            <Label htmlFor="rep_id">rep_id</Label>
            <Select
              options={repOptions}
              placeholder="rep_id"
              value={watch("rep_id") || ""}
              onChange={(value) => setValue("rep_id", value, { shouldValidate: true })}
              disabled={mode === "view"}
              className={selectClassName}
            />
            {errors.rep_id?.message && <p className="mt-1 text-xs text-error-500">{errors.rep_id.message}</p>}
          </div>
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
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
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
            <Label htmlFor="billable">billable</Label>
            <Select
              options={trueFalseOptions}
              placeholder="billable"
              value={watch("billable") || ""}
              onChange={(value) => setValue("billable", value, { shouldValidate: true })}
              disabled={mode === "view"}
              className={selectClassName}
            />
            {errors.billable?.message && <p className="mt-1 text-xs text-error-500">{errors.billable.message}</p>}
          </div>
          <div>
            <Label htmlFor="completed">completed</Label>
            <Select
              options={trueFalseOptions}
              placeholder="completed"
              value={watch("completed") || ""}
              onChange={(value) => setValue("completed", value, { shouldValidate: true })}
              disabled={mode === "view"}
              className={selectClassName}
            />
            {errors.completed?.message && <p className="mt-1 text-xs text-error-500">{errors.completed.message}</p>}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          <div>
            <Label htmlFor="phone_boolean">phone_boolean</Label>
            <Select
              options={trueFalseOptions}
              placeholder="phone_boolean"
              value={watch("phone_boolean") || ""}
              onChange={(value) => setValue("phone_boolean", value, { shouldValidate: true })}
              disabled={mode === "view"}
              className={selectClassName}
            />
            {errors.phone_boolean?.message && <p className="mt-1 text-xs text-error-500">{errors.phone_boolean.message}</p>}
          </div>
          <div>
            <Label htmlFor="fax">fax</Label>
            <Select
              options={trueFalseOptions}
              placeholder="fax"
              value={watch("fax") || ""}
              onChange={(value) => setValue("fax", value, { shouldValidate: true })}
              disabled={mode === "view"}
              className={selectClassName}
            />
            {errors.fax?.message && <p className="mt-1 text-xs text-error-500">{errors.fax.message}</p>}
          </div>
          <div>
            <Label htmlFor="message">message</Label>
            <Select
              options={trueFalseOptions}
              placeholder="message"
              value={watch("message") || ""}
              onChange={(value) => setValue("message", value, { shouldValidate: true })}
              disabled={mode === "view"}
              className={selectClassName}
            />
            {errors.message?.message && <p className="mt-1 text-xs text-error-500">{errors.message.message}</p>}
          </div>
          <div>
            <Label htmlFor="letter">letter</Label>
            <Select
              options={trueFalseOptions}
              placeholder="letter"
              value={watch("letter") || ""}
              onChange={(value) => setValue("letter", value, { shouldValidate: true })}
              disabled={mode === "view"}
              className={selectClassName}
            />
            {errors.letter?.message && <p className="mt-1 text-xs text-error-500">{errors.letter.message}</p>}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          <div>
            <Label htmlFor="email_message">email_message</Label>
            <Select
              options={trueFalseOptions}
              placeholder="email_message"
              value={watch("email_message") || ""}
              onChange={(value) => setValue("email_message", value, { shouldValidate: true })}
              disabled={mode === "view"}
              className={selectClassName}
            />
            {errors.email_message?.message && (
              <p className="mt-1 text-xs text-error-500">{errors.email_message.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="visit">visit</Label>
            <Select
              options={trueFalseOptions}
              placeholder="visit"
              value={watch("visit") || ""}
              onChange={(value) => setValue("visit", value, { shouldValidate: true })}
              disabled={mode === "view"}
              className={selectClassName}
            />
            {errors.visit?.message && <p className="mt-1 text-xs text-error-500">{errors.visit.message}</p>}
          </div>
          <div>
            <Label htmlFor="initiated_by">initiated_by</Label>
            <Input
              type="text"
              id="initiated_by"
              placeholder="initiated_by"
              {...register("initiated_by")}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="name_id">name_id</Label>
            <Input
              type="text"
              id="name_id"
              placeholder="name_id"
              {...register("name_id")}
              disabled={mode === "view"}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          <div>
            <Label htmlFor="date_create">date_create</Label>
            <Input
              type="date"
              id="date_create"
              placeholder="date_create"
              {...register("date_create")}
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
            <Label htmlFor="dt_completed">dt_completed</Label>
            <Input
              type="date"
              id="dt_completed"
              placeholder="dt_completed"
              {...register("dt_completed")}
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
              disabled={mode === "view"}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          <div>
            <Label htmlFor="who">who</Label>
            <Input
              type="text"
              id="who"
              placeholder="who"
              {...register("who")}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="cust_lead_id">cust_lead_id</Label>
            <Input
              type="text"
              id="cust_lead_id"
              placeholder="cust_lead_id"
              {...register("cust_lead_id")}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="table_id">table_id</Label>
            <Input
              type="text"
              id="table_id"
              placeholder="table_id"
              {...register("table_id")}
              disabled={mode === "view"}
            />
          </div>
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
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <Label htmlFor="subject">subject</Label>
            <Input
              type="text"
              id="subject"
              placeholder="subject"
              {...register("subject")}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="comment_text">comment_text</Label>
            <TextArea
              placeholder="comment_text"
              register={register("comment_text")}
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

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useDispatch } from "react-redux";

import ComponentCard from "./common/ComponentCard";
import Label from "./form/Label";
import { Input, Select, TextArea } from "./wrapper";

import { saveRecord } from "../api/wcapi";
import { showToast } from "../store/slices/toastSlice";
import staticLists from "../constants/staticLists";

const proposalSchema = z.object({
  company: z.string().min(1, "company is required"),
  attention: z.string().min(1, "attention is required"),
  address1: z.string().min(1, "address1 is required"),
  address2: z.string().optional(),
  city: z.string().min(1, "city is required"),
  state: z.string().optional(),
  zip: z.string().min(1, "zip is required"),
  email: z.string().email("email_must_be_valid").optional().or(z.literal("")),
  phone: z.string().optional(),
  phone_cell: z.string().optional(),
  action_by: z.string().optional(),
  action: z.string().optional(),
  action_date: z.string().optional(),
  action_time: z.string().optional(),
  sales_name_id: z.string().optional(),
  ordered_by: z.string().optional(),
  contract_detail_tag: z.string().optional(),
  terms: z.string().optional(),
  type_sale: z.string().optional(),
  tax_juris: z.string().optional(),
  ad_source: z.string().optional(),
  status: z.string().optional(),
  add_comment: z.string().optional(),
  comment: z.string().optional(),
  contract_detail: z.string().optional(),
});

type ProposalFormValues = z.infer<typeof proposalSchema>;

const proposalSchemaKeys = Object.keys(proposalSchema.shape) as Array<keyof ProposalFormValues>;

interface ProposalFormProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: Record<string, any> | null;
  inline?: boolean;
  onSaved?: () => void;
  onCancelInline?: () => void;
}

const mapListToOptions = (list?: unknown[]): { value: string; label: string }[] => {
  if (!Array.isArray(list)) return [];
  return list
    .map((entry) => {
      if (Array.isArray(entry)) {
        const value = entry[0] != null ? String(entry[0]) : "";
        const label = entry[1] != null ? String(entry[1]) : value;
        return { value, label };
      }
      if (entry == null) {
        return { value: "", label: "" };
      }
      const value = String(entry);
      return { value, label: value };
    })
    .filter((option) => option.value !== "");
};

export default function ProposalForm({
  modeProp,
  dataProp,
  inline = false,
  onSaved,
  onCancelInline,
}: ProposalFormProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
  } = useForm<ProposalFormValues>({
    resolver: zodResolver(proposalSchema),
    defaultValues: {},
  });

  const mode: "add" | "edit" | "view" = modeProp || "add";
  const data = dataProp || null;

  useEffect(() => {
    if (mode === "add") {
      reset();
    } else if (data) {
      proposalSchemaKeys.forEach((key) => {
        const value = (data as Record<string, any>)[key as string];
        if (value !== undefined && value !== null) {
          setValue(key, value as any);
        }
      });
    } else {
      reset({});
    }
  }, [data, mode, reset, setValue]);

  const onSubmit = async (formData: ProposalFormValues) => {
    try {
      const payload = { ...formData, id: data?.id };
      const res = await saveRecord("proposal", payload);
      if (res) {
        dispatch(
          showToast({
            message: `proposal ${mode === "add" ? "saved" : "updated"} successfully`,
            type: "success",
          })
        );
        if (onSaved) {
          onSaved();
        }
      }
    } catch (error: any) {
      dispatch(
        showToast({
          message: error?.message || "failed to save proposal",
          type: "error",
        })
      );
    }
  };

  const stateOptions = [
    { value: "", label: "state" },
    ...staticLists.aStates.map((state) => ({ value: state, label: state })),
  ];

  const sharedOptionLists = {
    actions: mapListToOptions(staticLists.aActionsProposals && staticLists.aActionsProposals.length ? staticLists.aActionsProposals : staticLists.aActions),
    actionBy: mapListToOptions(staticLists.aNameID),
    contractDetail: mapListToOptions(staticLists.aContractDetail),
    terms: mapListToOptions(staticLists.aTerms),
    typeSale: mapListToOptions(staticLists.aTypeSale),
    taxJuris: mapListToOptions(staticLists.aTaxJuris),
    adSource: mapListToOptions(staticLists.aAdSource),
    status: mapListToOptions(staticLists.aStatus),
  };

  return (
    <ComponentCard>
      {inline && (
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold dark:text-white">
            {mode === "edit" ? "edit proposal" : mode === "view" ? "view proposal" : "add proposal"}
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
            <Label htmlFor="company">company</Label>
            <Input
              type="text"
              id="company"
              placeholder="company"
              {...register("company")}
              error={Boolean(errors.company)}
              hint={errors.company?.message}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="attention">attention</Label>
            <Input
              type="text"
              id="attention"
              placeholder="attention"
              {...register("attention")}
              error={Boolean(errors.attention)}
              hint={errors.attention?.message}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="address1">address1</Label>
            <Input
              type="text"
              id="address1"
              placeholder="address1"
              {...register("address1")}
              error={Boolean(errors.address1)}
              hint={errors.address1?.message}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="address2">address2</Label>
            <Input
              type="text"
              id="address2"
              placeholder="address2"
              {...register("address2")}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="city">city</Label>
            <Input
              type="text"
              id="city"
              placeholder="city"
              {...register("city")}
              error={Boolean(errors.city)}
              hint={errors.city?.message}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="state">state</Label>
            <Select
              options={stateOptions}
              placeholder="state"
              value={watch("state") || ""}
              onChange={(value) => setValue("state", value)}
              className={mode === "view" ? "cursor-not-allowed opacity-50" : ""}
            />
          </div>
          <div>
            <Label htmlFor="zip">zip</Label>
            <Input
              type="text"
              id="zip"
              placeholder="zip"
              {...register("zip")}
              error={Boolean(errors.zip)}
              hint={errors.zip?.message}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="email">email</Label>
            <Input
              type="email"
              id="email"
              placeholder="email"
              {...register("email")}
              error={Boolean(errors.email)}
              hint={errors.email?.message}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="phone">phone</Label>
            <Input
              type="tel"
              id="phone"
              placeholder="phone"
              {...register("phone")}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="phone_cell">phone_cell</Label>
            <Input
              type="tel"
              id="phone_cell"
              placeholder="phone_cell"
              {...register("phone_cell")}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="action_by">action_by</Label>
            <Select
              options={[{ value: "", label: "action_by" }, ...sharedOptionLists.actionBy]}
              placeholder="action_by"
              value={watch("action_by") || ""}
              onChange={(value) => setValue("action_by", value)}
              className={mode === "view" ? "cursor-not-allowed opacity-50" : ""}
            />
          </div>
          <div>
            <Label htmlFor="action">action</Label>
            <Select
              options={[{ value: "", label: "action" }, ...sharedOptionLists.actions]}
              placeholder="action"
              value={watch("action") || ""}
              onChange={(value) => setValue("action", value)}
              className={mode === "view" ? "cursor-not-allowed opacity-50" : ""}
            />
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
          <div>
            <Label htmlFor="sales_name_id">sales_name_id</Label>
            <Select
              options={[{ value: "", label: "sales_name_id" }, ...sharedOptionLists.actionBy]}
              placeholder="sales_name_id"
              value={watch("sales_name_id") || ""}
              onChange={(value) => setValue("sales_name_id", value)}
              className={mode === "view" ? "cursor-not-allowed opacity-50" : ""}
            />
          </div>
          <div>
            <Label htmlFor="ordered_by">ordered_by</Label>
            <Input
              type="text"
              id="ordered_by"
              placeholder="ordered_by"
              {...register("ordered_by")}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="contract_detail_tag">contract_detail_tag</Label>
            <Select
              options={[{ value: "", label: "contract_detail_tag" }, ...sharedOptionLists.contractDetail]}
              placeholder="contract_detail_tag"
              value={watch("contract_detail_tag") || ""}
              onChange={(value) => setValue("contract_detail_tag", value)}
              className={mode === "view" ? "cursor-not-allowed opacity-50" : ""}
            />
          </div>
          <div>
            <Label htmlFor="terms">terms</Label>
            <Select
              options={[{ value: "", label: "terms" }, ...sharedOptionLists.terms]}
              placeholder="terms"
              value={watch("terms") || ""}
              onChange={(value) => setValue("terms", value)}
              className={mode === "view" ? "cursor-not-allowed opacity-50" : ""}
            />
          </div>
          <div>
            <Label htmlFor="type_sale">type_sale</Label>
            <Select
              options={[{ value: "", label: "type_sale" }, ...sharedOptionLists.typeSale]}
              placeholder="type_sale"
              value={watch("type_sale") || ""}
              onChange={(value) => setValue("type_sale", value)}
              className={mode === "view" ? "cursor-not-allowed opacity-50" : ""}
            />
          </div>
          <div>
            <Label htmlFor="tax_juris">tax_juris</Label>
            <Select
              options={[{ value: "", label: "tax_juris" }, ...sharedOptionLists.taxJuris]}
              placeholder="tax_juris"
              value={watch("tax_juris") || ""}
              onChange={(value) => setValue("tax_juris", value)}
              className={mode === "view" ? "cursor-not-allowed opacity-50" : ""}
            />
          </div>
          <div>
            <Label htmlFor="ad_source">ad_source</Label>
            <Select
              options={[{ value: "", label: "ad_source" }, ...sharedOptionLists.adSource]}
              placeholder="ad_source"
              value={watch("ad_source") || ""}
              onChange={(value) => setValue("ad_source", value)}
              className={mode === "view" ? "cursor-not-allowed opacity-50" : ""}
            />
          </div>
          <div>
            <Label htmlFor="status">status</Label>
            <Select
              options={[{ value: "", label: "status" }, ...sharedOptionLists.status]}
              placeholder="status"
              value={watch("status") || ""}
              onChange={(value) => setValue("status", value)}
              className={mode === "view" ? "cursor-not-allowed opacity-50" : ""}
            />
          </div>
        </div>

        <div>
          <Label htmlFor="add_comment">add_comment</Label>
          <TextArea
            placeholder="add_comment"
            register={register("add_comment")}
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

        <div>
          <Label htmlFor="contract_detail">contract_detail</Label>
          <TextArea
            placeholder="contract_detail"
            register={register("contract_detail")}
            disabled={mode === "view"}
          />
        </div>

        {mode !== "view" && (
          <div className="flex items-center gap-4">
            <button
              type="submit"
              className="flex items-center rounded-md bg-blue-500 px-4 py-2 text-white hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
            >
              {mode === "edit" ? "update" : "submit"}
            </button>
            {inline && onCancelInline && (
              <button
                type="button"
                onClick={onCancelInline}
                className="flex items-center rounded-md bg-gray-200 px-4 py-2 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
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

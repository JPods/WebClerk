import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input, CustTextArea } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createProposal, updateProposal } from "../services/proposalApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { proposalSchema } from "../utils/proposalSchema";
import { ProposalAddProps } from "../types/proposalType";

export default function ProposalDetailVueReact({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: ProposalAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof proposalSchema>>({
    resolver: zodResolver(proposalSchema),
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const mode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const data = dataProp || routeState.data || null;
  useEffect(() => {
    if (mode === "add") {
      reset();
    } else if (data) {
      Object.keys(data).forEach((key: any) => {
        if (data[key] !== undefined) {
          setValue(key, data[key]);
        }
      });
    } else {
      reset({});
    }
  }, [data, reset, setValue, mode]);

  const onSubmit = async (formData: z.infer<typeof proposalSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createProposal(formData)
          : await updateProposal(data.id, { ...formData, id: data.id });
      if (res) {
        dispatch(
          showToast({
            message: `Proposal ${
              mode === "add" ? "created" : "updated"
            } successfully`,
            type: "success",
          })
        );
        if (onSaved) {
          onSaved();
        }
      }
    } catch (error: any) {
      dispatch(showToast({ message: error.message, type: "error" }));
    }
  };

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Proposal"
              : mode === "view"
              ? "View Proposal"
              : "Proposal Detail React"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Proposal"
                : mode === "view"
                ? "View Proposal"
                : "Add New Proposal"}
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
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="ida">Proposal ID</Label>
              <Input
                type="text"
                id="ida"
                placeholder="Proposal ID"
                {...register("ida")}
                error={errors.ida && errors.ida.message ? true : false}
                hint={errors.ida && errors.ida.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="status">Status</Label>
              <select
                id="status"
                {...register("status")}
                disabled={mode === "view"}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              >
                <option value="">Select Status</option>
                <option value="planned">Planned</option>
                <option value="sent">Sent</option>
                <option value="accepted">Accepted</option>
                <option value="rejected">Rejected</option>
                <option value="cancelled">Cancelled</option>
              </select>
              {errors.status && <p className="text-red-500 text-sm">{errors.status.message}</p>}
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="priority">Priority</Label>
              <Input
                type="text"
                id="priority"
                placeholder="Priority"
                {...register("priority")}
                error={errors.priority && errors.priority.message ? true : false}
                hint={errors.priority && errors.priority.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="price_level">Price Level</Label>
              <Input
                type="text"
                id="price_level"
                placeholder="Price Level"
                {...register("price_level")}
                error={errors.price_level && errors.price_level.message ? true : false}
                hint={errors.price_level && errors.price_level.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label htmlFor="id_customer">Customer ID *</Label>
              <Input
                type="number"
                id="id_customer"
                placeholder="Customer ID"
                {...register("id_customer", { valueAsNumber: true })}
                error={errors.id_customer && errors.id_customer.message ? true : false}
                hint={errors.id_customer && errors.id_customer.message}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="id_manufacturer">Manufacturer ID</Label>
              <Input
                type="number"
                id="id_manufacturer"
                placeholder="Manufacturer ID"
                {...register("id_manufacturer", { valueAsNumber: true })}
                disabled={mode === "view"}
              />
            </div>
            <div>
              <Label htmlFor="id_vendor">Vendor ID</Label>
              <Input
                type="number"
                id="id_vendor"
                placeholder="Vendor ID"
                {...register("id_vendor", { valueAsNumber: true })}
                error={errors.id_vendor && errors.id_vendor.message ? true : false}
                hint={errors.id_vendor && errors.id_vendor.message}
                disabled={mode === "view"}
              />
            </div>
          </div>
          {mode !== "view" && (
            <div className="flex items-center gap-2">
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
}
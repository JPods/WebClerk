import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../../components/common/ComponentCard";
import Label from "../../../../../../components/form/Label";
import { Input, CustTextArea } from "../../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../../components/common/PageBreadCrumb";
import { createProposal, updateProposal } from "../services/proposalApi";
import { showToast } from "../../../../../../store/slices/toastSlice";
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
      // Set basic fields
      Object.keys(data).forEach((key: any) => {
        if (data[key] !== undefined && typeof data[key] !== 'object') {
          setValue(key, data[key]);
        }
      });
      // Flatten nested objects
      const setValueAny = setValue as any;
      ['cost', 'sell', 'finance', 'source', 'action', 'flow'].forEach(section => {
        if (data[section] && typeof data[section] === 'object') {
          Object.keys(data[section]).forEach(subKey => {
            if (section === 'action' && subKey === 'action_next' && typeof data[section][subKey] === 'object') {
              Object.keys(data[section][subKey]).forEach(actionKey => {
                setValueAny(`${section}.${subKey}.${actionKey}`, data[section][subKey][actionKey]);
              });
            } else if (section === 'flow' && (subKey === 'source' || subKey === 'children') && Array.isArray(data[section][subKey])) {
              setValueAny(`${section}.${subKey}`, JSON.stringify(data[section][subKey]));
            } else {
              setValueAny(`${section}.${subKey}`, data[section][subKey]);
            }
          });
        }
      });
    } else {
      reset({});
    }
  }, [data, reset, setValue, mode]);

  const onSubmit = async (formData: z.infer<typeof proposalSchema>) => {
    // Parse JSON fields
    const processedData = { ...formData };
    if (processedData.flow?.source && typeof processedData.flow.source === 'string') {
      try {
        processedData.flow.source = JSON.parse(processedData.flow.source);
      } catch (e) {
        processedData.flow.source = [];
      }
    }
    if (processedData.flow?.children && typeof processedData.flow.children === 'string') {
      try {
        processedData.flow.children = JSON.parse(processedData.flow.children);
      } catch (e) {
        processedData.flow.children = [];
      }
    }

    try {
      const res =
        mode === "add"
          ? await createProposal(processedData)
          : await updateProposal(data.id, { ...processedData, id: data.id });
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
          {/* Basic Information */}
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

          {/* Cost Section */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold dark:text-white">cost</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="cost.line_sum_goods">cost.line_sum_goods</Label>
                <Input
                  type="number"
                  id="cost.line_sum_goods"
                  placeholder="0.00"
                  {...register("cost.line_sum_goods", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="cost.line_sum_tax">cost.line_sum_tax</Label>
                <Input
                  type="number"
                  id="cost.line_sum_tax"
                  placeholder="0.00"
                  {...register("cost.line_sum_tax", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="cost.line_sum_shipping">cost.line_sum_shipping</Label>
                <Input
                  type="number"
                  id="cost.line_sum_shipping"
                  placeholder="0.00"
                  {...register("cost.line_sum_shipping", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="cost.line_sum_handling">cost.line_sum_handling</Label>
                <Input
                  type="number"
                  id="cost.line_sum_handling"
                  placeholder="0.00"
                  {...register("cost.line_sum_handling", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="cost.handling">cost.handling</Label>
                <Input
                  type="number"
                  id="cost.handling"
                  placeholder="0.00"
                  {...register("cost.handling", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="cost.freight">cost.freight</Label>
                <Input
                  type="number"
                  id="cost.freight"
                  placeholder="0.00"
                  {...register("cost.freight", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="cost.tax_rate">cost.tax_rate</Label>
                <Input
                  type="number"
                  id="cost.tax_rate"
                  placeholder="0.00"
                  {...register("cost.tax_rate", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="cost.tax">cost.tax</Label>
                <Input
                  type="number"
                  id="cost.tax"
                  placeholder="0.00"
                  {...register("cost.tax", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="cost.commissions">cost.commissions</Label>
                <Input
                  type="number"
                  id="cost.commissions"
                  placeholder="0.00"
                  {...register("cost.commissions", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="cost.total">cost.total</Label>
                <Input
                  type="number"
                  id="cost.total"
                  placeholder="0.00"
                  {...register("cost.total", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
            </div>
          </div>

          {/* Sell Section */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold dark:text-white">sell</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="sell.subtotal">sell.subtotal</Label>
                <Input
                  type="number"
                  id="sell.subtotal"
                  placeholder="0.00"
                  {...register("sell.subtotal", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="sell.discount">sell.discount</Label>
                <Input
                  type="number"
                  id="sell.discount"
                  placeholder="0.00"
                  {...register("sell.discount", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="sell.taxable">sell.taxable</Label>
                <Input
                  type="number"
                  id="sell.taxable"
                  placeholder="0.00"
                  {...register("sell.taxable", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="sell.tax">sell.tax</Label>
                <Input
                  type="number"
                  id="sell.tax"
                  placeholder="0.00"
                  {...register("sell.tax", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="sell.shipping">sell.shipping</Label>
                <Input
                  type="number"
                  id="sell.shipping"
                  placeholder="0.00"
                  {...register("sell.shipping", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="sell.other">sell.other</Label>
                <Input
                  type="number"
                  id="sell.other"
                  placeholder="0.00"
                  {...register("sell.other", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="sell.total">sell.total</Label>
                <Input
                  type="number"
                  id="sell.total"
                  placeholder="0.00"
                  {...register("sell.total", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="sell.cost">sell.cost</Label>
                <Input
                  type="number"
                  id="sell.cost"
                  placeholder="0.00"
                  {...register("sell.cost", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="sell.margin">sell.margin</Label>
                <Input
                  type="number"
                  id="sell.margin"
                  placeholder="0.00"
                  {...register("sell.margin", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="sell.margin_pc">sell.margin_pc</Label>
                <Input
                  type="number"
                  id="sell.margin_pc"
                  placeholder="0.00"
                  {...register("sell.margin_pc", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="sell.received">sell.received</Label>
                <Input
                  type="number"
                  id="sell.received"
                  placeholder="0.00"
                  {...register("sell.received", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="sell.balance">sell.balance</Label>
                <Input
                  type="number"
                  id="sell.balance"
                  placeholder="0.00"
                  {...register("sell.balance", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
            </div>
          </div>

          {/* Finance Section */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold dark:text-white">finance</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="finance.sales_tax_id">finance.sales_tax_id</Label>
                <Input
                  type="number"
                  id="finance.sales_tax_id"
                  placeholder="0"
                  {...register("finance.sales_tax_id", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="finance.sales_tax_name">finance.sales_tax_name</Label>
                <Input
                  type="text"
                  id="finance.sales_tax_name"
                  placeholder=""
                  {...register("finance.sales_tax_name")}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="finance.sales_tax_rate">finance.sales_tax_rate</Label>
                <Input
                  type="number"
                  id="finance.sales_tax_rate"
                  placeholder="0.00"
                  {...register("finance.sales_tax_rate", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="finance.sales_tax">finance.sales_tax</Label>
                <Input
                  type="number"
                  id="finance.sales_tax"
                  placeholder="0.00"
                  {...register("finance.sales_tax", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="finance.cost_tax_id">finance.cost_tax_id</Label>
                <Input
                  type="number"
                  id="finance.cost_tax_id"
                  placeholder="0"
                  {...register("finance.cost_tax_id", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="finance.cost_tax_name">finance.cost_tax_name</Label>
                <Input
                  type="text"
                  id="finance.cost_tax_name"
                  placeholder=""
                  {...register("finance.cost_tax_name")}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="finance.cost_tax_rate">finance.cost_tax_rate</Label>
                <Input
                  type="number"
                  id="finance.cost_tax_rate"
                  placeholder="0.00"
                  {...register("finance.cost_tax_rate", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="finance.cost_tax">finance.cost_tax</Label>
                <Input
                  type="number"
                  id="finance.cost_tax"
                  placeholder="0.00"
                  {...register("finance.cost_tax", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="finance.tax_subtotal">finance.tax_subtotal</Label>
                <Input
                  type="number"
                  id="finance.tax_subtotal"
                  placeholder="0.00"
                  {...register("finance.tax_subtotal", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="finance.tax_pc">finance.tax_pc</Label>
                <Input
                  type="number"
                  id="finance.tax_pc"
                  placeholder="0.00"
                  {...register("finance.tax_pc", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="finance.collection_expense">finance.collection_expense</Label>
                <Input
                  type="number"
                  id="finance.collection_expense"
                  placeholder="0.00"
                  {...register("finance.collection_expense", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="finance.exchange_expense">finance.exchange_expense</Label>
                <Input
                  type="number"
                  id="finance.exchange_expense"
                  placeholder="0.00"
                  {...register("finance.exchange_expense", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
            </div>
          </div>

          {/* Source Section */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold dark:text-white">source</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="source.campaign_id">source.campaign_id</Label>
                <Input
                  type="number"
                  id="source.campaign_id"
                  placeholder="0"
                  {...register("source.campaign_id", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="source.catalog_id">source.catalog_id</Label>
                <Input
                  type="number"
                  id="source.catalog_id"
                  placeholder="0"
                  {...register("source.catalog_id", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="source.vendor_id">source.vendor_id</Label>
                <Input
                  type="number"
                  id="source.vendor_id"
                  placeholder="0"
                  {...register("source.vendor_id", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="source.manufacturer_id">source.manufacturer_id</Label>
                <Input
                  type="number"
                  id="source.manufacturer_id"
                  placeholder="0"
                  {...register("source.manufacturer_id", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
            </div>
          </div>

          {/* Action Section */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold dark:text-white">action</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label htmlFor="action.action_next.who">action.action_next.who</Label>
                <Input
                  type="text"
                  id="action.action_next.who"
                  placeholder=""
                  {...register("action.action_next.who")}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="action.action_next.when">action.action_next.when</Label>
                <Input
                  type="number"
                  id="action.action_next.when"
                  placeholder="0"
                  {...register("action.action_next.when", { valueAsNumber: true })}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="action.action_next.what">action.action_next.what</Label>
                <Input
                  type="text"
                  id="action.action_next.what"
                  placeholder=""
                  {...register("action.action_next.what")}
                  disabled={mode === "view"}
                />
              </div>
            </div>
          </div>

          {/* Flow Section */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold dark:text-white">flow</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="flow.source">flow.source</Label>
                <CustTextArea
                  id="flow.source"
                  placeholder='[{"type": "", "id": 0}]'
                  {...register("flow.source")}
                  disabled={mode === "view"}
                />
              </div>
              <div>
                <Label htmlFor="flow.children">flow.children</Label>
                <CustTextArea
                  id="flow.children"
                  placeholder='[{"type": "", "id": 0}]'
                  {...register("flow.children")}
                  disabled={mode === "view"}
                />
              </div>
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
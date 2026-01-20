import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../../components/common/ComponentCard";
import Label from "../../../../../../components/form/Label";
import { Input } from "../../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../../components/common/PageBreadCrumb";
import { createSalesOrderLine, updateSalesOrderLine } from "../services/salesOrderLineApi";
import { showToast } from "../../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { salesOrderLineSchema } from "../utils/salesOrderLineSchema";
import { SalesOrderLineAddProps } from "../types/salesOrderLineType";

export default function SalesOrderLineDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: SalesOrderLineAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof salesOrderLineSchema>>({
    resolver: zodResolver(salesOrderLineSchema),
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

  const preparePayload = (formValues: z.infer<typeof salesOrderLineSchema>): Record<string, unknown> => {
    const numericPrice =
      typeof formValues.unit_price === "number" && Number.isFinite(formValues.unit_price) ? formValues.unit_price : 0;
    const existingPriceRaw = (data as Record<string, unknown> | null)?.price as unknown;
    const existingPrice =
      existingPriceRaw && typeof existingPriceRaw === "object" && !Array.isArray(existingPriceRaw)
        ? (existingPriceRaw as Record<string, unknown>)
        : undefined;
    const pricePayload = existingPrice ? { ...existingPrice, base: numericPrice } : { base: numericPrice };
    return {
      ...formValues,
      price: pricePayload,
      unit_price: numericPrice,
    };
  };

  const onSubmit = async (formData: z.infer<typeof salesOrderLineSchema>) => {
    try {
      const payload = preparePayload(formData);
      const res =
        mode === "add"
          ? await createSalesOrderLine(payload)
          : await updateSalesOrderLine(data && data.id, payload);
      if (res) {
        dispatch(
          showToast({
            message: `Sales order line ${
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
              ? "Edit Sales Order Line"
              : mode === "view"
              ? "View Sales Order Line"
              : "Sales Order Line Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Sales Order Line"
                : mode === "view"
                ? "View Sales Order Line"
                : "Add New Sales Order Line"}
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
          <div>
            <Label htmlFor="sales_order_id">sales_order_id</Label>
            <Input
              type="number"
              id="sales_order_id"
              placeholder="Sales Order ID"
              {...register("sales_order_id", { valueAsNumber: true })}
              error={errors.sales_order_id && errors.sales_order_id.message ? true : false}
              hint={errors.sales_order_id && errors.sales_order_id.message}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="item_id">item_id</Label>
            <Input
              type="number"
              id="item_id"
              placeholder="Item ID"
              {...register("item_id", { valueAsNumber: true })}
              error={errors.item_id && errors.item_id.message ? true : false}
              hint={errors.item_id && errors.item_id.message}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="quantity">quantity</Label>
            <Input
              type="number"
              id="quantity"
              placeholder="Quantity"
              {...register("quantity", { valueAsNumber: true })}
              error={errors.quantity && errors.quantity.message ? true : false}
              hint={errors.quantity && errors.quantity.message}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="unit_price">unit_price</Label>
            <Input
              type="number"
              step="0.01"
              id="unit_price"
              placeholder="Unit Price"
              {...register("unit_price", { valueAsNumber: true })}
              error={errors.unit_price && errors.unit_price.message ? true : false}
              hint={errors.unit_price && errors.unit_price.message}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="line_total">line_total</Label>
            <Input
              type="number"
              step="0.01"
              id="line_total"
              placeholder="Line Total"
              {...register("line_total", { valueAsNumber: true })}
              error={errors.line_total && errors.line_total.message ? true : false}
              hint={errors.line_total && errors.line_total.message}
              disabled={mode === "view"}
            />
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
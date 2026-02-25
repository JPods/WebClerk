import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import SimpleDetailHeader from "../../../../../components/common/SimpleDetailHeader";
import SimpleDetailToolbar from "../../../../../components/common/SimpleDetailToolbar";
import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createOrderLine, updateOrderLine } from "../services/orderLineApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { orderLineSchema } from "../utils/orderLineSchema";
import { OrderLineAddProps } from "../types/orderLineType";
import { ScalarCard, JsonCard, BaseModelCards } from "@/apps/common/components/detail";

export default function OrderLineDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: OrderLineAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof orderLineSchema>>({
    resolver: zodResolver(orderLineSchema),
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const data = dataProp || routeState.data || null;

  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);
  const [isSaving, setIsSaving] = useState(false);

  const handleEdit = () => setCurrentMode("edit");
  const handleCancel = () => {
    setCurrentMode("view");
    if (data) {
      Object.keys(data).forEach((key: any) => {
        if (data[key] !== undefined) {
          setValue(key, data[key]);
        }
      });
    }
  };

  useEffect(() => {
    if (currentMode === "add") {
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
  }, [data, reset, setValue, currentMode]);

  const preparePayload = (formValues: z.infer<typeof orderLineSchema>): Record<string, unknown> => {
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

  const onSubmit = async (formData: z.infer<typeof orderLineSchema>) => {
    setIsSaving(true);
    try {
      const payload = preparePayload(formData);
      const res =
        currentMode === "add"
          ? await createOrderLine(payload)
          : await updateOrderLine(data && data.id, payload);
      if (res) {
        dispatch(
          showToast({
            message: `Order line ${
              currentMode === "add" ? "created" : "updated"
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
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            currentMode === "edit"
              ? "Edit Order Line"
              : currentMode === "view"
              ? "View Order Line"
              : "Order Line Detail"
          }
        />
      )}
      <SimpleDetailHeader
        entityName="Order Line"
        id={data?.id}
        mode={currentMode}
      />
      <SimpleDetailToolbar
        mode={currentMode}
        isSaving={isSaving}
        onEdit={handleEdit}
        onCancel={handleCancel}
        onSave={handleSubmit(onSubmit)}
      />
      {currentMode === "view" && data && (
        <div className="space-y-4 py-2">
          <ScalarCard
            title="Line Details"
            fields={[
              { label: "line_number", value: data.line_number },
              { label: "status", value: data.status },
              { label: "price_level", value: data.price_level },
            ]}
            columns={3}
          />
          <JsonCard title="Item" fieldName="item" data={data.item as Record<string, unknown>} columns={2} />
          <JsonCard title="Quantity" fieldName="quantity" data={data.quantity as Record<string, unknown>} columns={2} />
          <JsonCard title="Price" fieldName="price" data={data.price as Record<string, unknown>} columns={2} />
          <JsonCard title="Cost" fieldName="cost" data={data.cost as Record<string, unknown>} columns={2} />
          <JsonCard title="Tax" fieldName="tax" data={data.tax as Record<string, unknown>} columns={2} />
          <JsonCard title="Physical" fieldName="physical" data={data.physical as Record<string, unknown>} columns={2} />
          <BaseModelCards data={data} />
        </div>
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {currentMode === "edit"
                ? "Edit Order Line"
                : currentMode === "view"
                ? "View Order Line"
                : "Add New Order Line"}
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
            <Label htmlFor="order_id">order_id</Label>
            <Input
              type="number"
              id="order_id"
              placeholder="Order ID"
              {...register("order_id", { valueAsNumber: true })}
              error={errors.order_id && errors.order_id.message ? true : false}
              hint={errors.order_id && errors.order_id.message}
              disabled={currentMode === "view"}
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
              disabled={currentMode === "view"}
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
              disabled={currentMode === "view"}
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
              disabled={currentMode === "view"}
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
              disabled={currentMode === "view"}
            />
          </div>
          {currentMode !== "view" && (
            <div className="flex items-center gap-2">
              <button
                type="submit"
                className="flex items-center px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
              >
                {currentMode === "edit" ? "Update" : "Submit"}
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
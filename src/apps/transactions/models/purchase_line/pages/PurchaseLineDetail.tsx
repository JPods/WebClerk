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
import { createPurchaseOrderLine, updatePurchaseOrderLine } from "../services/purchaseOrderLineApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { purchaseOrderLineSchema } from "../utils/purchaseOrderLineSchema";
import { PurchaseOrderLineAddProps } from "../types/purchaseOrderLineType";
import { coerceFormValue, coerceNumber } from "../../common/valueNormalization";

export default function PurchaseLineDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: PurchaseOrderLineAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof purchaseOrderLineSchema>>({
    resolver: zodResolver(purchaseOrderLineSchema),
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
      const numericFields = new Set(["purchaseorder_id", "item_id", "quantity", "unit_price", "line_total"]);
      Object.keys(data).forEach((key: any) => {
        if (data[key] === undefined) {
          return;
        }
        const sanitized = coerceFormValue(data[key]);
        if (sanitized === undefined || sanitized === null) {
          return;
        }
        const finalValue = numericFields.has(key)
          ? coerceNumber(sanitized)
          : sanitized;
        setValue(key, finalValue as any);
      });
    }
  };

  useEffect(() => {
    if (currentMode === "add") {
      reset();
    } else if (data) {
      const numericFields = new Set(["purchaseorder_id", "item_id", "quantity", "unit_price", "line_total"]);
      Object.keys(data).forEach((key: any) => {
        if (data[key] === undefined) {
          return;
        }
        const sanitized = coerceFormValue(data[key]);
        if (sanitized === undefined || sanitized === null) {
          return;
        }
        const finalValue = numericFields.has(key)
          ? coerceNumber(sanitized)
          : sanitized;
        setValue(key, finalValue as any);
      });
    } else {
      reset({});
    }
  }, [data, reset, setValue, currentMode]);

  const preparePayload = (formValues: z.infer<typeof purchaseOrderLineSchema>): Record<string, unknown> => {
    const numericPrice =
      typeof formValues.unit_price === "number" && Number.isFinite(formValues.unit_price) ? formValues.unit_price : 0;
    const existingCostRaw = (data as Record<string, unknown> | null)?.cost as unknown;
    const existingCost =
      existingCostRaw && typeof existingCostRaw === "object" && !Array.isArray(existingCostRaw)
        ? (existingCostRaw as Record<string, unknown>)
        : undefined;
    const costPayload = existingCost ? { ...existingCost, last: numericPrice } : { last: numericPrice };
    return {
      ...formValues,
      cost: costPayload,
      unit_price: numericPrice,
    };
  };

  const onSubmit = async (formData: z.infer<typeof purchaseOrderLineSchema>) => {
    setIsSaving(true);
    try {
      const payload = preparePayload(formData);
      const res =
        currentMode === "add"
          ? await createPurchaseOrderLine(payload)
          : await updatePurchaseOrderLine(data && data.id, payload);
      if (res) {
        dispatch(
          showToast({
            message: `Purchase order line ${
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
              ? "Edit Purchase Order Line"
              : currentMode === "view"
              ? "View Purchase Order Line"
              : "Purchase Order Line Detail"
          }
        />
      )}
      <SimpleDetailHeader
        entityName="Purchase Order Line"
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
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {currentMode === "edit"
                ? "Edit Purchase Order Line"
                : currentMode === "view"
                ? "View Purchase Order Line"
                : "Add New Purchase Order Line"}
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
            <Label htmlFor="purchaseorder_id">purchaseorder_id</Label>
            <Input
              type="number"
              id="purchaseorder_id"
              placeholder="Purchase Order ID"
              {...register("purchaseorder_id", { valueAsNumber: true })}
              error={errors.purchaseorder_id && errors.purchaseorder_id.message ? true : false}
              hint={errors.purchaseorder_id && errors.purchaseorder_id.message}
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
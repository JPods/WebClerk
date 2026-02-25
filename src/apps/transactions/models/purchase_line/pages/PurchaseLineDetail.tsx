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
import { createPurchaseLine, updatePurchaseLine } from "../services/purchaseLineApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { purchaseLineSchema } from "../utils/purchaseLineSchema";
import { PurchaseLineAddProps } from "../types/purchaseLineType";
import { coerceFormValue, coerceNumber } from "../../common/valueNormalization";
import { ScalarCard, JsonCard, BaseModelCards } from "@/apps/common/components/detail";

export default function PurchaseLineDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: PurchaseLineAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof purchaseLineSchema>>({
    resolver: zodResolver(purchaseLineSchema),
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
      const numericFields = new Set(["purchase_id", "item_id", "quantity", "unit_price", "line_total"]);
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
      const numericFields = new Set(["purchase_id", "item_id", "quantity", "unit_price", "line_total"]);
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

  const preparePayload = (formValues: z.infer<typeof purchaseLineSchema>): Record<string, unknown> => {
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

  const onSubmit = async (formData: z.infer<typeof purchaseLineSchema>) => {
    setIsSaving(true);
    try {
      const payload = preparePayload(formData);
      const res =
        currentMode === "add"
          ? await createPurchaseLine(payload)
          : await updatePurchaseLine(data && data.id, payload);
      if (res) {
        dispatch(
          showToast({
            message: `Purchase line ${
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
              ? "Edit Purchase Line"
              : currentMode === "view"
              ? "View Purchase Line"
              : "Purchase Line Detail"
          }
        />
      )}
      <SimpleDetailHeader
        entityName="Purchase Line"
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
                ? "Edit Purchase Line"
                : currentMode === "view"
                ? "View Purchase Line"
                : "Add New Purchase Line"}
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
            <Label htmlFor="purchase_id">purchase_id</Label>
            <Input
              type="number"
              id="purchase_id"
              placeholder="Purchase ID"
              {...register("purchase_id", { valueAsNumber: true })}
              error={errors.purchase_id && errors.purchase_id.message ? true : false}
              hint={errors.purchase_id && errors.purchase_id.message}
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
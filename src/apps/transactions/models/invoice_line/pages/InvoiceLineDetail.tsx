import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { SimpleDetailHeader } from "../../../../../components/common/SimpleDetailHeader";
import { SimpleDetailToolbar } from "../../../../../components/common/SimpleDetailToolbar";
import { createInvoiceLine, updateInvoiceLine } from "../services/invoiceLineApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { invoiceLineSchema } from "../utils/invoiceLineSchema";
import type { InvoiceLine } from "../types/invoiceLineType";
import { ScalarCard, JsonCard, BaseModelCards } from "@/apps/common/components/detail";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

interface InvoiceLineDetailProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: InvoiceLine | null;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

function InvoiceLineDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: InvoiceLineDetailProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof invoiceLineSchema>>({
    resolver: zodResolver(invoiceLineSchema),
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const initialMode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const [currentMode, setCurrentMode] = useState<"add" | "edit" | "view">(initialMode);
  const [isSaving, setIsSaving] = useState(false);
  const data = dataProp || routeState.data || null;

  const handleEdit = () => setCurrentMode("edit");
  const handleCancel = () => {
    if (inline && onCancelInline) {
      onCancelInline();
    } else {
      setCurrentMode("view");
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
      // Set flattened price fields
      if (data.price) {
        setValue("unit_price", data.price.sell || 0);
      }
    } else {
      reset({});
    }
  }, [data, reset, setValue, currentMode]);

  const preparePayload = (formValues: z.infer<typeof invoiceLineSchema>): Record<string, unknown> => {
    const numericPrice =
      typeof formValues.unit_price === "number" && Number.isFinite(formValues.unit_price) ? formValues.unit_price : 0;
    const existingPriceRaw = (data as Record<string, unknown> | null)?.price as unknown;
    const existingPrice =
      existingPriceRaw && typeof existingPriceRaw === "object" && !Array.isArray(existingPriceRaw)
        ? (existingPriceRaw as Record<string, unknown>)
        : undefined;
    const pricePayload = existingPrice ? { ...existingPrice, sell: numericPrice } : { sell: numericPrice, cost: 0 };
    return {
      ...formValues,
      price: pricePayload,
    };
  };

  const onSubmit = async (formData: z.infer<typeof invoiceLineSchema>) => {
    setIsSaving(true);
    try {
      const payload = preparePayload(formData);
      const res =
        currentMode === "add"
          ? await createInvoiceLine(payload)
          : await updateInvoiceLine(data && data.id, payload);
      if (res) {
        dispatch(
          showToast({
            message: `Invoice line ${
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
              ? "Edit Invoice Line"
              : currentMode === "view"
              ? "View Invoice Line"
              : "Invoice Line Detail"
          }
        />
      )}

      <SimpleDetailHeader
        entityName="Invoice Line"
        recordId={data?.id}
        recordName={data?.description || `Line ${data?.line_number || ''}`}
        mode={currentMode}
        backUrl={inline ? undefined : "/transactions/invoice-lines"}
        onClose={inline ? onCancelInline : undefined}
      />

      <SimpleDetailToolbar
        mode={currentMode}
        isSaving={isSaving}
        onSave={handleSubmit(onSubmit)}
        onCancel={handleCancel}
        onEdit={handleEdit}
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
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div>
            <Label htmlFor="parent">Invoice ID</Label>
            <Input
              type="number"
              id="parent"
              placeholder="Invoice ID"
              {...register("parent", { valueAsNumber: true })}
              error={errors.parent && errors.parent.message ? true : false}
              hint={errors.parent && errors.parent.message}
              disabled={currentMode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="item_id">Item ID</Label>
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
            <Label htmlFor="description">Description</Label>
            <Input
              type="text"
              id="description"
              placeholder="Description"
              {...register("description")}
              error={errors.description && errors.description.message ? true : false}
              hint={errors.description && errors.description.message}
              disabled={currentMode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="quantity">Quantity</Label>
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
            <Label htmlFor="unit_price">Unit Price</Label>
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
            <Label htmlFor="discount_amount">Discount Amount</Label>
            <Input
              type="number"
              step="0.01"
              id="discount_amount"
              placeholder="Discount Amount"
              {...register("discount_amount", { valueAsNumber: true })}
              error={errors.discount_amount && errors.discount_amount.message ? true : false}
              hint={errors.discount_amount && errors.discount_amount.message}
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

export default withDevIdentifier(InvoiceLineDetail, 'InvoiceLineDetail');

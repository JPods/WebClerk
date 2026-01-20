import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../../components/common/ComponentCard";
import Label from "../../../../../../components/form/Label";
import { Input } from "../../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../../components/common/PageBreadCrumb";
import { createPurchaseReceipt, updatePurchaseReceipt } from "../services/purchaseReceiptApi";
import { showToast } from "../../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { purchaseReceiptSchema } from "../utils/purchaseReceiptSchema";
import { PurchaseReceiptAddProps } from "../types/purchaseReceiptType";

export default function PurchaseReceiptDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: PurchaseReceiptAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof purchaseReceiptSchema>>({
    resolver: zodResolver(purchaseReceiptSchema),
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

  const onSubmit = async (formData: z.infer<typeof purchaseReceiptSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createPurchaseReceipt(formData)
          : await updatePurchaseReceipt(data && data.id, formData);
      if (res) {
        dispatch(
          showToast({
            message: `Purchase receipt ${
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
              ? "Edit Purchase Receipt"
              : mode === "view"
              ? "View Purchase Receipt"
              : "Purchase Receipt Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Purchase Receipt"
                : mode === "view"
                ? "View Purchase Receipt"
                : "Add New Purchase Receipt"}
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
            <Label htmlFor="purchase_order_id">purchase_order_id</Label>
            <Input
              type="number"
              id="purchase_order_id"
              placeholder="Purchase Order ID"
              {...register("purchase_order_id", { valueAsNumber: true })}
              error={errors.purchase_order_id && errors.purchase_order_id.message ? true : false}
              hint={errors.purchase_order_id && errors.purchase_order_id.message}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="receipt_date">receipt_date</Label>
            <Input
              type="date"
              id="receipt_date"
              placeholder="Receipt Date"
              {...register("receipt_date")}
              error={errors.receipt_date && errors.receipt_date.message ? true : false}
              hint={errors.receipt_date && errors.receipt_date.message}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="received_by">received_by</Label>
            <Input
              type="text"
              id="received_by"
              placeholder="Received By"
              {...register("received_by")}
              error={errors.received_by && errors.received_by.message ? true : false}
              hint={errors.received_by && errors.received_by.message}
              disabled={mode === "view"}
            />
          </div>
          <div>
            <Label htmlFor="notes">notes</Label>
            <Input
              type="text"
              id="notes"
              placeholder="Notes"
              {...register("notes")}
              error={errors.notes && errors.notes.message ? true : false}
              hint={errors.notes && errors.notes.message}
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
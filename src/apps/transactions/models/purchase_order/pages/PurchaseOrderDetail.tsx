import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../components/common/ComponentCard";
import Label from "../../../../../components/form/Label";
import { Input } from "../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { createPurchaseOrder, updatePurchaseOrder } from "../services/purchaseOrderApi";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { purchaseOrderSchema } from "../utils/purchaseOrderSchema";
import { PurchaseOrderAddProps } from "../types/purchaseOrderType";
import { AuditTrail } from "../../../../../components/transactions/common/AuditTrail";
import PurchaseOrderStatus from "../components/PurchaseOrderStatus";

export default function PurchaseOrderDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: PurchaseOrderAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof purchaseOrderSchema>>({
    resolver: zodResolver(purchaseOrderSchema),
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

  const onSubmit = async (formData: z.infer<typeof purchaseOrderSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createPurchaseOrder(formData)
          : await updatePurchaseOrder(data && data.id, formData);
      if (res) {
        dispatch(
          showToast({
            message: `Purchase order ${
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

  const handleStatusChange = async (newStatus: string) => {
    if (!data?.id) return;
    try {
      await updatePurchaseOrder(data.id, { ...data, status: newStatus });
      dispatch(showToast({ message: `Purchase order marked as ${newStatus}`, type: "success" }));
      if (onSaved) {
        onSaved();
      }
    } catch (error: any) {
      dispatch(showToast({ message: error.message || "Failed to update status", type: "error" }));
    }
  };

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Purchase Order"
              : mode === "view"
              ? "View Purchase Order"
              : "Purchase Order Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Purchase Order"
                : mode === "view"
                ? "View Purchase Order"
                : "Add New Purchase Order"}
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
           <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
             <div>
               <Label htmlFor="purchase_order_no">purchase_order_no</Label>
               <Input
                 type="text"
                 id="purchase_order_no"
                 placeholder="Purchase Order Number"
                 {...register("purchase_order_no")}
                 error={!!errors.purchase_order_no?.message}
                 hint={errors.purchase_order_no?.message}
                 disabled={mode === "view"}
               />
             </div>
             <div>
               <Label htmlFor="status">status</Label>
               <select
                 id="status"
                 {...register("status")}
                 disabled={mode === "view"}
                 className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
               >
                 <option value="draft">Draft</option>
                 <option value="approved">Approved</option>
                 <option value="rejected">Rejected</option>
                 <option value="received">Received</option>
                 <option value="closed">Closed</option>
               </select>
               {errors.status && <p className="text-red-500 text-sm">{errors.status.message}</p>}
             </div>
           </div>
          {mode === "view" && data && (
            <div className="space-y-6">
              <div>
                <Label htmlFor="dt_created">dt_created</Label>
                <Input
                  type="text"
                  id="dt_created"
                  value={new Date(data.dt_created * 1000).toLocaleString()}
                  disabled
                />
                {data.id && <AuditTrail transactionId={data.id} model="purchase_order" />}
              </div>

              {/* Status Management */}
              <div>
                <Label>Purchase Order Status</Label>
                <PurchaseOrderStatus
                  currentStatus={data.status || 'draft'}
                  onStatusChange={handleStatusChange}
                  showHistory={true}
                />
              </div>
            </div>
          )}
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
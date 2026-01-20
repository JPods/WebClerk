import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../../../../../components/common/ComponentCard";
import Label from "../../../../../../components/form/Label";
import { Input } from "../../../../../../components/wrapper";

import PageBreadcrumb from "../../../../../../components/common/PageBreadCrumb";
import { createSalesOrder, updateSalesOrder } from "../services/salesOrderApi";
import { showToast } from "../../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useLocation } from "react-router";
import { salesOrderSchema } from "../utils/salesOrderSchema";
import { SalesOrderAddProps } from "../types/salesOrderType";
import { AuditTrail } from "../../../../../../components/transactions/common/AuditTrail";
import SalesOrderStatus from "../components/SalesOrderStatus";

export default function SalesOrderDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: SalesOrderAddProps) {
  const dispatch = useDispatch();

  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<z.infer<typeof salesOrderSchema>>({
    resolver: zodResolver(salesOrderSchema),
  });

  const location = useLocation();
  const routeState = (location.state as any) || {};
  const mode: "add" | "edit" | "view" = modeProp || routeState.mode || "add";
  const data = dataProp || routeState.data || null;
  useEffect(() => {
    if (mode === "add") {
      reset();
    } else if (data) {
      Object.keys(data).forEach((key: string) => {
        if (data[key] !== undefined) {
          setValue(key as any, data[key]);
        }
      });
    } else {
      reset({});
    }
  }, [data, reset, setValue, mode]);

  const onSubmit = async (formData: z.infer<typeof salesOrderSchema>) => {
    try {
      const res =
        mode === "add"
          ? await createSalesOrder(formData)
          : await updateSalesOrder(data && data.id, formData);
      if (res) {
        dispatch(
          showToast({
            message: `Sales order ${
              mode === "add" ? "created" : "updated"
            } successfully`,
            type: "success",
          })
        );
        if (onSaved) {
          onSaved();
        }
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'An error occurred';
      dispatch(showToast({ message, type: "error" }));
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    if (!data?.id) return;
    try {
      await updateSalesOrder(data.id, { ...data, status: newStatus });
      dispatch(showToast({ message: `Sales order marked as ${newStatus}`, type: "success" }));
      if (onSaved) {
        onSaved();
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to update status";
      dispatch(showToast({ message, type: "error" }));
    }
  };

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Sales Order"
              : mode === "view"
              ? "View Sales Order"
              : "Sales Order Detail"
          }
        />
      )}
      <ComponentCard>
        {inline && (
          <div className="flex justify-between items-center mb-4">
            <h3 className="dark:text-white text-lg font-semibold">
              {mode === "edit"
                ? "Edit Sales Order"
                : mode === "view"
                ? "View Sales Order"
                : "Add New Sales Order"}
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
               <Label htmlFor="sales_order_no">sales_order_no</Label>
               <Input
                 type="text"
                 id="sales_order_no"
                 placeholder="Sales Order Number"
                 {...register("sales_order_no")}
                 error={errors.sales_order_no && errors.sales_order_no.message ? true : false}
                 hint={errors.sales_order_no && errors.sales_order_no.message}
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
                 <option value="confirmed">Confirmed</option>
                 <option value="shipped">Shipped</option>
                 <option value="delivered">Delivered</option>
                 <option value="cancelled">Cancelled</option>
               </select>
               {errors.status && <p className="text-red-500 text-sm">{errors.status.message}</p>}
             </div>
             <div>
               <Label htmlFor="id_customer">id_customer</Label>
               <Input
                 type="number"
                 id="id_customer"
                 placeholder="Customer ID"
                 {...register("id_customer")}
                 error={errors.id_customer && errors.id_customer.message ? true : false}
                 hint={errors.id_customer && errors.id_customer.message}
                 disabled={mode === "view"}
               />
             </div>
             <div>
               <Label htmlFor="total">total</Label>
               <Input
                 type="number"
                 id="total"
                 placeholder="Total"
                 {...register("total")}
                 error={errors.total && errors.total.message ? true : false}
                 hint={errors.total && errors.total.message}
                 disabled={mode === "view"}
               />
             </div>
             <div>
               <Label htmlFor="tax">tax</Label>
               <Input
                 type="number"
                 id="tax"
                 placeholder="Tax"
                 {...register("tax")}
                 error={errors.tax && errors.tax.message ? true : false}
                 hint={errors.tax && errors.tax.message}
                 disabled={mode === "view"}
               />
             </div>
             <div>
               <Label htmlFor="discount">discount</Label>
               <Input
                 type="number"
                 id="discount"
                 placeholder="Discount"
                 {...register("discount")}
                 error={errors.discount && errors.discount.message ? true : false}
                 hint={errors.discount && errors.discount.message}
                 disabled={mode === "view"}
               />
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
                {data.id && <AuditTrail transactionId={data.id} model="sales_order" />}
              </div>

              {/* Status Management */}
              <div>
                <Label>Sales Order Status</Label>
                <SalesOrderStatus
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